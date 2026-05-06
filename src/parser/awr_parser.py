"""Day 2 orchestration for parsing Oracle AWR report files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.models.parse_result import ParseResult
from src.models.run_metadata import RunMetadata
from src.parser.awr_file_loader import load_awr_file
from src.parser.ash_parser import parse_ash_samples
from src.parser.awr_section_locator import (
    AwrSectionLocation,
    locate_awr_sections_with_diagnostics,
)
from src.parser.cpu_parser import parse_cpu_section
from src.parser.datafile_io_parser import parse_datafile_io_stats
from src.parser.event_histogram_parser import parse_event_histograms
from src.parser.instance_activity_parser import parse_instance_activity_stats
from src.parser.metadata_parser import parse_awr_metadata
from src.parser.pga_advisory_parser import parse_pga_advisory
from src.parser.sql_parser import parse_sql_section
from src.parser.tablespace_io_parser import parse_tablespace_io_stats
from src.parser.topology_parser import parse_topology_signals
from src.parser.waits_parser import parse_waits_section
from src.parser.workarea_histogram_parser import parse_workarea_histogram


def parse_awr_file(file_path: str | Path) -> ParseResult:
    """Parse an Oracle AWR report file into the canonical Day 1 result.

    The orchestrator loads the source file, locates major sections,
    extracts run-level metadata, parses currently supported Day 2 metric
    sections, and assembles a deterministic ``ParseResult``.

    Args:
        file_path: Path to the Oracle AWR report file.

    Returns:
        A canonical ``ParseResult`` object for the provided file.

    Raises:
        FileNotFoundError: If the source file does not exist.
        IsADirectoryError: If the provided path is not a file.
        AwrFileLoaderError: If the file cannot be read or decoded.
    """

    loaded_file = load_awr_file(file_path)
    lines = loaded_file["lines"]
    section_detection = locate_awr_sections_with_diagnostics(
        loaded_file["lines"],
        source_file_name=loaded_file["file_name"],
        source_file_path=loaded_file["file_path"],
    )
    sections_found = section_detection.sections_found
    parse_diagnostics = section_detection.diagnostics

    metadata_dict, metadata_warnings = parse_awr_metadata(
        file_path=loaded_file["file_path"],
        file_name=loaded_file["file_name"],
        lines=lines,
        report_header=sections_found.get("report_header"),
    )

    run_metadata = RunMetadata(**metadata_dict)
    cpu_lines = _slice_section_lines(lines, sections_found.get("cpu"))
    waits_lines = _slice_section_lines(lines, sections_found.get("waits"))
    top_sql_lines = _slice_section_lines(lines, sections_found.get("top_sql"))
    workload_note_lines = _slice_section_lines(
        lines, sections_found.get("workload_note")
    )
    anomaly_flag_lines = _slice_section_lines(
        lines, sections_found.get("anomaly_flags")
    )

    cpu_metrics = parse_cpu_section(cpu_lines) if cpu_lines else []
    wait_events = parse_waits_section(waits_lines) if waits_lines else []
    top_sql = parse_sql_section(top_sql_lines) if top_sql_lines else []
    instance_activity_stats = parse_instance_activity_stats(lines)
    datafile_io_stats = parse_datafile_io_stats(lines)
    tablespace_io_stats = parse_tablespace_io_stats(lines)
    pga_advisory = parse_pga_advisory(lines)
    workarea_histogram = parse_workarea_histogram(lines)
    event_histograms = parse_event_histograms(lines)
    ash_samples = parse_ash_samples(lines)
    workload_notes = _extract_annotation_content(workload_note_lines)
    anomaly_flags = _extract_annotation_content(anomaly_flag_lines)
    topology_signals = parse_topology_signals(
        lines=lines,
        wait_events=wait_events,
        metadata=dict(metadata_dict),
    )

    return ParseResult(
        run_metadata=run_metadata,
        sections_found=sections_found,
        cpu_metrics=cpu_metrics,
        io_metrics=[],
        wait_events=wait_events,
        top_sql=top_sql,
        instance_activity_stats=instance_activity_stats,
        datafile_io_stats=datafile_io_stats,
        tablespace_io_stats=tablespace_io_stats,
        pga_advisory=pga_advisory,
        workarea_histogram=workarea_histogram,
        event_histograms=event_histograms,
        ash_samples=ash_samples,
        session_metrics=[],
        topology_signals=topology_signals,
        workload_notes=workload_notes,
        anomaly_flags=anomaly_flags,
        parse_diagnostics=parse_diagnostics,
        parse_warnings=(
            metadata_warnings + parse_diagnostics.to_warning_messages()
        ),
        parse_errors=[],
    )


def build_parser_result_contract(parse_result: ParseResult) -> dict[str, Any]:
    """Return a parser-boundary contract without changing extraction output.

    The canonical parser still returns ``ParseResult`` for existing runtime
    behavior. This adapter exposes the parser-facing responsibilities in a
    stable dictionary shape for orchestration, tests, and future UI adapters.
    It does not discover sources and does not mutate the parse result.
    """

    diagnostics = parse_result.parse_diagnostics
    sections_detected = list(
        diagnostics.sections_found or parse_result.sections_found.keys()
    )
    sections_missing = list(diagnostics.sections_missing)
    unknown_signals = [
        _unknown_parser_element_to_contract(unknown)
        for unknown in diagnostics.unknown_sections
    ]
    topology_hints = [
        key
        for key, value in sorted(parse_result.topology_signals.items())
        if value not in (None, "", [], {})
    ]
    platform_hints = [
        value
        for value in (
            parse_result.run_metadata.platform,
            parse_result.run_metadata.db_version,
        )
        if value
    ]
    parse_status = "PARSED_WITH_ERRORS" if parse_result.parse_errors else "PARSED"

    return {
        "file_name": parse_result.run_metadata.source_file_name,
        "parse_status": parse_status,
        "sections_detected": sections_detected,
        "sections_missing": sections_missing,
        "metrics": {
            "cpu_metrics": parse_result.cpu_metrics,
            "io_metrics": parse_result.io_metrics,
            "wait_events": parse_result.wait_events,
            "top_sql": parse_result.top_sql,
            "instance_activity_stats": parse_result.instance_activity_stats,
            "datafile_io_stats": parse_result.datafile_io_stats,
            "tablespace_io_stats": parse_result.tablespace_io_stats,
        },
        "topology_hints": topology_hints,
        "platform_hints": platform_hints,
        "parse_confidence": diagnostics.parse_completeness_ratio,
        "parser_notes": list(parse_result.parse_warnings),
        "unknown_signals": unknown_signals,
    }


def _unknown_parser_element_to_contract(unknown: Any) -> dict[str, Any]:
    return {
        "parser_stage": getattr(unknown, "parser_stage", None),
        "raw_text": getattr(unknown, "raw_text", None),
        "line_number": getattr(unknown, "line_number", None),
        "classification_hint": getattr(unknown, "classification_hint", None),
    }


def _slice_section_lines(
    lines: list[str],
    section_bounds: AwrSectionLocation | None,
) -> list[str]:
    """
    Return the lines for a detected section using inclusive 1-based
    bounds.
    """

    if not section_bounds:
        return []

    start_line = section_bounds.get("start_line")
    end_line = section_bounds.get("end_line")
    if not isinstance(start_line, int) or not isinstance(end_line, int):
        return []

    if start_line < 1 or end_line < start_line:
        return []

    return lines[start_line - 1:end_line]


def _extract_annotation_content(lines: list[str]) -> list[str]:
    """
    Return non-header, non-divider content lines for a lightweight
    annotation section.
    """

    if not lines:
        return []

    content_lines: list[str] = []
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if not stripped_line:
            continue
        if index == 0:
            continue
        if _is_section_divider(stripped_line):
            continue
        if stripped_line.lower() == "end of report":
            continue
        content_lines.append(stripped_line)
    return content_lines


def _is_section_divider(line: str) -> bool:
    stripped_line = line.strip()
    if not stripped_line:
        return False
    return all(character in {"~", "-", "="} for character in stripped_line)
