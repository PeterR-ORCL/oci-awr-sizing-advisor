from __future__ import annotations

import ast
import importlib
import os
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


def metadata_module():
    return importlib.import_module("src.reporting.ai_display_metadata")


class DashboardInteractivityFoundationTests(unittest.TestCase):
    def test_01_import_compile_safety(self) -> None:
        before_environment = dict(os.environ)

        ast.parse(read_text(HTML_DASHBOARD_PATH), filename=str(HTML_DASHBOARD_PATH))
        ast.parse(read_text(AI_METADATA_PATH), filename=str(AI_METADATA_PATH))
        dashboard = dashboard_module()

        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(dashboard, "DASHBOARD_INTERACTIVITY_STATE_KEYS"))
        self.assertTrue(hasattr(dashboard, "_build_dashboard_interactivity_javascript"))
        self.assertTrue(hasattr(dashboard, "_render_dashboard_interactivity_boundary_comment"))

    def test_foundation_script_exists_with_state_and_metadata_hooks(self) -> None:
        dashboard = dashboard_module()
        source = read_text(HTML_DASHBOARD_PATH)
        script = dashboard._build_dashboard_interactivity_javascript()
        boundary = dashboard._render_dashboard_interactivity_boundary_comment()
        combined = source + script + boundary

        required_functions = (
            "initializeDashboardInteractivity",
            "readDashboardState",
            "writeDashboardState",
            "parseHashState",
            "updateHashState",
            "applyDashboardState",
            "markSelectedElement",
            "updateSelectedSummary",
        )
        for function_name in required_functions:
            with self.subTest(function_name=function_name):
                self.assertIn(function_name, script)

        required_markers = (
            "Dashboard Interactivity Foundation",
            "Read-only selection state",
            "Exploratory only",
            "No backend writes",
        )
        for marker in required_markers:
            with self.subTest(marker=marker):
                self.assertIn(marker, combined)

        for key in dashboard.DASHBOARD_INTERACTIVITY_STATE_KEYS:
            with self.subTest(key=key):
                self.assertIn(key, script)

        for attribute in dashboard.DASHBOARD_INTERACTIVITY_SELECTABLE_ATTRIBUTES:
            with self.subTest(attribute=attribute):
                self.assertIn(attribute, combined)

    def test_rendered_output_contains_read_only_safety_wording(self) -> None:
        dashboard = dashboard_module()
        rendered = dashboard._build_page_html(
            page_key="home",
            page_title="Unit Dashboard",
            report_data={},
            content_html="",
            generated_at="unit-test",
        )

        required_phrases = (
            "Read-only selection state",
            "Exploratory only",
            "No backend writes",
            "Does not change diagnostic truth",
            "Does not change recommendation truth",
            "Does not approve or activate learning candidates",
            "Full screen-specific interactivity remains future Phase 7H subtasks",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_no_unsafe_write_controls_are_introduced_by_foundation(self) -> None:
        dashboard = dashboard_module()
        rendered = dashboard._build_page_html(
            page_key="home",
            page_title="Unit Dashboard",
            report_data={},
            content_html="",
            generated_at="unit-test",
        ).lower()
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
        )
        for control in forbidden_controls:
            with self.subTest(control=control):
                self.assertNotIn(control, rendered)

        forbidden_runtime_writes = (
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
        for phrase in forbidden_runtime_writes:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, script)

    def test_no_runtime_import_drift(self) -> None:
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
                if path != RUN_ANALYSIS_PATH:
                    self.assertNotIn("_build_dashboard_interactivity_javascript", text)
                    self.assertNotIn("DashboardInteractivityFoundation", text)

    def test_existing_dashboard_learning_visibility_remains_read_only(self) -> None:
        dashboard = dashboard_module()
        metadata = metadata_module()
        rendered = dashboard._render_learning_visibility_section(
            metadata.build_learning_visibility_metadata()
        )
        source = read_text(HTML_DASHBOARD_PATH)

        required = (
            "runtime_influence=false",
            "Not diagnostic evidence",
            "Not recommendation truth",
            "Learning visibility is read-only",
            "Full dashboard interactivity remains future Phase 7H",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

        self.assertIn("runtime_influence=false", source)
        self.assertNotIn("runtime_influence=true", source)

    def test_no_phase7h8_or_later_behavior_in_foundation(self) -> None:
        dashboard = dashboard_module()
        source = read_text(HTML_DASHBOARD_PATH).lower()
        script = dashboard._build_dashboard_interactivity_javascript().lower()

        forbidden_source_phrases = (
            "cross-screen propagation engine",
            "screen-specific diagnostic selection",
            "screen-specific recommendation selection",
            "learning_state_engine",
            "candidate-selection",
            "data-learning-action",
        )
        for phrase in forbidden_source_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, source)

        forbidden_script_phrases = (
            "diagnostic mutation",
            "recommendation mutation",
            "approvelearningcandidate",
            "activatelearningcandidate",
            "applylearningcandidate",
        )
        for phrase in forbidden_script_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, script)

    def test_static_dashboard_compatibility_for_foundation(self) -> None:
        dashboard = dashboard_module()
        rendered = dashboard._build_page_html(
            page_key="home",
            page_title="Unit Dashboard",
            report_data={},
            content_html="",
            generated_at="unit-test",
        ).lower()
        script = dashboard._build_dashboard_interactivity_javascript().lower()

        self.assertNotIn("<script src=", rendered)
        self.assertNotIn("https://", script)
        self.assertNotIn("http://", script)
        self.assertNotIn("react", script)
        self.assertNotIn("vue", script)
        self.assertNotIn("npm", script)
        self.assertNotIn("import ", script)
        self.assertNotIn("require(", script)
        self.assertIn("if (!selectableelements.length", script)
        self.assertIn("return {}", script)

    def test_documentation_exists_and_contains_required_boundaries(self) -> None:
        doc_path = DOCS / "phase7_dashboard_interactivity_foundation.md"
        self.assertTrue(doc_path.is_file())
        text = read_text(doc_path).lower()

        required_phrases = (
            "read-only",
            "exploratory only",
            "no backend writes",
            "no approval controls",
            "no write controls",
            "does not change diagnostic truth",
            "does not change recommendation truth",
            "screen-specific selection behavior is future work",
            "full cross-screen propagation is future 7h.8",
            "learning candidates remain review/proposal context only",
            "semantic context remains reviewer-assist only",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

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
