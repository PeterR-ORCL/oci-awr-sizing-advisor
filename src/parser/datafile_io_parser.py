"""Deterministic parsing utilities for Oracle AWR Datafile IO Stats."""

from __future__ import annotations

import re
from typing import Any


DATAFILE_IO_HEADER = "datafile io stats"
ROW_PATTERN = re.compile(
    r"^\s*(\d+)\s+([A-Za-z0-9_#$]+)\s+([0-9,]+)\s+([0-9,]+)\s+"
    r"([0-9,]+(?:\.\d+)?)\s+([0-9,]+(?:\.\d+)?)\s+([0-9,]+(?:\.\d+)?)\s+([0-9,]+(?:\.\d+)?)\s*$"
)


def parse_datafile_io_stats(lines: list[str]) -> list[dict[str, Any]]:
    """Parse Datafile IO Stats rows from the full AWR text."""

    records: list[dict[str, Any]] = []
    in_section = False
    seen_header = False

    for line in lines:
        normalized_line = _normalize_line(line)

        if normalized_line == DATAFILE_IO_HEADER:
            in_section = True
            seen_header = False
            continue

        if not in_section:
            continue

        if normalized_line.startswith("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"):
            if seen_header:
                break
            continue

        if not normalized_line or _is_divider_line(line):
            continue

        if normalized_line.startswith("file no tablespace"):
            seen_header = True
            continue

        if not seen_header:
            continue

        match = ROW_PATTERN.match(line)
        if not match:
            continue

        file_no = _to_int(match.group(1))
        tablespace = match.group(2).strip()
        reads = _to_float(match.group(3))
        writes = _to_float(match.group(4))
        read_mb = _to_float(match.group(5))
        write_mb = _to_float(match.group(6))
        avg_read_ms = _to_float(match.group(7))
        avg_write_ms = _to_float(match.group(8))
        if None in {file_no, reads, writes, read_mb, write_mb, avg_read_ms, avg_write_ms}:
            continue

        records.append(
            {
                "file_no": file_no,
                "tablespace": tablespace,
                "reads": reads,
                "writes": writes,
                "read_mb": read_mb,
                "write_mb": write_mb,
                "avg_read_ms": avg_read_ms,
                "avg_write_ms": avg_write_ms,
            }
        )

    return records


def _normalize_line(line: str) -> str:
    return " ".join(line.strip().lower().split())


def _is_divider_line(line: str) -> bool:
    return bool(re.fullmatch(r"[-=\s]+", line.strip() or ""))


def _to_float(value: str) -> float | None:
    try:
        return float(value.replace(",", ""))
    except (AttributeError, ValueError):
        return None


def _to_int(value: str) -> int | None:
    try:
        return int(value.replace(",", ""))
    except (AttributeError, ValueError):
        return None
