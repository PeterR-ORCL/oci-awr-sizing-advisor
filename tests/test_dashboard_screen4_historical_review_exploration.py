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


class DashboardScreen4HistoricalReviewExplorationTests(unittest.TestCase):
    def test_01_import_compile_safety(self) -> None:
        ast.parse(read_text(HTML_DASHBOARD_PATH), filename=str(HTML_DASHBOARD_PATH))
        ast.parse(read_text(AI_METADATA_PATH), filename=str(AI_METADATA_PATH))
        dashboard = dashboard_module()

        self.assertTrue(hasattr(dashboard, "_render_screen4_historical_exploration"))
        self.assertTrue(hasattr(dashboard, "_build_screen4_historical_exploration_model"))

    def test_screen4_historical_exploration_exists_with_summary_and_safety_labels(self) -> None:
        source = read_text(HTML_DASHBOARD_PATH)
        rendered = self.render_screen4()

        self.assertIn("Screen 4 Historical Review Exploration", source)
        self.assertIn("Screen 4 Historical Review Exploration", rendered)
        self.assertIn("data-dashboard-selected-summary", rendered)
        self.assertIn("Selected Historical Summary", rendered)
        self.assertIn("Read-only historical exploration", rendered)
        self.assertIn("Exploratory only", rendered)
        self.assertIn("No backend writes", rendered)
        self.assertIn("No approval controls", rendered)
        self.assertIn("No runtime activation", rendered)

    def test_selector_metadata_exists_for_historical_categories(self) -> None:
        rendered = self.render_screen4()

        required = (
            'data-dashboard-selectable="true"',
            'data-dashboard-select-type="historical-domain"',
            'data-dashboard-select-key="selectedDomain"',
            'data-dashboard-filter-key="selectedDomain"',
            'data-dashboard-filter-value="CPU"',
            'data-dashboard-select-domain="CPU"',
            'data-dashboard-select-type="historical-window"',
            'data-dashboard-select-key="selectedHistoricalWindow"',
            'data-dashboard-select-type="trend-metric"',
            'data-dashboard-select-key="selectedTrendMetric"',
            'data-dashboard-select-type="anomaly-group"',
            'data-dashboard-select-key="selectedAnomalyGroup"',
            'data-dashboard-select-type="distribution"',
            'data-dashboard-select-key="selectedDistribution"',
            'data-dashboard-select-type="similar-case"',
            'data-dashboard-select-key="selectedSimilarCase"',
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_authoritative_domain_controls_are_present(self) -> None:
        rendered = self.render_screen4()

        for domain in ("CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG"):
            with self.subTest(domain=domain):
                self.assertIn(f'data-dashboard-filter-value="{domain}"', rendered)
                self.assertIn(f">{domain}</span>", rendered)

    def test_required_safety_wording_is_rendered(self) -> None:
        rendered = self.render_screen4()

        required_phrases = (
            "Read-only historical exploration",
            "Exploratory only",
            "No backend writes",
            "Does not change historical truth",
            "Does not recalculate trends",
            "Does not reclassify anomalies",
            "Does not change baseline",
            "Does not change diagnostic truth",
            "Does not change recommendation truth",
            "Semantic/learning context is not historical evidence",
            "Selection only highlights deterministic historical context",
            "Cross-screen propagation remains future Phase 7H.8",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_no_unsafe_controls_or_write_runtime_are_introduced(self) -> None:
        dashboard = dashboard_module()
        rendered = self.render_screen4().lower()
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

    def test_no_semantic_learning_or_governance_historical_evidence(self) -> None:
        dashboard = dashboard_module()
        screen_4_source = inspect.getsource(dashboard._render_screen4_historical_exploration)
        rendered = self.render_screen4()

        forbidden = (
            "semantic recall as historical evidence",
            "semantic candidate context as historical evidence",
            "learning candidates as historical evidence",
            "governance status as historical evidence",
            "selectedLearningCandidate",
            "selectedSemanticItem",
            "selectedGovernanceItem",
        )
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, screen_4_source)
                self.assertNotIn(phrase, rendered)

        self.assertIn("Semantic/learning context is not historical evidence", rendered)

    def test_no_screen2_or_screen5_truth_drift(self) -> None:
        dashboard = dashboard_module()
        screen_2_source = inspect.getsource(dashboard._render_screen_2_page)
        screen_5_source = inspect.getsource(dashboard._render_screen_5_page)

        forbidden = (
            "selectedHistoricalWindow",
            "selectedTrendMetric",
            "selectedAnomalyGroup",
            "selectedDistribution",
            "selectedSimilarCase",
            "Screen 4 Historical Review Exploration",
            "historical exploration as recommendation truth",
        )
        for phrase in forbidden:
            with self.subTest(screen="screen_2", phrase=phrase):
                self.assertNotIn(phrase, screen_2_source)
            with self.subTest(screen="screen_5", phrase=phrase):
                self.assertNotIn(phrase, screen_5_source)

    def test_no_7h5_or_later_behavior_yet(self) -> None:
        source = read_text(HTML_DASHBOARD_PATH).lower()

        forbidden_phrases = (
            "screen 5 recommendation selector",
            "screen 5 recommendation/action exploration",
            "screen 1 governance selector",
            "screen 6 learning selector",
            "cross-screen propagation engine",
            "propagate selection to screen 5",
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
                self.assertNotIn("Screen 4 Historical Review Exploration", text)
                self.assertNotIn("DashboardInteractivityFoundation", text)

    def test_documentation_exists_and_contains_required_boundaries(self) -> None:
        doc_path = DOCS / "phase7_screen4_historical_review_exploration.md"
        self.assertTrue(doc_path.is_file())
        text = read_text(doc_path).lower()

        required_phrases = (
            "read-only",
            "exploratory only",
            "no backend writes",
            "no approval controls",
            "no write controls",
            "does not change historical truth",
            "does not recalculate trends",
            "does not reclassify anomalies",
            "does not change baseline",
            "does not change similarity results",
            "does not change diagnostic truth",
            "does not change recommendation truth",
            "semantic/learning context is not historical evidence",
            "full cross-screen propagation remains future 7h.8",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def render_screen4(self) -> str:
        return dashboard_module()._render_screen_4_page(
            self.sample_screen4_model(),
            chart_payload=self.sample_chart_payload(),
            violin_metric_groups=self.sample_violin_metric_groups(),
            time_series_groups=self.sample_time_series_groups(),
            derived_scalar_metrics={"pga_spill_pressure": 4.5},
        )

    @staticmethod
    def sample_screen4_model() -> dict[str, object]:
        return {
            "header": {
                "scope_label": "ORCL / 123456",
                "instance_name": "ORCL1",
                "host_name": "dbhost01",
                "snapshot_count": 4,
                "comparison_window": "4 snapshots / 2 hours",
            },
            "current_selection_summary": {
                "current_window": "Latest snapshot (10:00-11:00)",
                "comparison_mode": "Latest interval vs broader comparison window",
                "latest_vs_prior": "Latest interval aligns with the broader window.",
            },
            "historical_verdict": {
                "display_severity_label": "High",
                "historical_stability": "Mixed",
                "anomaly_burden": "2 anomaly windows",
                "historical_posture": "TUNE FIRST",
            },
            "normalized_decision": {
                "primary_issue": "CPU",
                "overall_status": "WARNING",
                "display_severity_label": "High",
                "confidence": 0.82,
                "domain_scores": {"CPU": 72.0, "IO": 18.0, "COMMIT": 12.0},
            },
            "historical_summary": {"summary": "CPU remained visible across the window."},
            "trend_review": {
                "trend_summary": {
                    "summary": "CPU trend remained visible.",
                    "findings": ["CPU stayed visible across snapshots."],
                }
            },
            "anomaly_review": {
                "anomalies": {"count": 2},
                "anomaly_summary": {
                    "windows": [
                        {"label": "snap-2 CPU anomaly", "severity": "medium"},
                        {"label": "snap-3 IO anomaly", "severity": "low"},
                    ]
                },
            },
            "comparison_review": {
                "latest_interval": "10:00-11:00",
                "worst_interval": "09:00-10:00",
                "latest_vs_trend": "Latest remains aligned with history.",
                "drift_summary": "No contradictory drift.",
            },
            "similarity_evidence": {
                "enabled": True,
                "similar_cases": [
                    {
                        "awr_id": 7002,
                        "db_name": "ORCL",
                        "similarity_score": 0.91,
                        "distance": 0.09,
                        "primary_signal_domain": "CPU",
                        "risk_level": "High",
                        "workload_class": "OLTP",
                    }
                ],
                "workload_cluster": {"cluster_label": "CPU-led OLTP"},
                "pattern_rarity": {"is_rare_pattern": False, "reason": "Common CPU-led case."},
                "anomaly_validation": {"supports_anomaly": True, "reason": "Similar cases exist."},
            },
            "visual_analysis": {"story": {"section_order": ["time_series", "violin"]}},
            "historical_scope_memory": {},
            "topology_platform_review": {},
            "explanation_panel": {},
        }

    @staticmethod
    def sample_chart_payload() -> dict[str, object]:
        return {
            "time_series_charts": {
                "snapshot_labels": ["snap-1", "snap-2", "snap-3", "snap-4"],
            },
            "violin_panel": {},
        }

    @staticmethod
    def sample_time_series_groups() -> list[dict[str, object]]:
        return [
            {
                "group_key": "cpu",
                "group_title": "CPU Time-Series Charts",
                "charts": [
                    {
                        "key": "cpu_trend",
                        "container_id": "timeSeriesCpuTrend",
                        "title": "DB CPU % DB Time",
                        "label": "DB CPU % DB time",
                        "color": "rgba(255, 107, 107, 0.92)",
                    }
                ],
            }
        ]

    @staticmethod
    def sample_violin_metric_groups() -> list[dict[str, object]]:
        return [
            {
                "group_key": "workload",
                "group_title": "Workload Distributions",
                "group_note": "Cluster-level workload values aggregated per snapshot.",
                "metrics": [
                    {
                        "payload_key": "cluster_cpu_pct_db_time",
                        "container_id": "violinClusterCpuPct",
                        "title": "Cluster CPU % DB Time",
                        "color": "rgba(255, 107, 107, 0.72)",
                    }
                ],
            }
        ]

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
