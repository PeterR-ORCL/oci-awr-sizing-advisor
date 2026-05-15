from __future__ import annotations

import ast
import importlib
import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
BOUNDARY_DOC = DOCS / "phase7au_screen1_parser_governance_workflow_boundary.md"
LIFECYCLE_DOC = DOCS / "phase7au_screen1_ingestion_parser_lifecycle.md"
README = DOCS / "README.md"
MODULE_PATH = ROOT / "src" / "learning" / "screen1_parser_governance_boundary.py"

RUNTIME_IMPORT_PATHS = (
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

FORBIDDEN_BEHAVIOR_FILES = (
    "src/reporting/html_dashboard.py",
    "src/reporting/ai_display_metadata.py",
    "scripts/awr_memory_cli.py",
    "scripts/run_analysis.py",
)

PHASE7AW_ALLOWED_BEHAVIOR_FILE = "src/reporting/html_dashboard.py"
PHASE7AW_PREVIEW_ARTIFACT_FILES = {
    "docs/architecture/phase7aw_screen1_parser_unknown_review_panel.md",
    "tests/test_dashboard_screen1_parser_unknown_review_panel.py",
}

FORBIDDEN_MODULE_IMPORT_PREFIXES = (
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
    "src.reporting",
    "src.parser",
    "src.parsing",
    "src.scoring",
    "src.decision",
    "src.recommendation",
    "src.recommendations",
    "src.analysis",
    "src.memory",
    "scripts.awr_memory_cli",
    "scripts.run_analysis",
    "oracle_agent_memory",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def lower_text(path: Path) -> str:
    return read_text(path).lower()


def python_files(paths: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for relative_path in paths:
        path = ROOT / relative_path
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(child for child in path.rglob("*.py") if child.is_file()))
    return files


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def git_changed_paths(pathspecs: tuple[str, ...] = ()) -> set[str]:
    changed: set[str] = set()
    git_commands = (
        ("git", "diff", "--name-only"),
        ("git", "diff", "--cached", "--name-only"),
        ("git", "ls-files", "--others", "--exclude-standard"),
    )
    for base_command in git_commands:
        command = base_command + (("--",) + pathspecs if pathspecs else ())
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "git change scan unavailable")
        changed.update(
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        )
    return changed


def disallowed_behavior_changes(changed: set[str], all_changed: set[str]) -> set[str]:
    disallowed = set(changed)
    if (
        PHASE7AW_ALLOWED_BEHAVIOR_FILE in disallowed
        and PHASE7AW_PREVIEW_ARTIFACT_FILES.intersection(all_changed)
    ):
        disallowed.remove(PHASE7AW_ALLOWED_BEHAVIOR_FILE)
    return disallowed


class Phase7AUScreen1ParserGovernanceBoundaryTests(unittest.TestCase):
    def test_required_docs_exist(self) -> None:
        self.assertTrue(BOUNDARY_DOC.is_file(), BOUNDARY_DOC)
        self.assertTrue(LIFECYCLE_DOC.is_file(), LIFECYCLE_DOC)

    def test_boundary_doc_contains_required_sections(self) -> None:
        text = read_text(BOUNDARY_DOC)
        for section in (
            "## 1. Purpose",
            "## 2. Scope",
            "## 3. Non-Goals",
            "## 4. Why Screen 1 Needs Ingestion / Parser Governance Workflow",
            "## 5. Existing Screen 1 Read-Only Boundary",
            "## 6. Source Intake Boundary",
            "## 7. Local Source Boundary",
            "## 8. Object Storage Source Boundary",
            "## 9. Parser Unknown Review Boundary",
            "## 10. Parser Mapping Request Boundary",
            "## 11. Parser Backlog Boundary",
            "## 12. Knowledge Request Boundary",
            "## 13. Knowledge Artifact Boundary",
            "## 14. Artifact Materialization Boundary",
            "## 15. Actor Requirement",
            "## 16. Governed Write-Path Requirement",
            "## 17. Audit Requirement",
            "## 18. Backend Execution Mode Requirement",
            "## 19. Output Artifact Lifecycle Requirement",
            "## 20. Runtime Parser Boundary",
            "## 21. Phase 4I Contract Boundary",
            "## 22. Future Workflow Target Types",
            "## 23. Future Workflow Actions",
            "## 24. Future Workflow Statuses",
            "## 25. Relationship to 7AD-7AI",
            "## 26. Relationship to 7AK Source Selection",
            "## 27. Relationship to Future 7AV",
            "## 28. Relationship to Future 7AW",
            "## 29. Relationship to Future 7AX",
            "## 30. Relationship to Future 7AY",
            "## 31. Relationship to Phase 8 EM Extract",
            "## 32. Acceptance Criteria",
        ):
            with self.subTest(section=section):
                self.assertIn(section, text)

    def test_lifecycle_doc_contains_required_sections(self) -> None:
        text = read_text(LIFECYCLE_DOC)
        for section in (
            "## 1. Purpose",
            "## 2. Lifecycle Overview",
            "## 3. Read-Only Ingestion / Parser Visibility Stage",
            "## 4. Source Selection Stage",
            "## 5. Source Validation Stage",
            "## 6. Source Intake Request Stage",
            "## 7. Parser Unknown Review Stage",
            "## 8. Parser Mapping Request Stage",
            "## 9. Parser Backlog Linkage Stage",
            "## 10. Knowledge Artifact Review Stage",
            "## 11. Governed Write-Path Stage",
            "## 12. Audit Trail Stage",
            "## 13. Output Artifact Stage",
            "## 14. Closure Stage",
            "## 15. Forbidden Shortcuts",
            "## 16. Required Validation Evidence",
            "## 17. Acceptance Criteria",
        ):
            with self.subTest(section=section):
                self.assertIn(section, text)

    def test_boundary_doc_contains_required_phrases(self) -> None:
        text = lower_text(BOUNDARY_DOC)
        for phrase in (
            "boundary-only",
            "no screen 1 workflow ui is added",
            "no source intake is invoked",
            "no local files are read",
            "no object storage calls are made",
            "no db lookup is made",
            "no parser unknown classification is performed",
            "no parser mapping records are created",
            "no parser candidates are created",
            "no knowledge artifacts are approved/rejected",
            "no parser output is changed",
            "no phase 4i mutation is added",
            "future source actions require actor identity",
            "future parser review actions require governed write path",
            "future artifact workflows require audit trail",
            "phase 8 em extract implementation is not included",
            "phase 8 sizing/tco is not implemented",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_lifecycle_doc_contains_required_phrases(self) -> None:
        text = lower_text(LIFECYCLE_DOC)
        for phrase in (
            "no lifecycle stage is implemented in 7au",
            "source selection is not source intake",
            "source validation is not source loading",
            "unknown review is not parser mutation",
            "parser mapping request is not parser update",
            "artifact review is not materialization",
            "future workflows cannot skip actor",
            "future workflows cannot skip validation",
            "future workflows cannot skip audit",
            "future workflows cannot bypass governed write path",
            "parser runtime remains authoritative",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_future_workflow_targets_are_documented(self) -> None:
        text = lower_text(BOUNDARY_DOC) + "\n" + lower_text(LIFECYCLE_DOC)
        for target_type in (
            "source_intake",
            "local_source",
            "object_storage_source",
            "existing_run_source",
            "parser_unknown_signal",
            "parser_section",
            "parser_confidence",
            "parser_diagnostic",
            "parser_mapping_candidate",
            "parser_backlog_item",
            "knowledge_request",
            "knowledge_artifact",
            "artifact_materialization",
            "source_validation_result",
            "ingestion_run",
        ):
            with self.subTest(target_type=target_type):
                self.assertIn(target_type, text)

    def test_future_workflow_actions_are_documented(self) -> None:
        text = lower_text(BOUNDARY_DOC) + "\n" + lower_text(LIFECYCLE_DOC)
        for action in (
            "validate_source",
            "request_source_intake",
            "classify_unknown_signal",
            "mark_unknown_false_positive",
            "mark_unknown_not_applicable",
            "request_parser_mapping",
            "link_unknown_to_candidate",
            "link_unknown_to_backlog",
            "request_artifact_revision",
            "approve_artifact_for_review",
            "reject_artifact",
            "link_artifact_to_candidate",
            "add_parser_review_note",
        ):
            with self.subTest(action=action):
                self.assertIn(action, text)

    def test_future_workflow_statuses_are_documented(self) -> None:
        text = lower_text(BOUNDARY_DOC) + "\n" + lower_text(LIFECYCLE_DOC)
        for status in (
            "proposed",
            "under_review",
            "validated",
            "rejected",
            "needs_revision",
            "routed_to_governance",
            "linked_to_candidate",
            "linked_to_backlog",
            "closed",
        ):
            with self.subTest(status=status):
                self.assertIn(status, text)

    def test_optional_module_safety_and_boundary_summary(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), MODULE_PATH)
        before_environment = dict(os.environ)
        module = importlib.import_module("src.learning.screen1_parser_governance_boundary")
        self.assertEqual(before_environment, dict(os.environ))

        imports = imported_modules(MODULE_PATH)
        for forbidden in FORBIDDEN_MODULE_IMPORT_PREFIXES:
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        imported == forbidden or imported.startswith(f"{forbidden}.")
                        for imported in imports
                    )
                )

        summary = module.screen1_parser_governance_boundary_summary()
        self.assertTrue(summary["boundary_only"])
        self.assertEqual(
            summary["target_types"],
            list(module.SCREEN1_WORKFLOW_TARGET_TYPES),
        )
        self.assertEqual(summary["actions"], list(module.SCREEN1_WORKFLOW_ACTIONS))
        self.assertEqual(summary["statuses"], list(module.SCREEN1_WORKFLOW_STATUSES))
        self.assertEqual(
            summary["required_gates"],
            list(module.SCREEN1_WORKFLOW_REQUIRED_GATES),
        )
        self.assertFalse(summary["workflow_implemented"])
        self.assertFalse(summary["screen1_workflow_ui_added"])
        self.assertFalse(summary["source_intake_invoked"])
        self.assertFalse(summary["local_file_read_performed"])
        self.assertFalse(summary["object_storage_call_performed"])
        self.assertFalse(summary["db_lookup_performed"])
        self.assertFalse(summary["parser_unknown_classification_performed"])
        self.assertFalse(summary["parser_mapping_records_created"])
        self.assertFalse(summary["parser_candidates_created"])
        self.assertFalse(summary["knowledge_artifacts_approved_rejected"])
        self.assertFalse(summary["artifact_materialization_performed"])
        self.assertFalse(summary["governed_write_path_invoked"])
        self.assertFalse(summary["run_analysis_wiring_added"])
        self.assertFalse(summary["source_ingestion_behavior_changed"])
        self.assertFalse(summary["parser_behavior_changed"])
        self.assertFalse(summary["parser_output_changed"])
        self.assertFalse(summary["phase4i_mutation_added"])
        self.assertTrue(summary["deterministic_runtime_authoritative"])
        self.assertTrue(summary["parser_runtime_authoritative"])
        self.assertFalse(summary["phase8_em_extract_implemented"])
        self.assertFalse(summary["phase8_sizing_tco_implemented"])
        self.assertIn("no Screen 1 ingestion/parser governance workflow is implemented", summary["summary"])

        boundary = module.validate_screen1_parser_governance_boundary()
        self.assertIn("source_intake", boundary["target_types"])
        self.assertIn("parser_unknown_signal", boundary["target_types"])
        self.assertIn("validate_source", boundary["actions"])
        self.assertIn("request_parser_mapping", boundary["actions"])
        self.assertIn("proposed", boundary["statuses"])
        self.assertIn("actor identity", boundary["required_gates"])
        self.assertIn("governed write path", boundary["required_gates"])
        self.assertIn("audit trail", boundary["required_gates"])

        with self.assertRaises(module.Screen1ParserGovernanceBoundaryError):
            module.validate_screen1_parser_governance_boundary(mode="execution")

    def test_runtime_import_isolation(self) -> None:
        run_analysis_imports = imported_modules(ROOT / "scripts" / "run_analysis.py")
        for module_name in (
            "src.learning.screen1_parser_governance_boundary",
            "learning.screen1_parser_governance_boundary",
            "screen1_parser_governance_boundary",
        ):
            with self.subTest(module_name=module_name):
                self.assertNotIn(module_name, run_analysis_imports)

        for path in python_files(RUNTIME_IMPORT_PATHS):
            imports = imported_modules(path)
            source = read_text(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.screen1_parser_governance_boundary", imports)
                self.assertNotIn("learning.screen1_parser_governance_boundary", imports)
                self.assertNotIn("screen1_parser_governance_boundary", imports)
                self.assertNotIn("screen1_parser_governance_boundary", source)

    def test_behavior_files_are_not_modified_by_phase7au(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not available")
        if not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")

        try:
            all_changed = git_changed_paths()
            changed = git_changed_paths(FORBIDDEN_BEHAVIOR_FILES)
        except RuntimeError as exc:
            self.skipTest(str(exc))

        disallowed = disallowed_behavior_changes(changed, all_changed)
        self.assertFalse(disallowed, f"behavior files modified: {sorted(disallowed)}")

    def test_readme_links_new_docs(self) -> None:
        text = read_text(README)
        for title, filename in (
            (
                "Phase 7AU Screen 1 Ingestion / Parser Governance Workflow Boundary",
                "phase7au_screen1_parser_governance_workflow_boundary.md",
            ),
            (
                "Phase 7AU Screen 1 Ingestion / Parser Lifecycle",
                "phase7au_screen1_ingestion_parser_lifecycle.md",
            ),
        ):
            with self.subTest(title=title):
                self.assertIn(title, text)
                self.assertIn(filename, text)


if __name__ == "__main__":
    unittest.main()
