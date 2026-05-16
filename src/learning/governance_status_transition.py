"""Phase 7BU governed status transition execution metadata.

This module defines local-only request, validation, and result metadata for
future governed status transitions. It validates metadata and safety flags only.
It does not persist records, change candidate/materialization/model/gate state,
activate runtime, deploy models, modify parser/scoring/recommendation behavior,
or mutate Phase 4I.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


GOVERNANCE_ENTITY_TYPES = (
    "learning_candidate",
    "materialization_artifact",
    "model_registry_entry",
    "runtime_gate",
    "parser_mapping_candidate",
    "scoring_review_candidate",
    "recommendation_rule_candidate",
    "governance_item",
    "workflow_record",
)

GOVERNANCE_TRANSITION_ACTIONS = (
    "mark_under_review",
    "approve_for_implementation",
    "approve_for_validation",
    "reject",
    "request_revision",
    "mark_implemented",
    "mark_validated",
    "retire",
    "supersede",
    "close",
    "request_runtime_review",
    "approve_for_shadow",
    "attach_reference",
)

GOVERNANCE_TRANSITION_VALIDATION_STATUSES = (
    "valid_metadata_only",
    "invalid",
    "needs_actor",
    "needs_idempotency_key",
    "needs_rollback_reference",
    "needs_validation_reference",
    "needs_payload",
    "unsupported_record_type",
    "unsupported_entity_type",
    "unsupported_transition",
    "db_write_not_allowed_in_this_phase",
    "runtime_activation_not_allowed",
)

GOVERNANCE_TRANSITION_RESULT_STATUSES = (
    "valid_for_future_persistence",
    "rejected_metadata_only",
    "invalid_metadata",
    "db_write_not_allowed_in_this_phase",
    "runtime_activation_not_allowed",
)

ALLOWED_STATUS_TRANSITIONS = {
    "proposed": ("under_review",),
    "under_review": (
        "approved_for_implementation",
        "approved_for_validation",
        "rejected",
        "needs_revision",
        "runtime_review_requested",
        "approved_for_shadow",
    ),
    "needs_revision": ("under_review", "rejected"),
    "approved_for_implementation": ("approved_for_validation", "implemented"),
    "approved_for_validation": ("implemented", "validated"),
    "implemented": ("validated",),
    "validated": ("closed",),
    "runtime_review_requested": ("under_review", "closed"),
    "approved_for_shadow": ("runtime_review_requested", "closed"),
    "__any__": ("retired", "superseded"),
}

STATE_CHANGING_TRANSITION_ACTIONS = (
    "mark_under_review",
    "approve_for_implementation",
    "approve_for_validation",
    "reject",
    "request_revision",
    "mark_implemented",
    "mark_validated",
    "retire",
    "supersede",
    "close",
    "request_runtime_review",
    "approve_for_shadow",
)

VALIDATION_REFERENCE_REQUIRED_ACTIONS = (
    "approve_for_implementation",
    "approve_for_validation",
    "mark_implemented",
    "mark_validated",
    "request_runtime_review",
    "approve_for_shadow",
)


class GovernanceStatusTransitionError(ValueError):
    """Raised when Phase 7BU status transition metadata is invalid."""


@dataclass(frozen=True)
class GovernanceStatusTransitionRequest:
    """Local request to transition a governed entity in a future phase."""

    transition_request_id: str
    entity_type: str
    entity_id: str
    from_status: str
    to_status: str
    transition_action: str
    actor_id: str | None = None
    actor_audit_context: dict[str, Any] | None = None
    validation_reference: str | None = None
    rollback_reference: str | None = None
    idempotency_key: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    transition_requested: bool = True
    transition_performed: bool = False
    status_changed: bool = False
    db_write_performed: bool = False
    runtime_activation_requested: bool = False
    runtime_active: bool = False
    phase4i_mutation_requested: bool = False
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.transition_request_id, "transition_request_id")
        _require_nonempty_string(self.entity_type, "entity_type")
        _require_nonempty_string(self.entity_id, "entity_id")
        _require_nonempty_string(self.from_status, "from_status")
        _require_nonempty_string(self.to_status, "to_status")
        _require_nonempty_string(self.transition_action, "transition_action")
        _require_optional_string(self.actor_id, "actor_id")
        _require_optional_mapping(self.actor_audit_context, "actor_audit_context")
        _require_optional_string(self.validation_reference, "validation_reference")
        _require_optional_string(self.rollback_reference, "rollback_reference")
        _require_optional_string(self.idempotency_key, "idempotency_key")
        _require_mapping(self.payload, "payload")
        _require_boolean(self.transition_requested, "transition_requested")
        _require_false(self.transition_performed, "transition_performed")
        _require_false(self.status_changed, "status_changed")
        _require_false(self.db_write_performed, "db_write_performed")
        _require_false(
            self.runtime_activation_requested,
            "runtime_activation_requested",
        )
        _require_false(self.runtime_active, "runtime_active")
        _require_false(self.phase4i_mutation_requested, "phase4i_mutation_requested")
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")


@dataclass(frozen=True)
class GovernanceStatusTransitionValidation:
    """Validation result for a future governed status transition."""

    transition_validation_id: str
    transition_request_id: str
    valid: bool
    validation_status: str
    entity_type: str
    transition_action: str
    actor_present: bool
    validation_reference_present: bool
    rollback_reference_present: bool
    idempotency_key_present: bool
    allowed_transition: bool
    can_transition_later: bool
    transition_performed: bool
    status_changed: bool
    db_write_performed: bool
    runtime_active: bool
    denied_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_next_steps: list[str] = field(default_factory=list)
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.transition_validation_id,
            "transition_validation_id",
        )
        _require_nonempty_string(self.transition_request_id, "transition_request_id")
        _require_boolean(self.valid, "valid")
        _require_supported(
            self.validation_status,
            GOVERNANCE_TRANSITION_VALIDATION_STATUSES,
            "validation_status",
        )
        _require_nonempty_string(self.entity_type, "entity_type")
        _require_nonempty_string(self.transition_action, "transition_action")
        _require_boolean(self.actor_present, "actor_present")
        _require_boolean(
            self.validation_reference_present,
            "validation_reference_present",
        )
        _require_boolean(self.rollback_reference_present, "rollback_reference_present")
        _require_boolean(self.idempotency_key_present, "idempotency_key_present")
        _require_boolean(self.allowed_transition, "allowed_transition")
        _require_boolean(self.can_transition_later, "can_transition_later")
        _require_false(self.transition_performed, "transition_performed")
        _require_false(self.status_changed, "status_changed")
        _require_false(self.db_write_performed, "db_write_performed")
        _require_false(self.runtime_active, "runtime_active")
        _require_list_of_strings(self.denied_reasons, "denied_reasons")
        _require_list_of_strings(self.warnings, "warnings")
        _require_list_of_strings(self.required_next_steps, "required_next_steps")
        _require_false(self.phase4i_mutation_requested, "phase4i_mutation_requested")
        _require_optional_string(self.notes, "notes")
        if self.can_transition_later and not self.valid:
            raise GovernanceStatusTransitionError(
                "can_transition_later can be true only when validation is valid."
            )
        if self.valid and self.validation_status != "valid_metadata_only":
            raise GovernanceStatusTransitionError(
                "valid transition metadata must use valid_metadata_only status."
            )


@dataclass(frozen=True)
class GovernanceStatusTransitionResult:
    """Local result metadata for a future governed status transition."""

    transition_result_id: str
    transition_request_id: str
    transition_validation_id: str
    entity_type: str
    entity_id: str
    from_status: str
    to_status: str
    transition_action: str
    result_status: str
    transition_performed: bool = False
    status_changed: bool = False
    db_write_performed: bool = False
    runtime_active: bool = False
    audit_record: dict[str, Any] | None = None
    transaction_metadata: dict[str, Any] | None = None
    rollback_reference: str | None = None
    denied_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_next_steps: list[str] = field(default_factory=list)
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.transition_result_id, "transition_result_id")
        _require_nonempty_string(self.transition_request_id, "transition_request_id")
        _require_nonempty_string(
            self.transition_validation_id,
            "transition_validation_id",
        )
        _require_supported(self.entity_type, GOVERNANCE_ENTITY_TYPES, "entity_type")
        _require_nonempty_string(self.entity_id, "entity_id")
        _require_nonempty_string(self.from_status, "from_status")
        _require_nonempty_string(self.to_status, "to_status")
        _require_supported(
            self.transition_action,
            GOVERNANCE_TRANSITION_ACTIONS,
            "transition_action",
        )
        _require_supported(
            self.result_status,
            GOVERNANCE_TRANSITION_RESULT_STATUSES,
            "result_status",
        )
        _require_false(self.transition_performed, "transition_performed")
        _require_false(self.status_changed, "status_changed")
        _require_false(self.db_write_performed, "db_write_performed")
        _require_false(self.runtime_active, "runtime_active")
        _require_optional_mapping(self.audit_record, "audit_record")
        _require_optional_mapping(self.transaction_metadata, "transaction_metadata")
        _require_optional_string(self.rollback_reference, "rollback_reference")
        _require_list_of_strings(self.denied_reasons, "denied_reasons")
        _require_list_of_strings(self.warnings, "warnings")
        _require_list_of_strings(self.required_next_steps, "required_next_steps")
        _require_false(self.phase4i_mutation_requested, "phase4i_mutation_requested")
        _require_optional_string(self.notes, "notes")


def create_transition_request_id(
    entity_type: str,
    entity_id: str,
    transition_action: str,
) -> str:
    """Create a deterministic governed status transition request id."""

    _require_supported(entity_type, GOVERNANCE_ENTITY_TYPES, "entity_type")
    _require_nonempty_string(entity_id, "entity_id")
    _require_supported(
        transition_action,
        GOVERNANCE_TRANSITION_ACTIONS,
        "transition_action",
    )
    return (
        "GOVERNANCE-STATUS-TRANSITION-REQUEST-"
        f"{_normalize_token(entity_type)}-"
        f"{_normalize_token(entity_id)}-"
        f"{_normalize_token(transition_action)}"
    )


def create_transition_validation_id(transition_request_id: str) -> str:
    """Create a deterministic governed status transition validation id."""

    _require_nonempty_string(transition_request_id, "transition_request_id")
    return (
        "GOVERNANCE-STATUS-TRANSITION-VALIDATION-"
        f"{_normalize_token(transition_request_id)}"
    )


def create_transition_result_id(transition_request_id: str) -> str:
    """Create a deterministic governed status transition result id."""

    _require_nonempty_string(transition_request_id, "transition_request_id")
    return (
        "GOVERNANCE-STATUS-TRANSITION-RESULT-"
        f"{_normalize_token(transition_request_id)}"
    )


def validate_governance_status_transition_request(
    request: GovernanceStatusTransitionRequest,
) -> GovernanceStatusTransitionRequest:
    """Validate transition metadata without changing status."""

    if not isinstance(request, GovernanceStatusTransitionRequest):
        raise GovernanceStatusTransitionError(
            "request must be a GovernanceStatusTransitionRequest instance."
        )
    request.__post_init__()
    _require_supported(request.entity_type, GOVERNANCE_ENTITY_TYPES, "entity_type")
    _require_supported(
        request.transition_action,
        GOVERNANCE_TRANSITION_ACTIONS,
        "transition_action",
    )
    _require_nonempty_string(request.actor_id, "actor_id")
    _require_nonempty_string(request.idempotency_key, "idempotency_key")
    if _requires_rollback_reference(request.transition_action):
        _require_nonempty_string(request.rollback_reference, "rollback_reference")
    if _requires_validation_reference(request.transition_action):
        _require_nonempty_string(
            request.validation_reference,
            "validation_reference",
        )
    if not is_allowed_status_transition(request.from_status, request.to_status):
        raise GovernanceStatusTransitionError(
            "status transition is not allowed by Phase 7BU metadata."
        )
    return request


def evaluate_governance_status_transition_request(
    request: GovernanceStatusTransitionRequest,
) -> GovernanceStatusTransitionValidation:
    """Evaluate status transition metadata for future persistence only."""

    if not isinstance(request, GovernanceStatusTransitionRequest):
        raise GovernanceStatusTransitionError(
            "request must be a GovernanceStatusTransitionRequest instance."
        )
    request.__post_init__()

    denied_reasons: list[str] = []
    warnings = [
        "Phase 7BU metadata only; transition_performed=false.",
        "No status change is performed in 7BU.",
        "No DB write or runtime activation is performed in 7BU.",
    ]
    required_next_steps: list[str] = []

    actor_present = bool(_optional_text(request.actor_id))
    validation_reference_present = bool(_optional_text(request.validation_reference))
    rollback_reference_present = bool(_optional_text(request.rollback_reference))
    idempotency_key_present = bool(_optional_text(request.idempotency_key))
    entity_supported = request.entity_type in GOVERNANCE_ENTITY_TYPES
    action_supported = request.transition_action in GOVERNANCE_TRANSITION_ACTIONS
    allowed_transition = is_allowed_status_transition(
        request.from_status,
        request.to_status,
    )

    valid = True
    validation_status = "valid_metadata_only"

    if not entity_supported:
        valid = False
        validation_status = "unsupported_entity_type"
        denied_reasons.append("entity_type is not supported")
        required_next_steps.append("choose a supported governed entity type")
    elif not action_supported:
        valid = False
        validation_status = "unsupported_transition"
        denied_reasons.append("transition_action is not supported")
        required_next_steps.append("choose a supported transition action")
    elif not actor_present:
        valid = False
        validation_status = "needs_actor"
        denied_reasons.append("actor_id is required")
        required_next_steps.append("attach actor identity metadata")
    elif not idempotency_key_present:
        valid = False
        validation_status = "needs_idempotency_key"
        denied_reasons.append("idempotency_key is required")
        required_next_steps.append("attach deterministic idempotency key")
    elif (
        _requires_rollback_reference(request.transition_action)
        and not rollback_reference_present
    ):
        valid = False
        validation_status = "needs_rollback_reference"
        denied_reasons.append("rollback_reference is required")
        required_next_steps.append("attach rollback reference metadata")
    elif (
        _requires_validation_reference(request.transition_action)
        and not validation_reference_present
    ):
        valid = False
        validation_status = "needs_validation_reference"
        denied_reasons.append("validation_reference is required")
        required_next_steps.append("attach validation reference metadata")
    elif not allowed_transition:
        valid = False
        validation_status = "invalid"
        denied_reasons.append("from_status to to_status is not allowed")
        required_next_steps.append("choose an allowed transition metadata pair")
    else:
        required_next_steps.append("future repository layer may persist transition")
        required_next_steps.append("future write must retain audit and rollback links")

    return validate_governance_status_transition_validation(
        GovernanceStatusTransitionValidation(
            transition_validation_id=create_transition_validation_id(
                request.transition_request_id
            ),
            transition_request_id=request.transition_request_id,
            valid=valid,
            validation_status=validation_status,
            entity_type=request.entity_type,
            transition_action=request.transition_action,
            actor_present=actor_present,
            validation_reference_present=validation_reference_present,
            rollback_reference_present=rollback_reference_present,
            idempotency_key_present=idempotency_key_present,
            allowed_transition=allowed_transition,
            can_transition_later=valid and request.transition_requested,
            transition_performed=False,
            status_changed=False,
            db_write_performed=False,
            runtime_active=False,
            denied_reasons=denied_reasons,
            warnings=warnings,
            required_next_steps=required_next_steps,
            phase4i_mutation_requested=False,
            notes=request.notes,
        )
    )


def validate_governance_status_transition_validation(
    validation: GovernanceStatusTransitionValidation,
) -> GovernanceStatusTransitionValidation:
    """Validate status transition validation metadata."""

    if not isinstance(validation, GovernanceStatusTransitionValidation):
        raise GovernanceStatusTransitionError(
            "validation must be a GovernanceStatusTransitionValidation instance."
        )
    validation.__post_init__()
    return validation


def create_governance_status_transition_result(
    request: GovernanceStatusTransitionRequest,
    validation: GovernanceStatusTransitionValidation,
    audit_record: dict[str, Any] | None = None,
    transaction_metadata: dict[str, Any] | None = None,
) -> GovernanceStatusTransitionResult:
    """Create local transition result metadata without changing status."""

    request.__post_init__()
    validation = validate_governance_status_transition_validation(validation)
    _require_optional_mapping(audit_record, "audit_record")
    _require_optional_mapping(transaction_metadata, "transaction_metadata")
    result_status = (
        "valid_for_future_persistence"
        if validation.valid
        else "rejected_metadata_only"
    )
    return GovernanceStatusTransitionResult(
        transition_result_id=create_transition_result_id(request.transition_request_id),
        transition_request_id=request.transition_request_id,
        transition_validation_id=validation.transition_validation_id,
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        from_status=request.from_status,
        to_status=request.to_status,
        transition_action=request.transition_action,
        result_status=result_status,
        transition_performed=False,
        status_changed=False,
        db_write_performed=False,
        runtime_active=False,
        audit_record=_copy_optional_mapping(audit_record),
        transaction_metadata=_copy_optional_mapping(transaction_metadata),
        rollback_reference=request.rollback_reference,
        denied_reasons=list(validation.denied_reasons),
        warnings=list(validation.warnings),
        required_next_steps=list(validation.required_next_steps),
        phase4i_mutation_requested=False,
        notes=request.notes,
    )


def validate_governance_status_transition_result(
    result: GovernanceStatusTransitionResult,
) -> GovernanceStatusTransitionResult:
    """Validate local status transition result metadata."""

    if not isinstance(result, GovernanceStatusTransitionResult):
        raise GovernanceStatusTransitionError(
            "result must be a GovernanceStatusTransitionResult instance."
        )
    result.__post_init__()
    return result


def is_allowed_status_transition(from_status: str, to_status: str) -> bool:
    """Return whether a transition pair is allowed as metadata only."""

    _require_nonempty_string(from_status, "from_status")
    _require_nonempty_string(to_status, "to_status")
    if to_status in ALLOWED_STATUS_TRANSITIONS["__any__"]:
        return from_status != to_status
    return to_status in ALLOWED_STATUS_TRANSITIONS.get(from_status, ())


def governance_status_transition_request_to_dict(
    request: GovernanceStatusTransitionRequest,
) -> dict[str, Any]:
    """Serialize status transition request metadata."""

    request.__post_init__()
    return {
        "transition_request_id": request.transition_request_id,
        "entity_type": request.entity_type,
        "entity_id": request.entity_id,
        "from_status": request.from_status,
        "to_status": request.to_status,
        "transition_action": request.transition_action,
        "actor_id": request.actor_id,
        "actor_audit_context": _copy_optional_mapping(request.actor_audit_context),
        "validation_reference": request.validation_reference,
        "rollback_reference": request.rollback_reference,
        "idempotency_key": request.idempotency_key,
        "payload": dict(request.payload),
        "transition_requested": request.transition_requested,
        "transition_performed": request.transition_performed,
        "status_changed": request.status_changed,
        "db_write_performed": request.db_write_performed,
        "runtime_activation_requested": request.runtime_activation_requested,
        "runtime_active": request.runtime_active,
        "phase4i_mutation_requested": request.phase4i_mutation_requested,
        "created_at": request.created_at,
        "notes": request.notes,
    }


def governance_status_transition_request_from_dict(
    data: dict[str, Any],
) -> GovernanceStatusTransitionRequest:
    """Deserialize status transition request metadata."""

    _require_mapping(data, "data")
    return GovernanceStatusTransitionRequest(
        transition_request_id=str(data["transition_request_id"]),
        entity_type=str(data["entity_type"]),
        entity_id=str(data["entity_id"]),
        from_status=str(data["from_status"]),
        to_status=str(data["to_status"]),
        transition_action=str(data["transition_action"]),
        actor_id=_optional_text(data.get("actor_id")),
        actor_audit_context=_copy_optional_mapping(data.get("actor_audit_context")),
        validation_reference=_optional_text(data.get("validation_reference")),
        rollback_reference=_optional_text(data.get("rollback_reference")),
        idempotency_key=_optional_text(data.get("idempotency_key")),
        payload=dict(data.get("payload") or {}),
        transition_requested=_bool_from_mapping(data, "transition_requested", True),
        transition_performed=_bool_from_mapping(data, "transition_performed", False),
        status_changed=_bool_from_mapping(data, "status_changed", False),
        db_write_performed=_bool_from_mapping(data, "db_write_performed", False),
        runtime_activation_requested=_bool_from_mapping(
            data,
            "runtime_activation_requested",
            False,
        ),
        runtime_active=_bool_from_mapping(data, "runtime_active", False),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        created_at=_optional_text(data.get("created_at")),
        notes=_optional_text(data.get("notes")),
    )


def governance_status_transition_validation_to_dict(
    validation: GovernanceStatusTransitionValidation,
) -> dict[str, Any]:
    """Serialize status transition validation metadata."""

    validation.__post_init__()
    return {
        "transition_validation_id": validation.transition_validation_id,
        "transition_request_id": validation.transition_request_id,
        "valid": validation.valid,
        "validation_status": validation.validation_status,
        "entity_type": validation.entity_type,
        "transition_action": validation.transition_action,
        "actor_present": validation.actor_present,
        "validation_reference_present": validation.validation_reference_present,
        "rollback_reference_present": validation.rollback_reference_present,
        "idempotency_key_present": validation.idempotency_key_present,
        "allowed_transition": validation.allowed_transition,
        "can_transition_later": validation.can_transition_later,
        "transition_performed": validation.transition_performed,
        "status_changed": validation.status_changed,
        "db_write_performed": validation.db_write_performed,
        "runtime_active": validation.runtime_active,
        "denied_reasons": list(validation.denied_reasons),
        "warnings": list(validation.warnings),
        "required_next_steps": list(validation.required_next_steps),
        "phase4i_mutation_requested": validation.phase4i_mutation_requested,
        "notes": validation.notes,
    }


def governance_status_transition_validation_from_dict(
    data: dict[str, Any],
) -> GovernanceStatusTransitionValidation:
    """Deserialize status transition validation metadata."""

    _require_mapping(data, "data")
    return GovernanceStatusTransitionValidation(
        transition_validation_id=str(data["transition_validation_id"]),
        transition_request_id=str(data["transition_request_id"]),
        valid=_bool_from_mapping(data, "valid", False),
        validation_status=str(data["validation_status"]),
        entity_type=str(data["entity_type"]),
        transition_action=str(data["transition_action"]),
        actor_present=_bool_from_mapping(data, "actor_present", False),
        validation_reference_present=_bool_from_mapping(
            data,
            "validation_reference_present",
            False,
        ),
        rollback_reference_present=_bool_from_mapping(
            data,
            "rollback_reference_present",
            False,
        ),
        idempotency_key_present=_bool_from_mapping(
            data,
            "idempotency_key_present",
            False,
        ),
        allowed_transition=_bool_from_mapping(data, "allowed_transition", False),
        can_transition_later=_bool_from_mapping(data, "can_transition_later", False),
        transition_performed=_bool_from_mapping(data, "transition_performed", False),
        status_changed=_bool_from_mapping(data, "status_changed", False),
        db_write_performed=_bool_from_mapping(data, "db_write_performed", False),
        runtime_active=_bool_from_mapping(data, "runtime_active", False),
        denied_reasons=list(data.get("denied_reasons") or []),
        warnings=list(data.get("warnings") or []),
        required_next_steps=list(data.get("required_next_steps") or []),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        notes=_optional_text(data.get("notes")),
    )


def governance_status_transition_result_to_dict(
    result: GovernanceStatusTransitionResult,
) -> dict[str, Any]:
    """Serialize status transition result metadata."""

    result.__post_init__()
    return {
        "transition_result_id": result.transition_result_id,
        "transition_request_id": result.transition_request_id,
        "transition_validation_id": result.transition_validation_id,
        "entity_type": result.entity_type,
        "entity_id": result.entity_id,
        "from_status": result.from_status,
        "to_status": result.to_status,
        "transition_action": result.transition_action,
        "result_status": result.result_status,
        "transition_performed": result.transition_performed,
        "status_changed": result.status_changed,
        "db_write_performed": result.db_write_performed,
        "runtime_active": result.runtime_active,
        "audit_record": _copy_optional_mapping(result.audit_record),
        "transaction_metadata": _copy_optional_mapping(result.transaction_metadata),
        "rollback_reference": result.rollback_reference,
        "denied_reasons": list(result.denied_reasons),
        "warnings": list(result.warnings),
        "required_next_steps": list(result.required_next_steps),
        "phase4i_mutation_requested": result.phase4i_mutation_requested,
        "notes": result.notes,
    }


def governance_status_transition_result_from_dict(
    data: dict[str, Any],
) -> GovernanceStatusTransitionResult:
    """Deserialize status transition result metadata."""

    _require_mapping(data, "data")
    return GovernanceStatusTransitionResult(
        transition_result_id=str(data["transition_result_id"]),
        transition_request_id=str(data["transition_request_id"]),
        transition_validation_id=str(data["transition_validation_id"]),
        entity_type=str(data["entity_type"]),
        entity_id=str(data["entity_id"]),
        from_status=str(data["from_status"]),
        to_status=str(data["to_status"]),
        transition_action=str(data["transition_action"]),
        result_status=str(data["result_status"]),
        transition_performed=_bool_from_mapping(data, "transition_performed", False),
        status_changed=_bool_from_mapping(data, "status_changed", False),
        db_write_performed=_bool_from_mapping(data, "db_write_performed", False),
        runtime_active=_bool_from_mapping(data, "runtime_active", False),
        audit_record=_copy_optional_mapping(data.get("audit_record")),
        transaction_metadata=_copy_optional_mapping(data.get("transaction_metadata")),
        rollback_reference=_optional_text(data.get("rollback_reference")),
        denied_reasons=list(data.get("denied_reasons") or []),
        warnings=list(data.get("warnings") or []),
        required_next_steps=list(data.get("required_next_steps") or []),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        notes=_optional_text(data.get("notes")),
    )


def _requires_rollback_reference(transition_action: str) -> bool:
    return transition_action in STATE_CHANGING_TRANSITION_ACTIONS


def _requires_validation_reference(transition_action: str) -> bool:
    return transition_action in VALIDATION_REFERENCE_REQUIRED_ACTIONS


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_from_mapping(data: dict[str, Any], field_name: str, default: bool) -> bool:
    value = data.get(field_name, default)
    if isinstance(value, bool):
        return value
    raise GovernanceStatusTransitionError(f"{field_name} must be a boolean.")


def _copy_optional_mapping(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise GovernanceStatusTransitionError("mapping value must be a dictionary.")
    return dict(value)


def _require_mapping(value: Any, field_name: str) -> None:
    if not isinstance(value, dict):
        raise GovernanceStatusTransitionError(f"{field_name} must be a mapping.")


def _require_optional_mapping(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, dict):
        raise GovernanceStatusTransitionError(
            f"{field_name} must be a mapping or None."
        )


def _require_nonempty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise GovernanceStatusTransitionError(
            f"{field_name} must be a non-empty string."
        )


def _require_optional_string(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise GovernanceStatusTransitionError(
            f"{field_name} must be a string or None."
        )


def _require_supported(value: Any, supported: tuple[str, ...], field_name: str) -> None:
    if value not in supported:
        raise GovernanceStatusTransitionError(
            f"{field_name} must be one of: {', '.join(supported)}."
        )


def _require_boolean(value: Any, field_name: str) -> None:
    if not isinstance(value, bool):
        raise GovernanceStatusTransitionError(f"{field_name} must be a boolean.")


def _require_false(value: Any, field_name: str) -> None:
    _require_boolean(value, field_name)
    if value:
        raise GovernanceStatusTransitionError(
            f"{field_name} must remain false in Phase 7BU."
        )


def _require_list_of_strings(value: Any, field_name: str) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise GovernanceStatusTransitionError(
            f"{field_name} must be a list of strings."
        )


def _normalize_token(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text).strip("-")
    return text or "NONE"
