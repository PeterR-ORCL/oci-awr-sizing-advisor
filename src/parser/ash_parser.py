"""Deterministic parsing utilities for Oracle AWR Appendix B ASH samples."""

from __future__ import annotations

import re
from typing import Any

SECTION_HEADER = "appendix b - ash sample"
ROW_PATTERN = re.compile(
    r"^\s*(\d{2}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}:\d{2})\s+"
    r"(\d+)\s+(\S+)\s+(.+?)\s{2,}(.+?)\s{2,}(.+?)\s*$"
)


def parse_ash_samples(lines: list[str]) -> list[dict[str, Any]]:
    """Parse ASH sample rows from the report appendix."""

    samples: list[dict[str, Any]] = []
    in_section = False
    seen_header = False

    for line in lines:
        normalized_line = _normalize_line(line)

        if normalized_line == SECTION_HEADER:
            in_section = True
            seen_header = False
            continue

        if not in_section:
            continue

        if (
            normalized_line.startswith("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            and seen_header
        ):
            break

        if not normalized_line or _is_divider_line(line):
            continue

        if normalized_line.startswith("sample time session id sql id event"):
            seen_header = True
            continue

        if not seen_header:
            continue

        match = ROW_PATTERN.match(line)
        if not match:
            continue

        sample_time = match.group(1).strip()
        session_id = _to_int(match.group(2))
        sql_id = match.group(3).strip()
        event_name = match.group(4).strip()
        wait_class = match.group(5).strip()
        module = match.group(6).strip()
        if session_id is None:
            continue

        samples.append(
            {
                "sample_time": sample_time,
                "session_id": session_id,
                "sql_id": sql_id,
                "event_name": event_name,
                "wait_class": wait_class,
                "module": module,
            }
        )

    return samples


def _normalize_line(line: str) -> str:
    return " ".join(line.strip().lower().split())


def _is_divider_line(line: str) -> bool:
    return bool(re.fullmatch(r"[-=\s]+", line.strip() or ""))


def _to_int(value: str) -> int | None:
    try:
        return int(value.replace(",", ""))
    except (AttributeError, ValueError):
        return None
