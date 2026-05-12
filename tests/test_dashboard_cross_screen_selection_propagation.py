from __future__ import annotations

import ast
import importlib
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
HTML_DASHBOARD_PATH = ROOT / "src" / "reporting" / "html_dashboard.py"
RUN_ANALYSIS_PATH = ROOT / "scripts" / "run_analysis.py"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def dashboard_module():
    return importlib.import_module("src.reporting.html_dashboard")


class DashboardCrossScreenSelectionPropagationTests(unittest.TestCase):
    def rendered_shell(self) -> str:
        dashboard = dashboard_module()
        return dashboard._build_page_html(
            page_key="home",
            page_title="Unit Dashboard",
            report_data={},
            content_html="",
            generated_at="unit-test",
        )

    def test_01_import_compile_safety(self) -> None:
        ast.parse(read_text(HTML_DASHBOARD_PATH), filename=str(HTML_DASHBOARD_PATH))
        dashboard = dashboard_module()

        self.assertTrue(hasattr(dashboard, "DASHBOARD_INTERACTIVITY_STATE_KEYS"))
        self.assertTrue(hasattr(dashboard, "_build_dashboard_interactivity_javascript"))
        self.assertTrue(hasattr(dashboard, "_render_page_navigation"))

    def test_cross_screen_propagation_foundation_exists(self) -> None:
        dashboard = dashboard_module()
        source = read_text(HTML_DASHBOARD_PATH)
        script = dashboard._build_dashboard_interactivity_javascript()
        rendered = self.rendered_shell()
        combined = source + script + rendered

        required = (
            "Cross-Screen Selection Propagation",
            "Browser-side selection state only",
            "URL hash/localStorage state is not authoritative truth",
            "Read-only",
            "Exploratory only",
            "No backend writes",
            "No API calls",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

    def test_state_keys_from_screens_1_through_6_are_supported(self) -> None:
        dashboard = dashboard_module()
        script = dashboard._build_dashboard_interactivity_javascript()
        source = read_text(HTML_DASHBOARD_PATH)
        combined = source + script

        required_keys = (
            "selectedAwr",
            "selectedRun",
            "selectedDb",
            "selectedSystem",
            "selectedDomain",
            "selectedSeverity",
            "selectedRecommendation",
            "selectedEvidenceGroup",
            "selectedHistoricalWindow",
            "selectedTrendMetric",
            "selectedParserSection",
            "selectedUnknownSignal",
            "selectedGovernanceItem",
            "selectedSemanticItem",
            "selectedLearningCandidate",
            "selectedFleetGroup",
        )
        for key in required_keys:
            with self.subTest(key=key):
                self.assertIn(key, dashboard.DASHBOARD_INTERACTIVITY_STATE_KEYS)
                self.assertIn(key, combined)

    def test_url_hash_behavior_is_safe_and_key_bounded(self) -> None:
        dashboard = dashboard_module()
        script = dashboard._build_dashboard_interactivity_javascript()
        lowered = script.lower()

        required = (
            "parseHashState",
            "updateHashState",
            "serializeDashboardState",
            "URLSearchParams",
            "DASHBOARD_STATE_KEY_SET",
            "DASHBOARD_STATE_KEYS.forEach",
            "isDashboardStateKey",
            "MAX_STATE_VALUE_LENGTH",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, script)

        forbidden_dynamic_execution = (
            "eval(",
            "new function",
            "function(",
            "settimeout(\"",
            "setinterval(\"",
            "innerhtml =",
        )
        for phrase in forbidden_dynamic_execution:
            with self.subTest(phrase=phrase):
                if phrase == "function(":
                    self.assertNotIn("new function(", lowered)
                else:
                    self.assertNotIn(phrase, lowered)

    def test_local_storage_behavior_is_optional_and_namespaced(self) -> None:
        dashboard = dashboard_module()
        script = dashboard._build_dashboard_interactivity_javascript()
        lowered = script.lower()

        self.assertIn("agenticAiAwrAdvisor.dashboardInteractivityState.v1", script)
        self.assertIn("localStorage", script)
        self.assertIn("try {", script)
        self.assertIn("catch (error)", script)
        self.assertIn("sanitizeDashboardState", script)

        forbidden_persistence = (
            "report_data",
            "raw report content",
            "awr_report_text",
            "document.body",
            "outerhtml",
        )
        for phrase in forbidden_persistence:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, lowered)

    def test_visual_selected_state_and_summary_support_exists(self) -> None:
        dashboard = dashboard_module()
        script = dashboard._build_dashboard_interactivity_javascript()
        source = read_text(HTML_DASHBOARD_PATH)
        combined = source + script

        required = (
            "is-selected",
            "markSelectedElement",
            "data-selected",
            "aria-selected",
            "updateSelectedSummary",
            "data-dashboard-selected-summary",
            "Non-matching elements remain visible",
            "deterministic truth is not hidden by default",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

        forbidden_hiding = (
            "display = 'none'",
            'display = "none"',
            ".style.display='none'",
            '.style.display="none"',
        )
        for phrase in forbidden_hiding:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, script)

    def test_screen_summary_support_exists_for_screens_1_through_6(self) -> None:
        dashboard = dashboard_module()
        source = read_text(HTML_DASHBOARD_PATH)
        script = dashboard._build_dashboard_interactivity_javascript()

        summary_markers = (
            "screen1-selected-governance-parser-summary",
            "screen2-selected-diagnostic-summary",
            "screen3-selected-summary",
            "screen4-selected-historical-summary",
            "screen5-selected-recommendation-summary",
            "screen6-selected-summary",
        )
        for marker in summary_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

        summary_boundaries = (
            "Browser-side selection state only",
            "Read-only",
            "Exploratory only",
            "No backend writes",
            "URL hash/localStorage state is not authoritative truth",
            "Does not change diagnostic truth",
            "Does not change historical truth",
            "Does not change recommendation truth",
        )
        for phrase in summary_boundaries:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, script)

    def test_navigation_persistence_is_static_dashboard_compatible(self) -> None:
        dashboard = dashboard_module()
        rendered = self.rendered_shell()
        script = dashboard._build_dashboard_interactivity_javascript()
        lowered_script = script.lower()

        required = (
            'data-dashboard-propagate-state="true"',
            "preserveDashboardStateInNavigation",
            "hrefWithDashboardState",
            "NAVIGATION_LINK_SELECTOR",
            "serializeDashboardState",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered + script)

        self.assertNotIn("<script src=", rendered.lower())
        self.assertNotIn("react", lowered_script)
        self.assertNotIn("vue", lowered_script)
        self.assertNotIn("npm", lowered_script)
        self.assertNotIn("require(", lowered_script)
        self.assertNotIn("import ", lowered_script)

    def test_no_unsafe_controls_or_write_behaviors(self) -> None:
        dashboard = dashboard_module()
        rendered = self.rendered_shell().lower()
        script = dashboard._build_dashboard_interactivity_javascript().lower()

        forbidden_controls = (
            "<button",
            "<form",
            "method=\"post\"",
            "type=\"submit\"",
            "onclick=",
            "data-action=",
            "approval-control",
            "write-control",
            "candidate-status-mutation-control",
            "governance-status-mutation-control",
            "parser-update-control",
            "knowledge-update-control",
            "materialize-control",
            "activate-control",
            "apply-control",
        )
        for phrase in forbidden_controls:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, rendered)

        forbidden_writes = (
            "fetch(",
            "xmlhttprequest",
            "sendbeacon",
            "form.submit",
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

    def test_no_backend_dependencies_or_phase7i_commands(self) -> None:
        dashboard = dashboard_module()
        script = dashboard._build_dashboard_interactivity_javascript().lower()
        run_analysis = read_text(RUN_ANALYSIS_PATH).lower()

        forbidden_script_dependencies = (
            "fetch(",
            "xmlhttprequest",
            "sendbeacon",
            "indexeddb",
            "websocket",
            "eventsource",
            "sessionstorage",
            "server-side state",
            "backend state persistence",
            "database call",
        )
        for phrase in forbidden_script_dependencies:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, script)

        forbidden_cli = (
            "approve_learning_candidate",
            "reject_learning_candidate",
            "activate_learning_candidate",
            "apply_learning_candidate",
        )
        for phrase in forbidden_cli:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, run_analysis)

    def test_truth_and_semantic_learning_boundaries_are_marked(self) -> None:
        dashboard = dashboard_module()
        combined = (
            read_text(HTML_DASHBOARD_PATH)
            + dashboard._build_dashboard_interactivity_javascript()
            + dashboard._render_dashboard_interactivity_boundary_comment()
        )

        required = (
            "Does not change diagnostic truth",
            "Does not change historical truth",
            "Does not change recommendation truth",
            "Does not change parser output",
            "Does not change governance state",
            "Does not change candidate status",
            "Semantic context remains reviewer-assist only",
            "Learning candidates remain proposal/review context only",
            "Does not activate learning candidates",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

    def test_documentation_exists_and_contains_required_boundaries(self) -> None:
        doc_path = DOCS / "phase7_cross_screen_selection_propagation.md"
        self.assertTrue(doc_path.is_file())
        text = read_text(doc_path).lower()

        required = (
            "browser-side only",
            "read-only",
            "exploratory only",
            "url hash/localstorage state is not authoritative truth",
            "no backend writes",
            "no api calls",
            "does not change parser output",
            "does not change diagnostic truth",
            "does not change historical truth",
            "does not change recommendation truth",
            "does not change governance state",
            "does not change candidate status",
            "semantic context remains reviewer-assist only",
            "learning candidates remain proposal/review context only",
            "no phase 7i cli learning commands",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
