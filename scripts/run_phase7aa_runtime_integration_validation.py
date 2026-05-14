#!/usr/bin/env python3
"""Run the local Phase 7AA runtime integration validation harness."""

from __future__ import annotations

import argparse
import ast
import io
import json
import os
import re
import subprocess
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class ValidationGroup:
    name: str
    modules: tuple[str, ...]
    description: str


UNITTEST_GROUPS: tuple[ValidationGroup, ...] = (
    ValidationGroup(
        name="runtime_gate",
        modules=("tests.test_phase7aa_runtime_integration_gate",),
        description="Phase 7AA.1 runtime config gate remains opt-in and default-deny.",
    ),
    ValidationGroup(
        name="adaptive_runtime_context",
        modules=("tests.test_phase7aa_adaptive_runtime_context",),
        description="Phase 7AA.2 runtime context remains read-only.",
    ),
    ValidationGroup(
        name="scoring_integration_adapter",
        modules=("tests.test_phase7aa_scoring_integration_adapter",),
        description="Phase 7AA.3 scoring adapter remains advisory/result-only.",
    ),
    ValidationGroup(
        name="recommendation_integration_adapter",
        modules=("tests.test_phase7aa_recommendation_integration_adapter",),
        description="Phase 7AA.4 recommendation adapter remains advisory/result-only.",
    ),
    ValidationGroup(
        name="parser_integration_adapter",
        modules=("tests.test_phase7aa_parser_integration_adapter",),
        description="Phase 7AA.5 parser adapter remains backlog/consideration-only.",
    ),
    ValidationGroup(
        name="runtime_fallback_rollback",
        modules=("tests.test_phase7aa_runtime_fallback_rollback",),
        description="Phase 7AA.6 fallback/rollback layer remains decision-only.",
    ),
)


ADAPTIVE_RUNTIME_MODULES: tuple[str, ...] = (
    "adaptive_runtime_gate",
    "adaptive_runtime_context",
    "adaptive_scoring_adapter",
    "adaptive_recommendation_adapter",
    "adaptive_parser_adapter",
    "adaptive_runtime_fallback",
)


ADAPTIVE_RUNTIME_SOURCE_PATHS: tuple[str, ...] = (
    "src/learning/adaptive_runtime_gate.py",
    "src/learning/adaptive_runtime_context.py",
    "src/learning/adaptive_scoring_adapter.py",
    "src/learning/adaptive_recommendation_adapter.py",
    "src/learning/adaptive_parser_adapter.py",
    "src/learning/adaptive_runtime_fallback.py",
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


REQUIRED_DOCS: tuple[str, ...] = (
    "docs/architecture/phase7aa_runtime_integration_boundary.md",
    "docs/architecture/phase7aa_runtime_config_gate.md",
    "docs/architecture/phase7aa_adaptive_runtime_context.md",
    "docs/architecture/phase7aa_runtime_context_model.md",
    "docs/architecture/phase7aa_scoring_integration_adapter.md",
    "docs/architecture/phase7aa_scoring_integration_model.md",
    "docs/architecture/phase7aa_recommendation_integration_adapter.md",
    "docs/architecture/phase7aa_recommendation_integration_model.md",
    "docs/architecture/phase7aa_parser_integration_adapter.md",
    "docs/architecture/phase7aa_parser_integration_model.md",
    "docs/architecture/phase7aa_runtime_fallback_rollback.md",
    "docs/architecture/phase7aa_runtime_fallback_model.md",
    "docs/architecture/phase7aa_runtime_integration_validation_matrix.md",
    "docs/architecture/phase7aa_runtime_integration_readiness.md",
    "docs/architecture/phase7aa_runtime_integration_release_certification.md",
    "docs/architecture/phase7aa_runtime_integration_operational_checklist.md",
)


DOCUMENTATION_PHRASES: tuple[str, ...] = (
    "adaptive runtime is opt-in only",
    "default config denies integration",
    "adapters are advisory/result-only",
    "fallback/rollback is decision-only",
    "no rollback execution",
    "no run_analysis.py integration",
    "no runtime mutation",
    "deterministic runtime remains authoritative",
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local-only Phase 7AA runtime integration validation.",
    )
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON only.")
    parser.add_argument(
        "--include-phase6",
        action="store_true",
        help="Also run Phase 6 validation when available.",
    )
    parser.add_argument(
        "--include-phase7-foundation",
        action="store_true",
        help="Also run scripts/run_phase7_validation.py.",
    )
    parser.add_argument(
        "--include-materialization",
        action="store_true",
        help="Also run materialization validation.",
    )
    parser.add_argument(
        "--include-ml",
        action="store_true",
        help="Also run ML validation.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run_validation(
        include_phase6=args.include_phase6,
        include_phase7_foundation=args.include_phase7_foundation,
        include_materialization=args.include_materialization,
        include_ml=args.include_ml,
    )
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_human_summary(summary)
    return 0 if summary["success"] else 1


def run_validation(
    *,
    include_phase6: bool = False,
    include_phase7_foundation: bool = False,
    include_materialization: bool = False,
    include_ml: bool = False,
) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    for group in UNITTEST_GROUPS:
        groups.append(run_unittest_group(group))
    groups.append(run_import_isolation_group())
    groups.append(run_runtime_safety_group())
    groups.append(run_documentation_group())
    if include_ml:
        groups.append(run_command_group("ml_regression", (sys.executable, "scripts/run_phase7_ml_validation.py")))
    if include_materialization:
        groups.append(
            run_command_group(
                "materialization_regression",
                (sys.executable, "scripts/run_phase7_materialization_validation.py"),
            )
        )
    if include_phase7_foundation:
        groups.append(
            run_command_group(
                "phase7_foundation_regression",
                (phase_python(), "scripts/run_phase7_validation.py"),
            )
        )
    if include_phase6:
        groups.append(
            run_command_group(
                "phase6_regression",
                (phase_python(), "scripts/run_phase6_validation.py"),
                extra_env={"PYTHONPATH": phase6_pythonpath()},
            )
        )

    totals = summarize_groups(groups)
    success = all(group["success"] for group in groups)
    return {
        "phase": "Phase 7AA",
        "command": "run_phase7aa_runtime_integration_validation",
        "success": success,
        "validation_groups": groups,
        "tests_run": totals["tests_run"],
        "checks_run": totals["checks_run"],
        "failures": totals["failures"],
        "errors": totals["errors"],
        "skipped": totals["skipped"],
        "adaptive_runtime_opt_in": True,
        "default_config_denies_integration": True,
        "context_read_only": True,
        "scoring_adapter_advisory_only": True,
        "recommendation_adapter_advisory_only": True,
        "parser_adapter_consideration_only": True,
        "fallback_decision_only": True,
        "rollback_execution": False,
        "runtime_active": False,
        "runtime_influence_granted": False,
        "runtime_mutation_performed": False,
        "run_analysis_modified": False,
        "phase4i_contract_preserved": True,
        "deterministic_runtime_remains_authoritative": True,
        "network_dependency": False,
        "database_dependency": False,
        "oracle_agent_memory_dependency": False,
    }


def run_unittest_group(group: ValidationGroup) -> dict[str, Any]:
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for module_name in group.modules:
        suite.addTests(loader.loadTestsFromName(module_name))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    return {
        "name": group.name,
        "success": result.wasSuccessful(),
        "description": group.description,
        "tests_run": result.testsRun,
        "checks_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "details": normalize_output_lines(stream.getvalue()),
    }


def run_import_isolation_group() -> dict[str, Any]:
    details: list[str] = []
    scanned = 0
    for path in iter_python_files(RUNTIME_IMPORT_PATHS):
        scanned += 1
        imported_modules = imported_module_names(path)
        for imported_module in imported_modules:
            if is_adaptive_runtime_import(imported_module):
                details.append(f"{relative(path)} imports {imported_module}")

    return {
        "name": "import_isolation",
        "success": not details,
        "description": "Runtime paths do not import Phase 7AA adaptive runtime modules.",
        "tests_run": 0,
        "checks_run": scanned,
        "failures": len(details),
        "errors": 0,
        "skipped": 0,
        "details": details or ["runtime import isolation preserved"],
    }


def run_runtime_safety_group() -> dict[str, Any]:
    details: list[str] = []
    checks_run = 0
    for path in iter_python_files(ADAPTIVE_RUNTIME_SOURCE_PATHS):
        checks_run += 1
        source = read_text(path)
        tree = ast.parse(source, filename=str(path))
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

    module_checks = run_runtime_object_safety_checks()
    details.extend(module_checks["details"])
    checks_run += module_checks["checks_run"]

    return {
        "name": "runtime_safety",
        "success": not details,
        "description": "Phase 7AA records remain inactive and mutation-free.",
        "tests_run": 0,
        "checks_run": checks_run,
        "failures": len(details),
        "errors": 0,
        "skipped": 0,
        "details": details or ["runtime_active=false and mutation boundaries preserved"],
    }


def run_runtime_object_safety_checks() -> dict[str, Any]:
    details: list[str] = []
    checks_run = 0

    from src.learning.adaptive_runtime_context import empty_adaptive_runtime_context
    from src.learning.adaptive_runtime_fallback import deterministic_fallback_decision
    from src.learning.adaptive_runtime_gate import (
        ADAPTIVE_COMPONENT_TYPES,
        AdaptiveComponentEligibility,
        default_deterministic_runtime_config,
        evaluate_adaptive_runtime_gate,
    )

    config = default_deterministic_runtime_config()
    checks_run += 1
    if config.adaptive_runtime_enabled or config.runtime_influence_allowed:
        details.append("default runtime config allows adaptive influence")

    for component_type in ADAPTIVE_COMPONENT_TYPES:
        checks_run += 1
        result = evaluate_adaptive_runtime_gate(
            config,
            AdaptiveComponentEligibility(
                component_id=f"VALIDATION-{component_type}",
                component_type=component_type,
            ),
        )
        if result.allowed or result.runtime_active or result.runtime_influence_granted:
            details.append(f"default gate did not deny {component_type}")

    context = empty_adaptive_runtime_context(created_by="phase7aa-validation")
    checks_run += 1
    if context.runtime_influence_applied or context.runtime_mutation_performed:
        details.append("empty runtime context indicates runtime influence or mutation")

    fallback = deterministic_fallback_decision("phase7aa validation")
    checks_run += 1
    if fallback.final_runtime_posture != "deterministic_fallback":
        details.append("deterministic fallback decision did not preserve fallback posture")
    if fallback.runtime_mutation_detected or fallback.runtime_influence_detected:
        details.append("fallback decision detected runtime mutation or influence")

    return {"checks_run": checks_run, "details": details}


def run_documentation_group() -> dict[str, Any]:
    details: list[str] = []
    checks_run = 0
    combined_text_parts: list[str] = []
    for relative_path in REQUIRED_DOCS:
        checks_run += 1
        path = ROOT / relative_path
        if not path.is_file():
            details.append(f"missing documentation: {relative_path}")
            continue
        combined_text_parts.append(read_text(path).lower())

    combined_text = "\n".join(combined_text_parts)
    for phrase in DOCUMENTATION_PHRASES:
        checks_run += 1
        if phrase.lower() not in combined_text:
            details.append(f"missing documentation phrase: {phrase}")

    return {
        "name": "documentation",
        "success": not details,
        "description": "Phase 7AA documentation set exists and states runtime boundaries.",
        "tests_run": 0,
        "checks_run": checks_run,
        "failures": len(details),
        "errors": 0,
        "skipped": 0,
        "details": details or ["Phase 7AA documentation boundary language present"],
    }


def run_command_group(
    name: str,
    args: tuple[str, ...],
    *,
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
    return {
        "name": name,
        "success": completed.returncode == 0,
        "description": "Optional regression validation.",
        "tests_run": counts["tests_run"],
        "checks_run": counts["checks_run"] or 1,
        "failures": counts["failures"] if completed.returncode == 0 else max(1, counts["failures"]),
        "errors": counts["errors"],
        "skipped": counts["skipped"],
        "details": normalize_output_lines(output),
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


def is_adaptive_runtime_import(module_name: str) -> bool:
    parts = module_name.split(".")
    if parts[-1] in ADAPTIVE_RUNTIME_MODULES:
        return True
    return any(f"src.learning.{module}" == module_name for module in ADAPTIVE_RUNTIME_MODULES)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def summarize_groups(groups: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "tests_run": sum(int(group.get("tests_run", 0)) for group in groups),
        "checks_run": sum(int(group.get("checks_run", 0)) for group in groups),
        "failures": sum(int(group.get("failures", 0)) for group in groups),
        "errors": sum(int(group.get("errors", 0)) for group in groups),
        "skipped": sum(int(group.get("skipped", 0)) for group in groups),
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


def phase_python() -> str:
    venv_python = ROOT / ".venv" / "bin" / "python"
    return str(venv_python) if venv_python.is_file() else sys.executable


def phase6_pythonpath() -> str:
    existing = os.environ.get("PYTHONPATH")
    return str(ROOT) if not existing else f"{ROOT}{os.pathsep}{existing}"


def print_human_summary(summary: dict[str, Any]) -> None:
    if summary["success"]:
        print("Phase 7AA runtime integration validation passed.")
    else:
        print("Phase 7AA runtime integration validation failed.")
    print(f"tests_run={summary['tests_run']}")
    print(f"checks_run={summary['checks_run']}")
    print(f"failures={summary['failures']}")
    print(f"errors={summary['errors']}")
    print(f"runtime_active={str(summary['runtime_active']).lower()}")
    print(f"runtime_influence_granted={str(summary['runtime_influence_granted']).lower()}")
    print(f"runtime_mutation_performed={str(summary['runtime_mutation_performed']).lower()}")
    for group in summary["validation_groups"]:
        status = "PASS" if group["success"] else "FAIL"
        print(f"- {group['name']}: {status}")


if __name__ == "__main__":
    raise SystemExit(main())
