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
BOUNDARY_DOC = DOCS / "phase7bk_screen6_governance_control_boundary.md"
LIFECYCLE_DOC = DOCS / "phase7bk_screen6_governance_control_lifecycle.md"
README = DOCS / "README.md"
MODULE_PATH = ROOT / "src" / "learning" / "screen6_governance_control_boundary.py"

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


class Phase7BKScreen6GovernanceControlBoundaryTests(unittest.TestCase):
    def test_required_docs_exist(self) -> None:
        self.assertTrue(BOUNDARY_DOC.is_file(), BOUNDARY_DOC)
        self.assertTrue(LIFECYCLE_DOC.is_file(), LIFECYCLE_DOC)

    def test_boundary_doc_contains_required_sections(self) -> None:
        text = read_text(BOUNDARY_DOC)
        for section in (
            "## 1. Purpose",
            "## 2. Scope",
            "## 3. Non-Goals",
            "## 4. Why Screen 6 Needs Governance Control Plane",
            "## 5. Existing Screen 6 Read-Only Boundary",
            "## 6. Governance Control Is Not Runtime Activation",
            "## 7. Candidate Review Boundary",
            "## 8. Materialization Review Boundary",
            "## 9. Model Registry Review Boundary",
            "## 10. Runtime Gate Review Boundary",
            "## 11. Unknown Signal / Knowledge Artifact Boundary",
            "## 12. Actor Requirement",
            "## 13. Governed Write-Path Requirement",
            "## 14. Audit Requirement",
            "## 15. Output Artifact Lifecycle Requirement",
            "## 16. Runtime Activation Boundary",
            "## 17. Phase 4I Contract Boundary",
            "## 18. Future Governance Target Types",
            "## 19. Future Governance Actions",
            "## 20. Future Governance Statuses",
            "## 21. Relationship to 7AD-7AI",
            "## 22. Relationship to 7AA-7AC",
            "## 23. Relationship to 7M-7R",
            "## 24. Relationship to 7S-7Z",
            "## 25. Relationship to Future 7BL",
            "## 26. Relationship to Future 7BM",
            "## 27. Relationship to Future 7BN",
            "## 28. Relationship to Future 7BO",
            "## 29. Relationship to Future 7BP",
            "## 30. Relationship to Phase 8",
            "## 31. Acceptance Criteria",
        ):
            with self.subTest(section=section):
                self.assertIn(section, text)

    def test_lifecycle_doc_contains_required_sections(self) -> None:
        text = read_text(LIFECYCLE_DOC)
        for section in (
            "## 1. Purpose",
            "## 2. Lifecycle Overview",
            "## 3. Read-Only Governance Visibility Stage",
            "## 4. Governance Target Selection Stage",
            "## 5. Actor Identification Stage",
            "## 6. Governance Action Request Stage",
            "## 7. Governed Write-Path Validation Stage",
            "## 8. Materialization / Model / Runtime Gate Review Stage",
            "## 9. Output Artifact Stage",
            "## 10. Audit Trail Stage",
            "## 11. Closure Stage",
            "## 12. Forbidden Shortcuts",
            "## 13. Required Validation Evidence",
            "## 14. Acceptance Criteria",
        ):
            with self.subTest(section=section):
                self.assertIn(section, text)

    def test_boundary_doc_contains_required_phrases(self) -> None:
        text = lower_text(BOUNDARY_DOC)
        for phrase in (
            "boundary-only",
            "no screen 6 governance controls are added",
            "no approval controls are added",
            "no governance records are persisted",
            "no candidate status is changed",
            "no materialization status is changed",
            "no model registry status is changed",
            "no runtime gate state is changed",
            "no runtime activation occurs",
            "no parser/scoring/decision/recommendation behavior changes are added",
            "no phase 4i mutation is added",
            "future governance actions require actor identity",
            "future governance actions require governed write path",
            "future governance actions require audit trail",
            "phase 8 sizing/tco is not implemented",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_lifecycle_doc_contains_required_phrases(self) -> None:
        text = lower_text(LIFECYCLE_DOC)
        for phrase in (
            "no lifecycle stage is implemented in 7bk",
            "governance target selection is not status mutation",
            "candidate review is not candidate activation",
            "materialization review is not runtime activation",
            "model registry review is not model deployment",
            "runtime gate review is not adaptive runtime activation",
            "future workflows cannot skip actor",
            "future workflows cannot skip validation",
            "future workflows cannot skip audit",
            "future workflows cannot bypass governed write path",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_future_governance_target_types_are_documented(self) -> None:
        text = lower_text(BOUNDARY_DOC) + "\n" + lower_text(LIFECYCLE_DOC)
        for target_type in (
            "learning_candidate",
            "materialization_artifact",
            "parser_mapping_candidate",
            "scoring_review_candidate",
            "recommendation_rule_candidate",
            "dashboard_wording_candidate",
            "semantic_summary_candidate",
            "validation_candidate",
            "documentation_candidate",
            "governance_workflow_candidate",
            "unknown_signal",
            "knowledge_request",
            "knowledge_artifact",
            "model_registry_entry",
            "model_eligibility_record",
            "runtime_gate",
            "adaptive_runtime_context",
            "fallback_decision",
            "governance_item",
        ):
            with self.subTest(target_type=target_type):
                self.assertIn(target_type, text)

    def test_future_governance_actions_are_documented(self) -> None:
        text = lower_text(BOUNDARY_DOC) + "\n" + lower_text(LIFECYCLE_DOC)
        for action in (
            "mark_under_review",
            "approve_for_implementation",
            "reject",
            "request_revision",
            "attach_materialization_reference",
            "approve_for_validation",
            "mark_implemented",
            "mark_validated",
            "approve_for_shadow",
            "request_runtime_review",
            "review_runtime_gate",
            "close_governance_item",
            "add_governance_note",
        ):
            with self.subTest(action=action):
                self.assertIn(action, text)

    def test_future_governance_statuses_are_documented(self) -> None:
        text = lower_text(BOUNDARY_DOC) + "\n" + lower_text(LIFECYCLE_DOC)
        for status in (
            "proposed",
            "under_review",
            "approved_for_implementation",
            "approved_for_validation",
            "implemented",
            "validated",
            "needs_revision",
            "rejected",
            "closed",
            "retired",
            "superseded",
        ):
            with self.subTest(status=status):
                self.assertIn(status, text)

    def test_optional_module_safety_and_boundary_summary(self) -> None:
        self.assertTrue(MODULE_PATH.is_file(), MODULE_PATH)
        before_environment = dict(os.environ)
        module = importlib.import_module("src.learning.screen6_governance_control_boundary")
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

        summary = module.screen6_governance_control_boundary_summary()
        self.assertTrue(summary["boundary_only"])
        self.assertEqual(
            summary["target_types"],
            list(module.SCREEN6_GOVERNANCE_TARGET_TYPES),
        )
        self.assertEqual(summary["actions"], list(module.SCREEN6_GOVERNANCE_ACTIONS))
        self.assertEqual(summary["statuses"], list(module.SCREEN6_GOVERNANCE_STATUSES))
        self.assertEqual(
            summary["required_gates"],
            list(module.SCREEN6_GOVERNANCE_REQUIRED_GATES),
        )
        self.assertFalse(summary["workflow_implemented"])
        self.assertFalse(summary["screen6_governance_controls_added"])
        self.assertFalse(summary["approval_controls_added"])
        self.assertFalse(summary["governance_records_persisted"])
        self.assertFalse(summary["candidate_status_changed"])
        self.assertFalse(summary["materialization_status_changed"])
        self.assertFalse(summary["model_registry_status_changed"])
        self.assertFalse(summary["runtime_gate_state_changed"])
        self.assertFalse(summary["runtime_activation_occurred"])
        self.assertFalse(summary["governed_write_path_invoked"])
        self.assertFalse(summary["dashboard_truth_changed"])
        self.assertFalse(summary["parser_behavior_changed"])
        self.assertFalse(summary["scoring_behavior_changed"])
        self.assertFalse(summary["decision_behavior_changed"])
        self.assertFalse(summary["recommendation_behavior_changed"])
        self.assertFalse(summary["phase4i_mutation_added"])
        self.assertTrue(summary["deterministic_runtime_authoritative"])
        self.assertFalse(summary["phase8_sizing_tco_implemented"])
        self.assertIn("no Screen 6 governance control workflow is implemented", summary["summary"])

        boundary = module.validate_screen6_governance_control_boundary()
        self.assertIn("learning_candidate", boundary["target_types"])
        self.assertIn("materialization_artifact", boundary["target_types"])
        self.assertIn("model_registry_entry", boundary["target_types"])
        self.assertIn("runtime_gate", boundary["target_types"])
        self.assertIn("mark_under_review", boundary["actions"])
        self.assertIn("review_runtime_gate", boundary["actions"])
        self.assertIn("proposed", boundary["statuses"])
        self.assertIn("actor identity", boundary["required_gates"])
        self.assertIn("governed write path", boundary["required_gates"])
        self.assertIn("audit trail", boundary["required_gates"])

        with self.assertRaises(module.Screen6GovernanceControlBoundaryError):
            module.validate_screen6_governance_control_boundary(mode="execution")

    def test_runtime_import_isolation(self) -> None:
        run_analysis_imports = imported_modules(ROOT / "scripts" / "run_analysis.py")
        for module_name in (
            "src.learning.screen6_governance_control_boundary",
            "learning.screen6_governance_control_boundary",
            "screen6_governance_control_boundary",
        ):
            with self.subTest(module_name=module_name):
                self.assertNotIn(module_name, run_analysis_imports)

        for path in python_files(RUNTIME_IMPORT_PATHS):
            imports = imported_modules(path)
            source = read_text(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.screen6_governance_control_boundary", imports)
                self.assertNotIn("learning.screen6_governance_control_boundary", imports)
                self.assertNotIn("screen6_governance_control_boundary", imports)
                self.assertNotIn("screen6_governance_control_boundary", source)

    def test_behavior_files_are_not_modified_by_phase7bk(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not available")
        if not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")

        try:
            changed = git_changed_paths(FORBIDDEN_BEHAVIOR_FILES)
        except RuntimeError as exc:
            self.skipTest(str(exc))

        self.assertFalse(changed, f"behavior files modified: {sorted(changed)}")

    def test_readme_links_new_docs(self) -> None:
        text = read_text(README)
        for title, filename in (
            (
                "Phase 7BK Screen 6 Governance Control Boundary",
                "phase7bk_screen6_governance_control_boundary.md",
            ),
            (
                "Phase 7BK Screen 6 Governance Control Lifecycle",
                "phase7bk_screen6_governance_control_lifecycle.md",
            ),
        ):
            with self.subTest(title=title):
                self.assertIn(title, text)
                self.assertIn(filename, text)


if __name__ == "__main__":
    unittest.main()
