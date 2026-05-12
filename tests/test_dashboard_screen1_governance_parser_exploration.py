from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
HTML_DASHBOARD_PATH = ROOT / "src" / "reporting" / "html_dashboard.py"
AI_METADATA_PATH = ROOT / "src" / "reporting" / "ai_display_metadata.py"
RUN_ANALYSIS_PATH = ROOT / "scripts" / "run_analysis.py"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def dashboard_module():
    return importlib.import_module("src.reporting.html_dashboard")


class DashboardScreen1GovernanceParserExplorationTests(unittest.TestCase):
    def test_01_import_compile_safety(self) -> None:
        ast.parse(read_text(HTML_DASHBOARD_PATH), filename=str(HTML_DASHBOARD_PATH))
        ast.parse(read_text(AI_METADATA_PATH), filename=str(AI_METADATA_PATH))
        dashboard = dashboard_module()

        self.assertTrue(hasattr(dashboard, "_render_screen1_governance_parser_exploration"))
        self.assertTrue(hasattr(dashboard, "_build_screen1_governance_parser_exploration_model"))

    def test_screen1_governance_parser_exploration_exists_with_summary_and_safety_labels(self) -> None:
        source = read_text(HTML_DASHBOARD_PATH)
        rendered = self.render_screen1()

        self.assertIn("Screen 1 Governance / Parser Exploration", source)
        self.assertIn("Screen 1 Governance / Parser Exploration", rendered)
        self.assertIn("data-dashboard-selected-summary", rendered)
        self.assertIn("Selected Governance / Parser Summary", rendered)
        self.assertIn("Read-only governance/parser exploration", rendered)
        self.assertIn("Exploratory only", rendered)
        self.assertIn("No backend writes", rendered)
        self.assertIn("No approval controls", rendered)
        self.assertIn("No runtime activation", rendered)

    def test_selector_metadata_exists_for_parser_and_governance_context(self) -> None:
        rendered = self.render_screen1()

        required = (
            'data-dashboard-selectable="true"',
            'data-dashboard-select-type="awr"',
            'data-dashboard-select-key="selectedAwr"',
            'data-dashboard-select-type="run"',
            'data-dashboard-select-key="selectedRun"',
            'data-dashboard-select-type="parser-section"',
            'data-dashboard-select-key="selectedParserSection"',
            'data-dashboard-filter-key="selectedParserSection"',
            'data-dashboard-select-type="parser-diagnostic"',
            'data-dashboard-select-key="selectedParserDiagnostic"',
            'data-dashboard-select-type="unknown-signal"',
            'data-dashboard-select-key="selectedUnknownSignal"',
            'data-dashboard-select-type="governance-item"',
            'data-dashboard-select-key="selectedGovernanceItem"',
            'data-dashboard-select-type="knowledge-request"',
            'data-dashboard-select-key="selectedKnowledgeRequest"',
            'data-dashboard-select-type="artifact"',
            'data-dashboard-select-key="selectedArtifact"',
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_required_safety_wording_is_rendered(self) -> None:
        rendered = self.render_screen1()

        required_phrases = (
            "Read-only governance/parser exploration",
            "Exploratory only",
            "No backend writes",
            "Does not change parser output",
            "Does not classify unknown signals",
            "Does not approve mappings",
            "Does not materialize artifacts",
            "Does not change governance state",
            "Does not change diagnostic truth",
            "Does not change recommendation truth",
            "Semantic/learning context is not parser evidence",
            "Selection only highlights existing parser/governance context",
            "Cross-Screen Selection Propagation is browser-side only",
            "URL hash/localStorage state is not authoritative truth",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_no_unsafe_controls_or_write_runtime_are_introduced(self) -> None:
        dashboard = dashboard_module()
        rendered = self.render_screen1().lower()
        source = read_text(HTML_DASHBOARD_PATH).lower()
        script = dashboard._build_dashboard_interactivity_javascript().lower()

        forbidden_controls = (
            "<button",
            "<form",
            "method=\"post\"",
            "type=\"submit\"",
            "onclick=",
            "data-action=",
            "role=\"button\"",
            "approval-control",
            "write-control",
            "learning-approval-control",
            "parser-update-control",
            "knowledge-update-control",
            "materialize-control",
            "apply-control",
            "activate-control",
        )
        for control in forbidden_controls:
            with self.subTest(control=control):
                self.assertNotIn(control, rendered)

        forbidden_writes = (
            "fetch(",
            "xmlhttprequest",
            "sendbeacon",
            "/api/write",
            "/api/approve",
            "/api/reject",
            "/api/implement",
            "/api/validate",
            "/api/close",
            "/api/activate",
        )
        for phrase in forbidden_writes:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, script)
                self.assertNotIn(phrase, source)

    def test_no_parser_or_governance_mutation_code_paths(self) -> None:
        dashboard = dashboard_module()
        screen_1_source = inspect.getsource(dashboard._render_screen1_governance_parser_exploration).lower()
        screen_1_source += inspect.getsource(dashboard._build_screen1_governance_parser_exploration_model).lower()

        forbidden = (
            "create_parser_mapping",
            "update_parser_mapping",
            "update_unknown_signal",
            "classify_unknown_signal",
            "update_governance_state",
            "approve_mapping",
            "reject_mapping",
            "materialize_artifact(",
            "activate_artifact(",
            "create_knowledge_request",
            "update_knowledge_request",
            "insert into",
            "update awr_",
            "delete from",
        )
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, screen_1_source)

    def test_no_semantic_learning_or_feedback_parser_evidence(self) -> None:
        dashboard = dashboard_module()
        screen_1_source = inspect.getsource(dashboard._render_screen1_governance_parser_exploration)
        rendered = self.render_screen1()

        forbidden = (
            "semantic recall as parser evidence",
            "semantic candidate context as parser evidence",
            "learning candidates as parser evidence",
            "feedback as parser evidence",
            "selectedLearningCandidate",
            "selectedSemanticItem",
            "selectedFeedbackContext",
        )
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, screen_1_source)
                self.assertNotIn(phrase, rendered)

        self.assertIn("Semantic/learning context is not parser evidence", rendered)

    def test_no_screen2_screen4_or_screen5_truth_drift(self) -> None:
        dashboard = dashboard_module()
        screen_2_source = inspect.getsource(dashboard._render_screen_2_page)
        screen_4_source = inspect.getsource(dashboard._render_screen_4_page)
        screen_5_source = inspect.getsource(dashboard._render_screen_5_page)

        forbidden = (
            "selectedParserSection",
            "selectedParserDiagnostic",
            "selectedUnknownSignal",
            "selectedKnowledgeRequest",
            "selectedArtifact",
            "Screen 1 Governance / Parser Exploration",
            "governance/parser exploration as diagnostic truth",
            "governance/parser exploration as historical truth",
            "governance/parser exploration as recommendation truth",
        )
        for phrase in forbidden:
            with self.subTest(screen="screen_2", phrase=phrase):
                self.assertNotIn(phrase, screen_2_source)
            with self.subTest(screen="screen_4", phrase=phrase):
                self.assertNotIn(phrase, screen_4_source)
            with self.subTest(screen="screen_5", phrase=phrase):
                self.assertNotIn(phrase, screen_5_source)

    def test_no_7h8_behavior_yet(self) -> None:
        source = read_text(HTML_DASHBOARD_PATH).lower()

        forbidden_phrases = (
            "cross-screen propagation engine",
            "propagate selection to screen 6",
            "activatelearningcandidate",
            "approvelearningcandidate",
        )
        for phrase in forbidden_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, source)

    def test_runtime_import_drift_is_absent(self) -> None:
        runtime_paths = [
            RUN_ANALYSIS_PATH,
            ROOT / "src" / "analysis" / "decision_engine.py",
            ROOT / "src" / "analysis" / "recommendation_engine.py",
        ]
        runtime_paths.extend((ROOT / "src" / "parser").glob("*.py"))
        runtime_paths.extend((ROOT / "src" / "analysis").glob("*scoring*.py"))

        for path in sorted(set(runtime_paths)):
            if not path.is_file():
                continue
            with self.subTest(path=path.relative_to(ROOT)):
                self.assert_no_learning_imports(path)
                text = read_text(path)
                self.assertNotIn("Screen 1 Governance / Parser Exploration", text)
                self.assertNotIn("DashboardInteractivityFoundation", text)

    def test_documentation_exists_and_contains_required_boundaries(self) -> None:
        doc_path = DOCS / "phase7_screen1_governance_parser_exploration.md"
        self.assertTrue(doc_path.is_file())
        text = read_text(doc_path).lower()

        required_phrases = (
            "read-only",
            "exploratory only",
            "no backend writes",
            "no approval controls",
            "no write controls",
            "does not change parser output",
            "does not classify unknown signals",
            "does not approve mappings",
            "does not materialize artifacts",
            "does not change governance state",
            "does not change diagnostic truth",
            "does not change recommendation truth",
            "semantic/learning context is not parser evidence",
            "full cross-screen propagation remains future 7h.8",
            "selections do not change loader behavior",
            "selections do not create/update knowledge requests",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def render_screen1(self) -> str:
        return dashboard_module()._render_screen_1_page(
            self.sample_screen1_model(),
            parser_review_payload=self.sample_parser_review_payload(),
            parser_governance_payload=self.sample_parser_governance_payload(),
            report_data=self.sample_report_data(),
        )

    @staticmethod
    def sample_screen1_model() -> dict[str, object]:
        return {
            "header": {
                "scope_label": "ORCL / 123456",
                "db_name": "ORCL",
                "dbid": "123456",
                "run_label": "unit-run-1",
            },
            "intake_summary": {
                "total_files": 1,
                "processed": 1,
                "succeeded": 1,
                "failed": 0,
                "skipped": 0,
                "manifest_status": "local",
            },
            "environment_context": {"database_name": "ORCL", "dbid": "123456"},
            "db_ingestion": {"summary": {"db_connectivity": "Not checked", "db_load_mode": "Local only"}},
            "parse_confidence_adaptation": {
                "adaptation_summary": "Parser confidence is stable for this export.",
                "parse_completeness_score": 0.94,
                "warnings_count": 2,
                "sections_detected": ["Load Profile", "Top Timed Events"],
                "sections_missing": ["SQL ordered by Elapsed Time"],
                "unknowns_captured": 1,
                "alias_fallback_matching": "enabled",
            },
            "report_rows": [
                {
                    "file_name": "awr_001.html",
                    "parse_status": "SUCCESS",
                    "awr_id": 7001,
                }
            ],
            "validation_notes": {"notes": ["awr_001.html: SQL section missing"]},
            "supportive_explanation": {},
        }

    @staticmethod
    def sample_parser_review_payload() -> dict[str, object]:
        return {
            "available": True,
            "summary": {"TOTAL": 1, "NEW": 1, "REVIEWED": 0, "CLASSIFIED": 0, "IGNORED": 0},
            "pattern_summary": [
                {
                    "section_name": "Load Profile",
                    "unknown_type": "metric_alias",
                    "detection_reason": "Unknown metric alias",
                    "count": 1,
                    "status_breakdown": {"NEW": 1},
                    "classification_breakdown": {},
                    "example_ids": [11],
                }
            ],
            "recent_unknowns": [
                {
                    "unknown_signal_id": 11,
                    "section_name": "Load Profile",
                    "unknown_type": "metric_alias",
                    "detection_reason": "Unknown metric alias",
                    "review_status": "NEW",
                    "review_classification": None,
                    "reviewed_by": None,
                    "reviewed_at": None,
                }
            ],
        }

    @staticmethod
    def sample_parser_governance_payload() -> dict[str, object]:
        return {
            "available": True,
            "items": [
                {
                    "unknown_signal_id": 11,
                    "parser_stage": "section_map",
                    "classification_hint": "Map Load Profile alias",
                    "review_status": "NEW",
                    "approval_status": "PENDING",
                    "source_file": "awr_001.html",
                    "first_seen_timestamp": "2026-01-01T00:00:00Z",
                    "last_seen_timestamp": "2026-01-01T00:00:00Z",
                }
            ],
            "knowledge_requests": [
                {
                    "request_id": "KR-001",
                    "title": "Review Load Profile alias",
                    "status": "PENDING",
                    "summary": "Request context only.",
                }
            ],
            "knowledge_artifacts": [
                {
                    "artifact_id": "KA-001",
                    "title": "Load Profile alias note",
                    "status": "INACTIVE",
                    "summary": "Artifact context only.",
                }
            ],
        }

    @staticmethod
    def sample_report_data() -> dict[str, object]:
        return {
            "metadata": {"awr_id": 7001, "db_name": "ORCL", "dbid": "123456"},
            "run_history_id": 42,
        }

    def assert_no_learning_imports(self, path: Path) -> None:
        tree = ast.parse(read_text(path), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(
                        self._is_learning_module(alias.name),
                        f"{path} imports learning module {alias.name}",
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                self.assertFalse(
                    self._is_learning_module(module),
                    f"{path} imports learning module {module}",
                )

    @staticmethod
    def _is_learning_module(module_name: str) -> bool:
        return (
            module_name == "learning"
            or module_name.startswith("learning.")
            or module_name == "src.learning"
            or module_name.startswith("src.learning.")
        )


if __name__ == "__main__":
    unittest.main()
