"""Phase 7AM Screen 3 re-analysis controller metadata.

This module creates local controller records and in-memory comparison artifacts
for future Screen 3 re-analysis. It does not perform backend execution, load
sources, write artifacts, regenerate dashboards, or mutate runtime truth.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from src.learning.screen3_reanalysis_request import (
    BackendReAnalysisRequest,
    SCREEN3_REANALYSIS_ACTIONS,
    SCREEN3_REANALYSIS_EXECUTION_MODES,
    SCREEN3_REANALYSIS_SOURCE_MODES,
    evaluate_backend_reanalysis_request,
)


REANALYSIS_EXECUTION_STATUSES = (
    "PLANNED",
    "BLOCKED",
    "COMMAND_PREVIEW_ONLY",
    "COMPARISON_BUILT_IN_MEMORY",
    "EXECUTION_NOT_ALLOWED_IN_THIS_PHASE",
    "INVALID_REQUEST",
)

COMPARISON_DIFFERENCE_TYPES = (
    "score",
    "wait_event",
    "sql_concentration",
    "trend",
    "anomaly",
    "topology",
    "platform_target",
    "data_availability",
    "option_source",
)


class Screen3ReAnalysisControllerError(ValueError):
    """Raised when 7AM controller metadata is invalid."""


@dataclass(frozen=True)
class ReAnalysisExecutionPlan:
    """Metadata plan for a future backend re-analysis action."""

    execution_plan_id: str
    request_id: str
    requested_action: str
    execution_mode: str
    source_mode: str
    deterministic_default: bool
    adaptive_runtime_requested: bool
    phase4i_contract_required: bool
    validation_reference: str | None = None
    command_preview: str | None = None
    execution_steps: list[str] | None = None
    execution_allowed_for_future: bool = False
    execution_performed: bool = False
    run_analysis_called: bool = False
    object_storage_called: bool = False
    local_file_read_performed: bool = False
    db_lookup_performed: bool = False
    dashboard_regenerated: bool = False
    output_written: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.execution_plan_id, "execution_plan_id")
        _require_nonempty_string(self.request_id, "request_id")
        _require_supported(
            self.requested_action,
            SCREEN3_REANALYSIS_ACTIONS,
            "requested_action",
        )
        _require_supported(
            self.execution_mode,
            SCREEN3_REANALYSIS_EXECUTION_MODES,
            "execution_mode",
        )
        _require_supported(self.source_mode, SCREEN3_REANALYSIS_SOURCE_MODES, "source_mode")
        _require_bool(self.deterministic_default, "deterministic_default")
        _require_bool(self.adaptive_runtime_requested, "adaptive_runtime_requested")
        _require_bool(self.phase4i_contract_required, "phase4i_contract_required")
        _require_optional_string(self.validation_reference, "validation_reference")
        _require_optional_string(self.command_preview, "command_preview")
        steps = [] if self.execution_steps is None else self.execution_steps
        _require_list_of_strings(steps, "execution_steps")
        _require_bool(self.execution_allowed_for_future, "execution_allowed_for_future")
        _require_bool(self.execution_performed, "execution_performed")
        _require_bool(self.run_analysis_called, "run_analysis_called")
        _require_bool(self.object_storage_called, "object_storage_called")
        _require_bool(self.local_file_read_performed, "local_file_read_performed")
        _require_bool(self.db_lookup_performed, "db_lookup_performed")
        _require_bool(self.dashboard_regenerated, "dashboard_regenerated")
        _require_bool(self.output_written, "output_written")
        _require_optional_string(self.notes, "notes")
        if not self.deterministic_default:
            raise Screen3ReAnalysisControllerError(
                "deterministic_default must remain true in Phase 7AM."
            )
        if not self.phase4i_contract_required:
            raise Screen3ReAnalysisControllerError(
                "phase4i_contract_required must remain true in Phase 7AM."
            )
        _reject_true(self.execution_performed, "execution_performed")
        _reject_true(self.run_analysis_called, "run_analysis_called")
        _reject_true(self.object_storage_called, "object_storage_called")
        _reject_true(self.local_file_read_performed, "local_file_read_performed")
        _reject_true(self.db_lookup_performed, "db_lookup_performed")
        _reject_true(self.dashboard_regenerated, "dashboard_regenerated")
        _reject_true(self.output_written, "output_written")


@dataclass(frozen=True)
class AWRReportComparisonArtifact:
    """Local in-memory comparison artifact for supplied report summaries."""

    comparison_id: str
    comparison_name: str
    compared_report_count: int
    compared_run_ids: list[str]
    compared_awr_ids: list[str]
    baseline_reference: str | None
    target_references: list[str]
    score_differences: dict[str, Any]
    wait_event_differences: dict[str, Any]
    sql_concentration_differences: dict[str, Any]
    trend_differences: dict[str, Any]
    anomaly_differences: dict[str, Any]
    topology_differences: dict[str, Any]
    platform_target_differences: dict[str, Any]
    data_availability_differences: dict[str, Any]
    difference_summary: str
    likely_difference_drivers: list[str]
    comparison_limitations: list[str]
    artifact_written: bool = False
    dashboard_generated: bool = False
    phase4i_mutated: bool = False
    created_by: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.comparison_id, "comparison_id")
        _require_nonempty_string(self.comparison_name, "comparison_name")
        if not isinstance(self.compared_report_count, int) or self.compared_report_count < 2:
            raise Screen3ReAnalysisControllerError(
                "compared_report_count must be at least 2."
            )
        _require_list_of_strings(self.compared_run_ids, "compared_run_ids")
        _require_list_of_strings(self.compared_awr_ids, "compared_awr_ids")
        _require_optional_string(self.baseline_reference, "baseline_reference")
        _require_list_of_strings(self.target_references, "target_references")
        _require_mapping(self.score_differences, "score_differences")
        _require_mapping(self.wait_event_differences, "wait_event_differences")
        _require_mapping(
            self.sql_concentration_differences,
            "sql_concentration_differences",
        )
        _require_mapping(self.trend_differences, "trend_differences")
        _require_mapping(self.anomaly_differences, "anomaly_differences")
        _require_mapping(self.topology_differences, "topology_differences")
        _require_mapping(
            self.platform_target_differences,
            "platform_target_differences",
        )
        _require_mapping(
            self.data_availability_differences,
            "data_availability_differences",
        )
        _require_nonempty_string(self.difference_summary, "difference_summary")
        _require_list_of_strings(
            self.likely_difference_drivers,
            "likely_difference_drivers",
        )
        _require_list_of_strings(self.comparison_limitations, "comparison_limitations")
        _require_bool(self.artifact_written, "artifact_written")
        _require_bool(self.dashboard_generated, "dashboard_generated")
        _require_bool(self.phase4i_mutated, "phase4i_mutated")
        _require_optional_string(self.created_by, "created_by")
        _require_optional_string(self.notes, "notes")
        _reject_true(self.artifact_written, "artifact_written")
        _reject_true(self.dashboard_generated, "dashboard_generated")
        _reject_true(self.phase4i_mutated, "phase4i_mutated")


@dataclass(frozen=True)
class ReAnalysisExecutionResult:
    """Controller decision result for a Screen 3 re-analysis request."""

    execution_result_id: str
    request_id: str
    requested_action: str
    execution_status: str
    execution_plan: ReAnalysisExecutionPlan | None = None
    comparison_artifact: AWRReportComparisonArtifact | None = None
    validation_status: str | None = None
    denied_reasons: list[str] | None = None
    warnings: list[str] | None = None
    required_next_steps: list[str] | None = None
    output_artifact_reference: str | None = None
    phase4i_reference: str | None = None
    dashboard_reference: str | None = None
    runtime_execution_performed: bool = False
    phase4i_mutated: bool = False
    dashboard_regenerated: bool = False
    output_written: bool = False
    deterministic_runtime_authoritative: bool = True
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.execution_result_id, "execution_result_id")
        _require_nonempty_string(self.request_id, "request_id")
        _require_supported(
            self.requested_action,
            SCREEN3_REANALYSIS_ACTIONS,
            "requested_action",
        )
        _require_supported(
            self.execution_status,
            REANALYSIS_EXECUTION_STATUSES,
            "execution_status",
        )
        if self.execution_plan is not None:
            validate_reanalysis_execution_plan(self.execution_plan)
        if self.comparison_artifact is not None:
            validate_awr_report_comparison_artifact(self.comparison_artifact)
        _require_optional_string(self.validation_status, "validation_status")
        denied = [] if self.denied_reasons is None else self.denied_reasons
        warnings = [] if self.warnings is None else self.warnings
        next_steps = [] if self.required_next_steps is None else self.required_next_steps
        _require_list_of_strings(denied, "denied_reasons")
        _require_list_of_strings(warnings, "warnings")
        _require_list_of_strings(next_steps, "required_next_steps")
        _require_optional_string(self.output_artifact_reference, "output_artifact_reference")
        _require_optional_string(self.phase4i_reference, "phase4i_reference")
        _require_optional_string(self.dashboard_reference, "dashboard_reference")
        _require_bool(self.runtime_execution_performed, "runtime_execution_performed")
        _require_bool(self.phase4i_mutated, "phase4i_mutated")
        _require_bool(self.dashboard_regenerated, "dashboard_regenerated")
        _require_bool(self.output_written, "output_written")
        _require_bool(
            self.deterministic_runtime_authoritative,
            "deterministic_runtime_authoritative",
        )
        _require_optional_string(self.notes, "notes")
        _reject_true(self.runtime_execution_performed, "runtime_execution_performed")
        _reject_true(self.phase4i_mutated, "phase4i_mutated")
        _reject_true(self.dashboard_regenerated, "dashboard_regenerated")
        _reject_true(self.output_written, "output_written")
        if not self.deterministic_runtime_authoritative:
            raise Screen3ReAnalysisControllerError(
                "deterministic_runtime_authoritative must remain true."
            )


def create_reanalysis_execution_plan_id(request_id: str, requested_action: str) -> str:
    """Create a deterministic execution plan id."""

    _require_nonempty_string(request_id, "request_id")
    _require_supported(
        requested_action,
        SCREEN3_REANALYSIS_ACTIONS,
        "requested_action",
    )
    return (
        "SCREEN3-REANALYSIS-PLAN-"
        f"{_normalize_token(request_id)}-"
        f"{_normalize_token(requested_action)}"
    )


def create_reanalysis_execution_result_id(request_id: str, requested_action: str) -> str:
    """Create a deterministic execution result id."""

    _require_nonempty_string(request_id, "request_id")
    _require_supported(
        requested_action,
        SCREEN3_REANALYSIS_ACTIONS,
        "requested_action",
    )
    return (
        "SCREEN3-REANALYSIS-RESULT-"
        f"{_normalize_token(request_id)}-"
        f"{_normalize_token(requested_action)}"
    )


def create_awr_report_comparison_id(
    comparison_name: str,
    compared_ids: list[str],
) -> str:
    """Create a deterministic comparison id."""

    _require_nonempty_string(comparison_name, "comparison_name")
    _require_list_of_strings(compared_ids, "compared_ids")
    if not compared_ids:
        raise Screen3ReAnalysisControllerError("compared_ids is required.")
    return (
        "AWR-COMPARISON-"
        f"{_normalize_token(comparison_name)}-"
        f"{_normalize_token('-'.join(compared_ids))}"
    )


def validate_reanalysis_execution_plan(
    plan: ReAnalysisExecutionPlan,
) -> ReAnalysisExecutionPlan:
    """Validate execution plan metadata."""

    if not isinstance(plan, ReAnalysisExecutionPlan):
        raise Screen3ReAnalysisControllerError(
            "plan must be a ReAnalysisExecutionPlan instance."
        )
    plan.__post_init__()
    return plan


def validate_reanalysis_execution_result(
    result: ReAnalysisExecutionResult,
) -> ReAnalysisExecutionResult:
    """Validate execution result metadata."""

    if not isinstance(result, ReAnalysisExecutionResult):
        raise Screen3ReAnalysisControllerError(
            "result must be a ReAnalysisExecutionResult instance."
        )
    result.__post_init__()
    return result


def validate_awr_report_comparison_artifact(
    artifact: AWRReportComparisonArtifact,
) -> AWRReportComparisonArtifact:
    """Validate in-memory comparison artifact metadata."""

    if not isinstance(artifact, AWRReportComparisonArtifact):
        raise Screen3ReAnalysisControllerError(
            "artifact must be an AWRReportComparisonArtifact instance."
        )
    artifact.__post_init__()
    return artifact


def build_reanalysis_execution_plan(
    request: BackendReAnalysisRequest,
    command_preview: str | None = None,
    execution_steps: list[str] | None = None,
    notes: str | None = None,
) -> ReAnalysisExecutionPlan:
    """Build a non-executing metadata plan for a request."""

    if not isinstance(request, BackendReAnalysisRequest):
        raise Screen3ReAnalysisControllerError(
            "request must be a BackendReAnalysisRequest instance."
        )
    request.__post_init__()
    validation = evaluate_backend_reanalysis_request(request)
    steps = execution_steps or [
        "validate actor metadata",
        "validate source metadata",
        "validate backend execution metadata",
        "keep execution blocked in Phase 7AM",
    ]
    _require_list_of_strings(steps, "execution_steps")
    return ReAnalysisExecutionPlan(
        execution_plan_id=create_reanalysis_execution_plan_id(
            request.request_id,
            request.requested_action,
        ),
        request_id=request.request_id,
        requested_action=request.requested_action,
        execution_mode=request.execution_mode,
        source_mode=request.selected_state.selected_source_mode,
        deterministic_default=request.deterministic_default,
        adaptive_runtime_requested=request.adaptive_runtime_requested,
        phase4i_contract_required=request.phase4i_contract_required,
        validation_reference=validation.validation_id,
        command_preview=command_preview,
        execution_steps=steps,
        execution_allowed_for_future=validation.valid,
        execution_performed=False,
        run_analysis_called=False,
        object_storage_called=False,
        local_file_read_performed=False,
        db_lookup_performed=False,
        dashboard_regenerated=False,
        output_written=False,
        notes=notes if notes is not None else request.notes,
    )


def evaluate_reanalysis_execution(
    request: BackendReAnalysisRequest,
    comparison_inputs: list[dict[str, Any]] | None = None,
    created_by: str | None = None,
    notes: str | None = None,
) -> ReAnalysisExecutionResult:
    """Evaluate controller metadata without performing backend execution."""

    if not isinstance(request, BackendReAnalysisRequest):
        raise Screen3ReAnalysisControllerError(
            "request must be a BackendReAnalysisRequest instance."
        )
    request.__post_init__()
    validation = evaluate_backend_reanalysis_request(request)
    plan = build_reanalysis_execution_plan(request, notes=notes)
    denied = list(validation.denied_reasons)
    warnings = list(validation.warnings)
    next_steps = list(validation.required_next_steps)
    comparison_artifact = None
    status = "EXECUTION_NOT_ALLOWED_IN_THIS_PHASE"

    if not validation.valid:
        status = "INVALID_REQUEST"
    elif request.requested_action == "load_from_object_storage":
        status = "BLOCKED"
        denied.append("object storage loading is not implemented in Phase 7AM")
        next_steps.append("defer object storage loading to a future execution phase")
    elif request.requested_action == "build_comparison":
        if comparison_inputs is None or len(comparison_inputs) < 2:
            status = "BLOCKED"
            denied.append("at least two in-memory comparison inputs are required")
            next_steps.append("supply at least two in-memory report summaries")
        else:
            comparison_artifact = build_awr_report_comparison(
                comparison_inputs,
                comparison_name="Screen 3 comparison",
                baseline_reference=None,
                created_by=created_by,
                notes=notes,
            )
            status = "COMPARISON_BUILT_IN_MEMORY"
            warnings.append("comparison artifact is in-memory metadata only")
    elif request.execution_mode == "local_command_generation":
        status = "COMMAND_PREVIEW_ONLY"
        warnings.append("command preview metadata only")
    elif request.requested_action in ("analyze_selection", "rerun_analysis"):
        status = "PLANNED"
        warnings.append("execution plan created but not performed")

    return ReAnalysisExecutionResult(
        execution_result_id=create_reanalysis_execution_result_id(
            request.request_id,
            request.requested_action,
        ),
        request_id=request.request_id,
        requested_action=request.requested_action,
        execution_status=status,
        execution_plan=plan,
        comparison_artifact=comparison_artifact,
        validation_status=validation.validation_status,
        denied_reasons=denied,
        warnings=warnings,
        required_next_steps=next_steps,
        output_artifact_reference=None,
        phase4i_reference=None,
        dashboard_reference=None,
        runtime_execution_performed=False,
        phase4i_mutated=False,
        dashboard_regenerated=False,
        output_written=False,
        deterministic_runtime_authoritative=True,
        notes=notes if notes is not None else request.notes,
    )


def build_awr_report_comparison(
    comparison_inputs: list[dict[str, Any]],
    comparison_name: str | None = None,
    baseline_reference: str | None = None,
    created_by: str | None = None,
    notes: str | None = None,
) -> AWRReportComparisonArtifact:
    """Compare supplied in-memory report summaries only."""

    if not isinstance(comparison_inputs, list):
        raise Screen3ReAnalysisControllerError("comparison_inputs must be a list.")
    if len(comparison_inputs) < 2:
        raise Screen3ReAnalysisControllerError(
            "at least two comparison inputs are required."
        )
    for item in comparison_inputs:
        _require_mapping(item, "comparison input")
    _require_optional_string(comparison_name, "comparison_name")
    _require_optional_string(baseline_reference, "baseline_reference")
    _require_optional_string(created_by, "created_by")
    _require_optional_string(notes, "notes")

    name = comparison_name or "AWR report comparison"
    references = [_report_reference(item, index) for index, item in enumerate(comparison_inputs)]
    baseline = baseline_reference or references[0]
    targets = references[1:]
    compared_ids = references

    score_differences, score_missing = _compare_numeric_sections(
        comparison_inputs,
        references,
        ("scores", "domain_scores"),
    )
    wait_differences, wait_missing = _compare_numeric_sections(
        comparison_inputs,
        references,
        ("waits", "wait_events"),
    )
    sql_differences, sql_missing = _compare_numeric_sections(
        comparison_inputs,
        references,
        ("sql_concentration", "top_sql_concentration"),
    )
    trend_differences, trend_missing = _compare_mixed_sections(
        comparison_inputs,
        references,
        ("trends",),
    )
    anomaly_differences, anomaly_missing = _compare_mixed_sections(
        comparison_inputs,
        references,
        ("anomalies",),
    )
    topology_differences, topology_missing = _compare_mixed_sections(
        comparison_inputs,
        references,
        ("topology",),
    )
    platform_differences, platform_missing = _compare_mixed_sections(
        comparison_inputs,
        references,
        ("platform_target", "target_platform", "source_options"),
    )
    supplied_availability, availability_missing = _compare_mixed_sections(
        comparison_inputs,
        references,
        ("data_availability", "missing_metrics"),
    )
    data_availability_differences = {
        "supplied_data_availability": supplied_availability,
        "missing_values": sorted(
            score_missing
            + wait_missing
            + sql_missing
            + trend_missing
            + anomaly_missing
            + topology_missing
            + platform_missing
            + availability_missing,
            key=lambda item: (item["field"], item["reference"]),
        ),
    }

    limitations = _comparison_limitations(
        comparison_inputs,
        data_availability_differences,
        references,
    )
    drivers = _difference_drivers(
        score_differences=score_differences,
        wait_event_differences=wait_differences,
        sql_concentration_differences=sql_differences,
        trend_differences=trend_differences,
        anomaly_differences=anomaly_differences,
        topology_differences=topology_differences,
        platform_target_differences=platform_differences,
        data_availability_differences=data_availability_differences,
    )
    summary = _difference_summary(
        report_count=len(comparison_inputs),
        score_differences=score_differences,
        wait_event_differences=wait_differences,
        sql_concentration_differences=sql_differences,
        trend_differences=trend_differences,
        anomaly_differences=anomaly_differences,
        topology_differences=topology_differences,
        platform_target_differences=platform_differences,
        data_availability_differences=data_availability_differences,
    )

    return AWRReportComparisonArtifact(
        comparison_id=create_awr_report_comparison_id(name, compared_ids),
        comparison_name=name,
        compared_report_count=len(comparison_inputs),
        compared_run_ids=_string_values(comparison_inputs, "run_id"),
        compared_awr_ids=_string_values(comparison_inputs, "awr_id"),
        baseline_reference=baseline,
        target_references=targets,
        score_differences=score_differences,
        wait_event_differences=wait_differences,
        sql_concentration_differences=sql_differences,
        trend_differences=trend_differences,
        anomaly_differences=anomaly_differences,
        topology_differences=topology_differences,
        platform_target_differences=platform_differences,
        data_availability_differences=data_availability_differences,
        difference_summary=summary,
        likely_difference_drivers=drivers,
        comparison_limitations=limitations,
        artifact_written=False,
        dashboard_generated=False,
        phase4i_mutated=False,
        created_by=created_by,
        notes=notes,
    )


def reanalysis_execution_plan_to_dict(plan: ReAnalysisExecutionPlan) -> dict[str, Any]:
    """Serialize execution plan metadata."""

    plan = validate_reanalysis_execution_plan(plan)
    return {
        "execution_plan_id": plan.execution_plan_id,
        "request_id": plan.request_id,
        "requested_action": plan.requested_action,
        "execution_mode": plan.execution_mode,
        "source_mode": plan.source_mode,
        "deterministic_default": plan.deterministic_default,
        "adaptive_runtime_requested": plan.adaptive_runtime_requested,
        "phase4i_contract_required": plan.phase4i_contract_required,
        "validation_reference": plan.validation_reference,
        "command_preview": plan.command_preview,
        "execution_steps": list(plan.execution_steps or []),
        "execution_allowed_for_future": plan.execution_allowed_for_future,
        "execution_performed": plan.execution_performed,
        "run_analysis_called": plan.run_analysis_called,
        "object_storage_called": plan.object_storage_called,
        "local_file_read_performed": plan.local_file_read_performed,
        "db_lookup_performed": plan.db_lookup_performed,
        "dashboard_regenerated": plan.dashboard_regenerated,
        "output_written": plan.output_written,
        "notes": plan.notes,
    }


def reanalysis_execution_plan_from_dict(data: dict[str, Any]) -> ReAnalysisExecutionPlan:
    """Deserialize execution plan metadata."""

    _require_mapping(data, "reanalysis_execution_plan")
    return ReAnalysisExecutionPlan(
        execution_plan_id=data.get("execution_plan_id"),
        request_id=data.get("request_id"),
        requested_action=data.get("requested_action"),
        execution_mode=data.get("execution_mode"),
        source_mode=data.get("source_mode"),
        deterministic_default=data.get("deterministic_default"),
        adaptive_runtime_requested=data.get("adaptive_runtime_requested", False),
        phase4i_contract_required=data.get("phase4i_contract_required"),
        validation_reference=data.get("validation_reference"),
        command_preview=data.get("command_preview"),
        execution_steps=data.get("execution_steps", []),
        execution_allowed_for_future=data.get("execution_allowed_for_future", False),
        execution_performed=data.get("execution_performed", False),
        run_analysis_called=data.get("run_analysis_called", False),
        object_storage_called=data.get("object_storage_called", False),
        local_file_read_performed=data.get("local_file_read_performed", False),
        db_lookup_performed=data.get("db_lookup_performed", False),
        dashboard_regenerated=data.get("dashboard_regenerated", False),
        output_written=data.get("output_written", False),
        notes=data.get("notes"),
    )


def reanalysis_execution_result_to_dict(
    result: ReAnalysisExecutionResult,
) -> dict[str, Any]:
    """Serialize execution result metadata."""

    result = validate_reanalysis_execution_result(result)
    return {
        "execution_result_id": result.execution_result_id,
        "request_id": result.request_id,
        "requested_action": result.requested_action,
        "execution_status": result.execution_status,
        "execution_plan": (
            reanalysis_execution_plan_to_dict(result.execution_plan)
            if result.execution_plan
            else None
        ),
        "comparison_artifact": (
            awr_report_comparison_artifact_to_dict(result.comparison_artifact)
            if result.comparison_artifact
            else None
        ),
        "validation_status": result.validation_status,
        "denied_reasons": list(result.denied_reasons or []),
        "warnings": list(result.warnings or []),
        "required_next_steps": list(result.required_next_steps or []),
        "output_artifact_reference": result.output_artifact_reference,
        "phase4i_reference": result.phase4i_reference,
        "dashboard_reference": result.dashboard_reference,
        "runtime_execution_performed": result.runtime_execution_performed,
        "phase4i_mutated": result.phase4i_mutated,
        "dashboard_regenerated": result.dashboard_regenerated,
        "output_written": result.output_written,
        "deterministic_runtime_authoritative": (
            result.deterministic_runtime_authoritative
        ),
        "notes": result.notes,
    }


def reanalysis_execution_result_from_dict(
    data: dict[str, Any],
) -> ReAnalysisExecutionResult:
    """Deserialize execution result metadata."""

    _require_mapping(data, "reanalysis_execution_result")
    plan_data = data.get("execution_plan")
    comparison_data = data.get("comparison_artifact")
    return ReAnalysisExecutionResult(
        execution_result_id=data.get("execution_result_id"),
        request_id=data.get("request_id"),
        requested_action=data.get("requested_action"),
        execution_status=data.get("execution_status"),
        execution_plan=(
            reanalysis_execution_plan_from_dict(plan_data)
            if plan_data is not None
            else None
        ),
        comparison_artifact=(
            awr_report_comparison_artifact_from_dict(comparison_data)
            if comparison_data is not None
            else None
        ),
        validation_status=data.get("validation_status"),
        denied_reasons=data.get("denied_reasons", []),
        warnings=data.get("warnings", []),
        required_next_steps=data.get("required_next_steps", []),
        output_artifact_reference=data.get("output_artifact_reference"),
        phase4i_reference=data.get("phase4i_reference"),
        dashboard_reference=data.get("dashboard_reference"),
        runtime_execution_performed=data.get("runtime_execution_performed", False),
        phase4i_mutated=data.get("phase4i_mutated", False),
        dashboard_regenerated=data.get("dashboard_regenerated", False),
        output_written=data.get("output_written", False),
        deterministic_runtime_authoritative=data.get(
            "deterministic_runtime_authoritative",
            True,
        ),
        notes=data.get("notes"),
    )


def awr_report_comparison_artifact_to_dict(
    artifact: AWRReportComparisonArtifact,
) -> dict[str, Any]:
    """Serialize comparison artifact metadata."""

    artifact = validate_awr_report_comparison_artifact(artifact)
    return {
        "comparison_id": artifact.comparison_id,
        "comparison_name": artifact.comparison_name,
        "compared_report_count": artifact.compared_report_count,
        "compared_run_ids": list(artifact.compared_run_ids),
        "compared_awr_ids": list(artifact.compared_awr_ids),
        "baseline_reference": artifact.baseline_reference,
        "target_references": list(artifact.target_references),
        "score_differences": artifact.score_differences,
        "wait_event_differences": artifact.wait_event_differences,
        "sql_concentration_differences": artifact.sql_concentration_differences,
        "trend_differences": artifact.trend_differences,
        "anomaly_differences": artifact.anomaly_differences,
        "topology_differences": artifact.topology_differences,
        "platform_target_differences": artifact.platform_target_differences,
        "data_availability_differences": artifact.data_availability_differences,
        "difference_summary": artifact.difference_summary,
        "likely_difference_drivers": list(artifact.likely_difference_drivers),
        "comparison_limitations": list(artifact.comparison_limitations),
        "artifact_written": artifact.artifact_written,
        "dashboard_generated": artifact.dashboard_generated,
        "phase4i_mutated": artifact.phase4i_mutated,
        "created_by": artifact.created_by,
        "notes": artifact.notes,
    }


def awr_report_comparison_artifact_from_dict(
    data: dict[str, Any],
) -> AWRReportComparisonArtifact:
    """Deserialize comparison artifact metadata."""

    _require_mapping(data, "awr_report_comparison_artifact")
    return AWRReportComparisonArtifact(
        comparison_id=data.get("comparison_id"),
        comparison_name=data.get("comparison_name"),
        compared_report_count=data.get("compared_report_count"),
        compared_run_ids=data.get("compared_run_ids", []),
        compared_awr_ids=data.get("compared_awr_ids", []),
        baseline_reference=data.get("baseline_reference"),
        target_references=data.get("target_references", []),
        score_differences=data.get("score_differences", {}),
        wait_event_differences=data.get("wait_event_differences", {}),
        sql_concentration_differences=data.get("sql_concentration_differences", {}),
        trend_differences=data.get("trend_differences", {}),
        anomaly_differences=data.get("anomaly_differences", {}),
        topology_differences=data.get("topology_differences", {}),
        platform_target_differences=data.get("platform_target_differences", {}),
        data_availability_differences=data.get("data_availability_differences", {}),
        difference_summary=data.get("difference_summary"),
        likely_difference_drivers=data.get("likely_difference_drivers", []),
        comparison_limitations=data.get("comparison_limitations", []),
        artifact_written=data.get("artifact_written", False),
        dashboard_generated=data.get("dashboard_generated", False),
        phase4i_mutated=data.get("phase4i_mutated", False),
        created_by=data.get("created_by"),
        notes=data.get("notes"),
    )


def _compare_numeric_sections(
    reports: list[dict[str, Any]],
    references: list[str],
    section_names: tuple[str, ...],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    flattened = [_flatten_selected(report, section_names) for report in reports]
    fields = sorted({field for values in flattened for field in values})
    differences: dict[str, Any] = {}
    missing: list[dict[str, str]] = []
    for field in fields:
        baseline_value = flattened[0].get(field)
        if baseline_value is None:
            missing.append({"reference": references[0], "field": field})
            continue
        target_entries = []
        for index, values in enumerate(flattened[1:], start=1):
            target_value = values.get(field)
            if target_value is None:
                missing.append({"reference": references[index], "field": field})
                continue
            if _is_number(baseline_value) and _is_number(target_value):
                difference = target_value - baseline_value
                if difference != 0:
                    target_entries.append(
                        {
                            "reference": references[index],
                            "baseline": baseline_value,
                            "value": target_value,
                            "difference": difference,
                        }
                    )
            elif target_value != baseline_value:
                target_entries.append(
                    {
                        "reference": references[index],
                        "baseline": baseline_value,
                        "value": target_value,
                        "changed": True,
                    }
                )
        if target_entries:
            differences[field] = {"targets": target_entries}
    return differences, missing


def _compare_mixed_sections(
    reports: list[dict[str, Any]],
    references: list[str],
    section_names: tuple[str, ...],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    flattened = [_flatten_selected(report, section_names) for report in reports]
    fields = sorted({field for values in flattened for field in values})
    differences: dict[str, Any] = {}
    missing: list[dict[str, str]] = []
    for field in fields:
        baseline_marker = flattened[0].get(field, _MISSING)
        if baseline_marker is _MISSING:
            missing.append({"reference": references[0], "field": field})
            continue
        target_entries = []
        for index, values in enumerate(flattened[1:], start=1):
            target_marker = values.get(field, _MISSING)
            if target_marker is _MISSING:
                missing.append({"reference": references[index], "field": field})
                continue
            if target_marker != baseline_marker:
                entry: dict[str, Any] = {
                    "reference": references[index],
                    "baseline": baseline_marker,
                    "value": target_marker,
                    "changed": True,
                }
                if _is_number(baseline_marker) and _is_number(target_marker):
                    entry["difference"] = target_marker - baseline_marker
                target_entries.append(entry)
        if target_entries:
            differences[field] = {"targets": target_entries}
    return differences, missing


def _flatten_selected(
    report: dict[str, Any],
    section_names: tuple[str, ...],
) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for section_name in section_names:
        if section_name in report:
            _flatten_value(section_name, report[section_name], flattened)
    return flattened


def _flatten_value(prefix: str, value: Any, target: dict[str, Any]) -> None:
    if isinstance(value, dict):
        for key in sorted(value):
            _flatten_value(f"{prefix}.{key}", value[key], target)
    elif isinstance(value, list):
        target[prefix] = tuple(value)
    else:
        target[prefix] = value


def _comparison_limitations(
    reports: list[dict[str, Any]],
    data_availability_differences: dict[str, Any],
    references: list[str],
) -> list[str]:
    limitations: list[str] = []
    missing_values = data_availability_differences.get("missing_values", [])
    if missing_values:
        limitations.append("Some supplied report summaries are missing comparison fields.")
    if not _string_values(reports, "run_id") and not _string_values(reports, "awr_id"):
        limitations.append("No run_id or awr_id values were supplied for comparison identity.")
    for index, report in enumerate(reports):
        if "data_availability" not in report and "missing_metrics" not in report:
            limitations.append(
                f"{references[index]} has no explicit data availability metadata."
            )
    return _unique_strings(limitations)


def _difference_drivers(**difference_sections: dict[str, Any]) -> list[str]:
    labels = {
        "score_differences": "score changes",
        "wait_event_differences": "wait/event posture changes",
        "sql_concentration_differences": "SQL concentration changes",
        "trend_differences": "trend indicator changes",
        "anomaly_differences": "anomaly indicator changes",
        "topology_differences": "topology differences",
        "platform_target_differences": "platform/target/source option differences",
        "data_availability_differences": "data availability differences",
    }
    drivers = []
    for key, value in difference_sections.items():
        if key == "data_availability_differences":
            missing = value.get("missing_values", [])
            supplied = value.get("supplied_data_availability", {})
            if missing or supplied:
                drivers.append(labels[key])
        elif value:
            drivers.append(labels[key])
    return drivers or ["No supplied differences detected."]


def _difference_summary(**sections: Any) -> str:
    report_count = sections.pop("report_count")
    counts = []
    for key in (
        "score_differences",
        "wait_event_differences",
        "sql_concentration_differences",
        "trend_differences",
        "anomaly_differences",
        "topology_differences",
        "platform_target_differences",
    ):
        counts.append(f"{key.replace('_', ' ')}={len(sections[key])}")
    missing_count = len(
        sections["data_availability_differences"].get("missing_values", [])
    )
    counts.append(f"missing values={missing_count}")
    return f"Compared {report_count} supplied report summaries; " + "; ".join(counts)


def _report_reference(report: dict[str, Any], index: int) -> str:
    for key in ("run_id", "awr_id", "snapshot_label", "database_name"):
        value = report.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return f"report-{index + 1}"


def _string_values(reports: list[dict[str, Any]], key: str) -> list[str]:
    return [
        value
        for value in (report.get(key) for report in reports)
        if isinstance(value, str) and value.strip()
    ]


def _unique_strings(values: list[str]) -> list[str]:
    seen = set()
    unique = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _is_number(value: Any) -> bool:
    return type(value) in (int, float)


def _normalize_token(value: str) -> str:
    _require_nonempty_string(value, "value")
    normalized = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().upper())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    return normalized or "NONE"


def _require_nonempty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise Screen3ReAnalysisControllerError(f"{field_name} is required.")
    return value


def _require_optional_string(value: Any, field_name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise Screen3ReAnalysisControllerError(
            f"{field_name} must be a string or None."
        )
    return value


def _require_supported(value: Any, supported: tuple[str, ...], field_name: str) -> str:
    if not isinstance(value, str) or value not in supported:
        raise Screen3ReAnalysisControllerError(f"Unsupported {field_name}: {value!r}.")
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise Screen3ReAnalysisControllerError(f"{field_name} must be boolean.")
    return value


def _require_list_of_strings(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise Screen3ReAnalysisControllerError(
            f"{field_name} must be a list of strings."
        )
    return value


def _require_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise Screen3ReAnalysisControllerError(f"{field_name} must be a dictionary.")
    return value


def _reject_true(value: bool, field_name: str) -> None:
    if value:
        raise Screen3ReAnalysisControllerError(
            f"{field_name} must remain false in Phase 7AM."
        )


_MISSING = object()
