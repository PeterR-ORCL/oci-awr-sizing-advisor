from __future__ import annotations

import json
import py_compile
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_phase7_active_screen3_execution_validation.py"
DOCS = ROOT / "docs" / "architecture"

REQUIRED_GROUPS = (
    "governed_workflow_repository",
    "deterministic_execution",
    "comparison_execution",
    "object_storage_load_execution",
    "dashboard_output_refresh",
    "screen3_reanalysis_validation",
    "import_isolation",
    "runtime_safety",
    "object_storage_path_convention",
    "documentation",
)

REQUIRED_DOCS = (
    "phase7_active_screen3_execution_validation_matrix.md",
    "phase7_active_screen3_execution_readiness.md",
    "phase7_active_screen3_execution_release_certification.md",
    "phase7_active_screen3_execution_operational_checklist.md",
)


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (sys.executable, str(SCRIPT), *args),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


class Phase7ActiveScreen3ExecutionValidationTests(unittest.TestCase):
    _json_payload: dict[str, object] | None = None
    _text_result: subprocess.CompletedProcess[str] | None = None

    def test_validation_script_exists_and_compiles(self) -> None:
        self.assertTrue(SCRIPT.is_file(), SCRIPT)
        with tempfile.TemporaryDirectory() as tempdir:
            py_compile.compile(
                str(SCRIPT),
                cfile=str(Path(tempdir) / "run_phase7_active_screen3_execution_validation.pyc"),
                doraise=True,
            )

    def test_text_output_passes(self) -> None:
        completed = self.text_result()
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("Phase 7 active Screen 3 execution validation passed.", completed.stdout)
        self.assertIn("active_screen3_execution_ready=true", completed.stdout)

    def test_json_output_valid(self) -> None:
        payload = self.json_payload()
        self.assertEqual(payload["phase"], "Phase 7CA-7CF")
        self.assertEqual(
            payload["command"],
            "run_phase7_active_screen3_execution_validation",
        )
        self.assertIs(payload["success"], True)
        self.assertIs(payload["active_screen3_execution_ready"], True)

    def test_required_validation_groups_present(self) -> None:
        payload = self.json_payload()
        groups = {group["name"] for group in payload["validation_groups"]}  # type: ignore[index]
        for group in REQUIRED_GROUPS:
            with self.subTest(group=group):
                self.assertIn(group, groups)

    def test_certification_categories_exist_and_pass(self) -> None:
        payload = self.json_payload()
        self.assertIn("db_persistence_validated", payload)
        self.assertIs(payload["deterministic_execution_validated"], True)
        self.assertIs(payload["comparison_execution_validated"], True)
        self.assertIs(payload["object_storage_load_validated"], True)
        self.assertIs(payload["dashboard_output_refresh_validated"], True)
        self.assertIn("object_storage_live_validated", payload)

    def test_safety_flags_false(self) -> None:
        payload = self.json_payload()
        for field_name in (
            "run_analysis_direct_call",
            "subprocess_called",
            "adaptive_runtime_default",
            "phase4i_mutated",
            "dashboard_regenerated_by_default",
            "generated_dashboard_committed",
            "phase8_implemented",
        ):
            with self.subTest(field_name=field_name):
                self.assertIs(payload[field_name], False)
        self.assertIs(payload["deterministic_runtime_remains_authoritative"], True)

    def test_object_storage_path_convention_category_exists(self) -> None:
        payload = self.json_payload()
        groups = {group["name"]: group for group in payload["validation_groups"]}  # type: ignore[index]
        self.assertIn("object_storage_path_convention", groups)
        self.assertIs(groups["object_storage_path_convention"]["success"], True)

    def test_docs_exist(self) -> None:
        for doc_name in REQUIRED_DOCS:
            with self.subTest(doc_name=doc_name):
                self.assertTrue((DOCS / doc_name).is_file())

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
