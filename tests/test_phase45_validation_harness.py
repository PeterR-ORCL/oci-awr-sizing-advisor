from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from src.models.decision import AwrDecision
from src.models.recommendation import ActionRecommendation
import src.validation.phase45_validation_harness as harness_module
from src.validation.phase45_validation_harness import (
    load_manifest_entries,
    main,
    normalize_decision_for_validation,
    run_validation_harness,
)

CSV_HEADER = (
    "begin_time,db_name,dbid,expected_primary_issue,expected_secondary_issues,"
    "expected_status,file,notes,scenario_name\n"
)

CSV_HEADER_NATIVE = (
    "filename,scenario_name,expected_primary_issue,expected_status,"
    "expected_secondary_issues,notes\n"
)


class Phase45ValidationHarnessTests(unittest.TestCase):
    def test_manifest_csv_preferred_over_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "manifest.csv").write_text(
                CSV_HEADER
                + "2026-04-01 00:00:00,VALDB,1,CPU,,WARNING,case_a.out,note,CSV_CASE\n",
                encoding="utf-8",
            )
            (root / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "begin_time": "2026-04-01 00:00:00",
                            "db_name": "VALDB",
                            "dbid": 1,
                            "expected_primary_issue": "IO",
                            "expected_secondary_issues": "",
                            "expected_status": "WARNING",
                            "file": "case_b.out",
                            "notes": "note",
                            "scenario_name": "JSON_CASE",
                        }
                    ]
                ),
                encoding="utf-8",
            )
            entries, manifest_source = load_manifest_entries(root)

        self.assertEqual(entries[0].scenario_name, "CSV_CASE")
        self.assertTrue(manifest_source.endswith("manifest.csv"))

    def test_explicit_manifest_path_overrides_directory_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "manifest.csv").write_text(
                CSV_HEADER
                + "2026-04-01 00:00:00,VALDB,1,CPU,,WARNING,case_a.out,note,CSV_CASE\n",
                encoding="utf-8",
            )
            explicit_manifest = root / "override.json"
            explicit_manifest.write_text(
                json.dumps(
                    [
                        {
                            "begin_time": "2026-04-01 00:00:00",
                            "db_name": "VALDB",
                            "dbid": 1,
                            "expected_primary_issue": "IO",
                            "expected_secondary_issues": "",
                            "expected_status": "WARNING",
                            "file": "case_b.out",
                            "notes": "note",
                            "scenario_name": "JSON_OVERRIDE",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            entries, manifest_source = load_manifest_entries(
                root,
                manifest_path=explicit_manifest,
            )

        self.assertEqual(entries[0].scenario_name, "JSON_OVERRIDE")
        self.assertTrue(manifest_source.endswith("override.json"))

    def test_new_manifest_schema_with_filename_and_no_begin_time_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "manifest.csv").write_text(
                CSV_HEADER_NATIVE
                + "case_b.out,CSV_NATIVE,IO,WARNING,,native note\n",
                encoding="utf-8",
            )

            entries, manifest_source = load_manifest_entries(root)

        self.assertTrue(manifest_source.endswith("manifest.csv"))
        self.assertEqual(entries[0].file, "case_b.out")
        self.assertEqual(entries[0].scenario_name, "CSV_NATIVE")
        self.assertIsNone(entries[0].begin_time)

    def test_manifest_order_is_deterministic_when_begin_time_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "manifest.csv").write_text(
                CSV_HEADER_NATIVE
                + "case_b.out,SCENARIO_B,IO,WARNING,,note b\n"
                + "case_a.out,SCENARIO_A,CPU,CRITICAL,,note a\n",
                encoding="utf-8",
            )

            entries, _ = load_manifest_entries(root)

        self.assertEqual(
            [entry.scenario_name for entry in entries],
            ["SCENARIO_B", "SCENARIO_A"],
        )
        self.assertEqual([entry.file for entry in entries], ["case_b.out", "case_a.out"])


    def test_expected_primary_issue_none_is_supported(self) -> None:
        decision = AwrDecision(
            awr_id=1,
            overall_status="OK",
            primary_issue="CPU",
            secondary_issues=[],
            severity_score=10.0,
            confidence=0.5,
            evidence={
                "domain_scores": {
                    domain: 0.0
                    for domain in ["CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG"]
                }
            },
        )

        actual_primary_issue, actual_secondary_issues = normalize_decision_for_validation(
            decision
        )

        self.assertEqual(actual_primary_issue, "NONE")
        self.assertEqual(actual_secondary_issues, [])

    def test_local_harness_runs_with_injected_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "manifest.csv").write_text(
                CSV_HEADER
                + "2026-04-01 00:00:00,VALDB,1,CPU,,WARNING,case_a.out,note,CASE_A\n",
                encoding="utf-8",
            )
            (root / "case_a.out").write_text("stub", encoding="utf-8")

            def parser(file_path: str | Path) -> dict[str, str]:
                return {"file_path": str(file_path)}

            def feature_vector_builder(
                parse_result: dict[str, str],
                awr_id: int,
                source_system_id: int,
            ) -> dict[str, str]:
                del parse_result, awr_id, source_system_id
                return {"feature_json": json.dumps({"DB_CPU_PCT_DB_TIME": 45.0})}

            def decision_builder(**kwargs: object) -> AwrDecision:
                del kwargs
                return AwrDecision(
                    awr_id=1,
                    overall_status="WARNING",
                    primary_issue="CPU",
                    secondary_issues=[],
                    severity_score=35.0,
                    confidence=0.71,
                    evidence={"domain_scores": {"CPU": 0.4}},
                )

            def recommendation_builder(
                decision: AwrDecision,
            ) -> list[ActionRecommendation]:
                del decision
                return [
                    ActionRecommendation(
                        priority=1,
                        issue="CPU",
                        action="Investigate Top SQL",
                        impact="HIGH",
                        confidence=0.71,
                        evidence={},
                    )
                ]

            def output_builder(**kwargs: object) -> dict[str, object]:
                return dict(kwargs)

            result = run_validation_harness(
                input_dir=root,
                parser=parser,
                feature_vector_builder=feature_vector_builder,
                decision_builder=decision_builder,
                recommendation_builder=recommendation_builder,
                output_builder=output_builder,
            )

        self.assertEqual(result.case_count, 1)
        self.assertEqual(result.passed_count, 1)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.cases[0].actual_primary_issue, "CPU")
        self.assertEqual(result.cases[0].actual_secondary_issues, [])
        diagnostics = result.cases[0].validation_diagnostics
        self.assertIsInstance(diagnostics, dict)
        self.assertFalse(diagnostics["normalized_to_none"])
        self.assertIsNone(diagnostics["decision_diagnostics"])
        self.assertEqual(
            result.cases[0].output.get("validation_diagnostics"),
            diagnostics,
        )

    def test_manifest_none_expectation_passes_through_harness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "manifest.csv").write_text(
                CSV_HEADER
                + "2026-04-02 00:00:00,TRENDDB,7,NONE,,OK,case_none.out,note,CASE_NONE\n",
                encoding="utf-8",
            )
            (root / "case_none.out").write_text("stub", encoding="utf-8")

            def parser(file_path: str | Path) -> dict[str, str]:
                return {"file_path": str(file_path)}

            def feature_vector_builder(
                parse_result: dict[str, str],
                awr_id: int,
                source_system_id: int,
            ) -> dict[str, str]:
                del parse_result, awr_id, source_system_id
                return {"feature_json": json.dumps({"DB_CPU_PCT_DB_TIME": 5.0})}

            def decision_builder(**kwargs: object) -> AwrDecision:
                del kwargs
                return AwrDecision(
                    awr_id=1,
                    overall_status="OK",
                    primary_issue="CPU",
                    secondary_issues=[],
                    severity_score=10.0,
                    confidence=0.82,
                    evidence={
                        "domain_scores": {
                            "CPU": 0.0,
                            "IO": 0.0,
                            "MEMORY": 0.0,
                            "COMMIT": 0.0,
                            "RAC": 0.0,
                            "ADG": 0.0,
                        }
                    },
                )

            result = run_validation_harness(
                input_dir=root,
                parser=parser,
                feature_vector_builder=feature_vector_builder,
                decision_builder=decision_builder,
                recommendation_builder=lambda decision: [],
                output_builder=lambda **kwargs: dict(kwargs),
            )

        self.assertEqual(result.passed_count, 1)
        self.assertEqual(result.failed_count, 0)
        self.assertEqual(result.cases[0].actual_primary_issue, "NONE")
        self.assertEqual(result.cases[0].actual_status, "OK")
        diagnostics = result.cases[0].validation_diagnostics
        self.assertIsInstance(diagnostics, dict)
        self.assertTrue(diagnostics["normalized_to_none"])
        self.assertEqual(
            result.cases[0].output.get("validation_diagnostics"),
            diagnostics,
        )

    def test_harness_captures_decision_diagnostics_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "manifest.csv").write_text(
                CSV_HEADER
                + "2026-04-01 00:00:00,VALDB,1,CPU,,WARNING,case_a.out,note,CASE_A\n",
                encoding="utf-8",
            )
            (root / "case_a.out").write_text("stub", encoding="utf-8")

            def parser(file_path: str | Path) -> dict[str, str]:
                return {"file_path": str(file_path)}

            def feature_vector_builder(
                parse_result: dict[str, str],
                awr_id: int,
                source_system_id: int,
            ) -> dict[str, str]:
                del parse_result, awr_id, source_system_id
                return {"feature_json": json.dumps({"DB_CPU_PCT_DB_TIME": 65.0})}

            def decision_builder(**kwargs: object) -> AwrDecision:
                self.assertTrue(kwargs.get("include_diagnostics"))
                return AwrDecision(
                    awr_id=1,
                    overall_status="WARNING",
                    primary_issue="CPU",
                    secondary_issues=[],
                    severity_score=35.0,
                    confidence=0.71,
                    evidence={
                        "domain_scores": {"CPU": 0.45},
                        "decision_diagnostics": {
                            "domain_diagnostics": {
                                "CPU": {
                                    "score": 0.45,
                                    "qualified_for_primary": True,
                                },
                                "IO": {
                                    "score": 0.0,
                                    "qualified_for_primary": False,
                                },
                                "MEMORY": {
                                    "score": 0.0,
                                    "qualified_for_primary": False,
                                },
                                "COMMIT": {
                                    "score": 0.0,
                                    "qualified_for_primary": False,
                                },
                                "RAC": {
                                    "score": 0.0,
                                    "qualified_for_primary": False,
                                },
                                "ADG": {
                                    "score": 0.0,
                                    "qualified_for_primary": False,
                                },
                            },
                            "ordered_candidates_pre_tiebreak": [
                                {"score": 0.45, "domains": ["CPU"]}
                            ],
                            "final_ranked_domains": [
                                "CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG"
                            ],
                        },
                    },
                )

            result = run_validation_harness(
                input_dir=root,
                parser=parser,
                feature_vector_builder=feature_vector_builder,
                decision_builder=decision_builder,
                recommendation_builder=lambda decision: [],
                output_builder=lambda **kwargs: dict(kwargs),
            )

        diagnostics = result.cases[0].validation_diagnostics
        self.assertIsInstance(diagnostics, dict)
        self.assertIn("decision_diagnostics", diagnostics)
        self.assertEqual(
            diagnostics["decision_diagnostics"]["final_ranked_domains"][0],
            "CPU",
        )
        self.assertEqual(
            result.cases[0].output.get("validation_diagnostics"),
            diagnostics,
        )

    def test_json_summary_emits_case_level_validation_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            json_output = root / "summary.json"
            original_runner = harness_module.run_validation_harness
            harness_module.run_validation_harness = lambda **kwargs: harness_module.ValidationHarnessResult(
                manifest_source="manifest.csv",
                case_count=1,
                passed_count=1,
                failed_count=0,
                cases=[
                    harness_module.ValidationCaseResult(
                        scenario_name="CASE_A",
                        file="case_a.out",
                        expected_primary_issue="CPU",
                        actual_primary_issue="CPU",
                        expected_secondary_issues=[],
                        actual_secondary_issues=[],
                        expected_status="WARNING",
                        actual_status="WARNING",
                        passed=True,
                        validation_diagnostics={
                            "decision_diagnostics": {
                                "domain_diagnostics": {
                                    "CPU": {
                                        "score": 0.45,
                                        "qualified_for_primary": True,
                                    },
                                    "IO": {
                                        "score": 0.0,
                                        "qualified_for_primary": False,
                                    },
                                    "MEMORY": {
                                        "score": 0.0,
                                        "qualified_for_primary": False,
                                    },
                                    "COMMIT": {
                                        "score": 0.0,
                                        "qualified_for_primary": False,
                                    },
                                    "RAC": {
                                        "score": 0.0,
                                        "qualified_for_primary": False,
                                    },
                                    "ADG": {
                                        "score": 0.0,
                                        "qualified_for_primary": False,
                                    },
                                },
                                "ordered_candidates_pre_tiebreak": [
                                    {"score": 0.45, "domains": ["CPU"]}
                                ],
                                "final_ranked_domains": [
                                    "CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG"
                                ],
                            },
                            "normalized_to_none": False,
                            "normalized_primary_issue": "CPU",
                            "normalized_secondary_issues": [],
                        },
                        output={
                            "awr_id": 1,
                            "validation_diagnostics": {
                                "decision_diagnostics": {
                                    "domain_diagnostics": {
                                        "CPU": {
                                            "score": 0.45,
                                            "qualified_for_primary": True,
                                        },
                                        "IO": {
                                            "score": 0.0,
                                            "qualified_for_primary": False,
                                        },
                                        "MEMORY": {
                                            "score": 0.0,
                                            "qualified_for_primary": False,
                                        },
                                        "COMMIT": {
                                            "score": 0.0,
                                            "qualified_for_primary": False,
                                        },
                                        "RAC": {
                                            "score": 0.0,
                                            "qualified_for_primary": False,
                                        },
                                        "ADG": {
                                            "score": 0.0,
                                            "qualified_for_primary": False,
                                        },
                                    },
                                    "ordered_candidates_pre_tiebreak": [
                                        {"score": 0.45, "domains": ["CPU"]}
                                    ],
                                    "final_ranked_domains": [
                                        "CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG"
                                    ],
                                },
                                "normalized_to_none": False,
                                "normalized_primary_issue": "CPU",
                                "normalized_secondary_issues": [],
                            },
                        },
                    )
                ],
            )
            try:
                exit_code = main([str(root), "--json-output", str(json_output)])
            finally:
                harness_module.run_validation_harness = original_runner

            self.assertEqual(exit_code, 0)
            payload = json.loads(json_output.read_text(encoding="utf-8"))
            case_payload = payload["cases"][0]
            self.assertIn("validation_diagnostics", case_payload)
            diagnostics = case_payload["validation_diagnostics"]
            self.assertEqual(diagnostics["normalized_primary_issue"], "CPU")
            self.assertIn("decision_diagnostics", diagnostics)
            self.assertIn("domain_diagnostics", diagnostics["decision_diagnostics"])
            self.assertEqual(
                set(diagnostics["decision_diagnostics"]["domain_diagnostics"].keys()),
                {"CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG"},
            )
            self.assertIn(
                "ordered_candidates_pre_tiebreak",
                diagnostics["decision_diagnostics"],
            )
            self.assertIn(
                "final_ranked_domains",
                diagnostics["decision_diagnostics"],
            )

    def test_cli_returns_zero_for_case_mismatches_and_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            json_output = root / "summary.json"
            original_runner = harness_module.run_validation_harness
            harness_module.run_validation_harness = lambda **kwargs: harness_module.ValidationHarnessResult(
                manifest_source="manifest.csv",
                case_count=1,
                passed_count=0,
                failed_count=1,
                cases=[],
            )
            try:
                exit_code = main([str(root), "--json-output", str(json_output)])
            finally:
                harness_module.run_validation_harness = original_runner

            self.assertEqual(exit_code, 0)
            payload = json.loads(json_output.read_text(encoding="utf-8"))
            self.assertEqual(payload["case_count"], 1)
            self.assertEqual(payload["failed_count"], 1)
            self.assertIn("passed_count", payload)


if __name__ == "__main__":
    unittest.main()
