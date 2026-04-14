"""Utilities for extracting run-level metadata from Oracle AWR reports.

This module provides a small, deterministic metadata parser for the
Day 1 parser foundation. It performs simple line and regex based
extraction against the loaded AWR report text and returns a canonical
metadata dictionary plus warnings for fields that were not confidently
found.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
from typing import TypeAlias, TypedDict

from src.parser.awr_section_locator import AwrSectionLocation


class AwrMetadata(TypedDict):
    """Canonical run-level metadata extracted from an AWR report."""

    source_file_name: str
    source_file_path: str
    parse_timestamp: str
    database_name: str | None
    db_id: str | None
    instance_name: str | None
    instance_number: str | None
    host_name: str | None
    platform: str | None
    db_version: str | None
    cpu_count: int | None
    core_count: int | None
    socket_count: int | None
    memory_gb: float | None
    snap_id_begin: int | None
    snap_id_end: int | None
    begin_snapshot_time: str | None
    end_snapshot_time: str | None


ReportHeaderBounds: TypeAlias = AwrSectionLocation


def parse_awr_metadata(
    file_path: str,
    file_name: str,
    lines: list[str],
    report_header: ReportHeaderBounds | None = None,
) -> tuple[AwrMetadata, list[str]]:
    """Extract run-level metadata from loaded Oracle AWR report lines.

    The parser prefers a provided report header slice when available,
    otherwise it inspects the first portion of the file. Missing fields
    do not cause failure; they are returned as ``None`` and reported in
    the warnings list.

    Args:
        file_path: Original source file path.
        file_name: Original source file name.
        lines: Loaded AWR report lines.
        report_header: Optional 1-based inclusive report header bounds.

    Returns:
        A tuple containing the canonical metadata dictionary and a list
        of warnings describing fields that were not confidently found.
    """

    metadata: AwrMetadata = {
        "source_file_name": file_name,
        "source_file_path": str(Path(file_path)),
        "parse_timestamp": datetime.now(timezone.utc).isoformat(),
        "database_name": None,
        "db_id": None,
        "instance_name": None,
        "instance_number": None,
        "host_name": None,
        "platform": None,
        "db_version": None,
        "cpu_count": None,
        "core_count": None,
        "socket_count": None,
        "memory_gb": None,
        "snap_id_begin": None,
        "snap_id_end": None,
        "begin_snapshot_time": None,
        "end_snapshot_time": None,
    }

    candidate_lines = _select_candidate_lines(lines, report_header)
    candidate_text = "\n".join(candidate_lines)

    identity_values = _extract_identity_table_fields(candidate_lines)
    if identity_values:
        metadata["database_name"] = identity_values[0]
        metadata["db_id"] = identity_values[1]
        metadata["instance_name"] = identity_values[2]
        metadata["instance_number"] = identity_values[3]
        metadata["db_version"] = identity_values[4]

    host_platform_values = _extract_host_platform_fields(candidate_lines)
    if host_platform_values:
        metadata["host_name"] = host_platform_values[0]
        metadata["platform"] = host_platform_values[1]

    resource_values = _extract_system_resource_fields(candidate_lines)
    if resource_values:
        metadata["cpu_count"] = resource_values[0]
        metadata["core_count"] = resource_values[1]
        metadata["socket_count"] = resource_values[2]
        metadata["memory_gb"] = resource_values[3]

    metadata["database_name"] = metadata["database_name"] or _search_patterns(
        candidate_text,
        (
            r"database name\s*[:=]\s*(.+)",
            r"db name\s*[:=]\s*(.+)",
        ),
    )
    metadata["db_id"] = metadata["db_id"] or _search_patterns(
        candidate_text,
        (
            r"db id\s*[:=]\s*(\d+)",
            r"dbid\s*[:=]\s*(\d+)",
        ),
    )
    metadata["instance_name"] = metadata["instance_name"] or _search_patterns(
        candidate_text,
        (
            r"instance name\s*[:=]\s*(.+)",
            r"instance\s*[:=]\s*(.+)",
        ),
    )
    metadata["instance_number"] = metadata["instance_number"] or _search_patterns(
        candidate_text,
        (
            r"instance number\s*[:=]\s*(\d+)",
            r"inst num\s*[:=]\s*(\d+)",
        ),
    )
    metadata["host_name"] = metadata["host_name"] or _search_patterns(
        candidate_text,
        (
            r"^host name\s*[:=]\s*(\S+)\s*$",
            r"^host\s*[:=]\s*(\S+)\s*$",
        ),
    )
    metadata["platform"] = metadata["platform"] or _search_patterns(
        candidate_text,
        (r"^platform\s*[:=]\s*([^\n]+)",),
    )
    metadata["db_version"] = metadata["db_version"] or _search_patterns(
        candidate_text,
        (
            r"^\s*version\s*[:=]?\s*([0-9][0-9A-Za-z\.\-_]+)",
            r"release\s+([0-9][0-9A-Za-z\.\-_]+)",
        ),
    )
    metadata["snap_id_begin"] = _search_int_patterns(
        candidate_text,
        (
            r"begin snap id\s*[:=]?\s*(\d+)",
            r"begin snapshot id\s*[:=]?\s*(\d+)",
            r"begin snap:\s*(\d+)",
        ),
    )
    metadata["snap_id_end"] = _search_int_patterns(
        candidate_text,
        (
            r"end snap id\s*[:=]?\s*(\d+)",
            r"end snapshot id\s*[:=]?\s*(\d+)",
            r"end snap:\s*(\d+)",
        ),
    )
    metadata["begin_snapshot_time"] = _extract_snapshot_time(
        candidate_text,
        label="begin",
    )
    metadata["end_snapshot_time"] = _extract_snapshot_time(
        candidate_text,
        label="end",
    )

    warnings = _build_warnings(metadata)
    return metadata, warnings


def _select_candidate_lines(
    lines: list[str],
    report_header: ReportHeaderBounds | None,
) -> list[str]:
    """Select the most likely lines to contain report-level metadata."""

    if report_header:
        start_line = max(report_header.get("start_line", 1), 1)
        end_line = min(report_header.get("end_line", len(lines)), len(lines))
        if start_line <= end_line:
            return lines[start_line - 1 : end_line]

    return lines[:200]


def _extract_table_row(
    lines: list[str],
    required_headers: tuple[str, ...],
) -> list[str] | None:
    """Extract values from a simple AWR-style header/value table pair."""

    for index, line in enumerate(lines):
        normalized_line = _normalize_line(line)
        if not all(header in normalized_line for header in required_headers):
            continue

        for value_line in lines[index + 1 :]:
            if not value_line.strip():
                continue

            if _is_separator_line(value_line):
                continue

            values = [part.strip() for part in re.split(r"\s{2,}", value_line.strip())]
            meaningful_values = [
                value for value in values if value and not _is_separator_line(value)
            ]
            if meaningful_values:
                return meaningful_values

    return None


def _extract_identity_table_fields(
    lines: list[str],
) -> tuple[str, str, str, str, str | None] | None:
    """Extract the main AWR identity row including release/version when present."""

    header_pattern = re.compile(
        r"\bDB\s+Name\b.*\bDB\s+Id\b.*\bInstance\b.*\bInst\s+Num\b",
        flags=re.IGNORECASE,
    )
    value_pattern = re.compile(
        r"^\s*(\S+)\s+(\d+)\s+(\S+)\s+(\d+)\s+(.+?)\s+([0-9][0-9A-Za-z\.\-_]+)(?:\s+\S+)?\s*$",
    )
    fallback_pattern = re.compile(
        r"^\s*(\S+)\s+(\d+)\s+(\S+)\s+(\d+)\b",
    )

    for index, header_line in enumerate(lines):
        if not header_pattern.search(header_line):
            continue

        value_line = _find_value_line(lines[index + 1 :])
        if value_line is None:
            return None

        match = value_pattern.match(value_line)
        if match:
            return (
                match.group(1),
                match.group(2),
                match.group(3),
                match.group(4),
                match.group(6),
            )

        fallback_match = fallback_pattern.match(value_line)
        if fallback_match:
            return (
                fallback_match.group(1),
                fallback_match.group(2),
                fallback_match.group(3),
                fallback_match.group(4),
                None,
            )

    return None


def _extract_host_platform_fields(
    lines: list[str],
) -> tuple[str, str] | None:
    """Extract host and platform from the AWR host/platform header row."""

    for index, line in enumerate(lines):
        normalized_line = _normalize_line(line)
        if "host name" not in normalized_line or "platform" not in normalized_line:
            continue

        value_line = _find_value_line(lines[index + 1 :])
        if value_line is None:
            return None

        match = re.match(r"^\s*(\S+)\s+(.+?)\s*$", value_line)
        if not match:
            return None

        host_name = match.group(1).strip()
        platform = match.group(2).strip()
        if not host_name or not platform:
            return None
        return host_name, platform

    return None


def _find_value_line(lines: list[str]) -> str | None:
    """Return the first nonblank, non-separator value line."""

    for line in lines:
        if not line.strip():
            continue

        if _is_separator_line(line):
            continue

        return line

    return None


def _extract_system_resource_fields(
    lines: list[str],
) -> tuple[int, int, int, float] | None:
    """Extract CPU/core/socket/memory values from the AWR header table."""

    for index, line in enumerate(lines):
        normalized_line = _normalize_line(line)
        if not all(
            token in normalized_line
            for token in ("cpu", "cores", "sockets", "memory")
        ):
            continue

        value_line = _find_value_line(lines[index + 1 :])
        if value_line is None:
            return None

        values = [
            part.strip()
            for part in re.split(r"\s{2,}", value_line.strip())
            if part.strip()
        ]
        if len(values) < 4:
            return None

        cpu_count = _to_int(values[0])
        core_count = _to_int(values[1])
        socket_count = _to_int(values[2])
        memory_gb = _to_float(values[3])
        if (
            cpu_count is None
            or core_count is None
            or socket_count is None
            or memory_gb is None
        ):
            return None
        return cpu_count, core_count, socket_count, memory_gb

    return None


def _extract_snapshot_time(text: str, label: str) -> str | None:
    """Extract a begin or end snapshot time using simple text patterns."""

    patterns = (
        rf"{label}\s+snap(?:shot)?\s*[:=]\s*(.+)",
        rf"{label}\s+snapshot\s+time\s*[:=]\s*(.+)",
    )
    return _search_patterns(text, patterns)


def _search_patterns(text: str, patterns: tuple[str, ...]) -> str | None:
    """Return the first regex capture group found from the given patterns."""

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if not match:
            continue

        value = match.group(1).strip()
        if value:
            return value

    return None


def _search_int_patterns(text: str, patterns: tuple[str, ...]) -> int | None:
    """Return the first integer capture group found from the given patterns."""

    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if not match:
            continue

        value = _to_int(match.group(1).strip())
        if value is not None:
            return value

    return None


def _build_warnings(metadata: AwrMetadata) -> list[str]:
    """Create warnings for metadata fields that were not confidently found."""

    warnings: list[str] = []

    for field_name in (
        "database_name",
        "db_id",
        "instance_name",
        "instance_number",
        "host_name",
        "platform",
        "db_version",
        "snap_id_begin",
        "snap_id_end",
        "begin_snapshot_time",
        "end_snapshot_time",
    ):
        if metadata[field_name] is None:
            warnings.append(f"Metadata field not found: {field_name}")

    return warnings


def _is_separator_line(line: str) -> bool:
    """Return True when a line is only a visual divider."""

    stripped_line = line.strip()
    if not stripped_line:
        return False

    return bool(re.fullmatch(r"[-=\s]+", stripped_line))


def _normalize_line(line: str) -> str:
    """Normalize a line for case-insensitive header detection."""

    return " ".join(line.strip().lower().split())


def _to_int(value: str) -> int | None:
    try:
        return int(value.replace(",", ""))
    except (AttributeError, ValueError):
        return None


def _to_float(value: str) -> float | None:
    try:
        return float(value.replace(",", ""))
    except (AttributeError, ValueError):
        return None


DATA_GUARD_LAG_PATTERNS = {
    "transport_lag_sec": (
        re.compile(
            r"transport lag\s*[:=]?\s*([0-9:\s]+(?:day[s]?\s+[0-9:]+)?)",
            re.IGNORECASE,
        ),
    ),
    "apply_lag_sec": (
        re.compile(
            r"apply lag\s*[:=]?\s*([0-9:\s]+(?:day[s]?\s+[0-9:]+)?)",
            re.IGNORECASE,
        ),
    ),
}


def _extract_snapshot_time(text: str, label: str) -> str | None:
    """Extract a begin or end snapshot time using simple text patterns."""

    patterns = (
        rf"{label}\s+snap(?:shot)?\s*[:=]\s*(.+)",
        rf"{label}\s+snapshot\s+time\s*[:=]\s*(.+)",
    )
    raw_value = _search_patterns(text, patterns)
    return _normalize_snapshot_time(raw_value)


def _normalize_snapshot_time(value: str | None) -> str | None:
    """Normalize supported snapshot timestamp formats to ISO-like text."""

    if not value:
        return None

    cleaned_value = value.strip()
    candidates = [cleaned_value]
    oracle_match = re.search(
        r"(\d{2}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2})",
        cleaned_value,
    )
    if oracle_match:
        candidates.append(oracle_match.group(1))

    for candidate in candidates:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%d-%b-%y %H:%M:%S"):
            try:
                parsed = datetime.strptime(candidate, fmt)
            except ValueError:
                continue
            return parsed.strftime("%Y-%m-%d %H:%M:%S")

    return None


def extract_dataguard_lag_metrics(lines: list[str]) -> dict[str, float | None]:
    """Extract deterministic Data Guard lag metrics from report text."""

    text = "\n".join(lines)
    return {
        "transport_lag_sec": _extract_duration_metric(
            text,
            DATA_GUARD_LAG_PATTERNS["transport_lag_sec"],
        ),
        "apply_lag_sec": _extract_duration_metric(
            text,
            DATA_GUARD_LAG_PATTERNS["apply_lag_sec"],
        ),
    }


def _extract_duration_metric(
    text: str,
    patterns: tuple[re.Pattern[str], ...],
) -> float | None:
    """Return the first matched duration metric normalized to seconds."""

    for pattern in patterns:
        match = pattern.search(text)
        if match is None:
            continue
        return _duration_to_seconds(match.group(1))
    return None


def _duration_to_seconds(value: str) -> float | None:
    """Convert common Oracle duration text into seconds."""

    candidate = " ".join(value.strip().split())
    if not candidate:
        return None

    day_match = re.fullmatch(
        r"(\d+)\s+day[s]?\s+(\d{1,2}):(\d{2}):(\d{2})",
        candidate,
        re.IGNORECASE,
    )
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

    return _to_float(candidate)
