"""Deterministic parsing utilities for Oracle AWR Instance Activity Stats."""

from __future__ import annotations

import re
from typing import Any

SECTION_HEADER = "instance activity stats"
ROW_PATTERN = re.compile(
    r"^\s*(.+?)\s+([0-9,]+(?:\.\d+)?)\s+([0-9,]+(?:\.\d+)?)\s+([0-9,]+(?:\.\d+)?)\s*$"
)


def parse_instance_activity_stats(lines: list[str]) -> list[dict[str, Any]]:
    """Parse Instance Activity Stats rows from the full AWR text.

    The AWR report already exposes interval totals in this section, so the
    ``total`` column can be treated as the snapshot delta for that report.
    """

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

        if normalized.startswith("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"):
            if seen_header:
                break
            continue

        if not normalized or _is_divider(line):
            continue

        if normalized.startswith("statistic total per second per trans"):
            seen_header = True
            continue

        if not seen_header:
            continue

        match = ROW_PATTERN.match(line)
        if not match:
            continue

        total = _to_float(match.group(2))
        per_second = _to_float(match.group(3))
        per_trans = _to_float(match.group(4))
        if None in {total, per_second, per_trans}:
            continue

        rows.append(
            {
                "statistic_name": match.group(1).strip(),
                "total": total,
                "per_second": per_second,
                "per_transaction": per_trans,
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
