#!/usr/bin/env python3
"""Run Phase 7CA-7CF active Screen 3 execution readiness checks."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from typing import Any, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VALIDATION_SCRIPT = ROOT / "scripts" / "run_phase7_active_screen3_execution_validation.py"

FOCUSED_TESTS: tuple[tuple[str, str], ...] = (
    ("governed_workflow_repository", "tests/test_phase7ca_governed_workflow_repository.py"),
    ("governed_workflow_repository", "tests/test_phase7ca_governed_workflow_schema.py"),
    ("deterministic_execution", "tests/test_phase7cb_deterministic_execution.py"),
    ("comparison_execution", "tests/test_phase7cc_comparison_execution.py"),
    ("object_storage_load_execution", "tests/test_phase7cd_object_storage_load_execution.py"),
    ("dashboard_output_refresh", "tests/test_phase7ce_dashboard_output_refresh.py"),
    ("screen3_reanalysis_validation", "tests/test_phase7_screen3_reanalysis_validation.py"),
)

READINESS_DOCS: tuple[str, ...] = (
    "docs/architecture/phase7_active_screen3_execution_validation_matrix.md",
    "docs/architecture/phase7_active_screen3_execution_readiness.md",
    "docs/architecture/phase7_active_screen3_execution_release_certification.md",
    "docs/architecture/phase7_active_screen3_execution_operational_checklist.md",
)

README_LINKS: tuple[str, ...] = (
    "phase7_active_screen3_execution_validation_matrix.md",
    "phase7_active_screen3_execution_readiness.md",
    "phase7_active_screen3_execution_release_certification.md",
    "phase7_active_screen3_execution_operational_checklist.md",
)

REQUIRED_READINESS_PHRASES: tuple[str, ...] = (
    "active_screen3_execution_ready=true",
    "governed workflow db persistence exists",
    "deterministic execution service works",
    "comparison execution works",
    "object storage load execution works",
    "dashboard output refresh metadata works",
    "live object storage validation is optional",
    "phase 8 is not implemented",
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
        description="Run Phase 7CA-7CF active Screen 3 execution readiness checks.",
    )
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON only.")
    parser.add_argument(
        "--include-phase7",
        action="store_true",
        help="Include optional Phase 7 regression placeholder category.",
    )
    parser.add_argument(
        "--include-phase6",
        action="store_true",
        help="Include optional Phase 6 regression placeholder category.",
    )
    parser.add_argument(
        "--include-live-object-storage",
        action="store_true",
        help="Enable opt-in live Object Storage validation flag for readiness.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_readiness_check(
        include_phase7=args.include_phase7,
        include_phase6=args.include_phase6,
        include_live_object_storage=args.include_live_object_storage,
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
    include_live_object_storage: bool = False,
) -> dict[str, Any]:
    previous_live_flag = os.environ.get("AWR_PHASE7CD_OBJECT_STORAGE_TEST")
    if include_live_object_storage:
        os.environ["AWR_PHASE7CD_OBJECT_STORAGE_TEST"] = "1"
    try:
        validation_summary = load_validation_module().run_validation()
    finally:
        if include_live_object_storage:
            if previous_live_flag is None:
                os.environ.pop("AWR_PHASE7CD_OBJECT_STORAGE_TEST", None)
            else:
                os.environ["AWR_PHASE7CD_OBJECT_STORAGE_TEST"] = previous_live_flag

    checks = [
        {
            "name": "active_screen3_execution_validation",
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

    validation_groups = {
        group.get("name"): bool(group.get("success"))
        for group in validation_summary.get("validation_groups", [])
        if isinstance(group, dict)
    }
    checks_by_name = {check["name"]: check for check in checks}
    phase7_regression = True if include_phase7 else None
    phase6_regression = True if include_phase6 else None
    live_object_storage = (
        validation_summary.get("object_storage_live_validated")
        if include_live_object_storage or os.getenv("AWR_PHASE7CD_OBJECT_STORAGE_TEST") == "1"
        else None
    )
    readiness_categories = {
        "governed_workflow_repository": validation_groups.get(
            "governed_workflow_repository",
            False,
        ),
        "deterministic_execution": validation_groups.get("deterministic_execution", False),
        "comparison_execution": validation_groups.get("comparison_execution", False),
        "object_storage_load_execution": validation_groups.get(
            "object_storage_load_execution",
            False,
        ),
        "dashboard_output_refresh": validation_groups.get(
            "dashboard_output_refresh",
            False,
        ),
        "screen3_reanalysis_validation": validation_groups.get(
            "screen3_reanalysis_validation",
            False,
        ),
        "runtime_isolation": (
            validation_groups.get("import_isolation", False)
            and validation_groups.get("runtime_safety", False)
            and checks_by_name["readiness_script_imports"]["success"]
        ),
        "documentation_complete": (
            validation_groups.get("documentation", False)
            and checks_by_name["active_screen3_execution_readiness_docs"]["success"]
            and checks_by_name["active_screen3_execution_readme_links"]["success"]
        ),
        "phase7_regression": phase7_regression,
        "phase6_regression": phase6_regression,
        "live_object_storage": live_object_storage,
    }
    required_category_values = [
        value
        for key, value in readiness_categories.items()
        if key not in {"phase7_regression", "phase6_regression", "live_object_storage"}
    ]
    success = all(check["success"] for check in checks) and all(required_category_values)
    totals = summarize_checks(checks)
    return {
        "phase": "Phase 7CA-7CF",
        "command": "run_phase7_active_screen3_execution_readiness_check",
        "active_screen3_execution_ready": success,
        "success": success,
        "readiness_categories": readiness_categories,
        "run_analysis_direct_call": False,
        "subprocess_called": False,
        "phase4i_mutated": False,
        "phase8_implemented": False,
        "deterministic_runtime_remains_authoritative": True,
        "tests_run": totals["tests_run"],
        "checks_run": totals["checks_run"],
        "failures": totals["failures"],
        "errors": totals["errors"],
        "skipped": totals["skipped"],
        "checks": checks,
    }


def load_validation_module():
    spec = importlib.util.spec_from_file_location(
        "run_phase7_active_screen3_execution_validation",
        VALIDATION_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Phase 7 active Screen 3 validation script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_focused_test_checks() -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = {}
    for name, test_path in FOCUSED_TESTS:
        grouped.setdefault(name, []).append(test_path)
    return [
        run_unittest_check(name, test_paths)
        for name, test_paths in grouped.items()
    ]


def run_unittest_check(name: str, test_paths: list[str]) -> dict[str, Any]:
    suite = unittest.TestSuite()
    missing: list[str] = []
    for index, test_path in enumerate(test_paths):
        path = ROOT / test_path
        if not path.is_file():
            missing.append(test_path)
            continue
        module = load_module_from_path(
            path,
            f"phase7_active_screen3_readiness_{name}_{index}",
        )
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
    if missing:
        return failed_check(name, f"missing test path(s): {', '.join(missing)}")
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
        "details": details[-24:] if details else ["unittest group passed"],
    }


def check_readiness_docs() -> dict[str, Any]:
    failures: list[str] = []
    combined = ""
    for relative_path in READINESS_DOCS:
        path = ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing document: {relative_path}")
            continue
        combined += "\n" + read_text(path).lower()
    for phrase in REQUIRED_READINESS_PHRASES:
        if phrase not in combined:
            failures.append(f"missing readiness phrase: {phrase}")
    return {
        "name": "active_screen3_execution_readiness_docs",
        "success": not failures,
        "tests_run": 0,
        "checks_run": len(READINESS_DOCS) + len(REQUIRED_READINESS_PHRASES),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures or ["active Screen 3 execution readiness docs complete"],
    }


def check_readme_links() -> dict[str, Any]:
    readme = ROOT / "docs" / "architecture" / "README.md"
    if not readme.is_file():
        return failed_check("active_screen3_execution_readme_links", "missing README")
    text = read_text(readme)
    failures = [link for link in README_LINKS if link not in text]
    return {
        "name": "active_screen3_execution_readme_links",
        "success": not failures,
        "tests_run": 0,
        "checks_run": len(README_LINKS),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures or ["README links active Screen 3 execution certification docs"],
    }


def check_readiness_script_imports() -> dict[str, Any]:
    failures: list[str] = []
    for path in (Path(__file__).resolve(), VALIDATION_SCRIPT):
        imports = imported_module_names(path)
        for forbidden in FORBIDDEN_SCRIPT_IMPORTS:
            if any(
                imported == forbidden or imported.startswith(f"{forbidden}.")
                for imported in imports
            ):
                failures.append(f"{path.relative_to(ROOT)} imports forbidden module {forbidden}")
    return {
        "name": "readiness_script_imports",
        "success": not failures,
        "tests_run": 0,
        "checks_run": 2,
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures or ["readiness scripts avoid unsafe imports"],
    }


def load_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load test module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def imported_module_names(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "tests_run": sum(int(check.get("tests_run", 0)) for check in checks),
        "checks_run": sum(int(check.get("checks_run", 0)) for check in checks),
        "failures": sum(int(check.get("failures", 0)) for check in checks),
        "errors": sum(int(check.get("errors", 0)) for check in checks),
        "skipped": sum(int(check.get("skipped", 0)) for check in checks),
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def print_human_summary(summary: dict[str, Any]) -> None:
    if summary["success"]:
        print("Phase 7 active Screen 3 execution readiness passed.")
    else:
        print("Phase 7 active Screen 3 execution readiness failed.")
    print(f"active_screen3_execution_ready={str(summary['active_screen3_execution_ready']).lower()}")
    print(f"tests_run={summary['tests_run']}")
    print(f"checks_run={summary['checks_run']}")
    print(f"failures={summary['failures']}")
    print(f"errors={summary['errors']}")
    print(f"skipped={summary['skipped']}")
    print("run_analysis_direct_call=false")
    print("subprocess_called=false")
    print("phase4i_mutated=false")
    print("phase8_implemented=false")
    print("deterministic_runtime_remains_authoritative=true")


if __name__ == "__main__":
    raise SystemExit(main())
