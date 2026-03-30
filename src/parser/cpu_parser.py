"""Deterministic parsing utilities for Oracle AWR CPU section metrics."""

from __future__ import annotations

import re
from typing import Any


LOAD_PROFILE_HEADER = "load profile"
INSTANCE_EFFICIENCY_HEADER = "instance efficiency percentages"
HOST_CPU_HEADER = "host cpu"

LOAD_PROFILE_ROW_PATTERN = re.compile(
    r"^\s*([^:]+):\s+([0-9,]+(?:\.\d+)?)"
    r"(?:\s+([0-9,]+(?:\.\d+)?))?\s*$"
)
PERCENT_ROW_PATTERN = re.compile(r"^\s*([^:]+):\s+([0-9,]+(?:\.\d+)?)\s*$")
HOST_CPU_VALUE_PATTERN = re.compile(
    r"^\s*([0-9]+(?:\.\d+)?)\s+([0-9]+(?:\.\d+)?)\s+([0-9]+(?:\.\d+)?)\s+"
    r"([0-9]+(?:\.\d+)?)\s+([0-9]+(?:\.\d+)?)\s+([0-9]+(?:\.\d+)?)\s+"
    r"([0-9]+(?:\.\d+)?)\s*$"
)


def parse_cpu_section(lines: list[str]) -> list[dict[str, Any]]:
    """Parse structured metrics from an Oracle AWR CPU section.

    The parser extracts known CPU-related metric groups from the input
    lines:

    - Load Profile
    - Instance Efficiency Percentages
    - Host CPU

    Rows that do not clearly match the expected AWR patterns are ignored.

    Args:
        lines: CPU section lines from the loaded AWR report.

    Returns:
        A list of structured metric records.
    """

    metrics: list[dict[str, Any]] = []
    current_group: str | None = None
    pending_host_cpu_values = False

    for line in lines:
        normalized_line = _normalize_line(line)
        if not normalized_line or _is_divider_line(line):
            continue

        if normalized_line == LOAD_PROFILE_HEADER:
            current_group = "load_profile"
            pending_host_cpu_values = False
            continue

        if normalized_line == INSTANCE_EFFICIENCY_HEADER:
            current_group = "instance_efficiency"
            pending_host_cpu_values = False
            continue

        if normalized_line == HOST_CPU_HEADER:
            current_group = "host_cpu"
            pending_host_cpu_values = False
            continue

        if current_group == "load_profile":
            if normalized_line.startswith("per second") or normalized_line.startswith(
                "per transaction"
            ):
                continue

            metric = _parse_load_profile_row(line)
            if metric is not None:
                metrics.append(metric)
            continue

        if current_group == "instance_efficiency":
            metric = _parse_instance_efficiency_row(line)
            if metric is not None:
                metrics.append(metric)
            continue

        if current_group == "host_cpu":
            if normalized_line.startswith("begin end user system idle wio busy"):
                pending_host_cpu_values = True
                continue

            if pending_host_cpu_values:
                host_cpu_metrics = _parse_host_cpu_values(line)
                if host_cpu_metrics:
                    metrics.extend(host_cpu_metrics)
                    pending_host_cpu_values = False

    return metrics


def _parse_load_profile_row(line: str) -> dict[str, Any] | None:
    """Parse a Load Profile metric row."""

    match = LOAD_PROFILE_ROW_PATTERN.match(line)
    if not match:
        return None

    metric_name = match.group(1).strip()
    per_second = _to_float(match.group(2))
    per_transaction = _to_float(match.group(3)) if match.group(3) else None

    if not metric_name or per_second is None:
        return None

    return {
        "metric_name": metric_name,
        "per_second": per_second,
        "per_transaction": per_transaction,
        "metric_source_section": "cpu",
        "metric_group": "load_profile",
    }


def _parse_instance_efficiency_row(line: str) -> dict[str, Any] | None:
    """Parse an Instance Efficiency Percentages row."""

    match = PERCENT_ROW_PATTERN.match(line)
    if not match:
        return None

    metric_name = match.group(1).strip()
    metric_value = _to_float(match.group(2))
    if not metric_name or metric_value is None:
        return None

    return {
        "metric_name": metric_name,
        "metric_value": metric_value,
        "metric_unit": "percent",
        "metric_source_section": "cpu",
        "metric_group": "instance_efficiency",
    }


def _parse_host_cpu_values(line: str) -> list[dict[str, Any]]:
    """Parse the Host CPU numeric row into structured metrics."""

    match = HOST_CPU_VALUE_PATTERN.match(line)
    if not match:
        return []

    metric_names = (
        "begin",
        "end",
        "user",
        "system",
        "idle",
        "wio",
        "busy",
    )
    metric_values = [_to_float(value) for value in match.groups()]

    if any(value is None for value in metric_values):
        return []

    return [
        {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "metric_unit": "percent",
            "metric_source_section": "cpu",
            "metric_group": "host_cpu",
        }
        for metric_name, metric_value in zip(metric_names, metric_values, strict=True)
    ]


def _is_divider_line(line: str) -> bool:
    """Return True when a line is only a visual divider."""

    stripped_line = line.strip()
    if not stripped_line:
        return False

    return bool(re.fullmatch(r"[-=\s]+", stripped_line))


def _normalize_line(line: str) -> str:
    """Normalize a line for deterministic header detection."""

    return " ".join(line.strip().lower().split())


def _to_float(value: str) -> float | None:
    """Convert a numeric string to float, tolerating commas."""

    try:
        return float(value.replace(",", ""))
    except (AttributeError, ValueError):
        return None
