"""Deterministic parse diagnostics and unknown parser element models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class UnknownParserElement:
    """Structured record for text the deterministic parser did not classify."""

    parser_stage: str
    raw_text: str
    line_number: int | None = None
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    source_file_name: str | None = None
    source_file_path: str | None = None
    classification_hint: str | None = None


@dataclass(slots=True)
class ParseDiagnostics:
    """Machine-readable diagnostics emitted by the deterministic parser."""

    source_file_name: str | None = None
    source_file_path: str | None = None
    sections_found: list[str] = field(default_factory=list)
    sections_missing: list[str] = field(default_factory=list)
    required_sections_missing: list[str] = field(default_factory=list)
    optional_sections_missing: list[str] = field(default_factory=list)
    optional_core_sections_missing: list[str] = field(default_factory=list)
    contextual_sections_relevant: list[str] = field(default_factory=list)
    contextual_sections_missing: list[str] = field(default_factory=list)
    synthetic_sections_missing: list[str] = field(default_factory=list)
    annotation_sections_found: list[str] = field(default_factory=list)
    annotation_sections_missing: list[str] = field(default_factory=list)
    unknown_sections: list[UnknownParserElement] = field(default_factory=list)
    suppressed_heading_candidates: list[UnknownParserElement] = field(default_factory=list)
    required_section_count: int = 0
    optional_section_count: int = 0
    annotation_section_count: int = 0
    observed_section_count: int = 0
    missing_section_count: int = 0
    observed_section_rate: float | None = None
    core_section_count: int = 0
    core_section_observed_count: int = 0
    core_section_missing_count: int = 0
    core_section_observed_rate: float | None = None
    contextual_section_count: int = 0
    contextual_section_relevant_count: int = 0
    contextual_section_observed_count: int = 0
    contextual_section_missing_count: int = 0
    contextual_section_observed_rate: float | None = None
    parse_completeness_ratio: float | None = None
    parse_quality: str | None = None

    def to_warning_messages(self) -> list[str]:
        """Return concise warning strings derived from diagnostics."""

        warnings: list[str] = []
        for section_name in self.required_sections_missing:
            warnings.append(f"Required section not found: {section_name}")
        for section_name in self.optional_sections_missing:
            warnings.append(f"Optional section not found: {section_name}")
        for unknown_section in self.unknown_sections:
            location = (
                f"line {unknown_section.line_number}"
                if unknown_section.line_number is not None
                else "unknown line"
            )
            warnings.append(
                f"Unknown section header detected at {location}: {unknown_section.raw_text}"
            )
        return warnings
