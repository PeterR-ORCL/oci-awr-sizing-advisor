#!/usr/bin/env python3
"""Run Phase 7AZ-7BD Screen 4 workflow validation."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from typing import Any, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEST_GROUPS: tuple[tuple[str, str], ...] = (
    ("workflow_boundary", "tests/test_phase7az_screen4_historical_review_boundary.py"),
    ("baseline_selection", "tests/test_phase7ba_historical_baseline_selection.py"),
    ("trend_anomaly_review", "tests/test_phase7bb_trend_anomaly_review_model.py"),
    ("historical_learning_bridge", "tests/test_phase7bc_historical_learning_bridge.py"),
    ("historical_review_panel", "tests/test_dashboard_screen4_historical_review_panel.py"),
    (
        "historical_execution_metadata",
        "tests/test_phase7bc3_historical_review_execution.py",
    ),
    (
        "historical_review_exploration_regression",
        "tests/test_dashboard_screen4_historical_review_exploration.py",
    ),
)

SCREEN4_WORKFLOW_MODULE_NAMES: tuple[str, ...] = (
    "screen4_historical_review_boundary",
    "screen4_baseline_selection",
    "screen4_trend_anomaly_review",
    "screen4_historical_learning_bridge",
    "screen4_historical_review_execution",
)

RUNTIME_IMPORT_PATHS: tuple[str, ...] = (
    "scripts/run_analysis.py",
    "src/parser",
    "src/parsing",
    "src/scoring",
    "src/decision",
    "src/recommendation",
    "src/recommendations",
    "src/analysis/decision_engine.py",
    "src/analysis/recommendation_engine.py",
    "src/analysis/scoring_adapter.py",
)

RUNTIME_SAFETY_SOURCE_PATHS: tuple[str, ...] = (
    "src/learning/screen4_historical_review_boundary.py",
    "src/learning/screen4_baseline_selection.py",
    "src/learning/screen4_trend_anomaly_review.py",
    "src/learning/screen4_historical_learning_bridge.py",
    "src/learning/screen4_historical_review_execution.py",
    "src/reporting/html_dashboard.py",
)

FORBIDDEN_MUTATION_FUNCTIONS: tuple[str, ...] = (
    "persist_baseline",
    "persist_trend_review",
    "persist_anomaly_review",
    "create_learning_candidate",
    "create_dataset_label",
    "update_historical_truth",
    "update_trend",
    "update_anomaly",
    "update_score",
    "update_recommendation",
    "mutate_phase4i",
    "auto_apply",
    "autonomous_apply",
)

FORBIDDEN_UI_SNIPPETS: tuple[str, ...] = (
    "fetch(",
    "XMLHttpRequest",
    'method="post"',
    'type="submit"',
    "data-action=",
)

REQUIRED_DOCS: tuple[str, ...] = (
    "docs/architecture/phase7az_screen4_historical_review_workflow_boundary.md",
    "docs/architecture/phase7az_historical_review_lifecycle.md",
    "docs/architecture/phase7ba_historical_baseline_selection.md",
    "docs/architecture/phase7ba_baseline_selection_model.md",
    "docs/architecture/phase7bb_trend_anomaly_review_model.md",
    "docs/architecture/phase7bb_trend_anomaly_review_lifecycle.md",
    "docs/architecture/phase7bc_historical_learning_bridge.md",
    "docs/architecture/phase7bc_historical_learning_intent_model.md",
    "docs/architecture/phase7bc_screen4_historical_review_panel.md",
    "docs/architecture/phase7bc3_historical_review_execution.md",
    "docs/architecture/phase7bc3_historical_review_execution_model.md",
    "docs/architecture/phase7_screen4_workflow_validation_matrix.md",
    "docs/architecture/phase7_screen4_workflow_readiness.md",
    "docs/architecture/phase7_screen4_workflow_release_certification.md",
    "docs/architecture/phase7_screen4_workflow_operational_checklist.md",
)

REQUIRED_DOC_PHRASES: tuple[str, ...] = (
    "screen 4 workflow is governed",
    "baseline selection is metadata only",
    "trend/anomaly review is local model only",
    "panel is preview-only",
    "governed execution is metadata-only",
    "no persistence occurs",
    "no historical/trend/anomaly/scoring truth changes occur",
    "no phase 4i mutation occurs",
    "no candidate is created automatically",
    "screen4_workflow_ready=true only when checks pass",
    "screen 4 workflow is certified as governed/preview-only/metadata-only",
    "active write execution remains future workflow",
    "no historical truth mutation is certified",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local-only Phase 7 Screen 4 workflow validation.",
    )
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON only.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_validation()
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_human_summary(summary)
    return 0 if summary["success"] else 1


def run_validation() -> dict[str, Any]:
    groups = [run_unittest_group(name, test_path) for name, test_path in TEST_GROUPS]
    groups.append(check_import_isolation())
    groups.append(check_runtime_safety())
    groups.append(check_documentation())

    totals = summarize_groups(groups)
    success = all(group["success"] for group in groups)
    return {
        "phase": "Phase 7AZ-7BD",
        "command": "run_phase7_screen4_workflow_validation",
        "success": success,
        "validation_groups": groups,
        "tests_run": totals["tests_run"],
        "checks_run": totals["checks_run"],
        "failures": totals["failures"],
        "errors": totals["errors"],
        "skipped": totals["skipped"],
        "screen4_workflow_ready": success,
        "baseline_official": False,
        "baseline_records_persisted": False,
        "trend_review_records_persisted": False,
        "anomaly_review_records_persisted": False,
        "candidate_created": False,
        "dataset_label_created": False,
        "governance_actions_performed": False,
        "historical_truth_changed": False,
        "trend_truth_changed": False,
        "anomaly_truth_changed": False,
        "scoring_changed": False,
        "recommendation_truth_changed": False,
        "parser_output_changed": False,
        "phase4i_mutated": False,
        "deterministic_runtime_remains_authoritative": True,
        "phase8_implemented": False,
    }


def run_unittest_group(name: str, test_path: str) -> dict[str, Any]:
    path = ROOT / test_path
    if not path.is_file():
        return failed_check(name, f"missing test path: {test_path}")
    module = load_module_from_path(path, f"phase7_screen4_workflow_validation_{name}")
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    details = [line.strip() for line in stream.getvalue().splitlines() if line.strip()]
    return {
        "name": name,
        "success": result.wasSuccessful(),
        "tests_run": result.testsRun,
        "checks_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "details": details[-20:] if details else ["unittest check passed"],
    }


def check_import_isolation() -> dict[str, Any]:
    failures: list[str] = []
    checked_paths = list(python_files(RUNTIME_IMPORT_PATHS))
    for path in checked_paths:
        source = read_text(path)
        imports = imported_module_names(path)
        for module_name in SCREEN4_WORKFLOW_MODULE_NAMES:
            forbidden_names = (
                module_name,
                f"learning.{module_name}",
                f"src.learning.{module_name}",
            )
            if any(name in imports for name in forbidden_names) or module_name in source:
                failures.append(f"{path.relative_to(ROOT)} imports or references {module_name}")
    return {
        "name": "import_isolation",
        "success": not failures,
        "tests_run": 0,
        "checks_run": max(1, len(checked_paths)),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures or ["runtime paths do not import Screen 4 workflow modules"],
    }


def check_runtime_safety() -> dict[str, Any]:
    failures: list[str] = []
    for relative_path in RUNTIME_SAFETY_SOURCE_PATHS:
        path = ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing safety source: {relative_path}")
            continue
        functions = function_names(path)
        for forbidden in FORBIDDEN_MUTATION_FUNCTIONS:
            if forbidden in functions:
                failures.append(f"{relative_path} defines forbidden function {forbidden}")
        if relative_path == "src/reporting/html_dashboard.py":
            source = read_text(path)
            for snippet in FORBIDDEN_UI_SNIPPETS:
                if snippet in source:
                    failures.append(f"{relative_path} contains unsafe UI snippet {snippet}")
    return {
        "name": "runtime_safety",
        "success": not failures,
        "tests_run": 0,
        "checks_run": len(RUNTIME_SAFETY_SOURCE_PATHS),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures
        or [
            "baseline_official=false",
            "baseline_records_persisted=false",
            "trend_review_records_persisted=false",
            "anomaly_review_records_persisted=false",
            "candidate_created=false",
            "dataset_label_created=false",
            "historical_truth_changed=false",
            "trend_truth_changed=false",
            "anomaly_truth_changed=false",
            "scoring_changed=false",
            "recommendation_truth_changed=false",
            "parser_output_changed=false",
            "phase4i_mutated=false",
        ],
    }


def check_documentation() -> dict[str, Any]:
    failures: list[str] = []
    combined_text_parts: list[str] = []
    for relative_path in REQUIRED_DOCS:
        path = ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing doc: {relative_path}")
            continue
        combined_text_parts.append(read_text(path).lower())
    combined_text = "\n".join(combined_text_parts)
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in combined_text:
            failures.append(f"missing documentation phrase: {phrase}")
    return {
        "name": "documentation",
        "success": not failures,
        "tests_run": 0,
        "checks_run": len(REQUIRED_DOCS) + len(REQUIRED_DOC_PHRASES),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures or ["Screen 4 workflow documentation complete"],
    }


def summarize_groups(groups: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "tests_run": sum(int(group.get("tests_run", 0)) for group in groups),
        "checks_run": sum(int(group.get("checks_run", 0)) for group in groups),
        "failures": sum(int(group.get("failures", 0)) for group in groups),
        "errors": sum(int(group.get("errors", 0)) for group in groups),
        "skipped": sum(int(group.get("skipped", 0)) for group in groups),
    }


def failed_check(name: str, detail: str) -> dict[str, Any]:
    return {
        "name": name,
        "success": False,
        "tests_run": 0,
        "checks_run": 1,
        "failures": 1,
        "errors": 0,
        "skipped": 0,
        "details": [detail],
    }


def load_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def python_files(paths: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for relative_path in paths:
        path = ROOT / relative_path
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(child for child in path.rglob("*.py") if child.is_file()))
    return files


def imported_module_names(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def function_names(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def print_human_summary(summary: dict[str, Any]) -> None:
    if summary["success"]:
        print("Phase 7 Screen 4 workflow validation passed.")
    else:
        print("Phase 7 Screen 4 workflow validation failed.")
    print(f"screen4_workflow_ready={str(summary['screen4_workflow_ready']).lower()}")
    print(f"tests_run={summary['tests_run']}")
    print(f"checks_run={summary['checks_run']}")
    print(f"failures={summary['failures']}")
    print(f"errors={summary['errors']}")


if __name__ == "__main__":
    raise SystemExit(main())
