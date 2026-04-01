"""Deterministic issue detection from parsed AWR outputs."""

from __future__ import annotations

from typing import Any

from src.models.parse_result import ParseResult

KNOWN_CONCURRENCY_EVENTS = {
    "buffer busy waits",
    "cursor: pin s wait on x",
    "latch: cache buffers chains",
}

ISSUE_PRIORITY_ORDER = (
    "cpu_pressure",
    "sql_concentration",
    "io_pressure",
    "commit_pressure",
    "concurrency_pressure",
)


def detect_issues(parse_result: ParseResult) -> list[dict[str, Any]]:
    """Detect deterministic issue classifications from a parse result.

    Args:
        parse_result: Canonical parsed AWR result.

    Returns:
        A list of issue dictionaries. Missing inputs simply result in
        fewer detected issues rather than failure.
    """

    detected_issues = {
        "cpu_pressure": _detect_cpu_pressure(parse_result.wait_events),
        "sql_concentration": _detect_sql_concentration(parse_result.top_sql),
        "io_pressure": _detect_io_pressure(parse_result.wait_events),
        "commit_pressure": _detect_commit_pressure(parse_result.wait_events),
        "concurrency_pressure": _detect_concurrency_pressure(parse_result.wait_events),
    }

    return [
        detected_issues[issue_type]
        for issue_type in ISSUE_PRIORITY_ORDER
        if detected_issues[issue_type] is not None
    ]


def _detect_cpu_pressure(wait_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Detect CPU pressure from the DB CPU foreground wait row."""

    db_cpu_event = _find_wait_event(wait_events, event_name="DB CPU")
    if not db_cpu_event:
        return None

    pct_db_time = _to_float(db_cpu_event.get("pct_db_time"))
    severity = _severity_from_thresholds(
        pct_db_time, high_threshold=50.0, medium_threshold=30.0
    )
    if severity is None:
        return None

    return {
        "issue_type": "cpu_pressure",
        "severity": severity,
        "summary": f"CPU is the dominant bottleneck, consuming {pct_db_time:.1f}% of total DB time.",
        "evidence": {
            "event_name": db_cpu_event.get("event_name"),
            "pct_db_time": pct_db_time,
            "time_seconds": _to_float(db_cpu_event.get("time_seconds")),
        },
    }


def _detect_io_pressure(wait_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Detect I/O pressure from the top User I/O wait event."""

    user_io_events = [
        event
        for event in wait_events
        if _normalize_text(event.get("wait_class")) == "user i/o"
    ]
    if not user_io_events:
        return None

    top_user_io_event = max(
        user_io_events,
        key=lambda event: _to_float(event.get("pct_db_time")) or 0.0,
    )
    pct_db_time = _to_float(top_user_io_event.get("pct_db_time"))
    severity = _severity_from_thresholds(
        pct_db_time, high_threshold=10.0, medium_threshold=5.0
    )
    if severity is None:
        return None

    return {
        "issue_type": "io_pressure",
        "severity": severity,
        "summary": (
            "User I/O is a significant contributor, with "
            f"'{top_user_io_event.get('event_name')}' accounting for {pct_db_time:.1f}% "
            "of DB time."
        ),
        "evidence": {
            "event_name": top_user_io_event.get("event_name"),
            "wait_class": top_user_io_event.get("wait_class"),
            "pct_db_time": pct_db_time,
            "time_seconds": _to_float(top_user_io_event.get("time_seconds")),
        },
    }


def _detect_commit_pressure(wait_events: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Detect commit pressure from log file sync waits."""

    log_file_sync = _find_wait_event(wait_events, event_name="log file sync")
    if not log_file_sync:
        return None

    pct_db_time = _to_float(log_file_sync.get("pct_db_time"))
    severity = _severity_from_thresholds(
        pct_db_time, high_threshold=5.0, medium_threshold=2.0
    )
    if severity is None:
        return None

    return {
        "issue_type": "commit_pressure",
        "severity": severity,
        "summary": f"Commit latency is material, with log file sync consuming {pct_db_time:.1f}% of DB time.",
        "evidence": {
            "event_name": log_file_sync.get("event_name"),
            "pct_db_time": pct_db_time,
            "avg_wait_ms": _to_float(log_file_sync.get("avg_wait_ms")),
            "waits": log_file_sync.get("waits"),
        },
    }


def _detect_concurrency_pressure(
    wait_events: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Detect concurrency pressure from concurrency waits and known events."""

    matching_events = [event for event in wait_events if _is_concurrency_event(event)]
    if not matching_events:
        return None

    combined_pct_db_time = sum(
        _to_float(event.get("pct_db_time")) or 0.0 for event in matching_events
    )
    severity = _severity_from_thresholds(
        combined_pct_db_time,
        high_threshold=3.0,
        medium_threshold=1.0,
    )
    if severity is None:
        return None

    return {
        "issue_type": "concurrency_pressure",
        "severity": severity,
        "summary": (
            "Concurrency waits are present but secondary, accounting for "
            f"{combined_pct_db_time:.1f}% of DB time."
        ),
        "evidence": {
            "combined_pct_db_time": combined_pct_db_time,
            "events": [
                {
                    "event_name": event.get("event_name"),
                    "wait_class": event.get("wait_class"),
                    "pct_db_time": _to_float(event.get("pct_db_time")),
                }
                for event in matching_events
            ],
        },
    }


def _detect_sql_concentration(top_sql: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Detect whether elapsed time is concentrated in the top SQL statements."""

    ranked_sql = sorted(
        (
            sql_record
            for sql_record in top_sql
            if _to_float(sql_record.get("pct_total")) is not None
        ),
        key=lambda sql_record: _to_float(sql_record.get("pct_total")) or 0.0,
        reverse=True,
    )
    if not ranked_sql:
        return None

    top_two_sql = ranked_sql[:2]
    combined_pct_total = sum(
        _to_float(sql_record.get("pct_total")) or 0.0 for sql_record in top_two_sql
    )
    severity = _severity_from_thresholds(
        combined_pct_total,
        high_threshold=20.0,
        medium_threshold=10.0,
    )
    if severity is None:
        return None

    modules = _extract_modules(top_two_sql)
    shared_module = modules[0] if len(modules) == 1 else None
    if shared_module:
        summary = (
            f"SQL concentration is {severity}, with the top 2 SQL statements from "
            f"module '{shared_module}' accounting for {combined_pct_total:.1f}% "
            "of total elapsed SQL time."
        )
    else:
        summary = (
            f"SQL concentration is {severity}, with the top 2 SQL statements "
            f"accounting for {combined_pct_total:.1f}% of total elapsed SQL time."
        )

    return {
        "issue_type": "sql_concentration",
        "severity": severity,
        "summary": summary,
        "evidence": {
            "combined_pct_total": combined_pct_total,
            "sql_ids": [sql_record.get("sql_id") for sql_record in top_two_sql],
            "modules": modules,
            "top_sql": [
                {
                    "sql_id": sql_record.get("sql_id"),
                    "pct_total": _to_float(sql_record.get("pct_total")),
                    "elapsed_time_seconds": _to_float(
                        sql_record.get("elapsed_time_seconds")
                    ),
                    "module": sql_record.get("module"),
                }
                for sql_record in top_two_sql
            ],
        },
    }


def _extract_modules(top_sql: list[dict[str, Any]]) -> list[str]:
    """Return stable unique module names from the provided SQL records."""

    modules: list[str] = []
    for sql_record in top_sql:
        module = str(sql_record.get("module") or "").strip()
        if module and module not in modules:
            modules.append(module)

    return modules


def _find_wait_event(
    wait_events: list[dict[str, Any]],
    event_name: str,
) -> dict[str, Any] | None:
    """Return the first wait event matching the given name."""

    target_name = _normalize_text(event_name)
    for event in wait_events:
        if _normalize_text(event.get("event_name")) == target_name:
            return event

    return None


def _is_concurrency_event(event: dict[str, Any]) -> bool:
    """Return True when the wait event should count toward concurrency pressure."""

    wait_class = _normalize_text(event.get("wait_class"))
    event_name = _normalize_text(event.get("event_name"))
    return wait_class == "concurrency" or event_name in KNOWN_CONCURRENCY_EVENTS


def _severity_from_thresholds(
    value: float | None,
    high_threshold: float,
    medium_threshold: float,
) -> str | None:
    """Map a numeric value to a deterministic severity."""

    if value is None:
        return None

    if value >= high_threshold:
        return "high"

    if value >= medium_threshold:
        return "medium"

    return None


def _normalize_text(value: Any) -> str:
    """Normalize text values for deterministic matching."""

    if value is None:
        return ""

    return " ".join(str(value).strip().lower().split())


def _to_float(value: Any) -> float | None:
    """Convert a supported numeric value to float."""

    if isinstance(value, int | float):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None

    return None
