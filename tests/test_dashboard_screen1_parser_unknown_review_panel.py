from __future__ import annotations

import importlib
import py_compile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
HTML_DASHBOARD_PATH = ROOT / "src" / "reporting" / "html_dashboard.py"
PANEL_DOC = DOCS / "phase7aw_screen1_parser_unknown_review_panel.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def lower_text(path: Path) -> str:
    return read_text(path).lower()


def dashboard_module():
    return importlib.import_module("src.reporting.html_dashboard")


class DashboardScreen1ParserUnknownReviewPanelTests(unittest.TestCase):
    def render_screen1(self) -> str:
        return dashboard_module()._render_screen_1_page(
            self.sample_screen1_model(),
            parser_review_payload=self.sample_parser_review_payload(),
            parser_governance_payload={},
            report_data={
                "run_history_id": "RUN-1",
                "metadata": {"awr_id": "AWR-1"},
            },
        )

    @staticmethod
    def sample_screen1_model() -> dict[str, object]:
        return {
            "header": {
                "run_history_id": "RUN-1",
                "awr_id": "AWR-1",
            },
            "intake_summary": {
                "total_files": 1,
                "processed": 1,
                "succeeded": 1,
                "failed": 0,
                "skipped": 0,
            },
            "parse_confidence_adaptation": {
                "parse_completeness_score": 0.91,
                "warnings_count": 1,
                "sections_detected": 12,
                "unknowns_captured": 1,
            },
            "report_rows": [],
            "validation_notes": {"notes": []},
        }

    @staticmethod
    def sample_parser_review_payload() -> dict[str, object]:
        return {
            "recent_unknowns": [
                {
                    "unknown_signal_id": "UNKNOWN-1",
                    "section_name": "Load Profile",
                    "signal_name": "Mystery Metric",
                    "raw_text": "Mystery Metric 42",
                    "review_status": "NEW",
                }
            ],
            "pattern_summary": [],
        }

    def test_dashboard_source_compiles(self) -> None:
        py_compile.compile(str(HTML_DASHBOARD_PATH), doraise=True)

    def test_parser_unknown_review_preview_panel_exists(self) -> None:
        source = read_text(HTML_DASHBOARD_PATH)
        rendered = self.render_screen1()
        for phrase in (
            "Screen 1 Parser Unknown Review Preview",
            "Mark Parser Gap",
            "Mark Source Gap",
            "Mark False Positive",
            "Mark Not Applicable",
            "Request Parser Mapping",
            "Route to Parser Backlog",
            "Add Review Note",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, source)
                self.assertIn(phrase, rendered)

    def test_controls_are_disabled_preview_only(self) -> None:
        source = read_text(HTML_DASHBOARD_PATH)
        rendered = self.render_screen1()
        for phrase in (
            "aria-disabled",
            "data-preview-only",
            "disabled-preview-only",
            "Parser unknown review disabled in this phase",
            "Preview only",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, source)
                self.assertIn(phrase, rendered)

    def test_safety_labels_exist(self) -> None:
        rendered = self.render_screen1()
        for phrase in (
            "No parser classification performed",
            "No parser mapping created",
            "No candidate created automatically",
            "No backlog item created",
            "No parser output changed",
            "No Phase 4I mutation",
            "No backend write",
            "No governed write path invoked",
            "Deterministic runtime remains authoritative",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_no_unsafe_backend_calls(self) -> None:
        source = lower_text(HTML_DASHBOARD_PATH)
        for phrase in (
            "fetch(",
            "xmlhttprequest",
            "method=\"post\"",
            "action=\"/",
            "persist_unknown_review",
            "create_parser_mapping",
            "create_parser_candidate",
            "update_parser_output",
            "mutate_phase4i",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, source)

    def test_preview_fields_exist(self) -> None:
        rendered = self.render_screen1()
        for phrase in (
            "unknown_signal_id",
            "parser_section",
            "signal_name",
            "review_decision",
            "review_status",
            "mapping_intent_type",
            "backlog_action",
            "actor required",
            "audit required",
            "governed write path required",
            "write_performed=false",
            "classification_persisted=false",
            "parser_mapping_created=false",
            "candidate_created=false",
            "backlog_item_created=false",
            "parser_output_mutation_requested=false",
            "phase4i_mutation_requested=false",
            "runtime_influence=false",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_docs_exist_and_contain_required_phrases(self) -> None:
        self.assertTrue(PANEL_DOC.is_file(), PANEL_DOC)
        text = lower_text(PANEL_DOC)
        for phrase in (
            "all controls are disabled/preview-only",
            "no parser unknown classification is persisted",
            "no parser mapping is created",
            "no parser candidate is created automatically",
            "no backlog item is created",
            "no parser output is changed",
            "no phase 4i mutation occurs",
            "no unsafe backend calls are added",
            "deterministic runtime remains authoritative",
            "phase 8 sizing/tco is not implemented",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
