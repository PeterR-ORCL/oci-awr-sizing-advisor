"""Build violin-panel metric arrays from AWR history or best-effort current-report samples."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from math import isfinite
from typing import Any

from src.models.parse_result import ParseResult


MIN_VALID_SAMPLES = 5
SNAPSHOT_TIME_FORMAT = "%d-%b-%y %H:%M:%S"
SNAPSHOT_TIME_PATTERN = re.compile(
    r"(\d{2}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2})"
)

EMPTY_VIOLIN_PANEL = {
    "cpu_pct": [],
    "execs_per_sec": [],
    "read_iops": [],
    "read_mb_per_sec": [],
    "write_iops": [],
    "write_mb_per_sec": [],
    "user_io_wait": [],
    "top_sql_elapsed_norm": [],
    "pga_spill_pressure": [],
    "temp_io_pressure": [],
    "hard_parses_per_sec": [],
    "log_file_sync_ms": [],
}


def build_violin_panel_data(
    parse_results: ParseResult | list[ParseResult],
) -> dict[str, list[float]]:
    """Build violin payload arrays from true history or best-effort single-report samples.

    Strict historical mode is used when multiple AWR snapshots are
    available. Best-effort single-report mode is used only when one AWR
    report exists and the report contains repeated, decomposable rows
    that form technically defensible samples. No filler or interpolated
    values are generated.
    """

    snapshots = _normalize_snapshots(parse_results)
    if len(snapshots) < 2:
        return _build_single_report_violin_panel(snapshots[0]) if snapshots else dict(EMPTY_VIOLIN_PANEL)

    return {
        "cpu_pct": _finalize_snapshot_series(
            [_extract_cpu_pct(snapshot) for snapshot in snapshots]
        ),
        "execs_per_sec": _finalize_snapshot_series(
            [_extract_load_profile_per_second(snapshot, "Executes") for snapshot in snapshots]
        ),
        "read_iops": _finalize_snapshot_series(
            [_extract_read_iops(snapshot) for snapshot in snapshots]
        ),
        "read_mb_per_sec": _finalize_snapshot_series(
            [_extract_read_mb_per_sec(snapshot) for snapshot in snapshots]
        ),
        "write_iops": _finalize_snapshot_series(
            [_extract_write_iops(snapshot) for snapshot in snapshots]
        ),
        "write_mb_per_sec": _finalize_snapshot_series(
            [_extract_write_mb_per_sec(snapshot) for snapshot in snapshots]
        ),
        "user_io_wait": _finalize_snapshot_series(
            [_extract_user_io_wait(snapshot) for snapshot in snapshots]
        ),
        "top_sql_elapsed_norm": _finalize_snapshot_series(
            [_extract_top_sql_elapsed_norm(snapshot) for snapshot in snapshots]
        ),
        "pga_spill_pressure": _finalize_snapshot_series(
            [_extract_pga_spill_pressure(snapshot) for snapshot in snapshots]
        ),
        "temp_io_pressure": _finalize_snapshot_series(
            [_extract_temp_io_pressure(snapshot) for snapshot in snapshots]
        ),
        "hard_parses_per_sec": _finalize_snapshot_series(
            [_extract_load_profile_per_second(snapshot, "Hard parses") for snapshot in snapshots]
        ),
        "log_file_sync_ms": _finalize_snapshot_series(
            [_extract_log_file_sync_ms(snapshot) for snapshot in snapshots]
        ),
    }


def _build_single_report_violin_panel(snapshot: ParseResult) -> dict[str, list[float]]:
    """Build best-effort distributions from repeated rows inside one AWR report."""

    elapsed_seconds = _derive_elapsed_seconds(snapshot)
    ash_buckets = _bucket_ash_samples_by_minute(snapshot.ash_samples or [])

    return {
        "cpu_pct": _finalize_best_effort_series(
            _ash_wait_class_pct_samples(ash_buckets, "CPU")
        ),
        "execs_per_sec": _finalize_best_effort_series(
            _top_sql_rate_samples(snapshot.top_sql, elapsed_seconds, "executions")
        ),
        "read_iops": _finalize_best_effort_series(
            _datafile_rate_samples_per_row(snapshot.datafile_io_stats, elapsed_seconds, "reads")
        ),
        "read_mb_per_sec": _finalize_best_effort_series(
            _datafile_rate_samples_per_row(snapshot.datafile_io_stats, elapsed_seconds, "read_mb")
        ),
        "write_iops": _finalize_best_effort_series(
            _datafile_rate_samples_per_row(snapshot.datafile_io_stats, elapsed_seconds, "writes")
        ),
        "write_mb_per_sec": _finalize_best_effort_series(
            _datafile_rate_samples_per_row(snapshot.datafile_io_stats, elapsed_seconds, "write_mb")
        ),
        "user_io_wait": _finalize_best_effort_series(
            _ash_wait_class_pct_samples(ash_buckets, "User I/O")
        ),
        "top_sql_elapsed_norm": _finalize_best_effort_series(
            _top_sql_elapsed_norm_samples(snapshot.top_sql)
        ),
        "pga_spill_pressure": [],
        "temp_io_pressure": _finalize_best_effort_series(
            _temp_io_pressure_samples(snapshot.tablespace_io_stats, elapsed_seconds)
        ),
        "hard_parses_per_sec": [],
        "log_file_sync_ms": _finalize_best_effort_series(
            _histogram_latency_samples(snapshot.event_histograms.get("log file sync") or [])
        ),
    }


def _normalize_snapshots(parse_results: ParseResult | list[ParseResult]) -> list[ParseResult]:
    if isinstance(parse_results, ParseResult):
        snapshots = [parse_results]
    else:
        snapshots = [snapshot for snapshot in parse_results if isinstance(snapshot, ParseResult)]

    return sorted(
        snapshots,
        key=lambda snapshot: _extract_snapshot_datetime(snapshot.run_metadata.begin_snapshot_time)
        or datetime.max,
    )


def _extract_cpu_pct(snapshot: ParseResult) -> float | None:
    db_cpu = _extract_load_profile_per_second(snapshot, "DB CPU(s)")
    db_time = _extract_load_profile_per_second(snapshot, "DB Time(s)")
    if db_cpu is None or db_time is None or db_time <= 0:
        return None
    return (db_cpu / db_time) * 100.0


def _extract_read_iops(snapshot: ParseResult) -> float | None:
    value = _extract_load_profile_per_second(snapshot, "Physical reads")
    if value is not None:
        return value
    return _extract_datafile_rate(snapshot, "reads")


def _extract_read_mb_per_sec(snapshot: ParseResult) -> float | None:
    return _extract_datafile_rate(snapshot, "read_mb")


def _extract_write_iops(snapshot: ParseResult) -> float | None:
    value = _extract_load_profile_per_second(snapshot, "Physical writes")
    if value is not None:
        return value
    return _extract_datafile_rate(snapshot, "writes")


def _extract_write_mb_per_sec(snapshot: ParseResult) -> float | None:
    return _extract_datafile_rate(snapshot, "write_mb")


def _extract_user_io_wait(snapshot: ParseResult) -> float | None:
    db_time = _extract_total_db_time_seconds(snapshot)
    if db_time is None or db_time <= 0:
        return None

    user_io_seconds = sum(
        float(wait_event.get("time_seconds") or 0.0)
        for wait_event in snapshot.wait_events
        if str(wait_event.get("wait_class") or "") == "User I/O"
    )
    return (user_io_seconds / db_time) * 100.0


def _extract_top_sql_elapsed_norm(snapshot: ParseResult) -> float | None:
    # Use the top 1 SQL elapsed-time share per snapshot to keep one
    # normalized history point per AWR interval.
    db_time = _extract_total_db_time_seconds(snapshot)
    if db_time is None or db_time <= 0 or not snapshot.top_sql:
        return None

    top_elapsed_seconds = max(
        (
            float(sql_record.get("elapsed_time_seconds"))
            for sql_record in snapshot.top_sql
            if isinstance(sql_record.get("elapsed_time_seconds"), (int, float))
        ),
        default=None,
    )
    if top_elapsed_seconds is None:
        return None
    return top_elapsed_seconds / db_time


def _extract_pga_spill_pressure(snapshot: ParseResult) -> float | None:
    # Preferred source would be onepass + multipass executions. When the
    # report exposes PGA advisory instead, use current-target overalloc
    # count normalized by total executions as the closest spill signal.
    advisory = snapshot.pga_advisory or {}
    rows = advisory.get("rows") or []
    if not rows:
        return None

    current_target_mb = advisory.get("current_target_mb")
    current_row = _pick_current_pga_advisory_row(rows, current_target_mb)
    if not current_row:
        return None

    overalloc_count = current_row.get("overalloc_count")
    total_execs_per_sec = _extract_load_profile_per_second(snapshot, "Executes")
    elapsed_seconds = _derive_elapsed_seconds(snapshot)
    if not isinstance(overalloc_count, (int, float)):
        return None
    if total_execs_per_sec is None or elapsed_seconds is None or total_execs_per_sec <= 0:
        return None

    total_execs = total_execs_per_sec * elapsed_seconds
    if total_execs <= 0:
        return None
    return float(overalloc_count) / total_execs


def _extract_temp_io_pressure(snapshot: ParseResult) -> float | None:
    elapsed_seconds = _derive_elapsed_seconds(snapshot)
    if elapsed_seconds is None or elapsed_seconds <= 0:
        return None

    for row in snapshot.tablespace_io_stats:
        if str(row.get("tablespace") or "").upper() != "TEMP":
            continue
        reads = row.get("reads")
        writes = row.get("writes")
        if not isinstance(reads, (int, float)) or not isinstance(writes, (int, float)):
            return None
        return (float(reads) + float(writes)) / elapsed_seconds

    return None


def _extract_log_file_sync_ms(snapshot: ParseResult) -> float | None:
    for wait_event in snapshot.wait_events:
        if str(wait_event.get("event_name") or "") != "log file sync":
            continue
        avg_wait_ms = wait_event.get("avg_wait_ms")
        if isinstance(avg_wait_ms, (int, float)) and avg_wait_ms >= 0:
            return float(avg_wait_ms)
    return None


def _bucket_ash_samples_by_minute(
    ash_samples: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in ash_samples:
        sample_time = sample.get("sample_time")
        if not isinstance(sample_time, str):
            continue
        try:
            sample_dt = datetime.strptime(sample_time, SNAPSHOT_TIME_FORMAT)
        except ValueError:
            continue
        buckets[sample_dt.strftime("%Y-%m-%d %H:%M")].append(sample)
    return buckets


def _ash_wait_class_pct_samples(
    buckets: dict[str, list[dict[str, Any]]],
    wait_class: str,
) -> list[float]:
    values: list[float] = []
    for samples in buckets.values():
        total = len(samples)
        if total <= 0:
            continue
        matching = sum(
            1 for sample in samples if str(sample.get("wait_class") or "") == wait_class
        )
        values.append((matching / total) * 100.0)
    return values


def _top_sql_rate_samples(
    top_sql: list[dict[str, Any]],
    elapsed_seconds: float | None,
    field_name: str,
) -> list[float]:
    if not elapsed_seconds or elapsed_seconds <= 0:
        return []

    values: list[float] = []
    for sql_record in top_sql:
        raw_value = sql_record.get(field_name)
        if not isinstance(raw_value, (int, float)) or raw_value < 0:
            continue
        values.append(float(raw_value) / elapsed_seconds)
    return values


def _top_sql_elapsed_norm_samples(top_sql: list[dict[str, Any]]) -> list[float]:
    # Best-effort single-report mode uses normalized top SQL rows from the
    # current snapshot instead of inventing interval history.
    values: list[float] = []
    for sql_record in top_sql:
        elapsed_per_exec_ms = sql_record.get("elapsed_per_exec_ms")
        if not isinstance(elapsed_per_exec_ms, (int, float)) or elapsed_per_exec_ms < 0:
            continue
        values.append(float(elapsed_per_exec_ms))
    return values


def _extract_datafile_rate(snapshot: ParseResult, field_name: str) -> float | None:
    elapsed_seconds = _derive_elapsed_seconds(snapshot)
    if elapsed_seconds is None or elapsed_seconds <= 0:
        return None

    values = [
        float(row.get(field_name))
        for row in snapshot.datafile_io_stats
        if isinstance(row.get(field_name), (int, float))
    ]
    if not values:
        return None
    return sum(values) / elapsed_seconds


def _datafile_rate_samples_per_row(
    datafile_io_stats: list[dict[str, Any]],
    elapsed_seconds: float | None,
    field_name: str,
) -> list[float]:
    if not elapsed_seconds or elapsed_seconds <= 0:
        return []

    values: list[float] = []
    for row in datafile_io_stats:
        raw_value = row.get(field_name)
        if not isinstance(raw_value, (int, float)) or raw_value < 0:
            continue
        values.append(float(raw_value) / elapsed_seconds)
    return values


def _extract_total_db_time_seconds(snapshot: ParseResult) -> float | None:
    db_time_per_second = _extract_load_profile_per_second(snapshot, "DB Time(s)")
    elapsed_seconds = _derive_elapsed_seconds(snapshot)
    if db_time_per_second is None or elapsed_seconds is None:
        return None
    return db_time_per_second * elapsed_seconds


def _extract_load_profile_per_second(snapshot: ParseResult, metric_name: str) -> float | None:
    for metric in snapshot.cpu_metrics:
        if str(metric.get("metric_group") or "") != "load_profile":
            continue
        if str(metric.get("metric_name") or "").strip() != metric_name:
            continue
        value = metric.get("per_second")
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    return None


def _pick_current_pga_advisory_row(
    rows: list[dict[str, Any]],
    current_target_mb: Any,
) -> dict[str, Any] | None:
    if not rows:
        return None

    if isinstance(current_target_mb, (int, float)):
        return min(
            rows,
            key=lambda row: abs(float(row.get("target_mb") or 0.0) - float(current_target_mb)),
        )

    return rows[0]


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


def _temp_io_pressure_samples(
    tablespace_io_stats: list[dict[str, Any]],
    elapsed_seconds: float | None,
) -> list[float]:
    if not elapsed_seconds or elapsed_seconds <= 0:
        return []

    values: list[float] = []
    for row in tablespace_io_stats:
        if str(row.get("tablespace") or "").upper() != "TEMP":
            continue
        reads = row.get("reads")
        writes = row.get("writes")
        if not isinstance(reads, (int, float)) or not isinstance(writes, (int, float)):
            continue
        values.append((float(reads) + float(writes)) / elapsed_seconds)
    return values


def _histogram_latency_samples(buckets: list[dict[str, Any]]) -> list[float]:
    if not buckets:
        return []

    total_waits = sum(
        int(bucket.get("wait_count") or 0)
        for bucket in buckets
        if isinstance(bucket.get("wait_count"), (int, float))
    )
    if total_waits <= 0:
        return []

    max_samples = 60
    values: list[float] = []
    for bucket in buckets:
        bucket_ms = bucket.get("bucket_ms")
        wait_count = bucket.get("wait_count")
        if not isinstance(bucket_ms, (int, float)) or not isinstance(wait_count, (int, float)):
            continue
        if bucket_ms < 0 or wait_count <= 0:
            continue
        sample_count = max(1, round((float(wait_count) / total_waits) * max_samples))
        values.extend([float(bucket_ms)] * sample_count)
    return values


def _finalize_snapshot_series(values: list[float | None]) -> list[float]:
    # Snapshot-series violins should represent one real normalized value
    # per AWR snapshot. If any snapshot is missing or invalid, keep the
    # series empty rather than synthesize or interpolate.
    if len(values) < MIN_VALID_SAMPLES:
        return []

    cleaned: list[float] = []
    for value in values:
        if value is None:
            return []
        if not isinstance(value, (int, float)) or not isfinite(float(value)) or float(value) < 0:
            return []
        cleaned.append(round(float(value), 6))

    return cleaned


def _finalize_best_effort_series(values: list[float]) -> list[float]:
    cleaned = [
        round(float(value), 6)
        for value in values
        if isinstance(value, (int, float)) and isfinite(float(value)) and float(value) >= 0
    ]
    if len(cleaned) < MIN_VALID_SAMPLES:
        return []
    return cleaned
