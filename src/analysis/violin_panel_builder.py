"""Build violin-panel metric arrays from AWR history or best-effort current-report samples."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from math import isfinite
from typing import Any

from src.analysis.derived_metric_extractor import (
    extract_derived_pressure_metrics,
    has_data,
)
from src.models.parse_result import ParseResult

MIN_VALID_SAMPLES = 2
SNAPSHOT_TIME_FORMAT = "%d-%b-%y %H:%M:%S"
SNAPSHOT_TIME_PATTERN = re.compile(r"(\d{2}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2})")
PERCENT_TOPOLOGY_KEYS = {
    "cluster_wait_pct_db_time",
    "gc_current_wait_pct_db_time",
    "gc_cr_wait_pct_db_time",
    "exa_cell_io_pct_db_time",
}

EMPTY_VIOLIN_PANEL = {
    "workload": {
        "cluster_cpu_pct_db_time": [],
        "cluster_execs_per_sec": [],
        "cluster_read_iops": [],
        "cluster_read_mb_per_sec": [],
        "cluster_write_iops": [],
        "cluster_write_mb_per_sec": [],
        "cluster_user_io_pct_db_time": [],
        "cluster_top_sql_concentration_pct": [],
        "cluster_pga_spill_pressure": [],
        "cluster_temp_io_pressure": [],
        "cluster_hard_parses_per_sec": [],
        "cluster_log_file_sync_ms": [],
    },
    "topology": {
        "cluster_wait_pct_db_time": [],
        "gc_current_wait_pct_db_time": [],
        "gc_cr_wait_pct_db_time": [],
        "transport_lag_sec": [],
        "apply_lag_sec": [],
    },
    "platform": {
        "cell_single_block_read_pct_db_time": [],
        "smart_scan_pct_db_time": [],
    },
    "rac_instance": {
        "per_instance_cpu_pct_db_time": [],
        "per_instance_cluster_wait_pct_db_time": [],
        "per_instance_gc_current_wait_pct_db_time": [],
        "per_instance_gc_cr_wait_pct_db_time": [],
    },
}


def build_violin_panel_data(
    parse_results: ParseResult | list[ParseResult],
) -> dict[str, dict[str, list[float]]]:
    """Build violin payload arrays from true history or best-effort single-report samples.

    Strict historical mode is used when multiple AWR snapshots are
    available. Best-effort single-report mode is used only when one AWR
    report exists and the report contains repeated, decomposable rows
    that form technically defensible samples. Violin plots require real
    distributions; scalar metrics must not be expanded into synthetic
    arrays. Small sample counts are preserved exactly as observed, and
    the renderer is responsible for displaying them honestly without
    synthetic expansion. No filler or interpolated values are generated.
    """

    snapshots = _normalize_snapshots(parse_results)
    if len(snapshots) < 2:
        return (
            _build_single_report_violin_panel(snapshots[0])
            if snapshots
            else dict(EMPTY_VIOLIN_PANEL)
        )

    snapshot_groups = _group_cluster_snapshots(snapshots)

    return {
        "workload": {
            "cluster_cpu_pct_db_time": _finalize_snapshot_series(
                [_extract_group_cpu_pct(group) for group in snapshot_groups]
            ),
            "cluster_execs_per_sec": _finalize_snapshot_series(
                [
                    _extract_group_load_profile_per_second(group, "Executes")
                    for group in snapshot_groups
                ]
            ),
            "cluster_read_iops": _finalize_snapshot_series(
                [_extract_group_read_iops(group) for group in snapshot_groups]
            ),
            "cluster_read_mb_per_sec": _finalize_snapshot_series(
                [_extract_group_read_mb_per_sec(group) for group in snapshot_groups]
            ),
            "cluster_write_iops": _finalize_snapshot_series(
                [_extract_group_write_iops(group) for group in snapshot_groups]
            ),
            "cluster_write_mb_per_sec": _finalize_snapshot_series(
                [_extract_group_write_mb_per_sec(group) for group in snapshot_groups]
            ),
            "cluster_user_io_pct_db_time": _finalize_snapshot_series(
                [_extract_group_user_io_pct(group) for group in snapshot_groups]
            ),
            "cluster_top_sql_concentration_pct": _finalize_snapshot_series(
                [
                    _extract_group_top_sql_concentration_pct(group)
                    for group in snapshot_groups
                ]
            ),
            "cluster_pga_spill_pressure": _finalize_snapshot_series(
                [
                    _extract_group_average_metric(group, _extract_pga_spill_pressure)
                    for group in snapshot_groups
                ],
                allow_sparse=True,
            ),
            "cluster_temp_io_pressure": _finalize_snapshot_series(
                [
                    _extract_group_average_metric(group, _extract_temp_io_pressure)
                    for group in snapshot_groups
                ],
                allow_sparse=True,
            ),
            "cluster_hard_parses_per_sec": _finalize_snapshot_series(
                [
                    _extract_group_sum_metric(group, _extract_hard_parses_per_sec)
                    for group in snapshot_groups
                ],
                allow_sparse=True,
            ),
            "cluster_log_file_sync_ms": _finalize_snapshot_series(
                [
                    _extract_group_average_metric(group, _extract_log_file_sync_ms)
                    for group in snapshot_groups
                ]
            ),
        },
        "topology": {
            "cluster_wait_pct_db_time": _finalize_snapshot_series(
                [_extract_group_cluster_wait_pct(group) for group in snapshot_groups],
                allow_sparse=True,
            ),
            "gc_current_wait_pct_db_time": _finalize_snapshot_series(
                [_extract_group_gc_current_wait_pct(group) for group in snapshot_groups],
                allow_sparse=True,
            ),
            "gc_cr_wait_pct_db_time": _finalize_snapshot_series(
                [_extract_group_gc_cr_wait_pct(group) for group in snapshot_groups],
                allow_sparse=True,
            ),
            "transport_lag_sec": _finalize_snapshot_series(
                [
                    _extract_group_topology_max(group, "transport_lag_sec")
                    for group in snapshot_groups
                ],
                allow_sparse=True,
            ),
            "apply_lag_sec": _finalize_snapshot_series(
                [
                    _extract_group_topology_max(group, "apply_lag_sec")
                    for group in snapshot_groups
                ],
                allow_sparse=True,
            ),
        },
        "platform": {
            "cell_single_block_read_pct_db_time": _finalize_snapshot_series(
                [
                    _extract_group_wait_event_pct(
                        group,
                        ("cell single block physical read",),
                    )
                    for group in snapshot_groups
                ],
                allow_sparse=True,
            ),
            "smart_scan_pct_db_time": _finalize_snapshot_series(
                [
                    _extract_group_wait_event_pct(
                        group,
                        ("cell smart table scan",),
                    )
                    for group in snapshot_groups
                ],
                allow_sparse=True,
            ),
        },
        "rac_instance": _build_per_instance_rac_panel(snapshots),
    }


def _build_single_report_violin_panel(
    snapshot: ParseResult,
) -> dict[str, dict[str, list[float]]]:
    """Build best-effort distributions from repeated rows inside one AWR report."""

    elapsed_seconds = _derive_elapsed_seconds(snapshot)
    ash_buckets = _bucket_ash_samples_by_minute(snapshot.ash_samples or [])

    return {
        "workload": {
            "cluster_cpu_pct_db_time": _finalize_best_effort_series(
                _ash_wait_class_pct_samples(ash_buckets, "CPU")
            ),
            "cluster_execs_per_sec": _finalize_best_effort_series(
                _top_sql_rate_samples(snapshot.top_sql, elapsed_seconds, "executions")
            ),
            "cluster_read_iops": _finalize_best_effort_series(
                _datafile_rate_samples_per_row(
                    snapshot.datafile_io_stats, elapsed_seconds, "reads"
                )
            ),
            "cluster_read_mb_per_sec": _finalize_best_effort_series(
                _datafile_rate_samples_per_row(
                    snapshot.datafile_io_stats, elapsed_seconds, "read_mb"
                )
            ),
            "cluster_write_iops": _finalize_best_effort_series(
                _datafile_rate_samples_per_row(
                    snapshot.datafile_io_stats, elapsed_seconds, "writes"
                )
            ),
            "cluster_write_mb_per_sec": _finalize_best_effort_series(
                _datafile_rate_samples_per_row(
                    snapshot.datafile_io_stats, elapsed_seconds, "write_mb"
                )
            ),
            "cluster_user_io_pct_db_time": _finalize_best_effort_series(
                _ash_wait_class_pct_samples(ash_buckets, "User I/O")
            ),
            "cluster_top_sql_concentration_pct": _finalize_best_effort_series(
                _top_sql_concentration_samples(snapshot.top_sql)
            ),
            "cluster_pga_spill_pressure": [],
            "cluster_temp_io_pressure": _finalize_best_effort_series(
                _temp_io_pressure_samples(snapshot, elapsed_seconds)
            ),
            "cluster_hard_parses_per_sec": [],
            "cluster_log_file_sync_ms": _finalize_best_effort_series(
                _histogram_latency_samples(
                    snapshot.event_histograms.get("log file sync") or []
                )
            ),
        },
        "topology": {},
        "platform": {},
        "rac_instance": {},
    }


def _normalize_snapshots(
    parse_results: ParseResult | list[ParseResult],
) -> list[ParseResult]:
    if isinstance(parse_results, ParseResult):
        snapshots = [parse_results]
    else:
        snapshots = [
            snapshot for snapshot in parse_results if isinstance(snapshot, ParseResult)
        ]

    return sorted(
        snapshots,
        key=lambda snapshot: _extract_snapshot_datetime(
            snapshot.run_metadata.begin_snapshot_time
        )
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
    return extract_derived_pressure_metrics(snapshot).get("pga_spill_pressure")


def _extract_temp_io_pressure(snapshot: ParseResult) -> float | None:
    metric = extract_derived_pressure_metrics(snapshot).get("temp_io_pressure")
    if has_data(metric):
        return metric

    elapsed_seconds = _derive_elapsed_seconds(snapshot)
    if elapsed_seconds is None or elapsed_seconds <= 0:
        return None

    for row in snapshot.tablespace_io_stats:
        if str(row.get("tablespace") or "").upper() != "TEMP":
            continue
        row_reads = row.get("reads")
        row_writes = row.get("writes")
        if not isinstance(row_reads, (int, float)) or not isinstance(
            row_writes, (int, float)
        ):
            return None
        return (float(row_reads) + float(row_writes)) / elapsed_seconds

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


def _top_sql_concentration_samples(top_sql: list[dict[str, Any]]) -> list[float]:
    values: list[float] = []
    for sql_record in top_sql:
        pct_total = sql_record.get("pct_total")
        if not isinstance(pct_total, (int, float)) or pct_total < 0:
            continue
        values.append(float(pct_total))
    return values


def _extract_instance_activity_total(
    snapshot: ParseResult, statistic_name: str
) -> float | None:
    for row in snapshot.instance_activity_stats:
        if (
            str(row.get("statistic_name") or "").strip().lower()
            != statistic_name.lower()
        ):
            continue
        value = row.get("total")
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    return None


def _extract_instance_activity_per_second(
    snapshot: ParseResult,
    statistic_name: str,
) -> float | None:
    for row in snapshot.instance_activity_stats:
        if (
            str(row.get("statistic_name") or "").strip().lower()
            != statistic_name.lower()
        ):
            continue
        value = row.get("per_second")
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    return None


def _coerce_non_negative(value: Any) -> float | None:
    if isinstance(value, (int, float)) and value >= 0:
        return float(value)
    return None


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


def _extract_load_profile_per_second(
    snapshot: ParseResult, metric_name: str
) -> float | None:
    for metric in snapshot.cpu_metrics:
        if str(metric.get("metric_group") or "") != "load_profile":
            continue
        if str(metric.get("metric_name") or "").strip() != metric_name:
            continue
        value = metric.get("per_second")
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    return None


def _extract_hard_parses_per_sec(snapshot: ParseResult) -> float | None:
    metric = extract_derived_pressure_metrics(snapshot).get("hard_parses_per_sec")
    if has_data(metric):
        return metric
    return None


def _group_cluster_snapshots(
    snapshots: list[ParseResult],
) -> list[list[ParseResult]]:
    grouped: dict[tuple[Any, ...], list[ParseResult]] = defaultdict(list)
    for snapshot in snapshots:
        begin = _extract_snapshot_datetime(snapshot.run_metadata.begin_snapshot_time)
        end = _extract_snapshot_datetime(snapshot.run_metadata.end_snapshot_time)
        if begin is None or end is None:
            key = (
                snapshot.run_metadata.source_file_name,
                snapshot.run_metadata.instance_name,
            )
        else:
            key = (
                snapshot.run_metadata.database_name,
                snapshot.run_metadata.db_id,
                begin,
                end,
            )
        grouped[key].append(snapshot)

    return sorted(
        grouped.values(),
        key=lambda group: _extract_snapshot_datetime(
            group[0].run_metadata.begin_snapshot_time
        )
        or datetime.max,
    )


def _extract_group_load_profile_per_second(
    snapshot_group: list[ParseResult],
    metric_name: str,
) -> float | None:
    values = [
        _extract_load_profile_per_second(snapshot, metric_name)
        for snapshot in snapshot_group
    ]
    return _sum_numeric(values)


def _extract_group_total_db_time_seconds(
    snapshot_group: list[ParseResult],
) -> float | None:
    values = [
        _extract_total_db_time_seconds(snapshot) for snapshot in snapshot_group
    ]
    return _sum_numeric(values)


def _extract_group_cpu_pct(snapshot_group: list[ParseResult]) -> float | None:
    total_db_cpu = _extract_group_load_profile_per_second(snapshot_group, "DB CPU(s)")
    total_db_time = _extract_group_load_profile_per_second(
        snapshot_group,
        "DB Time(s)",
    )
    if total_db_cpu is None or total_db_time is None or total_db_time <= 0:
        return None
    return (total_db_cpu / total_db_time) * 100.0


def _extract_group_read_iops(snapshot_group: list[ParseResult]) -> float | None:
    values = [_extract_read_iops(snapshot) for snapshot in snapshot_group]
    return _sum_numeric(values)


def _extract_group_read_mb_per_sec(
    snapshot_group: list[ParseResult],
) -> float | None:
    values = [_extract_read_mb_per_sec(snapshot) for snapshot in snapshot_group]
    return _sum_numeric(values)


def _extract_group_write_iops(snapshot_group: list[ParseResult]) -> float | None:
    values = [_extract_write_iops(snapshot) for snapshot in snapshot_group]
    return _sum_numeric(values)


def _extract_group_write_mb_per_sec(
    snapshot_group: list[ParseResult],
) -> float | None:
    values = [_extract_write_mb_per_sec(snapshot) for snapshot in snapshot_group]
    return _sum_numeric(values)


def _extract_group_user_io_pct(snapshot_group: list[ParseResult]) -> float | None:
    return _extract_group_wait_class_pct(snapshot_group, "User I/O")


def _extract_group_wait_class_pct(
    snapshot_group: list[ParseResult],
    wait_class: str,
) -> float | None:
    total_db_time = _extract_group_total_db_time_seconds(snapshot_group)
    if total_db_time is None or total_db_time <= 0:
        return None

    total_wait_seconds = 0.0
    found = False
    for snapshot in snapshot_group:
        for wait_event in snapshot.wait_events:
            if str(wait_event.get("wait_class") or "") != wait_class:
                continue
            time_seconds = wait_event.get("time_seconds")
            if isinstance(time_seconds, (int, float)) and time_seconds >= 0:
                total_wait_seconds += float(time_seconds)
                found = True

    if not found:
        return None
    return (total_wait_seconds / total_db_time) * 100.0


def _extract_group_wait_event_pct(
    snapshot_group: list[ParseResult],
    event_patterns: tuple[str, ...],
) -> float | None:
    total_db_time = _extract_group_total_db_time_seconds(snapshot_group)
    if total_db_time is None or total_db_time <= 0:
        return None

    total_wait_seconds = 0.0
    found = False
    for snapshot in snapshot_group:
        for wait_event in snapshot.wait_events:
            event_name = str(wait_event.get("event_name") or "").lower()
            if not any(pattern.lower() in event_name for pattern in event_patterns):
                continue
            time_seconds = wait_event.get("time_seconds")
            if isinstance(time_seconds, (int, float)) and time_seconds >= 0:
                total_wait_seconds += float(time_seconds)
                found = True

    if not found:
        return None
    return (total_wait_seconds / total_db_time) * 100.0


def _extract_group_top_sql_concentration_pct(
    snapshot_group: list[ParseResult],
) -> float | None:
    sql_rows = [
        sql_record
        for snapshot in snapshot_group
        for sql_record in snapshot.top_sql
        if isinstance(sql_record, dict)
    ]
    if not sql_rows:
        return None

    pct_rows = [
        float(sql_record.get("pct_total"))
        for sql_record in sql_rows
        if isinstance(sql_record.get("pct_total"), (int, float))
    ]
    if pct_rows:
        return min(sum(pct_rows[:3]), 100.0)

    elapsed_rows = [
        float(sql_record.get("elapsed_time_seconds"))
        for sql_record in sql_rows
        if isinstance(sql_record.get("elapsed_time_seconds"), (int, float))
    ]
    if not elapsed_rows:
        return None
    total_elapsed = sum(elapsed_rows)
    if total_elapsed <= 0:
        return None
    return (sum(elapsed_rows[:3]) / total_elapsed) * 100.0


def _extract_group_cluster_wait_pct(
    snapshot_group: list[ParseResult],
) -> float | None:
    topology_average = _extract_group_average_topology_pct(
        snapshot_group,
        "cluster_wait_pct_db_time",
    )
    if topology_average is not None:
        return topology_average
    return _extract_group_wait_class_pct(snapshot_group, "Cluster")


def _extract_group_gc_current_wait_pct(
    snapshot_group: list[ParseResult],
) -> float | None:
    topology_average = _extract_group_average_topology_pct(
        snapshot_group,
        "gc_current_wait_pct_db_time",
    )
    if topology_average is not None:
        return topology_average
    return _extract_group_wait_event_pct(snapshot_group, ("gc current",))


def _extract_group_gc_cr_wait_pct(
    snapshot_group: list[ParseResult],
) -> float | None:
    topology_average = _extract_group_average_topology_pct(
        snapshot_group,
        "gc_cr_wait_pct_db_time",
    )
    if topology_average is not None:
        return topology_average
    return _extract_group_wait_event_pct(snapshot_group, ("gc cr",))


def _extract_group_average_topology_pct(
    snapshot_group: list[ParseResult],
    key: str,
) -> float | None:
    values = [
        _extract_snapshot_topology_float(snapshot, key) for snapshot in snapshot_group
    ]
    return _average_numeric(values)


def _extract_group_topology_max(
    snapshot_group: list[ParseResult],
    key: str,
) -> float | None:
    values = [
        _extract_snapshot_topology_float(snapshot, key) for snapshot in snapshot_group
    ]
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return max(numeric_values)


def _extract_group_sum_metric(
    snapshot_group: list[ParseResult],
    extractor: Any,
) -> float | None:
    values = [extractor(snapshot) for snapshot in snapshot_group]
    return _sum_numeric(values)


def _extract_group_average_metric(
    snapshot_group: list[ParseResult],
    extractor: Any,
) -> float | None:
    values = [extractor(snapshot) for snapshot in snapshot_group]
    return _average_numeric(values)


def _extract_snapshot_topology_float(
    snapshot: ParseResult,
    key: str,
) -> float | None:
    topology_signals = getattr(snapshot, "topology_signals", None) or {}
    value = topology_signals.get(key)
    if isinstance(value, (int, float)) and value >= 0:
        numeric_value = float(value)
        if key in PERCENT_TOPOLOGY_KEYS and 0.0 <= numeric_value <= 1.0:
            return numeric_value * 100.0
        return numeric_value
    return None


def _build_per_instance_rac_panel(
    snapshots: list[ParseResult],
) -> dict[str, list[float]]:
    distinct_instances = {
        str(snapshot.run_metadata.instance_name or "").strip()
        for snapshot in snapshots
        if str(snapshot.run_metadata.instance_name or "").strip()
    }
    rac_detected = any(
        bool((getattr(snapshot, "topology_signals", None) or {}).get("is_rac"))
        for snapshot in snapshots
    )
    if not rac_detected or len(distinct_instances) < 2:
        return {
            "per_instance_cpu_pct_db_time": [],
            "per_instance_cluster_wait_pct_db_time": [],
            "per_instance_gc_current_wait_pct_db_time": [],
            "per_instance_gc_cr_wait_pct_db_time": [],
        }

    return {
        "per_instance_cpu_pct_db_time": _finalize_snapshot_series(
            [_extract_cpu_pct(snapshot) for snapshot in snapshots],
            allow_sparse=True,
        ),
        "per_instance_cluster_wait_pct_db_time": _finalize_snapshot_series(
            [
                _extract_snapshot_topology_float(snapshot, "cluster_wait_pct_db_time")
                for snapshot in snapshots
            ],
            allow_sparse=True,
        ),
        "per_instance_gc_current_wait_pct_db_time": _finalize_snapshot_series(
            [
                _extract_snapshot_topology_float(
                    snapshot,
                    "gc_current_wait_pct_db_time",
                )
                for snapshot in snapshots
            ],
            allow_sparse=True,
        ),
        "per_instance_gc_cr_wait_pct_db_time": _finalize_snapshot_series(
            [
                _extract_snapshot_topology_float(
                    snapshot,
                    "gc_cr_wait_pct_db_time",
                )
                for snapshot in snapshots
            ],
            allow_sparse=True,
        ),
    }


def _sum_numeric(values: list[float | None]) -> float | None:
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return sum(numeric_values)


def _average_numeric(values: list[float | None]) -> float | None:
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return sum(numeric_values) / len(numeric_values)


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
    snapshot: ParseResult,
    elapsed_seconds: float | None,
) -> list[float]:
    if not elapsed_seconds or elapsed_seconds <= 0:
        return []

    direct_reads = _extract_instance_activity_total(
        snapshot,
        "physical reads direct temporary tablespace",
    )
    direct_writes = _extract_instance_activity_total(
        snapshot,
        "physical writes direct temporary tablespace",
    )
    if direct_reads is not None and direct_writes is not None:
        return [(direct_reads + direct_writes) / elapsed_seconds]

    values: list[float] = []
    for row in snapshot.tablespace_io_stats:
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
        if not isinstance(bucket_ms, (int, float)) or not isinstance(
            wait_count, (int, float)
        ):
            continue
        if bucket_ms < 0 or wait_count <= 0:
            continue
        sample_count = max(1, round((float(wait_count) / total_waits) * max_samples))
        values.extend([float(bucket_ms)] * sample_count)
    return values


def _finalize_snapshot_series(
    values: list[float | None],
    allow_sparse: bool = False,
) -> list[float]:
    # Snapshot-series violins should represent one real normalized value
    # per AWR snapshot. If any snapshot is missing or invalid, keep the
    # series empty rather than synthesize or interpolate.
    if len(values) < MIN_VALID_SAMPLES:
        return []

    cleaned: list[float] = []
    for value in values:
        if value is None:
            if allow_sparse:
                continue
            return []
        if (
            not isinstance(value, (int, float))
            or not isfinite(float(value))
            or float(value) < 0
        ):
            if allow_sparse:
                continue
            return []
        cleaned.append(round(float(value), 6))

    if len(cleaned) < MIN_VALID_SAMPLES:
        return []
    return cleaned


def _finalize_best_effort_series(values: list[float]) -> list[float]:
    cleaned = [
        round(float(value), 6)
        for value in values
        if isinstance(value, (int, float))
        and isfinite(float(value))
        and float(value) >= 0
    ]
    if len(cleaned) < MIN_VALID_SAMPLES:
        return []
    return cleaned
