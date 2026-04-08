"""Deterministic topology and platform signal extraction from AWR text."""

from __future__ import annotations

import re
from typing import Any


RAC_TEXT_PATTERNS = (
    "global cache",
    "cache fusion",
    " gc cr",
    " gc current",
    "gc buffer busy",
    " gcs ",
    " ges ",
    "cluster",
)
DG_TEXT_PATTERNS = (
    "data guard",
    "transport lag",
    "apply lag",
    "redo transport",
    "redo apply",
    "failover",
    "switchover",
    "role transition",
    "post-failover",
    "resync",
    "managed recovery",
    "physical standby",
    "logical standby",
    "snapshot standby",
)
EXADATA_TEXT_PATTERNS = (
    "exadata",
    "cell smart table scan",
    "cell single block physical read",
    "cell multiblock physical read",
    "cell flash cache",
    "storage index",
    "predicate offload",
    "cell physical io interconnect bytes",
    "bytes eligible for predicate offload",
    "bytes saved by storage index",
    " idb ",
)
DATABASE_ROLE_PATTERNS = (
    re.compile(r"database role\s*[:=]\s*(primary|physical standby|logical standby|snapshot standby)", re.IGNORECASE),
    re.compile(r"role\s*[:=]\s*(primary|physical standby|logical standby|snapshot standby)", re.IGNORECASE),
)
INSTANCE_COUNT_PATTERNS = (
    re.compile(r"\b(\d+)\s+instances?\b", re.IGNORECASE),
    re.compile(r"\binstances?\s*[:=]\s*(\d+)\b", re.IGNORECASE),
)
LAG_PATTERNS = {
    "transport_lag_sec": (
        re.compile(r"transport lag\s*[:=]\s*([0-9:\s]+(?:day[s]?\s+[0-9:]+)?)", re.IGNORECASE),
    ),
    "apply_lag_sec": (
        re.compile(r"apply lag\s*[:=]\s*([0-9:\s]+(?:day[s]?\s+[0-9:]+)?)", re.IGNORECASE),
    ),
}
OFFLOAD_PATTERNS = {
    "cell_physical_io_interconnect_bytes": re.compile(
        r"cell physical io interconnect bytes\s*[:=]?\s*([0-9][0-9,]*(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    "bytes_eligible_for_predicate_offload": re.compile(
        r"bytes eligible for predicate offload\s*[:=]?\s*([0-9][0-9,]*(?:\.\d+)?)",
        re.IGNORECASE,
    ),
    "bytes_saved_by_storage_index": re.compile(
        r"bytes saved by storage index\s*[:=]?\s*([0-9][0-9,]*(?:\.\d+)?)",
        re.IGNORECASE,
    ),
}


def parse_topology_signals(
    lines: list[str],
    wait_events: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Extract deterministic RAC, Data Guard, and Exadata signals."""

    raw_text = "\n".join(lines)
    normalized_text = f" {_normalize_text(raw_text)} "
    cluster_wait_pct = _sum_wait_class_pct(wait_events, "Cluster")
    gc_cr_wait_pct = _sum_event_pct(wait_events, ("gc cr",))
    gc_current_wait_pct = _sum_event_pct(wait_events, ("gc current",))
    gc_buffer_busy_pct = _sum_event_pct(wait_events, ("gc buffer busy",))
    exa_cell_io_pct = _sum_event_pct(wait_events, ("cell ", " iDB"))

    explicit_instance_count = _extract_first_int(raw_text, INSTANCE_COUNT_PATTERNS)
    is_rac = bool(
        explicit_instance_count and explicit_instance_count > 1
        or cluster_wait_pct
        or gc_cr_wait_pct
        or gc_current_wait_pct
        or gc_buffer_busy_pct
        or _contains_any(normalized_text, RAC_TEXT_PATTERNS)
    )
    interconnect_stress_flag = bool(
        (cluster_wait_pct or 0.0) >= 8.0
        or (gc_cr_wait_pct or 0.0) + (gc_current_wait_pct or 0.0) >= 8.0
        or "interconnect" in normalized_text
    )
    rac_contention_flag = bool(
        (gc_buffer_busy_pct or 0.0) >= 2.0
        or (cluster_wait_pct or 0.0) >= 10.0
    )

    database_role = _extract_database_role(raw_text)
    transport_lag_sec = _extract_duration_metric(raw_text, LAG_PATTERNS["transport_lag_sec"])
    apply_lag_sec = _extract_duration_metric(raw_text, LAG_PATTERNS["apply_lag_sec"])
    failover_event_flag = _contains_any(
        normalized_text,
        ("failover", "post-failover", "resync"),
    )
    role_transition_flag = _contains_any(
        normalized_text,
        ("switchover", "role transition", "post-failover"),
    )
    post_failover_recovery_flag = _contains_any(
        normalized_text,
        ("post-failover", "resync", "managed recovery", "mrp"),
    )
    is_standby = (
        database_role in {"PHYSICAL STANDBY", "LOGICAL STANDBY", "SNAPSHOT STANDBY"}
    )
    is_primary = database_role == "PRIMARY"
    is_dataguard = bool(
        database_role
        or transport_lag_sec is not None
        or apply_lag_sec is not None
        or _contains_any(normalized_text, DG_TEXT_PATTERNS)
    )
    redo_transport_issue_flag = bool(
        (transport_lag_sec or 0.0) > 0.0
        or (apply_lag_sec or 0.0) > 0.0
        or _contains_any(normalized_text, ("redo transport", "transport lag", "apply lag", "rfs", "lns", "arch"))
    )

    exadata_metrics = {
        key: _extract_first_float(raw_text, pattern)
        for key, pattern in OFFLOAD_PATTERNS.items()
    }
    smart_scan_flag = bool(
        _contains_any(normalized_text, ("cell smart table scan", "predicate offload", "smart scan"))
    )
    flash_cache_hit_flag = bool(
        _contains_any(normalized_text, ("cell flash cache", "flash cache"))
    )
    eligible_bytes = exadata_metrics["bytes_eligible_for_predicate_offload"]
    interconnect_bytes = exadata_metrics["cell_physical_io_interconnect_bytes"]
    storage_saved_bytes = exadata_metrics["bytes_saved_by_storage_index"]
    exa_offload_efficiency = None
    if eligible_bytes is not None and eligible_bytes > 0 and interconnect_bytes is not None:
        exa_offload_efficiency = round(
            max(0.0, min(1.0, 1.0 - (interconnect_bytes / eligible_bytes))),
            6,
        )
    exa_storage_index_savings = None
    if eligible_bytes is not None and eligible_bytes > 0 and storage_saved_bytes is not None:
        exa_storage_index_savings = round(
            max(0.0, min(1.0, storage_saved_bytes / eligible_bytes)),
            6,
        )
    is_exadata = bool(
        "exadata" in _normalize_text(str(metadata.get("platform") or ""))
        or exa_cell_io_pct
        or smart_scan_flag
        or flash_cache_hit_flag
        or _contains_any(normalized_text, EXADATA_TEXT_PATTERNS)
    )
    exadata_io_benefit_flag = bool(
        smart_scan_flag
        or flash_cache_hit_flag
        or (exa_offload_efficiency or 0.0) >= 0.10
        or (exa_storage_index_savings or 0.0) >= 0.05
    )

    topology_class = _derive_topology_class(is_rac, is_dataguard, is_primary, is_standby)
    platform_class = "EXADATA" if is_exadata else "GENERIC"
    operational_event_class = _derive_operational_event_class(
        rac_contention_flag=rac_contention_flag,
        interconnect_stress_flag=interconnect_stress_flag,
        redo_transport_issue_flag=redo_transport_issue_flag,
        failover_event_flag=failover_event_flag,
        post_failover_recovery_flag=post_failover_recovery_flag,
    )

    return {
        "is_rac": is_rac,
        "instance_count": explicit_instance_count,
        "cluster_wait_pct_db_time": _round_metric(cluster_wait_pct),
        "gc_cr_wait_pct_db_time": _round_metric(gc_cr_wait_pct),
        "gc_current_wait_pct_db_time": _round_metric(gc_current_wait_pct),
        "gc_buffer_busy_pct_db_time": _round_metric(gc_buffer_busy_pct),
        "interconnect_stress_flag": interconnect_stress_flag,
        "rac_contention_flag": rac_contention_flag,
        "is_dataguard": is_dataguard,
        "database_role": database_role,
        "is_primary": is_primary,
        "is_standby": is_standby,
        "transport_lag_sec": transport_lag_sec,
        "apply_lag_sec": apply_lag_sec,
        "redo_transport_issue_flag": redo_transport_issue_flag,
        "failover_event_flag": failover_event_flag,
        "role_transition_flag": role_transition_flag,
        "post_failover_recovery_flag": post_failover_recovery_flag,
        "is_exadata": is_exadata,
        "smart_scan_flag": smart_scan_flag,
        "exa_cell_io_pct_db_time": _round_metric(exa_cell_io_pct),
        "exa_offload_efficiency": exa_offload_efficiency,
        "exa_storage_index_savings": exa_storage_index_savings,
        "flash_cache_hit_flag": flash_cache_hit_flag,
        "exadata_io_benefit_flag": exadata_io_benefit_flag,
        "topology_class": topology_class,
        "platform_class": platform_class,
        "operational_event_class": operational_event_class,
        "evidence": {
            "rac_text_detected": _contains_any(normalized_text, RAC_TEXT_PATTERNS),
            "dg_text_detected": _contains_any(normalized_text, DG_TEXT_PATTERNS),
            "exadata_text_detected": _contains_any(normalized_text, EXADATA_TEXT_PATTERNS),
            "offload_metrics": exadata_metrics,
        },
    }


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern.lower() in text for pattern in patterns)


def _sum_wait_class_pct(wait_events: list[dict[str, Any]], wait_class: str) -> float | None:
    values = [
        _to_float(row.get("pct_db_time"))
        for row in wait_events
        if str(row.get("wait_class") or "").strip().lower() == wait_class.lower()
    ]
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return sum(numeric_values)


def _sum_event_pct(wait_events: list[dict[str, Any]], name_patterns: tuple[str, ...]) -> float | None:
    values = []
    for row in wait_events:
        event_name = str(row.get("event_name") or "").lower()
        if any(pattern.lower() in event_name for pattern in name_patterns):
            pct_db_time = _to_float(row.get("pct_db_time"))
            if pct_db_time is not None:
                values.append(pct_db_time)
    if not values:
        return None
    return sum(values)


def _extract_database_role(text: str) -> str | None:
    for pattern in DATABASE_ROLE_PATTERNS:
        match = pattern.search(text)
        if match is None:
            continue
        return " ".join(match.group(1).upper().split())
    return None


def _extract_duration_metric(text: str, patterns: tuple[re.Pattern[str], ...]) -> float | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match is None:
            continue
        return _duration_to_seconds(match.group(1))
    return None


def _duration_to_seconds(value: str) -> float | None:
    candidate = " ".join(value.strip().split())
    if not candidate:
        return None
    day_match = re.fullmatch(r"(\d+)\s+day[s]?\s+(\d{1,2}):(\d{2}):(\d{2})", candidate, re.IGNORECASE)
    if day_match:
        days = int(day_match.group(1))
        hours = int(day_match.group(2))
        minutes = int(day_match.group(3))
        seconds = int(day_match.group(4))
        return float((((days * 24) + hours) * 60 + minutes) * 60 + seconds)
    time_match = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})", candidate)
    if time_match:
        hours = int(time_match.group(1))
        minutes = int(time_match.group(2))
        seconds = int(time_match.group(3))
        return float((hours * 60 + minutes) * 60 + seconds)
    numeric_value = _to_float(candidate)
    return numeric_value


def _extract_first_int(text: str, patterns: tuple[re.Pattern[str], ...]) -> int | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match is None:
            continue
        value = _to_int(match.group(1))
        if value is not None:
            return value
    return None


def _extract_first_float(text: str, pattern: re.Pattern[str]) -> float | None:
    match = pattern.search(text)
    if match is None:
        return None
    return _to_float(match.group(1))


def _derive_topology_class(
    is_rac: bool,
    is_dataguard: bool,
    is_primary: bool,
    is_standby: bool,
) -> str:
    if is_rac and is_dataguard:
        return "RAC_PLUS_ADG"
    if is_rac:
        return "RAC"
    if is_standby:
        return "ADG_STANDBY"
    if is_primary and is_dataguard:
        return "ADG_PRIMARY"
    return "SINGLE_INSTANCE"


def _derive_operational_event_class(
    rac_contention_flag: bool,
    interconnect_stress_flag: bool,
    redo_transport_issue_flag: bool,
    failover_event_flag: bool,
    post_failover_recovery_flag: bool,
) -> str:
    if failover_event_flag:
        return "FAILOVER_EVENT"
    if post_failover_recovery_flag:
        return "POST_FAILOVER_RECOVERY"
    if redo_transport_issue_flag:
        return "REDO_TRANSPORT_LAG"
    if interconnect_stress_flag:
        return "INTERCONNECT_STRESS"
    if rac_contention_flag:
        return "RAC_CONTENTION"
    return "NONE"


def _round_metric(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def _to_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    return None


def _to_int(value: Any) -> int | None:
    numeric_value = _to_float(value)
    if numeric_value is None:
        return None
    return int(numeric_value)
