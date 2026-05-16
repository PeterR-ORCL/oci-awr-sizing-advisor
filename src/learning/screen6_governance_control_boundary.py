"""Inert Phase 7BK Screen 6 governance control boundary metadata.

This module exposes static boundary metadata only. It does not create
governance records, transition candidate status, transition materialization
status, transition model registry status, change runtime gate state, activate
runtime, implement UI, implement a write path, call run_analysis.py, modify
dashboards, modify CLI behavior, write databases, write files, import runtime
parser, scoring, decision, or recommendation modules, or mutate Phase 4I.
"""

from __future__ import annotations

from typing import Any


SCREEN6_GOVERNANCE_TARGET_TYPES = (
    "learning_candidate",
    "materialization_artifact",
    "parser_mapping_candidate",
    "scoring_review_candidate",
    "recommendation_rule_candidate",
    "dashboard_wording_candidate",
    "semantic_summary_candidate",
    "validation_candidate",
    "documentation_candidate",
    "governance_workflow_candidate",
    "unknown_signal",
    "knowledge_request",
    "knowledge_artifact",
    "model_registry_entry",
    "model_eligibility_record",
    "runtime_gate",
    "adaptive_runtime_context",
    "fallback_decision",
    "governance_item",
)

SCREEN6_GOVERNANCE_ACTIONS = (
    "mark_under_review",
    "approve_for_implementation",
    "reject",
    "request_revision",
    "attach_materialization_reference",
    "approve_for_validation",
    "mark_implemented",
    "mark_validated",
    "approve_for_shadow",
    "request_runtime_review",
    "review_runtime_gate",
    "close_governance_item",
    "add_governance_note",
)

SCREEN6_GOVERNANCE_STATUSES = (
    "proposed",
    "under_review",
    "approved_for_implementation",
    "approved_for_validation",
    "implemented",
    "validated",
    "needs_revision",
    "rejected",
    "closed",
    "retired",
    "superseded",
)

SCREEN6_GOVERNANCE_REQUIRED_GATES = (
    "actor identity",
    "request validation",
    "governed write path",
    "audit trail",
    "output artifact lifecycle",
    "candidate review validation",
    "materialization review validation",
    "model registry review validation",
    "runtime gate review validation",
    "runtime activation separation",
    "Phase 4I contract preservation",
    "parser/scoring/decision/recommendation runtime protection",
    "Phase 8 exclusion",
)

_SUPPORTED_BOUNDARY_MODES = ("boundary_only",)


class Screen6GovernanceControlBoundaryError(ValueError):
    """Raised when Phase 7BK boundary metadata is asked to do real work."""


def validate_screen6_governance_control_boundary(
    mode: str = "boundary_only",
) -> dict[str, Any]:
    """Validate and return static Phase 7BK boundary metadata only."""

    if mode not in _SUPPORTED_BOUNDARY_MODES:
        raise Screen6GovernanceControlBoundaryError(
            f"Unsupported Screen 6 governance control boundary mode: {mode}"
        )
    return {
        "phase": "Phase 7BK",
        "boundary": "Screen 6 Governance Control Boundary",
        "mode": mode,
        "boundary_only": True,
        "target_types": list(SCREEN6_GOVERNANCE_TARGET_TYPES),
        "actions": list(SCREEN6_GOVERNANCE_ACTIONS),
        "statuses": list(SCREEN6_GOVERNANCE_STATUSES),
        "required_gates": list(SCREEN6_GOVERNANCE_REQUIRED_GATES),
        "workflow_implemented": False,
        "screen6_governance_controls_added": False,
        "approval_controls_added": False,
        "active_reject_controls_added": False,
        "active_revision_controls_added": False,
        "active_materialization_controls_added": False,
        "active_model_registry_controls_added": False,
        "active_runtime_gate_controls_added": False,
        "dashboard_forms_added": False,
        "backend_calls_added": False,
        "cli_commands_added": False,
        "governed_write_path_invoked": False,
        "governance_records_persisted": False,
        "candidate_status_changed": False,
        "materialization_status_changed": False,
        "model_registry_status_changed": False,
        "runtime_gate_state_changed": False,
        "runtime_activation_occurred": False,
        "runtime_eligibility_approved": False,
        "candidates_created": False,
        "materialization_artifacts_created": False,
        "models_deployed": False,
        "run_analysis_wiring_added": False,
        "dashboard_truth_changed": False,
        "parser_behavior_changed": False,
        "scoring_behavior_changed": False,
        "decision_behavior_changed": False,
        "recommendation_behavior_changed": False,
        "phase4i_mutation_added": False,
        "deterministic_runtime_authoritative": True,
        "future_learning_candidate_review_phase": "7BL",
        "future_materialization_review_phase": "7BM",
        "future_model_registry_review_phase": "7BN",
        "future_runtime_gate_review_phase": "7BO",
        "future_validation_certification_phase": "7BP",
        "phase8_sizing_tco_implemented": False,
    }


def screen6_governance_control_boundary_summary() -> dict[str, Any]:
    """Return a deterministic local summary of the Phase 7BK boundary."""

    boundary = validate_screen6_governance_control_boundary(
        mode="boundary_only"
    )
    return {
        **boundary,
        "summary": (
            "Phase 7BK is boundary-only; no Screen 6 governance control "
            "workflow is implemented; no Screen 6 governance controls are "
            "added; no approval controls are added; no governance records are "
            "persisted; no candidate, materialization, model registry, or "
            "runtime gate status is changed; no runtime activation occurs; "
            "deterministic runtime remains authoritative"
        ),
    }
