from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.models.decision import AwrDecision
from src.models.recommendation import ActionRecommendation

OUTPUT_VERSION = "phase4.frontend.v1"
OUTPUT_SOURCE = "phase4"

_METRIC_FIELD_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cpu_pct", ("DB_CPU_PCT_DB_TIME", "CPU_UTIL_AVG", "CPU_UTIL_P95")),
    ("read_latency_ms", ("READ_LATENCY_MS", "CELL_SINGLE_BLOCK_LATENCY_MS")),
    ("user_io_pressure", ("USER_IO_PRESSURE",)),
    ("hard_parses_per_sec", ("HARD_PARSES_PER_SEC",)),
    ("log_file_sync_ms", ("LOG_FILE_SYNC_MS",)),
    ("cluster_wait_pct_db_time", ("CLUSTER_WAIT_PCT_DB_TIME",)),
    ("transport_lag_sec", ("TRANSPORT_LAG_SEC", "APPLY_LAG_SEC")),
)


def build_frontend_contract(
    decision: AwrDecision,
    recommendations: list[ActionRecommendation],
    generated_at: datetime | None = None,
    output_version: str = OUTPUT_VERSION,
    source: str = OUTPUT_SOURCE,
) -> dict[str, Any]:
    timestamp = _format_timestamp(generated_at or datetime.now(timezone.utc))
    evidence = decision.evidence or {}
    flattened_features = _flatten_feature_evidence(evidence.get("feature_evidence"))

    return {
        "awr_id": decision.awr_id,
        "analysis": {
            "status": decision.overall_status,
            "primary_issue": decision.primary_issue,
            "secondary_issues": list(decision.secondary_issues),
            "severity_score": decision.severity_score,
            "confidence": decision.confidence,
        },
        "evidence": {
            "domain_scores": dict(evidence.get("domain_scores") or {}),
            "top_signals": list(evidence.get("primary_reasons") or []),
            "feature_evidence": dict(evidence.get("feature_evidence") or {}),
            "score_evidence": dict(evidence.get("score_evidence") or {}),
        },
        "metrics": _build_metrics_snapshot(flattened_features),
        "anomalies": _flatten_anomalies(evidence.get("anomaly_evidence")),
        "recommendations": [
            recommendation.to_dict() for recommendation in recommendations
        ],
        "metadata": {
            "generated_at": timestamp,
            "output_version": output_version,
            "source": source,
        },
    }


def render_frontend_contract_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=False)


def _build_metrics_snapshot(
    feature_values: dict[str, float],
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for output_name, source_names in _METRIC_FIELD_MAP:
        for source_name in source_names:
            value = feature_values.get(source_name)
            if value is None:
                continue
            metrics[output_name] = value
            break
    return metrics


def _flatten_feature_evidence(raw_feature_evidence: Any) -> dict[str, float]:
    flattened: dict[str, float] = {}
    if not isinstance(raw_feature_evidence, dict):
        return flattened
    for domain in raw_feature_evidence:
        metrics = raw_feature_evidence.get(domain)
        if not isinstance(metrics, dict):
            continue
        for metric_name, metric_value in metrics.items():
            numeric_value = _safe_float(metric_value)
            if numeric_value is None:
                continue
            flattened[str(metric_name)] = numeric_value
    return flattened


def _flatten_anomalies(raw_anomaly_evidence: Any) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    if not isinstance(raw_anomaly_evidence, dict):
        return anomalies
    for domain, entries in raw_anomaly_evidence.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            anomaly = dict(entry)
            anomaly["issue"] = domain
            anomalies.append(anomaly)
    return anomalies


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


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value_utc = value.astimezone(timezone.utc)
    return value_utc.isoformat(timespec="seconds").replace("+00:00", "Z")
