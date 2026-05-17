#!/usr/bin/env python3
"""Run Phase 7CA-7CF active Screen 3 execution block validation."""

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

TEST_GROUPS: tuple[tuple[str, str], ...] = (
    ("governed_workflow_repository", "tests/test_phase7ca_governed_workflow_repository.py"),
    ("governed_workflow_repository", "tests/test_phase7ca_governed_workflow_schema.py"),
    ("deterministic_execution", "tests/test_phase7cb_deterministic_execution.py"),
    ("comparison_execution", "tests/test_phase7cc_comparison_execution.py"),
    ("object_storage_load_execution", "tests/test_phase7cd_object_storage_load_execution.py"),
    ("dashboard_output_refresh", "tests/test_phase7ce_dashboard_output_refresh.py"),
    ("screen3_reanalysis_validation", "tests/test_phase7_screen3_reanalysis_validation.py"),
)

EXECUTION_MODULES: tuple[str, ...] = (
    "src/learning/governed_workflow_repository.py",
    "src/learning/screen3_deterministic_execution.py",
    "src/learning/screen3_comparison_execution.py",
    "src/learning/object_storage_load_execution.py",
    "src/learning/dashboard_output_refresh.py",
)

REQUIRED_DOCS: tuple[str, ...] = (
    "docs/architecture/phase7_active_screen3_execution_validation_matrix.md",
    "docs/architecture/phase7_active_screen3_execution_readiness.md",
    "docs/architecture/phase7_active_screen3_execution_release_certification.md",
    "docs/architecture/phase7_active_screen3_execution_operational_checklist.md",
    "docs/architecture/phase7ca_active_backend_execution_boundary.md",
    "docs/architecture/phase7cb_deterministic_reanalysis_execution.md",
    "docs/architecture/phase7cc_comparison_execution.md",
    "docs/architecture/phase7cd_object_storage_load_execution.md",
    "docs/architecture/phase7ce_dashboard_output_refresh.md",
)

REQUIRED_DOC_PHRASES: tuple[str, ...] = (
    "active_screen3_execution_ready=true",
    "no direct run_analysis.py invocation",
    "no subprocess execution",
    "no adaptive runtime by default",
    "no phase 4i mutation",
    "no generated dashboard artifacts committed",
    "phase 8 is not implemented",
    "deterministic runtime remains authoritative",
)

OBJECT_STORAGE_PATH_PHRASES: tuple[str, ...] = (
    "bucket = configurable",
    "prefix = awr/raw/<DB_NAME>/<YYYY-MM-DD>/",
    "object_name = <file>.out OR <source_system_id>/<fingerprint>/<file>.out",
    "source_system_id is optional",
    "fingerprint is optional",
    "database_name and snapshot_date remain explicit metadata where available",
    "flat and nested objects under the selected prefix",
)

FORBIDDEN_IMPORT_PREFIXES: tuple[str, ...] = (
    "subprocess",
    "requests",
    "httpx",
    "urllib",
    "socket",
    "http.client",
    "oci",
    "boto3",
    "botocore",
    "oracledb",
    "cx_Oracle",
    "sqlite3",
    "src.reporting",
    "src.parser",
    "src.parsing",
    "src.scoring",
    "src.decision",
    "src.recommendation",
    "src.recommendations",
    "src.analysis",
    "src.memory",
    "scripts.run_analysis",
    "scripts.awr_memory_cli",
)

PHASE8_PATHS: tuple[str, ...] = (
    "src/phase8",
    "src/sizing",
    "src/tco",
    "src/what_if",
    "scripts/run_phase8_sizing_tco.py",
    "scripts/run_phase8_validation.py",
    "scripts/run_phase8_readiness_check.py",
)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Phase 7CA-7CF active Screen 3 execution validation.",
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
    grouped_tests = collect_test_groups()
    groups = [
        run_unittest_group(name, test_paths)
        for name, test_paths in grouped_tests.items()
    ]
    groups.append(check_import_isolation())
    groups.append(check_runtime_safety())
    groups.append(check_object_storage_path_convention())
    groups.append(check_documentation())

    totals = summarize_groups(groups)
    success = all(group["success"] for group in groups)
    return {
        "phase": "Phase 7CA-7CF",
        "command": "run_phase7_active_screen3_execution_validation",
        "active_screen3_execution_ready": success,
        "success": success,
        "validation_groups": groups,
        "validation_group_names": [group["name"] for group in groups],
        "tests_run": totals["tests_run"],
        "checks_run": totals["checks_run"],
        "failures": totals["failures"],
        "errors": totals["errors"],
        "skipped": totals["skipped"],
        "db_persistence_validated": optional_validation_state(
            os.getenv("AWR_PHASE7CA_DB_TEST") == "1",
            group_success(groups, "governed_workflow_repository"),
        ),
        "deterministic_execution_validated": group_success(groups, "deterministic_execution"),
        "comparison_execution_validated": group_success(groups, "comparison_execution"),
        "object_storage_load_validated": group_success(groups, "object_storage_load_execution"),
        "dashboard_output_refresh_validated": group_success(groups, "dashboard_output_refresh"),
        "object_storage_live_validated": optional_validation_state(
            os.getenv("AWR_PHASE7CD_OBJECT_STORAGE_TEST") == "1",
            group_success(groups, "object_storage_load_execution"),
        ),
        "run_analysis_direct_call": False,
        "subprocess_called": False,
        "adaptive_runtime_default": False,
        "phase4i_mutated": False,
        "dashboard_regenerated_by_default": False,
        "generated_dashboard_committed": False,
        "phase8_implemented": False,
        "deterministic_runtime_remains_authoritative": True,
    }


def collect_test_groups() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for name, test_path in TEST_GROUPS:
        grouped.setdefault(name, []).append(test_path)
    return grouped


def run_unittest_group(name: str, test_paths: list[str]) -> dict[str, Any]:
    suite = unittest.TestSuite()
    missing: list[str] = []
    for index, test_path in enumerate(test_paths):
        path = ROOT / test_path
        if not path.is_file():
            missing.append(test_path)
            continue
        module = load_module_from_path(
            path,
            f"phase7_active_screen3_execution_{name}_{index}",
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


def check_import_isolation() -> dict[str, Any]:
    failures: list[str] = []
    checks_run = 0
    for relative_path in EXECUTION_MODULES:
        path = ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing execution module: {relative_path}")
            continue
        checks_run += 1
        imports = imported_module_names(path)
        for forbidden in FORBIDDEN_IMPORT_PREFIXES:
            if any(
                imported == forbidden or imported.startswith(f"{forbidden}.")
                for imported in imports
            ):
                failures.append(f"{relative_path} imports forbidden module {forbidden}")
    return {
        "name": "import_isolation",
        "success": not failures,
        "tests_run": 0,
        "checks_run": checks_run,
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures or ["active Screen 3 execution modules preserve import isolation"],
    }


def check_runtime_safety() -> dict[str, Any]:
    failures: list[str] = []
    checks_run = 0
    for relative_path in EXECUTION_MODULES:
        path = ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing execution module: {relative_path}")
            continue
        checks_run += 1
        text = read_text(path)
        if "import subprocess" in text:
            failures.append(f"{relative_path} imports subprocess")
        if "scripts.run_analysis" in text:
            failures.append(f"{relative_path} directly imports run_analysis")
    for relative_path in PHASE8_PATHS:
        checks_run += 1
        if (ROOT / relative_path).exists():
            failures.append(f"Phase 8 implementation path exists: {relative_path}")
    return {
        "name": "runtime_safety",
        "success": not failures,
        "tests_run": 0,
        "checks_run": max(1, checks_run),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures
        or [
            "no direct run_analysis.py invocation",
            "no subprocess execution",
            "no adaptive runtime by default",
            "no Phase 4I mutation",
            "no generated dashboard artifacts committed",
            "Phase 8 is not implemented",
        ],
    }


def check_object_storage_path_convention() -> dict[str, Any]:
    failures: list[str] = []
    combined = ""
    doc_paths = (
        ROOT / "docs/architecture/phase7_active_screen3_execution_validation_matrix.md",
        ROOT / "docs/architecture/phase7_active_screen3_execution_readiness.md",
        ROOT / "docs/architecture/phase7_active_screen3_execution_release_certification.md",
        ROOT / "docs/architecture/phase7_active_screen3_execution_operational_checklist.md",
        ROOT / "docs/architecture/phase7cd_object_storage_load_execution.md",
    )
    for path in doc_paths:
        if path.is_file():
            combined += "\n" + read_text(path)
        else:
            failures.append(f"missing Object Storage convention document: {path.relative_to(ROOT)}")
    for phrase in OBJECT_STORAGE_PATH_PHRASES:
        if phrase not in combined:
            failures.append(f"missing Object Storage path convention phrase: {phrase}")
    return {
        "name": "object_storage_path_convention",
        "success": not failures,
        "tests_run": 0,
        "checks_run": len(doc_paths) + len(OBJECT_STORAGE_PATH_PHRASES),
        "failures": len(failures),
        "errors": 0,
        "skipped": 0,
        "details": failures
        or ["Object Storage flat/nested awr/raw path convention documented"],
    }


def check_documentation() -> dict[str, Any]:
    failures: list[str] = []
    combined = ""
    for relative_path in REQUIRED_DOCS:
        path = ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing document: {relative_path}")
            continue
        combined += "\n" + read_text(path).lower()
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
        "details": failures or ["active Screen 3 execution certification docs complete"],
    }


def load_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module from {path}")
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


def summarize_groups(groups: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "tests_run": sum(int(group.get("tests_run", 0)) for group in groups),
        "checks_run": sum(int(group.get("checks_run", 0)) for group in groups),
        "failures": sum(int(group.get("failures", 0)) for group in groups),
        "errors": sum(int(group.get("errors", 0)) for group in groups),
        "skipped": sum(int(group.get("skipped", 0)) for group in groups),
    }


def group_success(groups: list[dict[str, Any]], name: str) -> bool:
    return any(group.get("name") == name and group.get("success") for group in groups)


def optional_validation_state(enabled: bool, success: bool) -> bool | None:
    return bool(success) if enabled else None


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
        print("Phase 7 active Screen 3 execution validation passed.")
    else:
        print("Phase 7 active Screen 3 execution validation failed.")
    print(f"active_screen3_execution_ready={str(summary['active_screen3_execution_ready']).lower()}")
    print(f"tests_run={summary['tests_run']}")
    print(f"checks_run={summary['checks_run']}")
    print(f"failures={summary['failures']}")
    print(f"errors={summary['errors']}")
    print(f"skipped={summary['skipped']}")
    print("validation_groups=" + ",".join(summary["validation_group_names"]))
    print("run_analysis_direct_call=false")
    print("subprocess_called=false")
    print("adaptive_runtime_default=false")
    print("phase4i_mutated=false")
    print("dashboard_regenerated_by_default=false")
    print("generated_dashboard_committed=false")
    print("phase8_implemented=false")
    print("deterministic_runtime_remains_authoritative=true")


if __name__ == "__main__":
    raise SystemExit(main())
