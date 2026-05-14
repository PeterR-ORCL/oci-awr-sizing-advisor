#!/usr/bin/env python3
"""Run the local Phase 7AA runtime integration readiness check."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]

READINESS_CATEGORY_KEYS: tuple[str, ...] = (
    "runtime_gate",
    "adaptive_runtime_context",
    "scoring_integration_adapter",
    "recommendation_integration_adapter",
    "parser_integration_adapter",
    "runtime_fallback_rollback",
    "runtime_isolation",
    "documentation_complete",
    "ml_regression",
    "materialization_regression",
    "phase7_regression",
    "phase6_regression",
)


READINESS_DOCS: tuple[str, ...] = (
    "docs/architecture/phase7aa_runtime_integration_validation_matrix.md",
    "docs/architecture/phase7aa_runtime_integration_readiness.md",
    "docs/architecture/phase7aa_runtime_integration_release_certification.md",
    "docs/architecture/phase7aa_runtime_integration_operational_checklist.md",
)


REQUIRED_SCRIPTS: tuple[str, ...] = (
    "scripts/run_phase7aa_runtime_integration_validation.py",
    "scripts/run_phase7aa_runtime_integration_readiness_check.py",
)


FORBIDDEN_IMPORTS: tuple[str, ...] = (
    "oracledb",
    "requests",
    "socket",
    "urllib",
    "http.client",
    "httpx",
    "oci",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local-only Phase 7AA runtime integration readiness checks.",
    )
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON only.")
    parser.add_argument(
        "--include-phase6",
        action="store_true",
        help="Also run Phase 6 regression validation.",
    )
    parser.add_argument(
        "--include-phase7",
        action="store_true",
        help="Retained for explicit Phase 7 regression readiness; Phase 7 is included by default.",
    )
    parser.add_argument(
        "--include-materialization",
        action="store_true",
        help="Retained for explicit materialization readiness; materialization is included by default.",
    )
    parser.add_argument(
        "--include-ml",
        action="store_true",
        help="Retained for explicit ML readiness; ML is included by default.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_readiness_check(include_phase6=args.include_phase6)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_human_summary(summary)
    return 0 if summary["success"] else 1


def run_readiness_check(*, include_phase6: bool = False) -> dict[str, Any]:
    checks = run_command_checks(include_phase6=include_phase6)
    checks.extend(
        [
            check_required_paths("phase7aa_required_scripts", REQUIRED_SCRIPTS),
            check_required_paths("phase7aa_readiness_docs", READINESS_DOCS),
            check_readiness_doc_language(),
            check_readiness_script_imports(),
        ]
    )
    checks_by_name = {check["name"]: check for check in checks}

    validation_json = checks_by_name["phase7aa_validation_json"].get("json_payload", {})
    validation_groups = {
        group.get("name"): bool(group.get("success"))
        for group in validation_json.get("validation_groups", [])
        if isinstance(group, dict)
    }

    readiness_categories = {
        "runtime_gate": validation_groups.get("runtime_gate", False),
        "adaptive_runtime_context": validation_groups.get("adaptive_runtime_context", False),
        "scoring_integration_adapter": validation_groups.get(
            "scoring_integration_adapter",
            False,
        ),
        "recommendation_integration_adapter": validation_groups.get(
            "recommendation_integration_adapter",
            False,
        ),
        "parser_integration_adapter": validation_groups.get(
            "parser_integration_adapter",
            False,
        ),
        "runtime_fallback_rollback": validation_groups.get(
            "runtime_fallback_rollback",
            False,
        ),
        "runtime_isolation": validation_groups.get("import_isolation", False),
        "documentation_complete": (
            validation_groups.get("documentation", False)
            and checks_by_name["phase7aa_readiness_docs"]["success"]
            and checks_by_name["phase7aa_readiness_doc_language"]["success"]
        ),
        "ml_regression": (
            checks_by_name["phase7_ml_validation"]["success"]
            and checks_by_name["phase7_ml_readiness"]["success"]
        ),
        "materialization_regression": (
            checks_by_name["phase7_materialization_validation"]["success"]
            and checks_by_name["phase7_materialization_readiness"]["success"]
        ),
        "phase7_regression": (
            checks_by_name["phase7_validation"]["success"]
            and checks_by_name["phase7_readiness"]["success"]
        ),
        "phase6_regression": None,
    }
    if include_phase6:
        readiness_categories["phase6_regression"] = checks_by_name["phase6_regression"]["success"]

    required_categories = [
        value for key, value in readiness_categories.items() if key != "phase6_regression"
    ]
    if include_phase6:
        required_categories.append(bool(readiness_categories["phase6_regression"]))

    totals = summarize_checks(checks)
    success = all(check["success"] for check in checks) and all(required_categories)
    return {
        "phase": "Phase 7AA",
        "command": "run_phase7aa_runtime_integration_readiness_check",
        "runtime_integration_ready": success,
        "success": success,
        "readiness_categories": readiness_categories,
        "tests_run": totals["tests_run"],
        "checks_run": totals["checks_run"],
        "failures": totals["failures"],
        "errors": totals["errors"],
        "skipped": totals["skipped"],
        "runtime_active": False,
        "runtime_influence_granted": False,
        "runtime_mutation_performed": False,
        "deterministic_runtime_remains_authoritative": True,
        "fallback_to_deterministic": True,
        "rollback_execution": False,
        "network_dependency": False,
        "database_dependency": False,
        "oracle_agent_memory_dependency": False,
        "phase6_validation_included": include_phase6,
        "checks": checks,
    }


def run_command_checks(*, include_phase6: bool) -> list[dict[str, Any]]:
    checks = [
        run_command_check(
            name="phase7aa_validation",
            args=(sys.executable, "scripts/run_phase7aa_runtime_integration_validation.py"),
        ),
        run_command_check(
            name="phase7aa_validation_json",
            args=(sys.executable, "scripts/run_phase7aa_runtime_integration_validation.py", "--json"),
            expect_json=True,
        ),
        run_command_check(
            name="phase7aa_validation_tests",
            args=(sys.executable, "-m", "unittest", "tests/test_phase7aa_runtime_integration_validation.py"),
        ),
        run_command_check(
            name="phase7aa_readiness_tests",
            args=(
                sys.executable,
                "-m",
                "unittest",
                "tests/test_phase7aa_runtime_integration_readiness_check.py",
            ),
            extra_env={"PHASE7AA_READINESS_SELFTEST": "1"},
        ),
        run_command_check(
            name="phase7_ml_validation",
            args=(sys.executable, "scripts/run_phase7_ml_validation.py"),
        ),
        run_command_check(
            name="phase7_ml_readiness",
            args=(sys.executable, "scripts/run_phase7_ml_readiness_check.py"),
        ),
        run_command_check(
            name="phase7_materialization_validation",
            args=(sys.executable, "scripts/run_phase7_materialization_validation.py"),
        ),
        run_command_check(
            name="phase7_materialization_readiness",
            args=(sys.executable, "scripts/run_phase7_materialization_readiness_check.py"),
        ),
        run_command_check(
            name="phase7_validation",
            args=(phase_python(), "scripts/run_phase7_validation.py"),
        ),
        run_command_check(
            name="phase7_readiness",
            args=(phase_python(), "scripts/run_phase7_readiness_check.py"),
        ),
        run_command_check(
            name="phase7h_dashboard_validation",
            args=(sys.executable, "scripts/run_phase7h_dashboard_validation.py"),
        ),
        run_command_check(
            name="phase7i_cli_validation",
            args=(phase_python(), "scripts/awr_memory_cli.py", "learning", "validate", "--json"),
            expect_json=True,
        ),
    ]
    if include_phase6:
        checks.append(
            run_command_check(
                name="phase6_regression",
                args=(phase_python(), "scripts/run_phase6_validation.py"),
                extra_env={"PYTHONPATH": phase6_pythonpath()},
            )
        )
    return checks


def run_command_check(
    *,
    name: str,
    args: tuple[str, ...],
    expect_json: bool = False,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_env:
        env.update(extra_env)
    completed = subprocess.run(
        args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    counts = parse_counts(output)
    json_payload: dict[str, Any] | None = None
    details: list[str] = []
    success = completed.returncode == 0
    if expect_json:
        try:
            json_payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            success = False
            details.append(f"invalid JSON output: {exc}")
    details.extend(normalize_output_lines(output))
    return {
        "name": name,
        "success": success,
        "returncode": completed.returncode,
        "tests_run": counts["tests_run"],
        "checks_run": counts["checks_run"] or 1,
        "failures": counts["failures"] if completed.returncode == 0 else max(1, counts["failures"]),
        "errors": counts["errors"],
        "skipped": counts["skipped"],
        "json_payload": json_payload,
        "details": details,
    }


def check_required_paths(name: str, relative_paths: tuple[str, ...]) -> dict[str, Any]:
    missing = [path for path in relative_paths if not (ROOT / path).is_file()]
    return {
        "name": name,
        "success": not missing,
        "tests_run": 0,
        "checks_run": len(relative_paths),
        "failures": len(missing),
        "errors": 0,
        "skipped": 0,
        "details": [f"missing path: {path}" for path in missing] or ["required paths present"],
    }


def check_readiness_doc_language() -> dict[str, Any]:
    required_phrases = (
        "runtime_integration_ready=true only when all checks pass",
        "7aa does not activate adaptive runtime",
        "deterministic runtime remains authoritative",
        "run_analysis.py remains untouched",
        "phase 8 is not implemented",
        "7aa is certified as controlled integration scaffolding only",
        "no adaptive runtime activation is certified",
        "no run_analysis.py integration is certified",
        "future 7ab/7ac remain required",
    )
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8", errors="ignore").lower()
        for path in READINESS_DOCS
        if (ROOT / path).is_file()
    )
    missing = [phrase for phrase in required_phrases if phrase not in combined]
    return {
        "name": "phase7aa_readiness_doc_language",
        "success": not missing,
        "tests_run": 0,
        "checks_run": len(required_phrases),
        "failures": len(missing),
        "errors": 0,
        "skipped": 0,
        "details": [f"missing phrase: {phrase}" for phrase in missing]
        or ["readiness and certification language present"],
    }


def check_readiness_script_imports() -> dict[str, Any]:
    path = ROOT / "scripts" / "run_phase7aa_runtime_integration_readiness_check.py"
    source = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source, filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)

    violations = [
        imported
        for imported in imports
        for forbidden in FORBIDDEN_IMPORTS
        if imported == forbidden or imported.startswith(f"{forbidden}.")
    ]
    shell_true = "shell" + "=True"
    if shell_true in source:
        violations.append(shell_true)
    return {
        "name": "phase7aa_readiness_script_imports",
        "success": not violations,
        "tests_run": 0,
        "checks_run": len(imports),
        "failures": len(violations),
        "errors": 0,
        "skipped": 0,
        "details": [f"unsafe import or shell usage: {item}" for item in violations]
        or ["readiness script imports are local and standard-library only"],
    }


def parse_counts(output: str) -> dict[str, int]:
    tests_run = 0
    ran_match = re.search(r"Ran (\d+) tests?", output)
    if ran_match:
        tests_run = int(ran_match.group(1))
    return {
        "tests_run": tests_run,
        "checks_run": tests_run,
        "failures": count_named_result(output, "failures"),
        "errors": count_named_result(output, "errors"),
        "skipped": count_named_result(output, "skipped"),
    }


def count_named_result(output: str, name: str) -> int:
    match = re.search(rf"{name}=(\d+)", output)
    if match:
        return int(match.group(1))
    return 0


def normalize_output_lines(output: str, *, limit: int = 12) -> list[str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[:limit]


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "tests_run": sum(int(check.get("tests_run", 0)) for check in checks),
        "checks_run": sum(int(check.get("checks_run", 0)) for check in checks),
        "failures": sum(int(check.get("failures", 0)) for check in checks),
        "errors": sum(int(check.get("errors", 0)) for check in checks),
        "skipped": sum(int(check.get("skipped", 0)) for check in checks),
    }


def phase_python() -> str:
    venv_python = ROOT / ".venv" / "bin" / "python"
    return str(venv_python) if venv_python.is_file() else sys.executable


def phase6_pythonpath() -> str:
    existing = os.environ.get("PYTHONPATH")
    return str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"


def print_human_summary(summary: dict[str, Any]) -> None:
    if summary["success"]:
        print("Phase 7AA runtime integration readiness passed.")
    else:
        print("Phase 7AA runtime integration readiness failed.")
    print(f"runtime_integration_ready={str(summary['runtime_integration_ready']).lower()}")
    print(f"tests_run={summary['tests_run']}")
    print(f"checks_run={summary['checks_run']}")
    print(f"failures={summary['failures']}")
    print(f"errors={summary['errors']}")
    for category, value in summary["readiness_categories"].items():
        print(f"- {category}: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
