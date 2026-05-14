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
SCRIPT = ROOT / "scripts" / "run_phase7aa_runtime_integration_readiness_check.py"
DOCS = ROOT / "docs" / "architecture"
README = DOCS / "README.md"
SELFTEST = os.environ.get("PHASE7AA_READINESS_SELFTEST") == "1"

READINESS_DOC = DOCS / "phase7aa_runtime_integration_readiness.md"
RELEASE_DOC = DOCS / "phase7aa_runtime_integration_release_certification.md"
CHECKLIST_DOC = DOCS / "phase7aa_runtime_integration_operational_checklist.md"

REQUIRED_CATEGORIES = (
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_readiness_module():
    spec = importlib.util.spec_from_file_location("phase7aa_readiness", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load readiness script module")
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


class Phase7AARuntimeIntegrationReadinessTests(unittest.TestCase):
    def test_readiness_script_exists_and_compiles(self) -> None:
        self.assertTrue(SCRIPT.is_file(), SCRIPT)
        with tempfile.TemporaryDirectory() as tempdir:
            py_compile.compile(
                str(SCRIPT),
                cfile=str(Path(tempdir) / "run_phase7aa_runtime_integration_readiness_check.pyc"),
                doraise=True,
            )

    @unittest.skipIf(SELFTEST, "avoid recursive readiness checker subprocess calls")
    def test_readiness_script_normal_output_returns_success(self) -> None:
        completed = run_script()
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("Phase 7AA runtime integration readiness passed.", completed.stdout)
        self.assertIn("runtime_integration_ready=true", completed.stdout)

    @unittest.skipIf(SELFTEST, "avoid recursive readiness checker subprocess calls")
    def test_readiness_script_json_returns_required_payload(self) -> None:
        completed = run_script("--json")
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertIs(payload["success"], True)
        self.assertIs(payload["runtime_integration_ready"], True)
        self.assertEqual(payload["phase"], "Phase 7AA")
        self.assertEqual(payload["command"], "run_phase7aa_runtime_integration_readiness_check")
        for category in REQUIRED_CATEGORIES:
            with self.subTest(category=category):
                self.assertIn(category, payload["readiness_categories"])
        self.assertIs(payload["runtime_active"], False)
        self.assertIs(payload["runtime_influence_granted"], False)
        self.assertIs(payload["runtime_mutation_performed"], False)
        self.assertIs(payload["deterministic_runtime_remains_authoritative"], True)

    def test_required_readiness_categories_are_declared(self) -> None:
        module = load_readiness_module()
        categories = set(module.READINESS_CATEGORY_KEYS)
        for category in REQUIRED_CATEGORIES:
            with self.subTest(category=category):
                self.assertIn(category, categories)

    def test_readiness_and_certification_docs_exist(self) -> None:
        for path in (READINESS_DOC, RELEASE_DOC, CHECKLIST_DOC):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), path)

    def test_readiness_docs_contain_required_language(self) -> None:
        text = "\n".join(read_text(path).lower() for path in (READINESS_DOC, RELEASE_DOC, CHECKLIST_DOC))
        for phrase in (
            "runtime_integration_ready=true only when all checks pass",
            "7aa does not activate adaptive runtime",
            "deterministic runtime remains authoritative",
            "run_analysis.py remains untouched",
            "phase 8 is not implemented",
            "7aa is certified as controlled integration scaffolding only",
            "no adaptive runtime activation is certified",
            "no run_analysis.py integration is certified",
            "no runtime scoring/recommendation/parser replacement is certified",
            "future 7ab/7ac remain required",
            "do not certify if validation fails",
            "do not bypass runtime isolation boundaries",
            "do not wire run_analysis.py until explicitly scoped",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_readme_links_new_readiness_and_certification_docs(self) -> None:
        text = read_text(README)
        for title, filename in (
            (
                "Phase 7AA Runtime Integration Validation Matrix",
                "phase7aa_runtime_integration_validation_matrix.md",
            ),
            (
                "Phase 7AA Runtime Integration Readiness",
                "phase7aa_runtime_integration_readiness.md",
            ),
            (
                "Phase 7AA Runtime Integration Release Certification",
                "phase7aa_runtime_integration_release_certification.md",
            ),
            (
                "Phase 7AA Runtime Integration Operational Checklist",
                "phase7aa_runtime_integration_operational_checklist.md",
            ),
        ):
            with self.subTest(title=title):
                self.assertIn(title, text)
                self.assertIn(filename, text)

    def test_readiness_script_has_no_unsafe_imports(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
