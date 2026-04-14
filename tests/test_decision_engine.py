from __future__ import annotations

import unittest

from src.analysis.decision_engine import build_decision


class DecisionEngineTests(unittest.TestCase):
    def test_single_dominant_issue(self) -> None:
        decision = build_decision(
            awr_id=101,
            feature_vector={
                "feature_json": {
                    "DB_CPU_PCT_DB_TIME": 72.0,
                    "CPU_UTIL_P95": 91.0,
                }
            },
            score_result={"severity_score": 82.0, "confidence_score": 88.0},
        )

        self.assertEqual(decision.primary_issue, "CPU")
        self.assertEqual(decision.overall_status, "CRITICAL")
        self.assertEqual(decision.secondary_issues, [])
        self.assertGreaterEqual(decision.confidence, 0.88)

    def test_tie_resolution_uses_fixed_domain_order(self) -> None:
        decision = build_decision(
            awr_id=102,
            feature_vector={
                "feature_json": {
                    "READ_LATENCY_MS": 0.08,
                    "USER_IO_PRESSURE": 25.0,
                    "DB_CPU_PCT_DB_TIME": 75.0,
                    "CPU_UTIL_P95": 75.0,
                }
            },
        )

        self.assertEqual(decision.primary_issue, "CPU")
        self.assertIn("IO", decision.secondary_issues)

    def test_multiple_secondary_issues_are_preserved(self) -> None:
        decision = build_decision(
            awr_id=103,
            feature_vector={
                "feature_json": {
                    "DB_CPU_PCT_DB_TIME": 75.0,
                    "CPU_UTIL_P95": 75.0,
                    "READ_LATENCY_MS": 0.12,
                    "LOG_FILE_SYNC_MS": 6.0,
                    "TRANSPORT_LAG_SEC": 360.0,
                }
            },
            trend_rows=[
                {
                    "metric_name": "TRANSPORT_LAG_SEC",
                    "anomaly_flag": "Y",
                    "anomaly_type": "SPIKE",
                    "anomaly_score": "HIGH",
                    "metric_value_num": 360.0,
                }
            ],
        )

        self.assertEqual(decision.primary_issue, "ADG")
        self.assertEqual(decision.secondary_issues, ["CPU", "IO", "COMMIT"])

    def test_low_severity_maps_to_ok(self) -> None:
        decision = build_decision(
            awr_id=104,
            feature_vector={"feature_json": {}},
            score_result={"severity_score": 10.0, "confidence_score": 40.0},
        )

        self.assertEqual(decision.overall_status, "OK")
        self.assertEqual(decision.severity_score, 10.0)

    def test_medium_severity_maps_to_warning(self) -> None:
        decision = build_decision(
            awr_id=105,
            feature_vector={"feature_json": {"LOG_FILE_SYNC_MS": 3.0}},
            score_result={"severity_score": 42.0, "confidence_score": 55.0},
        )

        self.assertEqual(decision.primary_issue, "COMMIT")
        self.assertEqual(decision.overall_status, "WARNING")
        self.assertEqual(decision.severity_score, 45.0)

    def test_high_severity_maps_to_critical(self) -> None:
        decision = build_decision(
            awr_id=106,
            feature_vector={"feature_json": {"TRANSPORT_LAG_SEC": 420.0}},
            score_result={"severity_score": 78.0, "confidence_score": 61.0},
        )

        self.assertEqual(decision.primary_issue, "ADG")
        self.assertEqual(decision.overall_status, "CRITICAL")
        self.assertEqual(decision.severity_score, 78.0)

    def test_diagnostics_structure_is_available_when_enabled(self) -> None:
        decision = build_decision(
            awr_id=107,
            feature_vector={
                "feature_json": {
                    "DB_CPU_PCT_DB_TIME": 75.0,
                    "CPU_UTIL_P95": 75.0,
                    "READ_LATENCY_MS": 0.12,
                }
            },
            include_diagnostics=True,
        )

        diagnostics = decision.evidence.get("decision_diagnostics")
        self.assertIsInstance(diagnostics, dict)
        self.assertEqual(
            set(diagnostics["domain_diagnostics"].keys()),
            {"CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG"},
        )
        self.assertTrue(
            diagnostics["domain_diagnostics"]["CPU"]["qualified_for_primary"]
        )
        self.assertTrue(
            diagnostics["domain_diagnostics"]["IO"]["qualified_for_primary"]
        )
        self.assertEqual(
            diagnostics["final_ranked_domains"][0],
            decision.primary_issue,
        )
        self.assertIsInstance(
            diagnostics["ordered_candidates_pre_tiebreak"],
            list,
        )

    def test_healthy_baseline_normalizes_to_ok_without_qualifying_domains(self) -> None:
        decision = build_decision(
            awr_id=108,
            feature_vector={
                "feature_json": {
                    "DB_CPU_PCT_DB_TIME": 60.0,
                    "CPU_UTIL_P95": 60.0,
                    "READ_LATENCY_MS": 0.0354,
                    "USER_IO_PRESSURE": 10.0,
                    "COMMIT_PRESSURE": 4.7,
                }
            },
        )

        self.assertEqual(decision.overall_status, "OK")
        self.assertEqual(decision.primary_issue, "CPU")
        self.assertLess(decision.evidence["domain_scores"]["CPU"], 0.35)

    def test_healthy_recovery_normalizes_to_ok_without_qualifying_domains(self) -> None:
        decision = build_decision(
            awr_id=109,
            feature_vector={
                "feature_json": {
                    "DB_CPU_PCT_DB_TIME": 60.3448,
                    "CPU_UTIL_P95": 60.3448,
                    "READ_LATENCY_MS": 0.0277,
                    "USER_IO_PRESSURE": 9.3,
                    "COMMIT_PRESSURE": 4.5,
                }
            },
        )

        self.assertEqual(decision.overall_status, "OK")
        self.assertLess(decision.evidence["domain_scores"]["CPU"], 0.35)

    def test_io_moderate_can_qualify_as_io(self) -> None:
        decision = build_decision(
            awr_id=110,
            feature_vector={
                "feature_json": {
                    "DB_CPU_PCT_DB_TIME": 41.4634,
                    "CPU_UTIL_P95": 41.4634,
                    "READ_LATENCY_MS": 0.0781,
                    "USER_IO_PRESSURE": 43.9,
                }
            },
        )

        self.assertEqual(decision.primary_issue, "IO")
        self.assertGreaterEqual(decision.evidence["domain_scores"]["IO"], 0.35)
        self.assertLess(decision.evidence["domain_scores"]["CPU"], 0.35)

    def test_io_severe_can_qualify_as_io(self) -> None:
        decision = build_decision(
            awr_id=111,
            feature_vector={
                "feature_json": {
                    "DB_CPU_PCT_DB_TIME": 27.9661,
                    "CPU_UTIL_P95": 27.9661,
                    "READ_LATENCY_MS": 0.1271,
                    "USER_IO_PRESSURE": 67.4,
                }
            },
        )

        self.assertEqual(decision.primary_issue, "IO")
        self.assertEqual(decision.overall_status, "CRITICAL")
        self.assertGreaterEqual(decision.evidence["domain_scores"]["IO"], 0.45)

    def test_adg_lag_and_flags_can_qualify_as_adg(self) -> None:
        decision = build_decision(
            awr_id=114,
            feature_vector={
                "feature_json": {
                    "DB_CPU_PCT_DB_TIME": 42.0,
                    "CPU_UTIL_P95": 42.0,
                    "NETWORK_WAIT_PCT_DB_TIME": 20.7,
                    "REDO_TRANSPORT_ISSUE_FLAG": 1.0,
                    "POST_FAILOVER_RECOVERY_FLAG": 1.0,
                }
            },
        )

        self.assertEqual(decision.primary_issue, "ADG")
        self.assertGreaterEqual(decision.evidence["domain_scores"]["ADG"], 0.45)

    def test_memory_severe_can_qualify_as_memory(self) -> None:
        decision = build_decision(
            awr_id=112,
            feature_vector={
                "feature_json": {
                    "DB_CPU_PCT_DB_TIME": 31.1475,
                    "CPU_UTIL_P95": 31.1475,
                    "HARD_PARSES_PER_SEC": 110.0,
                }
            },
        )

        self.assertEqual(decision.primary_issue, "MEMORY")
        self.assertGreaterEqual(decision.evidence["domain_scores"]["MEMORY"], 0.45)

    def test_mixed_cpu_memory_commit_can_qualify_multiple_domains(self) -> None:
        decision = build_decision(
            awr_id=115,
            feature_vector={
                "feature_json": {
                    "DB_CPU_PCT_DB_TIME": 75.0,
                    "CPU_UTIL_P95": 75.0,
                    "HARD_PARSES_PER_SEC": 110.0,
                    "COMMIT_PRESSURE": 17.9,
                }
            },
        )

        self.assertEqual(decision.primary_issue, "CPU")
        self.assertIn("MEMORY", decision.secondary_issues)
        self.assertIn("COMMIT", decision.secondary_issues)


if __name__ == "__main__":
    unittest.main()
