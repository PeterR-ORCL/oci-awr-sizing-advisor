"""Day 2 orchestration for parsing Oracle AWR report files."""

from __future__ import annotations

from pathlib import Path

from src.models.parse_result import ParseResult
from src.models.run_metadata import RunMetadata
from src.parser.awr_file_loader import load_awr_file
from src.parser.ash_parser import parse_ash_samples
from src.parser.cpu_parser import parse_cpu_section
from src.parser.awr_section_locator import locate_awr_sections
from src.parser.datafile_io_parser import parse_datafile_io_stats
from src.parser.event_histogram_parser import parse_event_histograms
from src.parser.metadata_parser import parse_awr_metadata
from src.parser.pga_advisory_parser import parse_pga_advisory
from src.parser.sql_parser import parse_sql_section
from src.parser.tablespace_io_parser import parse_tablespace_io_stats
from src.parser.waits_parser import parse_waits_section


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
    sections_found = locate_awr_sections(loaded_file["lines"])

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

    cpu_metrics = parse_cpu_section(cpu_lines) if cpu_lines else []
    wait_events = parse_waits_section(waits_lines) if waits_lines else []
    top_sql = parse_sql_section(top_sql_lines) if top_sql_lines else []
    datafile_io_stats = parse_datafile_io_stats(lines)
    tablespace_io_stats = parse_tablespace_io_stats(lines)
    pga_advisory = parse_pga_advisory(lines)
    event_histograms = parse_event_histograms(lines)
    ash_samples = parse_ash_samples(lines)

    return ParseResult(
        run_metadata=run_metadata,
        sections_found=sections_found,
        cpu_metrics=cpu_metrics,
        io_metrics=[],
        wait_events=wait_events,
        top_sql=top_sql,
        datafile_io_stats=datafile_io_stats,
        tablespace_io_stats=tablespace_io_stats,
        pga_advisory=pga_advisory,
        event_histograms=event_histograms,
        ash_samples=ash_samples,
        session_metrics=[],
        parse_warnings=metadata_warnings,
        parse_errors=[],
    )


def _slice_section_lines(
    lines: list[str],
    section_bounds: dict[str, int | str] | None,
) -> list[str]:
    """Return the lines for a detected section using inclusive 1-based bounds."""

    if not section_bounds:
        return []

    start_line = section_bounds.get("start_line")
    end_line = section_bounds.get("end_line")
    if not isinstance(start_line, int) or not isinstance(end_line, int):
        return []

    if start_line < 1 or end_line < start_line:
        return []

    return lines[start_line - 1 : end_line]
