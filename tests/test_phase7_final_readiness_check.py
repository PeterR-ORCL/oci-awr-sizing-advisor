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
SCRIPT = ROOT / "scripts" / "run_phase7_final_readiness_check.py"
DOCS = ROOT / "docs" / "architecture"
README = DOCS / "README.md"

FINAL_READINESS_DOC = DOCS / "phase7_final_readiness.md"
FINAL_RELEASE_DOC = DOCS / "phase7_final_release_certification.md"
FINAL_CHECKLIST_DOC = DOCS / "phase7_final_operational_checklist.md"
FINAL_MATRIX_DOC = DOCS / "phase7_final_validation_matrix.md"

REQUIRED_CATEGORIES = (
    "learning_foundation",
    "controlled_materialization",
    "ml_adaptive_scoring",
    "controlled_runtime_integration",
    "dashboard_cli_visibility",
    "runtime_isolation",
    "phase4i_contract_protected",
    "documentation_complete",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_readiness_module():
    spec = importlib.util.spec_from_file_location("phase7_final_readiness", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("could not load final readiness script module")
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


class Phase7FinalReadinessCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        completed = run_script("--json")
        if completed.returncode != 0:
            raise AssertionError(completed.stderr or completed.stdout)
        cls.json_payload = json.loads(completed.stdout)

    def test_final_readiness_script_exists_and_compiles(self) -> None:
        self.assertTrue(SCRIPT.is_file(), SCRIPT)
        with tempfile.TemporaryDirectory() as tempdir:
            py_compile.compile(
                str(SCRIPT),
                cfile=str(Path(tempdir) / "run_phase7_final_readiness_check.pyc"),
                doraise=True,
            )

    def test_final_readiness_script_normal_output_returns_success(self) -> None:
        completed = run_script()
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("Phase 7 final readiness passed.", completed.stdout)
        self.assertIn("phase7_final_ready=true", completed.stdout)

    def test_final_readiness_script_json_returns_valid_json(self) -> None:
        payload = self.json_payload
        self.assertIs(payload["success"], True)
        self.assertIs(payload["phase7_final_ready"], True)
        self.assertEqual(payload["phase"], "Phase 7")
        self.assertEqual(payload["command"], "run_phase7_final_readiness_check")

    def test_required_readiness_categories_are_present(self) -> None:
        payload = self.json_payload
        for category in REQUIRED_CATEGORIES:
            with self.subTest(category=category):
                self.assertIn(category, payload["readiness_categories"])
                self.assertIs(payload["readiness_categories"][category], True)

    def test_final_readiness_flags_are_safe(self) -> None:
        payload = self.json_payload
        self.assertIs(payload["deterministic_runtime_remains_authoritative"], True)
        self.assertIs(payload["adaptive_runtime_active"], False)
        self.assertIs(payload["runtime_active"], False)
        self.assertIs(payload["runtime_influence_granted"], False)
        self.assertIs(payload["runtime_mutation_performed"], False)
        self.assertIs(payload["run_analysis_integrated"], False)
        self.assertIs(payload["phase8_implemented"], False)

    def test_final_readiness_docs_exist(self) -> None:
        self.assertTrue(FINAL_READINESS_DOC.is_file(), FINAL_READINESS_DOC)

    def test_final_release_certification_docs_exist(self) -> None:
        self.assertTrue(FINAL_RELEASE_DOC.is_file(), FINAL_RELEASE_DOC)

    def test_final_operational_checklist_docs_exist(self) -> None:
        self.assertTrue(FINAL_CHECKLIST_DOC.is_file(), FINAL_CHECKLIST_DOC)

    def test_final_validation_matrix_exists(self) -> None:
        self.assertTrue(FINAL_MATRIX_DOC.is_file(), FINAL_MATRIX_DOC)

    def test_final_docs_contain_required_boundary_language(self) -> None:
        text = "\n".join(
            read_text(path).lower()
            for path in (
                FINAL_READINESS_DOC,
                FINAL_RELEASE_DOC,
                FINAL_CHECKLIST_DOC,
                FINAL_MATRIX_DOC,
            )
        )
        for phrase in (
            "phase 7 final readiness does not mean adaptive runtime is active.",
            "adaptive runtime remains gated.",
            "deterministic runtime remains authoritative.",
            "phase 8 is not implemented.",
            "phase 7 is certified as governed adaptive intelligence with controlled runtime integration scaffolding.",
            "phase 7 is not certified as fully active autonomous runtime mutation.",
            "adaptive runtime is not enabled by default.",
            "phase 8 sizing/tco is not certified here.",
            "readiness validates safety, not activation.",
            "no runtime activation occurs.",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_readme_links_final_phase7_docs(self) -> None:
        text = read_text(README)
        for title, filename in (
            ("Phase 7 Final Readiness", "phase7_final_readiness.md"),
            (
                "Phase 7 Final Release Certification",
                "phase7_final_release_certification.md",
            ),
            (
                "Phase 7 Final Operational Checklist",
                "phase7_final_operational_checklist.md",
            ),
            ("Phase 7 Final Validation Matrix", "phase7_final_validation_matrix.md"),
        ):
            with self.subTest(title=title):
                self.assertIn(title, text)
                self.assertIn(filename, text)

    def test_required_readiness_categories_are_declared(self) -> None:
        module = load_readiness_module()
        categories = set(module.READINESS_CATEGORY_KEYS)
        for category in REQUIRED_CATEGORIES:
            with self.subTest(category=category):
                self.assertIn(category, categories)

    def test_final_readiness_script_has_no_unsafe_imports(self) -> None:
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

    def test_final_readiness_has_no_db_network_oci_dependencies(self) -> None:
        payload = self.json_payload
        self.assertIs(payload["network_dependency"], False)
        self.assertIs(payload["database_dependency"], False)
        self.assertIs(payload["oracle_agent_memory_dependency"], False)


if __name__ == "__main__":
    unittest.main()
