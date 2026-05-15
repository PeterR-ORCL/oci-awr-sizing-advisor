"""Phase 7AW Screen 1 parser unknown review metadata.

The records in this module describe future parser unknown review intent for
Screen 1. They validate and route metadata only. They do not persist reviews,
change stored unknown signal state, create parser mappings, create parser
candidates, create backlog items, invoke parser behavior, write state, modify
dashboard behavior, modify CLI behavior, or mutate runtime output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


PARSER_UNKNOWN_REVIEW_DECISIONS = (
    "parser_gap",
    "source_gap",
    "false_positive",
    "not_applicable",
    "needs_mapping",
    "needs_backlog",
    "needs_human_review",
    "add_review_note",
)

PARSER_UNKNOWN_REVIEW_STATUSES = (
    "proposed",
    "under_review",
    "reviewed",
    "routed_to_mapping",
    "routed_to_backlog",
    "false_positive",
    "not_applicable",
    "closed",
)

PARSER_MAPPING_INTENT_TYPES = (
    "new_section_mapping",
    "section_mapping_refinement",
    "unknown_signal_mapping",
    "regex_pattern_review",
    "normalization_rule_review",
    "field_extraction_review",
    "parser_confidence_metadata_review",
)

PARSER_BACKLOG_ACTIONS = (
    "create_backlog_item",
    "link_to_existing_backlog",
    "request_parser_test",
    "request_regression_validation",
    "close_without_action",
)

PARSER_UNKNOWN_REVIEW_VALIDATION_STATUSES = (
    "VALID_METADATA_ONLY",
    "INVALID",
    "NEEDS_ACTOR",
    "NEEDS_UNKNOWN_SIGNAL",
    "REVIEW_NOT_PERSISTED_IN_THIS_PHASE",
)

_MAPPING_DECISIONS = ("parser_gap", "needs_mapping")


class Screen1ParserUnknownReviewError(ValueError):
    """Raised when Phase 7AW parser unknown review metadata is invalid."""


@dataclass(frozen=True)
class ParserUnknownReviewRecord:
    """Local review metadata for a parser unknown signal."""

    review_id: str
    unknown_signal_id: str
    source_run_id: str | None = None
    source_awr_id: str | None = None
    parser_section: str | None = None
    signal_name: str | None = None
    raw_text: str | None = None
    review_decision: str = "needs_human_review"
    review_status: str = "proposed"
    reviewer_actor_id: str | None = None
    actor_audit_context: dict[str, Any] | None = None
    review_notes: list[str] = field(default_factory=list)
    parser_mapping_intent_id: str | None = None
    parser_backlog_intent_id: str | None = None
    candidate_intent_id: str | None = None
    write_performed: bool = False
    runtime_influence: bool = False
    parser_output_mutation_requested: bool = False
    phase4i_mutation_requested: bool = False
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.review_id, "review_id")
        _require_nonempty_string(self.unknown_signal_id, "unknown_signal_id")
        _require_optional_string(self.source_run_id, "source_run_id")
        _require_optional_string(self.source_awr_id, "source_awr_id")
        _require_optional_string(self.parser_section, "parser_section")
        _require_optional_string(self.signal_name, "signal_name")
        _require_optional_string(self.raw_text, "raw_text")
        _require_supported(
            self.review_decision,
            PARSER_UNKNOWN_REVIEW_DECISIONS,
            "review_decision",
        )
        _require_supported(
            self.review_status,
            PARSER_UNKNOWN_REVIEW_STATUSES,
            "review_status",
        )
        _require_optional_string(self.reviewer_actor_id, "reviewer_actor_id")
        _require_optional_mapping(
            self.actor_audit_context,
            "actor_audit_context",
        )
        _require_list_of_strings(self.review_notes, "review_notes")
        _require_optional_string(
            self.parser_mapping_intent_id,
            "parser_mapping_intent_id",
        )
        _require_optional_string(
            self.parser_backlog_intent_id,
            "parser_backlog_intent_id",
        )
        _require_optional_string(self.candidate_intent_id, "candidate_intent_id")
        _require_bool(self.write_performed, "write_performed")
        _require_bool(self.runtime_influence, "runtime_influence")
        _require_bool(
            self.parser_output_mutation_requested,
            "parser_output_mutation_requested",
        )
        _require_bool(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")
        _reject_runtime_flags(
            write_performed=self.write_performed,
            runtime_influence=self.runtime_influence,
            parser_output_mutation_requested=(
                self.parser_output_mutation_requested
            ),
            phase4i_mutation_requested=self.phase4i_mutation_requested,
        )


@dataclass(frozen=True)
class ParserUnknownReviewRequest:
    """Future request metadata for parser unknown review workflow."""

    request_id: str
    unknown_signal_id: str | None
    requested_decision: str
    actor_id: str | None = None
    actor_audit_context: dict[str, Any] | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    validation_status: str = "VALID_METADATA_ONLY"
    can_route_to_write_path: bool = False
    write_performed: bool = False
    runtime_influence: bool = False
    parser_output_mutation_requested: bool = False
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.request_id, "request_id")
        _require_optional_string(self.unknown_signal_id, "unknown_signal_id")
        _require_supported(
            self.requested_decision,
            PARSER_UNKNOWN_REVIEW_DECISIONS,
            "requested_decision",
        )
        _require_optional_string(self.actor_id, "actor_id")
        _require_optional_mapping(
            self.actor_audit_context,
            "actor_audit_context",
        )
        _require_mapping(self.payload, "payload")
        _require_supported(
            self.validation_status,
            PARSER_UNKNOWN_REVIEW_VALIDATION_STATUSES,
            "validation_status",
        )
        _require_bool(self.can_route_to_write_path, "can_route_to_write_path")
        _require_bool(self.write_performed, "write_performed")
        _require_bool(self.runtime_influence, "runtime_influence")
        _require_bool(
            self.parser_output_mutation_requested,
            "parser_output_mutation_requested",
        )
        _require_bool(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.notes, "notes")
        _reject_runtime_flags(
            write_performed=self.write_performed,
            runtime_influence=self.runtime_influence,
            parser_output_mutation_requested=(
                self.parser_output_mutation_requested
            ),
            phase4i_mutation_requested=self.phase4i_mutation_requested,
        )


@dataclass(frozen=True)
class ParserMappingIntent:
    """Local intent to request parser mapping work later."""

    intent_id: str
    unknown_signal_id: str
    parser_section: str | None = None
    signal_name: str | None = None
    mapping_intent_type: str = "unknown_signal_mapping"
    proposed_mapping_summary: str | None = None
    candidate_type: str = "parser_mapping_candidate"
    requires_human_review: bool = True
    candidate_created: bool = False
    parser_mapping_created: bool = False
    runtime_influence: bool = False
    parser_output_mutation_requested: bool = False
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.intent_id, "intent_id")
        _require_nonempty_string(self.unknown_signal_id, "unknown_signal_id")
        _require_optional_string(self.parser_section, "parser_section")
        _require_optional_string(self.signal_name, "signal_name")
        _require_supported(
            self.mapping_intent_type,
            PARSER_MAPPING_INTENT_TYPES,
            "mapping_intent_type",
        )
        _require_optional_string(
            self.proposed_mapping_summary,
            "proposed_mapping_summary",
        )
        _require_nonempty_string(self.candidate_type, "candidate_type")
        _require_bool(self.requires_human_review, "requires_human_review")
        _require_bool(self.candidate_created, "candidate_created")
        _require_bool(self.parser_mapping_created, "parser_mapping_created")
        _require_bool(self.runtime_influence, "runtime_influence")
        _require_bool(
            self.parser_output_mutation_requested,
            "parser_output_mutation_requested",
        )
        _require_bool(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.notes, "notes")
        if not self.requires_human_review:
            raise Screen1ParserUnknownReviewError(
                "requires_human_review must remain true in Phase 7AW."
            )
        if self.candidate_created:
            raise Screen1ParserUnknownReviewError(
                "candidate_created must remain false in Phase 7AW."
            )
        if self.parser_mapping_created:
            raise Screen1ParserUnknownReviewError(
                "parser_mapping_created must remain false in Phase 7AW."
            )
        _reject_runtime_flags(
            write_performed=False,
            runtime_influence=self.runtime_influence,
            parser_output_mutation_requested=(
                self.parser_output_mutation_requested
            ),
            phase4i_mutation_requested=self.phase4i_mutation_requested,
        )


@dataclass(frozen=True)
class ParserBacklogIntent:
    """Local intent to route parser work to backlog later."""

    backlog_intent_id: str
    unknown_signal_id: str
    parser_section: str | None = None
    signal_name: str | None = None
    backlog_action: str = "create_backlog_item"
    backlog_summary: str | None = None
    backlog_item_created: bool = False
    runtime_influence: bool = False
    parser_output_mutation_requested: bool = False
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.backlog_intent_id, "backlog_intent_id")
        _require_nonempty_string(self.unknown_signal_id, "unknown_signal_id")
        _require_optional_string(self.parser_section, "parser_section")
        _require_optional_string(self.signal_name, "signal_name")
        _require_supported(
            self.backlog_action,
            PARSER_BACKLOG_ACTIONS,
            "backlog_action",
        )
        _require_optional_string(self.backlog_summary, "backlog_summary")
        _require_bool(self.backlog_item_created, "backlog_item_created")
        _require_bool(self.runtime_influence, "runtime_influence")
        _require_bool(
            self.parser_output_mutation_requested,
            "parser_output_mutation_requested",
        )
        _require_bool(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.notes, "notes")
        if self.backlog_item_created:
            raise Screen1ParserUnknownReviewError(
                "backlog_item_created must remain false in Phase 7AW."
            )
        _reject_runtime_flags(
            write_performed=False,
            runtime_influence=self.runtime_influence,
            parser_output_mutation_requested=(
                self.parser_output_mutation_requested
            ),
            phase4i_mutation_requested=self.phase4i_mutation_requested,
        )


@dataclass(frozen=True)
class ParserUnknownReviewValidation:
    """Metadata validation result for parser unknown review requests."""

    validation_id: str
    request_id: str
    valid: bool
    validation_status: str
    requested_decision: str
    actor_present: bool
    unknown_signal_present: bool
    can_route_to_write_path: bool
    write_performed: bool = False
    denied_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_next_steps: list[str] = field(default_factory=list)
    runtime_influence: bool = False
    parser_output_mutation_requested: bool = False
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.validation_id, "validation_id")
        _require_nonempty_string(self.request_id, "request_id")
        _require_bool(self.valid, "valid")
        _require_supported(
            self.validation_status,
            PARSER_UNKNOWN_REVIEW_VALIDATION_STATUSES,
            "validation_status",
        )
        _require_supported(
            self.requested_decision,
            PARSER_UNKNOWN_REVIEW_DECISIONS,
            "requested_decision",
        )
        _require_bool(self.actor_present, "actor_present")
        _require_bool(self.unknown_signal_present, "unknown_signal_present")
        _require_bool(
            self.can_route_to_write_path,
            "can_route_to_write_path",
        )
        _require_bool(self.write_performed, "write_performed")
        _require_list_of_strings(self.denied_reasons, "denied_reasons")
        _require_list_of_strings(self.warnings, "warnings")
        _require_list_of_strings(
            self.required_next_steps,
            "required_next_steps",
        )
        _require_bool(self.runtime_influence, "runtime_influence")
        _require_bool(
            self.parser_output_mutation_requested,
            "parser_output_mutation_requested",
        )
        _require_bool(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.notes, "notes")
        _reject_runtime_flags(
            write_performed=self.write_performed,
            runtime_influence=self.runtime_influence,
            parser_output_mutation_requested=(
                self.parser_output_mutation_requested
            ),
            phase4i_mutation_requested=self.phase4i_mutation_requested,
        )


def create_unknown_review_id(
    unknown_signal_id: str,
    review_decision: str,
) -> str:
    """Create a deterministic parser unknown review id."""

    _require_nonempty_string(unknown_signal_id, "unknown_signal_id")
    _require_supported(
        review_decision,
        PARSER_UNKNOWN_REVIEW_DECISIONS,
        "review_decision",
    )
    return (
        "SCREEN1-PARSER-UNKNOWN-REVIEW-"
        f"{_normalize_token(unknown_signal_id)}-"
        f"{_normalize_token(review_decision)}"
    )


def create_unknown_review_request_id(
    unknown_signal_id: str,
    requested_decision: str,
) -> str:
    """Create a deterministic parser unknown review request id."""

    _require_nonempty_string(unknown_signal_id, "unknown_signal_id")
    _require_supported(
        requested_decision,
        PARSER_UNKNOWN_REVIEW_DECISIONS,
        "requested_decision",
    )
    return (
        "SCREEN1-PARSER-UNKNOWN-REQUEST-"
        f"{_normalize_token(unknown_signal_id)}-"
        f"{_normalize_token(requested_decision)}"
    )


def make_mapping_intent_id(unknown_signal_id: str, mapping_intent_type: str) -> str:
    """Create a deterministic parser mapping intent id."""

    _require_nonempty_string(unknown_signal_id, "unknown_signal_id")
    _require_supported(
        mapping_intent_type,
        PARSER_MAPPING_INTENT_TYPES,
        "mapping_intent_type",
    )
    return (
        "SCREEN1-PARSER-MAPPING-INTENT-"
        f"{_normalize_token(unknown_signal_id)}-"
        f"{_normalize_token(mapping_intent_type)}"
    )


def make_backlog_intent_id(unknown_signal_id: str, backlog_action: str) -> str:
    """Create a deterministic parser backlog intent id."""

    _require_nonempty_string(unknown_signal_id, "unknown_signal_id")
    _require_supported(backlog_action, PARSER_BACKLOG_ACTIONS, "backlog_action")
    return (
        "SCREEN1-PARSER-BACKLOG-INTENT-"
        f"{_normalize_token(unknown_signal_id)}-"
        f"{_normalize_token(backlog_action)}"
    )


def create_unknown_review_validation_id(request_id: str) -> str:
    """Create a deterministic parser unknown review validation id."""

    _require_nonempty_string(request_id, "request_id")
    return f"SCREEN1-PARSER-UNKNOWN-VALIDATION-{_normalize_token(request_id)}"


def validate_parser_unknown_review_record(
    review: ParserUnknownReviewRecord,
) -> ParserUnknownReviewRecord:
    """Validate parser unknown review metadata without persisting it."""

    if not isinstance(review, ParserUnknownReviewRecord):
        raise Screen1ParserUnknownReviewError(
            "review must be a ParserUnknownReviewRecord instance."
        )
    review.__post_init__()
    return review


def validate_parser_unknown_review_request(
    request: ParserUnknownReviewRequest,
) -> ParserUnknownReviewRequest:
    """Validate parser unknown review request metadata."""

    if not isinstance(request, ParserUnknownReviewRequest):
        raise Screen1ParserUnknownReviewError(
            "request must be a ParserUnknownReviewRequest instance."
        )
    request.__post_init__()
    if not _actor_present(request):
        raise Screen1ParserUnknownReviewError(
            "parser unknown review requests require actor metadata."
        )
    return request


def evaluate_parser_unknown_review_request(
    request: ParserUnknownReviewRequest,
) -> ParserUnknownReviewValidation:
    """Evaluate review request metadata without writing or mutating runtime."""

    if not isinstance(request, ParserUnknownReviewRequest):
        raise Screen1ParserUnknownReviewError(
            "request must be a ParserUnknownReviewRequest instance."
        )
    request.__post_init__()
    actor_present = _actor_present(request)
    unknown_signal_present = bool(request.unknown_signal_id)
    denied_reasons: list[str] = ["review is not persisted in Phase 7AW"]
    warnings: list[str] = []
    required_next_steps: list[str] = [
        "route through a future governed write path before persistence"
    ]
    valid = False
    status = "INVALID"
    can_route = False

    if not actor_present:
        status = "NEEDS_ACTOR"
        denied_reasons.append("actor metadata is required")
        required_next_steps.append("provide actor identity through Phase 7AE")
    elif not unknown_signal_present:
        status = "NEEDS_UNKNOWN_SIGNAL"
        denied_reasons.append("unknown signal reference is required")
        required_next_steps.append("provide unknown_signal_id")
    else:
        status = "REVIEW_NOT_PERSISTED_IN_THIS_PHASE"
        valid = True
        can_route = bool(request.can_route_to_write_path)
        if can_route:
            warnings.append(
                "can_route_to_write_path is future eligibility only"
            )

    return ParserUnknownReviewValidation(
        validation_id=create_unknown_review_validation_id(request.request_id),
        request_id=request.request_id,
        valid=valid,
        validation_status=status,
        requested_decision=request.requested_decision,
        actor_present=actor_present,
        unknown_signal_present=unknown_signal_present,
        can_route_to_write_path=can_route,
        write_performed=False,
        denied_reasons=denied_reasons,
        warnings=warnings,
        required_next_steps=required_next_steps,
        runtime_influence=False,
        parser_output_mutation_requested=False,
        phase4i_mutation_requested=False,
        notes=request.notes,
    )


def validate_mapping_intent(intent: ParserMappingIntent) -> ParserMappingIntent:
    """Validate parser mapping intent metadata only."""

    if not isinstance(intent, ParserMappingIntent):
        raise Screen1ParserUnknownReviewError(
            "intent must be a ParserMappingIntent instance."
        )
    intent.__post_init__()
    return intent


def validate_backlog_intent(intent: ParserBacklogIntent) -> ParserBacklogIntent:
    """Validate parser backlog intent metadata only."""

    if not isinstance(intent, ParserBacklogIntent):
        raise Screen1ParserUnknownReviewError(
            "intent must be a ParserBacklogIntent instance."
        )
    intent.__post_init__()
    return intent


def validate_parser_unknown_review_validation(
    validation: ParserUnknownReviewValidation,
) -> ParserUnknownReviewValidation:
    """Validate parser unknown review validation metadata."""

    if not isinstance(validation, ParserUnknownReviewValidation):
        raise Screen1ParserUnknownReviewError(
            "validation must be a ParserUnknownReviewValidation instance."
        )
    validation.__post_init__()
    return validation


def build_mapping_intent_for_request(
    request: ParserUnknownReviewRequest,
) -> ParserMappingIntent | None:
    """Build mapping intent metadata for decisions that route to mapping."""

    validate_parser_unknown_review_request(request)
    if request.requested_decision not in _MAPPING_DECISIONS:
        return None
    parser_section = _optional_payload_string(request.payload, "parser_section")
    signal_name = _optional_payload_string(request.payload, "signal_name")
    mapping_type = request.payload.get("mapping_intent_type", "unknown_signal_mapping")
    _require_supported(
        mapping_type,
        PARSER_MAPPING_INTENT_TYPES,
        "mapping_intent_type",
    )
    return ParserMappingIntent(
        intent_id=make_mapping_intent_id(
            request.unknown_signal_id or "UNKNOWN-SIGNAL",
            mapping_type,
        ),
        unknown_signal_id=request.unknown_signal_id or "UNKNOWN-SIGNAL",
        parser_section=parser_section,
        signal_name=signal_name,
        mapping_intent_type=mapping_type,
        proposed_mapping_summary=request.payload.get("proposed_mapping_summary"),
        candidate_type="parser_mapping_candidate",
        requires_human_review=True,
        candidate_created=False,
        parser_mapping_created=False,
        runtime_influence=False,
        parser_output_mutation_requested=False,
        phase4i_mutation_requested=False,
        notes=request.notes,
    )


def build_backlog_intent_for_request(
    request: ParserUnknownReviewRequest,
) -> ParserBacklogIntent | None:
    """Build backlog intent metadata for decisions that route to backlog."""

    validate_parser_unknown_review_request(request)
    if request.requested_decision != "needs_backlog":
        return None
    parser_section = _optional_payload_string(request.payload, "parser_section")
    signal_name = _optional_payload_string(request.payload, "signal_name")
    backlog_action = request.payload.get("backlog_action", "create_backlog_item")
    _require_supported(backlog_action, PARSER_BACKLOG_ACTIONS, "backlog_action")
    return ParserBacklogIntent(
        backlog_intent_id=make_backlog_intent_id(
            request.unknown_signal_id or "UNKNOWN-SIGNAL",
            backlog_action,
        ),
        unknown_signal_id=request.unknown_signal_id or "UNKNOWN-SIGNAL",
        parser_section=parser_section,
        signal_name=signal_name,
        backlog_action=backlog_action,
        backlog_summary=request.payload.get("backlog_summary"),
        backlog_item_created=False,
        runtime_influence=False,
        parser_output_mutation_requested=False,
        phase4i_mutation_requested=False,
        notes=request.notes,
    )


def route_parser_unknown_review(
    request: ParserUnknownReviewRequest,
) -> dict[str, Any]:
    """Route parser unknown review metadata without creating runtime records."""

    validation = evaluate_parser_unknown_review_request(request)
    if not validation.valid:
        return {
            "validation": parser_unknown_review_validation_to_dict(validation),
            "review_record": None,
            "mapping_intent": None,
            "backlog_intent": None,
            "recommended_next_step": validation.required_next_steps[0],
        }

    mapping_intent = build_mapping_intent_for_request(request)
    backlog_intent = build_backlog_intent_for_request(request)
    review_status = _status_for_decision(request.requested_decision)
    review = ParserUnknownReviewRecord(
        review_id=create_unknown_review_id(
            request.unknown_signal_id or "UNKNOWN-SIGNAL",
            request.requested_decision,
        ),
        unknown_signal_id=request.unknown_signal_id or "UNKNOWN-SIGNAL",
        source_run_id=_optional_payload_string(request.payload, "source_run_id"),
        source_awr_id=_optional_payload_string(request.payload, "source_awr_id"),
        parser_section=_optional_payload_string(request.payload, "parser_section"),
        signal_name=_optional_payload_string(request.payload, "signal_name"),
        raw_text=_optional_payload_string(request.payload, "raw_text"),
        review_decision=request.requested_decision,
        review_status=review_status,
        reviewer_actor_id=request.actor_id,
        actor_audit_context=request.actor_audit_context,
        review_notes=_payload_notes(request.payload),
        parser_mapping_intent_id=(
            mapping_intent.intent_id if mapping_intent is not None else None
        ),
        parser_backlog_intent_id=(
            backlog_intent.backlog_intent_id if backlog_intent is not None else None
        ),
        candidate_intent_id=(
            mapping_intent.intent_id if mapping_intent is not None else None
        ),
        write_performed=False,
        runtime_influence=False,
        parser_output_mutation_requested=False,
        phase4i_mutation_requested=False,
        notes=request.notes,
    )
    return {
        "validation": parser_unknown_review_validation_to_dict(validation),
        "review_record": parser_unknown_review_record_to_dict(review),
        "mapping_intent": (
            mapping_intent_to_dict(mapping_intent)
            if mapping_intent is not None
            else None
        ),
        "backlog_intent": (
            backlog_intent_to_dict(backlog_intent)
            if backlog_intent is not None
            else None
        ),
        "recommended_next_step": _next_step_for_decision(request.requested_decision),
    }


def parser_unknown_review_record_to_dict(
    review: ParserUnknownReviewRecord,
) -> dict[str, Any]:
    """Serialize parser unknown review metadata."""

    review = validate_parser_unknown_review_record(review)
    return {
        "review_id": review.review_id,
        "unknown_signal_id": review.unknown_signal_id,
        "source_run_id": review.source_run_id,
        "source_awr_id": review.source_awr_id,
        "parser_section": review.parser_section,
        "signal_name": review.signal_name,
        "raw_text": review.raw_text,
        "review_decision": review.review_decision,
        "review_status": review.review_status,
        "reviewer_actor_id": review.reviewer_actor_id,
        "actor_audit_context": _copy_optional_mapping(review.actor_audit_context),
        "review_notes": list(review.review_notes),
        "parser_mapping_intent_id": review.parser_mapping_intent_id,
        "parser_backlog_intent_id": review.parser_backlog_intent_id,
        "candidate_intent_id": review.candidate_intent_id,
        "write_performed": review.write_performed,
        "runtime_influence": review.runtime_influence,
        "parser_output_mutation_requested": (
            review.parser_output_mutation_requested
        ),
        "phase4i_mutation_requested": review.phase4i_mutation_requested,
        "created_at": review.created_at,
        "notes": review.notes,
    }


def parser_unknown_review_record_from_dict(
    data: dict[str, Any],
) -> ParserUnknownReviewRecord:
    """Deserialize parser unknown review metadata."""

    _require_mapping(data, "parser_unknown_review_record")
    return ParserUnknownReviewRecord(
        review_id=data.get("review_id"),
        unknown_signal_id=data.get("unknown_signal_id"),
        source_run_id=data.get("source_run_id"),
        source_awr_id=data.get("source_awr_id"),
        parser_section=data.get("parser_section"),
        signal_name=data.get("signal_name"),
        raw_text=data.get("raw_text"),
        review_decision=data.get("review_decision", "needs_human_review"),
        review_status=data.get("review_status", "proposed"),
        reviewer_actor_id=data.get("reviewer_actor_id"),
        actor_audit_context=data.get("actor_audit_context"),
        review_notes=data.get("review_notes", []),
        parser_mapping_intent_id=data.get("parser_mapping_intent_id"),
        parser_backlog_intent_id=data.get("parser_backlog_intent_id"),
        candidate_intent_id=data.get("candidate_intent_id"),
        write_performed=data.get("write_performed", False),
        runtime_influence=data.get("runtime_influence", False),
        parser_output_mutation_requested=data.get(
            "parser_output_mutation_requested",
            False,
        ),
        phase4i_mutation_requested=data.get("phase4i_mutation_requested", False),
        created_at=data.get("created_at"),
        notes=data.get("notes"),
    )


def parser_unknown_review_request_to_dict(
    request: ParserUnknownReviewRequest,
) -> dict[str, Any]:
    """Serialize parser unknown review request metadata."""

    request.__post_init__()
    return {
        "request_id": request.request_id,
        "unknown_signal_id": request.unknown_signal_id,
        "requested_decision": request.requested_decision,
        "actor_id": request.actor_id,
        "actor_audit_context": _copy_optional_mapping(request.actor_audit_context),
        "payload": dict(request.payload),
        "validation_status": request.validation_status,
        "can_route_to_write_path": request.can_route_to_write_path,
        "write_performed": request.write_performed,
        "runtime_influence": request.runtime_influence,
        "parser_output_mutation_requested": (
            request.parser_output_mutation_requested
        ),
        "phase4i_mutation_requested": request.phase4i_mutation_requested,
        "notes": request.notes,
    }


def parser_unknown_review_request_from_dict(
    data: dict[str, Any],
) -> ParserUnknownReviewRequest:
    """Deserialize parser unknown review request metadata."""

    _require_mapping(data, "parser_unknown_review_request")
    return ParserUnknownReviewRequest(
        request_id=data.get("request_id"),
        unknown_signal_id=data.get("unknown_signal_id"),
        requested_decision=data.get("requested_decision"),
        actor_id=data.get("actor_id"),
        actor_audit_context=data.get("actor_audit_context"),
        payload=data.get("payload", {}),
        validation_status=data.get("validation_status", "VALID_METADATA_ONLY"),
        can_route_to_write_path=data.get("can_route_to_write_path", False),
        write_performed=data.get("write_performed", False),
        runtime_influence=data.get("runtime_influence", False),
        parser_output_mutation_requested=data.get(
            "parser_output_mutation_requested",
            False,
        ),
        phase4i_mutation_requested=data.get("phase4i_mutation_requested", False),
        notes=data.get("notes"),
    )


def mapping_intent_to_dict(intent: ParserMappingIntent) -> dict[str, Any]:
    """Serialize parser mapping intent metadata."""

    intent = validate_mapping_intent(intent)
    return {
        "intent_id": intent.intent_id,
        "unknown_signal_id": intent.unknown_signal_id,
        "parser_section": intent.parser_section,
        "signal_name": intent.signal_name,
        "mapping_intent_type": intent.mapping_intent_type,
        "proposed_mapping_summary": intent.proposed_mapping_summary,
        "candidate_type": intent.candidate_type,
        "requires_human_review": intent.requires_human_review,
        "candidate_created": intent.candidate_created,
        "parser_mapping_created": intent.parser_mapping_created,
        "runtime_influence": intent.runtime_influence,
        "parser_output_mutation_requested": (
            intent.parser_output_mutation_requested
        ),
        "phase4i_mutation_requested": intent.phase4i_mutation_requested,
        "notes": intent.notes,
    }


def mapping_intent_from_dict(data: dict[str, Any]) -> ParserMappingIntent:
    """Deserialize parser mapping intent metadata."""

    _require_mapping(data, "parser_mapping_intent")
    return ParserMappingIntent(
        intent_id=data.get("intent_id"),
        unknown_signal_id=data.get("unknown_signal_id"),
        parser_section=data.get("parser_section"),
        signal_name=data.get("signal_name"),
        mapping_intent_type=data.get(
            "mapping_intent_type",
            "unknown_signal_mapping",
        ),
        proposed_mapping_summary=data.get("proposed_mapping_summary"),
        candidate_type=data.get("candidate_type", "parser_mapping_candidate"),
        requires_human_review=data.get("requires_human_review", True),
        candidate_created=data.get("candidate_created", False),
        parser_mapping_created=data.get("parser_mapping_created", False),
        runtime_influence=data.get("runtime_influence", False),
        parser_output_mutation_requested=data.get(
            "parser_output_mutation_requested",
            False,
        ),
        phase4i_mutation_requested=data.get("phase4i_mutation_requested", False),
        notes=data.get("notes"),
    )


def backlog_intent_to_dict(intent: ParserBacklogIntent) -> dict[str, Any]:
    """Serialize parser backlog intent metadata."""

    intent = validate_backlog_intent(intent)
    return {
        "backlog_intent_id": intent.backlog_intent_id,
        "unknown_signal_id": intent.unknown_signal_id,
        "parser_section": intent.parser_section,
        "signal_name": intent.signal_name,
        "backlog_action": intent.backlog_action,
        "backlog_summary": intent.backlog_summary,
        "backlog_item_created": intent.backlog_item_created,
        "runtime_influence": intent.runtime_influence,
        "parser_output_mutation_requested": (
            intent.parser_output_mutation_requested
        ),
        "phase4i_mutation_requested": intent.phase4i_mutation_requested,
        "notes": intent.notes,
    }


def backlog_intent_from_dict(data: dict[str, Any]) -> ParserBacklogIntent:
    """Deserialize parser backlog intent metadata."""

    _require_mapping(data, "parser_backlog_intent")
    return ParserBacklogIntent(
        backlog_intent_id=data.get("backlog_intent_id"),
        unknown_signal_id=data.get("unknown_signal_id"),
        parser_section=data.get("parser_section"),
        signal_name=data.get("signal_name"),
        backlog_action=data.get("backlog_action", "create_backlog_item"),
        backlog_summary=data.get("backlog_summary"),
        backlog_item_created=data.get("backlog_item_created", False),
        runtime_influence=data.get("runtime_influence", False),
        parser_output_mutation_requested=data.get(
            "parser_output_mutation_requested",
            False,
        ),
        phase4i_mutation_requested=data.get("phase4i_mutation_requested", False),
        notes=data.get("notes"),
    )


def parser_unknown_review_validation_to_dict(
    validation: ParserUnknownReviewValidation,
) -> dict[str, Any]:
    """Serialize parser unknown review validation metadata."""

    validation = validate_parser_unknown_review_validation(validation)
    return {
        "validation_id": validation.validation_id,
        "request_id": validation.request_id,
        "valid": validation.valid,
        "validation_status": validation.validation_status,
        "requested_decision": validation.requested_decision,
        "actor_present": validation.actor_present,
        "unknown_signal_present": validation.unknown_signal_present,
        "can_route_to_write_path": validation.can_route_to_write_path,
        "write_performed": validation.write_performed,
        "denied_reasons": list(validation.denied_reasons),
        "warnings": list(validation.warnings),
        "required_next_steps": list(validation.required_next_steps),
        "runtime_influence": validation.runtime_influence,
        "parser_output_mutation_requested": (
            validation.parser_output_mutation_requested
        ),
        "phase4i_mutation_requested": validation.phase4i_mutation_requested,
        "notes": validation.notes,
    }


def parser_unknown_review_validation_from_dict(
    data: dict[str, Any],
) -> ParserUnknownReviewValidation:
    """Deserialize parser unknown review validation metadata."""

    _require_mapping(data, "parser_unknown_review_validation")
    return ParserUnknownReviewValidation(
        validation_id=data.get("validation_id"),
        request_id=data.get("request_id"),
        valid=data.get("valid"),
        validation_status=data.get("validation_status"),
        requested_decision=data.get("requested_decision"),
        actor_present=data.get("actor_present"),
        unknown_signal_present=data.get("unknown_signal_present"),
        can_route_to_write_path=data.get("can_route_to_write_path"),
        write_performed=data.get("write_performed", False),
        denied_reasons=data.get("denied_reasons", []),
        warnings=data.get("warnings", []),
        required_next_steps=data.get("required_next_steps", []),
        runtime_influence=data.get("runtime_influence", False),
        parser_output_mutation_requested=data.get(
            "parser_output_mutation_requested",
            False,
        ),
        phase4i_mutation_requested=data.get("phase4i_mutation_requested", False),
        notes=data.get("notes"),
    )


def _status_for_decision(decision: str) -> str:
    _require_supported(decision, PARSER_UNKNOWN_REVIEW_DECISIONS, "decision")
    if decision in _MAPPING_DECISIONS:
        return "routed_to_mapping"
    if decision == "needs_backlog":
        return "routed_to_backlog"
    if decision == "false_positive":
        return "false_positive"
    if decision == "not_applicable":
        return "not_applicable"
    if decision == "needs_human_review":
        return "under_review"
    return "reviewed"


def _next_step_for_decision(decision: str) -> str:
    _require_supported(decision, PARSER_UNKNOWN_REVIEW_DECISIONS, "decision")
    if decision in _MAPPING_DECISIONS:
        return "review parser mapping intent through future governance"
    if decision == "needs_backlog":
        return "review parser backlog intent through future governance"
    if decision == "source_gap":
        return "recommend source review"
    if decision == "false_positive":
        return "close as false positive in a future governed workflow"
    if decision == "not_applicable":
        return "close as not applicable in a future governed workflow"
    if decision == "needs_human_review":
        return "keep under human review"
    return "record note in a future governed workflow"


def _actor_present(request: ParserUnknownReviewRequest) -> bool:
    return bool(request.actor_id or request.actor_audit_context)


def _optional_payload_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    _require_optional_string(value, key)
    return value


def _payload_notes(payload: dict[str, Any]) -> list[str]:
    notes = payload.get("review_notes", [])
    if isinstance(notes, str):
        return [notes]
    _require_list_of_strings(notes, "review_notes")
    return list(notes)


def _copy_optional_mapping(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_mapping(value, "mapping")
    return dict(value)


def _reject_runtime_flags(
    *,
    write_performed: bool,
    runtime_influence: bool,
    parser_output_mutation_requested: bool,
    phase4i_mutation_requested: bool,
) -> None:
    if write_performed:
        raise Screen1ParserUnknownReviewError(
            "write_performed must remain false in Phase 7AW."
        )
    if runtime_influence:
        raise Screen1ParserUnknownReviewError(
            "runtime_influence must remain false in Phase 7AW."
        )
    if parser_output_mutation_requested:
        raise Screen1ParserUnknownReviewError(
            "parser_output_mutation_requested must remain false in Phase 7AW."
        )
    if phase4i_mutation_requested:
        raise Screen1ParserUnknownReviewError(
            "phase4i_mutation_requested must remain false in Phase 7AW."
        )


def _normalize_token(value: str) -> str:
    _require_nonempty_string(value, "value")
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().upper())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "NONE"


def _require_nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Screen1ParserUnknownReviewError(f"{field_name} is required.")
    return value


def _require_optional_string(value: Any, field_name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise Screen1ParserUnknownReviewError(
            f"{field_name} must be a string or None."
        )
    return value


def _require_supported(value: Any, supported: tuple[str, ...], field_name: str) -> str:
    if not isinstance(value, str) or value not in supported:
        raise Screen1ParserUnknownReviewError(
            f"Unsupported {field_name}: {value!r}."
        )
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise Screen1ParserUnknownReviewError(f"{field_name} must be boolean.")
    return value


def _require_list_of_strings(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise Screen1ParserUnknownReviewError(
            f"{field_name} must be a list of strings."
        )
    return value


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Screen1ParserUnknownReviewError(
            f"{field_name} must be a dictionary."
        )
    return value


def _require_optional_mapping(
    value: Any,
    field_name: str,
) -> dict[str, Any] | None:
    if value is not None and not isinstance(value, dict):
        raise Screen1ParserUnknownReviewError(
            f"{field_name} must be a dictionary or None."
        )
    return value
