"""Regex-based extraction of selected Oracle AWR metrics from raw text files.

This module parses one or more AWR ``.out`` reports directly from text and
returns a JSON-serializable structure with snapshot metadata, extracted
metric detail, scalar metric values, and real violin-series arrays for
three selected metrics:

1. PGA spill pressure
2. Temporary tablespace I/O pressure
3. Hard parses per second

No source values are fabricated. Violin plots require real distributions;
scalar metrics must not be expanded into synthetic arrays.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from src.parser.awr_file_loader import load_awr_file

NUMBER_PATTERN = r"([0-9][0-9,]*(?:\.\d+)?)"
SECTION_DIVIDER_PATTERN = re.compile(r"^\s*~{5,}\s*$")
BEGIN_SNAP_PATTERN = re.compile(
    rf"^\s*Begin\s+Snap\s*:\s*(\d+)\s+(.+?)\s*$",
    re.IGNORECASE,
)
END_SNAP_PATTERN = re.compile(
    rf"^\s*End\s+Snap\s*:\s*(\d+)\s+(.+?)\s*$",
    re.IGNORECASE,
)
ELAPSED_PATTERN = re.compile(
    rf"^\s*Elapsed\s*:\s*{NUMBER_PATTERN}\s*\((mins?|minutes?|secs?|seconds?|hrs?|hours?)\)\s*$",
    re.IGNORECASE,
)
DB_ROW_PATTERN = re.compile(
    r"^\s*(\S+)\s+(\d+)\s+(\S+)\s+(\d+)\b",
)
LOAD_PROFILE_HARD_PARSES_PATTERN = re.compile(
    rf"^\s*Hard\s+parses\s*:\s*{NUMBER_PATTERN}(?:\s+{NUMBER_PATTERN})?\s*$",
    re.IGNORECASE,
)
INSTANCE_ACTIVITY_ROW_PATTERN = re.compile(
    rf"^\s*(.+?)\s+{NUMBER_PATTERN}\s+{NUMBER_PATTERN}\s+{NUMBER_PATTERN}\s*$"
)
IN_MEMORY_SORT_PATTERN = re.compile(
    rf"In-memory\s+Sort\s*%\s*:\s*{NUMBER_PATTERN}",
    re.IGNORECASE,
)
WORKAREA_STAT_PATTERN = re.compile(
    rf"^\s*workarea\s+executions\s*-\s*(optimal|onepass|multipass)\b.*?{NUMBER_PATTERN}\s*$",
    re.IGNORECASE,
)
TABLESPACE_IO_ROW_PATTERN = re.compile(
    rf"^\s*(\S+)\s+{NUMBER_PATTERN}\s+{NUMBER_PATTERN}\s+{NUMBER_PATTERN}\s+{NUMBER_PATTERN}\s*$"
)


def parse_awr_metric_files(
    file_paths: list[str | Path],
) -> dict[str, list[dict[str, Any]]]:
    """Parse one or more raw AWR files into a JSON-serializable result."""

    return {
        "files": [parse_awr_metric_file(file_path) for file_path in file_paths],
    }


def parse_awr_metric_file(file_path: str | Path) -> dict[str, Any]:
    """Parse one raw AWR file for the requested snapshot and metric payload."""

    loaded = load_awr_file(file_path)
    lines = loaded["lines"]
    raw_text = loaded["raw_text"]

    snapshot = _parse_snapshot_metadata(lines, raw_text)
    pga_spill = _parse_pga_spill(lines, raw_text)
    temp_io = _parse_temp_io(lines, snapshot.get("elapsed_seconds"))
    hard_parses = _parse_hard_parses(lines, snapshot.get("elapsed_seconds"))
    scalar_metrics = _build_scalar_metrics(pga_spill, temp_io, hard_parses)

    # Violin plots require real distributions; scalar-only evidence stays in
    # derived_scalar_metrics and must not be expanded into violin arrays.
    return {
        "file_name": loaded["file_name"],
        "snapshot": snapshot,
        "extracted": {
            "pga_spill": pga_spill,
            "temp_io": temp_io,
            "hard_parses": hard_parses,
        },
        "derived_scalar_metrics": scalar_metrics,
        "violin_panel": _empty_violin_panel(),
        "violin_sources": {
            "pga_spill_pressure": None,
            "temp_io_pressure": None,
            "hard_parses_per_sec": None,
        },
    }


def _parse_snapshot_metadata(lines: list[str], raw_text: str) -> dict[str, Any]:
    """Extract snapshot metadata from the AWR header and summary lines."""

    db_name: str | None = None
    instance_name: str | None = None
    snap_begin: str | None = None
    snap_end: str | None = None
    snap_id_begin: int | None = None
    snap_id_end: int | None = None
    elapsed_seconds: float | None = None

    db_header_seen = False
    for line in lines[:200]:
        normalized = _normalize_line(line)
        if (
            "db name" in normalized
            and "instance" in normalized
            and "inst num" in normalized
        ):
            db_header_seen = True
            continue
        if db_header_seen:
            if not line.strip() or _is_separator_line(line):
                continue
            match = DB_ROW_PATTERN.match(line)
            if match:
                db_name = match.group(1)
                instance_name = match.group(3)
            db_header_seen = False

        begin_match = BEGIN_SNAP_PATTERN.match(line)
        if begin_match:
            snap_id_begin = _to_int(begin_match.group(1))
            snap_begin = begin_match.group(2).strip()
            continue

        end_match = END_SNAP_PATTERN.match(line)
        if end_match:
            snap_id_end = _to_int(end_match.group(1))
            snap_end = end_match.group(2).strip()
            continue

        elapsed_match = ELAPSED_PATTERN.match(line)
        if elapsed_match:
            elapsed_seconds = _elapsed_to_seconds(
                _to_float(elapsed_match.group(1)),
                elapsed_match.group(2),
            )

    if db_name is None:
        db_name = _search_first_group(raw_text, r"\bDB\s+Name\s*[:=]\s*(\S+)")
    if instance_name is None:
        instance_name = _search_first_group(
            raw_text, r"\bInstance\s+Name\s*[:=]\s*(\S+)"
        )

    return {
        "db_name": db_name,
        "instance_name": instance_name,
        "snap_begin": snap_begin,
        "snap_end": snap_end,
        "elapsed_seconds": elapsed_seconds,
    }


def _parse_pga_spill(lines: list[str], raw_text: str) -> dict[str, Any] | None:
    """Parse direct or proxy spill indicators from raw AWR text."""

    direct_counts = _parse_workarea_execution_counts(lines)
    in_memory_sort_pct = _search_first_float(raw_text, IN_MEMORY_SORT_PATTERN)

    if all(value is not None for value in direct_counts.values()):
        optimal = int(direct_counts["optimal"])
        onepass = int(direct_counts["onepass"])
        multipass = int(direct_counts["multipass"])
        total = optimal + onepass + multipass
        spill_ratio = None if total <= 0 else (onepass + multipass) / total
        return {
            "source": "workarea executions",
            "optimal": optimal,
            "onepass": onepass,
            "multipass": multipass,
            "spill_ratio": spill_ratio,
            "in_memory_sort_pct": in_memory_sort_pct,
        }

    if in_memory_sort_pct is not None:
        return {
            "source": "instance efficiency",
            "optimal": None,
            "onepass": None,
            "multipass": None,
            "spill_ratio": None,
            "in_memory_sort_pct": in_memory_sort_pct,
        }

    return None


def _parse_temp_io(
    lines: list[str],
    elapsed_seconds: float | None,
) -> dict[str, Any] | None:
    """Parse TEMP tablespace read/write counts from Tablespace IO Stats."""

    section_lines = _extract_section_lines(lines, "Tablespace IO Stats")
    temp_row = _find_temp_tablespace_row(section_lines)
    if temp_row is None:
        temp_row = _find_temp_tablespace_row(lines)
    if temp_row is None:
        return None

    temp_reads = _to_int(temp_row["reads"])
    temp_writes = _to_int(temp_row["writes"])
    avg_read_ms = _to_float(temp_row["avg_read_ms"])
    avg_write_ms = _to_float(temp_row["avg_write_ms"])
    if temp_reads is None or temp_writes is None:
        return None

    temp_total_io = temp_reads + temp_writes
    temp_iops = None
    if isinstance(elapsed_seconds, (int, float)) and elapsed_seconds > 0:
        temp_iops = temp_total_io / float(elapsed_seconds)

    return {
        "source": "tablespace io stats",
        "temp_reads": temp_reads,
        "temp_writes": temp_writes,
        "temp_total_io": temp_total_io,
        "avg_read_ms": avg_read_ms,
        "avg_write_ms": avg_write_ms,
        "temp_iops": temp_iops,
    }


def _parse_hard_parses(
    lines: list[str],
    elapsed_seconds: float | None,
) -> dict[str, Any] | None:
    """Parse hard parses per second from Load Profile or equivalent sections."""

    load_profile_lines = _extract_section_lines(lines, "Load Profile")
    hard_parses_per_sec = _search_hard_parses_per_second(load_profile_lines)
    source = "load profile" if hard_parses_per_sec is not None else None

    if hard_parses_per_sec is None:
        activity_value = _search_instance_activity_per_second(
            lines,
            "parse count (hard)",
        )
        if activity_value is not None:
            hard_parses_per_sec = activity_value
            source = "instance activity stats"

    if hard_parses_per_sec is None:
        return None

    if elapsed_seconds is not None and elapsed_seconds <= 0:
        return None

    return {
        "source": source,
        "hard_parses_per_sec": hard_parses_per_sec,
    }


def _build_scalar_metrics(
    pga_spill: dict[str, Any] | None,
    temp_io: dict[str, Any] | None,
    hard_parses: dict[str, Any] | None,
) -> dict[str, float | None]:
    """Return scalar values separately from violin series.

    Violin plots require real distributions; scalar metrics must not be
    expanded into synthetic arrays.
    """

    pga_value = None
    if pga_spill:
        spill_ratio = pga_spill.get("spill_ratio")
        if isinstance(spill_ratio, (int, float)) and spill_ratio >= 0:
            pga_value = float(spill_ratio) * 100.0

    temp_value = None
    if temp_io:
        temp_iops = temp_io.get("temp_iops")
        if isinstance(temp_iops, (int, float)) and temp_iops >= 0:
            temp_value = float(temp_iops)

    hard_parse_value = None
    if hard_parses:
        value = hard_parses.get("hard_parses_per_sec")
        if isinstance(value, (int, float)) and value >= 0:
            hard_parse_value = float(value)

    return {
        "pga_spill_pressure": pga_value,
        "temp_io_pressure": temp_value,
        "hard_parses_per_sec": hard_parse_value,
    }


def _empty_violin_panel() -> dict[str, list[float]]:
    """Return an empty violin payload for metrics without real series."""

    return {
        "pga_spill_pressure": [],
        "temp_io_pressure": [],
        "hard_parses_per_sec": [],
    }


def _parse_workarea_execution_counts(lines: list[str]) -> dict[str, int | None]:
    """Find direct workarea execution counters anywhere in the report text."""

    values: dict[str, int | None] = {
        "optimal": None,
        "onepass": None,
        "multipass": None,
    }

    for line in lines:
        match = WORKAREA_STAT_PATTERN.match(line)
        if not match:
            continue
        stat_name = match.group(1).lower()
        stat_value = _to_int(match.group(2))
        if stat_value is None:
            continue
        values[stat_name] = stat_value

    return values


def _find_temp_tablespace_row(lines: list[str]) -> dict[str, str] | None:
    """Return the parsed TEMP row from a Tablespace IO-style section."""

    for line in lines:
        match = TABLESPACE_IO_ROW_PATTERN.match(line)
        if not match:
            continue
        if match.group(1).strip().upper() != "TEMP":
            continue
        return {
            "reads": match.group(2),
            "avg_read_ms": match.group(3),
            "writes": match.group(4),
            "avg_write_ms": match.group(5),
        }

    return None


def _search_hard_parses_per_second(lines: list[str]) -> float | None:
    """Find the Load Profile 'Hard parses:' per-second value."""

    for line in lines:
        match = LOAD_PROFILE_HARD_PARSES_PATTERN.match(line)
        if not match:
            continue
        return _to_float(match.group(1))
    return None


def _search_instance_activity_per_second(
    lines: list[str],
    statistic_name: str,
) -> float | None:
    """Find a matching Instance Activity Stats row and return the per-second value."""

    section_lines = _extract_section_lines(lines, "Instance Activity Stats")
    for line in section_lines:
        match = INSTANCE_ACTIVITY_ROW_PATTERN.match(line)
        if not match:
            continue
        if match.group(1).strip().lower() != statistic_name.lower():
            continue
        return _to_float(match.group(3))
    return None


def _extract_section_lines(lines: list[str], section_title: str) -> list[str]:
    """Extract lines belonging to an AWR section by title."""

    normalized_title = _normalize_line(section_title)
    start_index: int | None = None

    for index, line in enumerate(lines):
        if _normalize_line(line) == normalized_title:
            start_index = index + 1
            break

    if start_index is None:
        return []

    section_lines: list[str] = []
    divider_count = 0
    for line in lines[start_index:]:
        if SECTION_DIVIDER_PATTERN.match(line):
            divider_count += 1
            if section_lines and divider_count >= 1:
                break
            continue
        divider_count = 0
        section_lines.append(line)

    return section_lines


def _search_first_group(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def _search_first_float(text: str, pattern: re.Pattern[str]) -> float | None:
    match = pattern.search(text)
    if not match:
        return None
    return _to_float(match.group(1))


def _elapsed_to_seconds(value: float | None, unit: str | None) -> float | None:
    if value is None or not unit:
        return None

    normalized_unit = unit.strip().lower()
    if normalized_unit.startswith("min"):
        return value * 60.0
    if normalized_unit.startswith("sec"):
        return value
    if normalized_unit.startswith("hr") or normalized_unit.startswith("hour"):
        return value * 3600.0
    return None


def _normalize_line(line: str) -> str:
    return " ".join(line.strip().lower().split())


def _is_separator_line(line: str) -> bool:
    return bool(re.fullmatch(r"[-=\s]+", line.strip() or ""))


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace(",", "").strip())
    except (AttributeError, ValueError):
        return None


def _to_int(value: str | None) -> int | None:
    parsed = _to_float(value)
    if parsed is None:
        return None
    if not float(parsed).is_integer():
        return int(parsed)
    return int(parsed)


if __name__ == "__main__":
    file_args = [Path(arg) for arg in sys.argv[1:]]
    if not file_args:
        raise SystemExit(
            "Usage: python -m src.parser.awr_regex_metrics_parser <awr1.out> [awr2.out ...]"
        )

    print(json.dumps(parse_awr_metric_files(file_args), indent=2))
