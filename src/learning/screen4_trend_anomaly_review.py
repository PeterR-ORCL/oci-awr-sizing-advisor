"""Phase 7BB Screen 4 trend/anomaly review metadata models.

The records in this module describe local metadata for future Screen 4
historical trend and anomaly review. They do not persist review records, create
candidates, implement UI, invoke write paths, execute analysis, modify
dashboards, modify CLI behavior, or mutate deterministic historical truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


HISTORICAL_REVIEW_TARGET_TYPES = (
    "trend_summary",
    "trend_metric",
    "anomaly_group",
    "anomaly_event",
    "historical_baseline",
    "comparison_baseline",
    "recurrence_pattern",
    "historical_confidence",
    "missing_historical_evidence",
    "trend_aware_scoring_reference",
    "learning_candidate_intent",
)

HISTORICAL_REVIEW_DECISIONS = (
    "approve_trend",
    "dispute_trend",
    "mark_trend_insufficient",
    "approve_anomaly",
    "mark_anomaly_false_positive",
    "mark_anomaly_insufficient",
    "request_trend_aware_scoring_review",
    "request_anomaly_sensitivity_review",
    "request_scoring_threshold_review",
    "request_learning_candidate",
    "add_historical_review_note",
)

HISTORICAL_REVIEW_STATUSES = (
    "proposed",
    "under_review",
    "approved",
    "disputed",
    "insufficient_evidence",
    "false_positive",
    "routed_to_governance",
    "linked_to_candidate",
    "closed",
)

HISTORICAL_REVIEW_VALIDATION_STATUSES = (
    "valid",
    "invalid",
    "needs_actor",
    "needs_target",
    "needs_baseline_context",
    "unsupported_decision",
    "write_not_allowed_in_this_phase",
)

HISTORICAL_REVIEW_ROUTING_INTENTS = {
    "approve_trend": "review_decision_intent",
    "dispute_trend": "human_review_intent",
    "mark_trend_insufficient": "evidence_validation_intent",
    "approve_anomaly": "review_decision_intent",
    "mark_anomaly_false_positive": "validation_intent",
    "mark_anomaly_insufficient": "evidence_validation_intent",
    "request_trend_aware_scoring_review": "scoring_review_intent",
    "request_anomaly_sensitivity_review": "scoring_review_intent",
    "request_scoring_threshold_review": "scoring_review_intent",
    "request_learning_candidate": "learning_candidate_intent",
    "add_historical_review_note": "note_intent",
}

_BASELINE_SENSITIVE_TARGETS = (
    "trend_summary",
    "trend_metric",
    "anomaly_group",
    "anomaly_event",
    "historical_baseline",
    "comparison_baseline",
    "recurrence_pattern",
    "historical_confidence",
    "missing_historical_evidence",
    "trend_aware_scoring_reference",
)

_NON_ACTIONABLE_DECISIONS = ("add_historical_review_note",)


class Screen4TrendAnomalyReviewError(ValueError):
    """Raised when Phase 7BB trend/anomaly review metadata is invalid."""


@dataclass(frozen=True)
class HistoricalTrendReviewRecord:
    """Local reviewer assessment metadata for a Screen 4 trend."""

    trend_review_id: str
    run_id: str | None = None
    awr_id: str | None = None
    baseline_candidate_id: str | None = None
    comparison_context_id: str | None = None
    trend_id: str | None = None
    trend_name: str | None = None
    domain: str | None = None
    trend_direction: str | None = None
    trend_strength: float | None = None
    review_decision: str = "add_historical_review_note"
    review_status: str = "proposed"
    reviewer_actor_id: str | None = None
    actor_audit_context: dict[str, Any] | None = None
    review_notes: str | None = None
    linked_scoring_review_id: str | None = None
    linked_candidate_intent_id: str | None = None
    write_performed: bool = False
    trend_truth_changed: bool = False
    scoring_mutation_requested: bool = False
    runtime_influence: bool = False
    phase4i_mutation_requested: bool = False
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.trend_review_id, "trend_review_id")
        _require_optional_string(self.run_id, "run_id")
        _require_optional_string(self.awr_id, "awr_id")
        _require_at_least_one_identifier(
            ("run_id", self.run_id),
            ("awr_id", self.awr_id),
        )
        _require_optional_string(self.baseline_candidate_id, "baseline_candidate_id")
        _require_optional_string(self.comparison_context_id, "comparison_context_id")
        _require_nonempty_string(self.trend_id, "trend_id")
        _require_optional_string(self.trend_name, "trend_name")
        _require_optional_string(self.domain, "domain")
        _require_optional_string(self.trend_direction, "trend_direction")
        _require_optional_unit_score(self.trend_strength, "trend_strength")
        _require_supported(
            self.review_decision,
            HISTORICAL_REVIEW_DECISIONS,
            "review_decision",
        )
        _require_supported(
            self.review_status,
            HISTORICAL_REVIEW_STATUSES,
            "review_status",
        )
        _require_optional_string(self.reviewer_actor_id, "reviewer_actor_id")
        if _decision_requires_actor(self.review_decision):
            _require_nonempty_string(self.reviewer_actor_id, "reviewer_actor_id")
        _require_optional_mapping(self.actor_audit_context, "actor_audit_context")
        _require_optional_string(self.review_notes, "review_notes")
        _require_optional_string(
            self.linked_scoring_review_id,
            "linked_scoring_review_id",
        )
        _require_optional_string(
            self.linked_candidate_intent_id,
            "linked_candidate_intent_id",
        )
        _require_boolean(self.write_performed, "write_performed")
        _require_boolean(self.trend_truth_changed, "trend_truth_changed")
        _require_boolean(
            self.scoring_mutation_requested,
            "scoring_mutation_requested",
        )
        _require_boolean(self.runtime_influence, "runtime_influence")
        _require_boolean(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _reject_true(self.write_performed, "write_performed")
        _reject_true(self.trend_truth_changed, "trend_truth_changed")
        _reject_true(
            self.scoring_mutation_requested,
            "scoring_mutation_requested",
        )
        _reject_true(self.runtime_influence, "runtime_influence")
        _reject_true(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")


@dataclass(frozen=True)
class HistoricalAnomalyReviewRecord:
    """Local reviewer assessment metadata for a Screen 4 anomaly."""

    anomaly_review_id: str
    run_id: str | None = None
    awr_id: str | None = None
    baseline_candidate_id: str | None = None
    comparison_context_id: str | None = None
    anomaly_id: str | None = None
    anomaly_name: str | None = None
    domain: str | None = None
    anomaly_pattern: str | None = None
    anomaly_severity: float | None = None
    review_decision: str = "add_historical_review_note"
    review_status: str = "proposed"
    reviewer_actor_id: str | None = None
    actor_audit_context: dict[str, Any] | None = None
    review_notes: str | None = None
    linked_scoring_review_id: str | None = None
    linked_candidate_intent_id: str | None = None
    write_performed: bool = False
    anomaly_truth_changed: bool = False
    scoring_mutation_requested: bool = False
    runtime_influence: bool = False
    phase4i_mutation_requested: bool = False
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.anomaly_review_id, "anomaly_review_id")
        _require_optional_string(self.run_id, "run_id")
        _require_optional_string(self.awr_id, "awr_id")
        _require_at_least_one_identifier(
            ("run_id", self.run_id),
            ("awr_id", self.awr_id),
        )
        _require_optional_string(self.baseline_candidate_id, "baseline_candidate_id")
        _require_optional_string(self.comparison_context_id, "comparison_context_id")
        _require_nonempty_string(self.anomaly_id, "anomaly_id")
        _require_optional_string(self.anomaly_name, "anomaly_name")
        _require_optional_string(self.domain, "domain")
        _require_optional_string(self.anomaly_pattern, "anomaly_pattern")
        _require_optional_unit_score(self.anomaly_severity, "anomaly_severity")
        _require_supported(
            self.review_decision,
            HISTORICAL_REVIEW_DECISIONS,
            "review_decision",
        )
        _require_supported(
            self.review_status,
            HISTORICAL_REVIEW_STATUSES,
            "review_status",
        )
        _require_optional_string(self.reviewer_actor_id, "reviewer_actor_id")
        if _decision_requires_actor(self.review_decision):
            _require_nonempty_string(self.reviewer_actor_id, "reviewer_actor_id")
        _require_optional_mapping(self.actor_audit_context, "actor_audit_context")
        _require_optional_string(self.review_notes, "review_notes")
        _require_optional_string(
            self.linked_scoring_review_id,
            "linked_scoring_review_id",
        )
        _require_optional_string(
            self.linked_candidate_intent_id,
            "linked_candidate_intent_id",
        )
        _require_boolean(self.write_performed, "write_performed")
        _require_boolean(self.anomaly_truth_changed, "anomaly_truth_changed")
        _require_boolean(
            self.scoring_mutation_requested,
            "scoring_mutation_requested",
        )
        _require_boolean(self.runtime_influence, "runtime_influence")
        _require_boolean(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _reject_true(self.write_performed, "write_performed")
        _reject_true(self.anomaly_truth_changed, "anomaly_truth_changed")
        _reject_true(
            self.scoring_mutation_requested,
            "scoring_mutation_requested",
        )
        _reject_true(self.runtime_influence, "runtime_influence")
        _reject_true(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")


@dataclass(frozen=True)
class HistoricalReviewRequest:
    """Future request metadata for Screen 4 historical review workflow."""

    request_id: str
    review_target_type: str
    review_target_id: str | None
    requested_decision: str
    actor_id: str | None
    actor_audit_context: dict[str, Any] | None = None
    baseline_candidate_id: str | None = None
    comparison_context_id: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    validation_status: str = "valid"
    can_route_to_governance: bool = False
    write_performed: bool = False
    truth_mutation_requested: bool = False
    scoring_mutation_requested: bool = False
    runtime_influence: bool = False
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.request_id, "request_id")
        _require_supported(
            self.review_target_type,
            HISTORICAL_REVIEW_TARGET_TYPES,
            "review_target_type",
        )
        _require_optional_string(self.review_target_id, "review_target_id")
        _require_supported(
            self.requested_decision,
            HISTORICAL_REVIEW_DECISIONS,
            "requested_decision",
        )
        _require_optional_string(self.actor_id, "actor_id")
        _require_optional_mapping(self.actor_audit_context, "actor_audit_context")
        _require_optional_string(self.baseline_candidate_id, "baseline_candidate_id")
        _require_optional_string(self.comparison_context_id, "comparison_context_id")
        _require_mapping(self.payload, "payload")
        _require_supported(
            self.validation_status,
            HISTORICAL_REVIEW_VALIDATION_STATUSES,
            "validation_status",
        )
        _require_boolean(self.can_route_to_governance, "can_route_to_governance")
        _require_boolean(self.write_performed, "write_performed")
        _require_boolean(
            self.truth_mutation_requested,
            "truth_mutation_requested",
        )
        _require_boolean(
            self.scoring_mutation_requested,
            "scoring_mutation_requested",
        )
        _require_boolean(self.runtime_influence, "runtime_influence")
        _require_boolean(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _reject_true(self.write_performed, "write_performed")
        _reject_true(
            self.truth_mutation_requested,
            "truth_mutation_requested",
        )
        _reject_true(
            self.scoring_mutation_requested,
            "scoring_mutation_requested",
        )
        _reject_true(self.runtime_influence, "runtime_influence")
        _reject_true(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.notes, "notes")


@dataclass(frozen=True)
class HistoricalReviewValidation:
    """Validation result metadata for historical review requests."""

    validation_id: str
    request_id: str
    valid: bool
    validation_status: str
    requested_decision: str
    actor_present: bool
    target_present: bool
    baseline_context_present: bool
    can_route_to_governance: bool = False
    write_performed: bool = False
    truth_mutation_requested: bool = False
    scoring_mutation_requested: bool = False
    denied_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_next_steps: list[str] = field(default_factory=list)
    runtime_influence: bool = False
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.validation_id, "validation_id")
        _require_nonempty_string(self.request_id, "request_id")
        _require_boolean(self.valid, "valid")
        _require_supported(
            self.validation_status,
            HISTORICAL_REVIEW_VALIDATION_STATUSES,
            "validation_status",
        )
        _require_supported(
            self.requested_decision,
            HISTORICAL_REVIEW_DECISIONS,
            "requested_decision",
        )
        _require_boolean(self.actor_present, "actor_present")
        _require_boolean(self.target_present, "target_present")
        _require_boolean(
            self.baseline_context_present,
            "baseline_context_present",
        )
        _require_boolean(self.can_route_to_governance, "can_route_to_governance")
        _require_boolean(self.write_performed, "write_performed")
        _require_boolean(
            self.truth_mutation_requested,
            "truth_mutation_requested",
        )
        _require_boolean(
            self.scoring_mutation_requested,
            "scoring_mutation_requested",
        )
        _require_string_list(self.denied_reasons, "denied_reasons")
        _require_string_list(self.warnings, "warnings")
        _require_string_list(self.required_next_steps, "required_next_steps")
        _require_boolean(self.runtime_influence, "runtime_influence")
        _require_boolean(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _reject_true(self.write_performed, "write_performed")
        _reject_true(
            self.truth_mutation_requested,
            "truth_mutation_requested",
        )
        _reject_true(
            self.scoring_mutation_requested,
            "scoring_mutation_requested",
        )
        _reject_true(self.runtime_influence, "runtime_influence")
        _reject_true(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.notes, "notes")


def create_trend_review_id(
    run_id: str | None,
    awr_id: str | None,
    trend_id: str,
) -> str:
    """Create a deterministic Screen 4 trend review id."""

    _require_optional_string(run_id, "run_id")
    _require_optional_string(awr_id, "awr_id")
    _require_at_least_one_identifier(("run_id", run_id), ("awr_id", awr_id))
    _require_nonempty_string(trend_id, "trend_id")
    return (
        "SCREEN4-TREND-REVIEW-"
        f"{_normalize_token(run_id or awr_id)}-"
        f"{_normalize_token(trend_id)}"
    )


def create_anomaly_review_id(
    run_id: str | None,
    awr_id: str | None,
    anomaly_id: str,
) -> str:
    """Create a deterministic Screen 4 anomaly review id."""

    _require_optional_string(run_id, "run_id")
    _require_optional_string(awr_id, "awr_id")
    _require_at_least_one_identifier(("run_id", run_id), ("awr_id", awr_id))
    _require_nonempty_string(anomaly_id, "anomaly_id")
    return (
        "SCREEN4-ANOMALY-REVIEW-"
        f"{_normalize_token(run_id or awr_id)}-"
        f"{_normalize_token(anomaly_id)}"
    )


def create_historical_review_request_id(
    review_target_type: str,
    review_target_id: str,
    requested_decision: str,
) -> str:
    """Create a deterministic Screen 4 historical review request id."""

    _require_supported(
        review_target_type,
        HISTORICAL_REVIEW_TARGET_TYPES,
        "review_target_type",
    )
    _require_nonempty_string(review_target_id, "review_target_id")
    _require_supported(
        requested_decision,
        HISTORICAL_REVIEW_DECISIONS,
        "requested_decision",
    )
    return (
        "SCREEN4-HIST-REQUEST-"
        f"{_normalize_token(review_target_type)}-"
        f"{_normalize_token(review_target_id)}-"
        f"{_normalize_token(requested_decision)}"
    )


def create_historical_review_validation_id(request_id: str) -> str:
    """Create a deterministic Screen 4 historical review validation id."""

    _require_nonempty_string(request_id, "request_id")
    return f"SCREEN4-HIST-VALIDATION-{_normalize_token(request_id)}"


def validate_historical_trend_review_record(
    record: HistoricalTrendReviewRecord,
) -> HistoricalTrendReviewRecord:
    """Validate and return trend review metadata."""

    if not isinstance(record, HistoricalTrendReviewRecord):
        raise Screen4TrendAnomalyReviewError(
            "record must be a HistoricalTrendReviewRecord instance."
        )
    record.__post_init__()
    return record


def validate_historical_anomaly_review_record(
    record: HistoricalAnomalyReviewRecord,
) -> HistoricalAnomalyReviewRecord:
    """Validate and return anomaly review metadata."""

    if not isinstance(record, HistoricalAnomalyReviewRecord):
        raise Screen4TrendAnomalyReviewError(
            "record must be a HistoricalAnomalyReviewRecord instance."
        )
    record.__post_init__()
    return record


def validate_historical_review_request(
    request: HistoricalReviewRequest,
) -> HistoricalReviewRequest:
    """Validate and return historical review request metadata."""

    if not isinstance(request, HistoricalReviewRequest):
        raise Screen4TrendAnomalyReviewError(
            "request must be a HistoricalReviewRequest instance."
        )
    request.__post_init__()
    _require_nonempty_string(request.review_target_id, "review_target_id")
    if _decision_requires_actor(request.requested_decision):
        _require_nonempty_string(request.actor_id, "actor_id")
    return request


def validate_historical_review_validation(
    validation: HistoricalReviewValidation,
) -> HistoricalReviewValidation:
    """Validate and return historical review validation metadata."""

    if not isinstance(validation, HistoricalReviewValidation):
        raise Screen4TrendAnomalyReviewError(
            "validation must be a HistoricalReviewValidation instance."
        )
    validation.__post_init__()
    return validation


def evaluate_historical_review_request(
    request: HistoricalReviewRequest,
) -> HistoricalReviewValidation:
    """Evaluate review request metadata without persistence or mutation."""

    if not isinstance(request, HistoricalReviewRequest):
        raise Screen4TrendAnomalyReviewError(
            "request must be a HistoricalReviewRequest instance."
        )
    request.__post_init__()

    actor_present = bool(_optional_text(request.actor_id))
    target_present = bool(_optional_text(request.review_target_id))
    baseline_context_present = bool(
        _optional_text(request.baseline_candidate_id)
        or _optional_text(request.comparison_context_id)
    )
    denied_reasons: list[str] = []
    required_next_steps: list[str] = []
    warnings = [
        "Historical review validation is metadata only.",
        "Future governed write path is required before record creation.",
    ]

    if _decision_requires_actor(request.requested_decision) and not actor_present:
        validation_status = "needs_actor"
        denied_reasons.append("actor_id is required for historical review")
        required_next_steps.append("provide Phase 7AE actor identity")
    elif not target_present:
        validation_status = "needs_target"
        denied_reasons.append("review_target_id is required")
        required_next_steps.append("provide historical review target reference")
    elif (
        request.review_target_type in _BASELINE_SENSITIVE_TARGETS
        and not baseline_context_present
    ):
        validation_status = "needs_baseline_context"
        denied_reasons.append("baseline or comparison context is required")
        required_next_steps.append("provide Phase 7BA baseline/comparison context")
    else:
        validation_status = "valid"
        required_next_steps.append("route through future governed write path")

    return HistoricalReviewValidation(
        validation_id=create_historical_review_validation_id(request.request_id),
        request_id=request.request_id,
        valid=validation_status == "valid",
        validation_status=validation_status,
        requested_decision=request.requested_decision,
        actor_present=actor_present,
        target_present=target_present,
        baseline_context_present=baseline_context_present,
        can_route_to_governance=(
            request.can_route_to_governance and validation_status == "valid"
        ),
        write_performed=False,
        truth_mutation_requested=False,
        scoring_mutation_requested=False,
        denied_reasons=denied_reasons,
        warnings=warnings,
        required_next_steps=required_next_steps,
        runtime_influence=False,
        phase4i_mutation_requested=False,
        notes=request.notes,
    )


def routing_intent_for_historical_decision(decision: str) -> str:
    """Return future routing intent metadata for a historical decision."""

    _require_supported(decision, HISTORICAL_REVIEW_DECISIONS, "decision")
    return HISTORICAL_REVIEW_ROUTING_INTENTS[decision]


def historical_trend_review_record_to_dict(
    record: HistoricalTrendReviewRecord,
) -> dict[str, Any]:
    """Serialize trend review metadata to a deterministic dict."""

    record = validate_historical_trend_review_record(record)
    return {
        "trend_review_id": record.trend_review_id,
        "run_id": record.run_id,
        "awr_id": record.awr_id,
        "baseline_candidate_id": record.baseline_candidate_id,
        "comparison_context_id": record.comparison_context_id,
        "trend_id": record.trend_id,
        "trend_name": record.trend_name,
        "domain": record.domain,
        "trend_direction": record.trend_direction,
        "trend_strength": record.trend_strength,
        "review_decision": record.review_decision,
        "review_status": record.review_status,
        "reviewer_actor_id": record.reviewer_actor_id,
        "actor_audit_context": _copy_optional_mapping(record.actor_audit_context),
        "review_notes": record.review_notes,
        "linked_scoring_review_id": record.linked_scoring_review_id,
        "linked_candidate_intent_id": record.linked_candidate_intent_id,
        "write_performed": record.write_performed,
        "trend_truth_changed": record.trend_truth_changed,
        "scoring_mutation_requested": record.scoring_mutation_requested,
        "runtime_influence": record.runtime_influence,
        "phase4i_mutation_requested": record.phase4i_mutation_requested,
        "created_at": record.created_at,
        "notes": record.notes,
    }


def historical_trend_review_record_from_dict(
    data: dict[str, Any],
) -> HistoricalTrendReviewRecord:
    """Deserialize trend review metadata from a dictionary."""

    _require_mapping(data, "trend_review_record")
    return HistoricalTrendReviewRecord(
        trend_review_id=str(data["trend_review_id"]),
        run_id=_optional_text(data.get("run_id")),
        awr_id=_optional_text(data.get("awr_id")),
        baseline_candidate_id=_optional_text(data.get("baseline_candidate_id")),
        comparison_context_id=_optional_text(data.get("comparison_context_id")),
        trend_id=_optional_text(data.get("trend_id")),
        trend_name=_optional_text(data.get("trend_name")),
        domain=_optional_text(data.get("domain")),
        trend_direction=_optional_text(data.get("trend_direction")),
        trend_strength=_optional_float(data.get("trend_strength")),
        review_decision=str(data.get("review_decision", "add_historical_review_note")),
        review_status=str(data.get("review_status", "proposed")),
        reviewer_actor_id=_optional_text(data.get("reviewer_actor_id")),
        actor_audit_context=_copy_optional_mapping(data.get("actor_audit_context")),
        review_notes=_optional_text(data.get("review_notes")),
        linked_scoring_review_id=_optional_text(
            data.get("linked_scoring_review_id")
        ),
        linked_candidate_intent_id=_optional_text(
            data.get("linked_candidate_intent_id")
        ),
        write_performed=_bool_from_mapping(data, "write_performed", False),
        trend_truth_changed=_bool_from_mapping(data, "trend_truth_changed", False),
        scoring_mutation_requested=_bool_from_mapping(
            data,
            "scoring_mutation_requested",
            False,
        ),
        runtime_influence=_bool_from_mapping(data, "runtime_influence", False),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        created_at=_optional_text(data.get("created_at")),
        notes=_optional_text(data.get("notes")),
    )


def historical_anomaly_review_record_to_dict(
    record: HistoricalAnomalyReviewRecord,
) -> dict[str, Any]:
    """Serialize anomaly review metadata to a deterministic dict."""

    record = validate_historical_anomaly_review_record(record)
    return {
        "anomaly_review_id": record.anomaly_review_id,
        "run_id": record.run_id,
        "awr_id": record.awr_id,
        "baseline_candidate_id": record.baseline_candidate_id,
        "comparison_context_id": record.comparison_context_id,
        "anomaly_id": record.anomaly_id,
        "anomaly_name": record.anomaly_name,
        "domain": record.domain,
        "anomaly_pattern": record.anomaly_pattern,
        "anomaly_severity": record.anomaly_severity,
        "review_decision": record.review_decision,
        "review_status": record.review_status,
        "reviewer_actor_id": record.reviewer_actor_id,
        "actor_audit_context": _copy_optional_mapping(record.actor_audit_context),
        "review_notes": record.review_notes,
        "linked_scoring_review_id": record.linked_scoring_review_id,
        "linked_candidate_intent_id": record.linked_candidate_intent_id,
        "write_performed": record.write_performed,
        "anomaly_truth_changed": record.anomaly_truth_changed,
        "scoring_mutation_requested": record.scoring_mutation_requested,
        "runtime_influence": record.runtime_influence,
        "phase4i_mutation_requested": record.phase4i_mutation_requested,
        "created_at": record.created_at,
        "notes": record.notes,
    }


def historical_anomaly_review_record_from_dict(
    data: dict[str, Any],
) -> HistoricalAnomalyReviewRecord:
    """Deserialize anomaly review metadata from a dictionary."""

    _require_mapping(data, "anomaly_review_record")
    return HistoricalAnomalyReviewRecord(
        anomaly_review_id=str(data["anomaly_review_id"]),
        run_id=_optional_text(data.get("run_id")),
        awr_id=_optional_text(data.get("awr_id")),
        baseline_candidate_id=_optional_text(data.get("baseline_candidate_id")),
        comparison_context_id=_optional_text(data.get("comparison_context_id")),
        anomaly_id=_optional_text(data.get("anomaly_id")),
        anomaly_name=_optional_text(data.get("anomaly_name")),
        domain=_optional_text(data.get("domain")),
        anomaly_pattern=_optional_text(data.get("anomaly_pattern")),
        anomaly_severity=_optional_float(data.get("anomaly_severity")),
        review_decision=str(data.get("review_decision", "add_historical_review_note")),
        review_status=str(data.get("review_status", "proposed")),
        reviewer_actor_id=_optional_text(data.get("reviewer_actor_id")),
        actor_audit_context=_copy_optional_mapping(data.get("actor_audit_context")),
        review_notes=_optional_text(data.get("review_notes")),
        linked_scoring_review_id=_optional_text(
            data.get("linked_scoring_review_id")
        ),
        linked_candidate_intent_id=_optional_text(
            data.get("linked_candidate_intent_id")
        ),
        write_performed=_bool_from_mapping(data, "write_performed", False),
        anomaly_truth_changed=_bool_from_mapping(
            data,
            "anomaly_truth_changed",
            False,
        ),
        scoring_mutation_requested=_bool_from_mapping(
            data,
            "scoring_mutation_requested",
            False,
        ),
        runtime_influence=_bool_from_mapping(data, "runtime_influence", False),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        created_at=_optional_text(data.get("created_at")),
        notes=_optional_text(data.get("notes")),
    )


def historical_review_request_to_dict(
    request: HistoricalReviewRequest,
) -> dict[str, Any]:
    """Serialize historical review request metadata."""

    request.__post_init__()
    return {
        "request_id": request.request_id,
        "review_target_type": request.review_target_type,
        "review_target_id": request.review_target_id,
        "requested_decision": request.requested_decision,
        "actor_id": request.actor_id,
        "actor_audit_context": _copy_optional_mapping(request.actor_audit_context),
        "baseline_candidate_id": request.baseline_candidate_id,
        "comparison_context_id": request.comparison_context_id,
        "payload": dict(request.payload),
        "validation_status": request.validation_status,
        "can_route_to_governance": request.can_route_to_governance,
        "write_performed": request.write_performed,
        "truth_mutation_requested": request.truth_mutation_requested,
        "scoring_mutation_requested": request.scoring_mutation_requested,
        "runtime_influence": request.runtime_influence,
        "phase4i_mutation_requested": request.phase4i_mutation_requested,
        "notes": request.notes,
    }


def historical_review_request_from_dict(
    data: dict[str, Any],
) -> HistoricalReviewRequest:
    """Deserialize historical review request metadata from a dictionary."""

    _require_mapping(data, "historical_review_request")
    return HistoricalReviewRequest(
        request_id=str(data["request_id"]),
        review_target_type=str(data["review_target_type"]),
        review_target_id=_optional_text(data.get("review_target_id")),
        requested_decision=str(data["requested_decision"]),
        actor_id=_optional_text(data.get("actor_id")),
        actor_audit_context=_copy_optional_mapping(data.get("actor_audit_context")),
        baseline_candidate_id=_optional_text(data.get("baseline_candidate_id")),
        comparison_context_id=_optional_text(data.get("comparison_context_id")),
        payload=dict(data.get("payload") or {}),
        validation_status=str(data.get("validation_status", "valid")),
        can_route_to_governance=_bool_from_mapping(
            data,
            "can_route_to_governance",
            False,
        ),
        write_performed=_bool_from_mapping(data, "write_performed", False),
        truth_mutation_requested=_bool_from_mapping(
            data,
            "truth_mutation_requested",
            False,
        ),
        scoring_mutation_requested=_bool_from_mapping(
            data,
            "scoring_mutation_requested",
            False,
        ),
        runtime_influence=_bool_from_mapping(data, "runtime_influence", False),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        notes=_optional_text(data.get("notes")),
    )


def historical_review_validation_to_dict(
    validation: HistoricalReviewValidation,
) -> dict[str, Any]:
    """Serialize historical review validation metadata."""

    validation = validate_historical_review_validation(validation)
    return {
        "validation_id": validation.validation_id,
        "request_id": validation.request_id,
        "valid": validation.valid,
        "validation_status": validation.validation_status,
        "requested_decision": validation.requested_decision,
        "actor_present": validation.actor_present,
        "target_present": validation.target_present,
        "baseline_context_present": validation.baseline_context_present,
        "can_route_to_governance": validation.can_route_to_governance,
        "write_performed": validation.write_performed,
        "truth_mutation_requested": validation.truth_mutation_requested,
        "scoring_mutation_requested": validation.scoring_mutation_requested,
        "denied_reasons": list(validation.denied_reasons),
        "warnings": list(validation.warnings),
        "required_next_steps": list(validation.required_next_steps),
        "runtime_influence": validation.runtime_influence,
        "phase4i_mutation_requested": validation.phase4i_mutation_requested,
        "notes": validation.notes,
    }


def historical_review_validation_from_dict(
    data: dict[str, Any],
) -> HistoricalReviewValidation:
    """Deserialize historical review validation metadata from a dictionary."""

    _require_mapping(data, "historical_review_validation")
    return HistoricalReviewValidation(
        validation_id=str(data["validation_id"]),
        request_id=str(data["request_id"]),
        valid=_bool_from_mapping(data, "valid", False),
        validation_status=str(data["validation_status"]),
        requested_decision=str(data["requested_decision"]),
        actor_present=_bool_from_mapping(data, "actor_present", False),
        target_present=_bool_from_mapping(data, "target_present", False),
        baseline_context_present=_bool_from_mapping(
            data,
            "baseline_context_present",
            False,
        ),
        can_route_to_governance=_bool_from_mapping(
            data,
            "can_route_to_governance",
            False,
        ),
        write_performed=_bool_from_mapping(data, "write_performed", False),
        truth_mutation_requested=_bool_from_mapping(
            data,
            "truth_mutation_requested",
            False,
        ),
        scoring_mutation_requested=_bool_from_mapping(
            data,
            "scoring_mutation_requested",
            False,
        ),
        denied_reasons=list(data.get("denied_reasons") or []),
        warnings=list(data.get("warnings") or []),
        required_next_steps=list(data.get("required_next_steps") or []),
        runtime_influence=_bool_from_mapping(data, "runtime_influence", False),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        notes=_optional_text(data.get("notes")),
    )


def _decision_requires_actor(decision: str) -> bool:
    _require_supported(decision, HISTORICAL_REVIEW_DECISIONS, "decision")
    return decision not in _NON_ACTIONABLE_DECISIONS


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise Screen4TrendAnomalyReviewError("numeric value must not be boolean.")
    return float(value)


def _bool_from_mapping(data: dict[str, Any], field_name: str, default: bool) -> bool:
    value = data.get(field_name, default)
    if isinstance(value, bool):
        return value
    raise Screen4TrendAnomalyReviewError(f"{field_name} must be a boolean.")


def _copy_optional_mapping(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise Screen4TrendAnomalyReviewError(
            "mapping value must be a dictionary."
        )
    return dict(value)


def _require_mapping(value: Any, field_name: str) -> None:
    if not isinstance(value, dict):
        raise Screen4TrendAnomalyReviewError(f"{field_name} must be a mapping.")


def _require_optional_mapping(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, dict):
        raise Screen4TrendAnomalyReviewError(
            f"{field_name} must be a mapping or None."
        )


def _require_nonempty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise Screen4TrendAnomalyReviewError(
            f"{field_name} must be a non-empty string."
        )


def _require_optional_string(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise Screen4TrendAnomalyReviewError(
            f"{field_name} must be a string or None."
        )


def _require_at_least_one_identifier(*pairs: tuple[str, str | None]) -> None:
    if not any(_optional_text(value) for _, value in pairs):
        names = ", ".join(name for name, _ in pairs)
        raise Screen4TrendAnomalyReviewError(
            f"at least one of {names} is required."
        )


def _require_supported(value: Any, supported: tuple[str, ...], field_name: str) -> None:
    if value not in supported:
        raise Screen4TrendAnomalyReviewError(
            f"{field_name} must be one of: {', '.join(supported)}."
        )


def _require_optional_unit_score(value: Any, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise Screen4TrendAnomalyReviewError(f"{field_name} must be numeric.")
    if value < 0.0 or value > 1.0:
        raise Screen4TrendAnomalyReviewError(
            f"{field_name} must be between 0.0 and 1.0."
        )


def _require_boolean(value: Any, field_name: str) -> None:
    if not isinstance(value, bool):
        raise Screen4TrendAnomalyReviewError(f"{field_name} must be a boolean.")


def _require_string_list(value: Any, field_name: str) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise Screen4TrendAnomalyReviewError(
            f"{field_name} must be a list of strings."
        )


def _reject_true(value: bool, field_name: str) -> None:
    if value:
        raise Screen4TrendAnomalyReviewError(
            f"{field_name} must remain false in Phase 7BB."
        )


def _normalize_token(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text).strip("-")
    return text or "NONE"
