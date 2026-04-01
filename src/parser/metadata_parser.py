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

    host_row_values = _extract_table_row(
        candidate_lines,
        required_headers=("host name", "platform"),
    )
    if host_row_values:
        metadata["host_name"] = host_row_values[0] if len(host_row_values) > 0 else None
        metadata["platform"] = host_row_values[1] if len(host_row_values) > 1 else None

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
            r"host name\s*[:=]\s*(.+)",
            r"host\s*[:=]\s*(.+)",
        ),
    )
    metadata["platform"] = metadata["platform"] or _search_patterns(
        candidate_text,
        (r"platform\s*[:=]\s*(.+)",),
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
) -> tuple[str, str, str, str] | None:
    """Extract the first four fields from the main AWR identity row."""

    header_pattern = re.compile(
        r"\bDB\s+Name\b.*\bDB\s+Id\b.*\bInstance\b.*\bInst\s+Num\b",
        flags=re.IGNORECASE,
    )
    value_pattern = re.compile(
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
            return match.group(1), match.group(2), match.group(3), match.group(4)

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
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue

        value = match.group(1).strip()
        if value:
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
