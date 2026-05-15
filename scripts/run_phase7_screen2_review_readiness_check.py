#!/usr/bin/env python3
"""Run Phase 7AP-7AT Screen 2 review workflow readiness checks."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import io
import json
import runpy
import sys
import unittest
from pathlib import Path
from typing import Any, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VALIDATION_SCRIPT = ROOT / "scripts" / "run_phase7_screen2_review_validation.py"

FOCUSED_TESTS: tuple[tuple[str, str], ...] = (
    ("review_boundary", "tests/test_phase7ap_screen2_review_workflow_boundary.py"),
    ("diagnostic_review_model", "tests/test_phase7aq_diagnostic_review_model.py"),
    ("governance_bridge", "tests/test_phase7ar_screen2_governance_bridge.py"),
    ("review_panel", "tests/test_dashboard_screen2_review_panel.py"),
    (
        "diagnostic_exploration_regression",
        "tests/test_dashboard_screen2_diagnostic_exploration.py",
    ),
)

READINESS_DOCS: tuple[str, ...] = (
    "docs/architecture/phase7_screen2_review_validation_matrix.md",
    "docs/architecture/phase7_screen2_review_readiness.md",
    "docs/architecture/phase7_screen2_review_release_certification.md",
    "docs/architecture/phase7_screen2_review_operational_checklist.md",
)

README_LINKS: tuple[str, ...] = (
    "phase7_screen2_review_validation_matrix.md",
    "phase7_screen2_review_readiness.md",
    "phase7_screen2_review_release_certification.md",
    "phase7_screen2_review_operational_checklist.md",
)

REQUIRED_READINESS_PHRASES: tuple[str, ...] = (
    "screen2_review_ready=true only when checks pass",
    "screen 2 review is governed and preview-only at the ui layer",
    "no deterministic diagnostic truth mutation occurs",
    "screen 2 review workflow is certified as governed/preview-only",
    "active write execution remains future workflow",
    "no diagnostic truth mutation is certified",
)

FORBIDDEN_SCRIPT_IMPORTS: tuple[str, ...] = (
    "subprocess",
    "oracledb",
    "cx_Oracle",
    "sqlite3",
    "oci",
    "requests",
    "socket",
    "urllib",
    "http.client",
    "httpx",
    "boto3",
    "botocore",
    "oracle_agent_memory",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local-only Phase 7 Screen 2 review workflow readiness checks.",
    )
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON only.")
    parser.add_argument(
        "--include-phase7",
        action="store_true",
        help="Also run the broader Phase 7 validation script.",
    )
    parser.add_argument(
        "--include-phase6",
        action="store_true",
        help="Also run the broader Phase 6 validation script.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_readiness_check(
        include_phase7=args.include_phase7,
        include_phase6=args.include_phase6,
    )
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_human_summary(summary)
    return 0 if summary["success"] else 1


def run_readiness_check(
    *,
    include_phase7: bool = False,
    include_phase6: bool = False,
) -> dict[str, Any]:
    validation_summary = load_validation_module().run_validation()
    checks = [
        {
            "name": "screen2_review_validation",
            "success": bool(validation_summary.get("success")),
            "tests_run": int(validation_summary.get("tests_run", 0)),
            "checks_run": int(validation_summary.get("checks_run", 0)),
            "failures": int(validation_summary.get("failures", 0)),
            "errors": int(validation_summary.get("errors", 0)),
            "skipped": int(validation_summary.get("skipped", 0)),
            "details": ["validation script summary imported and executed"],
            "json_payload": validation_summary,
        }
    ]
    checks.extend(run_focused_test_checks())
    checks.append(check_readiness_docs())
    checks.append(check_readme_links())
    checks.append(check_readiness_script_imports())
    if include_phase7:
        checks.append(run_optional_script_check("phase7_regression", "scripts/run_phase7_validation.py"))
    if include_phase6:
        checks.append(run_optional_script_check("phase6_regression", "scripts/run_phase6_validation.py"))

    checks_by_name = {check["name"]: check for check in checks}
    validation_groups = {
        group.get("name"): bool(group.get("success"))
        for group in validation_summary.get("validation_groups", [])
        if isinstance(group, dict)
    }
    readiness_categories = {
        "review_boundary": validation_groups.get("review_boundary", False),
        "diagnostic_review_model": validation_groups.get("diagnostic_review_model", False),
        "governance_bridge": validation_groups.get("governance_bridge", False),
        "review_panel": validation_groups.get("review_panel", False),
        "diagnostic_exploration_regression": validation_groups.get(
            "diagnostic_exploration_regression",
            False,
        ),
        "runtime_isolation": (
            validation_groups.get("import_isolation", False)
            and validation_groups.get("runtime_safety", False)
        ),
        "documentation_complete": (
            validation_groups.get("documentation", False)
            and checks_by_name["screen2_review_readiness_docs"]["success"]
            and checks_by_name["screen2_review_readme_links"]["success"]
        ),
        "phase7_regression": None,
        "phase6_regression": None,
    }
    if include_phase7:
        readiness_categories["phase7_regression"] = checks_by_name[
            "phase7_regression"
        ]["success"]
    if include_phase6:
        readiness_categories["phase6_regression"] = checks_by_name[
            "phase6_regression"
        ]["success"]

    required_categories = [
        value
        for key, value in readiness_categories.items()
        if key not in {"phase7_regression", "phase6_regression"}
    ]
    if include_phase7:
        required_categories.append(bool(readiness_categories["phase7_regression"]))
    if include_phase6:
        required_categories.append(bool(readiness_categories["phase6_regression"]))

    totals = summarize_checks(checks)
    success = all(check["success"] for check in checks) and all(required_categories)
    return {
        "phase": "Phase 7AP-7AT",
        "command": "run_phase7_screen2_review_readiness_check",
        "screen2_review_ready": success,
        "success": success,
        "readiness_categories": readiness_categories,
        "review_records_persisted": False,
        "governance_action_executed": False,
        "candidate_created": False,
        "diagnostic_truth_changed": False,
        "phase4i_mutated": False,
        "deterministic_runtime_remains_authoritative": True,
        "phase8_implemented": False,
        "phase7_validation_included": include_phase7,
        "phase6_validation_included": include_phase6,
        "tests_run": totals["tests_run"],
        "checks_run": totals["checks_run"],
        "failures": totals["failures"],
        "errors": totals["errors"],
        "skipped": totals["skipped"],
        "checks": checks,
    }


def load_validation_module():
    spec = importlib.util.spec_from_file_location(
        "run_phase7_screen2_review_validation",
        VALIDATION_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Screen 2 review validation script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_focused_test_checks() -> list[dict[str, Any]]:
    return [run_unittest_check(name, test_path) for name, test_path in FOCUSED_TESTS]


def run_unittest_check(name: str, test_path: str) -> dict[str, Any]:
    path = ROOT / test_path
    if not path.is_file():
        return failed_check(name, f"missing test path: {test_path}")
    module = load_module_from_path(path, f"phase7_screen2_review_readiness_{name}")
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


def run_optional_script_check(name: str, relative_script: str) -> dict[str, Any]:
    path = ROOT / relative_script
    if not path.is_file():
        return failed_check(name, f"missing optional script: {relative_script}")
    original_argv = sys.argv[:]
    stream = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.argv = [str(path)]
        sys.stdout = stream
        sys.stderr = stream
        try:
            runpy.run_path(str(path), run_name="__main__")
            returncode = 0
        except SystemExit as exc:
            returncode = int(exc.code or 0) if isinstance(exc.code, int) else 1
    finally:
        sys.argv = original_argv
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    details = [line.strip() for line in stream.getvalue().splitlines() if line.strip()]
    return {
        "name": name,
        "success": returncode == 0,
        "tests_run": 0,
        "checks_run": 1,
        "failures": 0 if returncode == 0 else 1,
        "errors": 0,
        "skipped": 0,
        "details": details[-20:] if details else ["optional script passed"],
    }


def check_readiness_docs() -> dict[str, Any]:
    failures: list[str] = []
    for relative_path in READINESS_DOCS:
        path = ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing doc: {relative_path}")
    combined = "\n".join(
        read_text(ROOT / relative_path).lower()
        for relative_path in READINESS_DOCS
        if (ROOT / relative_path).is_file()
    )
    for phrase in REQUIRED_READINESS_PHRASES:
        if phrase not in combined:
            failures.append(f"missing readiness phrase: {phrase}")
    return {
        "name": "screen2_review_readiness_docs",
        "success": not failures,
        "tests_run": 0,
        "checks_run": len(READINESS_DOCS) + len(REQUIRED_READINESS_PHRASES),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures or ["readiness documentation complete"],
    }


def check_readme_links() -> dict[str, Any]:
    readme = ROOT / "docs" / "architecture" / "README.md"
    if not readme.is_file():
        return failed_check("screen2_review_readme_links", "missing architecture README")
    text = read_text(readme)
    missing = [link for link in README_LINKS if link not in text]
    return {
        "name": "screen2_review_readme_links",
        "success": not missing,
        "tests_run": 0,
        "checks_run": len(README_LINKS),
        "failures": len(missing),
        "errors": 0,
        "skipped": 0,
        "details": missing or ["README links Screen 2 review readiness docs"],
    }


def check_readiness_script_imports() -> dict[str, Any]:
    imports = imported_module_names(ROOT / "scripts" / "run_phase7_screen2_review_readiness_check.py")
    failures = [
        imported
        for imported in imports
        for forbidden in FORBIDDEN_SCRIPT_IMPORTS
        if imported == forbidden or imported.startswith(f"{forbidden}.")
    ]
    return {
        "name": "screen2_review_readiness_script_imports",
        "success": not failures,
        "tests_run": 0,
        "checks_run": len(imports),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures or ["readiness script has no unsafe imports"],
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


def imported_module_names(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


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


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "tests_run": sum(int(check.get("tests_run", 0)) for check in checks),
        "checks_run": sum(int(check.get("checks_run", 0)) for check in checks),
        "failures": sum(int(check.get("failures", 0)) for check in checks),
        "errors": sum(int(check.get("errors", 0)) for check in checks),
        "skipped": sum(int(check.get("skipped", 0)) for check in checks),
    }


def print_human_summary(summary: dict[str, Any]) -> None:
    if summary["success"]:
        print("Phase 7 Screen 2 review readiness passed.")
    else:
        print("Phase 7 Screen 2 review readiness failed.")
    print(f"screen2_review_ready={str(summary['screen2_review_ready']).lower()}")
    print(f"tests_run={summary['tests_run']}")
    print(f"checks_run={summary['checks_run']}")
    print(f"failures={summary['failures']}")
    print(f"errors={summary['errors']}")
    print("review_records_persisted=false")
    print("governance_action_executed=false")
    print("candidate_created=false")
    print("diagnostic_truth_changed=false")
    print("phase4i_mutated=false")
    print("Readiness categories:")
    for name, passed in summary["readiness_categories"].items():
        print(f"- {name}: {passed}")


if __name__ == "__main__":
    raise SystemExit(main())
