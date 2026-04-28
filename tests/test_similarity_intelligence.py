from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.analysis import similarity_intelligence as si


class SimilarityIntelligenceTests(unittest.TestCase):
    def test_similarity_score_clamps_negative_distance_to_one(self) -> None:
        self.assertEqual(si._compute_similarity_score(-0.0001), 1.0)

    def test_rare_pattern_true_when_no_similar_cases(self) -> None:
        rarity = si._build_pattern_rarity([])

        self.assertTrue(rarity["is_rare_pattern"])
        self.assertIsNone(rarity["nearest_distance"])
        self.assertEqual(
            rarity["threshold_used"],
            si.RARE_PATTERN_DISTANCE_THRESHOLD,
        )

    def test_rare_pattern_true_when_nearest_distance_exceeds_threshold(self) -> None:
        rarity = si._build_pattern_rarity([{"distance": 0.31}])

        self.assertTrue(rarity["is_rare_pattern"])
        self.assertEqual(rarity["nearest_distance"], 0.31)

    def test_rare_pattern_false_when_nearest_distance_within_threshold(self) -> None:
        rarity = si._build_pattern_rarity([{"distance": 0.25}, {"distance": 0.32}])

        self.assertFalse(rarity["is_rare_pattern"])
        self.assertEqual(rarity["nearest_distance"], 0.25)

    def test_workload_clustering_majority_vote_works(self) -> None:
        cluster = si._build_workload_cluster(
            [
                {"workload_class": "OLTP"},
                {"workload_class": "OLTP"},
                {"workload_class": "BATCH"},
            ]
        )

        self.assertEqual(cluster["cluster_label"], "OLTP")
        self.assertEqual(cluster["cluster_confidence"], 0.6667)

    def test_workload_clustering_returns_unclassified_with_no_cases(self) -> None:
        cluster = si._build_workload_cluster([])

        self.assertEqual(cluster["cluster_label"], "UNCLASSIFIED")
        self.assertEqual(cluster["cluster_confidence"], 0.0)

    def test_anomaly_validation_returns_inconclusive_with_no_cases(self) -> None:
        validation = si._build_anomaly_validation({}, [])

        self.assertFalse(validation["supports_anomaly"])
        self.assertEqual(validation["similar_case_count"], 0)
        self.assertIn("inconclusive", validation["reason"].lower())

    def test_recommendation_context_is_present_and_non_empty(self) -> None:
        context = si._build_recommendation_context(
            {"primary_signal_domain": "CPU"},
            [
                {
                    "awr_id": 101,
                    "distance": 0.08,
                    "similarity_score": 0.92,
                    "primary_signal_domain": "CPU",
                    "risk_level": "HIGH",
                }
            ],
        )

        self.assertTrue(context["similarity_explanation"])
        self.assertTrue(context["recommended_use"])
        self.assertTrue(context["supporting_cases"])

    def test_runtime_disable_env_var_behavior(self) -> None:
        with patch.dict(os.environ, {"DISABLE_SIMILARITY_INTELLIGENCE": "true"}, clear=False):
            self.assertTrue(si.is_similarity_intelligence_disabled())

    def test_build_similarity_intelligence_returns_expected_structure(self) -> None:
        with (
            patch.object(
                si,
                "find_similar_awrs_approx",
                return_value=[
                    {"awr_id": 100, "distance": 0.0},
                    {"awr_id": 101, "distance": 0.08},
                    {"awr_id": 102, "distance": 0.12},
                ],
            ),
            patch.object(
                si,
                "_load_similar_case_metadata",
                side_effect=[
                    {
                        100: {
                            "awr_id": 100,
                            "primary_signal_domain": "CPU",
                            "risk_level": "HIGH",
                            "total_score": 82.0,
                            "workload_class": "OLTP",
                            "topology_class": "RAC",
                            "platform_class": "EXADATA",
                            "event_class": "STEADY",
                            "db_name": "SRCDB",
                            "source_file_name": "source.out",
                        }
                    },
                    {
                        101: {
                            "awr_id": 101,
                            "primary_signal_domain": "CPU",
                            "risk_level": "HIGH",
                            "total_score": 80.0,
                            "workload_class": "OLTP",
                            "topology_class": "RAC",
                            "platform_class": "EXADATA",
                            "event_class": "STEADY",
                            "db_name": "SIM1",
                            "source_file_name": "sim1.out",
                        },
                        102: {
                            "awr_id": 102,
                            "primary_signal_domain": "CPU",
                            "risk_level": "HIGH",
                            "total_score": 78.0,
                            "workload_class": "OLTP",
                            "topology_class": "RAC",
                            "platform_class": "EXADATA",
                            "event_class": "STEADY",
                            "db_name": "SIM2",
                            "source_file_name": "sim2.out",
                        },
                    },
                ],
            ),
        ):
            result = si.build_similarity_intelligence(
                connection=object(),
                awr_id=100,
                feature_vector=[0.1, 0.2, 0.3],
                top_k=2,
            )

        self.assertTrue(result["enabled"])
        self.assertEqual(result["source_awr_id"], 100)
        self.assertEqual(len(result["similar_cases"]), 2)
        self.assertEqual(result["similar_cases"][0]["awr_id"], 101)
        self.assertIn("pattern_rarity", result)
        self.assertIn("anomaly_validation", result)
        self.assertIn("recommendation_context", result)
        self.assertIn("workload_cluster", result)


if __name__ == "__main__":
    unittest.main()
