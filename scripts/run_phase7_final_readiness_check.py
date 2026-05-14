#!/usr/bin/env python3
"""Run the local final Phase 7 adaptive runtime readiness check."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]


READINESS_CATEGORY_KEYS: tuple[str, ...] = (
    "learning_foundation",
    "controlled_materialization",
    "ml_adaptive_scoring",
    "controlled_runtime_integration",
    "dashboard_cli_visibility",
    "runtime_isolation",
    "phase4i_contract_protected",
    "documentation_complete",
    "phase6_regression",
)


FINAL_DOCS: tuple[str, ...] = (
    "docs/architecture/phase7_final_readiness.md",
    "docs/architecture/phase7_final_release_certification.md",
    "docs/architecture/phase7_final_operational_checklist.md",
    "docs/architecture/phase7_final_validation_matrix.md",
)


REQUIRED_SCRIPTS: tuple[str, ...] = (
    "scripts/run_phase7_final_readiness_check.py",
    "scripts/run_phase7_readiness_check.py",
    "scripts/run_phase7_materialization_readiness_check.py",
    "scripts/run_phase7_ml_readiness_check.py",
    "scripts/run_phase7aa_runtime_integration_readiness_check.py",
)


PHASE7AA_RUNTIME_MODULES: tuple[str, ...] = (
    "adaptive_runtime_gate",
    "adaptive_runtime_context",
    "adaptive_scoring_adapter",
    "adaptive_recommendation_adapter",
    "adaptive_parser_adapter",
    "adaptive_runtime_fallback",
)


PHASE7_ML_RUNTIME_MODULES: tuple[str, ...] = (
    "ml_boundary",
    "feature_label_dataset",
    "trend_aware_scoring",
    "shadow_ml_model_interface",
    "ml_training_backtesting",
    "ml_explainability",
    "ml_model_registry",
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


PHASE7AA_SOURCE_PATHS: tuple[str, ...] = (
    "src/learning/adaptive_runtime_gate.py",
    "src/learning/adaptive_runtime_context.py",
    "src/learning/adaptive_scoring_adapter.py",
    "src/learning/adaptive_recommendation_adapter.py",
    "src/learning/adaptive_parser_adapter.py",
    "src/learning/adaptive_runtime_fallback.py",
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


FORBIDDEN_RUNTIME_FUNCTIONS: tuple[str, ...] = (
    "apply_adaptive_runtime",
    "activate_runtime",
    "execute_rollback",
    "apply_rollback",
    "update_runtime_scoring",
    "update_runtime_parser",
    "update_runtime_recommendation",
    "replace_scoring_engine",
    "replace_recommendation_engine",
    "mutate_parser",
    "auto_apply",
    "autonomous_apply",
)


PHASE8_IMPLEMENTATION_PATHS: tuple[str, ...] = (
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
        description="Run local-only final Phase 7 adaptive runtime readiness checks.",
    )
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON only.")
    parser.add_argument(
        "--include-phase6",
        action="store_true",
        help="Also run Phase 6 regression validation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_final_readiness_check(include_phase6=args.include_phase6)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_human_summary(summary)
    return 0 if summary["success"] else 1


def run_final_readiness_check(*, include_phase6: bool = False) -> dict[str, Any]:
    checks = run_command_checks(include_phase6=include_phase6)
    checks.extend(
        [
            check_required_paths("phase7_final_required_scripts", REQUIRED_SCRIPTS),
            check_required_paths("phase7_final_docs", FINAL_DOCS),
            check_final_doc_language(),
            check_final_readiness_script_imports(),
            check_import_isolation(),
            check_runtime_safety(),
            check_phase8_not_implemented(),
            check_readme_links(),
        ]
    )
    checks_by_name = {check["name"]: check for check in checks}

    readiness_categories = {
        "learning_foundation": checks_by_name["phase7_foundation_readiness"]["success"],
        "controlled_materialization": checks_by_name[
            "phase7_materialization_readiness"
        ]["success"],
        "ml_adaptive_scoring": checks_by_name["phase7_ml_readiness"]["success"],
        "controlled_runtime_integration": checks_by_name[
            "phase7aa_runtime_integration_readiness"
        ]["success"],
        "dashboard_cli_visibility": (
            checks_by_name["phase7h_dashboard_validation"]["success"]
            and checks_by_name["phase7i_cli_validation"]["success"]
            and checks_by_name["phase7ab_dashboard_visibility_tests"]["success"]
            and checks_by_name["phase7ab_cli_visibility_tests"]["success"]
        ),
        "runtime_isolation": checks_by_name["runtime_import_isolation"]["success"],
        "phase4i_contract_protected": checks_by_name[
            "phase7_final_doc_language"
        ]["success"],
        "documentation_complete": (
            checks_by_name["phase7_final_docs"]["success"]
            and checks_by_name["phase7_final_doc_language"]["success"]
            and checks_by_name["phase7_final_readme_links"]["success"]
        ),
        "phase6_regression": None,
    }
    if include_phase6:
        readiness_categories["phase6_regression"] = checks_by_name[
            "phase6_regression"
        ]["success"]

    required_categories = [
        value for key, value in readiness_categories.items() if key != "phase6_regression"
    ]
    if include_phase6:
        required_categories.append(bool(readiness_categories["phase6_regression"]))

    totals = summarize_checks(checks)
    success = all(check["success"] for check in checks) and all(required_categories)
    return {
        "phase": "Phase 7",
        "command": "run_phase7_final_readiness_check",
        "phase7_final_ready": success,
        "success": success,
        "readiness_categories": readiness_categories,
        "tests_run": totals["tests_run"],
        "checks_run": totals["checks_run"],
        "failures": totals["failures"],
        "errors": totals["errors"],
        "skipped": totals["skipped"],
        "deterministic_runtime_remains_authoritative": True,
        "adaptive_runtime_active": False,
        "runtime_active": False,
        "runtime_influence_granted": False,
        "runtime_mutation_performed": False,
        "rollback_execution": False,
        "run_analysis_integrated": False,
        "phase8_implemented": False,
        "network_dependency": False,
        "database_dependency": False,
        "oracle_agent_memory_dependency": False,
        "phase6_validation_included": include_phase6,
        "checks": checks,
    }


def run_command_checks(*, include_phase6: bool) -> list[dict[str, Any]]:
    checks = [
        run_command_check(
            name="phase7_foundation_readiness",
            args=(phase_python(), "scripts/run_phase7_readiness_check.py"),
        ),
        run_command_check(
            name="phase7_materialization_readiness",
            args=(sys.executable, "scripts/run_phase7_materialization_readiness_check.py"),
        ),
        run_command_check(
            name="phase7_ml_readiness",
            args=(sys.executable, "scripts/run_phase7_ml_readiness_check.py"),
        ),
        run_command_check(
            name="phase7aa_runtime_integration_readiness",
            args=(sys.executable, "scripts/run_phase7aa_runtime_integration_readiness_check.py"),
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
        run_command_check(
            name="phase7ab_dashboard_visibility_tests",
            args=(sys.executable, "-m", "unittest", "tests/test_dashboard_ml_explainability_visibility.py"),
        ),
        run_command_check(
            name="phase7ab_cli_visibility_tests",
            args=(sys.executable, "-m", "unittest", "tests/test_learning_cli_ml_visibility.py"),
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
    details: list[str] = []
    json_payload: dict[str, Any] | None = None
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


def check_final_doc_language() -> dict[str, Any]:
    required_phrases = (
        "Phase 7 final readiness does not mean adaptive runtime is active.",
        "adaptive runtime remains gated.",
        "deterministic runtime remains authoritative.",
        "Phase 8 is not implemented.",
        "Phase 7 is certified as governed adaptive intelligence with controlled runtime integration scaffolding.",
        "Phase 7 is not certified as fully active autonomous runtime mutation.",
        "Adaptive runtime is not enabled by default.",
        "Phase 8 sizing/TCO is not certified here.",
        "readiness validates safety, not activation.",
        "no runtime activation occurs.",
        "do not treat readiness as runtime activation",
    )
    combined = "\n".join(
        (ROOT / path).read_text(encoding="utf-8", errors="ignore")
        for path in FINAL_DOCS
        if (ROOT / path).is_file()
    )
    combined_lower = combined.lower()
    missing = [phrase for phrase in required_phrases if phrase.lower() not in combined_lower]
    return {
        "name": "phase7_final_doc_language",
        "success": not missing,
        "tests_run": 0,
        "checks_run": len(required_phrases),
        "failures": len(missing),
        "errors": 0,
        "skipped": 0,
        "details": [f"missing phrase: {phrase}" for phrase in missing]
        or ["final readiness and certification language present"],
    }


def check_final_readiness_script_imports() -> dict[str, Any]:
    path = ROOT / "scripts" / "run_phase7_final_readiness_check.py"
    imports = imported_module_names(path)
    source = read_text(path)
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
        "name": "phase7_final_readiness_script_imports",
        "success": not violations,
        "tests_run": 0,
        "checks_run": len(imports),
        "failures": len(violations),
        "errors": 0,
        "skipped": 0,
        "details": [f"unsafe import or shell usage: {item}" for item in violations]
        or ["final readiness script imports are local and standard-library only"],
    }


def check_import_isolation() -> dict[str, Any]:
    details: list[str] = []
    scanned = 0
    for path in iter_python_files(RUNTIME_IMPORT_PATHS):
        scanned += 1
        imported_modules = imported_module_names(path)
        for imported_module in imported_modules:
            if is_phase7aa_runtime_import(imported_module):
                details.append(f"{relative(path)} imports {imported_module}")
            if is_phase7_ml_runtime_import(imported_module):
                details.append(f"{relative(path)} imports ML runtime module {imported_module}")

    run_analysis = ROOT / "scripts" / "run_analysis.py"
    if run_analysis.is_file():
        source = read_text(run_analysis)
        if any(module in source for module in PHASE7AA_RUNTIME_MODULES):
            details.append("scripts/run_analysis.py references Phase 7AA runtime modules")
        if any(module in source for module in PHASE7_ML_RUNTIME_MODULES):
            details.append("scripts/run_analysis.py references Phase 7 ML modules")

    return {
        "name": "runtime_import_isolation",
        "success": not details,
        "tests_run": 0,
        "checks_run": scanned,
        "failures": len(details),
        "errors": 0,
        "skipped": 0,
        "details": details or ["runtime import isolation preserved"],
    }


def check_runtime_safety() -> dict[str, Any]:
    details: list[str] = []
    checks_run = 0
    for path in iter_python_files(PHASE7AA_SOURCE_PATHS):
        checks_run += 1
        tree = ast.parse(read_text(path), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in FORBIDDEN_RUNTIME_FUNCTIONS:
                    details.append(f"{relative(path)} defines forbidden function {node.name}")
            elif isinstance(node, ast.ClassDef):
                for body_node in node.body:
                    if isinstance(body_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if body_node.name in FORBIDDEN_RUNTIME_FUNCTIONS:
                            details.append(
                                f"{relative(path)} defines forbidden method {body_node.name}"
                            )
        details.extend(find_unsafe_runtime_true_assignments(path, tree))

    return {
        "name": "runtime_safety",
        "success": not details,
        "tests_run": 0,
        "checks_run": checks_run,
        "failures": len(details),
        "errors": 0,
        "skipped": 0,
        "details": details or ["runtime safety flags remain inactive"],
    }


def find_unsafe_runtime_true_assignments(path: Path, tree: ast.AST) -> list[str]:
    unsafe_names = {
        "runtime_active",
        "runtime_influence_granted",
        "runtime_mutation_performed",
        "runtime_score_applied",
        "runtime_recommendation_applied",
        "runtime_parser_applied",
    }
    details: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                target_name = assignment_target_name(target)
                if target_name in unsafe_names and is_true_literal(node.value):
                    details.append(f"{relative(path)} assigns {target_name}=True")
        elif isinstance(node, ast.AnnAssign):
            target_name = assignment_target_name(node.target)
            if target_name in unsafe_names and node.value is not None and is_true_literal(node.value):
                details.append(f"{relative(path)} assigns {target_name}=True")
        elif isinstance(node, ast.keyword):
            if node.arg in unsafe_names and is_true_literal(node.value):
                details.append(f"{relative(path)} passes {node.arg}=True")
    return details


def assignment_target_name(target: ast.AST) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def is_true_literal(value: ast.AST) -> bool:
    return isinstance(value, ast.Constant) and value.value is True


def check_phase8_not_implemented() -> dict[str, Any]:
    present = [path for path in PHASE8_IMPLEMENTATION_PATHS if (ROOT / path).exists()]
    return {
        "name": "phase8_not_implemented",
        "success": not present,
        "tests_run": 0,
        "checks_run": len(PHASE8_IMPLEMENTATION_PATHS),
        "failures": len(present),
        "errors": 0,
        "skipped": 0,
        "details": [f"unexpected Phase 8 implementation path: {path}" for path in present]
        or ["Phase 8 sizing/TCO implementation paths are absent"],
    }


def check_readme_links() -> dict[str, Any]:
    readme = ROOT / "docs" / "architecture" / "README.md"
    text = read_text(readme) if readme.is_file() else ""
    required = (
        "phase7_final_readiness.md",
        "phase7_final_release_certification.md",
        "phase7_final_operational_checklist.md",
        "phase7_final_validation_matrix.md",
    )
    missing = [item for item in required if item not in text]
    return {
        "name": "phase7_final_readme_links",
        "success": not missing,
        "tests_run": 0,
        "checks_run": len(required),
        "failures": len(missing),
        "errors": 0,
        "skipped": 0,
        "details": [f"README missing link: {item}" for item in missing]
        or ["README links final Phase 7 docs"],
    }


def iter_python_files(paths: Iterable[str]) -> list[Path]:
    files: list[Path] = []
    for relative_path in paths:
        path = ROOT / relative_path
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return files


def imported_module_names(path: Path) -> set[str]:
    imports: set[str] = set()
    tree = ast.parse(read_text(path), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def is_phase7aa_runtime_import(module_name: str) -> bool:
    parts = module_name.split(".")
    if parts[-1] in PHASE7AA_RUNTIME_MODULES:
        return True
    return any(f"src.learning.{module}" == module_name for module in PHASE7AA_RUNTIME_MODULES)


def is_phase7_ml_runtime_import(module_name: str) -> bool:
    parts = module_name.split(".")
    if parts[-1] in PHASE7_ML_RUNTIME_MODULES:
        return True
    return any(f"src.learning.{module}" == module_name for module in PHASE7_ML_RUNTIME_MODULES)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def summarize_checks(checks: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "tests_run": sum(int(check.get("tests_run", 0)) for check in checks),
        "checks_run": sum(int(check.get("checks_run", 0)) for check in checks),
        "failures": sum(int(check.get("failures", 0)) for check in checks),
        "errors": sum(int(check.get("errors", 0)) for check in checks),
        "skipped": sum(int(check.get("skipped", 0)) for check in checks),
    }


def parse_counts(output: str) -> dict[str, int]:
    tests_run = 0
    ran_match = re.search(r"Ran (\d+) tests?", output)
    if ran_match:
        tests_run = int(ran_match.group(1))
    checks_match = re.search(r"checks_run[=:](\d+)", output)
    checks_run = int(checks_match.group(1)) if checks_match else tests_run
    return {
        "tests_run": tests_run,
        "checks_run": checks_run,
        "failures": count_named_result(output, "failures"),
        "errors": count_named_result(output, "errors"),
        "skipped": count_named_result(output, "skipped"),
    }


def count_named_result(output: str, name: str) -> int:
    match = re.search(rf"{name}[=:](\d+)", output)
    if match:
        return int(match.group(1))
    return 0


def normalize_output_lines(output: str, *, limit: int = 12) -> list[str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[:limit]


def phase_python() -> str:
    venv_python = ROOT / ".venv" / "bin" / "python"
    return str(venv_python) if venv_python.is_file() else sys.executable


def phase6_pythonpath() -> str:
    existing = os.environ.get("PYTHONPATH")
    return str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"


def print_human_summary(summary: dict[str, Any]) -> None:
    if summary["success"]:
        print("Phase 7 final readiness passed.")
    else:
        print("Phase 7 final readiness failed.")
    print(f"phase7_final_ready={str(summary['phase7_final_ready']).lower()}")
    print(f"tests_run={summary['tests_run']}")
    print(f"checks_run={summary['checks_run']}")
    print(f"failures={summary['failures']}")
    print(f"errors={summary['errors']}")
    print(f"adaptive_runtime_active={str(summary['adaptive_runtime_active']).lower()}")
    print(f"runtime_active={str(summary['runtime_active']).lower()}")
    print(f"runtime_influence_granted={str(summary['runtime_influence_granted']).lower()}")
    print(f"runtime_mutation_performed={str(summary['runtime_mutation_performed']).lower()}")
    for category, value in summary["readiness_categories"].items():
        print(f"- {category}: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
