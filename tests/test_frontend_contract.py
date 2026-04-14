from __future__ import annotations

import json
from datetime import datetime, timezone
import unittest

from src.analysis.frontend_contract import (
    build_frontend_contract,
    render_frontend_contract_json,
)
from src.models.decision import AwrDecision
from src.models.recommendation import ActionRecommendation


class FrontendContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generated_at = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)

    def _decision(self) -> AwrDecision:
        return AwrDecision(
            awr_id=701,
            overall_status="WARNING",
            primary_issue="CPU",
            secondary_issues=["IO", "MEMORY"],
            severity_score=52.5,
            confidence=0.83,
            evidence={
                "domain_scores": {
                    "CPU": 0.61,
                    "IO": 0.41,
                    "MEMORY": 0.36,
                    "COMMIT": 0.0,
                    "RAC": 0.0,
                    "ADG": 0.0,
                },
                "primary_reasons": [
                    "DB_CPU_PCT_DB_TIME is elevated at 72.00.",
                    "CPU_UTIL_P95 is elevated at 77.00.",
                ],
                "feature_evidence": {
                    "CPU": {
                        "DB_CPU_PCT_DB_TIME": 72.0,
                        "CPU_UTIL_P95": 77.0,
                    },
                    "IO": {
                        "READ_LATENCY_MS": 0.11,
                        "USER_IO_PRESSURE": 44.0,
                    },
                    "MEMORY": {
                        "HARD_PARSES_PER_SEC": 88.0,
                    },
                    "COMMIT": {
                        "LOG_FILE_SYNC_MS": 0.09,
                    },
                    "RAC": {
                        "CLUSTER_WAIT_PCT_DB_TIME": 5.5,
                    },
                    "ADG": {
                        "TRANSPORT_LAG_SEC": 45.0,
                    },
                },
                "anomaly_evidence": {
                    "IO": [
                        {
                            "metric_name": "READ_LATENCY_MS",
                            "anomaly_type": "SPIKE",
                            "anomaly_score": "MEDIUM",
                            "metric_value_num": 0.11,
                        }
                    ]
                },
                "score_evidence": {
                    "CPU": {"CPU": 61.0},
                },
            },
        )

    def _recommendations(self) -> list[ActionRecommendation]:
        return [
            ActionRecommendation(
                priority=1,
                issue="CPU",
                action="Investigate Top SQL",
                impact="HIGH",
                confidence=0.83,
                evidence={"source": "decision"},
            ),
            ActionRecommendation(
                priority=2,
                issue="IO",
                action="Analyze storage / read latency",
                impact="HIGH",
                confidence=0.79,
                evidence={"source": "decision"},
            ),
        ]

    def test_required_top_level_keys_exist(self) -> None:
        payload = build_frontend_contract(
            decision=self._decision(),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )

        self.assertEqual(
            list(payload.keys()),
            [
                "awr_id",
                "analysis",
                "evidence",
                "metrics",
                "anomalies",
                "recommendations",
                "metadata",
            ],
        )

    def test_analysis_block_structure(self) -> None:
        payload = build_frontend_contract(
            decision=self._decision(),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )

        self.assertEqual(
            payload["analysis"],
            {
                "status": "WARNING",
                "primary_issue": "CPU",
                "secondary_issues": ["IO", "MEMORY"],
                "severity_score": 52.5,
                "confidence": 0.83,
            },
        )

    def test_evidence_block_structure(self) -> None:
        payload = build_frontend_contract(
            decision=self._decision(),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )

        evidence = payload["evidence"]
        self.assertIn("domain_scores", evidence)
        self.assertIn("top_signals", evidence)
        self.assertIn("feature_evidence", evidence)
        self.assertIn("score_evidence", evidence)
        self.assertEqual(
            evidence["top_signals"],
            [
                "DB_CPU_PCT_DB_TIME is elevated at 72.00.",
                "CPU_UTIL_P95 is elevated at 77.00.",
            ],
        )

    def test_metrics_block_only_includes_present_known_fields(self) -> None:
        payload = build_frontend_contract(
            decision=self._decision(),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )

        self.assertEqual(
            payload["metrics"],
            {
                "cpu_pct": 72.0,
                "read_latency_ms": 0.11,
                "user_io_pressure": 44.0,
                "hard_parses_per_sec": 88.0,
                "log_file_sync_ms": 0.09,
                "cluster_wait_pct_db_time": 5.5,
                "transport_lag_sec": 45.0,
            },
        )

    def test_anomalies_always_present_as_list(self) -> None:
        payload = build_frontend_contract(
            decision=self._decision(),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )

        self.assertIsInstance(payload["anomalies"], list)
        self.assertEqual(payload["anomalies"][0]["issue"], "IO")

        no_anomaly_decision = self._decision()
        no_anomaly_decision.evidence["anomaly_evidence"] = {}
        no_anomaly_payload = build_frontend_contract(
            decision=no_anomaly_decision,
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )
        self.assertEqual(no_anomaly_payload["anomalies"], [])

    def test_recommendations_preserved_in_deterministic_order(self) -> None:
        payload = build_frontend_contract(
            decision=self._decision(),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )

        self.assertEqual(
            [item["action"] for item in payload["recommendations"]],
            [
                "Investigate Top SQL",
                "Analyze storage / read latency",
            ],
        )

    def test_metadata_present(self) -> None:
        payload = build_frontend_contract(
            decision=self._decision(),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )

        self.assertEqual(
            payload["metadata"],
            {
                "generated_at": "2026-04-14T12:00:00Z",
                "output_version": "phase4.frontend.v1",
                "source": "phase4",
            },
        )

    def test_deterministic_output_for_same_input(self) -> None:
        payload_one = build_frontend_contract(
            decision=self._decision(),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )
        payload_two = build_frontend_contract(
            decision=self._decision(),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )

        self.assertEqual(payload_one, payload_two)
        self.assertEqual(
            render_frontend_contract_json(payload_one),
            render_frontend_contract_json(payload_two),
        )
        rendered = json.loads(render_frontend_contract_json(payload_one))
        self.assertEqual(rendered["analysis"]["primary_issue"], "CPU")


if __name__ == "__main__":
    unittest.main()
