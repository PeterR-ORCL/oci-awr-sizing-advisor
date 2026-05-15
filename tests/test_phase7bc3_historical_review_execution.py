from __future__ import annotations

import ast
import importlib
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
ARCHITECTURE_DOC = DOCS / "phase7bc3_historical_review_execution.md"
MODEL_DOC = DOCS / "phase7bc3_historical_review_execution_model.md"
README = DOCS / "README.md"
MODULE_PATH = ROOT / "src" / "learning" / "screen4_historical_review_execution.py"

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
    "src.trend",
    "src.anomaly",
    "src.decision",
    "src.recommendation",
    "src.recommendations",
    "src.analysis",
    "src.memory",
    "scripts.awr_memory_cli",
    "scripts.run_analysis",
    "oracle_agent_memory",
)

FORBIDDEN_SOURCE_TERMS = (
    "persist_to_db",
    "persist_record",
    "write_database",
    "call_backend",
    "run_analysis",
    "mutate_runtime",
    "mutate_phase4i",
    "create_actual_candidate",
    "create_actual_dataset_label",
    "auto_apply",
    "autonomous_apply",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def lower_text(path: Path) -> str:
    return read_text(path).lower()


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


def python_files(paths: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for relative_path in paths:
        path = ROOT / relative_path
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(
                sorted(child for child in path.rglob("*.py") if child.is_file())
            )
    return files


class Phase7BC3HistoricalReviewExecutionTests(unittest.TestCase):
    @staticmethod
    def module():
        return importlib.import_module("src.learning.screen4_historical_review_execution")

    @staticmethod
    def actor_module():
        return importlib.import_module("src.learning.dashboard_actor_identity")

    @staticmethod
    def write_module():
        return importlib.import_module("src.learning.dashboard_governed_write_path")

    def make_actor_audit_context(self) -> dict[str, object]:
        actor = self.actor_module()
        actor_identity = actor.DashboardActorIdentity(
            actor_id=actor.create_actor_id("Jane Reviewer", "local"),
            display_name="Jane Reviewer",
            role="reviewer",
            actor_source="local",
            permission_scope="review",
            authenticated=False,
        )
        context = actor.create_actor_audit_context(
            actor_identity,
            action_scope="screen4_historical_review",
            notes="unit-test actor metadata",
        )
        return actor.actor_audit_context_to_dict(context)

    def make_governed_write_request(self, **overrides) -> dict[str, object]:
        write = self.write_module()
        values: dict[str, object] = {
            "request_id": write.create_governed_write_request_id(
                "trend_anomaly_review",
                "TREND-CPU",
                "review",
            ),
            "target_type": "trend_anomaly_review",
            "target_id": "TREND-CPU",
            "write_intent": "review",
            "actor_id": "ACTOR-LOCAL-JANE-REVIEWER",
            "actor_audit_context": self.make_actor_audit_context(),
            "backend_execution_request": None,
            "payload": {"review_action": "approve_trend"},
            "dry_run": True,
            "requires_actor": True,
            "requires_audit": True,
            "requires_backend_validation": True,
            "runtime_mutation_requested": False,
            "phase4i_mutation_requested": False,
            "created_at": None,
            "notes": "metadata-only governed write request",
        }
        values.update(overrides)
        request = write.GovernedWriteRequest(**values)
        return write.governed_write_request_to_dict(request)

    def make_request(self, **overrides):
        module = self.module()
        action = overrides.get("review_action", "approve_trend")
        target_type = overrides.get("review_target_type", "trend_metric")
        target_id = overrides.get("review_target_id", "TREND-CPU")
        values = {
            "execution_request_id": module.create_historical_review_execution_request_id(
                action,
                target_type,
                target_id,
            ),
            "review_action": action,
            "review_target_type": target_type,
            "review_target_id": target_id,
            "actor_id": "ACTOR-LOCAL-JANE-REVIEWER",
            "actor_audit_context": self.make_actor_audit_context(),
            "governed_write_request": self.make_governed_write_request(),
            "trend_review_payload": {
                "run_id": "RUN-1",
                "awr_id": "AWR-1",
                "trend_id": "TREND-CPU",
                "trend_name": "CPU trend",
                "domain": "CPU",
                "trend_direction": "increasing",
                "trend_strength": 0.82,
                "baseline_candidate_id": "HIST-BASELINE-CANDIDATE-RUN-BASE",
                "comparison_context_id": "HIST-COMPARISON-CONTEXT-BASE-TARGET",
                "review_notes": "metadata execution only",
            },
            "anomaly_review_payload": {},
            "baseline_payload": {},
            "bridge_payload": {},
            "dry_run": True,
            "requires_actor": True,
            "requires_audit": True,
            "requires_governed_write_path": True,
            "write_performed": False,
            "runtime_influence": False,
            "phase4i_mutation_requested": False,
            "created_at": None,
            "notes": "unit-test request",
        }
        values.update(overrides)
        return module.HistoricalReviewExecutionRequest(**values)

    def make_validation(self, **overrides):
        module = self.module()
        request = self.make_request()
        values = {
            "execution_validation_id": (
                module.create_historical_review_execution_validation_id(
                    request.execution_request_id
                )
            ),
            "execution_request_id": request.execution_request_id,
            "valid": True,
            "validation_status": "execution_metadata_only",
            "actor_present": True,
            "governed_write_valid": True,
            "review_target_present": True,
            "can_execute_governed_action": True,
            "write_performed": False,
            "denied_reasons": [],
            "warnings": ["metadata-only"],
            "required_next_steps": ["record audit envelope"],
            "runtime_influence": False,
            "phase4i_mutation_requested": False,
            "notes": "validation only",
        }
        values.update(overrides)
        return module.HistoricalReviewExecutionValidation(**values)

    def make_audit_envelope(self, **overrides):
        module = self.module()
        request = self.make_request()
        values = {
            "audit_envelope_id": module.create_historical_review_audit_envelope_id(
                request.execution_request_id,
                request.review_action,
            ),
            "execution_request_id": request.execution_request_id,
            "actor_id": request.actor_id,
            "action": request.review_action,
            "target_type": request.review_target_type,
            "target_id": request.review_target_id,
            "governed_write_validation_id": "GOVERNED-WRITE-VALIDATION-1",
            "output_artifact_id": "DASHBOARD-OUTPUT-VALIDATION-1",
            "audit_summary": "metadata-only audit envelope",
            "write_performed": False,
            "runtime_influence": False,
            "phase4i_mutation_requested": False,
            "notes": "audit only",
        }
        values.update(overrides)
        return module.HistoricalReviewAuditEnvelope(**values)

    def make_result(self, **overrides):
        module = self.module()
        request = self.make_request()
        validation = module.evaluate_historical_review_execution_request(request)
        result = module.execute_historical_review_metadata_action(request, validation)
        data = module.historical_review_execution_result_to_dict(result)
        data.update(overrides)
        return module.HistoricalReviewExecutionResult(**data)

    def test_import_safety(self) -> None:
        module = self.module()
        self.assertTrue(hasattr(module, "HistoricalReviewExecutionRequest"))
        self.assertTrue(hasattr(module, "execute_historical_review_metadata_action"))

        imports = imported_modules(MODULE_PATH)
        for forbidden in FORBIDDEN_IMPORT_PREFIXES:
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        imported == forbidden
                        or imported.startswith(f"{forbidden}.")
                        for imported in imports
                    ),
                    f"forbidden import {forbidden} found in {imports}",
                )

    def test_docs_exist_and_contain_boundary_phrases(self) -> None:
        self.assertTrue(ARCHITECTURE_DOC.is_file(), ARCHITECTURE_DOC)
        self.assertTrue(MODEL_DOC.is_file(), MODEL_DOC)

        combined = f"{lower_text(ARCHITECTURE_DOC)}\n{lower_text(MODEL_DOC)}"
        for phrase in (
            "governed execution is metadata-only",
            "no runtime truth changes",
            "no candidate creation",
            "no dataset label creation",
            "no trend/anomaly/scoring mutation",
            "no phase 4i mutation",
            "deterministic runtime remains authoritative",
            "phase 8 sizing/tco is not implemented",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

    def test_request_validation(self) -> None:
        module = self.module()
        request = self.make_request()
        self.assertIs(module.validate_historical_review_execution_request(request), request)

        for field, value in (
            ("dry_run", False),
            ("requires_audit", False),
            ("write_performed", True),
            ("runtime_influence", True),
            ("phase4i_mutation_requested", True),
        ):
            with self.subTest(field=field):
                with self.assertRaises(module.Screen4HistoricalReviewExecutionError):
                    self.make_request(**{field: value})

    def test_validation_result_validation(self) -> None:
        module = self.module()
        validation = self.make_validation()
        self.assertIs(
            module.validate_historical_review_execution_validation(validation),
            validation,
        )

        for field, value in (
            ("write_performed", True),
            ("runtime_influence", True),
            ("phase4i_mutation_requested", True),
            ("validation_status", "unsupported"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(module.Screen4HistoricalReviewExecutionError):
                    self.make_validation(**{field: value})

        with self.assertRaises(module.Screen4HistoricalReviewExecutionError):
            self.make_validation(valid=False, can_execute_governed_action=True)

    def test_metadata_execution_result_validation(self) -> None:
        module = self.module()
        result = self.make_result()
        self.assertIs(module.validate_historical_review_execution_result(result), result)
        self.assertEqual(result.execution_status, "recorded_metadata_only")
        self.assertTrue(result.governed_action_recorded)
        self.assertIsNotNone(result.trend_review_record)
        self.assertIsNotNone(result.audit_record)
        self.assertIsNotNone(result.output_artifact)
        self.assertFalse(result.candidate_created)
        self.assertFalse(result.dataset_label_created)
        self.assertFalse(result.trend_truth_changed)
        self.assertFalse(result.anomaly_truth_changed)
        self.assertFalse(result.scoring_changed)
        self.assertFalse(result.phase4i_mutated)
        self.assertFalse(result.runtime_influence)

        for field in (
            "candidate_created",
            "dataset_label_created",
            "historical_truth_changed",
            "trend_truth_changed",
            "anomaly_truth_changed",
            "scoring_changed",
            "phase4i_mutated",
            "runtime_influence",
        ):
            with self.subTest(field=field):
                with self.assertRaises(module.Screen4HistoricalReviewExecutionError):
                    self.make_result(**{field: True})

    def test_audit_envelope_validation(self) -> None:
        module = self.module()
        envelope = self.make_audit_envelope()
        self.assertIs(module.validate_historical_review_audit_envelope(envelope), envelope)
        for field, value in (
            ("runtime_influence", True),
            ("phase4i_mutation_requested", True),
            ("action", "unsupported"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(module.Screen4HistoricalReviewExecutionError):
                    self.make_audit_envelope(**{field: value})

    def test_missing_actor_fails(self) -> None:
        module = self.module()
        request = self.make_request(actor_id=None, actor_audit_context=None)
        validation = module.evaluate_historical_review_execution_request(request)

        self.assertFalse(validation.valid)
        self.assertEqual(validation.validation_status, "needs_actor")
        self.assertFalse(validation.actor_present)
        self.assertFalse(validation.write_performed)

    def test_missing_governed_write_path_fails(self) -> None:
        module = self.module()
        request = self.make_request(governed_write_request=None)
        validation = module.evaluate_historical_review_execution_request(request)

        self.assertFalse(validation.valid)
        self.assertEqual(validation.validation_status, "needs_governed_write_path")
        self.assertFalse(validation.governed_write_valid)
        self.assertFalse(validation.write_performed)

    def test_unsupported_action_fails(self) -> None:
        module = self.module()
        with self.assertRaises(module.Screen4HistoricalReviewExecutionError):
            self.make_request(
                execution_request_id="SCREEN4-HIST-EXEC-REQUEST-UNSUPPORTED",
                review_action="unsupported_action",
            )

    def test_metadata_execution_can_create_anomaly_review_intents_only(self) -> None:
        module = self.module()
        request = self.make_request(
            execution_request_id=module.create_historical_review_execution_request_id(
                "mark_anomaly_false_positive",
                "anomaly_event",
                "ANOM-CPU",
            ),
            review_action="mark_anomaly_false_positive",
            review_target_type="anomaly_event",
            review_target_id="ANOM-CPU",
            trend_review_payload={},
            anomaly_review_payload={
                "run_id": "RUN-1",
                "awr_id": "AWR-1",
                "anomaly_id": "ANOM-CPU",
                "anomaly_name": "CPU anomaly",
                "domain": "CPU",
                "anomaly_pattern": "spike",
                "anomaly_severity": 0.7,
                "baseline_candidate_id": "HIST-BASELINE-CANDIDATE-RUN-BASE",
                "comparison_context_id": "HIST-COMPARISON-CONTEXT-BASE-TARGET",
                "review_notes": "false positive claim",
            },
        )
        validation = module.evaluate_historical_review_execution_request(request)
        result = module.execute_historical_review_metadata_action(request, validation)

        self.assertTrue(validation.valid)
        self.assertIsNone(result.trend_review_record)
        self.assertIsNotNone(result.anomaly_review_record)
        self.assertGreaterEqual(len(result.candidate_intents), 1)
        self.assertGreaterEqual(len(result.learning_signal_intents), 1)
        self.assertGreaterEqual(len(result.governance_routes), 1)
        self.assertFalse(result.candidate_created)
        self.assertFalse(result.dataset_label_created)
        self.assertFalse(result.anomaly_truth_changed)

    def test_serialization_round_trips(self) -> None:
        module = self.module()
        request = self.make_request()
        validation = module.evaluate_historical_review_execution_request(request)
        result = module.execute_historical_review_metadata_action(request, validation)
        envelope = module.historical_review_audit_envelope_from_dict(
            result.audit_record
        )

        objects = (
            (
                request,
                module.historical_review_execution_request_to_dict,
                module.historical_review_execution_request_from_dict,
            ),
            (
                validation,
                module.historical_review_execution_validation_to_dict,
                module.historical_review_execution_validation_from_dict,
            ),
            (
                result,
                module.historical_review_execution_result_to_dict,
                module.historical_review_execution_result_from_dict,
            ),
            (
                envelope,
                module.historical_review_audit_envelope_to_dict,
                module.historical_review_audit_envelope_from_dict,
            ),
        )
        for obj, to_dict, from_dict in objects:
            with self.subTest(obj=type(obj).__name__):
                data = to_dict(obj)
                round_trip = from_dict(data)
                self.assertEqual(to_dict(round_trip), data)

    def test_deterministic_ids(self) -> None:
        module = self.module()
        calls = (
            lambda: module.create_historical_review_execution_request_id(
                "approve_trend",
                "trend_metric",
                "TREND-CPU",
            ),
            lambda: module.create_historical_review_execution_validation_id(
                "SCREEN4-HIST-EXEC-REQUEST-1"
            ),
            lambda: module.create_historical_review_execution_result_id(
                "SCREEN4-HIST-EXEC-REQUEST-1",
                "approve_trend",
            ),
            lambda: module.create_historical_review_audit_envelope_id(
                "SCREEN4-HIST-EXEC-REQUEST-1",
                "approve_trend",
            ),
        )
        for call in calls:
            first = call()
            second = call()
            with self.subTest(identifier=first):
                self.assertEqual(first, second)
                self.assertNotRegex(first.lower(), r"[0-9a-f]{8}-[0-9a-f]{4}-")
                self.assertNotRegex(first, r"20\d{2}[-:]?\d{2}[-:]?\d{2}")

    def test_no_forbidden_runtime_or_persistence_functions(self) -> None:
        names = function_names(MODULE_PATH)
        source = lower_text(MODULE_PATH)
        for term in FORBIDDEN_SOURCE_TERMS:
            with self.subTest(term=term):
                self.assertNotIn(term, names)
                self.assertNotIn(term, source)
        self.assertIn("execute_historical_review_metadata_action", names)

    def test_runtime_import_isolation(self) -> None:
        run_analysis_imports = imported_modules(ROOT / "scripts" / "run_analysis.py")
        for module_name in (
            "src.learning.screen4_historical_review_execution",
            "learning.screen4_historical_review_execution",
            "screen4_historical_review_execution",
        ):
            with self.subTest(module_name=module_name):
                self.assertNotIn(module_name, run_analysis_imports)

        for path in python_files(RUNTIME_IMPORT_PATHS):
            imports = imported_modules(path)
            source = read_text(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.screen4_historical_review_execution", imports)
                self.assertNotIn("learning.screen4_historical_review_execution", imports)
                self.assertNotIn("screen4_historical_review_execution", imports)
                self.assertNotIn("screen4_historical_review_execution", source)

    def test_readme_links_new_docs(self) -> None:
        text = read_text(README)
        for title, filename in (
            (
                "Phase 7BC.3 Historical Review Execution",
                "phase7bc3_historical_review_execution.md",
            ),
            (
                "Phase 7BC.3 Historical Review Execution Model",
                "phase7bc3_historical_review_execution_model.md",
            ),
        ):
            with self.subTest(title=title):
                self.assertIn(title, text)
                self.assertIn(filename, text)


if __name__ == "__main__":
    unittest.main()
