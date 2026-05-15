"""Inert Phase 7AP Screen 2 diagnostic review boundary metadata.

This module exposes static boundary metadata only. It does not create review
records, implement UI, implement a write path, call run_analysis.py, modify
dashboards, modify CLI behavior, write databases, write files, import runtime
parser, scoring, decision, or recommendation modules, or mutate Phase 4I.
"""

from __future__ import annotations

from typing import Any


SCREEN2_REVIEW_TARGET_TYPES = (
    "primary_issue",
    "secondary_issue",
    "severity",
    "confidence",
    "domain_score",
    "evidence_group",
    "metric_group",
    "wait_event_group",
    "sql_signal_group",
    "diagnostic_section",
    "parser_derived_evidence",
    "trend_reference",
    "anomaly_reference",
    "missing_metric",
    "unavailable_evidence",
    "recommendation_context",
)

SCREEN2_REVIEW_DECISIONS = (
    "confirm",
    "dispute",
    "insufficient_evidence",
    "needs_parser_review",
    "needs_scoring_review",
    "needs_recommendation_review",
    "needs_learning_candidate",
    "add_reviewer_note",
)

SCREEN2_REVIEW_STATUSES = (
    "proposed",
    "under_review",
    "confirmed",
    "disputed",
    "insufficient_evidence",
    "needs_revision",
    "routed_to_governance",
    "closed",
)

SCREEN2_REVIEW_REQUIRED_GATES = (
    "actor identity",
    "request validation",
    "governed write path",
    "audit trail",
    "diagnostic truth protection",
    "Phase 4I contract preservation",
    "parser output protection",
    "scoring runtime protection",
    "recommendation truth protection",
    "missing metric/evidence review future 7AQ.1",
)

_SUPPORTED_BOUNDARY_MODES = ("boundary_only",)


class Screen2ReviewBoundaryError(ValueError):
    """Raised when Phase 7AP boundary metadata is asked to do real work."""


def validate_screen2_review_boundary(mode: str = "boundary_only") -> dict[str, Any]:
    """Validate and return static Phase 7AP boundary metadata only."""

    if mode not in _SUPPORTED_BOUNDARY_MODES:
        raise Screen2ReviewBoundaryError(
            f"Unsupported Screen 2 review boundary mode: {mode}"
        )
    return {
        "phase": "Phase 7AP",
        "boundary": "Screen 2 Review Workflow Boundary",
        "mode": mode,
        "boundary_only": True,
        "target_types": list(SCREEN2_REVIEW_TARGET_TYPES),
        "decisions": list(SCREEN2_REVIEW_DECISIONS),
        "statuses": list(SCREEN2_REVIEW_STATUSES),
        "required_gates": list(SCREEN2_REVIEW_REQUIRED_GATES),
        "review_workflow_implemented": False,
        "screen2_approval_ui_added": False,
        "review_panel_ui_added": False,
        "dashboard_write_controls_added": False,
        "review_records_created": False,
        "evidence_review_records_created": False,
        "governance_records_created": False,
        "learning_candidates_created": False,
        "backend_write_path_invoked": False,
        "backend_calls_added": False,
        "run_analysis_wiring_added": False,
        "diagnostic_truth_changed": False,
        "severity_changed": False,
        "confidence_changed": False,
        "score_changed": False,
        "evidence_changed": False,
        "parser_output_changed": False,
        "recommendation_truth_changed": False,
        "phase4i_mutation_added": False,
        "deterministic_runtime_authoritative": True,
        "missing_metric_evidence_review_future_phase": "7AQ.1",
        "phase8_sizing_tco_implemented": False,
    }


def screen2_review_boundary_summary() -> dict[str, Any]:
    """Return a deterministic local summary of the Phase 7AP boundary."""

    boundary = validate_screen2_review_boundary(mode="boundary_only")
    return {
        **boundary,
        "summary": (
            "Phase 7AP is boundary-only; no review workflow is implemented; "
            "no Screen 2 approval UI is added; no review records are created; "
            "no backend write path is invoked; deterministic diagnostic truth "
            "and deterministic runtime remain authoritative; missing "
            "metric/evidence review remains future 7AQ.1"
        ),
    }
