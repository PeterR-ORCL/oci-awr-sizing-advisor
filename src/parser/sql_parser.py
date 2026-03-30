"""Deterministic parsing utilities for Oracle AWR top SQL sections."""

from __future__ import annotations

import re
from typing import Any


ELAPSED_TIME_HEADER = "sql ordered by elapsed time"
SQL_TEXT_HEADER = "sql text"

ELAPSED_TIME_ROW_PATTERN = re.compile(
    r"^\s*(\w+)\s+([0-9,]+(?:\.\d+)?)\s+([0-9,]+)\s+([0-9,]+(?:\.\d+)?)\s+"
    r"([0-9,]+(?:\.\d+)?)\s+(.+?)\s*$"
)
SQL_ID_LINE_PATTERN = re.compile(r"^\s*SQL Id\s+(\w+)\s*$", flags=re.IGNORECASE)


def parse_sql_section(lines: list[str]) -> list[dict[str, Any]]:
    """Parse structured SQL records from an Oracle AWR top SQL section.

    The parser extracts only:

    - SQL ordered by Elapsed Time
    - SQL Text

    Other top SQL subsections are ignored for Day 2. SQL text is joined
    back to elapsed-time records by ``sql_id`` when available.

    Args:
        lines: Top SQL section lines from the loaded AWR report.

    Returns:
        A list of structured SQL records.
    """

    sql_records = _parse_elapsed_time_rows(lines)
    sql_text_by_id = _parse_sql_texts(lines)

    for record in sql_records:
        record["sql_text_snippet"] = sql_text_by_id.get(record["sql_id"])

    return sql_records


def _parse_elapsed_time_rows(lines: list[str]) -> list[dict[str, Any]]:
    """Parse rows from the SQL ordered by Elapsed Time subsection."""

    records: list[dict[str, Any]] = []
    in_elapsed_time_section = False
    seen_table_header = False

    for line in lines:
        normalized_line = _normalize_line(line)

        if not normalized_line:
            if in_elapsed_time_section and seen_table_header:
                continue
            continue

        if normalized_line == ELAPSED_TIME_HEADER:
            in_elapsed_time_section = True
            seen_table_header = False
            continue

        if not in_elapsed_time_section:
            continue

        if normalized_line != ELAPSED_TIME_HEADER and normalized_line.startswith("sql ordered by"):
            break

        if normalized_line == SQL_TEXT_HEADER:
            break

        if _is_divider_line(line) or _is_tilde_line(line):
            continue

        if normalized_line.startswith("sql id elapsed time"):
            seen_table_header = True
            continue

        if not seen_table_header:
            continue

        record = _parse_elapsed_time_row(line)
        if record is not None:
            records.append(record)

    return records


def _parse_elapsed_time_row(line: str) -> dict[str, Any] | None:
    """Parse a single SQL ordered by Elapsed Time table row."""

    match = ELAPSED_TIME_ROW_PATTERN.match(line)
    if not match:
        return None

    sql_id = match.group(1)
    elapsed_time_seconds = _to_float(match.group(2))
    executions = _to_int(match.group(3))
    elapsed_per_exec_ms = _to_float(match.group(4))
    pct_total = _to_float(match.group(5))
    module = match.group(6).strip()

    if not sql_id or not module:
        return None

    if (
        elapsed_time_seconds is None
        or executions is None
        or elapsed_per_exec_ms is None
        or pct_total is None
    ):
        return None

    return {
        "sql_id": sql_id,
        "elapsed_time_seconds": elapsed_time_seconds,
        "executions": executions,
        "elapsed_per_exec_ms": elapsed_per_exec_ms,
        "pct_total": pct_total,
        "module": module,
        "source_section": "top_sql",
    }


def _parse_sql_texts(lines: list[str]) -> dict[str, str]:
    """Parse SQL Text subsection entries keyed by SQL ID."""

    sql_text_by_id: dict[str, str] = {}
    in_sql_text_section = False
    current_sql_id: str | None = None
    current_text_lines: list[str] = []

    for line in lines:
        normalized_line = _normalize_line(line)

        if normalized_line == SQL_TEXT_HEADER:
            in_sql_text_section = True
            current_sql_id = None
            current_text_lines = []
            continue

        if not in_sql_text_section:
            continue

        if _is_tilde_line(line) or _is_divider_line(line):
            continue

        sql_id_match = SQL_ID_LINE_PATTERN.match(line)
        if sql_id_match:
            _store_sql_text(sql_text_by_id, current_sql_id, current_text_lines)
            current_sql_id = sql_id_match.group(1)
            current_text_lines = []
            continue

        if not line.strip():
            _store_sql_text(sql_text_by_id, current_sql_id, current_text_lines)
            current_sql_id = None
            current_text_lines = []
            continue

        if current_sql_id is not None:
            current_text_lines.append(line.strip())

    _store_sql_text(sql_text_by_id, current_sql_id, current_text_lines)
    return sql_text_by_id


def _store_sql_text(
    sql_text_by_id: dict[str, str],
    sql_id: str | None,
    text_lines: list[str],
) -> None:
    """Store a normalized SQL text snippet when both ID and text are present."""

    if sql_id is None or not text_lines:
        return

    sql_text_by_id[sql_id] = " ".join(part for part in text_lines if part)


def _is_divider_line(line: str) -> bool:
    """Return True when a line is only a visual divider."""

    stripped_line = line.strip()
    if not stripped_line:
        return False

    return bool(re.fullmatch(r"[-=\s]+", stripped_line))


def _is_tilde_line(line: str) -> bool:
    """Return True when a line is only a tilde subsection separator."""

    stripped_line = line.strip()
    if not stripped_line:
        return False

    return bool(re.fullmatch(r"[~\s]+", stripped_line))


def _normalize_line(line: str) -> str:
    """Normalize a line for deterministic subsection detection."""

    return " ".join(line.strip().lower().split())


def _to_float(value: str) -> float | None:
    """Convert a numeric string to float, tolerating commas."""

    try:
        return float(value.replace(",", ""))
    except (AttributeError, ValueError):
        return None


def _to_int(value: str) -> int | None:
    """Convert a numeric string to int, tolerating commas."""

    try:
        return int(value.replace(",", ""))
    except (AttributeError, ValueError):
        return None
