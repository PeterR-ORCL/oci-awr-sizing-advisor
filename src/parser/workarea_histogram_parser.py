"""Parse workarea execution behavior from AWR text when present."""

from __future__ import annotations

import re
from typing import Any


HEADER_PATTERN = re.compile(
    r"optimal.+onepass.+multipass",
    re.IGNORECASE,
)
SCALAR_PATTERN = re.compile(
    r"^\s*(Optimal|Onepass|Multipass)(?:\s+\w+)*\s+Executions?\s*:?\s*([\d,]+)\s*$",
    re.IGNORECASE,
)
ROW_PATTERN = re.compile(
    r"^\s*(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)(?:\s+([\d,]+))?\s*$"
)


def parse_workarea_histogram(lines: list[str]) -> dict[str, Any]:
    """Parse workarea execution counts from histogram/scalar sections.

    The AWR text report may expose interval workarea execution behavior as
    histogram rows or scalar counters. We aggregate optimal, onepass, and
    multipass executions so downstream logic can compute spill pressure as:
    (onepass + multipass) / total_executions.
    """

    rows = _parse_histogram_rows(lines)
    if rows:
        return _build_histogram_payload(rows)

    scalars = _parse_scalar_counts(lines)
    if scalars:
        return _build_scalar_payload(scalars)

    return {}


def _parse_histogram_rows(lines: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    in_section = False

    for line in lines:
        if not in_section and HEADER_PATTERN.search(line):
            in_section = True
            continue

        if not in_section:
            continue

        stripped = line.strip()
        if not stripped:
            if rows:
                break
            continue
        if set(stripped) <= {"-", " "}:
            continue
        if HEADER_PATTERN.search(line):
            continue

        match = ROW_PATTERN.match(line)
        if not match:
            if rows:
                break
            continue

        optimal = _parse_int(match.group(2))
        onepass = _parse_int(match.group(3))
        multipass = _parse_int(match.group(4))
        total = _parse_int(match.group(5)) if match.group(5) else optimal + onepass + multipass

        if min(optimal, onepass, multipass, total) < 0:
            continue
        if total <= 0:
            continue

        rows.append(
            {
                "bucket": match.group(1).strip(),
                "optimal_executions": optimal,
                "onepass_executions": onepass,
                "multipass_executions": multipass,
                "total_executions": total,
            }
        )

    return rows


def _parse_scalar_counts(lines: list[str]) -> dict[str, int]:
    scalars: dict[str, int] = {}
    for line in lines:
        match = SCALAR_PATTERN.match(line)
        if not match:
            continue
        label = match.group(1).lower()
        scalars[f"{label}_executions"] = _parse_int(match.group(2))

    return scalars


def _build_histogram_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    optimal = sum(int(row["optimal_executions"]) for row in rows)
    onepass = sum(int(row["onepass_executions"]) for row in rows)
    multipass = sum(int(row["multipass_executions"]) for row in rows)
    total = sum(int(row["total_executions"]) for row in rows)

    return {
        "rows": rows,
        "source": "awr_workarea_histogram",
        "scope": "interval",
        "optimal_executions": optimal,
        "onepass_executions": onepass,
        "multipass_executions": multipass,
        "total_executions": total,
        "spill_ratio": _safe_ratio(onepass + multipass, total),
        "weighted_spill_pressure": _safe_ratio(onepass + (3 * multipass), total),
    }


def _build_scalar_payload(scalars: dict[str, int]) -> dict[str, Any]:
    optimal = int(scalars.get("optimal_executions", 0))
    onepass = int(scalars.get("onepass_executions", 0))
    multipass = int(scalars.get("multipass_executions", 0))
    total = optimal + onepass + multipass
    if total <= 0:
        return {}

    return {
        "rows": [],
        "source": "awr_workarea_scalar",
        "scope": "interval",
        "optimal_executions": optimal,
        "onepass_executions": onepass,
        "multipass_executions": multipass,
        "total_executions": total,
        "spill_ratio": _safe_ratio(onepass + multipass, total),
        "weighted_spill_pressure": _safe_ratio(onepass + (3 * multipass), total),
    }


def _parse_int(value: str) -> int:
    return int(value.replace(",", "").strip())


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)
