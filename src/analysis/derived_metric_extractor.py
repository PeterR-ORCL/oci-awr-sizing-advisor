"""Extract derived AWR metrics for spill pressure, temp I/O pressure, and hard parses."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from src.models.parse_result import ParseResult


SNAPSHOT_TIME_FORMAT = "%d-%b-%y %H:%M:%S"
SNAPSHOT_TIME_PATTERN = re.compile(
    r"(\d{2}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2})"
)


def has_data(value: Any) -> bool:
    return value is not None


def extract_derived_pressure_metrics(snapshot: ParseResult) -> dict[str, Any]:
    """Return the three derived pressure metrics plus their raw inputs.

    All inputs are best-effort and missing values return ``None`` rather than
    raising. Numbers are expected to have already been parsed from AWR text
    with commas and spacing normalized by the upstream parsers.
    """

    optimal = _first_non_null(
        _extract_instance_activity_total(snapshot, "workarea executions - optimal"),
        _coerce_non_negative((snapshot.workarea_histogram or {}).get("optimal_executions")),
    )
    onepass = _first_non_null(
        _extract_instance_activity_total(snapshot, "workarea executions - onepass"),
        _coerce_non_negative((snapshot.workarea_histogram or {}).get("onepass_executions")),
    )
    multipass = _first_non_null(
        _extract_instance_activity_total(snapshot, "workarea executions - multipass"),
        _coerce_non_negative((snapshot.workarea_histogram or {}).get("multipass_executions")),
    )
    temp_reads = _extract_instance_activity_total(
        snapshot,
        "physical reads direct temporary tablespace",
    )
    temp_writes = _extract_instance_activity_total(
        snapshot,
        "physical writes direct temporary tablespace",
    )
    if temp_reads is None or temp_writes is None:
        temp_reads, temp_writes = _extract_temp_tablespace_io(snapshot)

    hard_parses = _first_non_null(
        _extract_instance_activity_total(snapshot, "parse count (hard)"),
        _derive_hard_parses_total(snapshot),
    )
    elapsed_seconds = _derive_elapsed_seconds(snapshot)
    in_memory_sort_pct = _extract_instance_efficiency_pct(snapshot, "In-memory Sort %")

    pga_spill_pressure = _compute_pga_spill_pressure(
        optimal,
        onepass,
        multipass,
        in_memory_sort_pct,
    )
    temp_io_pressure = _compute_temp_io_pressure(temp_reads, temp_writes, elapsed_seconds)
    hard_parses_per_sec = _compute_hard_parses_per_sec(hard_parses, elapsed_seconds)

    availability = {
        "pga_spill_pressure": has_data(pga_spill_pressure),
        "temp_io_pressure": has_data(temp_io_pressure),
        "hard_parses_per_sec": has_data(hard_parses_per_sec),
    }
    found_sources = {
        "optimal": has_data(optimal),
        "onepass": has_data(onepass),
        "multipass": has_data(multipass),
        "in_memory_sort_pct": has_data(in_memory_sort_pct),
        "temp_reads": has_data(temp_reads),
        "temp_writes": has_data(temp_writes),
        "hard_parses": has_data(hard_parses),
        "elapsed_seconds": has_data(elapsed_seconds),
    }

    return {
        "pga_spill_pressure": pga_spill_pressure,
        "temp_io_pressure": temp_io_pressure,
        "hard_parses_per_sec": hard_parses_per_sec,
        "availability": availability,
        "raw": {
            "optimal": optimal,
            "onepass": onepass,
            "multipass": multipass,
            "in_memory_sort_pct": in_memory_sort_pct,
            "temp_reads": temp_reads,
            "temp_writes": temp_writes,
            "hard_parses": hard_parses,
            "elapsed_seconds": elapsed_seconds,
        },
        "debug_summary": _build_debug_summary(found_sources, availability),
    }


def _compute_pga_spill_pressure(
    optimal: float | None,
    onepass: float | None,
    multipass: float | None,
    in_memory_sort_pct: float | None,
) -> float | None:
    if not has_data(optimal) or not has_data(onepass) or not has_data(multipass):
        return _derive_pga_proxy_from_in_memory_sort(in_memory_sort_pct)

    total = float(optimal) + float(onepass) + float(multipass)
    if total <= 0:
        return _derive_pga_proxy_from_in_memory_sort(in_memory_sort_pct)
    return (float(onepass) + float(multipass)) / total


def _compute_temp_io_pressure(
    temp_reads: float | None,
    temp_writes: float | None,
    elapsed_seconds: float | None,
) -> float | None:
    if not has_data(temp_reads) or not has_data(temp_writes):
        return None
    if not has_data(elapsed_seconds) or float(elapsed_seconds) <= 0:
        return None
    return (float(temp_reads) + float(temp_writes)) / float(elapsed_seconds)


def _compute_hard_parses_per_sec(
    hard_parses: float | None,
    elapsed_seconds: float | None,
) -> float | None:
    if not has_data(hard_parses):
        return None
    if not has_data(elapsed_seconds) or float(elapsed_seconds) <= 0:
        return None
    return float(hard_parses) / float(elapsed_seconds)


def _extract_instance_activity_total(snapshot: ParseResult, statistic_name: str) -> float | None:
    for row in snapshot.instance_activity_stats:
        if str(row.get("statistic_name") or "").strip().lower() != statistic_name.lower():
            continue
        value = row.get("total")
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    return None


def _derive_hard_parses_total(snapshot: ParseResult) -> float | None:
    for row in snapshot.cpu_metrics:
        if str(row.get("metric_group") or "") != "load_profile":
            continue
        if str(row.get("metric_name") or "").strip() != "Hard parses":
            continue
        per_second = row.get("per_second")
        elapsed_seconds = _derive_elapsed_seconds(snapshot)
        if (
            isinstance(per_second, (int, float))
            and per_second >= 0
            and isinstance(elapsed_seconds, (int, float))
            and elapsed_seconds > 0
        ):
            return float(per_second) * float(elapsed_seconds)
    return None


def _extract_instance_efficiency_pct(snapshot: ParseResult, metric_name: str) -> float | None:
    for row in snapshot.cpu_metrics:
        if str(row.get("metric_group") or "") != "instance_efficiency":
            continue
        if str(row.get("metric_name") or "").strip() != metric_name:
            continue
        value = row.get("metric_value")
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    return None


def _extract_temp_tablespace_io(snapshot: ParseResult) -> tuple[float | None, float | None]:
    for row in snapshot.tablespace_io_stats:
        if str(row.get("tablespace") or "").upper() != "TEMP":
            continue
        reads = row.get("reads")
        writes = row.get("writes")
        if not isinstance(reads, (int, float)) or reads < 0:
            return None, None
        if not isinstance(writes, (int, float)) or writes < 0:
            return None, None
        return float(reads), float(writes)
    return None, None


def _derive_pga_proxy_from_in_memory_sort(in_memory_sort_pct: float | None) -> float | None:
    if not isinstance(in_memory_sort_pct, (int, float)):
        return None

    pct = float(in_memory_sort_pct)
    if pct >= 99.5:
        return 0.0
    if pct >= 97.0:
        return 0.03
    if pct >= 90.0:
        return 0.12
    return 0.28


def _derive_elapsed_seconds(snapshot: ParseResult) -> float | None:
    begin = _extract_snapshot_datetime(snapshot.run_metadata.begin_snapshot_time)
    end = _extract_snapshot_datetime(snapshot.run_metadata.end_snapshot_time)
    if not begin or not end:
        return None

    elapsed_seconds = (end - begin).total_seconds()
    if elapsed_seconds <= 0:
        return None
    return elapsed_seconds


def _extract_snapshot_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None

    match = SNAPSHOT_TIME_PATTERN.search(value)
    if not match:
        return None

    try:
        return datetime.strptime(match.group(1), SNAPSHOT_TIME_FORMAT)
    except ValueError:
        return None


def _coerce_non_negative(value: Any) -> float | None:
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return None


def _first_non_null(*values: float | None) -> float | None:
    for value in values:
        if value is not None:
            return value
    return None


def _build_debug_summary(
    found_sources: dict[str, bool],
    availability: dict[str, bool],
) -> list[str]:
    summary: list[str] = []
    found = [name for name, present in found_sources.items() if present]
    missing = [name for name, present in found_sources.items() if not present]

    if found:
        summary.append("Found source stats: " + ", ".join(found))
    if missing:
        summary.append("Missing source stats: " + ", ".join(missing))

    for metric_name, present in availability.items():
        if present:
            summary.append(f"Computed {metric_name}.")
        else:
            summary.append(f"Skipped {metric_name}: source data absent in this AWR.")

    return summary
