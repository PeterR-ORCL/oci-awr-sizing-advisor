"""Phase 7BC.3 Screen 4 governed historical review execution metadata.

This module creates local request, validation, result, and audit envelope
records for Screen 4 historical review workflow actions. The records are
metadata only: they do not write databases, create learning candidates, create
dataset labels, alter deterministic review truth, or activate runtime behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from src.learning.dashboard_governed_write_path import (
    GovernedWriteValidation,
    evaluate_governed_write_request,
    governed_write_request_from_dict,
)
from src.learning.dashboard_output_lifecycle import (
    DashboardOutputArtifact,
    create_validation_response_artifact,
    dashboard_output_artifact_from_dict,
    dashboard_output_artifact_to_dict,
)
from src.learning.screen4_baseline_selection import (
    historical_baseline_selection_request_from_dict,
)
from src.learning.screen4_historical_learning_bridge import (
    bridge_historical_reviews,
    historical_governance_route_from_dict,
    historical_governance_route_to_dict,
    historical_learning_candidate_intent_from_dict,
    historical_learning_candidate_intent_to_dict,
    historical_learning_signal_intent_from_dict,
    historical_learning_signal_intent_to_dict,
)
from src.learning.screen4_trend_anomaly_review import (
    HISTORICAL_REVIEW_DECISIONS,
    HISTORICAL_REVIEW_TARGET_TYPES,
    HistoricalAnomalyReviewRecord,
    HistoricalTrendReviewRecord,
    create_anomaly_review_id,
    create_trend_review_id,
    historical_anomaly_review_record_from_dict,
    historical_anomaly_review_record_to_dict,
    historical_trend_review_record_from_dict,
    historical_trend_review_record_to_dict,
)


HISTORICAL_REVIEW_EXECUTION_VALIDATION_STATUSES = (
    "valid",
    "invalid",
    "needs_actor",
    "needs_governed_write_path",
    "needs_target",
    "unsupported_action",
    "execution_metadata_only",
    "blocked_by_safety",
)

HISTORICAL_REVIEW_EXECUTION_STATUSES = (
    "proposed",
    "validated",
    "recorded_metadata_only",
    "blocked",
    "invalid",
)

_TREND_ACTIONS = (
    "approve_trend",
    "dispute_trend",
    "mark_trend_insufficient",
    "request_trend_aware_scoring_review",
    "request_scoring_threshold_review",
)

_ANOMALY_ACTIONS = (
    "approve_anomaly",
    "mark_anomaly_false_positive",
    "mark_anomaly_insufficient",
    "request_anomaly_sensitivity_review",
)


class Screen4HistoricalReviewExecutionError(ValueError):
    """Raised when Phase 7BC.3 historical review execution metadata is invalid."""


@dataclass(frozen=True)
class HistoricalReviewExecutionRequest:
    """Governed metadata request for a Screen 4 historical review action."""

    execution_request_id: str
    review_action: str
    review_target_type: str
    review_target_id: str
    actor_id: str | None = None
    actor_audit_context: dict[str, object] | None = None
    governed_write_request: dict[str, object] | None = None
    trend_review_payload: dict[str, object] = field(default_factory=dict)
    anomaly_review_payload: dict[str, object] = field(default_factory=dict)
    baseline_payload: dict[str, object] = field(default_factory=dict)
    bridge_payload: dict[str, object] = field(default_factory=dict)
    dry_run: bool = True
    requires_actor: bool = True
    requires_audit: bool = True
    requires_governed_write_path: bool = True
    write_performed: bool = False
    runtime_influence: bool = False
    phase4i_mutation_requested: bool = False
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.execution_request_id, "execution_request_id")
        _require_supported(
            self.review_action,
            HISTORICAL_REVIEW_DECISIONS,
            "review_action",
        )
        _require_supported(
            self.review_target_type,
            HISTORICAL_REVIEW_TARGET_TYPES,
            "review_target_type",
        )
        _require_optional_string(self.review_target_id, "review_target_id")
        _require_optional_string(self.actor_id, "actor_id")
        _require_optional_mapping(self.actor_audit_context, "actor_audit_context")
        _require_optional_mapping(self.governed_write_request, "governed_write_request")
        if self.governed_write_request is not None:
            governed_write_request_from_dict(dict(self.governed_write_request))
        _require_mapping(self.trend_review_payload, "trend_review_payload")
        _require_mapping(self.anomaly_review_payload, "anomaly_review_payload")
        _require_mapping(self.baseline_payload, "baseline_payload")
        _require_mapping(self.bridge_payload, "bridge_payload")
        _require_boolean(self.dry_run, "dry_run")
        _require_boolean(self.requires_actor, "requires_actor")
        _require_boolean(self.requires_audit, "requires_audit")
        _require_boolean(
            self.requires_governed_write_path,
            "requires_governed_write_path",
        )
        _require_boolean(self.write_performed, "write_performed")
        _require_boolean(self.runtime_influence, "runtime_influence")
        _require_boolean(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")
        _reject_false(self.dry_run, "dry_run")
        _reject_false(self.requires_audit, "requires_audit")
        _reject_true(self.write_performed, "write_performed")
        _reject_true(self.runtime_influence, "runtime_influence")
        _reject_true(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )


@dataclass(frozen=True)
class HistoricalReviewExecutionValidation:
    """Validation metadata for Screen 4 governed historical review execution."""

    execution_validation_id: str
    execution_request_id: str
    valid: bool
    validation_status: str
    actor_present: bool
    governed_write_valid: bool
    review_target_present: bool
    can_execute_governed_action: bool
    write_performed: bool
    denied_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_next_steps: list[str] = field(default_factory=list)
    runtime_influence: bool = False
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.execution_validation_id,
            "execution_validation_id",
        )
        _require_nonempty_string(self.execution_request_id, "execution_request_id")
        _require_boolean(self.valid, "valid")
        _require_supported(
            self.validation_status,
            HISTORICAL_REVIEW_EXECUTION_VALIDATION_STATUSES,
            "validation_status",
        )
        _require_boolean(self.actor_present, "actor_present")
        _require_boolean(self.governed_write_valid, "governed_write_valid")
        _require_boolean(self.review_target_present, "review_target_present")
        _require_boolean(
            self.can_execute_governed_action,
            "can_execute_governed_action",
        )
        _require_boolean(self.write_performed, "write_performed")
        _require_string_list(self.denied_reasons, "denied_reasons")
        _require_string_list(self.warnings, "warnings")
        _require_string_list(self.required_next_steps, "required_next_steps")
        _require_boolean(self.runtime_influence, "runtime_influence")
        _require_boolean(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.notes, "notes")
        if self.can_execute_governed_action and not self.valid:
            raise Screen4HistoricalReviewExecutionError(
                "can_execute_governed_action requires valid=true."
            )
        _reject_true(self.write_performed, "write_performed")
        _reject_true(self.runtime_influence, "runtime_influence")
        _reject_true(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )


@dataclass(frozen=True)
class HistoricalReviewAuditEnvelope:
    """Audit envelope for local Screen 4 governed metadata execution."""

    audit_envelope_id: str
    execution_request_id: str
    actor_id: str | None
    action: str
    target_type: str
    target_id: str
    governed_write_validation_id: str | None
    output_artifact_id: str | None
    audit_summary: str
    write_performed: bool = False
    runtime_influence: bool = False
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.audit_envelope_id, "audit_envelope_id")
        _require_nonempty_string(self.execution_request_id, "execution_request_id")
        _require_optional_string(self.actor_id, "actor_id")
        _require_supported(self.action, HISTORICAL_REVIEW_DECISIONS, "action")
        _require_supported(self.target_type, HISTORICAL_REVIEW_TARGET_TYPES, "target_type")
        _require_nonempty_string(self.target_id, "target_id")
        _require_optional_string(
            self.governed_write_validation_id,
            "governed_write_validation_id",
        )
        _require_optional_string(self.output_artifact_id, "output_artifact_id")
        _require_nonempty_string(self.audit_summary, "audit_summary")
        _require_boolean(self.write_performed, "write_performed")
        _require_boolean(self.runtime_influence, "runtime_influence")
        _require_boolean(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )
        _require_optional_string(self.notes, "notes")
        _reject_true(self.runtime_influence, "runtime_influence")
        _reject_true(
            self.phase4i_mutation_requested,
            "phase4i_mutation_requested",
        )


@dataclass(frozen=True)
class HistoricalReviewExecutionResult:
    """Result metadata for a Screen 4 historical review metadata action."""

    execution_result_id: str
    execution_request_id: str
    execution_status: str
    review_action: str
    trend_review_record: dict[str, object] | None = None
    anomaly_review_record: dict[str, object] | None = None
    baseline_selection_request: dict[str, object] | None = None
    candidate_intents: list[dict[str, object]] = field(default_factory=list)
    learning_signal_intents: list[dict[str, object]] = field(default_factory=list)
    governance_routes: list[dict[str, object]] = field(default_factory=list)
    audit_record: dict[str, object] | None = None
    output_artifact: dict[str, object] | None = None
    governed_action_recorded: bool = False
    candidate_created: bool = False
    dataset_label_created: bool = False
    historical_truth_changed: bool = False
    trend_truth_changed: bool = False
    anomaly_truth_changed: bool = False
    scoring_changed: bool = False
    phase4i_mutated: bool = False
    runtime_influence: bool = False
    warnings: list[str] = field(default_factory=list)
    required_next_steps: list[str] = field(default_factory=list)
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.execution_result_id, "execution_result_id")
        _require_nonempty_string(self.execution_request_id, "execution_request_id")
        _require_supported(
            self.execution_status,
            HISTORICAL_REVIEW_EXECUTION_STATUSES,
            "execution_status",
        )
        _require_supported(self.review_action, HISTORICAL_REVIEW_DECISIONS, "review_action")
        _require_optional_mapping(self.trend_review_record, "trend_review_record")
        if self.trend_review_record is not None:
            historical_trend_review_record_from_dict(dict(self.trend_review_record))
        _require_optional_mapping(self.anomaly_review_record, "anomaly_review_record")
        if self.anomaly_review_record is not None:
            historical_anomaly_review_record_from_dict(dict(self.anomaly_review_record))
        _require_optional_mapping(
            self.baseline_selection_request,
            "baseline_selection_request",
        )
        if self.baseline_selection_request is not None:
            historical_baseline_selection_request_from_dict(
                dict(self.baseline_selection_request)
            )
        _require_mapping_list(self.candidate_intents, "candidate_intents")
        for intent in self.candidate_intents:
            historical_learning_candidate_intent_from_dict(dict(intent))
        _require_mapping_list(
            self.learning_signal_intents,
            "learning_signal_intents",
        )
        for intent in self.learning_signal_intents:
            historical_learning_signal_intent_from_dict(dict(intent))
        _require_mapping_list(self.governance_routes, "governance_routes")
        for route in self.governance_routes:
            historical_governance_route_from_dict(dict(route))
        _require_optional_mapping(self.audit_record, "audit_record")
        if self.audit_record is not None:
            historical_review_audit_envelope_from_dict(dict(self.audit_record))
        _require_optional_mapping(self.output_artifact, "output_artifact")
        if self.output_artifact is not None:
            dashboard_output_artifact_from_dict(dict(self.output_artifact))
        _require_boolean(self.governed_action_recorded, "governed_action_recorded")
        _require_boolean(self.candidate_created, "candidate_created")
        _require_boolean(self.dataset_label_created, "dataset_label_created")
        _require_boolean(self.historical_truth_changed, "historical_truth_changed")
        _require_boolean(self.trend_truth_changed, "trend_truth_changed")
        _require_boolean(self.anomaly_truth_changed, "anomaly_truth_changed")
        _require_boolean(self.scoring_changed, "scoring_changed")
        _require_boolean(self.phase4i_mutated, "phase4i_mutated")
        _require_boolean(self.runtime_influence, "runtime_influence")
        _require_string_list(self.warnings, "warnings")
        _require_string_list(self.required_next_steps, "required_next_steps")
        _require_optional_string(self.notes, "notes")
        _reject_true(self.candidate_created, "candidate_created")
        _reject_true(self.dataset_label_created, "dataset_label_created")
        _reject_true(self.historical_truth_changed, "historical_truth_changed")
        _reject_true(self.trend_truth_changed, "trend_truth_changed")
        _reject_true(self.anomaly_truth_changed, "anomaly_truth_changed")
        _reject_true(self.scoring_changed, "scoring_changed")
        _reject_true(self.phase4i_mutated, "phase4i_mutated")
        _reject_true(self.runtime_influence, "runtime_influence")


def create_historical_review_execution_request_id(
    action: str,
    target_type: str,
    target_id: str,
) -> str:
    """Create a deterministic Screen 4 historical review execution request id."""

    _require_supported(action, HISTORICAL_REVIEW_DECISIONS, "action")
    _require_supported(target_type, HISTORICAL_REVIEW_TARGET_TYPES, "target_type")
    _require_nonempty_string(target_id, "target_id")
    return (
        "SCREEN4-HIST-EXEC-REQUEST-"
        f"{_normalize_token(action)}-"
        f"{_normalize_token(target_type)}-"
        f"{_normalize_token(target_id)}"
    )


def create_historical_review_execution_validation_id(request_id: str) -> str:
    """Create a deterministic Screen 4 execution validation id."""

    _require_nonempty_string(request_id, "request_id")
    return f"SCREEN4-HIST-EXEC-VALIDATION-{_normalize_token(request_id)}"


def create_historical_review_execution_result_id(
    request_id: str,
    action: str,
) -> str:
    """Create a deterministic Screen 4 execution result id."""

    _require_nonempty_string(request_id, "request_id")
    _require_supported(action, HISTORICAL_REVIEW_DECISIONS, "action")
    return (
        "SCREEN4-HIST-EXEC-RESULT-"
        f"{_normalize_token(request_id)}-"
        f"{_normalize_token(action)}"
    )


def create_historical_review_audit_envelope_id(
    request_id: str,
    action: str,
) -> str:
    """Create a deterministic Screen 4 execution audit envelope id."""

    _require_nonempty_string(request_id, "request_id")
    _require_supported(action, HISTORICAL_REVIEW_DECISIONS, "action")
    return (
        "SCREEN4-HIST-EXEC-AUDIT-"
        f"{_normalize_token(request_id)}-"
        f"{_normalize_token(action)}"
    )


def validate_historical_review_execution_request(
    request: HistoricalReviewExecutionRequest,
) -> HistoricalReviewExecutionRequest:
    """Validate Screen 4 historical review execution request metadata."""

    if not isinstance(request, HistoricalReviewExecutionRequest):
        raise Screen4HistoricalReviewExecutionError(
            "request must be a HistoricalReviewExecutionRequest instance."
        )
    request.__post_init__()
    return request


def validate_historical_review_execution_validation(
    validation: HistoricalReviewExecutionValidation,
) -> HistoricalReviewExecutionValidation:
    """Validate Screen 4 historical review execution validation metadata."""

    if not isinstance(validation, HistoricalReviewExecutionValidation):
        raise Screen4HistoricalReviewExecutionError(
            "validation must be a HistoricalReviewExecutionValidation instance."
        )
    validation.__post_init__()
    return validation


def validate_historical_review_execution_result(
    result: HistoricalReviewExecutionResult,
) -> HistoricalReviewExecutionResult:
    """Validate Screen 4 historical review execution result metadata."""

    if not isinstance(result, HistoricalReviewExecutionResult):
        raise Screen4HistoricalReviewExecutionError(
            "result must be a HistoricalReviewExecutionResult instance."
        )
    result.__post_init__()
    return result


def validate_historical_review_audit_envelope(
    envelope: HistoricalReviewAuditEnvelope,
) -> HistoricalReviewAuditEnvelope:
    """Validate Screen 4 historical review audit envelope metadata."""

    if not isinstance(envelope, HistoricalReviewAuditEnvelope):
        raise Screen4HistoricalReviewExecutionError(
            "envelope must be a HistoricalReviewAuditEnvelope instance."
        )
    envelope.__post_init__()
    return envelope


def evaluate_historical_review_execution_request(
    request: HistoricalReviewExecutionRequest,
) -> HistoricalReviewExecutionValidation:
    """Evaluate a Screen 4 governed historical review request as metadata only."""

    request = validate_historical_review_execution_request(request)
    denied_reasons: list[str] = []
    warnings = [
        "governed historical review execution is metadata-only",
        "no runtime truth changes are performed",
    ]
    required_next_steps: list[str] = []

    actor_present = bool(request.actor_id) or request.actor_audit_context is not None
    review_target_present = bool(request.review_target_id and request.review_target_id.strip())
    governed_write_validation = _evaluate_governed_write_request(request)
    governed_write_valid = bool(
        governed_write_validation and governed_write_validation.valid
    )

    validation_status = "execution_metadata_only"
    valid = True

    if request.requires_actor and not actor_present:
        valid = False
        validation_status = "needs_actor"
        denied_reasons.append("actor identity is required")
        required_next_steps.append("attach 7AE actor identity metadata")

    if request.requires_governed_write_path and not governed_write_validation:
        valid = False
        validation_status = "needs_governed_write_path"
        denied_reasons.append("7AG governed write-path request is required")
        required_next_steps.append("attach governed write request metadata")
    elif request.requires_governed_write_path and not governed_write_valid:
        valid = False
        validation_status = "needs_governed_write_path"
        denied_reasons.append("governed write-path validation is not valid")
        if governed_write_validation:
            required_next_steps.extend(governed_write_validation.required_next_steps)

    if not review_target_present:
        valid = False
        validation_status = "needs_target"
        denied_reasons.append("review target is required")
        required_next_steps.append("attach a Screen 4 review target")

    if valid:
        required_next_steps.append("record metadata-only audit envelope")
        required_next_steps.append("create output artifact metadata")

    return HistoricalReviewExecutionValidation(
        execution_validation_id=create_historical_review_execution_validation_id(
            request.execution_request_id
        ),
        execution_request_id=request.execution_request_id,
        valid=valid,
        validation_status=validation_status,
        actor_present=actor_present,
        governed_write_valid=governed_write_valid,
        review_target_present=review_target_present,
        can_execute_governed_action=valid,
        write_performed=False,
        denied_reasons=denied_reasons,
        warnings=warnings,
        required_next_steps=required_next_steps,
        runtime_influence=False,
        phase4i_mutation_requested=False,
        notes=request.notes,
    )


def execute_historical_review_metadata_action(
    request: HistoricalReviewExecutionRequest,
    validation: HistoricalReviewExecutionValidation,
) -> HistoricalReviewExecutionResult:
    """Create local Screen 4 historical review execution metadata only."""

    request = validate_historical_review_execution_request(request)
    validation = validate_historical_review_execution_validation(validation)

    output_artifact = _create_output_artifact(request, validation)
    governed_validation = _evaluate_governed_write_request(request)
    audit_envelope = _create_audit_envelope(
        request,
        governed_validation,
        output_artifact,
    )

    trend_record: HistoricalTrendReviewRecord | None = None
    anomaly_record: HistoricalAnomalyReviewRecord | None = None
    if validation.valid:
        trend_record = _create_trend_review_record(request)
        anomaly_record = _create_anomaly_review_record(request)

    bridge_result = bridge_historical_reviews(
        trend_reviews=[trend_record] if trend_record else [],
        anomaly_reviews=[anomaly_record] if anomaly_record else [],
        notes=request.notes,
    )
    execution_status = "recorded_metadata_only" if validation.valid else "blocked"

    return HistoricalReviewExecutionResult(
        execution_result_id=create_historical_review_execution_result_id(
            request.execution_request_id,
            request.review_action,
        ),
        execution_request_id=request.execution_request_id,
        execution_status=execution_status,
        review_action=request.review_action,
        trend_review_record=(
            historical_trend_review_record_to_dict(trend_record)
            if trend_record
            else None
        ),
        anomaly_review_record=(
            historical_anomaly_review_record_to_dict(anomaly_record)
            if anomaly_record
            else None
        ),
        baseline_selection_request=request.baseline_payload or None,
        candidate_intents=[
            historical_learning_candidate_intent_to_dict(intent)
            for intent in bridge_result.candidate_intents
        ],
        learning_signal_intents=[
            historical_learning_signal_intent_to_dict(intent)
            for intent in bridge_result.learning_signal_intents
        ],
        governance_routes=[
            historical_governance_route_to_dict(route)
            for route in bridge_result.governance_routes
        ],
        audit_record=historical_review_audit_envelope_to_dict(audit_envelope),
        output_artifact=dashboard_output_artifact_to_dict(output_artifact),
        governed_action_recorded=validation.valid,
        candidate_created=False,
        dataset_label_created=False,
        historical_truth_changed=False,
        trend_truth_changed=False,
        anomaly_truth_changed=False,
        scoring_changed=False,
        phase4i_mutated=False,
        runtime_influence=False,
        warnings=[*validation.warnings, *bridge_result.warnings],
        required_next_steps=[
            *validation.required_next_steps,
            *bridge_result.required_next_steps,
        ],
        notes=request.notes,
    )


def historical_review_execution_request_to_dict(
    request: HistoricalReviewExecutionRequest,
) -> dict[str, Any]:
    """Serialize Screen 4 historical review execution request metadata."""

    request = validate_historical_review_execution_request(request)
    return {
        "execution_request_id": request.execution_request_id,
        "review_action": request.review_action,
        "review_target_type": request.review_target_type,
        "review_target_id": request.review_target_id,
        "actor_id": request.actor_id,
        "actor_audit_context": request.actor_audit_context,
        "governed_write_request": request.governed_write_request,
        "trend_review_payload": dict(request.trend_review_payload),
        "anomaly_review_payload": dict(request.anomaly_review_payload),
        "baseline_payload": dict(request.baseline_payload),
        "bridge_payload": dict(request.bridge_payload),
        "dry_run": request.dry_run,
        "requires_actor": request.requires_actor,
        "requires_audit": request.requires_audit,
        "requires_governed_write_path": request.requires_governed_write_path,
        "write_performed": request.write_performed,
        "runtime_influence": request.runtime_influence,
        "phase4i_mutation_requested": request.phase4i_mutation_requested,
        "created_at": request.created_at,
        "notes": request.notes,
    }


def historical_review_execution_request_from_dict(
    data: dict[str, Any],
) -> HistoricalReviewExecutionRequest:
    """Deserialize Screen 4 historical review execution request metadata."""

    _require_mapping(data, "execution_request")
    return HistoricalReviewExecutionRequest(
        execution_request_id=str(data["execution_request_id"]),
        review_action=str(data["review_action"]),
        review_target_type=str(data["review_target_type"]),
        review_target_id=str(data.get("review_target_id", "")),
        actor_id=_optional_text(data.get("actor_id")),
        actor_audit_context=_optional_mapping_copy(data.get("actor_audit_context")),
        governed_write_request=_optional_mapping_copy(
            data.get("governed_write_request")
        ),
        trend_review_payload=dict(data.get("trend_review_payload") or {}),
        anomaly_review_payload=dict(data.get("anomaly_review_payload") or {}),
        baseline_payload=dict(data.get("baseline_payload") or {}),
        bridge_payload=dict(data.get("bridge_payload") or {}),
        dry_run=_bool_from_mapping(data, "dry_run", True),
        requires_actor=_bool_from_mapping(data, "requires_actor", True),
        requires_audit=_bool_from_mapping(data, "requires_audit", True),
        requires_governed_write_path=_bool_from_mapping(
            data,
            "requires_governed_write_path",
            True,
        ),
        write_performed=_bool_from_mapping(data, "write_performed", False),
        runtime_influence=_bool_from_mapping(data, "runtime_influence", False),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        created_at=_optional_text(data.get("created_at")),
        notes=_optional_text(data.get("notes")),
    )


def historical_review_execution_validation_to_dict(
    validation: HistoricalReviewExecutionValidation,
) -> dict[str, Any]:
    """Serialize Screen 4 historical review execution validation metadata."""

    validation = validate_historical_review_execution_validation(validation)
    return {
        "execution_validation_id": validation.execution_validation_id,
        "execution_request_id": validation.execution_request_id,
        "valid": validation.valid,
        "validation_status": validation.validation_status,
        "actor_present": validation.actor_present,
        "governed_write_valid": validation.governed_write_valid,
        "review_target_present": validation.review_target_present,
        "can_execute_governed_action": validation.can_execute_governed_action,
        "write_performed": validation.write_performed,
        "denied_reasons": list(validation.denied_reasons),
        "warnings": list(validation.warnings),
        "required_next_steps": list(validation.required_next_steps),
        "runtime_influence": validation.runtime_influence,
        "phase4i_mutation_requested": validation.phase4i_mutation_requested,
        "notes": validation.notes,
    }


def historical_review_execution_validation_from_dict(
    data: dict[str, Any],
) -> HistoricalReviewExecutionValidation:
    """Deserialize Screen 4 historical review execution validation metadata."""

    _require_mapping(data, "execution_validation")
    return HistoricalReviewExecutionValidation(
        execution_validation_id=str(data["execution_validation_id"]),
        execution_request_id=str(data["execution_request_id"]),
        valid=bool(data["valid"]),
        validation_status=str(data["validation_status"]),
        actor_present=bool(data["actor_present"]),
        governed_write_valid=bool(data["governed_write_valid"]),
        review_target_present=bool(data["review_target_present"]),
        can_execute_governed_action=bool(data["can_execute_governed_action"]),
        write_performed=_bool_from_mapping(data, "write_performed", False),
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


def historical_review_execution_result_to_dict(
    result: HistoricalReviewExecutionResult,
) -> dict[str, Any]:
    """Serialize Screen 4 historical review execution result metadata."""

    result = validate_historical_review_execution_result(result)
    return {
        "execution_result_id": result.execution_result_id,
        "execution_request_id": result.execution_request_id,
        "execution_status": result.execution_status,
        "review_action": result.review_action,
        "trend_review_record": result.trend_review_record,
        "anomaly_review_record": result.anomaly_review_record,
        "baseline_selection_request": result.baseline_selection_request,
        "candidate_intents": [dict(item) for item in result.candidate_intents],
        "learning_signal_intents": [
            dict(item) for item in result.learning_signal_intents
        ],
        "governance_routes": [dict(item) for item in result.governance_routes],
        "audit_record": result.audit_record,
        "output_artifact": result.output_artifact,
        "governed_action_recorded": result.governed_action_recorded,
        "candidate_created": result.candidate_created,
        "dataset_label_created": result.dataset_label_created,
        "historical_truth_changed": result.historical_truth_changed,
        "trend_truth_changed": result.trend_truth_changed,
        "anomaly_truth_changed": result.anomaly_truth_changed,
        "scoring_changed": result.scoring_changed,
        "phase4i_mutated": result.phase4i_mutated,
        "runtime_influence": result.runtime_influence,
        "warnings": list(result.warnings),
        "required_next_steps": list(result.required_next_steps),
        "notes": result.notes,
    }


def historical_review_execution_result_from_dict(
    data: dict[str, Any],
) -> HistoricalReviewExecutionResult:
    """Deserialize Screen 4 historical review execution result metadata."""

    _require_mapping(data, "execution_result")
    return HistoricalReviewExecutionResult(
        execution_result_id=str(data["execution_result_id"]),
        execution_request_id=str(data["execution_request_id"]),
        execution_status=str(data["execution_status"]),
        review_action=str(data["review_action"]),
        trend_review_record=_optional_mapping_copy(data.get("trend_review_record")),
        anomaly_review_record=_optional_mapping_copy(data.get("anomaly_review_record")),
        baseline_selection_request=_optional_mapping_copy(
            data.get("baseline_selection_request")
        ),
        candidate_intents=[dict(item) for item in data.get("candidate_intents", [])],
        learning_signal_intents=[
            dict(item) for item in data.get("learning_signal_intents", [])
        ],
        governance_routes=[dict(item) for item in data.get("governance_routes", [])],
        audit_record=_optional_mapping_copy(data.get("audit_record")),
        output_artifact=_optional_mapping_copy(data.get("output_artifact")),
        governed_action_recorded=_bool_from_mapping(
            data,
            "governed_action_recorded",
            False,
        ),
        candidate_created=_bool_from_mapping(data, "candidate_created", False),
        dataset_label_created=_bool_from_mapping(
            data,
            "dataset_label_created",
            False,
        ),
        historical_truth_changed=_bool_from_mapping(
            data,
            "historical_truth_changed",
            False,
        ),
        trend_truth_changed=_bool_from_mapping(data, "trend_truth_changed", False),
        anomaly_truth_changed=_bool_from_mapping(data, "anomaly_truth_changed", False),
        scoring_changed=_bool_from_mapping(data, "scoring_changed", False),
        phase4i_mutated=_bool_from_mapping(data, "phase4i_mutated", False),
        runtime_influence=_bool_from_mapping(data, "runtime_influence", False),
        warnings=list(data.get("warnings") or []),
        required_next_steps=list(data.get("required_next_steps") or []),
        notes=_optional_text(data.get("notes")),
    )


def historical_review_audit_envelope_to_dict(
    envelope: HistoricalReviewAuditEnvelope,
) -> dict[str, Any]:
    """Serialize Screen 4 historical review audit envelope metadata."""

    envelope = validate_historical_review_audit_envelope(envelope)
    return {
        "audit_envelope_id": envelope.audit_envelope_id,
        "execution_request_id": envelope.execution_request_id,
        "actor_id": envelope.actor_id,
        "action": envelope.action,
        "target_type": envelope.target_type,
        "target_id": envelope.target_id,
        "governed_write_validation_id": envelope.governed_write_validation_id,
        "output_artifact_id": envelope.output_artifact_id,
        "audit_summary": envelope.audit_summary,
        "write_performed": envelope.write_performed,
        "runtime_influence": envelope.runtime_influence,
        "phase4i_mutation_requested": envelope.phase4i_mutation_requested,
        "notes": envelope.notes,
    }


def historical_review_audit_envelope_from_dict(
    data: dict[str, Any],
) -> HistoricalReviewAuditEnvelope:
    """Deserialize Screen 4 historical review audit envelope metadata."""

    _require_mapping(data, "audit_envelope")
    return HistoricalReviewAuditEnvelope(
        audit_envelope_id=str(data["audit_envelope_id"]),
        execution_request_id=str(data["execution_request_id"]),
        actor_id=_optional_text(data.get("actor_id")),
        action=str(data["action"]),
        target_type=str(data["target_type"]),
        target_id=str(data["target_id"]),
        governed_write_validation_id=_optional_text(
            data.get("governed_write_validation_id")
        ),
        output_artifact_id=_optional_text(data.get("output_artifact_id")),
        audit_summary=str(data["audit_summary"]),
        write_performed=_bool_from_mapping(data, "write_performed", False),
        runtime_influence=_bool_from_mapping(data, "runtime_influence", False),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        notes=_optional_text(data.get("notes")),
    )


def _evaluate_governed_write_request(
    request: HistoricalReviewExecutionRequest,
) -> GovernedWriteValidation | None:
    if request.governed_write_request is None:
        return None
    governed_request = governed_write_request_from_dict(
        dict(request.governed_write_request)
    )
    return evaluate_governed_write_request(governed_request)


def _create_output_artifact(
    request: HistoricalReviewExecutionRequest,
    validation: HistoricalReviewExecutionValidation,
) -> DashboardOutputArtifact:
    status = validation.validation_status
    summary = (
        f"Screen 4 historical review action {request.review_action} "
        f"recorded as governed metadata only; validation={status}."
    )
    return create_validation_response_artifact(
        source_request_id=request.execution_request_id,
        summary=summary,
        validation_status=status,
        created_by=request.actor_id,
        notes=request.notes,
    )


def _create_audit_envelope(
    request: HistoricalReviewExecutionRequest,
    governed_validation: GovernedWriteValidation | None,
    output_artifact: DashboardOutputArtifact,
) -> HistoricalReviewAuditEnvelope:
    governed_validation_id = (
        governed_validation.validation_id if governed_validation is not None else None
    )
    return HistoricalReviewAuditEnvelope(
        audit_envelope_id=create_historical_review_audit_envelope_id(
            request.execution_request_id,
            request.review_action,
        ),
        execution_request_id=request.execution_request_id,
        actor_id=request.actor_id,
        action=request.review_action,
        target_type=request.review_target_type,
        target_id=request.review_target_id,
        governed_write_validation_id=governed_validation_id,
        output_artifact_id=output_artifact.artifact_id,
        audit_summary=(
            f"Screen 4 historical review {request.review_action} for "
            f"{request.review_target_type}:{request.review_target_id} is "
            "metadata-only; runtime_influence=false"
        ),
        write_performed=False,
        runtime_influence=False,
        phase4i_mutation_requested=False,
        notes=request.notes,
    )


def _create_trend_review_record(
    request: HistoricalReviewExecutionRequest,
) -> HistoricalTrendReviewRecord | None:
    if not _should_create_trend_review(request):
        return None
    payload = dict(request.trend_review_payload)
    run_id = _optional_text(payload.get("run_id")) or "SCREEN4-HISTORICAL-REVIEW"
    awr_id = _optional_text(payload.get("awr_id"))
    trend_id = _optional_text(payload.get("trend_id")) or request.review_target_id
    return HistoricalTrendReviewRecord(
        trend_review_id=create_trend_review_id(run_id, awr_id, trend_id),
        run_id=run_id,
        awr_id=awr_id,
        baseline_candidate_id=_optional_text(payload.get("baseline_candidate_id")),
        comparison_context_id=_optional_text(payload.get("comparison_context_id")),
        trend_id=trend_id,
        trend_name=_optional_text(payload.get("trend_name")),
        domain=_optional_text(payload.get("domain")),
        trend_direction=_optional_text(payload.get("trend_direction")),
        trend_strength=_optional_float(payload.get("trend_strength")),
        review_decision=request.review_action,
        review_status=_review_status_for_action(request.review_action),
        reviewer_actor_id=request.actor_id,
        actor_audit_context=dict(request.actor_audit_context or {}),
        review_notes=_optional_text(payload.get("review_notes")) or request.notes,
        linked_scoring_review_id=None,
        linked_candidate_intent_id=None,
        write_performed=False,
        trend_truth_changed=False,
        scoring_mutation_requested=False,
        runtime_influence=False,
        phase4i_mutation_requested=False,
        created_at=request.created_at,
        notes=request.notes,
    )


def _create_anomaly_review_record(
    request: HistoricalReviewExecutionRequest,
) -> HistoricalAnomalyReviewRecord | None:
    if not _should_create_anomaly_review(request):
        return None
    payload = dict(request.anomaly_review_payload)
    run_id = _optional_text(payload.get("run_id")) or "SCREEN4-HISTORICAL-REVIEW"
    awr_id = _optional_text(payload.get("awr_id"))
    anomaly_id = _optional_text(payload.get("anomaly_id")) or request.review_target_id
    return HistoricalAnomalyReviewRecord(
        anomaly_review_id=create_anomaly_review_id(run_id, awr_id, anomaly_id),
        run_id=run_id,
        awr_id=awr_id,
        baseline_candidate_id=_optional_text(payload.get("baseline_candidate_id")),
        comparison_context_id=_optional_text(payload.get("comparison_context_id")),
        anomaly_id=anomaly_id,
        anomaly_name=_optional_text(payload.get("anomaly_name")),
        domain=_optional_text(payload.get("domain")),
        anomaly_pattern=_optional_text(payload.get("anomaly_pattern")),
        anomaly_severity=_optional_float(payload.get("anomaly_severity")),
        review_decision=request.review_action,
        review_status=_review_status_for_action(request.review_action),
        reviewer_actor_id=request.actor_id,
        actor_audit_context=dict(request.actor_audit_context or {}),
        review_notes=_optional_text(payload.get("review_notes")) or request.notes,
        linked_scoring_review_id=None,
        linked_candidate_intent_id=None,
        write_performed=False,
        anomaly_truth_changed=False,
        scoring_mutation_requested=False,
        runtime_influence=False,
        phase4i_mutation_requested=False,
        created_at=request.created_at,
        notes=request.notes,
    )


def _should_create_trend_review(request: HistoricalReviewExecutionRequest) -> bool:
    return request.review_action in _TREND_ACTIONS or (
        request.review_action in ("request_learning_candidate", "add_historical_review_note")
        and request.review_target_type in ("trend_summary", "trend_metric")
    )


def _should_create_anomaly_review(request: HistoricalReviewExecutionRequest) -> bool:
    return request.review_action in _ANOMALY_ACTIONS or (
        request.review_action in ("request_learning_candidate", "add_historical_review_note")
        and request.review_target_type in ("anomaly_group", "anomaly_event")
    )


def _review_status_for_action(action: str) -> str:
    if action in ("approve_trend", "approve_anomaly"):
        return "approved"
    if action == "dispute_trend":
        return "disputed"
    if action in ("mark_trend_insufficient", "mark_anomaly_insufficient"):
        return "insufficient_evidence"
    if action == "mark_anomaly_false_positive":
        return "false_positive"
    if action == "request_learning_candidate":
        return "linked_to_candidate"
    if action.startswith("request_"):
        return "routed_to_governance"
    return "proposed"


def _normalize_token(value: str) -> str:
    _require_nonempty_string(value, "value")
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().upper())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "NONE"


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_mapping_copy(value: Any) -> dict[str, object] | None:
    if value is None:
        return None
    _require_mapping(value, "value")
    return dict(value)


def _bool_from_mapping(data: dict[str, Any], key: str, default: bool) -> bool:
    value = data.get(key, default)
    _require_boolean(value, key)
    return value


def _require_nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Screen4HistoricalReviewExecutionError(f"{field_name} is required.")
    return value


def _require_optional_string(value: Any, field_name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise Screen4HistoricalReviewExecutionError(
            f"{field_name} must be a string or None."
        )
    return value


def _require_supported(value: Any, supported: tuple[str, ...], field_name: str) -> str:
    if not isinstance(value, str) or value not in supported:
        raise Screen4HistoricalReviewExecutionError(
            f"Unsupported {field_name}: {value!r}."
        )
    return value


def _require_boolean(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise Screen4HistoricalReviewExecutionError(
            f"{field_name} must be boolean."
        )
    return value


def _require_mapping(value: Any, field_name: str) -> dict[Any, Any]:
    if not isinstance(value, dict):
        raise Screen4HistoricalReviewExecutionError(
            f"{field_name} must be a dictionary."
        )
    return value


def _require_optional_mapping(value: Any, field_name: str) -> dict[Any, Any] | None:
    if value is not None and not isinstance(value, dict):
        raise Screen4HistoricalReviewExecutionError(
            f"{field_name} must be a dictionary or None."
        )
    return value


def _require_mapping_list(value: Any, field_name: str) -> list[dict[str, object]]:
    if not isinstance(value, list):
        raise Screen4HistoricalReviewExecutionError(f"{field_name} must be a list.")
    for item in value:
        _require_mapping(item, field_name)
    return value


def _require_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise Screen4HistoricalReviewExecutionError(
            f"{field_name} must be a list of strings."
        )
    return value


def _reject_true(value: bool, field_name: str) -> None:
    if value:
        raise Screen4HistoricalReviewExecutionError(
            f"{field_name} must remain false in Phase 7BC.3."
        )


def _reject_false(value: bool, field_name: str) -> None:
    if not value:
        raise Screen4HistoricalReviewExecutionError(
            f"{field_name} must remain true in Phase 7BC.3."
        )
