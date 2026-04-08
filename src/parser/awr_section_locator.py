"""Utilities for locating major sections within Oracle AWR report lines.

This module provides a small, deterministic section locator for the
Day 1 parser foundation. It scans normalized AWR report lines for a
fixed set of known section header patterns and returns a canonical map
of the sections that were found.
"""

from __future__ import annotations

from typing import TypedDict


class AwrSectionLocation(TypedDict):
    """Location metadata for a detected AWR report section."""

    start_line: int
    end_line: int
    matched_pattern: str


AwrSectionMap = dict[str, AwrSectionLocation]


SECTION_PATTERNS: dict[str, tuple[str, ...]] = {
    "report_header": (
        "workload repository report",
        "awr report",
    ),
    "cpu": (
        "load profile",
        "host cpu",
        "cpu statistics",
        "foreground cpu usage summary",
    ),
    "waits": (
        "top 10 foreground events by total wait time",
        "foreground wait events",
        "wait classes by total wait time",
    ),
    "top_sql": (
        "sql ordered by elapsed time",
        "sql ordered by cpu time",
        "sql ordered by gets",
        "sql ordered by reads",
        "sql ordered by executions",
    ),
    "io": (
        "iostat by function",
        "iostat by filetype summary",
        "i/o statistics",
        "io profile",
        "tablespace io stats",
        "file io stats",
        "segments by physical reads",
    ),
    "sessions": (
        "session statistics",
        "sql ordered by version count",
        "logons cumulative",
        "activity during the snapshot period",
    ),
    "cluster": (
        "global cache",
        "cluster wait",
        "cache fusion",
        "gc cr",
        "gc current",
    ),
    "dataguard": (
        "data guard",
        "transport lag",
        "apply lag",
        "managed recovery",
        "database role",
    ),
    "exadata": (
        "exadata",
        "cell smart table scan",
        "cell physical io interconnect bytes",
        "bytes eligible for predicate offload",
        "storage index",
    ),
}


def locate_awr_sections(lines: list[str]) -> AwrSectionMap:
    """Locate major Oracle AWR report sections from file lines.

    The locator scans the input lines in order and records the first
    matching header pattern for each supported canonical section key.
    Section end lines are calculated from the next detected section start
    or the end of file when no later section exists.

    Returned line numbers are 1-based and inclusive.

    Args:
        lines: AWR report lines, typically produced by the file loader.

    Returns:
        A dictionary keyed by canonical section name for each section that
        was found in the input.
    """

    detections: list[tuple[str, int, str]] = []
    seen_sections: set[str] = set()

    for index, line in enumerate(lines, start=1):
        normalized_line = _normalize_line(line)

        if not normalized_line:
            continue

        for section_key, patterns in SECTION_PATTERNS.items():
            if section_key in seen_sections:
                continue

            matched_pattern = _match_pattern(normalized_line, patterns)
            if matched_pattern is None:
                continue

            detections.append((section_key, index, matched_pattern))
            seen_sections.add(section_key)
            break

    section_map: AwrSectionMap = {}
    file_end_line = len(lines)

    for position, (section_key, start_line, matched_pattern) in enumerate(detections):
        if position + 1 < len(detections):
            next_start_line = detections[position + 1][1]
            end_line = next_start_line - 1
        else:
            end_line = file_end_line

        section_map[section_key] = {
            "start_line": start_line,
            "end_line": end_line,
            "matched_pattern": matched_pattern,
        }

    return section_map


def _match_pattern(normalized_line: str, patterns: tuple[str, ...]) -> str | None:
    """Return the first matching pattern contained in the normalized line."""

    for pattern in patterns:
        if pattern in normalized_line:
            return pattern

    return None


def _normalize_line(line: str) -> str:
    """Normalize line text for simple case-insensitive pattern matching."""

    return " ".join(line.strip().lower().split())
