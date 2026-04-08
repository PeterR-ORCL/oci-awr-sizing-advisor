"""Data model for canonical Day 1 AWR parse results."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.models.run_metadata import RunMetadata
from src.parser.awr_section_locator import AwrSectionMap


@dataclass(slots=True)
class ParseResult:
    """Canonical parse result container for the Day 1 parser foundation."""

    run_metadata: RunMetadata
    sections_found: AwrSectionMap = field(default_factory=dict)
    cpu_metrics: list[dict[str, Any]] = field(default_factory=list)
    io_metrics: list[dict[str, Any]] = field(default_factory=list)
    wait_events: list[dict[str, Any]] = field(default_factory=list)
    top_sql: list[dict[str, Any]] = field(default_factory=list)
    instance_activity_stats: list[dict[str, Any]] = field(default_factory=list)
    datafile_io_stats: list[dict[str, Any]] = field(default_factory=list)
    tablespace_io_stats: list[dict[str, Any]] = field(default_factory=list)
    pga_advisory: dict[str, Any] = field(default_factory=dict)
    workarea_histogram: dict[str, Any] = field(default_factory=dict)
    event_histograms: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    ash_samples: list[dict[str, Any]] = field(default_factory=list)
    session_metrics: list[dict[str, Any]] = field(default_factory=list)
    topology_signals: dict[str, Any] = field(default_factory=dict)
    parse_warnings: list[str] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary representation."""

        return asdict(self)
