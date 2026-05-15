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
BOUNDARY_DOC = DOCS / "phase7ap_screen2_review_workflow_boundary.md"
LIFECYCLE_DOC = DOCS / "phase7ap_screen2_review_lifecycle.md"
README = DOCS / "README.md"
MODULE_PATH = ROOT / "src" / "learning" / "screen2_review_boundary.py"

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


class Phase7APScreen2ReviewWorkflowBoundaryTests(unittest.TestCase):
    def test_required_docs_exist(self) -> None:
        self.assertTrue(BOUNDARY_DOC.is_file(), BOUNDARY_DOC)
        self.assertTrue(LIFECYCLE_DOC.is_file(), LIFECYCLE_DOC)

    def test_boundary_doc_contains_required_sections(self) -> None:
        text = read_text(BOUNDARY_DOC)
        for section in (
            "## 1. Purpose",
            "## 2. Scope",
            "## 3. Non-Goals",
            "## 4. Why Screen 2 Needs Review Workflow",
            "## 5. Existing Screen 2 Diagnostic Boundary",
            "## 6. Review Is Not Mutation",
            "## 7. Diagnostic Truth Boundary",
            "## 8. Evidence Review Boundary",
            "## 9. Actor Requirement",
            "## 10. Governed Write-Path Requirement",
            "## 11. Audit Requirement",
            "## 12. Phase 4I Contract Boundary",
            "## 13. Parser Review Request Boundary",
            "## 14. Scoring Review Request Boundary",
            "## 15. Recommendation Review Request Boundary",
            "## 16. Missing Metric / Evidence Availability Boundary",
            "## 17. Future Review Target Types",
            "## 18. Future Review Decisions",
            "## 19. Future Review Statuses",
            "## 20. Relationship to 7AD-7AI",
            "## 21. Relationship to Future 7AQ",
            "## 22. Relationship to Future 7AQ.1",
            "## 23. Relationship to Future 7AR",
            "## 24. Relationship to Future 7AS",
            "## 25. Relationship to Future 7AT",
            "## 26. Relationship to Phase 8",
            "## 27. Acceptance Criteria",
        ):
            with self.subTest(section=section):
                self.assertIn(section, text)

    def test_lifecycle_doc_contains_required_sections(self) -> None:
        text = read_text(LIFECYCLE_DOC)
        for section in (
            "## 1. Purpose",
            "## 2. Lifecycle Overview",
            "## 3. Read-Only Diagnostic Stage",
            "## 4. Review Target Selection Stage",
            "## 5. Actor Identification Stage",
            "## 6. Review Decision Stage",
            "## 7. Request Validation Stage",
            "## 8. Governed Write-Path Stage",
            "## 9. Governance Routing Stage",
            "## 10. Candidate Linkage Stage",
            "## 11. Audit Trail Stage",
            "## 12. Closure Stage",
            "## 13. Forbidden Shortcuts",
            "## 14. Required Validation Evidence",
            "## 15. Acceptance Criteria",
        ):
            with self.subTest(section=section):
                self.assertIn(section, text)

    def test_boundary_doc_contains_required_phrases(self) -> None:
        text = lower_text(BOUNDARY_DOC)
        for phrase in (
            "boundary-only",
            "no screen 2 approval ui is added",
            "no review records are created",
            "no backend write path is invoked",
            "no diagnostic truth is changed",
            "no severity is changed",
            "no confidence is changed",
            "no score is changed",
            "no parser output is changed",
            "no recommendation truth is changed",
            "no phase 4i mutation is added",
            "future review actions require actor identity",
            "future review actions require governed write path",
            "future review actions require audit trail",
            "missing metric/evidence review is future 7aq.1",
            "phase 8 sizing/tco is not implemented",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_lifecycle_doc_contains_required_phrases(self) -> None:
        text = lower_text(LIFECYCLE_DOC)
        for phrase in (
            "no lifecycle stage is implemented in 7ap",
            "review target selection is not mutation",
            "future review cannot skip actor",
            "future review cannot skip validation",
            "future review cannot skip audit",
            "future review cannot bypass governed write path",
            "future parser/scoring/recommendation review requests cannot mutate runtime",
            "missing evidence must be handled through future 7aq.1",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_future_review_target_types_are_documented(self) -> None:
        text = lower_text(BOUNDARY_DOC) + "\n" + lower_text(LIFECYCLE_DOC)
        for target_type in (
            "primary_issue",
            "secondary_issue",
            "severity",
            "confidence",
            "domain_score",
            "evidence_group",
            "metric_group",
            "wait_event_group",
            "sql_signal_group",
            "diagnostic_section",
            "parser_derived_evidence",
            "trend_reference",
            "anomaly_reference",
            "missing_metric",
            "unavailable_evidence",
            "recommendation_context",
        ):
            with self.subTest(target_type=target_type):
                self.assertIn(target_type, text)

    def test_future_review_decisions_are_documented(self) -> None:
        text = lower_text(BOUNDARY_DOC) + "\n" + lower_text(LIFECYCLE_DOC)
        for decision in (
            "confirm",
            "dispute",
            "insufficient_evidence",
            "needs_parser_review",
            "needs_scoring_review",
            "needs_recommendation_review",
            "needs_learning_candidate",
            "add_reviewer_note",
        ):
            with self.subTest(decision=decision):
                self.assertIn(decision, text)

    def test_future_review_statuses_are_documented(self) -> None:
        text = lower_text(BOUNDARY_DOC) + "\n" + lower_text(LIFECYCLE_DOC)
        for status in (
            "proposed",
            "under_review",
            "confirmed",
            "disputed",
            "insufficient_evidence",
            "needs_revision",
            "routed_to_governance",
            "closed",
        ):
            with self.subTest(status=status):
                self.assertIn(status, text)

    def test_optional_module_safety_and_boundary_summary(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), MODULE_PATH)
        before_environment = dict(os.environ)
        module = importlib.import_module("src.learning.screen2_review_boundary")
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

        summary = module.screen2_review_boundary_summary()
        self.assertTrue(summary["boundary_only"])
        self.assertEqual(summary["target_types"], list(module.SCREEN2_REVIEW_TARGET_TYPES))
        self.assertEqual(summary["decisions"], list(module.SCREEN2_REVIEW_DECISIONS))
        self.assertEqual(summary["statuses"], list(module.SCREEN2_REVIEW_STATUSES))
        self.assertEqual(summary["required_gates"], list(module.SCREEN2_REVIEW_REQUIRED_GATES))
        self.assertFalse(summary["review_workflow_implemented"])
        self.assertFalse(summary["screen2_approval_ui_added"])
        self.assertFalse(summary["review_panel_ui_added"])
        self.assertFalse(summary["dashboard_write_controls_added"])
        self.assertFalse(summary["review_records_created"])
        self.assertFalse(summary["evidence_review_records_created"])
        self.assertFalse(summary["governance_records_created"])
        self.assertFalse(summary["learning_candidates_created"])
        self.assertFalse(summary["backend_write_path_invoked"])
        self.assertFalse(summary["backend_calls_added"])
        self.assertFalse(summary["run_analysis_wiring_added"])
        self.assertFalse(summary["diagnostic_truth_changed"])
        self.assertFalse(summary["severity_changed"])
        self.assertFalse(summary["confidence_changed"])
        self.assertFalse(summary["score_changed"])
        self.assertFalse(summary["evidence_changed"])
        self.assertFalse(summary["parser_output_changed"])
        self.assertFalse(summary["recommendation_truth_changed"])
        self.assertFalse(summary["phase4i_mutation_added"])
        self.assertTrue(summary["deterministic_runtime_authoritative"])
        self.assertEqual(summary["missing_metric_evidence_review_future_phase"], "7AQ.1")
        self.assertFalse(summary["phase8_sizing_tco_implemented"])
        self.assertIn("no review workflow is implemented", summary["summary"])

        boundary = module.validate_screen2_review_boundary()
        self.assertIn("primary_issue", boundary["target_types"])
        self.assertIn("confirm", boundary["decisions"])
        self.assertIn("proposed", boundary["statuses"])
        self.assertIn("actor identity", boundary["required_gates"])
        self.assertIn("governed write path", boundary["required_gates"])
        self.assertIn("audit trail", boundary["required_gates"])

        with self.assertRaises(module.Screen2ReviewBoundaryError):
            module.validate_screen2_review_boundary(mode="execution")

    def test_runtime_import_isolation(self) -> None:
        run_analysis_imports = imported_modules(ROOT / "scripts" / "run_analysis.py")
        for module_name in (
            "src.learning.screen2_review_boundary",
            "learning.screen2_review_boundary",
            "screen2_review_boundary",
        ):
            with self.subTest(module_name=module_name):
                self.assertNotIn(module_name, run_analysis_imports)

        for path in python_files(RUNTIME_IMPORT_PATHS):
            imports = imported_modules(path)
            source = read_text(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.screen2_review_boundary", imports)
                self.assertNotIn("learning.screen2_review_boundary", imports)
                self.assertNotIn("screen2_review_boundary", imports)
                self.assertNotIn("screen2_review_boundary", source)

    def test_behavior_files_are_not_modified_by_phase7ap(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not available")
        if not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")

        completed = subprocess.run(
            ("git", "diff", "--name-only", "--", *FORBIDDEN_BEHAVIOR_FILES),
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            self.skipTest(completed.stderr.strip() or "git diff unavailable")

        changed = {
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        }
        self.assertFalse(changed, f"behavior files modified: {sorted(changed)}")

    def test_readme_links_new_docs(self) -> None:
        text = read_text(README)
        for title, filename in (
            (
                "Phase 7AP Screen 2 Review Workflow Boundary",
                "phase7ap_screen2_review_workflow_boundary.md",
            ),
            (
                "Phase 7AP Screen 2 Review Lifecycle",
                "phase7ap_screen2_review_lifecycle.md",
            ),
        ):
            with self.subTest(title=title):
                self.assertIn(title, text)
                self.assertIn(filename, text)


if __name__ == "__main__":
    unittest.main()
