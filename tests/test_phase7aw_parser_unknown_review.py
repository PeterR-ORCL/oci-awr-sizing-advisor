from __future__ import annotations

import ast
import importlib
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
WORKFLOW_DOC = DOCS / "phase7aw_parser_unknown_review_workflow.md"
MODEL_DOC = DOCS / "phase7aw_parser_unknown_review_model.md"
MODULE_PATH = ROOT / "src" / "learning" / "screen1_parser_unknown_review.py"

RUNTIME_IMPORT_PATHS = (
    "scripts/run_analysis.py",
    "src/parser",
    "src/parsing",
    "src/scoring",
    "src/decision",
    "src/recommendation",
    "src/recommendations",
    "src/analysis/decision_engine.py",
    "src/analysis/recommendation_engine.py",
    "src/analysis/scoring_adapter.py",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "subprocess",
    "oracledb",
    "cx_Oracle",
    "sqlite3",
    "oci",
    "requests",
    "socket",
    "urllib",
    "http.client",
    "httpx",
    "boto3",
    "botocore",
    "src.reporting",
    "src.parser",
    "src.parsing",
    "src.scoring",
    "src.decision",
    "src.recommendation",
    "src.recommendations",
    "src.analysis",
    "src.memory",
    "scripts.awr_memory_cli",
    "scripts.run_analysis",
    "oracle_agent_memory",
)

FORBIDDEN_FUNCTION_NAMES = (
    "persist_unknown_review",
    "classify_unknown_signal",
    "create_parser_mapping",
    "create_parser_candidate",
    "create_backlog_item",
    "update_parser_output",
    "mutate_phase4i",
    "write_database",
    "run_analysis",
    "auto_apply",
    "autonomous_apply",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def lower_text(path: Path) -> str:
    return read_text(path).lower()


def python_files(paths: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for relative_path in paths:
        path = ROOT / relative_path
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(child for child in path.rglob("*.py") if child.is_file()))
    return files


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def function_names(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


class Phase7AWParserUnknownReviewTests(unittest.TestCase):
    @staticmethod
    def module():
        return importlib.import_module("src.learning.screen1_parser_unknown_review")

    def make_request(self, decision: str = "parser_gap", **overrides):
        module = self.module()
        values = {
            "request_id": module.create_unknown_review_request_id(
                "UNKNOWN-1",
                decision,
            ),
            "unknown_signal_id": "UNKNOWN-1",
            "requested_decision": decision,
            "actor_id": "ACTOR-LOCAL-REVIEWER",
            "payload": {
                "parser_section": "Load Profile",
                "signal_name": "mystery metric",
                "raw_text": "Mystery Metric 42",
                "review_notes": ["metadata only"],
            },
            "can_route_to_write_path": True,
            "notes": "unit test",
        }
        values.update(overrides)
        return module.ParserUnknownReviewRequest(**values)

    def make_review(self, **overrides):
        module = self.module()
        values = {
            "review_id": module.create_unknown_review_id("UNKNOWN-1", "parser_gap"),
            "unknown_signal_id": "UNKNOWN-1",
            "source_run_id": "RUN-1",
            "source_awr_id": "AWR-1",
            "parser_section": "Load Profile",
            "signal_name": "mystery metric",
            "raw_text": "Mystery Metric 42",
            "review_decision": "parser_gap",
            "review_status": "routed_to_mapping",
            "reviewer_actor_id": "ACTOR-LOCAL-REVIEWER",
            "review_notes": ["metadata only"],
        }
        values.update(overrides)
        return module.ParserUnknownReviewRecord(**values)

    def test_module_import_safety(self) -> None:
        before_environment = dict(os.environ)
        module = self.module()
        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(module, "ParserUnknownReviewRecord"))
        self.assertTrue(hasattr(module, "ParserUnknownReviewRequest"))
        self.assertTrue(hasattr(module, "ParserMappingIntent"))
        self.assertTrue(hasattr(module, "ParserBacklogIntent"))

        imports = imported_modules(MODULE_PATH)
        for forbidden in FORBIDDEN_IMPORT_PREFIXES:
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        imported == forbidden or imported.startswith(f"{forbidden}.")
                        for imported in imports
                    )
                )

    def test_docs_exist(self) -> None:
        self.assertTrue(WORKFLOW_DOC.is_file(), WORKFLOW_DOC)
        self.assertTrue(MODEL_DOC.is_file(), MODEL_DOC)

    def test_docs_contain_required_boundary_phrases(self) -> None:
        text = lower_text(WORKFLOW_DOC) + "\n" + lower_text(MODEL_DOC)
        for phrase in (
            "no parser unknown classification is persisted",
            "no parser mapping is created",
            "no parser candidate is created automatically",
            "no backlog item is created",
            "no parser output is changed",
            "no phase 4i mutation occurs",
            "parser mapping intent is not parser mapping",
            "backlog intent is not backlog item",
            "deterministic runtime remains authoritative",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_supported_values_and_unsupported_values_fail(self) -> None:
        module = self.module()
        self.assertEqual(
            module.PARSER_UNKNOWN_REVIEW_DECISIONS,
            (
                "parser_gap",
                "source_gap",
                "false_positive",
                "not_applicable",
                "needs_mapping",
                "needs_backlog",
                "needs_human_review",
                "add_review_note",
            ),
        )
        self.assertIn("routed_to_mapping", module.PARSER_UNKNOWN_REVIEW_STATUSES)
        self.assertIn(
            "parser_confidence_metadata_review",
            module.PARSER_MAPPING_INTENT_TYPES,
        )
        self.assertIn("request_regression_validation", module.PARSER_BACKLOG_ACTIONS)

        with self.assertRaises(module.Screen1ParserUnknownReviewError):
            self.make_request(decision="unsupported")
        with self.assertRaises(module.Screen1ParserUnknownReviewError):
            self.make_review(review_status="unsupported")
        with self.assertRaises(module.Screen1ParserUnknownReviewError):
            module.ParserMappingIntent(
                intent_id="INTENT-1",
                unknown_signal_id="UNKNOWN-1",
                mapping_intent_type="unsupported",
            )
        with self.assertRaises(module.Screen1ParserUnknownReviewError):
            module.ParserBacklogIntent(
                backlog_intent_id="BACKLOG-1",
                unknown_signal_id="UNKNOWN-1",
                backlog_action="unsupported",
            )

    def test_review_record_validation_rejects_runtime_flags(self) -> None:
        module = self.module()
        review = self.make_review()
        self.assertIs(module.validate_parser_unknown_review_record(review), review)

        for field_name in (
            "write_performed",
            "runtime_influence",
            "parser_output_mutation_requested",
            "phase4i_mutation_requested",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaises(module.Screen1ParserUnknownReviewError):
                    self.make_review(**{field_name: True})

    def test_review_request_validation(self) -> None:
        module = self.module()
        request = self.make_request()
        self.assertIs(module.validate_parser_unknown_review_request(request), request)

        with self.assertRaises(module.Screen1ParserUnknownReviewError):
            module.validate_parser_unknown_review_request(
                self.make_request(actor_id=None, actor_audit_context=None)
            )
        with self.assertRaises(module.Screen1ParserUnknownReviewError):
            self.make_request(decision="unsupported")

        for field_name in (
            "write_performed",
            "runtime_influence",
            "parser_output_mutation_requested",
            "phase4i_mutation_requested",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaises(module.Screen1ParserUnknownReviewError):
                    self.make_request(**{field_name: True})

    def test_mapping_intent_for_parser_gap_and_needs_mapping(self) -> None:
        module = self.module()
        for decision in ("parser_gap", "needs_mapping"):
            with self.subTest(decision=decision):
                intent = module.build_mapping_intent_for_request(
                    self.make_request(decision)
                )
                self.assertIsNotNone(intent)
                self.assertEqual(intent.candidate_type, "parser_mapping_candidate")
                self.assertFalse(intent.candidate_created)
                self.assertFalse(intent.parser_mapping_created)
                self.assertFalse(intent.runtime_influence)
                self.assertFalse(intent.parser_output_mutation_requested)
                self.assertFalse(intent.phase4i_mutation_requested)

    def test_backlog_intent_for_needs_backlog(self) -> None:
        module = self.module()
        intent = module.build_backlog_intent_for_request(
            self.make_request("needs_backlog")
        )
        self.assertIsNotNone(intent)
        self.assertEqual(intent.backlog_action, "create_backlog_item")
        self.assertFalse(intent.backlog_item_created)
        self.assertFalse(intent.runtime_influence)
        self.assertFalse(intent.parser_output_mutation_requested)
        self.assertFalse(intent.phase4i_mutation_requested)

    def test_decision_routing(self) -> None:
        module = self.module()
        parser_gap = module.route_parser_unknown_review(self.make_request("parser_gap"))
        self.assertIsNotNone(parser_gap["mapping_intent"])
        self.assertEqual(parser_gap["review_record"]["review_status"], "routed_to_mapping")

        source_gap = module.route_parser_unknown_review(self.make_request("source_gap"))
        self.assertIsNone(source_gap["mapping_intent"])
        self.assertIn("source review", source_gap["recommended_next_step"])

        false_positive = module.route_parser_unknown_review(
            self.make_request("false_positive")
        )
        self.assertEqual(
            false_positive["review_record"]["review_status"],
            "false_positive",
        )

        not_applicable = module.route_parser_unknown_review(
            self.make_request("not_applicable")
        )
        self.assertEqual(
            not_applicable["review_record"]["review_status"],
            "not_applicable",
        )

        human_review = module.route_parser_unknown_review(
            self.make_request("needs_human_review")
        )
        self.assertEqual(
            human_review["review_record"]["review_status"],
            "under_review",
        )

    def test_serialization_round_trip(self) -> None:
        module = self.module()
        request = self.make_request()
        validation = module.evaluate_parser_unknown_review_request(request)
        review = self.make_review()
        mapping_intent = module.build_mapping_intent_for_request(request)
        backlog_intent = module.build_backlog_intent_for_request(
            self.make_request("needs_backlog")
        )
        self.assertIsNotNone(mapping_intent)
        self.assertIsNotNone(backlog_intent)

        review_dict = module.parser_unknown_review_record_to_dict(review)
        request_dict = module.parser_unknown_review_request_to_dict(request)
        validation_dict = module.parser_unknown_review_validation_to_dict(validation)
        mapping_dict = module.mapping_intent_to_dict(mapping_intent)
        backlog_dict = module.backlog_intent_to_dict(backlog_intent)

        self.assertEqual(
            review_dict,
            module.parser_unknown_review_record_to_dict(
                module.parser_unknown_review_record_from_dict(review_dict)
            ),
        )
        self.assertEqual(
            request_dict,
            module.parser_unknown_review_request_to_dict(
                module.parser_unknown_review_request_from_dict(request_dict)
            ),
        )
        self.assertEqual(
            validation_dict,
            module.parser_unknown_review_validation_to_dict(
                module.parser_unknown_review_validation_from_dict(validation_dict)
            ),
        )
        self.assertEqual(
            mapping_dict,
            module.mapping_intent_to_dict(module.mapping_intent_from_dict(mapping_dict)),
        )
        self.assertEqual(
            backlog_dict,
            module.backlog_intent_to_dict(module.backlog_intent_from_dict(backlog_dict)),
        )

    def test_deterministic_ids(self) -> None:
        module = self.module()
        first = module.create_unknown_review_id("UNKNOWN-1", "parser_gap")
        second = module.create_unknown_review_id("UNKNOWN-1", "parser_gap")
        self.assertEqual(first, second)
        self.assertEqual(
            module.create_unknown_review_request_id("UNKNOWN-1", "parser_gap"),
            module.create_unknown_review_request_id("UNKNOWN-1", "parser_gap"),
        )
        self.assertEqual(
            module.make_mapping_intent_id("UNKNOWN-1", "unknown_signal_mapping"),
            module.make_mapping_intent_id("UNKNOWN-1", "unknown_signal_mapping"),
        )
        self.assertEqual(
            module.make_backlog_intent_id("UNKNOWN-1", "create_backlog_item"),
            module.make_backlog_intent_id("UNKNOWN-1", "create_backlog_item"),
        )
        self.assertNotIn("UUID", first.upper())

    def test_no_mutation_or_persistence_functions(self) -> None:
        names = function_names(MODULE_PATH)
        for forbidden in FORBIDDEN_FUNCTION_NAMES:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, names)

    def test_runtime_import_isolation(self) -> None:
        run_analysis_imports = imported_modules(ROOT / "scripts" / "run_analysis.py")
        for module_name in (
            "src.learning.screen1_parser_unknown_review",
            "learning.screen1_parser_unknown_review",
            "screen1_parser_unknown_review",
        ):
            with self.subTest(module_name=module_name):
                self.assertNotIn(module_name, run_analysis_imports)

        for path in python_files(RUNTIME_IMPORT_PATHS):
            imports = imported_modules(path)
            source = read_text(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.screen1_parser_unknown_review", imports)
                self.assertNotIn("learning.screen1_parser_unknown_review", imports)
                self.assertNotIn("screen1_parser_unknown_review", imports)
                self.assertNotIn("screen1_parser_unknown_review", source)


if __name__ == "__main__":
    unittest.main()
