from __future__ import annotations

import os
from collections import Counter
from typing import Any

from src.analysis.vector_search import execute_query, find_similar_awrs_approx

CURRENT_FEATURE_SET_NAME = "awr_core_metrics"
CURRENT_FEATURE_SET_VERSION = "4H_VECTOR_1"
CURRENT_VECTOR_VERSION = "4H_VECTOR_1"
RARE_PATTERN_DISTANCE_THRESHOLD = 0.25
HIGH_RISK_LEVELS = {"HIGH", "CRITICAL"}


def is_similarity_intelligence_disabled() -> bool:
    return str(
        os.getenv("DISABLE_SIMILARITY_INTELLIGENCE", "") or ""
    ).strip().upper() in {"1", "Y", "YES", "TRUE"}


def build_similarity_intelligence(
    connection: Any,
    awr_id: int,
    feature_vector: list[float],
    top_k: int = 5,
) -> dict[str, Any]:
    source_case = _load_source_case_context(connection, awr_id)
    raw_neighbors = find_similar_awrs_approx(
        connection,
        feature_vector,
        top_k=max(top_k * 4, top_k + 5),
    )
    similar_cases = _prepare_similar_cases(
        connection=connection,
        source_awr_id=awr_id,
        raw_neighbors=raw_neighbors,
        top_k=top_k,
    )
    return {
        "enabled": True,
        "source_awr_id": awr_id,
        "similar_cases": similar_cases,
        "pattern_rarity": _build_pattern_rarity(similar_cases),
        "anomaly_validation": _build_anomaly_validation(source_case, similar_cases),
        "recommendation_context": _build_recommendation_context(
            source_case,
            similar_cases,
        ),
        "workload_cluster": _build_workload_cluster(similar_cases),
    }


def build_disabled_similarity_intelligence(reason: str) -> dict[str, Any]:
    return {
        "enabled": False,
        "reason": reason,
    }


def build_failed_similarity_intelligence(error: str) -> dict[str, Any]:
    safe_error = str(error or "").strip() or "Similarity intelligence unavailable."
    return {
        "enabled": False,
        "error": safe_error,
    }


def _prepare_similar_cases(
    connection: Any,
    source_awr_id: int,
    raw_neighbors: list[dict[str, Any]],
    top_k: int,
) -> list[dict[str, Any]]:
    nearest_by_awr: dict[int, float] = {}
    for row in raw_neighbors:
        candidate_awr_id = _safe_int(row.get("awr_id"))
        distance = _safe_float(row.get("distance"))
        if candidate_awr_id is None or distance is None:
            continue
        if candidate_awr_id == source_awr_id:
            continue
        if candidate_awr_id not in nearest_by_awr:
            nearest_by_awr[candidate_awr_id] = distance
    if not nearest_by_awr:
        return []

    metadata_by_awr = _load_similar_case_metadata(connection, list(nearest_by_awr))
    ordered_awrs = sorted(nearest_by_awr, key=lambda awr_key: nearest_by_awr[awr_key])
    similar_cases: list[dict[str, Any]] = []
    for candidate_awr_id in ordered_awrs:
        metadata = metadata_by_awr.get(candidate_awr_id)
        if metadata is None:
            continue
        distance = nearest_by_awr[candidate_awr_id]
        similar_cases.append(
            {
                "awr_id": candidate_awr_id,
                "distance": round(distance, 6),
                "similarity_score": _compute_similarity_score(distance),
                "db_name": metadata.get("db_name"),
                "source_file_name": metadata.get("source_file_name"),
                "workload_class": metadata.get("workload_class"),
                "topology_class": metadata.get("topology_class"),
                "platform_class": metadata.get("platform_class"),
                "event_class": metadata.get("event_class"),
                "primary_signal_domain": metadata.get("primary_signal_domain"),
                "risk_level": metadata.get("risk_level"),
                "total_score": metadata.get("total_score"),
            }
        )
        if len(similar_cases) >= top_k:
            break
    return similar_cases


def _build_pattern_rarity(similar_cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not similar_cases:
        return {
            "is_rare_pattern": True,
            "nearest_distance": None,
            "mean_distance": None,
            "threshold_used": RARE_PATTERN_DISTANCE_THRESHOLD,
            "reason": "No similar prior AWRs were found for this feature vector.",
        }

    distances = [
        _safe_float(case.get("distance"))
        for case in similar_cases
        if _safe_float(case.get("distance")) is not None
    ]
    if not distances:
        return {
            "is_rare_pattern": True,
            "nearest_distance": None,
            "mean_distance": None,
            "threshold_used": RARE_PATTERN_DISTANCE_THRESHOLD,
            "reason": "Nearest-neighbor distances were unavailable, so rarity is treated as high.",
        }
    nearest_distance = min(distances)
    mean_distance = sum(distances) / len(distances)
    is_rare = nearest_distance > RARE_PATTERN_DISTANCE_THRESHOLD
    if is_rare:
        reason = (
            f"Nearest similar case distance {nearest_distance:.4f} exceeds the rarity threshold."
        )
    else:
        reason = (
            f"Nearest similar case distance {nearest_distance:.4f} is within the rarity threshold."
        )
    return {
        "is_rare_pattern": is_rare,
        "nearest_distance": round(nearest_distance, 6),
        "mean_distance": round(mean_distance, 6),
        "threshold_used": RARE_PATTERN_DISTANCE_THRESHOLD,
        "reason": reason,
    }


def _build_anomaly_validation(
    source_case: dict[str, Any],
    similar_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    risk_distribution = _distribution(
        str(case.get("risk_level") or "UNKNOWN").upper() for case in similar_cases
    )
    domain_distribution = _distribution(
        str(case.get("primary_signal_domain") or "UNKNOWN").upper()
        for case in similar_cases
    )
    if not similar_cases:
        return {
            "supports_anomaly": False,
            "similar_case_count": 0,
            "risk_distribution": risk_distribution,
            "domain_distribution": domain_distribution,
            "reason": "No similar cases were found; anomaly validation is inconclusive.",
        }

    current_risk = str(source_case.get("risk_level") or "").upper()
    current_domain = str(source_case.get("primary_signal_domain") or "").upper()
    similar_case_count = len(similar_cases)
    high_risk_match_count = sum(
        1
        for case in similar_cases
        if str(case.get("risk_level") or "").upper() in HIGH_RISK_LEVELS
    )
    same_domain_count = sum(
        1
        for case in similar_cases
        if current_domain
        and str(case.get("primary_signal_domain") or "").upper() == current_domain
    )
    majority_threshold = max(1, (similar_case_count + 1) // 2)

    if current_risk in HIGH_RISK_LEVELS:
        if high_risk_match_count == 0:
            return {
                "supports_anomaly": False,
                "similar_case_count": similar_case_count,
                "risk_distribution": risk_distribution,
                "domain_distribution": domain_distribution,
                "reason": "Current case is high risk, but nearest similar cases are mostly low risk.",
            }
        if high_risk_match_count >= majority_threshold and (
            not current_domain or same_domain_count >= majority_threshold
        ):
            return {
                "supports_anomaly": True,
                "similar_case_count": similar_case_count,
                "risk_distribution": risk_distribution,
                "domain_distribution": domain_distribution,
                "reason": "Nearest similar cases support the current high-risk anomaly pattern.",
            }
        return {
            "supports_anomaly": False,
            "similar_case_count": similar_case_count,
            "risk_distribution": risk_distribution,
            "domain_distribution": domain_distribution,
            "reason": "Current case is high risk, but nearest similar cases provide only mixed anomaly support.",
        }

    if current_domain and same_domain_count >= majority_threshold:
        return {
            "supports_anomaly": True,
            "similar_case_count": similar_case_count,
            "risk_distribution": risk_distribution,
            "domain_distribution": domain_distribution,
            "reason": "Nearest similar cases agree with the current primary signal domain.",
        }
    return {
        "supports_anomaly": False,
        "similar_case_count": similar_case_count,
        "risk_distribution": risk_distribution,
        "domain_distribution": domain_distribution,
        "reason": "Nearest similar cases provide mixed support for the current anomaly interpretation.",
    }


def _build_recommendation_context(
    source_case: dict[str, Any],
    similar_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    if not similar_cases:
        return {
            "similarity_explanation": "No close prior AWRs were found, so recommendations rely on deterministic scoring alone.",
            "supporting_cases": [],
            "recommended_use": "Treat similarity as unavailable and use deterministic evidence only.",
        }

    nearest_case = similar_cases[0]
    source_domain = str(source_case.get("primary_signal_domain") or "").upper()
    explanation_domain = source_domain or str(
        nearest_case.get("primary_signal_domain") or "MIXED"
    ).upper()
    similarity_explanation = (
        f"This AWR resembles prior {explanation_domain} cases with low vector distance, "
        f"supporting the deterministic {explanation_domain} interpretation."
    )
    supporting_cases = [
        {
            "awr_id": case["awr_id"],
            "distance": case["distance"],
            "similarity_score": case["similarity_score"],
            "primary_signal_domain": case.get("primary_signal_domain"),
            "risk_level": case.get("risk_level"),
        }
        for case in similar_cases[:3]
    ]
    return {
        "similarity_explanation": similarity_explanation,
        "supporting_cases": supporting_cases,
        "recommended_use": "Use similar prior cases to explain and reinforce deterministic recommendations.",
    }


def _build_workload_cluster(similar_cases: list[dict[str, Any]]) -> dict[str, Any]:
    if not similar_cases:
        return {
            "cluster_label": "UNCLASSIFIED",
            "cluster_confidence": 0.0,
            "basis": {
                "similar_case_count": 0,
                "workload_distribution": {},
            },
        }

    workload_distribution = _distribution(
        str(case.get("workload_class") or "").strip().upper() or "UNKNOWN"
        for case in similar_cases
    )
    majority_label, majority_count = max(
        workload_distribution.items(),
        key=lambda item: item[1],
    )
    similar_case_count = len(similar_cases)
    if majority_count <= similar_case_count / 2:
        return {
            "cluster_label": "UNCLASSIFIED",
            "cluster_confidence": 0.0,
            "basis": {
                "similar_case_count": similar_case_count,
                "workload_distribution": workload_distribution,
            },
        }
    return {
        "cluster_label": majority_label,
        "cluster_confidence": round(majority_count / similar_case_count, 4),
        "basis": {
            "similar_case_count": similar_case_count,
            "workload_distribution": workload_distribution,
            "majority_count": majority_count,
        },
    }


def _load_source_case_context(connection: Any, awr_id: int) -> dict[str, Any]:
    return _load_similar_case_metadata(connection, [awr_id]).get(awr_id, {})


def _load_similar_case_metadata(
    connection: Any,
    awr_ids: list[int],
) -> dict[int, dict[str, Any]]:
    if not awr_ids:
        return {}
    binds: dict[str, Any] = {
        "feature_set_name": CURRENT_FEATURE_SET_NAME,
        "feature_set_version": CURRENT_FEATURE_SET_VERSION,
        "vector_version": CURRENT_VECTOR_VERSION,
    }
    placeholders: list[str] = []
    for index, awr_id in enumerate(awr_ids):
        bind_name = f"awr_id_{index}"
        placeholders.append(f":{bind_name}")
        binds[bind_name] = awr_id

    rows = execute_query(
        connection,
        f"""
        WITH latest_scores AS (
            SELECT feature_vector_id,
                   workload_class,
                   topology_class,
                   platform_class,
                   event_class,
                   primary_signal_domain,
                   risk_level,
                   total_score
            FROM (
                SELECT sr.feature_vector_id,
                       sr.workload_class,
                       sr.topology_class,
                       sr.platform_class,
                       sr.event_class,
                       sr.primary_signal_domain,
                       sr.risk_level,
                       sr.total_score,
                       ROW_NUMBER() OVER (
                           PARTITION BY sr.feature_vector_id
                           ORDER BY sr.scored_at DESC, sr.score_result_id DESC
                       ) AS rn
                FROM AWR_SCORE_RESULT sr
            )
            WHERE rn = 1
        )
        SELECT fv.awr_id,
               r.db_name,
               r.source_file_name,
               ls.workload_class,
               ls.topology_class,
               ls.platform_class,
               ls.event_class,
               ls.primary_signal_domain,
               ls.risk_level,
               ls.total_score
        FROM AWR_FEATURE_VECTOR fv
        LEFT JOIN AWR_REPORT r
          ON r.awr_id = fv.awr_id
         AND r.source_system_id = fv.source_system_id
        LEFT JOIN latest_scores ls
          ON ls.feature_vector_id = fv.feature_vector_id
        WHERE fv.feature_set_name = :feature_set_name
          AND fv.feature_set_version = :feature_set_version
          AND fv.vector_version = :vector_version
          AND fv.feature_vector IS NOT NULL
          AND fv.awr_id IN ({', '.join(placeholders)})
        """,
        **binds,
    )
    return {
        int(row["awr_id"]): row
        for row in rows
        if _safe_int(row.get("awr_id")) is not None
    }


def _compute_similarity_score(distance: float | None) -> float:
    numeric_distance = _safe_float(distance)
    if numeric_distance is None:
        return 0.0
    return round(max(0.0, min(1.0, 1.0 - numeric_distance)), 6)


def _distribution(values: Any) -> dict[str, int]:
    counter = Counter(str(value) for value in values if str(value))
    return dict(sorted(counter.items()))


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
