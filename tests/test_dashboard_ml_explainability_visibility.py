from __future__ import annotations

import importlib
import inspect
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def metadata_module():
    return importlib.import_module("src.reporting.ai_display_metadata")


def dashboard_module():
    return importlib.import_module("src.reporting.html_dashboard")


class DashboardMLExplainabilityVisibilityTests(unittest.TestCase):
    def test_metadata_builder_import_safety(self) -> None:
        metadata = metadata_module()
        self.assertTrue(hasattr(metadata, "build_ml_explainability_visibility_metadata"))

    def test_empty_metadata_is_safe_and_read_only(self) -> None:
        payload = metadata_module().build_ml_explainability_visibility_metadata()

        self.assertTrue(payload["enabled"])
        self.assertTrue(payload["read_only"])
        self.assertTrue(payload["advisory_only"])
        self.assertTrue(payload["deterministic_runtime_authoritative"])
        self.assertFalse(payload["runtime_active"])
        self.assertFalse(payload["runtime_influence"])
        self.assertFalse(payload["runtime_influence_granted"])
        self.assertFalse(payload["runtime_eligibility_granted"])
        self.assertTrue(payload["empty_state"])

    def test_metadata_includes_required_safety_labels(self) -> None:
        payload = metadata_module().build_ml_explainability_visibility_metadata()
        labels = " ".join(payload["safety_labels"]).lower()
        for phrase in (
            "read-only",
            "advisory / shadow only",
            "not diagnostic evidence",
            "not recommendation truth",
            "deterministic runtime remains authoritative",
            "runtime_active=false",
            "runtime_influence=false",
            "runtime_influence_granted=false",
            "runtime_eligibility_granted=false",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, labels)

    def test_screen_6_renders_ml_adaptive_visibility_section(self) -> None:
        dashboard = dashboard_module()
        payload = metadata_module().build_ml_explainability_visibility_metadata(
            explanations=[
                {
                    "explanation_id": "EXP-1",
                    "model_id": "MODEL-1",
                    "domain": "SQL",
                    "summary": "Shadow model saw SQL elapsed time pressure.",
                    "feature_contributions": [
                        {"feature": "db_time_pct", "contribution": 0.42, "direction": "positive"}
                    ],
                }
            ],
            model_registry_entries=[
                {
                    "model_id": "MODEL-1",
                    "model_family": "shadow",
                    "governance_status": "REGISTERED",
                    "shadow_eligible": True,
                    "runtime_eligibility_requested": True,
                }
            ],
            scoring_integration_results=[
                {
                    "result_id": "SCORE-1",
                    "domain": "SQL",
                    "deterministic_score": 70,
                    "shadow_ml_score": 75,
                    "selected_score_source": "shadow_ml",
                    "selected_advisory_score": 75,
                    "gate_allowed_for_consideration": True,
                }
            ],
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
            learning_visibility_payload={},
            ml_explainability_visibility_payload=payload,
        )

        self.assertIn("ML / Adaptive Explainability Visibility", rendered)
        self.assertIn("EXP-1", rendered)
        self.assertIn("MODEL-1", rendered)
        self.assertIn("Shadow model saw SQL elapsed time pressure.", rendered)
        self.assertIn("Not diagnostic evidence", rendered)
        self.assertIn("Not recommendation truth", rendered)
        self.assertIn("Deterministic runtime remains authoritative", rendered)
        self.assertIn("runtime_active=false", rendered)
        self.assertIn("No runtime activation", rendered)

    def test_rendering_contains_no_write_or_activation_controls(self) -> None:
        rendered = dashboard_module()._render_ml_explainability_visibility_section(
            metadata_module().build_ml_explainability_visibility_metadata()
        ).lower()
        for forbidden in (
            "<button",
            "<form",
            "<input",
            "<select",
            "<textarea",
            "onclick=",
            "data-action=",
            "role=\"button\"",
            "approval-control",
            "write-control",
            "activation-control",
            "rollback-control",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, rendered)

    def test_screen_2_and_screen_5_do_not_render_ml_truth(self) -> None:
        dashboard = dashboard_module()
        screen_2_source = inspect.getsource(dashboard._render_screen_2_page)
        screen_5_source = inspect.getsource(dashboard._render_screen_5_page)
        forbidden = (
            "ML / Adaptive Explainability Visibility",
            "_render_ml_explainability_visibility_section",
            "ml_explanations",
            "feature_contribution_rows",
        )
        for phrase in forbidden:
            with self.subTest(screen="screen_2", phrase=phrase):
                self.assertNotIn(phrase, screen_2_source)
            with self.subTest(screen="screen_5", phrase=phrase):
                self.assertNotIn(phrase, screen_5_source)

    def test_no_generated_dashboard_dependency(self) -> None:
        source = read_text(ROOT / "src" / "reporting" / "html_dashboard.py")
        self.assertNotIn("docs/generated", source)
        self.assertNotIn("generated_dashboard.html", source)

    def test_docs_exist_and_contain_boundary_phrases(self) -> None:
        doc_path = DOCS / "phase7ab_ml_explainability_visibility.md"
        self.assertTrue(doc_path.is_file(), doc_path)
        text = read_text(doc_path).lower()
        for phrase in (
            "dashboard visibility is read-only",
            "ml explanations are not diagnostic evidence",
            "ml explanations are not recommendation truth",
            "model registry visibility does not deploy models",
            "runtime gate visibility does not activate runtime",
            "fallback visibility does not execute rollback",
            "deterministic runtime remains authoritative",
            "no runtime behavior changes are made",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
