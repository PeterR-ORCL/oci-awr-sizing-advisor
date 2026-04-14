"""Registry-driven utilities for locating major sections within AWR reports."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TypedDict

from src.models.parse_diagnostics import ParseDiagnostics, UnknownParserElement
from src.parser.section_registry import AwrSectionDefinition, get_section_registry


class AwrSectionLocation(TypedDict):
    """Location metadata for a detected AWR report section."""

    start_line: int
    end_line: int
    matched_pattern: str


AwrSectionMap = dict[str, AwrSectionLocation]


@dataclass(frozen=True, slots=True)
class AwrSectionDetectionResult:
    """Canonical section detection result plus parse diagnostics."""

    sections_found: AwrSectionMap
    diagnostics: ParseDiagnostics


def locate_awr_sections(lines: list[str]) -> AwrSectionMap:
    """Compatibility wrapper returning only the canonical section map."""

    return locate_awr_sections_with_diagnostics(lines).sections_found


def locate_awr_sections_with_diagnostics(
    lines: list[str],
    source_file_name: str | None = None,
    source_file_path: str | None = None,
) -> AwrSectionDetectionResult:
    """Locate canonical sections and capture deterministic discovery diagnostics."""

    registry = get_section_registry()
    detections: list[tuple[str, int, str]] = []
    seen_sections: set[str] = set()

    for index, line in enumerate(lines, start=1):
        normalized_line = _normalize_line(line)
        if not normalized_line:
            continue

        for definition in registry:
            if definition.canonical_name in seen_sections:
                continue
            if (
                definition.canonical_name != "report_header"
                and not _looks_like_known_section_candidate(
                    lines,
                    index - 1,
                    normalized_line,
                    definition.aliases,
                )
            ):
                continue

            matched_pattern = _match_alias(normalized_line, definition.aliases)
            if matched_pattern is None:
                continue

            detections.append((definition.canonical_name, index, matched_pattern))
            seen_sections.add(definition.canonical_name)
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

    diagnostics = _build_parse_diagnostics(
        lines=lines,
        section_map=section_map,
        registry=registry,
        source_file_name=source_file_name,
        source_file_path=source_file_path,
    )
    return AwrSectionDetectionResult(
        sections_found=section_map,
        diagnostics=diagnostics,
    )


def _build_parse_diagnostics(
    lines: list[str],
    section_map: AwrSectionMap,
    registry: tuple[AwrSectionDefinition, ...],
    source_file_name: str | None,
    source_file_path: str | None,
) -> ParseDiagnostics:
    registry_names = [definition.canonical_name for definition in registry]
    normalized_lines = [_normalize_line(line) for line in lines]
    sections_found = list(section_map.keys())
    sections_missing = [
        section_name for section_name in registry_names if section_name not in section_map
    ]

    required_sections = [
        definition for definition in registry if definition.completeness_role == "required"
    ]
    optional_core_sections = [
        definition
        for definition in registry
        if definition.completeness_role == "optional_core"
    ]
    contextual_sections = [
        definition
        for definition in registry
        if definition.completeness_role == "optional_contextual"
    ]
    neutral_sections = [
        definition for definition in registry if definition.completeness_role == "neutral"
    ]
    annotation_sections = [
        definition for definition in registry if definition.section_kind == "annotation"
    ]

    required_missing = [
        definition.canonical_name
        for definition in required_sections
        if definition.canonical_name not in section_map
    ]
    optional_core_missing = [
        definition.canonical_name
        for definition in optional_core_sections
        if definition.canonical_name not in section_map
    ]
    contextual_relevant = [
        definition.canonical_name
        for definition in contextual_sections
        if _is_contextually_relevant(definition, section_map, lines, normalized_lines)
    ]
    contextual_missing = [
        section_name for section_name in contextual_relevant if section_name not in section_map
    ]
    synthetic_missing = [
        definition.canonical_name
        for definition in neutral_sections
        if definition.section_kind == "functional"
        and definition.canonical_name not in section_map
    ]
    annotation_found = [
        definition.canonical_name
        for definition in annotation_sections
        if definition.canonical_name in section_map
    ]
    annotation_missing = [
        definition.canonical_name
        for definition in annotation_sections
        if definition.canonical_name not in section_map
    ]
    unknown_sections = _detect_unknown_sections(
        lines=lines,
        section_map=section_map,
        source_file_name=source_file_name,
        source_file_path=source_file_path,
    )
    suppressed_heading_candidates = _detect_suppressed_heading_candidates(
        lines=lines,
        registry=registry,
        section_map=section_map,
        source_file_name=source_file_name,
        source_file_path=source_file_path,
    )

    core_sections = required_sections + optional_core_sections
    core_found_count = sum(
        1 for definition in core_sections if definition.canonical_name in section_map
    )
    core_section_count = len(core_sections)
    contextual_relevant_count = len(contextual_relevant)
    contextual_observed_count = sum(
        1 for section_name in contextual_relevant if section_name in section_map
    )
    observed_section_count = core_found_count + contextual_observed_count
    missing_section_count = (
        (core_section_count - core_found_count)
        + (contextual_relevant_count - contextual_observed_count)
    )
    denominator = observed_section_count + missing_section_count
    observed_rate = round(observed_section_count / denominator, 4) if denominator else None
    core_observed_rate = (
        round(core_found_count / core_section_count, 4) if core_section_count else None
    )
    contextual_observed_rate = (
        round(contextual_observed_count / contextual_relevant_count, 4)
        if contextual_relevant_count
        else None
    )

    if required_missing:
        parse_quality = "INCOMPLETE"
    elif unknown_sections:
        parse_quality = "PARTIAL"
    elif core_found_count == core_section_count and not contextual_missing:
        parse_quality = "COMPLETE"
    else:
        parse_quality = "PARTIAL"

    return ParseDiagnostics(
        source_file_name=source_file_name,
        source_file_path=source_file_path,
        sections_found=sections_found,
        sections_missing=sections_missing,
        required_sections_missing=required_missing,
        optional_sections_missing=optional_core_missing + contextual_missing,
        optional_core_sections_missing=optional_core_missing,
        contextual_sections_relevant=contextual_relevant,
        contextual_sections_missing=contextual_missing,
        synthetic_sections_missing=synthetic_missing,
        annotation_sections_found=annotation_found,
        annotation_sections_missing=annotation_missing,
        unknown_sections=unknown_sections,
        suppressed_heading_candidates=suppressed_heading_candidates,
        required_section_count=len(required_sections),
        optional_section_count=len(optional_core_sections) + len(contextual_sections),
        annotation_section_count=len(annotation_sections),
        observed_section_count=observed_section_count,
        missing_section_count=missing_section_count,
        observed_section_rate=observed_rate,
        core_section_count=core_section_count,
        core_section_observed_count=core_found_count,
        core_section_missing_count=core_section_count - core_found_count,
        core_section_observed_rate=core_observed_rate,
        contextual_section_count=len(contextual_sections),
        contextual_section_relevant_count=contextual_relevant_count,
        contextual_section_observed_count=contextual_observed_count,
        contextual_section_missing_count=contextual_relevant_count - contextual_observed_count,
        contextual_section_observed_rate=contextual_observed_rate,
        parse_completeness_ratio=observed_rate,
        parse_quality=parse_quality,
    )


def _detect_unknown_sections(
    lines: list[str],
    section_map: AwrSectionMap,
    source_file_name: str | None,
    source_file_path: str | None,
) -> list[UnknownParserElement]:
    known_start_lines = {
        bounds["start_line"]
        for bounds in section_map.values()
        if isinstance(bounds.get("start_line"), int)
    }
    unknown_sections: list[UnknownParserElement] = []

    for zero_index, line in enumerate(lines):
        line_number = zero_index + 1
        if line_number in known_start_lines:
            continue
        if not _looks_like_unknown_section_header(lines, zero_index):
            continue

        previous_context = [
            context_line.rstrip()
            for context_line in lines[max(0, zero_index - 2) : zero_index]
            if context_line.strip()
        ]
        following_context = [
            context_line.rstrip()
            for context_line in lines[zero_index + 1 : zero_index + 3]
            if context_line.strip()
        ]
        unknown_sections.append(
            UnknownParserElement(
                parser_stage="section_locator",
                raw_text=line.strip(),
                line_number=line_number,
                context_before=previous_context,
                context_after=following_context,
                source_file_name=source_file_name,
                source_file_path=source_file_path,
                classification_hint="header_candidate",
            )
        )

    return unknown_sections


def _detect_suppressed_heading_candidates(
    lines: list[str],
    registry: tuple[AwrSectionDefinition, ...],
    section_map: AwrSectionMap,
    source_file_name: str | None,
    source_file_path: str | None,
) -> list[UnknownParserElement]:
    known_start_lines = {
        bounds["start_line"]
        for bounds in section_map.values()
        if isinstance(bounds.get("start_line"), int)
    }
    suppressed: list[UnknownParserElement] = []

    for zero_index, line in enumerate(lines):
        line_number = zero_index + 1
        stripped_line = line.strip()
        if line_number in known_start_lines or not stripped_line.startswith("*"):
            continue

        normalized_line = _normalize_line(stripped_line)
        matched_pattern = None
        for definition in registry:
            matched_pattern = _match_alias(normalized_line, definition.aliases)
            if matched_pattern is not None:
                break
        if matched_pattern is None:
            continue

        previous_context = [
            context_line.rstrip()
            for context_line in lines[max(0, zero_index - 2) : zero_index]
            if context_line.strip()
        ]
        following_context = [
            context_line.rstrip()
            for context_line in lines[zero_index + 1 : zero_index + 3]
            if context_line.strip()
        ]
        suppressed.append(
            UnknownParserElement(
                parser_stage="section_locator",
                raw_text=stripped_line,
                line_number=line_number,
                context_before=previous_context,
                context_after=following_context,
                source_file_name=source_file_name,
                source_file_path=source_file_path,
                classification_hint="suppressed_toc_entry",
            )
        )

    return suppressed


def _is_contextually_relevant(
    definition: AwrSectionDefinition,
    section_map: AwrSectionMap,
    lines: list[str],
    normalized_lines: list[str],
) -> bool:
    if definition.canonical_name == "cluster":
        return _has_strong_cluster_context(normalized_lines)
    if definition.canonical_name == "dataguard":
        return _has_strong_dataguard_context(lines)
    if definition.canonical_name in section_map:
        return True
    return any(_match_alias(line, definition.aliases) for line in normalized_lines)


def _has_strong_cluster_context(normalized_lines: list[str]) -> bool:
    strong_markers = (
        "gc cr request",
        "gc current block busy",
        "gc buffer busy acquire",
        "ges message buffer allocation",
        "cluster wait",
        "cache fusion",
    )
    return any(any(marker in line for marker in strong_markers) for line in normalized_lines)


def _has_strong_dataguard_context(lines: list[str]) -> bool:
    lag_pattern = re.compile(r"^(Transport Lag|Apply Lag)\s+(?!00:00:00)(\S+)")
    for line in lines:
        stripped_line = line.strip()
        if lag_pattern.search(stripped_line):
            return True
    return False


def _looks_like_unknown_section_header(lines: list[str], zero_index: int) -> bool:
    return _looks_like_section_header_candidate(lines, zero_index)


def _looks_like_known_section_candidate(
    lines: list[str],
    zero_index: int,
    normalized_line: str,
    aliases: tuple[str, ...],
) -> bool:
    line = lines[zero_index].strip()
    if not line or _is_separator_line(line):
        return False
    if line.startswith("*"):
        return False
    if not re.search(r"[a-zA-Z]", line):
        return False

    next_nonblank = _find_next_nonblank_line(lines, zero_index + 1)
    if next_nonblank is not None and _is_separator_line(next_nonblank):
        return True

    if len(normalized_line.split()) > 12:
        return False

    for alias in aliases:
        normalized_alias = _normalize_line(alias)
        if not normalized_alias:
            continue
        if normalized_line == normalized_alias:
            return True
        if normalized_line.startswith(f"{normalized_alias} "):
            return True
        if normalized_line.endswith(f" {normalized_alias}"):
            return True

    return False


def _looks_like_section_header_candidate(lines: list[str], zero_index: int) -> bool:
    line = lines[zero_index].strip()
    if not line or _is_separator_line(line):
        return False

    normalized_line = _normalize_line(line)
    if len(normalized_line) < 4:
        return False
    if len(normalized_line.split()) > 10:
        return False
    if re.search(r"\s{2,}", line):
        return False
    if not re.search(r"[a-zA-Z]", line):
        return False

    next_nonblank = _find_next_nonblank_line(lines, zero_index + 1)
    if next_nonblank is None or not _is_separator_line(next_nonblank):
        return False

    return True


def _find_next_nonblank_line(lines: list[str], start_index: int) -> str | None:
    for line in lines[start_index:]:
        if line.strip():
            return line
    return None


def _match_alias(normalized_line: str, aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        normalized_alias = _normalize_line(alias)
        if normalized_alias and normalized_alias in normalized_line:
            return alias
    return None


def _is_separator_line(line: str) -> bool:
    stripped_line = line.strip()
    if not stripped_line:
        return False
    return bool(re.fullmatch(r"[~=\-\s]+", stripped_line))


def _normalize_line(line: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", line.strip().lower()).split())
