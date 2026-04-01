"""Deterministic parsing utilities for Oracle AWR Tablespace IO Stats."""

from __future__ import annotations

import re
from typing import Any

SECTION_HEADER = "tablespace io stats"
ROW_PATTERN = re.compile(
    r"^\s*([A-Za-z0-9_$#]+)\s+([0-9,]+)\s+([0-9,]+(?:\.\d+)?)\s+([0-9,]+)\s+([0-9,]+(?:\.\d+)?)\s*$"
)


def parse_tablespace_io_stats(lines: list[str]) -> list[dict[str, Any]]:
    """Parse Tablespace IO Stats rows from the full AWR text."""

    rows: list[dict[str, Any]] = []
    in_section = False
    seen_header = False

    for line in lines:
        normalized = _normalize(line)

        if normalized == SECTION_HEADER:
            in_section = True
            seen_header = False
            continue

        if not in_section:
            continue

        if normalized.startswith("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~") and seen_header:
            break

        if not normalized or _is_divider(line):
            continue

        if normalized.startswith("tablespace reads avg read"):
            seen_header = True
            continue

        if not seen_header:
            continue

        match = ROW_PATTERN.match(line)
        if not match:
            continue

        reads = _to_float(match.group(2))
        avg_read_ms = _to_float(match.group(3))
        writes = _to_float(match.group(4))
        avg_write_ms = _to_float(match.group(5))
        if None in {reads, avg_read_ms, writes, avg_write_ms}:
            continue

        rows.append(
            {
                "tablespace": match.group(1).strip(),
                "reads": reads,
                "avg_read_ms": avg_read_ms,
                "writes": writes,
                "avg_write_ms": avg_write_ms,
            }
        )

    return rows


def _normalize(line: str) -> str:
    return " ".join(line.strip().lower().split())


def _is_divider(line: str) -> bool:
    return bool(re.fullmatch(r"[-=\s]+", line.strip() or ""))


def _to_float(value: str) -> float | None:
    try:
        return float(value.replace(",", ""))
    except (AttributeError, ValueError):
        return None
