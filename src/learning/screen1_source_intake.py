"""Phase 7AV Screen 1 source intake control metadata.

The records in this module describe future source intake intent for Screen 1.
They validate metadata shape only. They do not load sources, call external
services, inspect databases, invoke parser behavior, write state, modify
dashboard behavior, modify CLI behavior, or mutate runtime output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


SCREEN1_SOURCE_MODES = (
    "none",
    "local_staged",
    "local_file",
    "existing_run",
    "object_storage",
    "future_upload",
    "future_em_extract",
)

SOURCE_INTAKE_ACTIONS = (
    "validate_source",
    "request_source_intake",
    "preview_source_intake",
    "prepare_for_reanalysis",
    "prepare_for_parser_review",
    "prepare_for_existing_run_review",
    "prepare_for_object_storage_load",
    "prepare_for_future_em_extract",
)

SOURCE_INTAKE_VALIDATION_STATUSES = (
    "VALID_METADATA_ONLY",
    "INVALID",
    "NEEDS_ACTOR",
    "NEEDS_SOURCE_REFERENCE",
    "NEEDS_BACKEND_VALIDATION",
    "NEEDS_OBJECT_STORAGE_CONFIG",
    "FUTURE_SOURCE_NOT_IMPLEMENTED",
    "INTAKE_NOT_ALLOWED_IN_THIS_PHASE",
)

EXPECTED_INTAKE_FILE_TYPES = (
    "awr",
    "html",
    "txt",
    "zip",
    "json",
    "xml",
)

_SOURCE_REFERENCE_REQUIRED_MODES = (
    "local_staged",
    "local_file",
    "existing_run",
    "object_storage",
    "future_upload",
    "future_em_extract",
)


class Screen1SourceIntakeError(ValueError):
    """Raised when Phase 7AV source intake metadata is invalid."""


@dataclass(frozen=True)
class SourceIntakeRequest:
    """Metadata for a future Screen 1 source intake request."""

    intake_request_id: str
    source_mode: str = "none"
    source_reference: dict[str, Any] | None = None
    requested_action: str = "preview_source_intake"
    actor_id: str | None = None
    actor_audit_context: dict[str, Any] | None = None
    backend_execution_request: dict[str, Any] | None = None
    expected_file_type: str | None = None
    target_screen: str | None = "screen1"
    source_label: str | None = None
    dry_run: bool = True
    requires_actor: bool = True
    requires_source_validation: bool = True
    requires_backend_validation: bool = True
    requires_audit: bool = True
    intake_performed: bool = False
    file_read_performed: bool = False
    object_storage_called: bool = False
    db_lookup_performed: bool = False
    parser_invoked: bool = False
    run_analysis_called: bool = False
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.intake_request_id, "intake_request_id")
        _require_supported(self.source_mode, SCREEN1_SOURCE_MODES, "source_mode")
        _require_optional_mapping(self.source_reference, "source_reference")
        _require_supported(
            self.requested_action,
            SOURCE_INTAKE_ACTIONS,
            "requested_action",
        )
        _require_optional_string(self.actor_id, "actor_id")
        _require_optional_mapping(
            self.actor_audit_context,
            "actor_audit_context",
        )
        _require_optional_mapping(
            self.backend_execution_request,
            "backend_execution_request",
        )
        _require_optional_string(self.expected_file_type, "expected_file_type")
        if self.expected_file_type is not None:
            _require_supported(
                self.expected_file_type,
                EXPECTED_INTAKE_FILE_TYPES,
                "expected_file_type",
            )
        _require_optional_string(self.target_screen, "target_screen")
        _require_optional_string(self.source_label, "source_label")
        _require_bool(self.dry_run, "dry_run")
        _require_bool(self.requires_actor, "requires_actor")
        _require_bool(
            self.requires_source_validation,
            "requires_source_validation",
        )
        _require_bool(
            self.requires_backend_validation,
            "requires_backend_validation",
        )
        _require_bool(self.requires_audit, "requires_audit")
        _require_bool(self.intake_performed, "intake_performed")
        _require_bool(self.file_read_performed, "file_read_performed")
        _require_bool(self.object_storage_called, "object_storage_called")
        _require_bool(self.db_lookup_performed, "db_lookup_performed")
        _require_bool(self.parser_invoked, "parser_invoked")
        _require_bool(self.run_analysis_called, "run_analysis_called")
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")
        if not self.dry_run:
            raise Screen1SourceIntakeError(
                "dry_run must remain true in Phase 7AV."
            )
        if not self.requires_actor:
            raise Screen1SourceIntakeError(
                "requires_actor must remain true in Phase 7AV."
            )
        if not self.requires_source_validation:
            raise Screen1SourceIntakeError(
                "requires_source_validation must remain true in Phase 7AV."
            )
        if not self.requires_backend_validation:
            raise Screen1SourceIntakeError(
                "requires_backend_validation must remain true in Phase 7AV."
            )
        if not self.requires_audit:
            raise Screen1SourceIntakeError(
                "requires_audit must remain true in Phase 7AV."
            )
        if self.intake_performed:
            raise Screen1SourceIntakeError(
                "intake_performed must remain false in Phase 7AV."
            )
        if self.file_read_performed:
            raise Screen1SourceIntakeError(
                "file_read_performed must remain false in Phase 7AV."
            )
        if self.object_storage_called:
            raise Screen1SourceIntakeError(
                "object_storage_called must remain false in Phase 7AV."
            )
        if self.db_lookup_performed:
            raise Screen1SourceIntakeError(
                "db_lookup_performed must remain false in Phase 7AV."
            )
        if self.parser_invoked:
            raise Screen1SourceIntakeError(
                "parser_invoked must remain false in Phase 7AV."
            )
        if self.run_analysis_called:
            raise Screen1SourceIntakeError(
                "run_analysis_called must remain false in Phase 7AV."
            )


@dataclass(frozen=True)
class SourceIntakeValidation:
    """Metadata result for source intake validation in Phase 7AV."""

    validation_id: str
    intake_request_id: str
    valid: bool
    validation_status: str
    source_mode: str
    source_metadata_valid: bool
    actor_present: bool
    backend_validation_present: bool
    can_intake: bool = False
    intake_blocked: bool = True
    denied_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_next_steps: list[str] = field(default_factory=list)
    file_read_performed: bool = False
    object_storage_called: bool = False
    db_lookup_performed: bool = False
    parser_invoked: bool = False
    run_analysis_called: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.validation_id, "validation_id")
        _require_nonempty_string(self.intake_request_id, "intake_request_id")
        _require_bool(self.valid, "valid")
        _require_supported(
            self.validation_status,
            SOURCE_INTAKE_VALIDATION_STATUSES,
            "validation_status",
        )
        _require_supported(self.source_mode, SCREEN1_SOURCE_MODES, "source_mode")
        _require_bool(self.source_metadata_valid, "source_metadata_valid")
        _require_bool(self.actor_present, "actor_present")
        _require_bool(
            self.backend_validation_present,
            "backend_validation_present",
        )
        _require_bool(self.can_intake, "can_intake")
        _require_bool(self.intake_blocked, "intake_blocked")
        _require_list_of_strings(self.denied_reasons, "denied_reasons")
        _require_list_of_strings(self.warnings, "warnings")
        _require_list_of_strings(
            self.required_next_steps,
            "required_next_steps",
        )
        _require_bool(self.file_read_performed, "file_read_performed")
        _require_bool(self.object_storage_called, "object_storage_called")
        _require_bool(self.db_lookup_performed, "db_lookup_performed")
        _require_bool(self.parser_invoked, "parser_invoked")
        _require_bool(self.run_analysis_called, "run_analysis_called")
        _require_optional_string(self.notes, "notes")
        if self.can_intake:
            raise Screen1SourceIntakeError(
                "can_intake must remain false in Phase 7AV."
            )
        if not self.intake_blocked:
            raise Screen1SourceIntakeError(
                "intake_blocked must remain true in Phase 7AV."
            )
        if self.file_read_performed:
            raise Screen1SourceIntakeError(
                "file_read_performed must remain false in Phase 7AV."
            )
        if self.object_storage_called:
            raise Screen1SourceIntakeError(
                "object_storage_called must remain false in Phase 7AV."
            )
        if self.db_lookup_performed:
            raise Screen1SourceIntakeError(
                "db_lookup_performed must remain false in Phase 7AV."
            )
        if self.parser_invoked:
            raise Screen1SourceIntakeError(
                "parser_invoked must remain false in Phase 7AV."
            )
        if self.run_analysis_called:
            raise Screen1SourceIntakeError(
                "run_analysis_called must remain false in Phase 7AV."
            )


@dataclass(frozen=True)
class SourceIntakePreview:
    """Preview metadata for future Screen 1 source intake workflow."""

    preview_id: str
    intake_request_id: str
    source_mode: str
    source_label: str | None
    expected_file_type: str | None
    target_screen: str | None
    preview_summary: str
    source_available_hint: bool | None = None
    source_validation_required: bool = True
    backend_execution_required: bool = True
    actor_required: bool = True
    audit_required: bool = True
    intake_performed: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.preview_id, "preview_id")
        _require_nonempty_string(self.intake_request_id, "intake_request_id")
        _require_supported(self.source_mode, SCREEN1_SOURCE_MODES, "source_mode")
        _require_optional_string(self.source_label, "source_label")
        _require_optional_string(self.expected_file_type, "expected_file_type")
        if self.expected_file_type is not None:
            _require_supported(
                self.expected_file_type,
                EXPECTED_INTAKE_FILE_TYPES,
                "expected_file_type",
            )
        _require_optional_string(self.target_screen, "target_screen")
        _require_nonempty_string(self.preview_summary, "preview_summary")
        _require_optional_bool(self.source_available_hint, "source_available_hint")
        _require_bool(
            self.source_validation_required,
            "source_validation_required",
        )
        _require_bool(
            self.backend_execution_required,
            "backend_execution_required",
        )
        _require_bool(self.actor_required, "actor_required")
        _require_bool(self.audit_required, "audit_required")
        _require_bool(self.intake_performed, "intake_performed")
        _require_optional_string(self.notes, "notes")
        if self.intake_performed:
            raise Screen1SourceIntakeError(
                "intake_performed must remain false in Phase 7AV."
            )


def create_source_intake_request_id(
    source_mode: str,
    requested_action: str,
    source_label: str | None = None,
) -> str:
    """Create a deterministic source intake request id."""

    _require_supported(source_mode, SCREEN1_SOURCE_MODES, "source_mode")
    _require_supported(requested_action, SOURCE_INTAKE_ACTIONS, "requested_action")
    _require_optional_string(source_label, "source_label")
    label_token = source_label or "NO-SOURCE"
    return (
        "SCREEN1-SOURCE-INTAKE-REQUEST-"
        f"{_normalize_token(source_mode)}-"
        f"{_normalize_token(requested_action)}-"
        f"{_normalize_token(label_token)}"
    )


def create_source_intake_validation_id(intake_request_id: str) -> str:
    """Create a deterministic source intake validation id."""

    _require_nonempty_string(intake_request_id, "intake_request_id")
    return f"SCREEN1-SOURCE-INTAKE-VALIDATION-{_normalize_token(intake_request_id)}"


def create_source_intake_preview_id(intake_request_id: str) -> str:
    """Create a deterministic source intake preview id."""

    _require_nonempty_string(intake_request_id, "intake_request_id")
    return f"SCREEN1-SOURCE-INTAKE-PREVIEW-{_normalize_token(intake_request_id)}"


def validate_source_intake_request(
    request: SourceIntakeRequest,
) -> SourceIntakeRequest:
    """Validate source intake request metadata without executing intake."""

    if not isinstance(request, SourceIntakeRequest):
        raise Screen1SourceIntakeError(
            "request must be a SourceIntakeRequest instance."
        )
    request.__post_init__()
    return request


def evaluate_source_intake_request(
    request: SourceIntakeRequest,
) -> SourceIntakeValidation:
    """Evaluate request metadata while keeping intake blocked in Phase 7AV."""

    request = validate_source_intake_request(request)
    denied_reasons: list[str] = ["intake is not allowed in Phase 7AV"]
    warnings: list[str] = []
    required_next_steps: list[str] = [
        "route through a future governed source intake workflow"
    ]

    actor_present = _actor_present(request)
    backend_present = bool(request.backend_execution_request)
    source_metadata_valid = _source_metadata_present(request)
    valid = False
    status = "INVALID"

    if request.requires_actor and not actor_present:
        status = "NEEDS_ACTOR"
        denied_reasons.append("actor identity is required")
        required_next_steps.append("provide actor identity through Phase 7AE")
    elif request.source_mode in _SOURCE_REFERENCE_REQUIRED_MODES and not source_metadata_valid:
        status = "NEEDS_SOURCE_REFERENCE"
        denied_reasons.append("source reference metadata is required")
        required_next_steps.append("provide source reference metadata")
    elif request.requires_backend_validation and not backend_present:
        status = "NEEDS_BACKEND_VALIDATION"
        denied_reasons.append("backend validation metadata is required")
        required_next_steps.append("provide backend execution validation metadata")
    elif request.source_mode == "object_storage" and not _object_storage_configured(
        request.source_reference
    ):
        status = "NEEDS_OBJECT_STORAGE_CONFIG"
        denied_reasons.append("object storage configuration is not confirmed")
        required_next_steps.append("validate object storage configuration later")
    elif request.source_mode in ("future_upload", "future_em_extract"):
        status = "FUTURE_SOURCE_NOT_IMPLEMENTED"
        denied_reasons.append(f"{request.source_mode} is placeholder metadata only")
        required_next_steps.append("wait for the future source implementation phase")
    else:
        status = "INTAKE_NOT_ALLOWED_IN_THIS_PHASE"
        valid = True
        if request.source_mode == "object_storage":
            warnings.append("object storage metadata was not verified externally")
        if request.source_mode in ("local_staged", "local_file"):
            warnings.append("local source metadata was not verified against files")
        if request.source_mode == "existing_run":
            warnings.append("existing run metadata was not verified against storage")

    return SourceIntakeValidation(
        validation_id=create_source_intake_validation_id(request.intake_request_id),
        intake_request_id=request.intake_request_id,
        valid=valid,
        validation_status=status,
        source_mode=request.source_mode,
        source_metadata_valid=source_metadata_valid,
        actor_present=actor_present,
        backend_validation_present=backend_present,
        can_intake=False,
        intake_blocked=True,
        denied_reasons=denied_reasons,
        warnings=warnings,
        required_next_steps=required_next_steps,
        file_read_performed=False,
        object_storage_called=False,
        db_lookup_performed=False,
        parser_invoked=False,
        run_analysis_called=False,
        notes=request.notes,
    )


def validate_source_intake_validation(
    validation: SourceIntakeValidation,
) -> SourceIntakeValidation:
    """Validate source intake validation metadata."""

    if not isinstance(validation, SourceIntakeValidation):
        raise Screen1SourceIntakeError(
            "validation must be a SourceIntakeValidation instance."
        )
    validation.__post_init__()
    return validation


def create_source_intake_preview(
    request: SourceIntakeRequest,
    validation: SourceIntakeValidation | None = None,
) -> SourceIntakePreview:
    """Create preview metadata for a future intake workflow."""

    request = validate_source_intake_request(request)
    if validation is None:
        validation = evaluate_source_intake_request(request)
    else:
        validation = validate_source_intake_validation(validation)
        if validation.intake_request_id != request.intake_request_id:
            raise Screen1SourceIntakeError(
                "validation intake_request_id must match request."
            )

    source_available_hint = (
        request.source_reference.get("available_hint")
        if isinstance(request.source_reference, dict)
        else None
    )
    if source_available_hint is not None:
        _require_bool(source_available_hint, "source_available_hint")

    summary = (
        f"Screen 1 source intake preview for {request.source_mode}; "
        f"status={validation.validation_status}; intake_performed=false"
    )
    return SourceIntakePreview(
        preview_id=create_source_intake_preview_id(request.intake_request_id),
        intake_request_id=request.intake_request_id,
        source_mode=request.source_mode,
        source_label=request.source_label,
        expected_file_type=request.expected_file_type,
        target_screen=request.target_screen,
        preview_summary=summary,
        source_available_hint=source_available_hint,
        source_validation_required=request.requires_source_validation,
        backend_execution_required=request.requires_backend_validation,
        actor_required=request.requires_actor,
        audit_required=request.requires_audit,
        intake_performed=False,
        notes=request.notes,
    )


def validate_source_intake_preview(
    preview: SourceIntakePreview,
) -> SourceIntakePreview:
    """Validate source intake preview metadata."""

    if not isinstance(preview, SourceIntakePreview):
        raise Screen1SourceIntakeError(
            "preview must be a SourceIntakePreview instance."
        )
    preview.__post_init__()
    return preview


def source_intake_request_to_dict(request: SourceIntakeRequest) -> dict[str, Any]:
    """Serialize source intake request metadata."""

    request = validate_source_intake_request(request)
    return {
        "intake_request_id": request.intake_request_id,
        "source_mode": request.source_mode,
        "source_reference": _copy_optional_mapping(request.source_reference),
        "requested_action": request.requested_action,
        "actor_id": request.actor_id,
        "actor_audit_context": _copy_optional_mapping(request.actor_audit_context),
        "backend_execution_request": _copy_optional_mapping(
            request.backend_execution_request
        ),
        "expected_file_type": request.expected_file_type,
        "target_screen": request.target_screen,
        "source_label": request.source_label,
        "dry_run": request.dry_run,
        "requires_actor": request.requires_actor,
        "requires_source_validation": request.requires_source_validation,
        "requires_backend_validation": request.requires_backend_validation,
        "requires_audit": request.requires_audit,
        "intake_performed": request.intake_performed,
        "file_read_performed": request.file_read_performed,
        "object_storage_called": request.object_storage_called,
        "db_lookup_performed": request.db_lookup_performed,
        "parser_invoked": request.parser_invoked,
        "run_analysis_called": request.run_analysis_called,
        "created_at": request.created_at,
        "notes": request.notes,
    }


def source_intake_request_from_dict(data: dict[str, Any]) -> SourceIntakeRequest:
    """Deserialize source intake request metadata."""

    _require_mapping(data, "source_intake_request")
    return SourceIntakeRequest(
        intake_request_id=data.get("intake_request_id"),
        source_mode=data.get("source_mode", "none"),
        source_reference=data.get("source_reference"),
        requested_action=data.get("requested_action", "preview_source_intake"),
        actor_id=data.get("actor_id"),
        actor_audit_context=data.get("actor_audit_context"),
        backend_execution_request=data.get("backend_execution_request"),
        expected_file_type=data.get("expected_file_type"),
        target_screen=data.get("target_screen", "screen1"),
        source_label=data.get("source_label"),
        dry_run=data.get("dry_run", True),
        requires_actor=data.get("requires_actor", True),
        requires_source_validation=data.get("requires_source_validation", True),
        requires_backend_validation=data.get("requires_backend_validation", True),
        requires_audit=data.get("requires_audit", True),
        intake_performed=data.get("intake_performed", False),
        file_read_performed=data.get("file_read_performed", False),
        object_storage_called=data.get("object_storage_called", False),
        db_lookup_performed=data.get("db_lookup_performed", False),
        parser_invoked=data.get("parser_invoked", False),
        run_analysis_called=data.get("run_analysis_called", False),
        created_at=data.get("created_at"),
        notes=data.get("notes"),
    )


def source_intake_validation_to_dict(
    validation: SourceIntakeValidation,
) -> dict[str, Any]:
    """Serialize source intake validation metadata."""

    validation = validate_source_intake_validation(validation)
    return {
        "validation_id": validation.validation_id,
        "intake_request_id": validation.intake_request_id,
        "valid": validation.valid,
        "validation_status": validation.validation_status,
        "source_mode": validation.source_mode,
        "source_metadata_valid": validation.source_metadata_valid,
        "actor_present": validation.actor_present,
        "backend_validation_present": validation.backend_validation_present,
        "can_intake": validation.can_intake,
        "intake_blocked": validation.intake_blocked,
        "denied_reasons": list(validation.denied_reasons),
        "warnings": list(validation.warnings),
        "required_next_steps": list(validation.required_next_steps),
        "file_read_performed": validation.file_read_performed,
        "object_storage_called": validation.object_storage_called,
        "db_lookup_performed": validation.db_lookup_performed,
        "parser_invoked": validation.parser_invoked,
        "run_analysis_called": validation.run_analysis_called,
        "notes": validation.notes,
    }


def source_intake_validation_from_dict(
    data: dict[str, Any],
) -> SourceIntakeValidation:
    """Deserialize source intake validation metadata."""

    _require_mapping(data, "source_intake_validation")
    return SourceIntakeValidation(
        validation_id=data.get("validation_id"),
        intake_request_id=data.get("intake_request_id"),
        valid=data.get("valid"),
        validation_status=data.get("validation_status"),
        source_mode=data.get("source_mode"),
        source_metadata_valid=data.get("source_metadata_valid"),
        actor_present=data.get("actor_present"),
        backend_validation_present=data.get("backend_validation_present"),
        can_intake=data.get("can_intake", False),
        intake_blocked=data.get("intake_blocked", True),
        denied_reasons=data.get("denied_reasons", []),
        warnings=data.get("warnings", []),
        required_next_steps=data.get("required_next_steps", []),
        file_read_performed=data.get("file_read_performed", False),
        object_storage_called=data.get("object_storage_called", False),
        db_lookup_performed=data.get("db_lookup_performed", False),
        parser_invoked=data.get("parser_invoked", False),
        run_analysis_called=data.get("run_analysis_called", False),
        notes=data.get("notes"),
    )


def source_intake_preview_to_dict(preview: SourceIntakePreview) -> dict[str, Any]:
    """Serialize source intake preview metadata."""

    preview = validate_source_intake_preview(preview)
    return {
        "preview_id": preview.preview_id,
        "intake_request_id": preview.intake_request_id,
        "source_mode": preview.source_mode,
        "source_label": preview.source_label,
        "expected_file_type": preview.expected_file_type,
        "target_screen": preview.target_screen,
        "preview_summary": preview.preview_summary,
        "source_available_hint": preview.source_available_hint,
        "source_validation_required": preview.source_validation_required,
        "backend_execution_required": preview.backend_execution_required,
        "actor_required": preview.actor_required,
        "audit_required": preview.audit_required,
        "intake_performed": preview.intake_performed,
        "notes": preview.notes,
    }


def source_intake_preview_from_dict(data: dict[str, Any]) -> SourceIntakePreview:
    """Deserialize source intake preview metadata."""

    _require_mapping(data, "source_intake_preview")
    return SourceIntakePreview(
        preview_id=data.get("preview_id"),
        intake_request_id=data.get("intake_request_id"),
        source_mode=data.get("source_mode"),
        source_label=data.get("source_label"),
        expected_file_type=data.get("expected_file_type"),
        target_screen=data.get("target_screen"),
        preview_summary=data.get("preview_summary"),
        source_available_hint=data.get("source_available_hint"),
        source_validation_required=data.get("source_validation_required", True),
        backend_execution_required=data.get("backend_execution_required", True),
        actor_required=data.get("actor_required", True),
        audit_required=data.get("audit_required", True),
        intake_performed=data.get("intake_performed", False),
        notes=data.get("notes"),
    )


def default_source_intake_request(notes: str | None = None) -> SourceIntakeRequest:
    """Create a deterministic placeholder request for no selected source."""

    _require_optional_string(notes, "notes")
    return SourceIntakeRequest(
        intake_request_id=create_source_intake_request_id(
            "none",
            "preview_source_intake",
            "NO-SOURCE",
        ),
        source_mode="none",
        source_reference=None,
        requested_action="preview_source_intake",
        source_label="No source selected",
        notes=notes,
    )


def _actor_present(request: SourceIntakeRequest) -> bool:
    return bool(request.actor_id or request.actor_audit_context)


def _source_metadata_present(request: SourceIntakeRequest) -> bool:
    if request.source_mode == "none":
        return True
    return bool(request.source_reference)


def _object_storage_configured(source_reference: dict[str, Any] | None) -> bool:
    if not source_reference:
        return False
    return source_reference.get("configured_hint") is True


def _copy_optional_mapping(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_mapping(value, "mapping")
    return dict(value)


def _normalize_token(value: str) -> str:
    _require_nonempty_string(value, "value")
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().upper())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "NONE"


def _require_nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Screen1SourceIntakeError(f"{field_name} is required.")
    return value


def _require_optional_string(value: Any, field_name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise Screen1SourceIntakeError(
            f"{field_name} must be a string or None."
        )
    return value


def _require_supported(value: Any, supported: tuple[str, ...], field_name: str) -> str:
    if not isinstance(value, str) or value not in supported:
        raise Screen1SourceIntakeError(f"Unsupported {field_name}: {value!r}.")
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise Screen1SourceIntakeError(f"{field_name} must be boolean.")
    return value


def _require_optional_bool(value: Any, field_name: str) -> bool | None:
    if value is not None and type(value) is not bool:
        raise Screen1SourceIntakeError(
            f"{field_name} must be boolean or None."
        )
    return value


def _require_list_of_strings(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise Screen1SourceIntakeError(
            f"{field_name} must be a list of strings."
        )
    return value


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Screen1SourceIntakeError(f"{field_name} must be a dictionary.")
    return value


def _require_optional_mapping(
    value: Any,
    field_name: str,
) -> dict[str, Any] | None:
    if value is not None and not isinstance(value, dict):
        raise Screen1SourceIntakeError(
            f"{field_name} must be a dictionary or None."
        )
    return value
