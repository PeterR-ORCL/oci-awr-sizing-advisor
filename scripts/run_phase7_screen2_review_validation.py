#!/usr/bin/env python3
"""Run Phase 7AP-7AT Screen 2 review workflow validation."""

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
    ("review_boundary", "tests/test_phase7ap_screen2_review_workflow_boundary.py"),
    ("diagnostic_review_model", "tests/test_phase7aq_diagnostic_review_model.py"),
    ("governance_bridge", "tests/test_phase7ar_screen2_governance_bridge.py"),
    ("review_panel", "tests/test_dashboard_screen2_review_panel.py"),
    (
        "diagnostic_exploration_regression",
        "tests/test_dashboard_screen2_diagnostic_exploration.py",
    ),
)

SCREEN2_REVIEW_MODULE_NAMES: tuple[str, ...] = (
    "screen2_review_boundary",
    "screen2_diagnostic_review",
    "screen2_governance_bridge",
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
    "src/learning/screen2_review_boundary.py",
    "src/learning/screen2_diagnostic_review.py",
    "src/learning/screen2_governance_bridge.py",
    "src/reporting/html_dashboard.py",
)

FORBIDDEN_MUTATION_FUNCTIONS: tuple[str, ...] = (
    "persist_review_record",
    "execute_governance_action",
    "create_learning_candidate",
    "mutate_diagnostic_truth",
    "update_severity",
    "update_confidence",
    "update_score",
    "update_parser_output",
    "update_recommendation",
    "mutate_phase4i",
    "auto_apply",
    "autonomous_apply",
)

FORBIDDEN_UI_SNIPPETS: tuple[str, ...] = (
    "fetch(",
    "XMLHttpRequest",
    'method="post"',
    'action="/"',
    "type=\"submit\"",
)

REQUIRED_DOCS: tuple[str, ...] = (
    "docs/architecture/phase7ap_screen2_review_workflow_boundary.md",
    "docs/architecture/phase7ap_screen2_review_lifecycle.md",
    "docs/architecture/phase7aq_diagnostic_review_model.md",
    "docs/architecture/phase7aq_evidence_availability_review.md",
    "docs/architecture/phase7ar_screen2_governance_bridge.md",
    "docs/architecture/phase7ar_governance_route_model.md",
    "docs/architecture/phase7as_screen2_review_panel.md",
    "docs/architecture/phase7as_screen2_review_request_preview.md",
    "docs/architecture/phase7_screen2_review_validation_matrix.md",
    "docs/architecture/phase7_screen2_review_readiness.md",
    "docs/architecture/phase7_screen2_review_release_certification.md",
    "docs/architecture/phase7_screen2_review_operational_checklist.md",
)

REQUIRED_DOC_PHRASES: tuple[str, ...] = (
    "review workflow is not runtime mutation",
    "review panel is preview-only",
    "no review records are persisted",
    "no candidate is created automatically",
    "no diagnostic truth changes",
    "screen2_review_ready=true only when checks pass",
    "screen 2 review workflow is certified as governed/preview-only",
    "active write execution remains future workflow",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local-only Phase 7 Screen 2 review workflow validation.",
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
        "phase": "Phase 7AP-7AT",
        "command": "run_phase7_screen2_review_validation",
        "success": success,
        "validation_groups": groups,
        "tests_run": totals["tests_run"],
        "checks_run": totals["checks_run"],
        "failures": totals["failures"],
        "errors": totals["errors"],
        "skipped": totals["skipped"],
        "screen2_review_ready": success,
        "review_panel_preview_only": success,
        "review_records_persisted": False,
        "governance_action_executed": False,
        "candidate_created": False,
        "diagnostic_truth_changed": False,
        "severity_changed": False,
        "confidence_changed": False,
        "score_changed": False,
        "parser_output_changed": False,
        "recommendation_truth_changed": False,
        "phase4i_mutated": False,
        "deterministic_runtime_remains_authoritative": True,
        "phase8_implemented": False,
    }


def run_unittest_group(name: str, test_path: str) -> dict[str, Any]:
    path = ROOT / test_path
    if not path.is_file():
        return failed_check(name, f"missing test path: {test_path}")
    module = load_module_from_path(path, f"phase7_screen2_review_validation_{name}")
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
    for path in python_files(RUNTIME_IMPORT_PATHS):
        source = read_text(path)
        imports = imported_module_names(path)
        for module_name in SCREEN2_REVIEW_MODULE_NAMES:
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
        "checks_run": max(1, len(list(python_files(RUNTIME_IMPORT_PATHS)))),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures or ["runtime paths do not import Screen 2 review modules"],
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
            "no write performed",
            "no governance action executed",
            "no candidate created",
            "no diagnostic truth mutation",
            "no score/severity/confidence mutation",
            "no parser output mutation",
            "no recommendation mutation",
            "no Phase 4I mutation",
        ],
    }


def check_documentation() -> dict[str, Any]:
    failures: list[str] = []
    for relative_path in REQUIRED_DOCS:
        path = ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing doc: {relative_path}")
    combined = "\n".join(
        read_text(ROOT / relative_path).lower()
        for relative_path in REQUIRED_DOCS
        if (ROOT / relative_path).is_file()
    )
    for phrase in REQUIRED_DOC_PHRASES:
        if phrase not in combined:
            failures.append(f"missing documentation phrase: {phrase}")
    return {
        "name": "documentation",
        "success": not failures,
        "tests_run": 0,
        "checks_run": len(REQUIRED_DOCS) + len(REQUIRED_DOC_PHRASES),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures or ["required 7AP-7AT docs exist and contain boundary language"],
    }


def load_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


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
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def failed_check(name: str, message: str) -> dict[str, Any]:
    return {
        "name": name,
        "success": False,
        "tests_run": 0,
        "checks_run": 1,
        "failures": 1,
        "errors": 0,
        "skipped": 0,
        "details": [message],
    }


def summarize_groups(groups: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "tests_run": sum(int(group.get("tests_run", 0)) for group in groups),
        "checks_run": sum(int(group.get("checks_run", 0)) for group in groups),
        "failures": sum(int(group.get("failures", 0)) for group in groups),
        "errors": sum(int(group.get("errors", 0)) for group in groups),
        "skipped": sum(int(group.get("skipped", 0)) for group in groups),
    }


def print_human_summary(summary: dict[str, Any]) -> None:
    if summary["success"]:
        print("Phase 7 Screen 2 review validation passed.")
    else:
        print("Phase 7 Screen 2 review validation failed.")
    print(f"screen2_review_ready={str(summary['screen2_review_ready']).lower()}")
    print(f"review_panel_preview_only={str(summary['review_panel_preview_only']).lower()}")
    print(f"tests_run={summary['tests_run']}")
    print(f"checks_run={summary['checks_run']}")
    print(f"failures={summary['failures']}")
    print(f"errors={summary['errors']}")
    print("review_records_persisted=false")
    print("governance_action_executed=false")
    print("candidate_created=false")
    print("diagnostic_truth_changed=false")
    print("severity_changed=false")
    print("confidence_changed=false")
    print("score_changed=false")
    print("parser_output_changed=false")
    print("recommendation_truth_changed=false")
    print("phase4i_mutated=false")
    print("Validation groups:")
    for group in summary["validation_groups"]:
        print(f"- {group['name']}: {group['success']}")


if __name__ == "__main__":
    raise SystemExit(main())
