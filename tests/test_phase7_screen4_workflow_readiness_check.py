"""Tests for Phase 7AZ-7BD Screen 4 workflow readiness checks."""

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
SCRIPT = ROOT / "scripts" / "run_phase7_screen4_workflow_readiness_check.py"
README = ROOT / "docs" / "architecture" / "README.md"

REQUIRED_CATEGORIES = (
    "workflow_boundary",
    "baseline_selection",
    "trend_anomaly_review",
    "historical_learning_bridge",
    "historical_review_panel",
    "historical_execution_metadata",
    "historical_review_exploration_regression",
    "runtime_isolation",
    "documentation_complete",
    "phase7_regression",
    "phase6_regression",
)

README_LINKS = (
    "phase7_screen4_workflow_validation_matrix.md",
    "phase7_screen4_workflow_readiness.md",
    "phase7_screen4_workflow_release_certification.md",
    "phase7_screen4_workflow_operational_checklist.md",
)

FORBIDDEN_IMPORTS = (
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, str(SCRIPT), *args),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


class Phase7Screen4WorkflowReadinessCheckTests(unittest.TestCase):
    def test_readiness_script_exists_and_compiles(self) -> None:
        self.assertTrue(SCRIPT.is_file(), SCRIPT)
        with tempfile.TemporaryDirectory() as tempdir:
            py_compile.compile(
                str(SCRIPT),
                cfile=str(
                    Path(tempdir) / "run_phase7_screen4_workflow_readiness_check.pyc"
                ),
                doraise=True,
            )

    def test_text_output_passes(self) -> None:
        completed = run_script()
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("Phase 7 Screen 4 workflow readiness passed.", completed.stdout)
        self.assertIn("screen4_workflow_ready=true", completed.stdout)

    def test_json_output_valid(self) -> None:
        completed = run_script("--json")
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["phase"], "Phase 7AZ-7BD")
        self.assertEqual(payload["command"], "run_phase7_screen4_workflow_readiness_check")
        self.assertIs(payload["success"], True)
        self.assertIs(payload["screen4_workflow_ready"], True)

    def test_readiness_categories_present(self) -> None:
        payload = json.loads(run_script("--json").stdout)
        categories = payload["readiness_categories"]
        for category in REQUIRED_CATEGORIES:
            with self.subTest(category=category):
                self.assertIn(category, categories)
        self.assertIs(categories["phase7_regression"], None)
        self.assertIs(categories["phase6_regression"], None)

    def test_required_json_safety_flags(self) -> None:
        payload = json.loads(run_script("--json").stdout)
        self.assertIs(payload["screen4_workflow_ready"], True)
        self.assertIs(payload["baseline_official"], False)
        self.assertIs(payload["candidate_created"], False)
        self.assertIs(payload["dataset_label_created"], False)
        self.assertIs(payload["historical_truth_changed"], False)
        self.assertIs(payload["trend_truth_changed"], False)
        self.assertIs(payload["anomaly_truth_changed"], False)
        self.assertIs(payload["scoring_changed"], False)
        self.assertIs(payload["phase4i_mutated"], False)
        self.assertIs(payload["deterministic_runtime_remains_authoritative"], True)

    def test_readme_links_docs(self) -> None:
        text = read_text(README)
        for link in README_LINKS:
            with self.subTest(link=link):
                self.assertIn(link, text)

    def test_no_unsafe_imports(self) -> None:
        imports = imported_modules(SCRIPT)
        for forbidden in FORBIDDEN_IMPORTS:
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        imported == forbidden or imported.startswith(f"{forbidden}.")
                        for imported in imports
                    ),
                    f"unsafe import found: {forbidden}",
                )


if __name__ == "__main__":
    unittest.main()
