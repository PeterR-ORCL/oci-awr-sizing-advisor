from __future__ import annotations

import ast
import importlib.util
import json
import os
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_phase7aa_runtime_integration_validation.py"
DOCS = ROOT / "docs" / "architecture"
VALIDATION_MATRIX = DOCS / "phase7aa_runtime_integration_validation_matrix.md"

REQUIRED_FIELDS = (
    "phase",
    "command",
    "success",
    "validation_groups",
    "tests_run",
    "checks_run",
    "failures",
    "errors",
    "skipped",
    "adaptive_runtime_opt_in",
    "default_config_denies_integration",
    "context_read_only",
    "scoring_adapter_advisory_only",
    "recommendation_adapter_advisory_only",
    "parser_adapter_consideration_only",
    "fallback_decision_only",
    "rollback_execution",
    "runtime_active",
    "runtime_influence_granted",
    "runtime_mutation_performed",
    "run_analysis_modified",
    "phase4i_contract_preserved",
    "deterministic_runtime_remains_authoritative",
    "network_dependency",
    "database_dependency",
    "oracle_agent_memory_dependency",
)

REQUIRED_GROUPS = (
    "runtime_gate",
    "adaptive_runtime_context",
    "scoring_integration_adapter",
    "recommendation_integration_adapter",
    "parser_integration_adapter",
    "runtime_fallback_rollback",
    "import_isolation",
    "runtime_safety",
    "documentation",
)

VALIDATION_PHRASES = (
    "adaptive runtime is opt-in only",
    "default config denies integration",
    "adapters are advisory/result-only",
    "fallback/rollback is decision-only",
    "no rollback execution",
    "no run_analysis.py integration",
    "no runtime mutation",
    "deterministic runtime remains authoritative",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_validation_module():
    spec = importlib.util.spec_from_file_location("phase7aa_validation", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load validation script module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, str(SCRIPT), *args),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


class Phase7AARuntimeIntegrationValidationTests(unittest.TestCase):
    def test_validation_script_exists_and_compiles(self) -> None:
        self.assertTrue(SCRIPT.is_file(), SCRIPT)
        with tempfile.TemporaryDirectory() as tempdir:
            py_compile.compile(
                str(SCRIPT),
                cfile=str(Path(tempdir) / "run_phase7aa_runtime_integration_validation.pyc"),
                doraise=True,
            )

    def test_validation_script_normal_output_returns_success(self) -> None:
        completed = run_script()
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("Phase 7AA runtime integration validation passed.", completed.stdout)

    def test_validation_script_json_returns_required_payload(self) -> None:
        completed = run_script("--json")
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        for field in REQUIRED_FIELDS:
            with self.subTest(field=field):
                self.assertIn(field, payload)
        self.assertEqual(payload["phase"], "Phase 7AA")
        self.assertEqual(payload["command"], "run_phase7aa_runtime_integration_validation")
        self.assertIs(payload["success"], True)

    def test_required_validation_groups_are_present(self) -> None:
        module = load_validation_module()
        group_names = {group.name for group in module.UNITTEST_GROUPS}
        group_names.update({"import_isolation", "runtime_safety", "documentation"})
        for group_name in REQUIRED_GROUPS:
            with self.subTest(group_name=group_name):
                self.assertIn(group_name, group_names)

    def test_json_runtime_safety_fields(self) -> None:
        completed = run_script("--json")
        payload = json.loads(completed.stdout)
        self.assertIs(payload["runtime_active"], False)
        self.assertIs(payload["runtime_influence_granted"], False)
        self.assertIs(payload["runtime_mutation_performed"], False)
        self.assertIs(payload["rollback_execution"], False)
        self.assertIs(payload["run_analysis_modified"], False)
        self.assertIs(payload["deterministic_runtime_remains_authoritative"], True)
        self.assertIs(payload["network_dependency"], False)
        self.assertIs(payload["database_dependency"], False)
        self.assertIs(payload["oracle_agent_memory_dependency"], False)

    def test_validation_script_has_no_unsafe_imports(self) -> None:
        source = read_text(SCRIPT)
        tree = ast.parse(source, filename=str(SCRIPT))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        for forbidden in ("oracledb", "requests", "socket", "urllib", "http.client", "httpx", "oci"):
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        module == forbidden or module.startswith(f"{forbidden}.")
                        for module in imports
                    )
                )
        self.assertNotIn("shell=True", source)

    def test_documentation_validation_matrix_exists_and_contains_phrases(self) -> None:
        self.assertTrue(VALIDATION_MATRIX.is_file(), VALIDATION_MATRIX)
        text = read_text(VALIDATION_MATRIX).lower()
        for phrase in VALIDATION_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
