"""Deterministic parsing utilities for Oracle AWR PGA Target Advisory."""

from __future__ import annotations

import re
from typing import Any

CACHE_PGA_PATTERN = re.compile(
    r"^\s*PGA Target\s*:\s*([0-9,]+)G\s+([0-9,]+)G\s*$", re.IGNORECASE
)
ADVISORY_HEADER = "pga target advisory"
ROW_PATTERN = re.compile(r"^\s*([0-9,]+)\s+([0-9,]+(?:\.\d+)?)\s+([0-9,]+)\s*$")


def parse_pga_advisory(lines: list[str]) -> dict[str, Any]:
    """Parse PGA advisory rows and the configured target size when present."""

    current_target_mb: float | None = None
    rows: list[dict[str, Any]] = []
    in_section = False
    seen_header = False

    for line in lines:
        if current_target_mb is None:
            current_target_mb = _parse_current_target_mb(line)

        normalized = _normalize(line)

        if normalized == ADVISORY_HEADER:
            in_section = True
            seen_header = False
            continue

        if not in_section:
            continue

        if normalized.startswith("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~") and seen_header:
            break

        if not normalized or _is_divider(line):
            continue

        if normalized.startswith("pga target (mb) estd pga cache hit"):
            seen_header = True
            continue

        if not seen_header:
            continue

        match = ROW_PATTERN.match(line)
        if not match:
            continue

        target_mb = _to_float(match.group(1))
        cache_hit_pct = _to_float(match.group(2))
        overalloc_count = _to_float(match.group(3))
        if None in {target_mb, cache_hit_pct, overalloc_count}:
            continue

        rows.append(
            {
                "target_mb": target_mb,
                "cache_hit_pct": cache_hit_pct,
                "overalloc_count": overalloc_count,
            }
        )

    return {
        "current_target_mb": current_target_mb,
        "rows": rows,
    }


def _parse_current_target_mb(line: str) -> float | None:
    match = CACHE_PGA_PATTERN.match(line)
    if not match:
        return None

    end_gb = _to_float(match.group(2))
    if end_gb is None:
        return None
    return end_gb * 1024.0


def _normalize(line: str) -> str:
    return " ".join(line.strip().lower().split())


def _is_divider(line: str) -> bool:
    return bool(re.fullmatch(r"[-=\s]+", line.strip() or ""))


def _to_float(value: str) -> float | None:
    try:
        return float(value.replace(",", ""))
    except (AttributeError, ValueError):
        return None
