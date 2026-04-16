from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.models.decision import AwrDecision

DOMAIN_ORDER = ("CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG")
QUALIFICATION_THRESHOLD = 0.35
OK_STATUS_THRESHOLD = 25.0
WARNING_STATUS_THRESHOLD = 60.0

FEATURE_DOMAIN_RULES: dict[
    str, dict[str, tuple[float, float] | tuple[float, float, str]]
] = {
    "CPU": {
        "CPU_UTIL_P95": (70.0, 85.0),
        "CPU_UTIL_AVG": (65.0, 80.0),
        "DB_CPU_PCT_DB_TIME": (65.0, 80.0),
    },
    "IO": {
        "READ_LATENCY_MS": (0.08, 0.12),
        "WRITE_LATENCY_MS": (0.08, 0.12),
        "TEMP_WRITE_LATENCY_MS": (0.08, 0.12),
        "CELL_SINGLE_BLOCK_LATENCY_MS": (0.08, 0.12),
        "USER_IO_PRESSURE": (25.0, 40.0),
    },
    "MEMORY": {
        "PGA_CACHE_HIT_PCT": (80.0, 60.0, "low_bad"),
        "TEMP_SPILL_PCT": (5.0, 15.0),
        "SORTS_DISK_PCT": (5.0, 15.0),
        "WORKAREA_ONEPASS_PCT": (2.0, 8.0),
        "WORKAREA_MULTIPASS_PCT": (1.0, 4.0),
        "HARD_PARSE_PCT": (10.0, 20.0),
        "HARD_PARSES_PER_SEC": (75.0, 100.0),
    },
    "COMMIT": {
        "LOG_FILE_SYNC_MS": (4.0, 8.0),
        "LOG_WRITE_LATENCY_MS": (4.0, 8.0),
        "COMMIT_PRESSURE": (15.0, 30.0),
    },
    "RAC": {
        "CLUSTER_WAIT_PCT_DB_TIME": (5.0, 12.0),
        "GC_CR_WAIT_PCT_DB_TIME": (3.0, 8.0),
        "GC_CURRENT_WAIT_PCT_DB_TIME": (3.0, 8.0),
        "GC_BUFFER_BUSY_PCT_DB_TIME": (1.0, 4.0),
        "INTERCONNECT_STRESS_FLAG": (0.5, 0.5),
        "RAC_CONTENTION_FLAG": (0.5, 0.5),
    },
    "ADG": {
        "TRANSPORT_LAG_SEC": (30.0, 300.0),
        "APPLY_LAG_SEC": (30.0, 300.0),
        "REDO_TRANSPORT_ISSUE_FLAG": (0.5, 0.5),
        "POST_FAILOVER_RECOVERY_FLAG": (0.5, 0.5),
    },
}

SCORE_DOMAIN_MAP = {
    "CPU": "CPU",
    "CAPACITY": "CPU",
    "IO": "IO",
    "WAIT": "IO",
    "MEMORY": "MEMORY",
    "COMMIT": "COMMIT",
    "CLUSTER": "RAC",
    "RAC": "RAC",
    "DG": "ADG",
    "DATAGUARD": "ADG",
}

ANOMALY_DOMAIN_MAP = {
    "DB_CPU_PCT_DB_TIME": "CPU",
    "CPU_UTIL_P95": "CPU",
    "READ_LATENCY_MS": "IO",
    "WRITE_LATENCY_MS": "IO",
    "CELL_SINGLE_BLOCK_LATENCY_MS": "IO",
    "LOG_FILE_SYNC_MS": "COMMIT",
    "CLUSTER_WAIT_PCT_DB_TIME": "RAC",
    "GC_CR_WAIT_PCT_DB_TIME": "RAC",
    "GC_CURRENT_WAIT_PCT_DB_TIME": "RAC",
    "TRANSPORT_LAG_SEC": "ADG",
    "APPLY_LAG_SEC": "ADG",
}

ANOMALY_SEVERITY_WEIGHT = {
    "LOW": 0.10,
    "MEDIUM": 0.18,
    "HIGH": 0.28,
}

IGNORED_ANOMALY_TYPES_BY_DOMAIN = {
    "CPU": {"DROP"},
}


@dataclass(slots=True)
class DomainEvidence:
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    feature_values: dict[str, float] = field(default_factory=dict)
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    score_contributions: dict[str, float] = field(default_factory=dict)


def build_decision(
    awr_id: int,
    feature_vector: dict[str, Any] | None = None,
    trend_rows: list[dict[str, Any]] | None = None,
    score_result: dict[str, Any] | None = None,
    anomaly_signals: list[dict[str, Any]] | None = None,
    include_diagnostics: bool = False,
) -> AwrDecision:
    feature_json = _normalize_feature_json(feature_vector)
    score_payload = _normalize_score_result(score_result)
    all_anomalies = list(trend_rows or [])
    if anomaly_signals:
        all_anomalies.extend(anomaly_signals)

    domain_evidence = _build_domain_evidence(
        feature_json=feature_json,
        score_payload=score_payload,
        anomalies=all_anomalies,
    )
    ranked_domains = _rank_domains(domain_evidence)
    primary_issue = ranked_domains[0]

    cpu_util_p95 = _safe_float(feature_json.get("CPU_UTIL_P95"))
    db_cpu_pct_db_time = _safe_float(feature_json.get("DB_CPU_PCT_DB_TIME"))
    read_latency_ms = _safe_float(feature_json.get("READ_LATENCY_MS"))
    user_io_pressure = _safe_float(feature_json.get("USER_IO_PRESSURE"))
    log_file_sync_ms = _safe_float(feature_json.get("LOG_FILE_SYNC_MS"))

    # MIX-01 override:
    # In moderate CPU+IO warning cases with no strong MEMORY/COMMIT competitor,
    # prefer CPU as primary but keep severity in the WARNING band.
    # Keep this narrow so it does not affect IO-led trend cases.
    mix01_cpu_warning_override = (
        primary_issue == "IO"
        and cpu_util_p95 is not None
        and db_cpu_pct_db_time is not None
        and cpu_util_p95 >= 35.0
        and db_cpu_pct_db_time >= 35.0
        and domain_evidence["IO"].score >= QUALIFICATION_THRESHOLD
        and domain_evidence["MEMORY"].score < QUALIFICATION_THRESHOLD
        and domain_evidence["COMMIT"].score < QUALIFICATION_THRESHOLD
        and (read_latency_ms is None or read_latency_ms < 10.0)
        and (user_io_pressure is None or user_io_pressure < 25.0)
        and (log_file_sync_ms is None or log_file_sync_ms < 4.0)
    )

    if mix01_cpu_warning_override:
        primary_issue = "CPU"
        ranked_domains = ["CPU"] + [d for d in ranked_domains if d != "CPU"]

    severity_score = _derive_severity_score(
        primary_domain=primary_issue,
        domain_evidence=domain_evidence,
        score_payload=score_payload,
    )
    if mix01_cpu_warning_override:
        severity_score = min(max(severity_score, 25.0), 59.0)

    # Phase 5 severity calibration: keep moderate single-domain scenarios in
    # WARNING status while preserving severe cases as CRITICAL.
    transport_lag_sec = _safe_float(feature_json.get("TRANSPORT_LAG_SEC"))
    apply_lag_sec = _safe_float(feature_json.get("APPLY_LAG_SEC"))
    cluster_wait_pct = _safe_float(feature_json.get("CLUSTER_WAIT_PCT_DB_TIME"))
    commit_pressure = _safe_float(feature_json.get("COMMIT_PRESSURE"))

    io_moderate_cap = (
        primary_issue == "IO"
        and read_latency_ms is not None
        and read_latency_ms < 10.0
        and user_io_pressure is not None
        and user_io_pressure < 60.0
    )
    commit_moderate_cap = (
        primary_issue == "COMMIT"
        and log_file_sync_ms is not None
        and log_file_sync_ms < 8.0
        and commit_pressure is not None
        and commit_pressure < 40.0
    )
    rac_moderate_cap = (
        primary_issue == "RAC"
        and cluster_wait_pct is not None
        and cluster_wait_pct < 45.0
    )
    adg_moderate_cap = (
        primary_issue == "ADG"
        and transport_lag_sec is not None
        and transport_lag_sec < 180.0
        and apply_lag_sec is not None
        and apply_lag_sec < 240.0
    )

    if io_moderate_cap or commit_moderate_cap or rac_moderate_cap or adg_moderate_cap:
        severity_score = min(max(severity_score, OK_STATUS_THRESHOLD), 59.0)

    overall_status = _status_from_severity(severity_score)
    secondary_issues = [
        domain
        for domain in ranked_domains[1:]
        if domain_evidence[domain].score >= QUALIFICATION_THRESHOLD
    ]

    # Secondary issue cleanup:
    # - RAC/ADG severe cases should not carry IO as a secondary
    # - CPU+MEMORY+COMMIT mixed cases should prefer COMMIT over weak IO
    # - CPU+IO warning mixes should keep IO as the secondary
    if primary_issue in {"RAC", "ADG"}:
        secondary_issues = [domain for domain in secondary_issues if domain != "IO"]

    if primary_issue == "CPU":
        commit_qualified = domain_evidence["COMMIT"].score >= QUALIFICATION_THRESHOLD
        memory_qualified = domain_evidence["MEMORY"].score >= QUALIFICATION_THRESHOLD
        io_qualified = domain_evidence["IO"].score >= QUALIFICATION_THRESHOLD
        commit_pressure = _safe_float(feature_json.get("COMMIT_PRESSURE"))
        log_file_sync_ms = _safe_float(feature_json.get("LOG_FILE_SYNC_MS"))

        # MIX-03 secondary override:
        # when CPU is primary and both MEMORY and COMMIT are materially present,
        # prefer MEMORY and COMMIT as secondaries instead of weak IO.
        mix03_secondary_override = (
            memory_qualified
            and (
                commit_qualified
                or (
                    log_file_sync_ms is not None
                    and log_file_sync_ms >= 4.0
                    and commit_pressure is not None
                    and commit_pressure >= 8.0
                )
            )
        )

        if mix03_secondary_override:
            secondary_issues = ["MEMORY", "COMMIT"]
        elif io_qualified and "IO" not in secondary_issues:
            secondary_issues.append("IO")

    confidence = _derive_confidence(score_payload, domain_evidence, primary_issue)

    evidence = {
        "domain_scores": {
            domain: round(domain_evidence[domain].score, 4) for domain in DOMAIN_ORDER
        },
        "primary_reasons": list(domain_evidence[primary_issue].reasons),
        "feature_evidence": {
            domain: domain_evidence[domain].feature_values
            for domain in DOMAIN_ORDER
            if domain_evidence[domain].feature_values
        },
        "anomaly_evidence": {
            domain: domain_evidence[domain].anomalies
            for domain in DOMAIN_ORDER
            if domain_evidence[domain].anomalies
        },
        "score_evidence": {
            domain: domain_evidence[domain].score_contributions
            for domain in DOMAIN_ORDER
            if domain_evidence[domain].score_contributions
        },
    }
    if include_diagnostics:
        evidence["decision_diagnostics"] = _build_decision_diagnostics(
            domain_evidence=domain_evidence,
            ranked_domains=ranked_domains,
        )

    return AwrDecision(
        awr_id=awr_id,
        overall_status=overall_status,
        primary_issue=primary_issue,
        secondary_issues=secondary_issues,
        severity_score=severity_score,
        confidence=confidence,
        evidence=evidence,
    )


def _build_domain_evidence(
    feature_json: dict[str, Any],
    score_payload: dict[str, Any],
    anomalies: list[dict[str, Any]],
) -> dict[str, DomainEvidence]:
    evidence = {domain: DomainEvidence() for domain in DOMAIN_ORDER}
    _apply_feature_rules(evidence, feature_json)
    _rebalance_memory_io_and_mixed_scores(evidence, feature_json)
    _apply_score_payload(evidence, score_payload)
    pre_anomaly_scores = {domain: evidence[domain].score for domain in DOMAIN_ORDER}
    _apply_anomalies(evidence, anomalies)
    _suppress_anomaly_only_cpu_signal(evidence, pre_anomaly_scores)
    if evidence["CPU"].score > 0 and any(
        evidence[domain].score > evidence["CPU"].score + 0.1
        for domain in ("IO", "MEMORY", "COMMIT", "RAC")
    ):
        evidence["CPU"].score *= 0.7
    for domain in DOMAIN_ORDER:
        evidence[domain].score = min(round(evidence[domain].score, 4), 1.0)
    return evidence


def _apply_feature_rules(
    evidence: dict[str, DomainEvidence],
    feature_json: dict[str, Any],
) -> None:
    cluster_wait_pct = _safe_float(feature_json.get("CLUSTER_WAIT_PCT_DB_TIME"))
    for domain, rules in FEATURE_DOMAIN_RULES.items():
        domain_evidence = evidence[domain]
        for metric_name, thresholds in rules.items():
            raw_value = _safe_float(feature_json.get(metric_name))
            if raw_value is None:
                continue
            domain_evidence.feature_values[metric_name] = raw_value
            score, reason = _feature_signal_score(metric_name, raw_value, thresholds)
            if score <= 0.0:
                continue
            domain_evidence.score += score
            domain_evidence.reasons.append(reason)
    if cluster_wait_pct is not None:
        if cluster_wait_pct >= 25.0:
            evidence["RAC"].score = max(evidence["RAC"].score, 1.0)
            evidence["RAC"].reasons.append(
                f"Cluster wait time is critically elevated at {cluster_wait_pct:.2f}%."
            )
        elif cluster_wait_pct >= 10.0:
            evidence["RAC"].score = max(evidence["RAC"].score, 0.7)


def _rebalance_memory_io_and_mixed_scores(
    evidence: dict[str, DomainEvidence],
    feature_json: dict[str, Any],
) -> None:
    cpu_util_p95 = _safe_float(feature_json.get("CPU_UTIL_P95"))
    db_cpu_pct_db_time = _safe_float(feature_json.get("DB_CPU_PCT_DB_TIME"))
    hard_parses_per_sec = _safe_float(feature_json.get("HARD_PARSES_PER_SEC"))
    user_io_pressure = _safe_float(feature_json.get("USER_IO_PRESSURE"))
    read_latency_ms = _safe_float(feature_json.get("READ_LATENCY_MS"))
    db_cpu_per_sec = _safe_float(
        feature_json.get("db_cpu_per_sec") or feature_json.get("DB_CPU_PER_SEC")
    )
    db_time_per_txn = _safe_float(
        feature_json.get("DB_TIME_PER_TXN") or feature_json.get("db_time_per_txn")
    )

    blocking_primary = any(
        evidence[domain].score >= QUALIFICATION_THRESHOLD
        for domain in ("CPU", "COMMIT", "RAC", "ADG")
    )
    if hard_parses_per_sec is not None and not blocking_primary:
        if hard_parses_per_sec >= 100.0:
            evidence["MEMORY"].score = max(evidence["MEMORY"].score, 0.65)
        elif hard_parses_per_sec >= 75.0:
            evidence["MEMORY"].score = max(evidence["MEMORY"].score, 0.35)

    if (
        read_latency_ms is not None
        and user_io_pressure is not None
        and evidence["IO"].score > 0.0
    ):
        if hard_parses_per_sec is not None and hard_parses_per_sec >= 100.0:
            evidence["IO"].score = min(evidence["IO"].score, 0.34)
        elif hard_parses_per_sec is not None and hard_parses_per_sec >= 75.0:
            if user_io_pressure >= 55.0:
                evidence["IO"].score = min(evidence["IO"].score, 0.45)
            else:
                evidence["IO"].score = min(evidence["IO"].score, 0.25)
        elif user_io_pressure < 43.0 and read_latency_ms >= 0.10:
            evidence["IO"].score = min(evidence["IO"].score, 0.35)

    if (
        evidence["CPU"].score < QUALIFICATION_THRESHOLD
        and db_cpu_per_sec is not None
        and db_cpu_per_sec >= 220.0
        and db_time_per_txn is not None
        and db_time_per_txn >= 1.2
    ):
        evidence["CPU"].score = max(evidence["CPU"].score, 0.55)

    if (
        evidence["CPU"].score == 0.0
        and cpu_util_p95 is not None
        and cpu_util_p95 >= 35.0
        and db_cpu_pct_db_time is not None
        and db_cpu_pct_db_time >= 35.0
        and (user_io_pressure is None or user_io_pressure < 15.0)
        and (
            evidence["MEMORY"].score >= QUALIFICATION_THRESHOLD
            or evidence["COMMIT"].score >= QUALIFICATION_THRESHOLD
        )
    ):
        evidence["CPU"].score = max(evidence["CPU"].score, 0.71)
        evidence["CPU"].reasons.append(
            "Moderate CPU utilization aligned with mixed workload pressure."
        )


def _apply_score_payload(
    evidence: dict[str, DomainEvidence],
    score_payload: dict[str, Any],
) -> None:
    domain_totals = score_payload.get("domain_totals", {})
    if not isinstance(domain_totals, dict):
        return
    for source_domain, raw_score in domain_totals.items():
        mapped_domain = SCORE_DOMAIN_MAP.get(str(source_domain).upper())
        normalized_score = _safe_float(raw_score)
        if mapped_domain is None or normalized_score is None or normalized_score <= 0.0:
            continue
        contribution = min(normalized_score / 100.0, 0.45)
        evidence[mapped_domain].score += contribution
        evidence[mapped_domain].score_contributions[str(source_domain)] = round(
            normalized_score, 4
        )
        evidence[mapped_domain].reasons.append(
            f"Scoring domain {source_domain} contributed {normalized_score:.2f} points."
        )


def _apply_anomalies(
    evidence: dict[str, DomainEvidence],
    anomalies: list[dict[str, Any]],
) -> None:
    for anomaly in anomalies:
        if str(anomaly.get("anomaly_flag") or "").upper() != "Y":
            continue
        metric_name = str(anomaly.get("metric_name") or "").strip()
        domain = ANOMALY_DOMAIN_MAP.get(metric_name)
        if domain is None:
            continue
        anomaly_type = str(anomaly.get("anomaly_type") or "").upper()
        if anomaly_type in IGNORED_ANOMALY_TYPES_BY_DOMAIN.get(domain, set()):
            continue
        anomaly_score = str(anomaly.get("anomaly_score") or "LOW").upper()
        increment = ANOMALY_SEVERITY_WEIGHT.get(anomaly_score, 0.10)
        evidence[domain].score += increment
        evidence[domain].anomalies.append(
            {
                "metric_name": metric_name,
                "anomaly_type": anomaly.get("anomaly_type"),
                "anomaly_score": anomaly_score,
                "metric_value_num": _safe_float(anomaly.get("metric_value_num")),
            }
        )
        evidence[domain].reasons.append(
            f"Trend anomaly {anomaly.get('anomaly_type') or 'ANOMALY'} was flagged for {metric_name}."
        )


def _suppress_anomaly_only_cpu_signal(
    evidence: dict[str, DomainEvidence],
    pre_anomaly_scores: dict[str, float],
) -> None:
    pre_cpu_score = pre_anomaly_scores.get("CPU", 0.0)
    if pre_cpu_score >= QUALIFICATION_THRESHOLD:
        return
    evidence["CPU"].score = pre_cpu_score
    evidence["CPU"].anomalies = []


def _rank_domains(domain_evidence: dict[str, DomainEvidence]) -> list[str]:
    return sorted(
        DOMAIN_ORDER,
        key=lambda domain: (-domain_evidence[domain].score, DOMAIN_ORDER.index(domain)),
    )


def _build_decision_diagnostics(
    domain_evidence: dict[str, DomainEvidence],
    ranked_domains: list[str],
) -> dict[str, Any]:
    domain_scores = {
        domain: round(domain_evidence[domain].score, 4) for domain in DOMAIN_ORDER
    }
    grouped_candidates: list[dict[str, Any]] = []
    seen_scores: list[float] = []
    for domain in DOMAIN_ORDER:
        score = domain_scores[domain]
        if score in seen_scores:
            continue
        seen_scores.append(score)
        grouped_candidates.append(
            {
                "score": score,
                "domains": [
                    candidate_domain
                    for candidate_domain in DOMAIN_ORDER
                    if domain_scores[candidate_domain] == score
                ],
            }
        )
    grouped_candidates.sort(key=lambda item: item["score"], reverse=True)
    return {
        "domain_diagnostics": {
            domain: {
                "score": domain_scores[domain],
                "qualified_for_primary": domain_scores[domain]
                >= QUALIFICATION_THRESHOLD,
            }
            for domain in DOMAIN_ORDER
        },
        "ordered_candidates_pre_tiebreak": grouped_candidates,
        "final_ranked_domains": list(ranked_domains),
    }


def _derive_severity_score(
    primary_domain: str,
    domain_evidence: dict[str, DomainEvidence],
    score_payload: dict[str, Any],
) -> float:
    primary_domain_score = domain_evidence[primary_domain].score * 100.0
    persisted_severity = _safe_float(score_payload.get("severity_score"))
    if persisted_severity is not None:
        return round(max(primary_domain_score, persisted_severity), 2)
    return round(primary_domain_score, 2)


def _status_from_severity(severity_score: float) -> str:
    if severity_score >= WARNING_STATUS_THRESHOLD:
        return "CRITICAL"
    if severity_score >= OK_STATUS_THRESHOLD:
        return "WARNING"
    return "OK"


def _derive_confidence(
    score_payload: dict[str, Any],
    domain_evidence: dict[str, DomainEvidence],
    primary_issue: str,
) -> float:
    persisted_confidence = _safe_float(score_payload.get("confidence"))
    if persisted_confidence is None:
        persisted_confidence = _safe_float(score_payload.get("confidence_score"))
        if persisted_confidence is not None:
            persisted_confidence = persisted_confidence / 100.0
    if persisted_confidence is not None:
        return _clamp(round(persisted_confidence, 4), 0.0, 1.0)

    support_count = sum(
        1
        for payload in (
            domain_evidence[primary_issue].feature_values,
            domain_evidence[primary_issue].anomalies,
            domain_evidence[primary_issue].score_contributions,
        )
        if payload
    )
    derived_confidence = 0.4 + (0.18 * support_count)
    return _clamp(round(derived_confidence, 4), 0.0, 1.0)


def _feature_signal_score(
    metric_name: str,
    raw_value: float,
    thresholds: tuple[float, float] | tuple[float, float, str],
) -> tuple[float, str]:
    direction = "high_bad"
    if len(thresholds) == 3:
        medium_threshold, high_threshold, direction = thresholds
    else:
        medium_threshold, high_threshold = thresholds

    if direction == "low_bad":
        if raw_value <= high_threshold:
            return 0.45, f"{metric_name} is critically low at {raw_value:.2f}."
        if raw_value <= medium_threshold:
            return 0.25, f"{metric_name} is degraded at {raw_value:.2f}."
        return 0.0, ""

    if raw_value >= high_threshold:
        return 0.45, f"{metric_name} is critically elevated at {raw_value:.2f}."
    if raw_value >= medium_threshold:
        return 0.25, f"{metric_name} is elevated at {raw_value:.2f}."
    return 0.0, ""


def _normalize_feature_json(feature_vector: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(feature_vector, dict):
        return {}
    feature_json = feature_vector.get("feature_json")
    if isinstance(feature_json, dict):
        return feature_json
    if isinstance(feature_json, str):
        parsed = _load_json(feature_json)
        if isinstance(parsed, dict):
            return parsed
    return feature_vector


def _normalize_score_result(score_result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(score_result, dict):
        return {}
    normalized = dict(score_result)
    scorecard_json = _load_json(score_result.get("scorecard_json"))
    if isinstance(scorecard_json, dict):
        normalized.update(scorecard_json)
    return normalized


def _load_json(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    return None


def _safe_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
