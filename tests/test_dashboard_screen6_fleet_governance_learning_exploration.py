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


class DashboardScreen6FleetGovernanceLearningExplorationTests(unittest.TestCase):
    def test_01_import_compile_safety(self) -> None:
        ast.parse(read_text(HTML_DASHBOARD_PATH), filename=str(HTML_DASHBOARD_PATH))
        ast.parse(read_text(AI_METADATA_PATH), filename=str(AI_METADATA_PATH))
        dashboard = dashboard_module()

        self.assertTrue(hasattr(dashboard, "_render_screen6_fleet_governance_learning_exploration"))
        self.assertTrue(hasattr(dashboard, "_build_screen6_fleet_governance_learning_exploration_model"))

    def test_screen6_fleet_governance_learning_exploration_exists_with_summary_and_safety_labels(self) -> None:
        source = read_text(HTML_DASHBOARD_PATH)
        rendered = self.render_screen6()

        self.assertIn("Screen 6 Fleet / Governance / Semantic / Learning Exploration", source)
        self.assertIn("Screen 6 Fleet / Governance / Semantic / Learning Exploration", rendered)
        self.assertIn("data-dashboard-selected-summary", rendered)
        self.assertIn("Selected Screen 6 Summary", rendered)
        self.assertIn("Read-only fleet/governance/semantic/learning exploration", rendered)
        self.assertIn("Exploratory only", rendered)
        self.assertIn("No backend writes", rendered)
        self.assertIn("No approval controls", rendered)
        self.assertIn("No runtime activation", rendered)

    def test_selector_metadata_exists_for_fleet_governance_semantic_and_learning_context(self) -> None:
        rendered = self.render_screen6()

        required = (
            'data-dashboard-selectable="true"',
            'data-dashboard-select-type="fleet-group"',
            'data-dashboard-select-key="selectedFleetGroup"',
            'data-dashboard-filter-key="selectedFleetGroup"',
            'data-dashboard-select-type="governance-item"',
            'data-dashboard-select-key="selectedGovernanceItem"',
            'data-dashboard-select-type="unknown-signal"',
            'data-dashboard-select-key="selectedUnknownSignal"',
            'data-dashboard-select-type="knowledge-request"',
            'data-dashboard-select-key="selectedKnowledgeRequest"',
            'data-dashboard-select-type="artifact"',
            'data-dashboard-select-key="selectedArtifact"',
            'data-dashboard-select-type="semantic-item"',
            'data-dashboard-select-key="selectedSemanticItem"',
            'data-dashboard-select-type="learning-candidate"',
            'data-dashboard-select-key="selectedLearningCandidate"',
            'data-dashboard-select-type="learning-candidate-status"',
            'data-dashboard-select-key="selectedLearningCandidateStatus"',
            'data-dashboard-select-type="learning-candidate-type"',
            'data-dashboard-select-key="selectedLearningCandidateType"',
            'data-dashboard-select-type="outcome-pattern"',
            'data-dashboard-select-key="selectedOutcomePattern"',
            'data-dashboard-select-type="action-effectiveness-pattern"',
            'data-dashboard-select-key="selectedActionEffectivenessPattern"',
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_authoritative_domain_controls_are_present(self) -> None:
        rendered = self.render_screen6()

        for domain in ("CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG"):
            with self.subTest(domain=domain):
                self.assertIn(f'data-dashboard-filter-value="{domain}"', rendered)
                self.assertIn(f">{domain}</span>", rendered)

    def test_required_safety_wording_is_rendered(self) -> None:
        rendered = self.render_screen6()

        required_phrases = (
            "Read-only fleet/governance/semantic/learning exploration",
            "Exploratory only",
            "No backend writes",
            "Does not change fleet posture",
            "Does not change governance state",
            "Does not classify unknown signals",
            "Does not materialize artifacts",
            "Does not change diagnostic truth",
            "Does not change recommendation truth",
            "Semantic context is reviewer-assist only",
            "Semantic context is non-authoritative",
            "Semantic context is not diagnostic evidence",
            "Semantic context is not recommendation truth",
            "Learning candidates are proposal/review context only",
            "Learning candidates are not diagnostic evidence",
            "Learning candidates are not recommendation truth",
            "Pattern records are not candidates",
            "runtime_influence=false",
            "requires_human_review=true",
            "Cross-screen propagation remains future Phase 7H.8",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rendered)

    def test_no_unsafe_controls_or_write_runtime_are_introduced(self) -> None:
        dashboard = dashboard_module()
        rendered = self.render_screen6().lower()
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
            "candidate-status-mutation-control",
            "governance-status-mutation-control",
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

    def test_no_governance_candidate_or_artifact_mutation_code_paths(self) -> None:
        dashboard = dashboard_module()
        screen_6_source = inspect.getsource(dashboard._render_screen6_fleet_governance_learning_exploration).lower()
        screen_6_source += inspect.getsource(dashboard._build_screen6_fleet_governance_learning_exploration_model).lower()

        forbidden = (
            "create_parser_mapping",
            "update_parser_mapping",
            "update_unknown_signal",
            "classify_unknown_signal",
            "update_governance_state",
            "update_candidate_status",
            "approvelearningcandidate",
            "rejectlearningcandidate",
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
                self.assertNotIn(phrase, screen_6_source)

    def test_no_semantic_learning_or_governance_evidence_drift(self) -> None:
        dashboard = dashboard_module()
        screen_6_source = inspect.getsource(dashboard._render_screen6_fleet_governance_learning_exploration)
        rendered = self.render_screen6()

        forbidden = (
            "semantic recall as diagnostic evidence",
            "semantic recall as recommendation truth",
            "learning candidates as diagnostic evidence",
            "learning candidates as recommendation truth",
            "governance review as diagnostic evidence",
            "governance review as recommendation truth",
        )
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, screen_6_source)
                self.assertNotIn(phrase, rendered)

        self.assertIn("Semantic context is not diagnostic evidence", rendered)
        self.assertIn("Semantic context is not recommendation truth", rendered)
        self.assertIn("Learning candidates are not diagnostic evidence", rendered)
        self.assertIn("Learning candidates are not recommendation truth", rendered)

    def test_no_screen1_screen2_screen4_or_screen5_truth_drift(self) -> None:
        dashboard = dashboard_module()
        screen_sources = {
            "screen_1": inspect.getsource(dashboard._render_screen_1_page),
            "screen_2": inspect.getsource(dashboard._render_screen_2_page),
            "screen_4": inspect.getsource(dashboard._render_screen_4_page),
            "screen_5": inspect.getsource(dashboard._render_screen_5_page),
        }

        forbidden = (
            "selectedFleetGroup",
            "selectedLearningCandidateStatus",
            "selectedLearningCandidateType",
            "selectedOutcomePattern",
            "selectedActionEffectivenessPattern",
            "Screen 6 Fleet / Governance / Semantic / Learning Exploration",
            "screen 6 selection as diagnostic truth",
            "screen 6 selection as recommendation truth",
            "screen 6 selection as parser truth",
            "screen 6 selection as historical truth",
        )
        for screen, source in screen_sources.items():
            for phrase in forbidden:
                with self.subTest(screen=screen, phrase=phrase):
                    self.assertNotIn(phrase, source)

    def test_no_7h8_behavior_yet(self) -> None:
        source = read_text(HTML_DASHBOARD_PATH).lower()

        forbidden_phrases = (
            "cross-screen propagation engine",
            "synchronize all screens",
            "backend state persistence",
            "dashboard write path",
            "cli learning command",
            "phase 7i cli learning",
            "propagate selection to screen 1",
            "propagate selection to screen 2",
            "propagate selection to screen 3",
            "propagate selection to screen 4",
            "propagate selection to screen 5",
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
                self.assertNotIn("Screen 6 Fleet / Governance / Semantic / Learning Exploration", text)
                self.assertNotIn("DashboardInteractivityFoundation", text)

    def test_documentation_exists_and_contains_required_boundaries(self) -> None:
        doc_path = DOCS / "phase7_screen6_fleet_governance_learning_exploration.md"
        self.assertTrue(doc_path.is_file())
        text = read_text(doc_path).lower()

        required_phrases = (
            "read-only",
            "exploratory only",
            "no backend writes",
            "no approval controls",
            "no write controls",
            "does not change fleet posture",
            "does not change governance state",
            "does not classify unknown signals",
            "does not materialize artifacts",
            "does not change diagnostic truth",
            "does not change recommendation truth",
            "semantic context is reviewer-assist only",
            "semantic context is non-authoritative",
            "semantic context is not diagnostic evidence",
            "semantic context is not recommendation truth",
            "learning candidates are proposal/review context only",
            "learning candidates are not diagnostic evidence",
            "learning candidates are not recommendation truth",
            "pattern records are not candidates",
            "full cross-screen propagation remains future 7h.8",
        )
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def render_screen6(self) -> str:
        return dashboard_module()._render_screen_6_page(
            self.sample_screen6_model(),
            governance_payload=self.sample_governance_payload(),
            semantic_recall_payload=self.sample_semantic_payload(),
            learning_visibility_payload=self.sample_learning_payload(),
        )

    @staticmethod
    def sample_screen6_model() -> dict[str, object]:
        return {
            "similarity_enabled": True,
            "header": {
                "scope_label": "ORCL / 123456",
                "db_name": "ORCL",
                "dbid": "123456",
                "instance_name": "ORCL1",
                "host_name": "dbhost01",
                "snapshot_count": 4,
                "comparison_window": "2 hours",
                "awr_id": 7001,
                "run_history_id": 42,
            },
            "fleet_summary": {
                "cluster_label": "CPU-bound peers",
                "cluster_confidence": 0.72,
                "similar_awrs": 2,
                "rarity": "common",
            },
            "clusters": {
                "similar_cases": [
                    {
                        "awr_id": 7002,
                        "db_name": "ORCL",
                        "dbid": "123456",
                        "host_name": "peer01",
                        "distance": 0.12,
                    }
                ]
            },
            "rare_patterns": {
                "is_rare_pattern": False,
                "nearest_distance": 0.12,
                "mean_distance": 0.34,
                "reason": "CPU peer group is established.",
            },
            "anomaly_validation": {
                "supports_anomaly": True,
                "similar_case_count": 2,
                "reason": "CPU peers support the visible anomaly.",
            },
            "repeated_issues": [{"issue": "CPU", "count": 2}],
            "recommendation_backlog": [{"issue": "CPU", "count": 1}],
            "outliers": [
                {
                    "awr_id": 7010,
                    "db_name": "ORCL",
                    "dbid": "123456",
                    "host_name": "outlier01",
                    "distance": 0.55,
                }
            ],
            "outcome_patterns": [
                {
                    "pattern_id": "OP-001",
                    "domain": "CPU",
                    "summary": "CPU tuning improved elapsed time.",
                }
            ],
            "action_effectiveness_patterns": [
                {
                    "pattern_id": "AE-001",
                    "domain": "CPU",
                    "summary": "SQL tuning was effective for prior CPU cases.",
                }
            ],
        }

    @staticmethod
    def sample_governance_payload() -> dict[str, object]:
        return {
            "available": True,
            "unknown_signal_summary": {"TOTAL": 3, "PENDING_REVIEW": 1, "APPROVED": 1, "REJECTED": 0},
            "approval_summary": {"PENDING": 1, "APPROVED": 1, "REJECTED": 0, "NEEDS_REVIEW": 0},
            "artifact_summary": {"INACTIVE": 1, "READY": 0, "ACTIVE": 0, "TOTAL": 1, "MATERIALIZED": 1},
            "workflow_summary": {"NEW": 1, "PENDING": 1, "APPROVED": 1, "REJECTED": 0},
            "linkage": [
                {
                    "request_id": "KR-001",
                    "source_type": "UNKNOWN_SIGNAL",
                    "source_id": 11,
                    "run_history_id": 42,
                    "approval_status": "PENDING",
                    "artifact_id": "KA-001",
                    "artifact_classification": "parser_mapping",
                    "activation_status": "INACTIVE",
                }
            ],
        }

    @staticmethod
    def sample_semantic_payload() -> dict[str, object]:
        return {
            "enabled": True,
            "provider": "Oracle Agent Memory",
            "mode": "offline metadata",
            "authoritative": False,
            "runtime_influence": False,
            "status_message": "Reviewer assist only.",
            "assist_scope": ["Reviewer context", "Governance assist"],
            "latest_context": [
                {
                    "query": "CPU wait context",
                    "count": 2,
                    "summary": "Reviewer assist only for CPU context.",
                }
            ],
        }

    @staticmethod
    def sample_learning_payload() -> dict[str, object]:
        return {
            "candidate_count": 1,
            "status_counts": {"PROPOSED": 1},
            "type_counts": {"recommendation_tuning_candidate": 1},
            "affected_domain_counts": {"CPU": 1},
            "semantic_context_count": 1,
            "candidates": [
                {
                    "candidate_id": "LC-001",
                    "candidate_type": "recommendation_tuning_candidate",
                    "status": "PROPOSED",
                    "affected_domain": "CPU",
                    "title": "Tune SQL candidate",
                    "runtime_influence": False,
                    "requires_human_review": True,
                }
            ],
            "governance": {"records": []},
            "outcome_patterns": [
                {
                    "pattern_id": "OP-L001",
                    "domain": "IO",
                    "summary": "Outcome pattern context only.",
                }
            ],
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
