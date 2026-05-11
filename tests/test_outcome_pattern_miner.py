from __future__ import annotations

import ast
from copy import deepcopy
import importlib
import os
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
MINER_PATH = ROOT / "src" / "learning" / "outcome_pattern_miner.py"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def miner_module():
    return importlib.import_module("src.learning.outcome_pattern_miner")


class OutcomePatternMinerTests(unittest.TestCase):
    def test_01_import_safety(self) -> None:
        before_environment = dict(os.environ)

        module = miner_module()

        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(module, "OutcomePatternMiner"))
        self.assertTrue(hasattr(module, "mine_outcome_patterns"))

    def test_empty_input_returns_no_patterns(self) -> None:
        module = miner_module()

        self.assertEqual(module.OutcomePatternMiner().mine_patterns({}), [])
        self.assertEqual(module.mine_outcome_patterns({}), [])

    def test_missing_optional_categories_are_tolerated(self) -> None:
        module = miner_module()
        miner = module.OutcomePatternMiner()

        examples = (
            {
                "unknown_signals": [
                    {"unknown_signal_id": "u1", "section": "SQL", "signature": "X"},
                    {"unknown_signal_id": "u2", "section": "SQL", "signature": "X"},
                ]
            },
            {
                "feedback": [
                    {"feedback_id": "f1", "feedback_text": "The wording is confusing."},
                    {"feedback_id": "f2", "feedback_text": "Confusing wording on evidence."},
                ]
            },
            {
                "runs": [
                    {"run_id": "r1", "primary_domain": "CPU"},
                    {"run_id": "r2", "domain": "cpu"},
                ]
            },
        )

        for records in examples:
            self.assertIsInstance(miner.mine_patterns(records), list)

    def test_repeated_unknown_signal_detection(self) -> None:
        module = miner_module()
        records = {
            "unknown_signals": [
                {
                    "unknown_signal_id": "u1",
                    "section": "SQL ordered by Elapsed Time",
                    "signature": "PX wait sample",
                },
                {
                    "unknown_signal_id": "u2",
                    "section": "SQL ordered by Elapsed Time",
                    "raw_signature": "PX wait sample",
                },
                {
                    "unknown_signal_id": "u3",
                    "section": "Wait Classes",
                    "signature": "single signal",
                },
            ]
        }

        patterns = module.mine_outcome_patterns(records)
        unknown_patterns = [
            pattern for pattern in patterns if pattern["pattern_type"] == "repeated_unknown_signal"
        ]

        self.assertEqual(len(unknown_patterns), 1)
        pattern = unknown_patterns[0]
        self.assertEqual(pattern["recurrence_count"], 2)
        self.assertFalse(pattern["runtime_influence"])
        self.assertTrue(pattern["requires_human_review"])
        self.assertEqual(pattern["suggested_candidate_type"], "parser_mapping_candidate")
        self.assertEqual(len(pattern["source_records"]), 2)

    def test_repeated_rejected_recommendation_detection(self) -> None:
        module = miner_module()
        records = {
            "recommendations": [
                {
                    "recommendation_id": "rec1",
                    "recommendation_type": "Gather optimizer statistics",
                    "recommendation_status": "REJECTED",
                },
                {
                    "recommendation_id": "rec2",
                    "recommendation": "gather optimizer statistics",
                    "disposition": "declined by DBA",
                },
                {
                    "recommendation_id": "rec3",
                    "recommendation": "gather optimizer statistics",
                    "recommendation_status": "ACCEPTED",
                },
            ]
        }

        patterns = module.mine_outcome_patterns(records)
        rejected = [
            pattern
            for pattern in patterns
            if pattern["pattern_type"] == "repeated_rejected_recommendation"
        ]

        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0]["recurrence_count"], 2)
        self.assertEqual(rejected[0]["suggested_candidate_type"], "recommendation_rule_candidate")

    def test_poor_outcome_after_action_detection(self) -> None:
        module = miner_module()
        records = {
            "actions": [
                {"action_history_id": 1, "action_type": "SQL_TUNING"},
                {"action_history_id": 2, "action_type": "sql tuning"},
                {"action_history_id": 3, "action_type": "CACHE_CHANGE"},
            ],
            "outcomes": [
                {"outcome_id": "o1", "action_history_id": 1, "outcome_status": "FAILED"},
                {
                    "outcome_id": "o2",
                    "action_history_id": 2,
                    "outcome_summary": "Latency worsened after the action.",
                },
                {"outcome_id": "o3", "action_history_id": 3, "outcome_status": "SUCCESS"},
            ],
        }

        patterns = module.mine_outcome_patterns(records)
        poor = [
            pattern for pattern in patterns if pattern["pattern_type"] == "poor_outcome_after_action"
        ]

        self.assertEqual(len(poor), 1)
        self.assertEqual(poor[0]["recurrence_count"], 2)
        self.assertFalse(poor[0]["runtime_influence"])

    def test_recurring_domain_issue_detection(self) -> None:
        module = miner_module()
        records = {
            "runs": [
                {"run_id": "r1", "primary_domain": "CPU"},
                {"run_id": "r2", "domain": "cpu"},
                {"run_id": "r3", "domain": "IO"},
            ]
        }

        patterns = module.mine_outcome_patterns(records)
        domains = [
            pattern for pattern in patterns if pattern["pattern_type"] == "recurring_domain_issue"
        ]

        self.assertEqual(len(domains), 1)
        self.assertEqual(domains[0]["affected_domain"], "CPU")
        self.assertEqual(domains[0]["recurrence_count"], 2)

    def test_repeated_feedback_theme_detection(self) -> None:
        module = miner_module()
        records = {
            "feedback": [
                {"feedback_id": "f1", "feedback_text": "The evidence wording is confusing."},
                {"feedback_id": "f2", "comment": "Confusing wording in the finding."},
                {"feedback_id": "f3", "feedback_text": "This looks like a false positive."},
            ]
        }

        patterns = module.mine_outcome_patterns(records)
        themes = [
            pattern for pattern in patterns if pattern["pattern_type"] == "repeated_feedback_theme"
        ]

        self.assertEqual(len(themes), 1)
        self.assertEqual(themes[0]["observed_effect"], "confusing wording")
        self.assertEqual(themes[0]["suggested_candidate_type"], "dashboard_wording_candidate")

    def test_deterministic_output_and_stable_order(self) -> None:
        module = miner_module()
        records = {
            "unknown_signals": [
                {"unknown_signal_id": "u2", "section": "SQL", "signature": "B"},
                {"unknown_signal_id": "u1", "section": "SQL", "signature": "B"},
            ],
            "feedback": [
                {"feedback_id": "f2", "feedback_text": "Recommendation not useful."},
                {"feedback_id": "f1", "feedback_text": "This recommendation is not useful."},
            ],
        }

        first = module.mine_outcome_patterns(records)
        second = module.mine_outcome_patterns(records)

        self.assertEqual(first, second)
        self.assertEqual(
            [pattern["pattern_type"] for pattern in first],
            ["repeated_unknown_signal", "repeated_feedback_theme"],
        )

    def test_confidence_model_is_deterministic_and_bounded(self) -> None:
        module = miner_module()
        unknown_signals = []
        for signature, count in (("two", 2), ("three", 3), ("four", 4), ("five", 5)):
            for index in range(count):
                unknown_signals.append(
                    {
                        "unknown_signal_id": f"{signature}-{index}",
                        "section": "SQL",
                        "signature": signature,
                    }
                )

        patterns = module.mine_outcome_patterns({"unknown_signals": unknown_signals})
        confidence_by_count = {
            pattern["recurrence_count"]: pattern["confidence"]
            for pattern in patterns
            if pattern["pattern_type"] == "repeated_unknown_signal"
        }

        self.assertEqual(confidence_by_count[2], 0.50)
        self.assertEqual(confidence_by_count[3], 0.65)
        self.assertEqual(confidence_by_count[4], 0.75)
        self.assertEqual(confidence_by_count[5], 0.85)
        for confidence in confidence_by_count.values():
            self.assertLessEqual(confidence, 0.95)
            self.assertNotEqual(confidence, 1.0)

    def test_source_evidence_is_present(self) -> None:
        module = miner_module()
        records = {
            "unknown_signals": [
                {"unknown_signal_id": "u1", "section": "SQL", "signature": "X"},
                {"unknown_signal_id": "u2", "section": "SQL", "signature": "X"},
            ],
            "feedback": [
                {"feedback_id": "f1", "feedback_text": "False positive."},
                {"feedback_id": "f2", "comment": "This is a false positive."},
            ],
        }

        patterns = module.mine_outcome_patterns(records)

        self.assertTrue(patterns)
        for pattern in patterns:
            self.assertTrue(pattern["source_records"])
            for source_record in pattern["source_records"]:
                self.assertIn("source_type", source_record)
                self.assertIn("normalized_key", source_record)

    def test_input_records_are_not_mutated(self) -> None:
        module = miner_module()
        records = {
            "runs": [{"run_id": "r1", "primary_domain": "CPU"}, {"run_id": "r2", "domain": "cpu"}],
            "unknown_signals": [
                {"unknown_signal_id": "u1", "section": "SQL", "signature": "X"},
                {"unknown_signal_id": "u2", "section": "SQL", "signature": "X"},
            ],
        }
        original = deepcopy(records)

        module.mine_outcome_patterns(records)

        self.assertEqual(records, original)

    def test_no_autonomous_function_names_exist_in_miner(self) -> None:
        text = read_text(MINER_PATH).lower()
        for forbidden_name in (
            "auto_apply",
            "autonomous_apply",
            "self_modify",
            "mutate_runtime",
            "update_parser_automatically",
            "update_scoring_automatically",
            "update_recommendations_automatically",
        ):
            self.assertNotIn(forbidden_name, text)

    def test_runtime_paths_do_not_import_learning_modules(self) -> None:
        runtime_paths = [
            ROOT / "scripts" / "run_analysis.py",
            ROOT / "src" / "parser",
            ROOT / "src" / "parsing",
            ROOT / "src" / "analysis",
            ROOT / "src" / "recommendation",
            ROOT / "src" / "recommendations",
            ROOT / "src" / "scoring",
            ROOT / "src" / "decision",
        ]

        checked_files: list[Path] = []
        for path in runtime_paths:
            if path.is_dir():
                checked_files.extend(sorted(path.rglob("*.py")))
            elif path.is_file():
                checked_files.append(path)

        self.assertTrue(checked_files, "expected at least one runtime file to inspect")
        for path in checked_files:
            self.assertNoLearningImports(path)

    def test_documentation_exists_and_contains_boundaries(self) -> None:
        path = DOCS / "phase7_outcome_pattern_mining.md"

        self.assertTrue(path.is_file())
        text = read_text(path).lower()
        for phrase in (
            "observational only",
            "pattern records are not learning candidates",
            "runtime_influence=false",
            "semantic recall is not used as evidence",
            "candidate model is future phase 7c",
            "candidate generation is future phase 7d",
            "dashboard interactivity remains future phase 7h",
        ):
            self.assertIn(phrase, text)

    def assertNoLearningImports(self, path: Path) -> None:
        text = read_text(path)
        tree = ast.parse(text, filename=str(path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertFalse(
                        self._is_learning_module(alias.name),
                        f"{path} imports {alias.name}",
                    )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                self.assertFalse(
                    self._is_learning_module(module),
                    f"{path} imports from {module}",
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
