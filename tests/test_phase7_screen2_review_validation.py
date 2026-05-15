"""Tests for Phase 7AP-7AT Screen 2 review validation."""

from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_phase7_screen2_review_validation.py"
DOCS = ROOT / "docs" / "architecture"

REQUIRED_GROUPS = (
    "review_boundary",
    "diagnostic_review_model",
    "governance_bridge",
    "review_panel",
    "diagnostic_exploration_regression",
    "import_isolation",
    "runtime_safety",
    "documentation",
)

REQUIRED_DOCS = (
    "phase7_screen2_review_validation_matrix.md",
    "phase7_screen2_review_readiness.md",
    "phase7_screen2_review_release_certification.md",
    "phase7_screen2_review_operational_checklist.md",
)


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, str(SCRIPT), *args),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


class Phase7Screen2ReviewValidationTests(unittest.TestCase):
    def test_validation_script_exists_and_compiles(self) -> None:
        self.assertTrue(SCRIPT.is_file(), SCRIPT)
        with tempfile.TemporaryDirectory() as tempdir:
            py_compile.compile(
                str(SCRIPT),
                cfile=str(Path(tempdir) / "run_phase7_screen2_review_validation.pyc"),
                doraise=True,
            )

    def test_text_output_passes(self) -> None:
        completed = run_script()
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("Phase 7 Screen 2 review validation passed.", completed.stdout)

    def test_json_output_valid(self) -> None:
        completed = run_script("--json")
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["phase"], "Phase 7AP-7AT")
        self.assertEqual(payload["command"], "run_phase7_screen2_review_validation")
        self.assertIs(payload["success"], True)
        self.assertIs(payload["screen2_review_ready"], True)

    def test_required_validation_groups_present(self) -> None:
        payload = json.loads(run_script("--json").stdout)
        groups = {group["name"] for group in payload["validation_groups"]}
        for group in REQUIRED_GROUPS:
            with self.subTest(group=group):
                self.assertIn(group, groups)

    def test_required_json_safety_flags(self) -> None:
        payload = json.loads(run_script("--json").stdout)
        self.assertIs(payload["review_panel_preview_only"], True)
        self.assertIs(payload["review_records_persisted"], False)
        self.assertIs(payload["governance_action_executed"], False)
        self.assertIs(payload["candidate_created"], False)
        self.assertIs(payload["diagnostic_truth_changed"], False)
        self.assertIs(payload["severity_changed"], False)
        self.assertIs(payload["confidence_changed"], False)
        self.assertIs(payload["score_changed"], False)
        self.assertIs(payload["parser_output_changed"], False)
        self.assertIs(payload["recommendation_truth_changed"], False)
        self.assertIs(payload["phase4i_mutated"], False)
        self.assertIs(payload["deterministic_runtime_remains_authoritative"], True)
        self.assertIs(payload["phase8_implemented"], False)

    def test_docs_exist(self) -> None:
        for doc_name in REQUIRED_DOCS:
            with self.subTest(doc_name=doc_name):
                self.assertTrue((DOCS / doc_name).is_file())


if __name__ == "__main__":
    unittest.main()
