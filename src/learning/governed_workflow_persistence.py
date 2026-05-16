"""Phase 7BU governed workflow persistence and audit metadata.

This module defines local-only request, validation, audit, and transaction
metadata for future governed workflow persistence. It validates envelope shape
and safety flags only. It does not persist records, write files, connect to a
database, invoke runtime materialization, change workflow state, or mutate
Phase 4I.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any


WORKFLOW_RECORD_TYPES = (
    "diagnostic_review",
    "evidence_review",
    "screen3_reanalysis_request",
    "screen3_comparison_artifact",
    "recommendation_decision",
    "action_tracking",
    "outcome_capture",
    "feedback_intent",
    "parser_unknown_review",
    "parser_mapping_intent",
    "knowledge_artifact_review",
    "historical_review",
    "baseline_selection",
    "trend_anomaly_review",
    "learning_candidate_review",
    "materialization_review",
    "model_registry_review",
    "runtime_gate_review",
    "governance_audit",
    "output_artifact",
)

PERSISTENCE_VALIDATION_STATUSES = (
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

TRANSACTION_SCOPES = (
    "workflow_record",
    "workflow_screen",
    "governance_entity",
    "audit_only",
    "runtime_materialization_execution",
)

DUPLICATE_HANDLING_MODES = (
    "reject_duplicate",
    "return_existing",
    "idempotent_replay_metadata_only",
)

DEFAULT_TRANSACTION_SCOPE = "runtime_materialization_execution"
DEFAULT_DUPLICATE_HANDLING = "idempotent_replay_metadata_only"


class GovernedWorkflowPersistenceError(ValueError):
    """Raised when Phase 7BU persistence metadata violates safety rules."""


@dataclass(frozen=True)
class GovernedWorkflowPersistenceRequest:
    """Local request to persist a governed workflow record in a future phase."""

    persistence_request_id: str
    workflow_record_type: str
    workflow_record_id: str
    source_screen: str | None = None
    actor_id: str | None = None
    actor_audit_context: dict[str, Any] | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    idempotency_key: str | None = None
    transaction_group_id: str | None = None
    rollback_reference: str | None = None
    dry_run: bool = True
    persistence_requested: bool = True
    persistence_performed: bool = False
    db_write_performed: bool = False
    runtime_mutation_requested: bool = False
    phase4i_mutation_requested: bool = False
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.persistence_request_id,
            "persistence_request_id",
        )
        _require_nonempty_string(self.workflow_record_type, "workflow_record_type")
        _require_nonempty_string(self.workflow_record_id, "workflow_record_id")
        _require_optional_string(self.source_screen, "source_screen")
        _require_optional_string(self.actor_id, "actor_id")
        _require_optional_mapping(self.actor_audit_context, "actor_audit_context")
        _require_mapping(self.payload, "payload")
        _require_optional_string(self.idempotency_key, "idempotency_key")
        _require_optional_string(self.transaction_group_id, "transaction_group_id")
        _require_optional_string(self.rollback_reference, "rollback_reference")
        _require_boolean(self.dry_run, "dry_run")
        _require_boolean(self.persistence_requested, "persistence_requested")
        _require_false(self.persistence_performed, "persistence_performed")
        _require_false(self.db_write_performed, "db_write_performed")
        _require_false(self.runtime_mutation_requested, "runtime_mutation_requested")
        _require_false(self.phase4i_mutation_requested, "phase4i_mutation_requested")
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")
        if not self.dry_run:
            raise GovernedWorkflowPersistenceError(
                "dry_run must remain true in Phase 7BU."
            )


@dataclass(frozen=True)
class GovernedWorkflowPersistenceValidation:
    """Validation result for future governed workflow persistence."""

    persistence_validation_id: str
    persistence_request_id: str
    valid: bool
    validation_status: str
    workflow_record_type: str
    actor_present: bool
    idempotency_key_present: bool
    rollback_reference_present: bool
    payload_present: bool
    can_persist_later: bool
    persistence_performed: bool
    db_write_performed: bool
    denied_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_next_steps: list[str] = field(default_factory=list)
    runtime_mutation_requested: bool = False
    phase4i_mutation_requested: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(
            self.persistence_validation_id,
            "persistence_validation_id",
        )
        _require_nonempty_string(self.persistence_request_id, "persistence_request_id")
        _require_boolean(self.valid, "valid")
        _require_supported(
            self.validation_status,
            PERSISTENCE_VALIDATION_STATUSES,
            "validation_status",
        )
        _require_nonempty_string(self.workflow_record_type, "workflow_record_type")
        _require_boolean(self.actor_present, "actor_present")
        _require_boolean(self.idempotency_key_present, "idempotency_key_present")
        _require_boolean(self.rollback_reference_present, "rollback_reference_present")
        _require_boolean(self.payload_present, "payload_present")
        _require_boolean(self.can_persist_later, "can_persist_later")
        _require_false(self.persistence_performed, "persistence_performed")
        _require_false(self.db_write_performed, "db_write_performed")
        _require_list_of_strings(self.denied_reasons, "denied_reasons")
        _require_list_of_strings(self.warnings, "warnings")
        _require_list_of_strings(self.required_next_steps, "required_next_steps")
        _require_false(self.runtime_mutation_requested, "runtime_mutation_requested")
        _require_false(self.phase4i_mutation_requested, "phase4i_mutation_requested")
        _require_optional_string(self.notes, "notes")
        if self.can_persist_later and not self.valid:
            raise GovernedWorkflowPersistenceError(
                "can_persist_later can be true only when validation is valid."
            )
        if self.valid and self.validation_status != "valid_metadata_only":
            raise GovernedWorkflowPersistenceError(
                "valid persistence metadata must use valid_metadata_only status."
            )


@dataclass(frozen=True)
class GovernedWorkflowAuditRecord:
    """Local audit metadata for a governed workflow persistence request."""

    audit_record_id: str
    workflow_record_type: str
    workflow_record_id: str
    actor_id: str | None
    action: str
    source_screen: str | None
    transaction_group_id: str | None
    idempotency_key: str | None
    audit_summary: str
    payload_hash: str
    persisted: bool = False
    db_write_performed: bool = False
    runtime_mutation_performed: bool = False
    phase4i_mutation_performed: bool = False
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.audit_record_id, "audit_record_id")
        _require_supported(
            self.workflow_record_type,
            WORKFLOW_RECORD_TYPES,
            "workflow_record_type",
        )
        _require_nonempty_string(self.workflow_record_id, "workflow_record_id")
        _require_optional_string(self.actor_id, "actor_id")
        _require_nonempty_string(self.action, "action")
        _require_optional_string(self.source_screen, "source_screen")
        _require_optional_string(self.transaction_group_id, "transaction_group_id")
        _require_optional_string(self.idempotency_key, "idempotency_key")
        _require_nonempty_string(self.audit_summary, "audit_summary")
        _require_nonempty_string(self.payload_hash, "payload_hash")
        _require_false(self.persisted, "persisted")
        _require_false(self.db_write_performed, "db_write_performed")
        _require_false(
            self.runtime_mutation_performed,
            "runtime_mutation_performed",
        )
        _require_false(self.phase4i_mutation_performed, "phase4i_mutation_performed")
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")


@dataclass(frozen=True)
class GovernedWorkflowTransactionMetadata:
    """Local transaction metadata for future governed workflow writes."""

    transaction_group_id: str
    idempotency_key: str
    transaction_scope: str = DEFAULT_TRANSACTION_SCOPE
    requested_operations: list[str] = field(default_factory=list)
    rollback_reference: str | None = None
    retry_allowed: bool = True
    duplicate_handling: str = DEFAULT_DUPLICATE_HANDLING
    committed: bool = False
    rolled_back: bool = False
    db_write_performed: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.transaction_group_id, "transaction_group_id")
        _require_nonempty_string(self.idempotency_key, "idempotency_key")
        _require_supported(
            self.transaction_scope,
            TRANSACTION_SCOPES,
            "transaction_scope",
        )
        _require_list_of_strings(self.requested_operations, "requested_operations")
        _require_optional_string(self.rollback_reference, "rollback_reference")
        _require_boolean(self.retry_allowed, "retry_allowed")
        _require_supported(
            self.duplicate_handling,
            DUPLICATE_HANDLING_MODES,
            "duplicate_handling",
        )
        _require_false(self.committed, "committed")
        _require_false(self.rolled_back, "rolled_back")
        _require_false(self.db_write_performed, "db_write_performed")
        _require_optional_string(self.notes, "notes")


def create_persistence_request_id(
    workflow_record_type: str,
    workflow_record_id: str,
) -> str:
    """Create a deterministic governed workflow persistence request id."""

    _require_supported(
        workflow_record_type,
        WORKFLOW_RECORD_TYPES,
        "workflow_record_type",
    )
    _require_nonempty_string(workflow_record_id, "workflow_record_id")
    return (
        "GOVERNED-WORKFLOW-PERSISTENCE-REQUEST-"
        f"{_normalize_token(workflow_record_type)}-"
        f"{_normalize_token(workflow_record_id)}"
    )


def create_persistence_validation_id(persistence_request_id: str) -> str:
    """Create a deterministic governed workflow persistence validation id."""

    _require_nonempty_string(persistence_request_id, "persistence_request_id")
    return (
        "GOVERNED-WORKFLOW-PERSISTENCE-VALIDATION-"
        f"{_normalize_token(persistence_request_id)}"
    )


def create_audit_record_id(
    workflow_record_type: str,
    workflow_record_id: str,
    actor_id: str | None = None,
) -> str:
    """Create a deterministic governed workflow audit record id."""

    _require_supported(
        workflow_record_type,
        WORKFLOW_RECORD_TYPES,
        "workflow_record_type",
    )
    _require_nonempty_string(workflow_record_id, "workflow_record_id")
    _require_optional_string(actor_id, "actor_id")
    actor_token = actor_id or "NO-ACTOR"
    return (
        "GOVERNED-WORKFLOW-AUDIT-"
        f"{_normalize_token(workflow_record_type)}-"
        f"{_normalize_token(workflow_record_id)}-"
        f"{_normalize_token(actor_token)}"
    )


def create_transaction_group_id(
    idempotency_key: str,
    transaction_scope: str | None = None,
) -> str:
    """Create a deterministic transaction group id."""

    _require_nonempty_string(idempotency_key, "idempotency_key")
    scope = transaction_scope or DEFAULT_TRANSACTION_SCOPE
    _require_supported(scope, TRANSACTION_SCOPES, "transaction_scope")
    return (
        "GOVERNED-WORKFLOW-TX-"
        f"{_normalize_token(scope)}-"
        f"{_normalize_token(idempotency_key)}"
    )


def validate_governed_workflow_persistence_request(
    request: GovernedWorkflowPersistenceRequest,
) -> GovernedWorkflowPersistenceRequest:
    """Validate a persistence request without performing persistence."""

    if not isinstance(request, GovernedWorkflowPersistenceRequest):
        raise GovernedWorkflowPersistenceError(
            "request must be a GovernedWorkflowPersistenceRequest instance."
        )
    request.__post_init__()
    _require_supported(
        request.workflow_record_type,
        WORKFLOW_RECORD_TYPES,
        "workflow_record_type",
    )
    _require_nonempty_string(request.actor_id, "actor_id")
    _require_nonempty_string(request.idempotency_key, "idempotency_key")
    _require_nonempty_string(request.rollback_reference, "rollback_reference")
    if not _payload_present(request.payload):
        raise GovernedWorkflowPersistenceError("payload must be present.")
    return request


def evaluate_governed_workflow_persistence_request(
    request: GovernedWorkflowPersistenceRequest,
) -> GovernedWorkflowPersistenceValidation:
    """Evaluate persistence metadata for future persistence only."""

    if not isinstance(request, GovernedWorkflowPersistenceRequest):
        raise GovernedWorkflowPersistenceError(
            "request must be a GovernedWorkflowPersistenceRequest instance."
        )
    request.__post_init__()

    denied_reasons: list[str] = []
    warnings = [
        "Phase 7BU metadata only; persistence_performed=false.",
        "No DB write is performed in 7BU.",
        "No runtime mutation is performed in 7BU.",
    ]
    required_next_steps: list[str] = []

    actor_present = bool(_optional_text(request.actor_id))
    idempotency_key_present = bool(_optional_text(request.idempotency_key))
    rollback_reference_present = bool(_optional_text(request.rollback_reference))
    payload_present = _payload_present(request.payload)
    workflow_type_supported = request.workflow_record_type in WORKFLOW_RECORD_TYPES

    valid = True
    validation_status = "valid_metadata_only"

    if not workflow_type_supported:
        valid = False
        validation_status = "unsupported_record_type"
        denied_reasons.append("workflow_record_type is not supported")
        required_next_steps.append("choose a supported Phase 7BU workflow record type")
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
    elif not rollback_reference_present:
        valid = False
        validation_status = "needs_rollback_reference"
        denied_reasons.append("rollback_reference is required")
        required_next_steps.append("attach rollback reference metadata")
    elif not payload_present:
        valid = False
        validation_status = "needs_payload"
        denied_reasons.append("payload is required")
        required_next_steps.append("attach workflow payload metadata")
    else:
        required_next_steps.append("future repository layer may persist this envelope")
        required_next_steps.append("future write must be audited before durable commit")

    return validate_governed_workflow_persistence_validation(
        GovernedWorkflowPersistenceValidation(
            persistence_validation_id=create_persistence_validation_id(
                request.persistence_request_id
            ),
            persistence_request_id=request.persistence_request_id,
            valid=valid,
            validation_status=validation_status,
            workflow_record_type=request.workflow_record_type,
            actor_present=actor_present,
            idempotency_key_present=idempotency_key_present,
            rollback_reference_present=rollback_reference_present,
            payload_present=payload_present,
            can_persist_later=valid and request.persistence_requested,
            persistence_performed=False,
            db_write_performed=False,
            denied_reasons=denied_reasons,
            warnings=warnings,
            required_next_steps=required_next_steps,
            runtime_mutation_requested=False,
            phase4i_mutation_requested=False,
            notes=request.notes,
        )
    )


def validate_governed_workflow_persistence_validation(
    validation: GovernedWorkflowPersistenceValidation,
) -> GovernedWorkflowPersistenceValidation:
    """Validate persistence validation metadata."""

    if not isinstance(validation, GovernedWorkflowPersistenceValidation):
        raise GovernedWorkflowPersistenceError(
            "validation must be a GovernedWorkflowPersistenceValidation instance."
        )
    validation.__post_init__()
    return validation


def create_governed_workflow_audit_record(
    request: GovernedWorkflowPersistenceRequest,
    validation: GovernedWorkflowPersistenceValidation,
    notes: str | None = None,
) -> GovernedWorkflowAuditRecord:
    """Create local audit metadata without persisting an audit row."""

    validate_governed_workflow_persistence_request(request)
    validation = validate_governed_workflow_persistence_validation(validation)
    _require_optional_string(notes, "notes")
    return GovernedWorkflowAuditRecord(
        audit_record_id=create_audit_record_id(
            request.workflow_record_type,
            request.workflow_record_id,
            request.actor_id,
        ),
        workflow_record_type=request.workflow_record_type,
        workflow_record_id=request.workflow_record_id,
        actor_id=request.actor_id,
        action="persistence_metadata_evaluated",
        source_screen=request.source_screen,
        transaction_group_id=request.transaction_group_id,
        idempotency_key=request.idempotency_key,
        audit_summary=(
            "Phase 7BU local audit metadata for "
            f"{request.workflow_record_type}:{request.workflow_record_id}; "
            f"validation={validation.validation_status}; persisted=false"
        ),
        payload_hash=_hash_payload(request.payload),
        persisted=False,
        db_write_performed=False,
        runtime_mutation_performed=False,
        phase4i_mutation_performed=False,
        created_at=request.created_at,
        notes=notes,
    )


def validate_governed_workflow_audit_record(
    record: GovernedWorkflowAuditRecord,
) -> GovernedWorkflowAuditRecord:
    """Validate local audit metadata."""

    if not isinstance(record, GovernedWorkflowAuditRecord):
        raise GovernedWorkflowPersistenceError(
            "record must be a GovernedWorkflowAuditRecord instance."
        )
    record.__post_init__()
    return record


def create_transaction_metadata(
    idempotency_key: str,
    transaction_scope: str | None = None,
    rollback_reference: str | None = None,
    requested_operations: list[str] | None = None,
) -> GovernedWorkflowTransactionMetadata:
    """Create local transaction metadata without opening a transaction."""

    _require_nonempty_string(idempotency_key, "idempotency_key")
    _require_optional_string(rollback_reference, "rollback_reference")
    scope = transaction_scope or DEFAULT_TRANSACTION_SCOPE
    _require_supported(scope, TRANSACTION_SCOPES, "transaction_scope")
    operations = list(requested_operations or ["metadata_validation"])
    return GovernedWorkflowTransactionMetadata(
        transaction_group_id=create_transaction_group_id(idempotency_key, scope),
        idempotency_key=idempotency_key,
        transaction_scope=scope,
        requested_operations=operations,
        rollback_reference=rollback_reference,
        retry_allowed=True,
        duplicate_handling=DEFAULT_DUPLICATE_HANDLING,
        committed=False,
        rolled_back=False,
        db_write_performed=False,
        notes=None,
    )


def validate_transaction_metadata(
    metadata: GovernedWorkflowTransactionMetadata,
) -> GovernedWorkflowTransactionMetadata:
    """Validate transaction metadata without committing or rolling back."""

    if not isinstance(metadata, GovernedWorkflowTransactionMetadata):
        raise GovernedWorkflowPersistenceError(
            "metadata must be a GovernedWorkflowTransactionMetadata instance."
        )
    metadata.__post_init__()
    _require_nonempty_string(metadata.rollback_reference, "rollback_reference")
    return metadata


def governed_workflow_persistence_request_to_dict(
    request: GovernedWorkflowPersistenceRequest,
) -> dict[str, Any]:
    """Serialize governed workflow persistence request metadata."""

    request.__post_init__()
    return {
        "persistence_request_id": request.persistence_request_id,
        "workflow_record_type": request.workflow_record_type,
        "workflow_record_id": request.workflow_record_id,
        "source_screen": request.source_screen,
        "actor_id": request.actor_id,
        "actor_audit_context": _copy_optional_mapping(request.actor_audit_context),
        "payload": dict(request.payload),
        "idempotency_key": request.idempotency_key,
        "transaction_group_id": request.transaction_group_id,
        "rollback_reference": request.rollback_reference,
        "dry_run": request.dry_run,
        "persistence_requested": request.persistence_requested,
        "persistence_performed": request.persistence_performed,
        "db_write_performed": request.db_write_performed,
        "runtime_mutation_requested": request.runtime_mutation_requested,
        "phase4i_mutation_requested": request.phase4i_mutation_requested,
        "created_at": request.created_at,
        "notes": request.notes,
    }


def governed_workflow_persistence_request_from_dict(
    data: dict[str, Any],
) -> GovernedWorkflowPersistenceRequest:
    """Deserialize governed workflow persistence request metadata."""

    _require_mapping(data, "data")
    return GovernedWorkflowPersistenceRequest(
        persistence_request_id=str(data["persistence_request_id"]),
        workflow_record_type=str(data["workflow_record_type"]),
        workflow_record_id=str(data["workflow_record_id"]),
        source_screen=_optional_text(data.get("source_screen")),
        actor_id=_optional_text(data.get("actor_id")),
        actor_audit_context=_copy_optional_mapping(data.get("actor_audit_context")),
        payload=dict(data.get("payload") or {}),
        idempotency_key=_optional_text(data.get("idempotency_key")),
        transaction_group_id=_optional_text(data.get("transaction_group_id")),
        rollback_reference=_optional_text(data.get("rollback_reference")),
        dry_run=_bool_from_mapping(data, "dry_run", True),
        persistence_requested=_bool_from_mapping(
            data,
            "persistence_requested",
            True,
        ),
        persistence_performed=_bool_from_mapping(
            data,
            "persistence_performed",
            False,
        ),
        db_write_performed=_bool_from_mapping(data, "db_write_performed", False),
        runtime_mutation_requested=_bool_from_mapping(
            data,
            "runtime_mutation_requested",
            False,
        ),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        created_at=_optional_text(data.get("created_at")),
        notes=_optional_text(data.get("notes")),
    )


def governed_workflow_persistence_validation_to_dict(
    validation: GovernedWorkflowPersistenceValidation,
) -> dict[str, Any]:
    """Serialize governed workflow persistence validation metadata."""

    validation.__post_init__()
    return {
        "persistence_validation_id": validation.persistence_validation_id,
        "persistence_request_id": validation.persistence_request_id,
        "valid": validation.valid,
        "validation_status": validation.validation_status,
        "workflow_record_type": validation.workflow_record_type,
        "actor_present": validation.actor_present,
        "idempotency_key_present": validation.idempotency_key_present,
        "rollback_reference_present": validation.rollback_reference_present,
        "payload_present": validation.payload_present,
        "can_persist_later": validation.can_persist_later,
        "persistence_performed": validation.persistence_performed,
        "db_write_performed": validation.db_write_performed,
        "denied_reasons": list(validation.denied_reasons),
        "warnings": list(validation.warnings),
        "required_next_steps": list(validation.required_next_steps),
        "runtime_mutation_requested": validation.runtime_mutation_requested,
        "phase4i_mutation_requested": validation.phase4i_mutation_requested,
        "notes": validation.notes,
    }


def governed_workflow_persistence_validation_from_dict(
    data: dict[str, Any],
) -> GovernedWorkflowPersistenceValidation:
    """Deserialize governed workflow persistence validation metadata."""

    _require_mapping(data, "data")
    return GovernedWorkflowPersistenceValidation(
        persistence_validation_id=str(data["persistence_validation_id"]),
        persistence_request_id=str(data["persistence_request_id"]),
        valid=_bool_from_mapping(data, "valid", False),
        validation_status=str(data["validation_status"]),
        workflow_record_type=str(data["workflow_record_type"]),
        actor_present=_bool_from_mapping(data, "actor_present", False),
        idempotency_key_present=_bool_from_mapping(
            data,
            "idempotency_key_present",
            False,
        ),
        rollback_reference_present=_bool_from_mapping(
            data,
            "rollback_reference_present",
            False,
        ),
        payload_present=_bool_from_mapping(data, "payload_present", False),
        can_persist_later=_bool_from_mapping(data, "can_persist_later", False),
        persistence_performed=_bool_from_mapping(
            data,
            "persistence_performed",
            False,
        ),
        db_write_performed=_bool_from_mapping(data, "db_write_performed", False),
        denied_reasons=list(data.get("denied_reasons") or []),
        warnings=list(data.get("warnings") or []),
        required_next_steps=list(data.get("required_next_steps") or []),
        runtime_mutation_requested=_bool_from_mapping(
            data,
            "runtime_mutation_requested",
            False,
        ),
        phase4i_mutation_requested=_bool_from_mapping(
            data,
            "phase4i_mutation_requested",
            False,
        ),
        notes=_optional_text(data.get("notes")),
    )


def governed_workflow_audit_record_to_dict(
    record: GovernedWorkflowAuditRecord,
) -> dict[str, Any]:
    """Serialize governed workflow audit metadata."""

    record.__post_init__()
    return {
        "audit_record_id": record.audit_record_id,
        "workflow_record_type": record.workflow_record_type,
        "workflow_record_id": record.workflow_record_id,
        "actor_id": record.actor_id,
        "action": record.action,
        "source_screen": record.source_screen,
        "transaction_group_id": record.transaction_group_id,
        "idempotency_key": record.idempotency_key,
        "audit_summary": record.audit_summary,
        "payload_hash": record.payload_hash,
        "persisted": record.persisted,
        "db_write_performed": record.db_write_performed,
        "runtime_mutation_performed": record.runtime_mutation_performed,
        "phase4i_mutation_performed": record.phase4i_mutation_performed,
        "created_at": record.created_at,
        "notes": record.notes,
    }


def governed_workflow_audit_record_from_dict(
    data: dict[str, Any],
) -> GovernedWorkflowAuditRecord:
    """Deserialize governed workflow audit metadata."""

    _require_mapping(data, "data")
    return GovernedWorkflowAuditRecord(
        audit_record_id=str(data["audit_record_id"]),
        workflow_record_type=str(data["workflow_record_type"]),
        workflow_record_id=str(data["workflow_record_id"]),
        actor_id=_optional_text(data.get("actor_id")),
        action=str(data["action"]),
        source_screen=_optional_text(data.get("source_screen")),
        transaction_group_id=_optional_text(data.get("transaction_group_id")),
        idempotency_key=_optional_text(data.get("idempotency_key")),
        audit_summary=str(data["audit_summary"]),
        payload_hash=str(data["payload_hash"]),
        persisted=_bool_from_mapping(data, "persisted", False),
        db_write_performed=_bool_from_mapping(data, "db_write_performed", False),
        runtime_mutation_performed=_bool_from_mapping(
            data,
            "runtime_mutation_performed",
            False,
        ),
        phase4i_mutation_performed=_bool_from_mapping(
            data,
            "phase4i_mutation_performed",
            False,
        ),
        created_at=_optional_text(data.get("created_at")),
        notes=_optional_text(data.get("notes")),
    )


def governed_workflow_transaction_metadata_to_dict(
    metadata: GovernedWorkflowTransactionMetadata,
) -> dict[str, Any]:
    """Serialize governed workflow transaction metadata."""

    metadata.__post_init__()
    return {
        "transaction_group_id": metadata.transaction_group_id,
        "idempotency_key": metadata.idempotency_key,
        "transaction_scope": metadata.transaction_scope,
        "requested_operations": list(metadata.requested_operations),
        "rollback_reference": metadata.rollback_reference,
        "retry_allowed": metadata.retry_allowed,
        "duplicate_handling": metadata.duplicate_handling,
        "committed": metadata.committed,
        "rolled_back": metadata.rolled_back,
        "db_write_performed": metadata.db_write_performed,
        "notes": metadata.notes,
    }


def governed_workflow_transaction_metadata_from_dict(
    data: dict[str, Any],
) -> GovernedWorkflowTransactionMetadata:
    """Deserialize governed workflow transaction metadata."""

    _require_mapping(data, "data")
    return GovernedWorkflowTransactionMetadata(
        transaction_group_id=str(data["transaction_group_id"]),
        idempotency_key=str(data["idempotency_key"]),
        transaction_scope=str(
            data.get("transaction_scope", DEFAULT_TRANSACTION_SCOPE)
        ),
        requested_operations=list(data.get("requested_operations") or []),
        rollback_reference=_optional_text(data.get("rollback_reference")),
        retry_allowed=_bool_from_mapping(data, "retry_allowed", True),
        duplicate_handling=str(data.get("duplicate_handling", DEFAULT_DUPLICATE_HANDLING)),
        committed=_bool_from_mapping(data, "committed", False),
        rolled_back=_bool_from_mapping(data, "rolled_back", False),
        db_write_performed=_bool_from_mapping(data, "db_write_performed", False),
        notes=_optional_text(data.get("notes")),
    )


def _payload_present(payload: dict[str, Any]) -> bool:
    return isinstance(payload, dict) and bool(payload)


def _hash_payload(payload: dict[str, Any]) -> str:
    _require_mapping(payload, "payload")
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_from_mapping(data: dict[str, Any], field_name: str, default: bool) -> bool:
    value = data.get(field_name, default)
    if isinstance(value, bool):
        return value
    raise GovernedWorkflowPersistenceError(f"{field_name} must be a boolean.")


def _copy_optional_mapping(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise GovernedWorkflowPersistenceError("mapping value must be a dictionary.")
    return dict(value)


def _require_mapping(value: Any, field_name: str) -> None:
    if not isinstance(value, dict):
        raise GovernedWorkflowPersistenceError(f"{field_name} must be a mapping.")


def _require_optional_mapping(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, dict):
        raise GovernedWorkflowPersistenceError(
            f"{field_name} must be a mapping or None."
        )


def _require_nonempty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise GovernedWorkflowPersistenceError(
            f"{field_name} must be a non-empty string."
        )


def _require_optional_string(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise GovernedWorkflowPersistenceError(
            f"{field_name} must be a string or None."
        )


def _require_supported(value: Any, supported: tuple[str, ...], field_name: str) -> None:
    if value not in supported:
        raise GovernedWorkflowPersistenceError(
            f"{field_name} must be one of: {', '.join(supported)}."
        )


def _require_boolean(value: Any, field_name: str) -> None:
    if not isinstance(value, bool):
        raise GovernedWorkflowPersistenceError(f"{field_name} must be a boolean.")


def _require_false(value: Any, field_name: str) -> None:
    _require_boolean(value, field_name)
    if value:
        raise GovernedWorkflowPersistenceError(
            f"{field_name} must remain false in Phase 7BU."
        )


def _require_list_of_strings(value: Any, field_name: str) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise GovernedWorkflowPersistenceError(
            f"{field_name} must be a list of strings."
        )


def _normalize_token(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text).strip("-")
    return text or "NONE"
