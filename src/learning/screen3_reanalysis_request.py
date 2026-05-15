"""Phase 7AL Screen 3 backend re-analysis request metadata.

The records in this module describe future Screen 3 re-analysis intent. They
validate selected state, action metadata, source linkage, actor linkage, and
execution mode metadata only. They do not perform backend work, load sources,
write artifacts, mutate dashboard state, or change runtime behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from src.learning.screen3_source_selection import SCREEN3_SOURCE_MODES


SCREEN3_REANALYSIS_ACTIONS = (
    "analyze_selection",
    "rerun_analysis",
    "build_comparison",
    "load_from_object_storage",
)

SCREEN3_REANALYSIS_EXECUTION_MODES = (
    "static_read_only",
    "local_command_generation",
    "local_backend_execution",
    "future_api_server_execution",
)

SCREEN3_REANALYSIS_SOURCE_MODES = SCREEN3_SOURCE_MODES

REANALYSIS_REQUEST_VALIDATION_STATUSES = (
    "VALID_METADATA_ONLY",
    "INVALID",
    "NEEDS_ACTOR",
    "NEEDS_SOURCE_SELECTION",
    "NEEDS_SOURCE_VALIDATION",
    "NEEDS_BACKEND_EXECUTION_VALIDATION",
    "UNSUPPORTED_ACTION",
    "UNSUPPORTED_EXECUTION_MODE",
    "UNSUPPORTED_SOURCE_MODE",
    "EXECUTION_NOT_ALLOWED_IN_THIS_PHASE",
)

SCREEN3_REANALYSIS_ISSUE_DOMAINS = (
    "CPU",
    "IO",
    "MEMORY",
    "COMMIT",
    "RAC",
    "ADG",
)


class Screen3ReAnalysisRequestError(ValueError):
    """Raised when 7AL re-analysis request metadata is invalid."""


@dataclass(frozen=True)
class Screen3SelectedState:
    """Metadata describing the selected Screen 3 state."""

    selected_state_id: str
    selected_awr: str | None = None
    selected_run: str | None = None
    selected_database: str | None = None
    selected_system: str | None = None
    selected_snapshot: str | None = None
    selected_comparison_baseline: str | None = None
    selected_issue_domain: str | None = None
    selected_severity_status: str | None = None
    selected_source_mode: str = "none"
    selected_execution_mode: str = "static_read_only"
    selected_object_storage_reference: str | None = None
    selected_local_source_reference: str | None = None
    selected_existing_run_reference: str | None = None
    selected_future_em_extract_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.selected_state_id, "selected_state_id")
        _require_optional_string(self.selected_awr, "selected_awr")
        _require_optional_string(self.selected_run, "selected_run")
        _require_optional_string(self.selected_database, "selected_database")
        _require_optional_string(self.selected_system, "selected_system")
        _require_optional_string(self.selected_snapshot, "selected_snapshot")
        _require_optional_string(
            self.selected_comparison_baseline,
            "selected_comparison_baseline",
        )
        _require_optional_string(self.selected_issue_domain, "selected_issue_domain")
        if self.selected_issue_domain is not None:
            _require_issue_domain(self.selected_issue_domain)
        _require_optional_string(self.selected_severity_status, "selected_severity_status")
        _require_supported(
            self.selected_source_mode,
            SCREEN3_REANALYSIS_SOURCE_MODES,
            "selected_source_mode",
        )
        _require_supported(
            self.selected_execution_mode,
            SCREEN3_REANALYSIS_EXECUTION_MODES,
            "selected_execution_mode",
        )
        _require_optional_string(
            self.selected_object_storage_reference,
            "selected_object_storage_reference",
        )
        _require_optional_string(
            self.selected_local_source_reference,
            "selected_local_source_reference",
        )
        _require_optional_string(
            self.selected_existing_run_reference,
            "selected_existing_run_reference",
        )
        _require_optional_string(
            self.selected_future_em_extract_reference,
            "selected_future_em_extract_reference",
        )
        _require_optional_string(self.notes, "notes")


@dataclass(frozen=True)
class BackendReAnalysisRequest:
    """Metadata-only request for future Screen 3 backend re-analysis."""

    request_id: str
    requested_action: str
    selected_state: Screen3SelectedState
    source_selection: dict[str, object] | None = None
    backend_execution_request: dict[str, object] | None = None
    actor_audit_context: dict[str, object] | None = None
    execution_mode: str = "static_read_only"
    adaptive_runtime_requested: bool = False
    deterministic_default: bool = True
    requires_validation: bool = True
    requires_actor: bool = True
    requires_source_validation: bool = True
    requires_backend_execution_validation: bool = True
    phase4i_contract_required: bool = True
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.request_id, "request_id")
        _require_supported(
            self.requested_action,
            SCREEN3_REANALYSIS_ACTIONS,
            "requested_action",
        )
        if not isinstance(self.selected_state, Screen3SelectedState):
            raise Screen3ReAnalysisRequestError(
                "selected_state must be a Screen3SelectedState instance."
            )
        self.selected_state.__post_init__()
        _require_optional_mapping(self.source_selection, "source_selection")
        _require_optional_mapping(
            self.backend_execution_request,
            "backend_execution_request",
        )
        _require_optional_mapping(self.actor_audit_context, "actor_audit_context")
        _require_supported(
            self.execution_mode,
            SCREEN3_REANALYSIS_EXECUTION_MODES,
            "execution_mode",
        )
        _require_bool(self.adaptive_runtime_requested, "adaptive_runtime_requested")
        _require_bool(self.deterministic_default, "deterministic_default")
        _require_bool(self.requires_validation, "requires_validation")
        _require_bool(self.requires_actor, "requires_actor")
        _require_bool(self.requires_source_validation, "requires_source_validation")
        _require_bool(
            self.requires_backend_execution_validation,
            "requires_backend_execution_validation",
        )
        _require_bool(self.phase4i_contract_required, "phase4i_contract_required")
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")
        if not self.deterministic_default:
            raise Screen3ReAnalysisRequestError(
                "deterministic_default must remain true in Phase 7AL."
            )
        if not self.requires_validation:
            raise Screen3ReAnalysisRequestError(
                "requires_validation must remain true in Phase 7AL."
            )
        if not self.requires_actor:
            raise Screen3ReAnalysisRequestError(
                "requires_actor must remain true in Phase 7AL."
            )
        if not self.requires_source_validation:
            raise Screen3ReAnalysisRequestError(
                "requires_source_validation must remain true in Phase 7AL."
            )
        if not self.requires_backend_execution_validation:
            raise Screen3ReAnalysisRequestError(
                "requires_backend_execution_validation must remain true in Phase 7AL."
            )
        if not self.phase4i_contract_required:
            raise Screen3ReAnalysisRequestError(
                "phase4i_contract_required must remain true in Phase 7AL."
            )


@dataclass(frozen=True)
class BackendReAnalysisRequestValidation:
    """Metadata result for Phase 7AL request validation."""

    validation_id: str
    request_id: str
    valid: bool
    validation_status: str
    requested_action: str
    source_mode: str
    execution_mode: str
    actor_present: bool
    source_validation_present: bool
    backend_execution_validation_present: bool
    can_execute: bool
    execution_blocked: bool
    denied_reasons: list[str]
    warnings: list[str]
    required_next_steps: list[str]
    phase4i_contract_required: bool
    deterministic_default: bool
    adaptive_runtime_requested: bool
    runtime_execution_performed: bool
    run_analysis_called: bool
    object_storage_called: bool
    local_file_read_performed: bool
    db_lookup_performed: bool
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.validation_id, "validation_id")
        _require_nonempty_string(self.request_id, "request_id")
        _require_bool(self.valid, "valid")
        _require_supported(
            self.validation_status,
            REANALYSIS_REQUEST_VALIDATION_STATUSES,
            "validation_status",
        )
        _require_supported(
            self.requested_action,
            SCREEN3_REANALYSIS_ACTIONS,
            "requested_action",
        )
        _require_supported(self.source_mode, SCREEN3_REANALYSIS_SOURCE_MODES, "source_mode")
        _require_supported(
            self.execution_mode,
            SCREEN3_REANALYSIS_EXECUTION_MODES,
            "execution_mode",
        )
        _require_bool(self.actor_present, "actor_present")
        _require_bool(self.source_validation_present, "source_validation_present")
        _require_bool(
            self.backend_execution_validation_present,
            "backend_execution_validation_present",
        )
        _require_bool(self.can_execute, "can_execute")
        _require_bool(self.execution_blocked, "execution_blocked")
        _require_list_of_strings(self.denied_reasons, "denied_reasons")
        _require_list_of_strings(self.warnings, "warnings")
        _require_list_of_strings(self.required_next_steps, "required_next_steps")
        _require_bool(self.phase4i_contract_required, "phase4i_contract_required")
        _require_bool(self.deterministic_default, "deterministic_default")
        _require_bool(self.adaptive_runtime_requested, "adaptive_runtime_requested")
        _require_bool(self.runtime_execution_performed, "runtime_execution_performed")
        _require_bool(self.run_analysis_called, "run_analysis_called")
        _require_bool(self.object_storage_called, "object_storage_called")
        _require_bool(self.local_file_read_performed, "local_file_read_performed")
        _require_bool(self.db_lookup_performed, "db_lookup_performed")
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")
        if self.can_execute:
            raise Screen3ReAnalysisRequestError(
                "can_execute must remain false in Phase 7AL."
            )
        if not self.execution_blocked:
            raise Screen3ReAnalysisRequestError(
                "execution_blocked must remain true in Phase 7AL."
            )
        if self.runtime_execution_performed:
            raise Screen3ReAnalysisRequestError(
                "runtime_execution_performed must remain false in Phase 7AL."
            )
        if self.run_analysis_called:
            raise Screen3ReAnalysisRequestError(
                "run_analysis_called must remain false in Phase 7AL."
            )
        if self.object_storage_called:
            raise Screen3ReAnalysisRequestError(
                "object_storage_called must remain false in Phase 7AL."
            )
        if self.local_file_read_performed:
            raise Screen3ReAnalysisRequestError(
                "local_file_read_performed must remain false in Phase 7AL."
            )
        if self.db_lookup_performed:
            raise Screen3ReAnalysisRequestError(
                "db_lookup_performed must remain false in Phase 7AL."
            )
        if not self.phase4i_contract_required:
            raise Screen3ReAnalysisRequestError(
                "phase4i_contract_required must remain true in Phase 7AL."
            )
        if not self.deterministic_default:
            raise Screen3ReAnalysisRequestError(
                "deterministic_default must remain true in Phase 7AL."
            )


def create_selected_state_id(
    selected_run: str | None = None,
    selected_awr: str | None = None,
    selected_snapshot: str | None = None,
) -> str:
    """Create a deterministic selected-state id."""

    _require_optional_string(selected_run, "selected_run")
    _require_optional_string(selected_awr, "selected_awr")
    _require_optional_string(selected_snapshot, "selected_snapshot")
    run_or_awr = selected_run or selected_awr or "NO-RUN-OR-AWR"
    snapshot = selected_snapshot or "NO-SNAPSHOT"
    return (
        "SCREEN3-SELECTED-STATE-"
        f"{_normalize_token(run_or_awr)}-"
        f"{_normalize_token(snapshot)}"
    )


def create_reanalysis_request_id(
    requested_action: str,
    selected_state_id: str,
    execution_mode: str,
) -> str:
    """Create a deterministic re-analysis request id."""

    _require_supported(
        requested_action,
        SCREEN3_REANALYSIS_ACTIONS,
        "requested_action",
    )
    _require_nonempty_string(selected_state_id, "selected_state_id")
    _require_supported(
        execution_mode,
        SCREEN3_REANALYSIS_EXECUTION_MODES,
        "execution_mode",
    )
    return (
        "SCREEN3-REANALYSIS-REQUEST-"
        f"{_normalize_token(requested_action)}-"
        f"{_normalize_token(selected_state_id)}-"
        f"{_normalize_token(execution_mode)}"
    )


def create_reanalysis_validation_id(request_id: str) -> str:
    """Create a deterministic re-analysis validation id."""

    _require_nonempty_string(request_id, "request_id")
    return f"SCREEN3-REANALYSIS-VALIDATION-{_normalize_token(request_id)}"


def validate_screen3_selected_state(
    state: Screen3SelectedState,
) -> Screen3SelectedState:
    """Validate selected-state metadata."""

    if not isinstance(state, Screen3SelectedState):
        raise Screen3ReAnalysisRequestError(
            "state must be a Screen3SelectedState instance."
        )
    state.__post_init__()
    return state


def validate_backend_reanalysis_request(
    request: BackendReAnalysisRequest,
) -> BackendReAnalysisRequest:
    """Validate backend re-analysis request metadata."""

    if not isinstance(request, BackendReAnalysisRequest):
        raise Screen3ReAnalysisRequestError(
            "request must be a BackendReAnalysisRequest instance."
        )
    request.__post_init__()
    return request


def evaluate_backend_reanalysis_request(
    request: BackendReAnalysisRequest,
) -> BackendReAnalysisRequestValidation:
    """Evaluate request metadata while blocking execution in Phase 7AL."""

    if not isinstance(request, BackendReAnalysisRequest):
        raise Screen3ReAnalysisRequestError(
            "request must be a BackendReAnalysisRequest instance."
        )
    request.__post_init__()

    denied_reasons = ["execution is not allowed in Phase 7AL"]
    warnings: list[str] = []
    required_next_steps = ["defer execution to a future controller phase"]
    status = "EXECUTION_NOT_ALLOWED_IN_THIS_PHASE"
    valid = True

    actor_present = bool(request.actor_audit_context)
    source_present = bool(request.source_selection)
    source_validation_present = _source_validation_present(request.source_selection)
    backend_validation_present = bool(request.backend_execution_request)
    source_mode = request.selected_state.selected_source_mode

    if not actor_present:
        status = "NEEDS_ACTOR"
        valid = False
        denied_reasons.append("actor audit context is required")
        required_next_steps.append("provide actor audit context")
    elif not source_present:
        status = "NEEDS_SOURCE_SELECTION"
        valid = False
        denied_reasons.append("source selection metadata is required")
        required_next_steps.append("provide source selection metadata")
    elif not source_validation_present:
        status = "NEEDS_SOURCE_VALIDATION"
        valid = False
        denied_reasons.append("source validation metadata is required")
        required_next_steps.append("provide source validation metadata")
    elif not backend_validation_present:
        status = "NEEDS_BACKEND_EXECUTION_VALIDATION"
        valid = False
        denied_reasons.append("backend execution validation metadata is required")
        required_next_steps.append("provide backend execution validation metadata")
    else:
        warnings.append("request is metadata-valid but execution remains blocked")

    return BackendReAnalysisRequestValidation(
        validation_id=create_reanalysis_validation_id(request.request_id),
        request_id=request.request_id,
        valid=valid,
        validation_status=status,
        requested_action=request.requested_action,
        source_mode=source_mode,
        execution_mode=request.execution_mode,
        actor_present=actor_present,
        source_validation_present=source_validation_present,
        backend_execution_validation_present=backend_validation_present,
        can_execute=False,
        execution_blocked=True,
        denied_reasons=denied_reasons,
        warnings=warnings,
        required_next_steps=required_next_steps,
        phase4i_contract_required=request.phase4i_contract_required,
        deterministic_default=request.deterministic_default,
        adaptive_runtime_requested=request.adaptive_runtime_requested,
        runtime_execution_performed=False,
        run_analysis_called=False,
        object_storage_called=False,
        local_file_read_performed=False,
        db_lookup_performed=False,
        created_at=None,
        notes=request.notes,
    )


def validate_backend_reanalysis_request_validation(
    validation: BackendReAnalysisRequestValidation,
) -> BackendReAnalysisRequestValidation:
    """Validate request validation metadata."""

    if not isinstance(validation, BackendReAnalysisRequestValidation):
        raise Screen3ReAnalysisRequestError(
            "validation must be a BackendReAnalysisRequestValidation instance."
        )
    validation.__post_init__()
    return validation


def screen3_selected_state_to_dict(state: Screen3SelectedState) -> dict[str, Any]:
    """Serialize selected-state metadata."""

    state = validate_screen3_selected_state(state)
    return {
        "selected_state_id": state.selected_state_id,
        "selected_awr": state.selected_awr,
        "selected_run": state.selected_run,
        "selected_database": state.selected_database,
        "selected_system": state.selected_system,
        "selected_snapshot": state.selected_snapshot,
        "selected_comparison_baseline": state.selected_comparison_baseline,
        "selected_issue_domain": state.selected_issue_domain,
        "selected_severity_status": state.selected_severity_status,
        "selected_source_mode": state.selected_source_mode,
        "selected_execution_mode": state.selected_execution_mode,
        "selected_object_storage_reference": state.selected_object_storage_reference,
        "selected_local_source_reference": state.selected_local_source_reference,
        "selected_existing_run_reference": state.selected_existing_run_reference,
        "selected_future_em_extract_reference": (
            state.selected_future_em_extract_reference
        ),
        "notes": state.notes,
    }


def screen3_selected_state_from_dict(data: dict[str, Any]) -> Screen3SelectedState:
    """Deserialize selected-state metadata."""

    _require_mapping(data, "selected_state")
    return Screen3SelectedState(
        selected_state_id=data.get("selected_state_id"),
        selected_awr=data.get("selected_awr"),
        selected_run=data.get("selected_run"),
        selected_database=data.get("selected_database"),
        selected_system=data.get("selected_system"),
        selected_snapshot=data.get("selected_snapshot"),
        selected_comparison_baseline=data.get("selected_comparison_baseline"),
        selected_issue_domain=data.get("selected_issue_domain"),
        selected_severity_status=data.get("selected_severity_status"),
        selected_source_mode=data.get("selected_source_mode", "none"),
        selected_execution_mode=data.get(
            "selected_execution_mode",
            "static_read_only",
        ),
        selected_object_storage_reference=data.get("selected_object_storage_reference"),
        selected_local_source_reference=data.get("selected_local_source_reference"),
        selected_existing_run_reference=data.get("selected_existing_run_reference"),
        selected_future_em_extract_reference=data.get(
            "selected_future_em_extract_reference"
        ),
        notes=data.get("notes"),
    )


def backend_reanalysis_request_to_dict(
    request: BackendReAnalysisRequest,
) -> dict[str, Any]:
    """Serialize re-analysis request metadata."""

    request = validate_backend_reanalysis_request(request)
    return {
        "request_id": request.request_id,
        "requested_action": request.requested_action,
        "selected_state": screen3_selected_state_to_dict(request.selected_state),
        "source_selection": request.source_selection,
        "backend_execution_request": request.backend_execution_request,
        "actor_audit_context": request.actor_audit_context,
        "execution_mode": request.execution_mode,
        "adaptive_runtime_requested": request.adaptive_runtime_requested,
        "deterministic_default": request.deterministic_default,
        "requires_validation": request.requires_validation,
        "requires_actor": request.requires_actor,
        "requires_source_validation": request.requires_source_validation,
        "requires_backend_execution_validation": (
            request.requires_backend_execution_validation
        ),
        "phase4i_contract_required": request.phase4i_contract_required,
        "created_at": request.created_at,
        "notes": request.notes,
    }


def backend_reanalysis_request_from_dict(
    data: dict[str, Any],
) -> BackendReAnalysisRequest:
    """Deserialize re-analysis request metadata."""

    _require_mapping(data, "backend_reanalysis_request")
    selected_state_data = data.get("selected_state")
    if selected_state_data is None:
        raise Screen3ReAnalysisRequestError("selected_state is required.")
    return BackendReAnalysisRequest(
        request_id=data.get("request_id"),
        requested_action=data.get("requested_action"),
        selected_state=screen3_selected_state_from_dict(selected_state_data),
        source_selection=data.get("source_selection"),
        backend_execution_request=data.get("backend_execution_request"),
        actor_audit_context=data.get("actor_audit_context"),
        execution_mode=data.get("execution_mode", "static_read_only"),
        adaptive_runtime_requested=data.get("adaptive_runtime_requested", False),
        deterministic_default=data.get("deterministic_default", True),
        requires_validation=data.get("requires_validation", True),
        requires_actor=data.get("requires_actor", True),
        requires_source_validation=data.get("requires_source_validation", True),
        requires_backend_execution_validation=data.get(
            "requires_backend_execution_validation",
            True,
        ),
        phase4i_contract_required=data.get("phase4i_contract_required", True),
        created_at=data.get("created_at"),
        notes=data.get("notes"),
    )


def backend_reanalysis_request_validation_to_dict(
    validation: BackendReAnalysisRequestValidation,
) -> dict[str, Any]:
    """Serialize request validation metadata."""

    validation = validate_backend_reanalysis_request_validation(validation)
    return {
        "validation_id": validation.validation_id,
        "request_id": validation.request_id,
        "valid": validation.valid,
        "validation_status": validation.validation_status,
        "requested_action": validation.requested_action,
        "source_mode": validation.source_mode,
        "execution_mode": validation.execution_mode,
        "actor_present": validation.actor_present,
        "source_validation_present": validation.source_validation_present,
        "backend_execution_validation_present": (
            validation.backend_execution_validation_present
        ),
        "can_execute": validation.can_execute,
        "execution_blocked": validation.execution_blocked,
        "denied_reasons": list(validation.denied_reasons),
        "warnings": list(validation.warnings),
        "required_next_steps": list(validation.required_next_steps),
        "phase4i_contract_required": validation.phase4i_contract_required,
        "deterministic_default": validation.deterministic_default,
        "adaptive_runtime_requested": validation.adaptive_runtime_requested,
        "runtime_execution_performed": validation.runtime_execution_performed,
        "run_analysis_called": validation.run_analysis_called,
        "object_storage_called": validation.object_storage_called,
        "local_file_read_performed": validation.local_file_read_performed,
        "db_lookup_performed": validation.db_lookup_performed,
        "created_at": validation.created_at,
        "notes": validation.notes,
    }


def backend_reanalysis_request_validation_from_dict(
    data: dict[str, Any],
) -> BackendReAnalysisRequestValidation:
    """Deserialize request validation metadata."""

    _require_mapping(data, "backend_reanalysis_request_validation")
    return BackendReAnalysisRequestValidation(
        validation_id=data.get("validation_id"),
        request_id=data.get("request_id"),
        valid=data.get("valid"),
        validation_status=data.get("validation_status"),
        requested_action=data.get("requested_action"),
        source_mode=data.get("source_mode"),
        execution_mode=data.get("execution_mode"),
        actor_present=data.get("actor_present"),
        source_validation_present=data.get("source_validation_present"),
        backend_execution_validation_present=data.get(
            "backend_execution_validation_present"
        ),
        can_execute=data.get("can_execute", False),
        execution_blocked=data.get("execution_blocked", True),
        denied_reasons=data.get("denied_reasons", []),
        warnings=data.get("warnings", []),
        required_next_steps=data.get("required_next_steps", []),
        phase4i_contract_required=data.get("phase4i_contract_required", True),
        deterministic_default=data.get("deterministic_default", True),
        adaptive_runtime_requested=data.get("adaptive_runtime_requested", False),
        runtime_execution_performed=data.get("runtime_execution_performed", False),
        run_analysis_called=data.get("run_analysis_called", False),
        object_storage_called=data.get("object_storage_called", False),
        local_file_read_performed=data.get("local_file_read_performed", False),
        db_lookup_performed=data.get("db_lookup_performed", False),
        created_at=data.get("created_at"),
        notes=data.get("notes"),
    )


def default_screen3_selected_state(notes: str | None = None) -> Screen3SelectedState:
    """Create a deterministic placeholder selected state."""

    _require_optional_string(notes, "notes")
    return Screen3SelectedState(
        selected_state_id=create_selected_state_id(),
        selected_source_mode="none",
        selected_execution_mode="static_read_only",
        notes=notes,
    )


def _source_validation_present(source_selection: dict[str, object] | None) -> bool:
    if not source_selection:
        return False
    validation_status = source_selection.get("validation_status")
    return isinstance(validation_status, str) and bool(validation_status.strip())


def _normalize_token(value: str) -> str:
    _require_nonempty_string(value, "value")
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().upper())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "NONE"


def _require_nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Screen3ReAnalysisRequestError(f"{field_name} is required.")
    return value


def _require_optional_string(value: Any, field_name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise Screen3ReAnalysisRequestError(
            f"{field_name} must be a string or None."
        )
    return value


def _require_supported(value: Any, supported: tuple[str, ...], field_name: str) -> str:
    if not isinstance(value, str) or value not in supported:
        raise Screen3ReAnalysisRequestError(f"Unsupported {field_name}: {value!r}.")
    return value


def _require_issue_domain(value: str) -> str:
    normalized = value.strip().upper()
    if normalized not in SCREEN3_REANALYSIS_ISSUE_DOMAINS:
        raise Screen3ReAnalysisRequestError(
            f"Unsupported selected_issue_domain: {value!r}."
        )
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise Screen3ReAnalysisRequestError(f"{field_name} must be boolean.")
    return value


def _require_list_of_strings(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise Screen3ReAnalysisRequestError(
            f"{field_name} must be a list of strings."
        )
    return value


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Screen3ReAnalysisRequestError(f"{field_name} must be a dictionary.")
    return value


def _require_optional_mapping(value: Any, field_name: str) -> dict[str, Any] | None:
    if value is not None and not isinstance(value, dict):
        raise Screen3ReAnalysisRequestError(
            f"{field_name} must be a dictionary or None."
        )
    return value
