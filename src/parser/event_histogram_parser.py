"""Deterministic parsing utilities for Oracle AWR top event histograms."""

from __future__ import annotations

import re
from typing import Any


SECTION_HEADER = "top event histograms"
EVENT_HEADER_PATTERN = re.compile(r"^\s*Event:\s+(.+?)\s*$", re.IGNORECASE)
BUCKET_PATTERN = re.compile(r"^\s*([0-9,]+(?:\.\d+)?)\s+([0-9,]+)\s*$")


def parse_event_histograms(lines: list[str]) -> dict[str, list[dict[str, Any]]]:
    """Parse event histograms keyed by event name."""

    histograms: dict[str, list[dict[str, Any]]] = {}
    in_section = False
    current_event: str | None = None

    for line in lines:
        normalized_line = _normalize_line(line)

        if normalized_line == SECTION_HEADER:
            in_section = True
            current_event = None
            continue

        if not in_section:
            continue

        if normalized_line.startswith("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~") and histograms:
            break

        if not normalized_line or _is_divider_line(line):
            continue

        event_match = EVENT_HEADER_PATTERN.match(line)
        if event_match:
            current_event = event_match.group(1).strip()
            histograms.setdefault(current_event, [])
            continue

        if normalized_line.startswith("bucket(ms) wait count"):
            continue

        if current_event is None:
            continue

        bucket_match = BUCKET_PATTERN.match(line)
        if not bucket_match:
            continue

        bucket_ms = _to_float(bucket_match.group(1))
        wait_count = _to_int(bucket_match.group(2))
        if bucket_ms is None or wait_count is None:
            continue

        histograms[current_event].append(
            {
                "bucket_ms": bucket_ms,
                "wait_count": wait_count,
            }
        )

    return histograms


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
