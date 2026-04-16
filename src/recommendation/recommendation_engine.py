from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

MAX_RECOMMENDATIONS = 3
CPU_RECOMMENDATION_SIGNAL_KEYS = (
    "CPU_UTIL_P95",
    "DB_CPU_PCT_DB_TIME",
    "DB_CPU_PER_SEC",
    "DB_TIME_PER_TXN",
)
SEVERITY_PRIORITY_MAP = {
    "LOW": "LOW",
    "MODERATE": "MEDIUM",
    "HIGH": "HIGH",
    "CRITICAL": "CRITICAL",
}


@dataclass(slots=True)
class Recommendation:
    """Structured deterministic recommendation payload."""

    domain: str
    category: str
    title: str
    action: str
    rationale: str
    priority: str
    confidence: float
    source_signals: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def generate_recommendations(
    primary_issue: str,
    secondary_issues: list[str] | None,
    overall_status: str,
    severity: str | float | int,
    feature_vector: dict[str, Any] | None,
) -> list[Recommendation]:
    """Generate up to three deterministic Phase 6 recommendations."""

    ordered_issues = [primary_issue, *(secondary_issues or [])]
    if "CPU" not in ordered_issues:
        return []

    flattened_features = _flatten_feature_vector(feature_vector or {})
    severity_label = _normalize_severity(overall_status, severity)
    priority = SEVERITY_PRIORITY_MAP[severity_label]
    source_signals = _cpu_source_signals(flattened_features)
    confidence = _cpu_recommendation_confidence(primary_issue, source_signals)

    recommendations = [
        Recommendation(
            domain="CPU",
            category="capacity",
            title="Stabilize Sustained CPU Pressure",
            action=(
                "Reduce sustained CPU saturation by validating host capacity, "
                "concurrency limits, and workload scheduling before adding more load."
            ),
            rationale=_cpu_capacity_rationale(source_signals),
            priority=priority,
            confidence=confidence,
            source_signals=source_signals,
        ),
        Recommendation(
            domain="CPU",
            category="sql_tuning",
            title="Prioritize CPU-Heavy SQL Tuning",
            action=(
                "Tune the highest CPU-consuming SQL first, focusing on execution plans, "
                "row-source efficiency, and avoidable repeated work."
            ),
            rationale=_cpu_sql_rationale(source_signals),
            priority=priority,
            confidence=confidence,
            source_signals=source_signals,
        ),
    ]
    return recommendations[:MAX_RECOMMENDATIONS]


def _flatten_feature_vector(feature_vector: dict[str, Any]) -> dict[str, float]:
    """Flatten supported feature-vector shapes into one numeric dictionary."""

    raw_features = feature_vector.get("feature_json", feature_vector)
    if not isinstance(raw_features, dict):
        return {}

    flattened: dict[str, float] = {}
    for key, value in raw_features.items():
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                numeric_value = _safe_float(nested_value)
                if numeric_value is not None:
                    flattened[str(nested_key)] = numeric_value
            continue
        numeric_value = _safe_float(value)
        if numeric_value is not None:
            flattened[str(key)] = numeric_value
    return flattened


def _normalize_severity(
    overall_status: str,
    severity: str | float | int,
) -> str:
    """Normalize status/severity input into one recommendation severity label."""

    if isinstance(severity, str):
        normalized = severity.strip().upper()
        if normalized in SEVERITY_PRIORITY_MAP:
            return normalized

    numeric_severity = _safe_float(severity)
    if numeric_severity is not None:
        if numeric_severity >= 80.0:
            return "CRITICAL"
        if numeric_severity >= 60.0:
            return "HIGH"
        if numeric_severity >= 25.0:
            return "MODERATE"
        return "LOW"

    normalized_status = str(overall_status or "").strip().upper()
    if normalized_status == "CRITICAL":
        return "HIGH"
    if normalized_status == "WARNING":
        return "MODERATE"
    return "LOW"


def _cpu_source_signals(feature_vector: dict[str, float]) -> dict[str, float]:
    """Return only the CPU-oriented signals used by deterministic recommendations."""

    return {
        signal: feature_vector[signal]
        for signal in CPU_RECOMMENDATION_SIGNAL_KEYS
        if signal in feature_vector
    }


def _cpu_recommendation_confidence(
    primary_issue: str,
    source_signals: dict[str, float],
) -> float:
    """Derive a deterministic confidence score for CPU recommendations."""

    confidence = 0.55 if primary_issue == "CPU" else 0.4
    confidence += min(len(source_signals), 3) * 0.1
    return round(min(confidence, 0.95), 2)


def _cpu_capacity_rationale(source_signals: dict[str, float]) -> str:
    """Build a concise rationale for CPU capacity recommendations."""

    cpu_util = source_signals.get("CPU_UTIL_P95")
    db_cpu_pct = source_signals.get("DB_CPU_PCT_DB_TIME")
    signal_parts: list[str] = []
    if cpu_util is not None:
        signal_parts.append(f"CPU_UTIL_P95={cpu_util:.1f}")
    if db_cpu_pct is not None:
        signal_parts.append(f"DB_CPU_PCT_DB_TIME={db_cpu_pct:.1f}")
    if not signal_parts:
        return "CPU was selected as the dominant issue in the validated decision output."
    return "Validated CPU pressure is present via " + ", ".join(signal_parts) + "."


def _cpu_sql_rationale(source_signals: dict[str, float]) -> str:
    """Build a concise rationale for CPU-oriented SQL tuning recommendations."""

    db_cpu_per_sec = source_signals.get("DB_CPU_PER_SEC")
    db_time_per_txn = source_signals.get("DB_TIME_PER_TXN")
    signal_parts: list[str] = []
    if db_cpu_per_sec is not None:
        signal_parts.append(f"DB_CPU_PER_SEC={db_cpu_per_sec:.1f}")
    if db_time_per_txn is not None:
        signal_parts.append(f"DB_TIME_PER_TXN={db_time_per_txn:.2f}")
    if not signal_parts:
        return "CPU saturation should be reduced by tuning the highest-load SQL paths first."
    return "Supporting workload intensity signals include " + ", ".join(signal_parts) + "."


def _safe_float(value: Any) -> float | None:
    """Convert supported numeric inputs into floats."""

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
