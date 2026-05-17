from __future__ import annotations

import ast
import json
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_phase7_active_screen3_execution_readiness_check.py"
VALIDATION_SCRIPT = ROOT / "scripts" / "run_phase7_active_screen3_execution_validation.py"
README = ROOT / "docs" / "architecture" / "README.md"

REQUIRED_CATEGORIES = (
    "governed_workflow_repository",
    "deterministic_execution",
    "comparison_execution",
    "object_storage_load_execution",
    "dashboard_output_refresh",
    "screen3_reanalysis_validation",
    "runtime_isolation",
    "documentation_complete",
    "phase7_regression",
    "phase6_regression",
    "live_object_storage",
)

README_LINKS = (
    "phase7_active_screen3_execution_validation_matrix.md",
    "phase7_active_screen3_execution_readiness.md",
    "phase7_active_screen3_execution_release_certification.md",
    "phase7_active_screen3_execution_operational_checklist.md",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "subprocess",
    "requests",
    "httpx",
    "urllib",
    "socket",
    "http.client",
    "oci",
    "oracledb",
    "cx_Oracle",
    "sqlite3",
)


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, str(SCRIPT), *args),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


class Phase7ActiveScreen3ExecutionReadinessTests(unittest.TestCase):
    _json_payload: dict[str, object] | None = None
    _text_result: subprocess.CompletedProcess[str] | None = None

    def test_readiness_script_exists_and_compiles(self) -> None:
        self.assertTrue(SCRIPT.is_file(), SCRIPT)
        with tempfile.TemporaryDirectory() as tempdir:
            py_compile.compile(
                str(SCRIPT),
                cfile=str(Path(tempdir) / "run_phase7_active_screen3_execution_readiness_check.pyc"),
                doraise=True,
            )

    def test_text_output_passes(self) -> None:
        completed = self.text_result()
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("Phase 7 active Screen 3 execution readiness passed.", completed.stdout)
        self.assertIn("active_screen3_execution_ready=true", completed.stdout)

    def test_json_output_valid(self) -> None:
        payload = self.json_payload()
        self.assertEqual(payload["phase"], "Phase 7CA-7CF")
        self.assertEqual(
            payload["command"],
            "run_phase7_active_screen3_execution_readiness_check",
        )
        self.assertIs(payload["success"], True)
        self.assertIs(payload["active_screen3_execution_ready"], True)

    def test_readiness_categories_present(self) -> None:
        categories = self.json_payload()["readiness_categories"]  # type: ignore[index]
        for category in REQUIRED_CATEGORIES:
            with self.subTest(category=category):
                self.assertIn(category, categories)

    def test_required_readiness_categories_pass(self) -> None:
        categories = self.json_payload()["readiness_categories"]  # type: ignore[index]
        for category in (
            "governed_workflow_repository",
            "deterministic_execution",
            "comparison_execution",
            "object_storage_load_execution",
            "dashboard_output_refresh",
            "screen3_reanalysis_validation",
            "runtime_isolation",
            "documentation_complete",
        ):
            with self.subTest(category=category):
                self.assertIs(categories[category], True)

    def test_safety_flags_false(self) -> None:
        payload = self.json_payload()
        self.assertIs(payload["run_analysis_direct_call"], False)
        self.assertIs(payload["subprocess_called"], False)
        self.assertIs(payload["phase4i_mutated"], False)
        self.assertIs(payload["phase8_implemented"], False)
        self.assertIs(payload["deterministic_runtime_remains_authoritative"], True)

    def test_readme_links_docs(self) -> None:
        text = README.read_text(encoding="utf-8")
        for link in README_LINKS:
            with self.subTest(link=link):
                self.assertIn(link, text)

    def test_no_unsafe_imports_in_scripts(self) -> None:
        for path in (SCRIPT, VALIDATION_SCRIPT):
            imports = imported_modules(path)
            for forbidden in FORBIDDEN_IMPORT_PREFIXES:
                with self.subTest(path=path.name, forbidden=forbidden):
                    self.assertFalse(
                        any(
                            imported == forbidden
                            or imported.startswith(f"{forbidden}.")
                            for imported in imports
                        )
                    )

    @classmethod
    def json_payload(cls) -> dict[str, object]:
        if cls._json_payload is None:
            completed = run_script("--json")
            if completed.returncode != 0:
                raise AssertionError(completed.stderr or completed.stdout)
            cls._json_payload = json.loads(completed.stdout)
        return cls._json_payload

    @classmethod
    def text_result(cls) -> subprocess.CompletedProcess[str]:
        if cls._text_result is None:
            cls._text_result = run_script()
        return cls._text_result


if __name__ == "__main__":
    unittest.main()
