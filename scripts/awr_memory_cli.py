#!/usr/bin/env python3
"""Unified Phase 6 memory, governance, recall, and semantic-assist CLI."""

from __future__ import annotations

import argparse
from copy import deepcopy
import importlib
import io
import json
from pathlib import Path
import sys
import unittest
from typing import Any, Callable, Mapping, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.memory import memory_orchestrator
from src.memory.oracle_agent_memory_adapter import load_config_from_env
from src.memory import governance_semantic_assist, semantic_recall_service
from src.learning import (
    learning_candidate_engine,
    learning_candidate_model,
    learning_governance_bridge,
    outcome_pattern_miner,
    semantic_candidate_context,
)
from src.reporting.ai_display_metadata import build_ml_explainability_visibility_metadata


MEMORY_RECORD_KEYS = (
    "runs",
    "recommendations",
    "actions",
    "outcomes",
    "feedback",
    "unknown_signals",
    "knowledge_requests",
    "knowledge_artifacts",
)

LEARNING_REVIEW_ACTIONS = (
    "under-review",
    "reject",
    "needs-revision",
    "approve-for-implementation",
    "attach-materialization",
    "implemented",
    "validated",
    "close",
)

LEARNING_VALIDATE_MODULES = (
    "tests.test_outcome_pattern_miner",
    "tests.test_learning_candidate_model",
    "tests.test_learning_candidate_engine",
    "tests.test_semantic_candidate_context",
    "tests.test_learning_governance_bridge",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified Phase 6 operational CLI for memory, governance, recall, and semantic assist.",
    )
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON.")
    parser.add_argument("--format", choices=("json",), default="json")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _add_recall_commands(subparsers)
    _add_review_commands(subparsers)
    _add_governance_commands(subparsers)
    _add_artifact_commands(subparsers)
    _add_semantic_commands(subparsers)
    _add_learning_commands(subparsers)
    subparsers.add_parser("status", help="Show overall Phase 6 operational status.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = dispatch(args)
    if _should_print_json(args, result):
        _print_json(_public_result(result), compact=bool(args.compact))
    else:
        _print_text(result)
    if not result.get("enabled", True):
        return 0
    return 0 if result.get("success", False) else 1


def dispatch(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "status":
        return _status_result()
    if args.command == "recall":
        return _dispatch_recall(args)
    if args.command == "review":
        return _dispatch_review(args)
    if args.command == "governance":
        return _dispatch_governance(args)
    if args.command == "artifact":
        return _dispatch_artifact(args)
    if args.command == "semantic":
        return _dispatch_semantic(args)
    if args.command == "learning":
        return _dispatch_learning(args)
    return _error("unknown command")


def _add_recall_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    recall = subparsers.add_parser("recall", help="Read-only structured memory recall.")
    recall_sub = recall.add_subparsers(dest="recall_command", required=True)
    for name in (
        "summary",
        "runs",
        "recommendations",
        "actions",
        "outcomes",
        "feedback",
        "unknown-signals",
        "knowledge-requests",
        "knowledge-artifacts",
    ):
        command = recall_sub.add_parser(name)
        _add_common_recall_filters(command)


def _add_review_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    review = subparsers.add_parser("review", help="Explicit parser review operations.")
    review_sub = review.add_subparsers(dest="review_command", required=True)
    unknown = review_sub.add_parser("unknown-signal")
    unknown.add_argument("--unknown-signal-id", required=True, type=int)
    unknown.add_argument("--review-status", required=True)
    unknown.add_argument("--review-classification")
    unknown.add_argument("--review-notes")
    unknown.add_argument("--actor", required=True)
    unknown.add_argument("--metadata", type=_json_object)


def _add_governance_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    governance = subparsers.add_parser("governance", help="Explicit governance operations.")
    governance_sub = governance.add_subparsers(dest="governance_command", required=True)

    create = governance_sub.add_parser("create-request")
    create.add_argument("--source-type", required=True)
    create.add_argument("--source-id", required=True, type=int)
    create.add_argument("--classification")
    create.add_argument("--summary", required=True)
    create.add_argument("--details")
    create.add_argument("--run-history-id", type=int)
    create.add_argument("--actor", required=True)
    create.add_argument("--metadata", type=_json_object)

    approve = governance_sub.add_parser("approve-request")
    approve.add_argument("--request-id", required=True, type=int)
    approve.add_argument("--approval-status", required=True)
    approve.add_argument("--actor", required=True)
    approve.add_argument("--notes")


def _add_artifact_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    artifact = subparsers.add_parser("artifact", help="Knowledge artifact operations.")
    artifact_sub = artifact.add_subparsers(dest="artifact_command", required=True)

    materialize = artifact_sub.add_parser("materialize")
    materialize.add_argument("--request-id", required=True, type=int)
    materialize.add_argument("--artifact-type", required=True)
    materialize.add_argument("--classification")
    materialize.add_argument("--summary")
    materialize.add_argument("--details")
    materialize.add_argument("--actor", required=True)
    materialize.add_argument("--metadata", type=_json_object)

    list_cmd = artifact_sub.add_parser("list")
    list_cmd.add_argument("--status")
    list_cmd.add_argument("--type")
    list_cmd.add_argument("--classification")
    list_cmd.add_argument("--run-history-id", type=int)
    list_cmd.add_argument("--limit", type=int, default=10)
    list_cmd.add_argument("--order", choices=("newest", "oldest"), default="newest")


def _add_semantic_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    semantic = subparsers.add_parser("semantic", help="Read-only semantic recall and reviewer assist.")
    semantic_sub = semantic.add_subparsers(dest="semantic_command", required=True)

    semantic_sub.add_parser("status")

    recall = semantic_sub.add_parser("recall")
    recall.add_argument("--query", required=True)
    recall.add_argument("--limit", type=int, default=5)

    unknown = semantic_sub.add_parser("assist-unknown-signal")
    unknown.add_argument("--unknown-signal-id", required=True, type=int)
    unknown.add_argument("--limit", type=int, default=5)

    knowledge = semantic_sub.add_parser("assist-knowledge-request")
    knowledge.add_argument("--request-id", type=int)
    knowledge.add_argument("--source-type")
    knowledge.add_argument("--source-id", type=int)
    knowledge.add_argument("--classification")
    knowledge.add_argument("--summary")
    knowledge.add_argument("--db-name")
    knowledge.add_argument("--posture")
    knowledge.add_argument("--limit", type=int, default=5)

    artifact = semantic_sub.add_parser("assist-artifact")
    artifact.add_argument("--artifact-id", type=int)
    artifact.add_argument("--artifact-type")
    artifact.add_argument("--classification")
    artifact.add_argument("--summary")
    artifact.add_argument("--db-name")
    artifact.add_argument("--limit", type=int, default=5)

    parser_review = semantic_sub.add_parser("assist-parser-governance")
    parser_review.add_argument("--parser-stage")
    parser_review.add_argument("--classification-hint")
    parser_review.add_argument("--section-context")
    parser_review.add_argument("--db-name")
    parser_review.add_argument("--detection-reason")
    parser_review.add_argument("--limit", type=int, default=5)


def _add_learning_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    learning = subparsers.add_parser(
        "learning",
        help="Safe local Phase 7 learning visibility and review commands.",
    )
    learning_sub = learning.add_subparsers(dest="learning_command", required=True)

    status = learning_sub.add_parser("status", help="Show Phase 7 learning subsystem status.")
    status.add_argument("--json", action="store_true", help="Emit JSON output.")

    ml_status = learning_sub.add_parser(
        "ml-status",
        help="Show read-only Phase 7 ML/adaptive subsystem status.",
    )
    ml_status.add_argument("--json", action="store_true", help="Emit JSON output.")

    ml_explain = learning_sub.add_parser(
        "ml-explain",
        help="Render local ML explanation records from JSON input.",
    )
    ml_explain.add_argument("--input", help="Optional local JSON explanation input file.")
    ml_explain.add_argument("--json", action="store_true", help="Emit JSON output.")

    ml_models = learning_sub.add_parser(
        "ml-models",
        help="Render local model registry entries from JSON input.",
    )
    ml_models.add_argument("--input", help="Optional local JSON model registry input file.")
    ml_models.add_argument("--json", action="store_true", help="Emit JSON output.")

    adaptive_runtime_status = learning_sub.add_parser(
        "adaptive-runtime-status",
        help="Show read-only adaptive runtime gate/context/adapter/fallback status.",
    )
    adaptive_runtime_status.add_argument(
        "--input",
        help="Optional local JSON adaptive runtime status input file.",
    )
    adaptive_runtime_status.add_argument("--json", action="store_true", help="Emit JSON output.")

    patterns = learning_sub.add_parser("patterns", help="Mine local outcome patterns.")
    patterns.add_argument("--input", help="Optional local JSON memory input file.")
    patterns.add_argument("--json", action="store_true", help="Emit JSON output.")

    candidates = learning_sub.add_parser(
        "candidates",
        help="Generate proposal-only candidates from local patterns or memory records.",
    )
    candidates.add_argument("--input", help="Optional local JSON input file.")
    candidates.add_argument(
        "--from-memory",
        action="store_true",
        help="Mine local memory records before generating candidates.",
    )
    candidates.add_argument("--json", action="store_true", help="Emit JSON output.")

    detail = learning_sub.add_parser("candidate-detail", help="Show one local candidate record.")
    detail.add_argument("--input", required=True, help="Local JSON candidate input file.")
    detail.add_argument("--candidate-id", required=True)
    detail.add_argument("--json", action="store_true", help="Emit JSON output.")

    semantic = learning_sub.add_parser(
        "semantic-context",
        help="Attach local reviewer-assist semantic context to one candidate.",
    )
    semantic.add_argument("--candidate-input", required=True, help="Local JSON candidate file.")
    semantic.add_argument("--semantic-input", required=True, help="Local JSON semantic records file.")
    semantic.add_argument("--candidate-id")
    semantic.add_argument("--output", help="Optional local JSON output file.")
    semantic.add_argument("--force", action="store_true", help="Overwrite --output if it exists.")
    semantic.add_argument("--json", action="store_true", help="Emit JSON output.")

    review = learning_sub.add_parser("review", help="Apply local governed review transitions.")
    review.add_argument("--input", required=True, help="Local JSON candidate input file.")
    review.add_argument("--candidate-id")
    review.add_argument("--action", required=True, choices=LEARNING_REVIEW_ACTIONS)
    review.add_argument("--actor", required=True)
    review.add_argument("--review-notes")
    review.add_argument("--materialization-reference")
    review.add_argument("--json", action="store_true", help="Emit JSON output.")

    export = learning_sub.add_parser("export", help="Normalize local learning records to JSON.")
    export.add_argument("--input", required=True, help="Local JSON input file.")
    export.add_argument("--kind", choices=("patterns", "candidates"))
    export.add_argument("--output", help="Optional local JSON output file.")
    export.add_argument("--force", action="store_true", help="Overwrite --output if it exists.")
    export.add_argument("--json", action="store_true", help="Accepted for consistency; export emits JSON.")

    validate = learning_sub.add_parser("validate", help="Run local Phase 7 learning validations.")
    validate.add_argument("--json", action="store_true", help="Emit JSON output.")


def _add_common_recall_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-history-id", type=int)
    parser.add_argument("--action-history-id", type=int)
    parser.add_argument("--db-name")
    parser.add_argument("--dbid")
    parser.add_argument("--source-file-name")
    parser.add_argument("--section-name")
    parser.add_argument("--status")
    parser.add_argument("--type")
    parser.add_argument("--classification")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--order", choices=("newest", "oldest"), default="newest")


def _dispatch_recall(args: argparse.Namespace) -> dict[str, Any]:
    command = args.recall_command
    if command == "summary":
        return memory_orchestrator.recall_memory_summary(order=args.order)
    recall_map: dict[str, tuple[Callable[..., dict[str, Any]], dict[str, Any]]] = {
        "runs": (
            memory_orchestrator.recall_run_history,
            {
                "db_name": args.db_name,
                "dbid": args.dbid,
                "source_file_name": args.source_file_name,
                "limit": args.limit,
                "order": args.order,
            },
        ),
        "recommendations": (
            memory_orchestrator.recall_recommendation_history,
            {
                "run_history_id": args.run_history_id,
                "db_name": args.db_name,
                "recommendation_status": args.status,
                "limit": args.limit,
                "order": args.order,
            },
        ),
        "actions": (
            memory_orchestrator.recall_action_history,
            {
                "run_history_id": args.run_history_id,
                "action_status": args.status,
                "action_type": args.type,
                "limit": args.limit,
                "order": args.order,
            },
        ),
        "outcomes": (
            memory_orchestrator.recall_outcome_history,
            {
                "run_history_id": args.run_history_id,
                "action_history_id": args.action_history_id,
                "outcome_status": args.status,
                "limit": args.limit,
                "order": args.order,
            },
        ),
        "feedback": (
            memory_orchestrator.recall_feedback_history,
            {
                "run_history_id": args.run_history_id,
                "feedback_type": args.type,
                "feedback_rating": args.status,
                "limit": args.limit,
                "order": args.order,
            },
        ),
        "unknown-signals": (
            memory_orchestrator.recall_unknown_signals,
            {
                "review_status": args.status,
                "review_classification": args.classification,
                "db_name": args.db_name,
                "section_name": args.section_name,
                "limit": args.limit,
                "order": args.order,
            },
        ),
        "knowledge-requests": (
            memory_orchestrator.recall_knowledge_requests,
            {
                "approval_status": args.status,
                "source_type": args.type,
                "run_history_id": args.run_history_id,
                "limit": args.limit,
                "order": args.order,
            },
        ),
        "knowledge-artifacts": (
            memory_orchestrator.recall_knowledge_artifacts,
            {
                "activation_status": args.status,
                "artifact_type": args.type,
                "artifact_classification": args.classification,
                "run_history_id": args.run_history_id,
                "limit": args.limit,
                "order": args.order,
            },
        ),
    }
    callback, kwargs = recall_map[command]
    return callback(**kwargs)


def _dispatch_review(args: argparse.Namespace) -> dict[str, Any]:
    if args.review_command != "unknown-signal":
        return _error("unknown review command")
    return memory_orchestrator.review_unknown_signal(
        unknown_signal_id=args.unknown_signal_id,
        review_status=args.review_status,
        review_classification=args.review_classification,
        review_notes=args.review_notes,
        reviewed_by=args.actor,
        metadata=args.metadata,
    )


def _dispatch_governance(args: argparse.Namespace) -> dict[str, Any]:
    if args.governance_command == "create-request":
        return memory_orchestrator.create_knowledge_update_request(
            source_type=args.source_type,
            source_id=args.source_id,
            candidate_classification=args.classification,
            candidate_summary=args.summary,
            candidate_details=args.details,
            run_history_id=args.run_history_id,
            created_by=args.actor,
            metadata=args.metadata,
        )
    if args.governance_command == "approve-request":
        return memory_orchestrator.approve_knowledge_update_request(
            request_id=args.request_id,
            approval_status=args.approval_status,
            approved_by=args.actor,
            approval_notes=args.notes,
        )
    return _error("unknown governance command")


def _dispatch_artifact(args: argparse.Namespace) -> dict[str, Any]:
    if args.artifact_command == "materialize":
        return memory_orchestrator.materialize_knowledge_artifact(
            request_id=args.request_id,
            artifact_type=args.artifact_type,
            artifact_classification=args.classification,
            artifact_summary=args.summary,
            artifact_details=args.details,
            created_by=args.actor,
            metadata=args.metadata,
        )
    if args.artifact_command == "list":
        return memory_orchestrator.recall_knowledge_artifacts(
            activation_status=args.status,
            artifact_type=args.type,
            artifact_classification=args.classification,
            run_history_id=args.run_history_id,
            limit=args.limit,
            order=args.order,
        )
    return _error("unknown artifact command")


def _dispatch_semantic(args: argparse.Namespace) -> dict[str, Any]:
    if args.semantic_command == "status":
        return _semantic_status_result()
    if args.semantic_command == "recall":
        return semantic_recall_service.recall_related_context(args.query, limit=args.limit)
    if args.semantic_command == "assist-unknown-signal":
        unknown_signal = _recall_unknown_signal_by_id(args.unknown_signal_id)
        if not unknown_signal.get("success"):
            return unknown_signal
        return governance_semantic_assist.assist_unknown_signal_review(
            unknown_signal["record"],
            limit=args.limit,
        )
    if args.semantic_command == "assist-knowledge-request":
        return governance_semantic_assist.assist_knowledge_request_review(
            {
                "REQUEST_ID": args.request_id,
                "SOURCE_TYPE": args.source_type,
                "SOURCE_ID": args.source_id,
                "CANDIDATE_CLASSIFICATION": args.classification,
                "CANDIDATE_SUMMARY": args.summary,
                "DB_NAME": args.db_name,
                "POSTURE": args.posture,
            },
            limit=args.limit,
        )
    if args.semantic_command == "assist-artifact":
        return governance_semantic_assist.assist_artifact_review(
            {
                "ARTIFACT_ID": args.artifact_id,
                "ARTIFACT_TYPE": args.artifact_type,
                "ARTIFACT_CLASSIFICATION": args.classification,
                "ARTIFACT_SUMMARY": args.summary,
                "DB_NAME": args.db_name,
            },
            limit=args.limit,
        )
    if args.semantic_command == "assist-parser-governance":
        return governance_semantic_assist.assist_parser_governance_review(
            {
                "PARSER_STAGE": args.parser_stage,
                "CLASSIFICATION_HINT": args.classification_hint,
                "SECTION_NAME": args.section_context,
                "DB_NAME": args.db_name,
                "DETECTION_REASON": args.detection_reason,
            },
            limit=args.limit,
        )
    return _error("unknown semantic command")


def _dispatch_learning(args: argparse.Namespace) -> dict[str, Any]:
    try:
        if args.learning_command == "status":
            return _learning_status_result()
        if args.learning_command == "ml-status":
            return _learning_ml_status_result()
        if args.learning_command == "ml-explain":
            return _learning_ml_explain_result(args)
        if args.learning_command == "ml-models":
            return _learning_ml_models_result(args)
        if args.learning_command == "adaptive-runtime-status":
            return _learning_adaptive_runtime_status_result(args)
        if args.learning_command == "patterns":
            return _learning_patterns_result(args)
        if args.learning_command == "candidates":
            return _learning_candidates_result(args)
        if args.learning_command == "candidate-detail":
            return _learning_candidate_detail_result(args)
        if args.learning_command == "semantic-context":
            return _learning_semantic_context_result(args)
        if args.learning_command == "review":
            return _learning_review_result(args)
        if args.learning_command == "export":
            return _learning_export_result(args)
        if args.learning_command == "validate":
            return _learning_validate_result()
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return _learning_error(str(exc))
    return _learning_error("unknown learning command")


def _learning_status_result() -> dict[str, Any]:
    result = _learning_success(
        command="learning status",
        learning_modules_available=True,
        outcome_pattern_miner_available=hasattr(outcome_pattern_miner, "mine_outcome_patterns"),
        candidate_model_available=hasattr(learning_candidate_model, "LearningCandidate"),
        candidate_engine_available=hasattr(
            learning_candidate_engine,
            "generate_learning_candidates",
        ),
        semantic_candidate_context_available=hasattr(
            semantic_candidate_context,
            "attach_semantic_context",
        ),
        governance_bridge_available=hasattr(
            learning_governance_bridge,
            "apply_governance_action",
        ),
        read_only=True,
        no_runtime_activation=True,
        deterministic_runtime_remains_authoritative=True,
        oracle_agent_memory_dependency=False,
        semantic_recall_service_dependency=False,
        network_dependency=False,
    )
    return _with_human(
        result,
        "\n".join(
            (
                "Phase 7 learning status",
                "learning modules available: true",
                "outcome pattern miner available: true",
                "candidate model available: true",
                "candidate engine available: true",
                "semantic candidate context available: true",
                "governance bridge available: true",
                "runtime_influence=false",
                "deterministic runtime remains authoritative",
                "no runtime activation",
                "read-only operational visibility",
            )
        ),
    )


def _learning_ml_status_result() -> dict[str, Any]:
    module_names = {
        "ml_boundary_present": "src.learning.ml_boundary",
        "dataset_model_present": "src.learning.feature_label_dataset",
        "trend_aware_scoring_present": "src.learning.trend_aware_scoring",
        "shadow_ml_interface_present": "src.learning.shadow_ml_model_interface",
        "training_backtesting_present": "src.learning.ml_training_backtesting",
        "explainability_present": "src.learning.ml_explainability",
        "model_registry_present": "src.learning.ml_model_registry",
        "runtime_integration_gate_present": "src.learning.adaptive_runtime_gate",
        "runtime_context_present": "src.learning.adaptive_runtime_context",
        "scoring_adapter_present": "src.learning.adaptive_scoring_adapter",
        "recommendation_adapter_present": "src.learning.adaptive_recommendation_adapter",
        "parser_adapter_present": "src.learning.adaptive_parser_adapter",
        "fallback_layer_present": "src.learning.adaptive_runtime_fallback",
    }
    status = {field: _local_module_available(module) for field, module in module_names.items()}
    result = _learning_success(
        command="learning ml-status",
        read_only=True,
        advisory_only=True,
        deterministic_runtime_remains_authoritative=True,
        runtime_active=False,
        runtime_influence=False,
        runtime_influence_granted=False,
        runtime_eligibility_granted=False,
        no_runtime_activation=True,
        no_backend_writes=True,
        network_dependency=False,
        oracle_agent_memory_dependency=False,
        database_dependency=False,
        **status,
    )
    lines = [
        "Phase 7 ML/adaptive status",
        "read-only",
        "deterministic runtime remains authoritative",
        "no runtime activation",
        "runtime_active=false",
        "runtime_influence=false",
        "runtime_influence_granted=false",
        "runtime_eligibility_granted=false",
    ]
    lines.extend(f"{field}: {str(value).lower()}" for field, value in status.items())
    return _with_human(result, "\n".join(lines))


def _learning_ml_explain_result(args: argparse.Namespace) -> dict[str, Any]:
    data = _load_optional_json(args.input)
    explanations = _ml_explanation_records_from_data(data)
    visibility = build_ml_explainability_visibility_metadata(explanations=explanations)
    result = _learning_success(
        command="learning ml-explain",
        read_only=True,
        advisory_only=True,
        explanations=visibility["explanation_rows"],
        feature_contributions=visibility["feature_contribution_rows"],
        count=len(visibility["explanation_rows"]),
        visibility=visibility,
        deterministic_runtime_remains_authoritative=True,
        no_runtime_activation=True,
        no_backend_writes=True,
        network_dependency=False,
        oracle_agent_memory_dependency=False,
        database_dependency=False,
    )
    lines = [
        "Phase 7 ML explanations",
        "read-only",
        f"explanations: {len(visibility['explanation_rows'])}",
        f"feature contributions: {len(visibility['feature_contribution_rows'])}",
        "ML explanations are not diagnostic evidence",
        "ML explanations are not recommendation truth",
        "deterministic runtime remains authoritative",
        "no runtime activation",
    ]
    return _with_human(result, "\n".join(lines))


def _learning_ml_models_result(args: argparse.Namespace) -> dict[str, Any]:
    data = _load_optional_json(args.input)
    models = _ml_model_records_from_data(data)
    visibility = build_ml_explainability_visibility_metadata(model_registry_entries=models)
    result = _learning_success(
        command="learning ml-models",
        read_only=True,
        advisory_only=True,
        models=visibility["model_registry_rows"],
        count=len(visibility["model_registry_rows"]),
        visibility=visibility,
        deterministic_runtime_remains_authoritative=True,
        runtime_active=False,
        runtime_eligibility_granted=False,
        runtime_influence_granted=False,
        no_runtime_activation=True,
        no_backend_writes=True,
        network_dependency=False,
        oracle_agent_memory_dependency=False,
        database_dependency=False,
    )
    lines = [
        "Phase 7 ML model registry visibility",
        "read-only",
        f"models: {len(visibility['model_registry_rows'])}",
        "model registry visibility does not deploy models",
        "runtime_active=false",
        "runtime_eligibility_granted=false",
        "runtime_influence_granted=false",
        "deterministic runtime remains authoritative",
        "no runtime activation",
    ]
    for model in visibility["model_registry_rows"][:5]:
        lines.append(
            "- "
            f"{model.get('model_id')}: {model.get('model_family')} "
            f"governance_status={model.get('governance_status')} "
            f"runtime_active={str(model.get('runtime_active')).lower()}"
        )
    return _with_human(result, "\n".join(lines))


def _learning_adaptive_runtime_status_result(args: argparse.Namespace) -> dict[str, Any]:
    data = _load_optional_json(args.input)
    status = _adaptive_runtime_status_from_data(data)
    visibility = build_ml_explainability_visibility_metadata(
        adaptive_runtime_context=status.get("runtime_context"),
        gate_results=status.get("gate_results"),
        scoring_integration_results=status.get("scoring_results"),
        recommendation_integration_results=status.get("recommendation_results"),
        parser_integration_results=status.get("parser_results"),
        fallback_decisions=status.get("fallback_decisions"),
        readiness_summary=status.get("readiness_summary"),
    )
    fallback_rows = visibility["fallback_rows"]
    gate_rows = visibility["runtime_gate_rows"]
    result = _learning_success(
        command="learning adaptive-runtime-status",
        read_only=True,
        advisory_only=True,
        runtime_context=visibility["runtime_context"],
        gate_results=gate_rows,
        scoring_results=visibility["adapter_rows"],
        fallback_decisions=fallback_rows,
        visibility=visibility,
        deterministic_runtime_remains_authoritative=True,
        runtime_active=False,
        runtime_influence=False,
        runtime_influence_granted=False,
        runtime_eligibility_granted=False,
        fallback_to_deterministic=True,
        no_runtime_activation=True,
        no_backend_writes=True,
        network_dependency=False,
        oracle_agent_memory_dependency=False,
        database_dependency=False,
    )
    posture = (
        fallback_rows[0].get("final_runtime_posture")
        if fallback_rows
        else "deterministic_fallback"
    )
    lines = [
        "Phase 7 adaptive runtime status",
        "read-only",
        f"runtime gate rows: {len(gate_rows)}",
        f"fallback posture: {posture}",
        "runtime gate visibility does not activate runtime",
        "fallback visibility does not execute rollback",
        "runtime_active=false",
        "runtime_influence=false",
        "runtime_influence_granted=false",
        "deterministic runtime remains authoritative",
        "no runtime activation",
    ]
    return _with_human(result, "\n".join(lines))


def _learning_patterns_result(args: argparse.Namespace) -> dict[str, Any]:
    memory_records = _load_memory_records(args.input)
    patterns = outcome_pattern_miner.mine_outcome_patterns(memory_records)
    result = _learning_success(
        command="learning patterns",
        read_only=True,
        patterns=patterns,
        count=len(patterns),
        no_candidates_generated=True,
        no_runtime_activation=True,
        deterministic_runtime_remains_authoritative=True,
    )
    lines = [
        "Phase 7 learning patterns",
        "read-only local pattern mining",
        f"patterns: {len(patterns)}",
        "runtime_influence=false",
        "requires_human_review=true",
        "no candidates generated by this command",
        "no runtime activation",
        "deterministic runtime remains authoritative",
    ]
    lines.extend(f"- {pattern.get('pattern_id')}: {pattern.get('title')}" for pattern in patterns)
    return _with_human(result, "\n".join(lines))


def _learning_candidates_result(args: argparse.Namespace) -> dict[str, Any]:
    if args.from_memory:
        memory_records = _load_memory_records(args.input)
        candidates = learning_candidate_engine.generate_learning_candidates_from_memory(
            memory_records
        )
        source_mode = "memory"
    else:
        patterns = _load_pattern_records(args.input)
        candidates = learning_candidate_engine.generate_learning_candidates(patterns)
        source_mode = "patterns"

    result = _learning_success(
        command="learning candidates",
        source_mode=source_mode,
        proposal_only=True,
        candidates=candidates,
        count=len(candidates),
        no_approval=True,
        no_runtime_activation=True,
        deterministic_runtime_remains_authoritative=True,
    )
    lines = [
        "Phase 7 learning candidates",
        f"source mode: {source_mode}",
        f"proposal-only candidates: {len(candidates)}",
        "status=PROPOSED",
        "runtime_influence=false",
        "requires_human_review=true",
        "no approval",
        "no runtime activation",
        "deterministic runtime remains authoritative",
    ]
    lines.extend(
        f"- {candidate.get('candidate_id')}: {candidate.get('title')}"
        for candidate in candidates
    )
    return _with_human(result, "\n".join(lines))


def _learning_candidate_detail_result(args: argparse.Namespace) -> dict[str, Any]:
    candidate = _select_candidate(_load_candidate_records(args.input), args.candidate_id)
    result = _learning_success(
        command="learning candidate-detail",
        read_only=True,
        candidate_id=candidate["candidate_id"],
        candidate=candidate,
        no_runtime_activation=True,
        deterministic_runtime_remains_authoritative=True,
    )
    return _with_human(
        result,
        "\n".join(
            (
                "Phase 7 learning candidate detail",
                f"candidate_id: {candidate['candidate_id']}",
                f"candidate_type: {candidate['candidate_type']}",
                f"status: {candidate['status']}",
                f"title: {candidate['title']}",
                "read-only",
                "proposal-only",
                "runtime_influence=false",
                "requires_human_review=true",
                "no runtime activation",
            )
        ),
    )


def _learning_semantic_context_result(args: argparse.Namespace) -> dict[str, Any]:
    original = _select_candidate(_load_candidate_records(args.candidate_input), args.candidate_id)
    candidate = learning_candidate_model.from_dict(original)
    semantic_records = _load_semantic_records(args.semantic_input)
    attached = semantic_candidate_context.attach_semantic_context(candidate, semantic_records)
    attached_data = learning_candidate_model.to_dict(attached)
    semantic_context_attached = attached_data.get("semantic_context") is not None
    result = _learning_success(
        command="learning semantic-context",
        candidate_id=attached_data["candidate_id"],
        candidate=attached_data,
        semantic_context_attached=semantic_context_attached,
        semantic_context_is_reviewer_assist_only=True,
        semantic_context_is_non_authoritative=True,
        semantic_context_is_not_source_evidence=True,
        confidence_unchanged=attached_data["confidence"] == original["confidence"],
        status_unchanged=attached_data["status"] == original["status"],
        no_runtime_activation=True,
        deterministic_runtime_remains_authoritative=True,
    )
    if args.output:
        write_result = _write_json_file(args.output, _public_result(result), force=args.force)
        result["output_path"] = write_result
    lines = [
        "Phase 7 learning semantic context",
        f"candidate_id: {attached_data['candidate_id']}",
        f"semantic_context attached: {str(semantic_context_attached).lower()}",
        "semantic context is reviewer-assist only",
        "semantic context is non-authoritative",
        "semantic context is not source_evidence",
        "confidence unchanged",
        "status unchanged",
        "runtime_influence=false",
        "requires_human_review=true",
        "no runtime activation",
    ]
    return _with_human(result, "\n".join(lines))


def _learning_review_result(args: argparse.Namespace) -> dict[str, Any]:
    candidate_data = _select_candidate(_load_candidate_records(args.input), args.candidate_id)
    candidate = learning_candidate_model.from_dict(candidate_data)
    updated, decision = learning_governance_bridge.apply_governance_action(
        candidate,
        args.action,
        args.actor,
        review_notes=args.review_notes,
        materialization_reference=args.materialization_reference,
    )
    updated_data = learning_candidate_model.to_dict(updated)
    decision_data = learning_governance_bridge.governance_decision_to_dict(decision)
    approval_boundary = (
        "approved for implementation only, not runtime activation"
        if args.action == "approve-for-implementation"
        else None
    )
    result = _learning_success(
        command="learning review",
        action=args.action,
        actor=args.actor,
        candidate_id=updated_data["candidate_id"],
        candidate=updated_data,
        governance_decision=decision_data,
        approved_for_implementation_only=bool(
            decision_data.get("approved_for_implementation_only")
        ),
        approval_boundary=approval_boundary,
        local_review_only=True,
        no_runtime_activation=True,
        deterministic_runtime_remains_authoritative=True,
    )
    lines = [
        "Phase 7 learning review",
        f"candidate_id: {updated_data['candidate_id']}",
        f"action: {args.action}",
        f"status: {updated_data['status']}",
        f"actor: {args.actor}",
        "local governed review transition only",
        "runtime_influence=false",
        "requires_human_review=true",
        "no runtime activation",
    ]
    if approval_boundary:
        lines.append(approval_boundary)
    return _with_human(result, "\n".join(lines))


def _learning_export_result(args: argparse.Namespace) -> dict[str, Any]:
    raw_data = _load_json(args.input)
    kind = args.kind or _infer_learning_record_kind(raw_data)
    if kind == "candidates":
        candidates = _candidate_records_from_data(raw_data)
        result = _learning_success(
            command="learning export",
            kind="candidates",
            candidates=candidates,
            count=len(candidates),
            local_file_output_only=bool(args.output),
            no_runtime_activation=True,
            deterministic_runtime_remains_authoritative=True,
        )
    elif kind == "patterns":
        patterns = _pattern_records_from_data(raw_data)
        result = _learning_success(
            command="learning export",
            kind="patterns",
            patterns=patterns,
            count=len(patterns),
            local_file_output_only=bool(args.output),
            no_runtime_activation=True,
            deterministic_runtime_remains_authoritative=True,
        )
    else:
        result = _learning_success(
            command="learning export",
            kind="raw",
            record=raw_data,
            local_file_output_only=bool(args.output),
            no_runtime_activation=True,
            deterministic_runtime_remains_authoritative=True,
        )

    if args.output:
        result["output_path"] = _write_json_file(args.output, _public_result(result), force=args.force)
    result["_force_json_output"] = True
    return result


def _learning_validate_result() -> dict[str, Any]:
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    modules_run: list[str] = []
    missing_modules: list[str] = []

    for module_name in LEARNING_VALIDATE_MODULES:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            if exc.name == module_name:
                missing_modules.append(module_name)
                continue
            raise
        modules_run.append(module_name)
        suite.addTests(loader.loadTestsFromModule(module))

    stream = io.StringIO()
    validation = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    success = validation.wasSuccessful()
    result = {
        "enabled": True,
        "success": success,
        "command": "learning validate",
        "modules_run": modules_run,
        "missing_modules": missing_modules,
        "tests_run": validation.testsRun,
        "failures": len(validation.failures),
        "errors": len(validation.errors),
        "failure_summaries": _validation_summaries(validation.failures),
        "error_summaries": _validation_summaries(validation.errors),
        "local_validation_only": True,
        "runtime_influence": False,
        "requires_human_review": True,
        "no_runtime_activation": True,
        "deterministic_runtime_remains_authoritative": True,
        "network_dependency": False,
        "oracle_agent_memory_dependency": False,
    }
    lines = [
        "Phase 7 learning validation",
        f"success: {str(success).lower()}",
        f"modules run: {len(modules_run)}",
        f"tests run: {validation.testsRun}",
        f"failures: {len(validation.failures)}",
        f"errors: {len(validation.errors)}",
        "local validation only",
        "runtime_influence=false",
        "no runtime activation",
        "deterministic runtime remains authoritative",
    ]
    return _with_human(result, "\n".join(lines))


def _learning_success(command: str, **fields: Any) -> dict[str, Any]:
    result = {
        "enabled": True,
        "success": True,
        "command": command,
        "runtime_influence": False,
        "requires_human_review": True,
        "proposal_only": bool(fields.pop("proposal_only", False)),
        "no_runtime_activation": True,
        "safety_labels": [
            "runtime_influence=false",
            "requires_human_review=true",
            "no runtime activation",
            "deterministic runtime remains authoritative",
        ],
    }
    result.update(fields)
    return result


def _learning_error(message: str) -> dict[str, Any]:
    return _with_human(
        {
            "enabled": True,
            "success": False,
            "error": message,
            "errors": [message],
            "runtime_influence": False,
            "requires_human_review": True,
            "no_runtime_activation": True,
        },
        f"Phase 7 learning command failed: {message}",
    )


def _with_human(result: dict[str, Any], text: str) -> dict[str, Any]:
    result["_human"] = text
    return result


def _load_memory_records(input_path: str | None) -> dict[str, list[Any]]:
    if input_path is None:
        return {key: [] for key in MEMORY_RECORD_KEYS}
    return _memory_records_from_data(_load_json(input_path))


def _memory_records_from_data(data: Any) -> dict[str, list[Any]]:
    if not isinstance(data, Mapping):
        raise ValueError("memory input must be a JSON object.")
    source = data.get("memory_records") or data.get("memory") or data
    if not isinstance(source, Mapping):
        raise ValueError("memory_records must be a JSON object.")

    records: dict[str, list[Any]] = {}
    for key in MEMORY_RECORD_KEYS:
        value = source.get(key, [])
        if value is None:
            value = []
        if not isinstance(value, list):
            raise ValueError(f"memory field {key!r} must be a list.")
        records[key] = deepcopy(value)
    return records


def _load_pattern_records(input_path: str | None) -> list[dict[str, Any]]:
    if input_path is None:
        return []
    return _pattern_records_from_data(_load_json(input_path))


def _pattern_records_from_data(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, Mapping) and "patterns" in data:
        records = data["patterns"]
    elif isinstance(data, Mapping) and "pattern_id" in data:
        records = [data]
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError("pattern input must be a list, a {patterns: [...]} object, or one pattern object.")

    if not isinstance(records, list):
        raise ValueError("patterns must be a list.")
    normalized: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("each pattern record must be a JSON object.")
        normalized.append(deepcopy(dict(record)))
    return normalized


def _load_candidate_records(input_path: str) -> list[dict[str, Any]]:
    return _candidate_records_from_data(_load_json(input_path))


def _candidate_records_from_data(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, Mapping) and "candidates" in data:
        records = data["candidates"]
    elif isinstance(data, Mapping) and "candidate" in data:
        records = [data["candidate"]]
    elif isinstance(data, Mapping) and "candidate_id" in data:
        records = [data]
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError(
            "candidate input must be a list, a {candidates: [...]} object, or one candidate object."
        )

    if not isinstance(records, list):
        raise ValueError("candidates must be a list.")
    normalized: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("each candidate record must be a JSON object.")
        candidate = learning_candidate_model.from_dict(record)
        normalized.append(learning_candidate_model.to_dict(candidate))
    return normalized


def _select_candidate(
    candidates: Sequence[dict[str, Any]],
    candidate_id: str | None,
) -> dict[str, Any]:
    if candidate_id is None:
        if len(candidates) == 1:
            return deepcopy(candidates[0])
        raise ValueError("candidate-id is required when candidate input contains multiple candidates.")

    for candidate in candidates:
        if candidate.get("candidate_id") == candidate_id:
            return deepcopy(candidate)
    raise ValueError(f"candidate_id {candidate_id!r} was not found.")


def _load_semantic_records(input_path: str) -> list[dict[str, Any]]:
    data = _load_json(input_path)
    if isinstance(data, Mapping) and "semantic_records" in data:
        records = data["semantic_records"]
    elif isinstance(data, Mapping):
        records = [data]
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError("semantic input must be a list or a {semantic_records: [...]} object.")

    if not isinstance(records, list):
        raise ValueError("semantic_records must be a list.")
    normalized: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("each semantic record must be a JSON object.")
        normalized.append(deepcopy(dict(record)))
    return normalized


def _load_json(input_path: str) -> Any:
    path = Path(input_path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _load_optional_json(input_path: str | None) -> Any:
    if input_path is None:
        return {}
    return _load_json(input_path)


def _ml_explanation_records_from_data(data: Any) -> list[dict[str, Any]]:
    return _records_from_flexible_json(
        data,
        container_keys=("explanations", "ml_explanations"),
        object_keys=("explanation_id", "summary", "feature_contributions"),
        field_name="explanations",
    )


def _ml_model_records_from_data(data: Any) -> list[dict[str, Any]]:
    return _records_from_flexible_json(
        data,
        container_keys=("models", "model_registry_entries", "entries"),
        object_keys=("model_id", "model_family", "governance_status"),
        field_name="models",
    )


def _adaptive_runtime_status_from_data(data: Any) -> dict[str, Any]:
    if data is None or data == {}:
        return {
            "runtime_context": {},
            "gate_results": [],
            "scoring_results": [],
            "recommendation_results": [],
            "parser_results": [],
            "fallback_decisions": [],
            "readiness_summary": {},
        }
    if not isinstance(data, Mapping):
        raise ValueError("adaptive runtime status input must be a JSON object.")

    return {
        "runtime_context": deepcopy(
            data.get("runtime_context")
            or data.get("adaptive_runtime_context")
            or {}
        ),
        "gate_results": _records_from_flexible_json(
            data.get("gate_results") or data.get("runtime_gate_results") or [],
            container_keys=("gate_results", "runtime_gate_results"),
            object_keys=("gate_id", "component_type"),
            field_name="gate_results",
        ),
        "scoring_results": _records_from_flexible_json(
            data.get("scoring_result")
            or data.get("scoring_results")
            or data.get("scoring_integration_results")
            or [],
            container_keys=("scoring_results", "scoring_integration_results"),
            object_keys=("result_id", "selected_score_source", "deterministic_score"),
            field_name="scoring_results",
        ),
        "recommendation_results": _records_from_flexible_json(
            data.get("recommendation_result")
            or data.get("recommendation_results")
            or data.get("recommendation_integration_results")
            or [],
            container_keys=("recommendation_results", "recommendation_integration_results"),
            object_keys=("result_id", "selected_recommendation_source"),
            field_name="recommendation_results",
        ),
        "parser_results": _records_from_flexible_json(
            data.get("parser_result")
            or data.get("parser_results")
            or data.get("parser_integration_results")
            or [],
            container_keys=("parser_results", "parser_integration_results"),
            object_keys=("result_id", "selected_parser_source", "selected_parser_action"),
            field_name="parser_results",
        ),
        "fallback_decisions": _records_from_flexible_json(
            data.get("fallback_decision")
            or data.get("fallback_decisions")
            or [],
            container_keys=("fallback_decisions",),
            object_keys=("decision_id", "final_runtime_posture"),
            field_name="fallback_decisions",
        ),
        "readiness_summary": deepcopy(
            data.get("readiness_summary")
            or data.get("runtime_integration_readiness")
            or {}
        ),
    }


def _records_from_flexible_json(
    data: Any,
    *,
    container_keys: tuple[str, ...],
    object_keys: tuple[str, ...],
    field_name: str,
) -> list[dict[str, Any]]:
    if data is None or data == {}:
        return []
    if isinstance(data, Mapping):
        for key in container_keys:
            if key in data:
                return _records_from_flexible_json(
                    data[key],
                    container_keys=container_keys,
                    object_keys=object_keys,
                    field_name=field_name,
                )
        if any(key in data for key in object_keys):
            return [deepcopy(dict(data))]
        return []
    if isinstance(data, list):
        records: list[dict[str, Any]] = []
        for record in data:
            if not isinstance(record, Mapping):
                raise ValueError(f"each {field_name} record must be a JSON object.")
            records.append(deepcopy(dict(record)))
        return records
    raise ValueError(
        f"{field_name} input must be a list, a container object, or one record object."
    )


def _local_module_available(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return False
        raise
    return True


def _write_json_file(output_path: str, data: Mapping[str, Any], *, force: bool) -> str:
    path = Path(output_path)
    if path.exists() and not force:
        raise FileExistsError(f"output file already exists: {output_path}; pass --force to overwrite.")
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def _infer_learning_record_kind(data: Any) -> str:
    if isinstance(data, Mapping):
        if "candidates" in data or "candidate" in data or "candidate_id" in data:
            return "candidates"
        if "patterns" in data or "pattern_id" in data:
            return "patterns"
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, Mapping) and "candidate_id" in first:
            return "candidates"
        if isinstance(first, Mapping) and "pattern_id" in first:
            return "patterns"
    return "raw"


def _validation_summaries(entries: Sequence[tuple[unittest.case.TestCase, str]]) -> list[str]:
    summaries: list[str] = []
    for test, details in entries:
        first_line = details.strip().splitlines()[-1:] or [""]
        summaries.append(f"{test.id()}: {first_line[0]}")
    return summaries


def _recall_unknown_signal_by_id(unknown_signal_id: int) -> dict[str, Any]:
    result = memory_orchestrator.recall_unknown_signals(limit=500, order="newest")
    if not result.get("enabled", True):
        return result
    if not result.get("success"):
        return result
    for record in result.get("records", []):
        if _record_int(record, "UNKNOWN_SIGNAL_ID", "unknown_signal_id") == int(unknown_signal_id):
            return {
                "enabled": True,
                "success": True,
                "record": record,
                "authoritative": False,
                "runtime_influence": False,
                "semantic_only": True,
                "reviewer_assist_only": True,
            }
    return {
        "enabled": True,
        "success": False,
        "error": f"unknown_signal_id {unknown_signal_id} was not found",
        "records": [],
        "errors": [f"unknown_signal_id {unknown_signal_id} was not found"],
    }


def _status_result() -> dict[str, Any]:
    summary = memory_orchestrator.recall_memory_summary()
    semantic_status = _semantic_status_result()
    return {
        "enabled": summary.get("enabled", True),
        "success": bool(summary.get("success", False) and semantic_status.get("success", False)),
        "memory_enabled": bool(summary.get("enabled", True)),
        "structured_recall_available": bool(summary.get("success", False)),
        "semantic_recall_enabled": bool(semantic_status.get("semantic_recall_enabled")),
        "governance_apis_available": True,
        "artifact_apis_available": True,
        "runtime_influence": False,
        "semantic_authoritative": False,
        "summary": summary.get("summary"),
        "semantic": semantic_status,
        "errors": list(summary.get("errors", [])) + list(semantic_status.get("errors", [])),
    }


def _semantic_status_result() -> dict[str, Any]:
    config = load_config_from_env()
    missing = []
    if config.enabled:
        adapter = __import__(
            "src.memory.oracle_agent_memory_adapter",
            fromlist=["OracleAgentMemoryPrototypeAdapter"],
        ).OracleAgentMemoryPrototypeAdapter(config)
        missing = adapter.validate_config()
    return {
        "enabled": True,
        "success": True,
        "semantic_recall_enabled": bool(config.enabled),
        "provider": "Oracle Agent Memory",
        "mode": "curated semantic recall",
        "authoritative": False,
        "runtime_influence": False,
        "semantic_only": True,
        "reviewer_assist_only": True,
        "missing_configuration": missing,
        "skipped": [] if config.enabled else ["oracle_agent_memory_disabled"],
    }


def _record_int(record: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        if key in record:
            try:
                return int(record[key])
            except (TypeError, ValueError):
                return None
    return None


def _json_object(raw_value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("must be a JSON object")
    return parsed


def _should_print_json(args: argparse.Namespace, result: Mapping[str, Any]) -> bool:
    if args.command != "learning":
        return True
    if result.get("_force_json_output"):
        return True
    return bool(getattr(args, "json", False))


def _public_result(result: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if not key.startswith("_")}


def _print_text(result: Mapping[str, Any]) -> None:
    text = result.get("_human")
    if text is None:
        text = result.get("error") or json.dumps(_public_result(result), indent=2, sort_keys=True)
    print(text)


def _print_json(result: dict[str, Any], *, compact: bool) -> None:
    if compact:
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))


def _error(message: str) -> dict[str, Any]:
    return {
        "enabled": True,
        "success": False,
        "error": message,
        "errors": [message],
    }


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
