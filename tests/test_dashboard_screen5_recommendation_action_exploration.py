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


class DashboardScreen5RecommendationActionExplorationTests(unittest.TestCase):
    def test_01_import_compile_safety(self) -> None:
        ast.parse(read_text(HTML_DASHBOARD_PATH), filename=str(HTML_DASHBOARD_PATH))
        ast.parse(read_text(AI_METADATA_PATH), filename=str(AI_METADATA_PATH))
        dashboard = dashboard_module()

        self.assertTrue(hasattr(dashboard, "_render_screen5_recommendation_action_exploration"))
        self.assertTrue(hasattr(dashboard, "_build_screen5_recommendation_action_exploration_model"))

    def test_screen5_recommendation_action_exploration_exists_with_summary_and_safety_labels(self) -> None:
        source = read_text(HTML_DASHBOARD_PATH)
        rendered = self.render_screen5()

        self.assertIn("Screen 5 Recommendation/Action Exploration", source)
        self.assertIn("Screen 5 Recommendation/Action Exploration", rendered)
        self.assertIn("data-dashboard-selected-summary", rendered)
        self.assertIn("Selected Recommendation / Action Summary", rendered)
        self.assertIn("Read-only recommendation/action exploration", rendered)
        self.assertIn("Exploratory only", rendered)
        self.assertIn("No backend writes", rendered)
        self.assertIn("No approval controls", rendered)
        self.assertIn("No runtime activation", rendered)

    def test_selector_metadata_exists_for_recommendation_action_context(self) -> None:
        rendered = self.render_screen5()

        required = (
            'data-dashboard-selectable="true"',
            'data-dashboard-select-type="recommendation"',
            'data-dashboard-select-key="selectedRecommendation"',
            'data-dashboard-filter-key="selectedRecommendation"',
            'data-dashboard-select-type="recommendation-category"',
            'data-dashboard-select-key="selectedRecommendationCategory"',
            'data-dashboard-select-type="recommendation-evidence"',
            'data-dashboard-select-key="selectedRecommendationEvidence"',
            'data-dashboard-select-type="action-context"',
            'data-dashboard-select-key="selectedActionContext"',
            'data-dashboard-select-type="outcome-context"',
            'data-dashboard-select-key="selectedOutcomeContext"',
            'data-dashboard-select-type="feedback-context"',
            'data-dashboard-select-key="selectedFeedbackContext"',
            'data-dashboard-select-type="learning-candidate"',
            'data-dashboard-select-key="selectedLearningCandidate"',
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_authoritative_domain_controls_are_present(self) -> None:
        rendered = self.render_screen5()

        for domain in ("CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG"):
            with self.subTest(domain=domain):
                self.assertIn(f'data-dashboard-filter-value="{domain}"', rendered)
                self.assertIn(f">{domain}</span>", rendered)

    def test_required_safety_wording_is_rendered(self) -> None:
        rendered = self.render_screen5()

        required_phrases = (
            "Read-only recommendation/action exploration",
            "Exploratory only",
            "No backend writes",
            "Does not change recommendation truth",
            "Does not change recommendation priority",
            "Does not change recommendation rationale",
            "Does not change supporting evidence",
            "Does not change diagnostic truth",
            "Learning candidates are not recommendation evidence",
            "Semantic context is not recommendation evidence",
            "Selection only highlights existing recommendation/action context",
            "Cross-screen propagation remains future Phase 7H.8",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_no_unsafe_controls_or_write_runtime_are_introduced(self) -> None:
        dashboard = dashboard_module()
        rendered = self.render_screen5().lower()
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

    def test_no_learning_semantic_or_governance_recommendation_evidence(self) -> None:
        dashboard = dashboard_module()
        screen_5_source = inspect.getsource(dashboard._render_screen5_recommendation_action_exploration)
        rendered = self.render_screen5()

        forbidden = (
            "semantic recall as recommendation evidence",
            "semantic candidate context as recommendation evidence",
            "learning candidates as recommendation evidence",
            "governance status as recommendation evidence",
        )
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, screen_5_source)
                self.assertNotIn(phrase, rendered)

        self.assertIn("Learning candidates are not recommendation evidence", rendered)
        self.assertIn("Semantic context is not recommendation evidence", rendered)
        self.assertIn("runtime_influence=false", rendered)

    def test_no_action_outcome_or_feedback_mutation_controls(self) -> None:
        rendered = self.render_screen5().lower()

        forbidden = (
            "action-tracking write control",
            "outcome-tracking write control",
            "feedback write control",
            "status mutation control",
            "data-status-mutation",
            "data-feedback-write",
            "data-outcome-write",
            "data-action-write",
        )
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, rendered)

        self.assertIn("no action tracking writes", rendered)
        self.assertIn("no outcome tracking writes", rendered)
        self.assertIn("no feedback writes", rendered)

    def test_no_screen2_or_screen4_truth_drift(self) -> None:
        dashboard = dashboard_module()
        screen_2_source = inspect.getsource(dashboard._render_screen_2_page)
        screen_4_source = inspect.getsource(dashboard._render_screen_4_page)

        forbidden = (
            "selectedRecommendationCategory",
            "selectedRecommendationEvidence",
            "selectedActionContext",
            "selectedOutcomeContext",
            "selectedFeedbackContext",
            "Screen 5 Recommendation/Action Exploration",
            "recommendation/action exploration as diagnostic truth",
            "recommendation/action exploration as historical truth",
        )
        for phrase in forbidden:
            with self.subTest(screen="screen_2", phrase=phrase):
                self.assertNotIn(phrase, screen_2_source)
            with self.subTest(screen="screen_4", phrase=phrase):
                self.assertNotIn(phrase, screen_4_source)

    def test_no_7h8_behavior_yet(self) -> None:
        source = read_text(HTML_DASHBOARD_PATH).lower()

        forbidden_phrases = (
            "cross-screen propagation engine",
            "propagate selection to screen 1",
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
                self.assertNotIn("Screen 5 Recommendation/Action Exploration", text)
                self.assertNotIn("DashboardInteractivityFoundation", text)

    def test_documentation_exists_and_contains_required_boundaries(self) -> None:
        doc_path = DOCS / "phase7_screen5_recommendation_action_exploration.md"
        self.assertTrue(doc_path.is_file())
        text = read_text(doc_path).lower()

        required_phrases = (
            "read-only",
            "exploratory only",
            "no backend writes",
            "no approval controls",
            "no write controls",
            "does not change recommendation truth",
            "does not change recommendation priority",
            "does not change recommendation rationale",
            "does not change supporting evidence",
            "does not change diagnostic truth",
            "learning candidates are not recommendation evidence",
            "semantic context is not recommendation evidence",
            "action/outcome/feedback selectors do not write or mutate records",
            "full cross-screen propagation remains future 7h.8",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def render_screen5(self) -> str:
        return dashboard_module()._render_screen_5_page(
            self.sample_screen5_model(),
            ai_sections={},
            agentic_decision={},
            report_data=self.sample_report_data(),
        )

    @staticmethod
    def sample_screen5_model() -> dict[str, object]:
        return {
            "header": {
                "decision_posture": "TUNE FIRST",
                "display_severity_label": "High",
                "confidence": 0.82,
                "primary_issue": "CPU",
            },
            "normalized_decision": {
                "primary_issue": "CPU",
                "overall_status": "WARNING",
                "display_severity_label": "High",
                "confidence": 0.82,
                "domain_scores": {"CPU": 72.0, "IO": 18.0, "COMMIT": 12.0},
            },
            "canonical_recommendation_count": 1,
            "recommendation_groups": [
                {
                    "title": "SQL Tuning",
                    "items": [
                        {
                            "issue": "CPU",
                            "action": "Tune top SQL before scaling",
                            "priority": "HIGH",
                            "confidence": 0.82,
                            "category": "tuning",
                            "category_label": "Tuning",
                            "rationale": "CPU evidence supports SQL tuning first.",
                        }
                    ],
                }
            ],
            "recommendation_list": [
                {
                    "issue": "CPU",
                    "action": "Tune top SQL before scaling",
                    "priority": "HIGH",
                    "confidence": 0.82,
                    "category": "tuning",
                    "rationale": "CPU evidence supports SQL tuning first.",
                }
            ],
            "recommendation_evidence_tie_back": {
                "primary_evidence": {
                    "domain": "CPU",
                    "summary": "CPU is the strongest deterministic evidence.",
                    "reasons": ["DB CPU remained high."],
                },
                "secondary_evidence": [
                    {"domain": "COMMIT", "summary": "Commit latency is secondary."}
                ],
            },
            "posture_guidance": [
                "Validate top SQL elapsed time before scaling.",
                "Complete tuning validation before making a scaling decision.",
            ],
            "validation_focus_areas": [
                {"title": "Top Waits", "items": ["DB CPU remained visible."]},
                {"title": "Missing Metrics", "items": ["SQL plan history missing."]},
            ],
            "action_context": [
                {"id": "action-1", "title": "Action Context", "summary": "Open tuning review."}
            ],
            "outcome_context": [
                {"id": "outcome-1", "title": "Outcome Context", "summary": "Outcome not yet recorded."}
            ],
            "feedback_context": [
                {"id": "feedback-1", "title": "Feedback Context", "summary": "Feedback pending review."}
            ],
            "related_learning_candidates": [
                {
                    "candidate_id": "LC-001",
                    "candidate_type": "recommendation_tuning_candidate",
                    "domain": "CPU",
                    "summary": "Proposal context only.",
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
