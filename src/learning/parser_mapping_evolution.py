"""Proposal-only Phase 7Q parser mapping evolution model.

Parser mapping evolution records describe proposed parser mapping changes that
originate from validated parser materialization artifacts. They do not import,
mutate, activate, or otherwise influence runtime parser behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from src.learning.materialization_artifact import (
    MATERIALIZED,
    PARSER_MAPPING_ARTIFACT,
    VALIDATED as MATERIALIZATION_VALIDATED,
    MaterializationArtifact,
    MaterializationArtifactError,
    is_runtime_sensitive_artifact_type,
    materialization_artifact_from_dict,
    validate_materialization_artifact,
)


NEW_SECTION_MAPPING = "new_section_mapping"
SECTION_MAPPING_REFINEMENT = "section_mapping_refinement"
UNKNOWN_SIGNAL_MAPPING = "unknown_signal_mapping"
REGEX_PATTERN_REVIEW = "regex_pattern_review"
NORMALIZATION_RULE_REVIEW = "normalization_rule_review"
FIELD_EXTRACTION_REVIEW = "field_extraction_review"
UNIT_CONVERSION_REVIEW = "unit_conversion_review"
PARSER_CONFIDENCE_METADATA_REVIEW = "parser_confidence_metadata_review"
SECTION_REGISTRY_REVIEW = "section_registry_review"
PARSER_REGRESSION_TEST_ADDITION = "parser_regression_test_addition"

PARSER_EVOLUTION_TYPES = (
    NEW_SECTION_MAPPING,
    SECTION_MAPPING_REFINEMENT,
    UNKNOWN_SIGNAL_MAPPING,
    REGEX_PATTERN_REVIEW,
    NORMALIZATION_RULE_REVIEW,
    FIELD_EXTRACTION_REVIEW,
    UNIT_CONVERSION_REVIEW,
    PARSER_CONFIDENCE_METADATA_REVIEW,
    SECTION_REGISTRY_REVIEW,
    PARSER_REGRESSION_TEST_ADDITION,
)

PARSER_CODE_CHANGE = "parser_code_change"
PARSER_CONFIG_CHANGE = "parser_config_change"
REGEX_MAPPING_CHANGE = "regex_mapping_change"
SECTION_REGISTRY_CHANGE = "section_registry_change"
NORMALIZATION_RULE_CHANGE = "normalization_rule_change"
FIELD_EXTRACTION_CHANGE = "field_extraction_change"
UNIT_CONVERSION_CHANGE = "unit_conversion_change"
TEST_ONLY_CHANGE = "test_only_change"
DOCUMENTATION_CHANGE = "documentation_change"

PARSER_CHANGE_TYPES = (
    PARSER_CODE_CHANGE,
    PARSER_CONFIG_CHANGE,
    REGEX_MAPPING_CHANGE,
    SECTION_REGISTRY_CHANGE,
    NORMALIZATION_RULE_CHANGE,
    FIELD_EXTRACTION_CHANGE,
    UNIT_CONVERSION_CHANGE,
    TEST_ONLY_CHANGE,
    DOCUMENTATION_CHANGE,
)

PROPOSED = "PROPOSED"
UNDER_REVIEW = "UNDER_REVIEW"
APPROVED_FOR_IMPLEMENTATION = "APPROVED_FOR_IMPLEMENTATION"
BACKLOG_CREATED = "BACKLOG_CREATED"
IMPLEMENTED = "IMPLEMENTED"
VALIDATED = "VALIDATED"
REJECTED = "REJECTED"
ROLLED_BACK = "ROLLED_BACK"
CLOSED = "CLOSED"

PARSER_EVOLUTION_STATUSES = (
    PROPOSED,
    UNDER_REVIEW,
    APPROVED_FOR_IMPLEMENTATION,
    BACKLOG_CREATED,
    IMPLEMENTED,
    VALIDATED,
    REJECTED,
    ROLLED_BACK,
    CLOSED,
)

REQUIRED_PARSER_VALIDATION_REQUIREMENTS = (
    "parser tests",
    "AWR regression validation",
    "Phase 4I contract validation",
    "unknown signal safety",
    "scoring regression check",
    "rollback plan",
    "deterministic runtime remains authoritative",
)

PARSER_MAPPING_EVOLUTION_FIELDS = (
    "evolution_id",
    "source_materialization_id",
    "source_candidate_id",
    "evolution_type",
    "parser_section",
    "signal_name",
    "affected_component",
    "proposed_mapping_summary",
    "proposed_parser_change_type",
    "proposed_mapping",
    "implementation_reference",
    "validation_requirements",
    "rollback_plan",
    "phase4i_contract_required",
    "awr_regression_required",
    "scoring_regression_required",
    "runtime_influence_requested",
    "runtime_influence_granted",
    "status",
    "actor",
    "created_at",
    "validation_reference",
    "source_evidence",
    "semantic_context",
)

PARSER_BACKLOG_ITEM_FIELDS = (
    "backlog_id",
    "source_evolution_id",
    "parser_section",
    "signal_name",
    "proposed_parser_change_type",
    "title",
    "description",
    "acceptance_criteria",
    "validation_requirements",
    "rollback_plan",
    "runtime_active",
    "runtime_influence_granted",
    "status",
    "actor",
    "source_materialization_id",
    "source_candidate_id",
)

_DEFAULT_CHANGE_TYPE_BY_EVOLUTION_TYPE = {
    NEW_SECTION_MAPPING: SECTION_REGISTRY_CHANGE,
    SECTION_MAPPING_REFINEMENT: SECTION_REGISTRY_CHANGE,
    UNKNOWN_SIGNAL_MAPPING: SECTION_REGISTRY_CHANGE,
    REGEX_PATTERN_REVIEW: REGEX_MAPPING_CHANGE,
    NORMALIZATION_RULE_REVIEW: NORMALIZATION_RULE_CHANGE,
    FIELD_EXTRACTION_REVIEW: FIELD_EXTRACTION_CHANGE,
    UNIT_CONVERSION_REVIEW: UNIT_CONVERSION_CHANGE,
    PARSER_CONFIDENCE_METADATA_REVIEW: PARSER_CONFIG_CHANGE,
    SECTION_REGISTRY_REVIEW: SECTION_REGISTRY_CHANGE,
    PARSER_REGRESSION_TEST_ADDITION: TEST_ONLY_CHANGE,
}

_EVOLUTION_TYPE_VALIDATION_REQUIREMENTS = {
    NEW_SECTION_MAPPING: ("section detection validation",),
    SECTION_MAPPING_REFINEMENT: ("old/new section comparison",),
    UNKNOWN_SIGNAL_MAPPING: ("unknown signal safety validation",),
    REGEX_PATTERN_REVIEW: ("regex regression validation",),
    NORMALIZATION_RULE_REVIEW: ("normalization regression validation",),
    FIELD_EXTRACTION_REVIEW: ("field extraction validation",),
    UNIT_CONVERSION_REVIEW: ("unit conversion validation",),
    PARSER_CONFIDENCE_METADATA_REVIEW: (
        "parser confidence metadata validation",
    ),
    SECTION_REGISTRY_REVIEW: ("registry compatibility validation",),
    PARSER_REGRESSION_TEST_ADDITION: ("test coverage validation",),
}

_BASE_VALIDATION_CONCEPTS = (
    ("parser", "test"),
    ("awr", "regression"),
    ("phase", "4i", "contract"),
    ("unknown", "signal", "safety"),
    ("scoring", "regression"),
    ("rollback", "plan"),
    ("deterministic", "runtime", "remains", "authoritative"),
)

_SOURCE_ARTIFACT_VALIDATION_CONCEPTS = (
    ("parser", "test"),
    ("awr", "regression"),
    ("phase", "4i", "contract"),
    ("unknown", "signal", "safety"),
    ("scoring", "regression"),
)

_EVOLUTION_TYPE_VALIDATION_CONCEPTS = {
    NEW_SECTION_MAPPING: (("section", "detection"),),
    SECTION_MAPPING_REFINEMENT: (("old", "new", "section", "comparison"),),
    UNKNOWN_SIGNAL_MAPPING: (("unknown", "signal", "safety", "validation"),),
    REGEX_PATTERN_REVIEW: (("regex", "regression"),),
    NORMALIZATION_RULE_REVIEW: (("normalization", "regression"),),
    FIELD_EXTRACTION_REVIEW: (("field", "extraction"),),
    UNIT_CONVERSION_REVIEW: (("unit", "conversion"),),
    PARSER_CONFIDENCE_METADATA_REVIEW: (("parser", "confidence", "metadata"),),
    SECTION_REGISTRY_REVIEW: (("registry", "compatibility"),),
    PARSER_REGRESSION_TEST_ADDITION: (("test", "coverage"),),
}


class ParserMappingEvolutionError(ValueError):
    """Raised when a Phase 7Q parser evolution violates proposal-only rules."""


@dataclass(frozen=True)
class ParserMappingEvolution:
    """Serializable proposal-only parser mapping evolution record."""

    evolution_id: str
    source_materialization_id: str
    source_candidate_id: str
    evolution_type: str
    parser_section: str | None
    signal_name: str | None
    affected_component: str | None
    proposed_mapping_summary: str
    proposed_parser_change_type: str
    proposed_mapping: dict[str, object]
    implementation_reference: str | None
    validation_requirements: list[str]
    rollback_plan: str
    phase4i_contract_required: bool = True
    awr_regression_required: bool = True
    scoring_regression_required: bool = True
    runtime_influence_requested: bool = False
    runtime_influence_granted: bool = False
    status: str = PROPOSED
    actor: str = ""
    created_at: str | None = None
    validation_reference: str | None = None
    source_evidence: list[dict[str, object]] = field(default_factory=list)
    semantic_context: dict[str, object] | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.evolution_id, "evolution_id")
        _require_non_empty_string(
            self.source_materialization_id,
            "source_materialization_id",
        )
        _require_non_empty_string(self.source_candidate_id, "source_candidate_id")
        _validate_evolution_type(self.evolution_type)
        _validate_optional_string(self.parser_section, "parser_section")
        _validate_optional_string(self.signal_name, "signal_name")
        _validate_optional_string(self.affected_component, "affected_component")
        _require_non_empty_string(
            self.proposed_mapping_summary,
            "proposed_mapping_summary",
        )
        _validate_parser_change_type(self.proposed_parser_change_type)
        _validate_optional_string(
            self.implementation_reference,
            "implementation_reference",
        )
        _require_non_empty_string(self.rollback_plan, "rollback_plan")
        _validate_status(self.status)
        _require_non_empty_string(self.actor, "actor")
        _validate_optional_string(self.created_at, "created_at")
        _validate_optional_string(self.validation_reference, "validation_reference")

        if self.phase4i_contract_required is not True:
            raise ParserMappingEvolutionError(
                "phase4i_contract_required must be true for parser evolution."
            )
        if self.awr_regression_required is not True:
            raise ParserMappingEvolutionError(
                "awr_regression_required must be true for parser evolution."
            )
        if self.scoring_regression_required is not True:
            raise ParserMappingEvolutionError(
                "scoring_regression_required must be true for parser evolution."
            )
        if not isinstance(self.runtime_influence_requested, bool):
            raise ParserMappingEvolutionError(
                "runtime_influence_requested must be a bool."
            )
        if self.runtime_influence_granted is not False:
            raise ParserMappingEvolutionError(
                "Phase 7Q parser mapping evolution cannot grant runtime influence."
            )

        proposed_mapping = _normalize_object_mapping(
            self.proposed_mapping,
            "proposed_mapping",
            allow_empty=False,
        )
        object.__setattr__(self, "proposed_mapping", proposed_mapping)

        requirements = _normalize_validation_requirements(self.validation_requirements)
        _validate_parser_validation_concepts(self.evolution_type, requirements)
        object.__setattr__(self, "validation_requirements", requirements)
        object.__setattr__(
            self,
            "source_evidence",
            _normalize_source_evidence(self.source_evidence),
        )
        object.__setattr__(
            self,
            "semantic_context",
            _normalize_optional_object_mapping(self.semantic_context, "semantic_context"),
        )
        object.__setattr__(self, "phase4i_contract_required", True)
        object.__setattr__(self, "awr_regression_required", True)
        object.__setattr__(self, "scoring_regression_required", True)
        object.__setattr__(self, "runtime_influence_granted", False)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic serializable dictionary for this evolution."""

        return {
            field_name: deepcopy(getattr(self, field_name))
            for field_name in PARSER_MAPPING_EVOLUTION_FIELDS
        }


@dataclass(frozen=True)
class ParserBacklogItem:
    """Inactive parser backlog work item derived from parser evolution."""

    backlog_id: str
    source_evolution_id: str
    parser_section: str | None
    signal_name: str | None
    proposed_parser_change_type: str
    title: str
    description: str
    acceptance_criteria: list[str]
    validation_requirements: list[str]
    rollback_plan: str
    runtime_active: bool = False
    runtime_influence_granted: bool = False
    status: str = PROPOSED
    actor: str = ""
    source_materialization_id: str | None = None
    source_candidate_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.backlog_id, "backlog_id")
        _require_non_empty_string(self.source_evolution_id, "source_evolution_id")
        _validate_optional_string(self.parser_section, "parser_section")
        _validate_optional_string(self.signal_name, "signal_name")
        _validate_parser_change_type(self.proposed_parser_change_type)
        _require_non_empty_string(self.title, "title")
        _require_non_empty_string(self.description, "description")
        _require_non_empty_string(self.rollback_plan, "rollback_plan")
        _validate_status(self.status)
        _require_non_empty_string(self.actor, "actor")
        _validate_optional_string(
            self.source_materialization_id,
            "source_materialization_id",
        )
        _validate_optional_string(self.source_candidate_id, "source_candidate_id")
        if self.runtime_active is not False:
            raise ParserMappingEvolutionError(
                "Phase 7Q parser backlog items cannot be runtime active."
            )
        if self.runtime_influence_granted is not False:
            raise ParserMappingEvolutionError(
                "Phase 7Q parser backlog items cannot grant runtime influence."
            )

        acceptance_criteria = _normalize_string_list(
            self.acceptance_criteria,
            "acceptance_criteria",
        )
        object.__setattr__(self, "acceptance_criteria", acceptance_criteria)

        requirements = _normalize_validation_requirements(self.validation_requirements)
        _validate_required_concepts(
            requirements,
            _BASE_VALIDATION_CONCEPTS,
            "validation_requirements",
        )
        object.__setattr__(self, "validation_requirements", requirements)
        object.__setattr__(self, "runtime_active", False)
        object.__setattr__(self, "runtime_influence_granted", False)

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic serializable dictionary for this backlog item."""

        return {
            field_name: deepcopy(getattr(self, field_name))
            for field_name in PARSER_BACKLOG_ITEM_FIELDS
        }


def create_parser_mapping_evolution(
    materialization_artifact: MaterializationArtifact | Mapping[str, Any],
    actor: str,
    evolution_type: str,
    proposed_mapping: Mapping[str, Any],
    proposed_mapping_summary: str,
    parser_section: str | None = None,
    signal_name: str | None = None,
    proposed_parser_change_type: str | None = None,
    implementation_reference: str | None = None,
    validation_requirements: Sequence[str] | None = None,
    rollback_plan: str | None = None,
    runtime_influence_requested: bool = False,
) -> ParserMappingEvolution:
    """Create an inactive parser evolution from a parser materialization artifact."""

    source = _coerce_source_artifact(materialization_artifact)
    _validate_source_artifact_for_evolution(source)
    _require_non_empty_string(actor, "actor")
    _validate_evolution_type(evolution_type)
    _require_non_empty_string(proposed_mapping_summary, "proposed_mapping_summary")
    _require_non_empty_string(rollback_plan, "rollback_plan")
    mapping_payload = _normalize_object_mapping(
        proposed_mapping,
        "proposed_mapping",
        allow_empty=False,
    )
    change_type = (
        _DEFAULT_CHANGE_TYPE_BY_EVOLUTION_TYPE[evolution_type]
        if proposed_parser_change_type is None
        else proposed_parser_change_type
    )
    _validate_parser_change_type(change_type)

    requirements = (
        required_parser_validation_requirements(evolution_type)
        if validation_requirements is None
        else list(validation_requirements)
    )

    evolution = ParserMappingEvolution(
        evolution_id=create_parser_evolution_id(
            source.materialization_id,
            evolution_type,
            parser_section=parser_section,
            signal_name=signal_name,
        ),
        source_materialization_id=source.materialization_id,
        source_candidate_id=source.source_candidate_id,
        evolution_type=evolution_type,
        parser_section=parser_section,
        signal_name=signal_name,
        affected_component=source.affected_component,
        proposed_mapping_summary=proposed_mapping_summary,
        proposed_parser_change_type=change_type,
        proposed_mapping=deepcopy(mapping_payload),
        implementation_reference=implementation_reference,
        validation_requirements=requirements,
        rollback_plan="" if rollback_plan is None else rollback_plan,
        phase4i_contract_required=True,
        awr_regression_required=True,
        scoring_regression_required=True,
        runtime_influence_requested=runtime_influence_requested,
        runtime_influence_granted=False,
        status=PROPOSED,
        actor=actor,
        created_at=None,
        validation_reference=None,
        source_evidence=deepcopy(source.source_evidence),
        semantic_context=deepcopy(source.semantic_context),
    )
    return validate_parser_mapping_evolution(evolution)


def validate_parser_mapping_evolution(
    evolution: ParserMappingEvolution,
) -> ParserMappingEvolution:
    """Validate and return a parser evolution without activating runtime."""

    if not isinstance(evolution, ParserMappingEvolution):
        raise ParserMappingEvolutionError(
            "evolution must be a ParserMappingEvolution."
        )
    ParserMappingEvolution(**evolution.to_dict())
    return evolution


def parser_mapping_evolution_to_dict(
    evolution: ParserMappingEvolution,
) -> dict[str, Any]:
    """Return a deterministic dictionary for one parser evolution."""

    return validate_parser_mapping_evolution(evolution).to_dict()


def parser_mapping_evolution_from_dict(
    data: Mapping[str, Any],
) -> ParserMappingEvolution:
    """Reconstruct and validate one parser evolution from dictionary data."""

    if not isinstance(data, Mapping):
        raise ParserMappingEvolutionError("evolution data must be a mapping.")
    missing = [
        field_name
        for field_name in (
            "evolution_id",
            "source_materialization_id",
            "source_candidate_id",
            "evolution_type",
            "proposed_mapping_summary",
            "proposed_parser_change_type",
            "proposed_mapping",
            "validation_requirements",
            "rollback_plan",
            "actor",
        )
        if field_name not in data
    ]
    if missing:
        raise ParserMappingEvolutionError(
            f"Missing parser mapping evolution fields: {', '.join(missing)}."
        )
    values = {
        field_name: deepcopy(data[field_name])
        for field_name in PARSER_MAPPING_EVOLUTION_FIELDS
        if field_name in data
    }
    return ParserMappingEvolution(**values)


def parser_mapping_evolutions_to_dicts(
    evolutions: Sequence[ParserMappingEvolution],
) -> list[dict[str, Any]]:
    """Return deterministic dictionaries for parser evolutions."""

    return [parser_mapping_evolution_to_dict(evolution) for evolution in evolutions]


def create_parser_evolution_id(
    materialization_id: str,
    evolution_type: str,
    parser_section: str | None = None,
    signal_name: str | None = None,
) -> str:
    """Create a deterministic parser evolution identifier from stable inputs."""

    _require_non_empty_string(materialization_id, "materialization_id")
    _validate_evolution_type(evolution_type)
    return (
        f"PARSER-EVO-{_identifier_fragment(evolution_type)}-"
        f"{_identifier_fragment(materialization_id)}-"
        f"{_identifier_fragment(parser_section or 'unspecified')}-"
        f"{_identifier_fragment(signal_name or 'unspecified')}"
    )


def create_parser_backlog_item(
    evolution: ParserMappingEvolution,
    title: str | None = None,
    description: str | None = None,
) -> ParserBacklogItem:
    """Create an inactive parser backlog item from parser evolution."""

    evolution = validate_parser_mapping_evolution(evolution)
    item = ParserBacklogItem(
        backlog_id=_create_parser_backlog_id(evolution.evolution_id),
        source_evolution_id=evolution.evolution_id,
        parser_section=evolution.parser_section,
        signal_name=evolution.signal_name,
        proposed_parser_change_type=evolution.proposed_parser_change_type,
        title=title
        or f"Review {evolution.evolution_type} parser mapping proposal",
        description=description or evolution.proposed_mapping_summary,
        acceptance_criteria=[
            "parser tests pass",
            "AWR regression validation completed",
            "Phase 4I contract validation completed",
            "unknown signal safety validation completed",
            "scoring regression check completed",
            "rollback plan reviewed",
            "deterministic runtime remains authoritative",
        ],
        validation_requirements=deepcopy(evolution.validation_requirements),
        rollback_plan=evolution.rollback_plan,
        runtime_active=False,
        runtime_influence_granted=False,
        status=PROPOSED,
        actor=evolution.actor,
        source_materialization_id=evolution.source_materialization_id,
        source_candidate_id=evolution.source_candidate_id,
    )
    return validate_parser_backlog_item(item)


def validate_parser_backlog_item(item: ParserBacklogItem) -> ParserBacklogItem:
    """Validate and return a parser backlog item without activating runtime."""

    if not isinstance(item, ParserBacklogItem):
        raise ParserMappingEvolutionError("item must be a ParserBacklogItem.")
    ParserBacklogItem(**item.to_dict())
    return item


def parser_backlog_item_to_dict(item: ParserBacklogItem) -> dict[str, Any]:
    """Return a deterministic dictionary for one parser backlog item."""

    return validate_parser_backlog_item(item).to_dict()


def parser_backlog_item_from_dict(data: Mapping[str, Any]) -> ParserBacklogItem:
    """Reconstruct and validate one parser backlog item from dictionary data."""

    if not isinstance(data, Mapping):
        raise ParserMappingEvolutionError("backlog item data must be a mapping.")
    missing = [
        field_name
        for field_name in (
            "backlog_id",
            "source_evolution_id",
            "proposed_parser_change_type",
            "title",
            "description",
            "acceptance_criteria",
            "validation_requirements",
            "rollback_plan",
            "actor",
        )
        if field_name not in data
    ]
    if missing:
        raise ParserMappingEvolutionError(
            f"Missing parser backlog item fields: {', '.join(missing)}."
        )
    values = {
        field_name: deepcopy(data[field_name])
        for field_name in PARSER_BACKLOG_ITEM_FIELDS
        if field_name in data
    }
    return ParserBacklogItem(**values)


def parser_backlog_items_to_dicts(
    items: Sequence[ParserBacklogItem],
) -> list[dict[str, Any]]:
    """Return deterministic dictionaries for parser backlog items."""

    return [parser_backlog_item_to_dict(item) for item in items]


def required_parser_validation_requirements(evolution_type: str) -> list[str]:
    """Return required parser validation requirements for one evolution type."""

    _validate_evolution_type(evolution_type)
    requirements = list(REQUIRED_PARSER_VALIDATION_REQUIREMENTS)
    requirements.extend(_EVOLUTION_TYPE_VALIDATION_REQUIREMENTS[evolution_type])
    return requirements


def is_supported_parser_evolution_type(evolution_type: str) -> bool:
    """Return True when evolution_type is supported by Phase 7Q."""

    return evolution_type in PARSER_EVOLUTION_TYPES


def is_supported_parser_change_type(change_type: str) -> bool:
    """Return True when change_type is supported by Phase 7Q."""

    return change_type in PARSER_CHANGE_TYPES


def _coerce_source_artifact(
    materialization_artifact: MaterializationArtifact | Mapping[str, Any],
) -> MaterializationArtifact:
    if isinstance(materialization_artifact, MaterializationArtifact):
        source = materialization_artifact
    elif isinstance(materialization_artifact, Mapping):
        try:
            source = materialization_artifact_from_dict(materialization_artifact)
        except MaterializationArtifactError as exc:
            raise ParserMappingEvolutionError(str(exc)) from exc
    else:
        raise ParserMappingEvolutionError(
            "materialization_artifact must be a MaterializationArtifact or mapping."
        )

    try:
        return validate_materialization_artifact(source)
    except MaterializationArtifactError as exc:
        raise ParserMappingEvolutionError(str(exc)) from exc


def _validate_source_artifact_for_evolution(source: MaterializationArtifact) -> None:
    if source.proposed_artifact_type != PARSER_MAPPING_ARTIFACT:
        raise ParserMappingEvolutionError(
            "Parser mapping evolution requires a parser_mapping_artifact source."
        )
    if not is_runtime_sensitive_artifact_type(source.proposed_artifact_type):
        raise ParserMappingEvolutionError(
            "Parser mapping evolution source artifact must be runtime-sensitive."
        )
    if source.runtime_influence_granted is not False:
        raise ParserMappingEvolutionError(
            "Parser mapping evolution source cannot have runtime influence granted."
        )
    if source.status not in (MATERIALIZED, MATERIALIZATION_VALIDATED):
        raise ParserMappingEvolutionError(
            "Parser mapping evolution source must be MATERIALIZED or VALIDATED."
        )
    _validate_required_concepts(
        source.validation_requirements,
        _SOURCE_ARTIFACT_VALIDATION_CONCEPTS,
        "source artifact validation_requirements",
    )


def _create_parser_backlog_id(source_evolution_id: str) -> str:
    _require_non_empty_string(source_evolution_id, "source_evolution_id")
    return f"PARSER-BACKLOG-{_identifier_fragment(source_evolution_id)}"


def _validate_parser_validation_concepts(
    evolution_type: str,
    requirements: Sequence[str],
) -> None:
    concepts = list(_BASE_VALIDATION_CONCEPTS)
    concepts.extend(_EVOLUTION_TYPE_VALIDATION_CONCEPTS[evolution_type])
    _validate_required_concepts(requirements, concepts, "validation_requirements")


def _validate_evolution_type(evolution_type: Any) -> None:
    if evolution_type not in PARSER_EVOLUTION_TYPES:
        raise ParserMappingEvolutionError(
            f"Unsupported parser evolution type: {evolution_type!r}."
        )


def _validate_parser_change_type(change_type: Any) -> None:
    if change_type not in PARSER_CHANGE_TYPES:
        raise ParserMappingEvolutionError(
            f"Unsupported parser change type: {change_type!r}."
        )


def _validate_status(status: Any) -> None:
    if status not in PARSER_EVOLUTION_STATUSES:
        raise ParserMappingEvolutionError(f"Unsupported parser evolution status: {status!r}.")


def _normalize_validation_requirements(requirements: Any) -> list[str]:
    return _normalize_string_list(requirements, "validation_requirements")


def _normalize_string_list(values: Any, field_name: str) -> list[str]:
    if not isinstance(values, list):
        raise ParserMappingEvolutionError(f"{field_name} must be a list.")
    if not values:
        raise ParserMappingEvolutionError(f"{field_name} must not be empty.")
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ParserMappingEvolutionError(
                f"{field_name} must contain non-empty strings."
            )
        normalized.append(value.strip())
    return normalized


def _normalize_source_evidence(source_evidence: Any) -> list[dict[str, object]]:
    if source_evidence is None:
        return []
    if not isinstance(source_evidence, list):
        raise ParserMappingEvolutionError("source_evidence must be a list.")
    normalized: list[dict[str, object]] = []
    for item in source_evidence:
        if not isinstance(item, Mapping):
            raise ParserMappingEvolutionError(
                "source_evidence must contain mapping objects only."
            )
        normalized.append(deepcopy(dict(item)))
    return normalized


def _normalize_object_mapping(
    data: Any,
    field_name: str,
    allow_empty: bool = True,
) -> dict[str, object]:
    if data is None:
        data = {}
    if not isinstance(data, Mapping):
        raise ParserMappingEvolutionError(f"{field_name} must be a mapping.")
    normalized = deepcopy(dict(data))
    if not allow_empty and not normalized:
        raise ParserMappingEvolutionError(f"{field_name} must not be empty.")
    return normalized


def _normalize_optional_object_mapping(
    data: Any,
    field_name: str,
) -> dict[str, object] | None:
    if data is None:
        return None
    return _normalize_object_mapping(data, field_name)


def _require_non_empty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ParserMappingEvolutionError(f"{field_name} must be a non-empty string.")


def _validate_optional_string(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise ParserMappingEvolutionError(f"{field_name} must be None or a string.")
    if isinstance(value, str) and not value.strip():
        raise ParserMappingEvolutionError(f"{field_name} must not be blank.")


def _validate_required_concepts(
    requirements: Sequence[str],
    concepts: Sequence[Sequence[str]],
    field_name: str,
) -> None:
    normalized_requirements = [_normalize_text(requirement) for requirement in requirements]
    for concept in concepts:
        if not any(
            all(token in normalized_requirement for token in concept)
            for normalized_requirement in normalized_requirements
        ):
            raise ParserMappingEvolutionError(
                f"{field_name} missing required concept: {' '.join(concept)}."
            )


def _identifier_fragment(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "UNSPECIFIED"


def _normalize_text(value: str) -> str:
    text = value.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()
