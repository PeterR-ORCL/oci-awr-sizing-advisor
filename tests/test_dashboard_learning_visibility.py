from __future__ import annotations

import ast
import importlib
import inspect
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
HTML_DASHBOARD_PATH = ROOT / "src" / "reporting" / "html_dashboard.py"
AI_METADATA_PATH = ROOT / "src" / "reporting" / "ai_display_metadata.py"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def metadata_module():
    return importlib.import_module("src.reporting.ai_display_metadata")


def dashboard_module():
    return importlib.import_module("src.reporting.html_dashboard")


class DashboardLearningVisibilityTests(unittest.TestCase):
    def test_01_import_safety(self) -> None:
        before_environment = dict(os.environ)

        metadata = metadata_module()
        dashboard = dashboard_module()

        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(metadata, "build_learning_visibility_metadata"))
        self.assertTrue(hasattr(dashboard, "_render_learning_visibility_section"))

    def test_empty_state_is_safe_and_read_only(self) -> None:
        metadata = metadata_module()
        dashboard = dashboard_module()

        payload = metadata.build_learning_visibility_metadata()
        rendered = dashboard._render_learning_visibility_section(payload)

        self.assertEqual(payload["candidate_count"], 0)
        self.assertIn("No learning candidates available", rendered)
        self.assertIn("Learning visibility is read-only", rendered)
        self.assertIn("No runtime influence", rendered)
        self.assertIn("Read-only", rendered)
        self.assertIn("runtime_influence=false", rendered)

    def test_candidate_summary_counts_are_deterministic(self) -> None:
        metadata = metadata_module()
        candidates = [
            self.make_candidate("CAND-2", "dashboard_wording_candidate", "UNDER_REVIEW"),
            self.make_candidate("CAND-1", "parser_mapping_candidate", "PROPOSED"),
            self.make_candidate("CAND-3", "dashboard_wording_candidate", "PROPOSED"),
        ]

        payload = metadata.build_learning_visibility_metadata(candidates=candidates)

        self.assertEqual(
            payload["status_counts"],
            {"PROPOSED": 2, "UNDER_REVIEW": 1},
        )
        self.assertEqual(
            payload["type_counts"],
            {
                "dashboard_wording_candidate": 2,
                "parser_mapping_candidate": 1,
            },
        )
        self.assertEqual(
            [candidate["candidate_id"] for candidate in payload["candidates"]],
            ["CAND-1", "CAND-3", "CAND-2"],
        )

    def test_candidate_safety_labels_are_rendered(self) -> None:
        dashboard = dashboard_module()
        rendered = self.render_sample_learning_visibility()

        required = (
            "runtime_influence=false",
            "requires_human_review=true",
            "Human review required",
            "Not diagnostic evidence",
            "Not recommendation truth",
            "Not automatically applied",
            "Read-only",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

        self.assertIn("Learning Visibility", rendered)
        self.assertIn("candidate_id", rendered)
        self.assertIn("candidate_type", rendered)
        self.assertTrue(hasattr(dashboard, "_render_learning_visibility_section"))

    def test_semantic_context_is_reviewer_assist_only(self) -> None:
        rendered = self.render_sample_learning_visibility()

        self.assertIn("semantic_context present", rendered)
        self.assertIn("Semantic context is reviewer-assist only", rendered)
        self.assertIn("not source_evidence", rendered)
        self.assertIn("not diagnostic evidence", rendered)
        self.assertNotIn("semantic prior note should not render as evidence", rendered)

    def test_governance_status_is_review_state_only(self) -> None:
        rendered = self.render_sample_learning_visibility()

        self.assertIn("APPROVED_FOR_IMPLEMENTATION", rendered)
        self.assertIn("Approved for implementation only, not runtime activation", rendered)
        self.assertIn("Governance approval is not runtime activation", rendered)
        self.assertIn("Reference only: commit:abc123", rendered)
        self.assertIn("approved_for_implementation_only=true", rendered)
        self.assertIn("runtime_influence=false", rendered)

    def test_no_write_controls_are_rendered(self) -> None:
        rendered = self.render_sample_learning_visibility().lower()

        forbidden_controls = (
            "<button",
            "<form",
            "<input",
            "<select",
            "<textarea",
            "onclick=",
            "data-action=",
            "role=\"button\"",
            "learning-write-control",
            "learning-approval-control",
        )
        for control in forbidden_controls:
            with self.subTest(control=control):
                self.assertNotIn(control, rendered)

    def test_no_runtime_import_drift(self) -> None:
        runtime_paths = [
            ROOT / "scripts" / "run_analysis.py",
            ROOT / "src" / "analysis" / "decision_engine.py",
            ROOT / "src" / "analysis" / "recommendation_engine.py",
        ]
        runtime_paths.extend((ROOT / "src" / "parser").glob("*.py"))
        runtime_paths.extend((ROOT / "src" / "analysis").glob("*scoring*.py"))

        for path in sorted(set(runtime_paths)):
            with self.subTest(path=path.relative_to(ROOT)):
                self.assert_no_learning_imports(path)
                text = read_text(path)
                self.assertNotIn("learning_visibility", text)
                self.assertNotIn("_render_learning_visibility_section", text)

    def test_screen_2_and_screen_5_do_not_render_learning_truth(self) -> None:
        dashboard = dashboard_module()
        screen_2_source = inspect.getsource(dashboard._render_screen_2_page)
        screen_5_source = inspect.getsource(dashboard._render_screen_5_page)

        screen_2_forbidden = (
            "Learning Visibility",
            "learning_candidate",
            "_render_learning_visibility_section",
            "semantic_context present",
        )
        screen_5_forbidden = (
            "Learning Visibility",
            "learning_candidate",
            "_render_learning_visibility_section",
            "semantic_context present",
        )
        for phrase in screen_2_forbidden:
            with self.subTest(screen="screen_2", phrase=phrase):
                self.assertNotIn(phrase, screen_2_source)
        for phrase in screen_5_forbidden:
            with self.subTest(screen="screen_5", phrase=phrase):
                self.assertNotIn(phrase, screen_5_source)

    def test_no_phase7h_write_or_propagation_interactivity(self) -> None:
        rendered = self.render_sample_learning_visibility().lower()
        source = read_text(HTML_DASHBOARD_PATH).lower()

        self.assertIn("full dashboard interactivity remains future phase 7h", rendered)
        self.assertNotIn("learning_state_engine", source)
        self.assertNotIn("cross-screen propagation engine", source)
        self.assertNotIn("approvelearningcandidate", source)
        self.assertNotIn("activatelearningcandidate", source)
        self.assertNotIn("data-learning-action", rendered)
        self.assertNotIn("candidate-selection", rendered)

    def test_documentation_exists_and_contains_boundaries(self) -> None:
        doc_path = DOCS / "phase7_dashboard_learning_visibility.md"
        self.assertTrue(doc_path.is_file())
        text = read_text(doc_path).lower()

        required_phrases = (
            "read-only",
            "learning candidates are not diagnostic evidence",
            "learning candidates are not recommendation truth",
            "no approval controls",
            "no write controls",
            "runtime_influence=false",
            "requires_human_review=true",
            "semantic context is reviewer-assist only",
            "full dashboard interactivity remains future phase 7h",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_screen_6_accepts_optional_learning_payload(self) -> None:
        dashboard = dashboard_module()
        payload = metadata_module().build_learning_visibility_metadata(
            candidates=[self.make_candidate("CAND-S6", "dashboard_wording_candidate", "PROPOSED")]
        )

        rendered = dashboard._render_screen_6_page(
            {
                "similarity_enabled": False,
                "header": {"scope_label": "unit"},
                "clusters": {},
                "fleet_summary": {},
            },
            governance_payload={},
            semantic_recall_payload={},
            learning_visibility_payload=payload,
        )

        self.assertIn("Learning Visibility", rendered)
        self.assertIn("CAND-S6", rendered)
        self.assertIn("Not diagnostic evidence", rendered)
        self.assertIn("Not recommendation truth", rendered)

    def render_sample_learning_visibility(self) -> str:
        metadata = metadata_module()
        dashboard = dashboard_module()
        payload = metadata.build_learning_visibility_metadata(
            candidates=[
                self.make_candidate(
                    "CAND-APPROVED",
                    "dashboard_wording_candidate",
                    "APPROVED_FOR_IMPLEMENTATION",
                    semantic_context={"summary": "semantic prior note should not render as evidence"},
                    materialization_reference="commit:abc123",
                )
            ],
            governance_records=[
                {
                    "to_status": "APPROVED_FOR_IMPLEMENTATION",
                    "actor": "reviewer@example.com",
                    "review_notes": "Implementation work only.",
                    "materialization_reference": "commit:abc123",
                    "approved_for_implementation_only": True,
                    "runtime_influence": False,
                }
            ],
        )
        return dashboard._render_learning_visibility_section(payload)

    @staticmethod
    def make_candidate(
        candidate_id: str,
        candidate_type: str,
        status: str,
        semantic_context: dict[str, object] | None = None,
        materialization_reference: str | None = None,
    ) -> dict[str, object]:
        return {
            "candidate_id": candidate_id,
            "candidate_type": candidate_type,
            "status": status,
            "affected_component": "dashboard",
            "affected_domain": "governance",
            "confidence": 0.81,
            "requires_human_review": True,
            "runtime_influence": False,
            "title": f"{candidate_id} visibility record",
            "source_evidence": [{"source_type": "unit", "source_id": candidate_id}],
            "semantic_context": semantic_context,
            "materialization_reference": materialization_reference,
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
