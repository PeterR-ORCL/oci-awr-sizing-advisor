"""Phase 7BU tests for governed workflow persistence metadata."""

from __future__ import annotations

import ast
import importlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "learning" / "governed_workflow_persistence.py"
DOCS = ROOT / "docs" / "architecture"
BOUNDARY_DOC = DOCS / "phase7bu_runtime_materialization_execution_boundary.md"
PERSISTENCE_DOC = DOCS / "phase7bu_governed_workflow_persistence.md"
TRANSITION_DOC = DOCS / "phase7bu_status_transition_execution_model.md"

FORBIDDEN_IMPORT_PREFIXES = (
    "subprocess",
    "requests",
    "httpx",
    "urllib",
    "socket",
    "http.client",
    "oci",
    "oracledb",
    "cx_Oracle",
    "sqlite3",
    "src.reporting",
    "src.parser",
    "src.parsing",
    "src.scoring",
    "src.decision",
    "src.recommendation",
    "src.recommendations",
    "scripts.run_analysis",
    "scripts.awr_memory_cli",
)

FORBIDDEN_FUNCTION_NAMES = (
    "persist_governed_workflow_record",
    "persist_audit_record",
    "write_database",
    "write_file",
    "connect_database",
    "perform_db_write",
    "change_runtime_state",
    "mutate_phase4i",
    "run_analysis",
    "activate_runtime",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


class Phase7BUGovernedWorkflowPersistenceTests(unittest.TestCase):
    @staticmethod
    def module():
        return importlib.import_module("src.learning.governed_workflow_persistence")

    def make_request(self, **overrides):
        module = self.module()
        workflow_record_type = overrides.get(
            "workflow_record_type",
            "learning_candidate_review",
        )
        workflow_record_id = overrides.get("workflow_record_id", "LC-REVIEW-001")
        if workflow_record_type in module.WORKFLOW_RECORD_TYPES:
            request_id = module.create_persistence_request_id(
                workflow_record_type,
                workflow_record_id,
            )
        else:
            request_id = "GOVERNED-WORKFLOW-PERSISTENCE-REQUEST-LOCAL-TEST"
        idempotency_key = overrides.get("idempotency_key", "IDEMP-7BU-001")
        values = {
            "persistence_request_id": request_id,
            "workflow_record_type": workflow_record_type,
            "workflow_record_id": workflow_record_id,
            "source_screen": "Screen 6",
            "actor_id": "ACTOR-LOCAL-JANE-REVIEWER",
            "actor_audit_context": {"actor_id": "ACTOR-LOCAL-JANE-REVIEWER"},
            "payload": {"decision": "approve_for_implementation"},
            "idempotency_key": idempotency_key,
            "transaction_group_id": module.create_transaction_group_id(
                idempotency_key or "MISSING-IDEMPOTENCY"
            ),
            "rollback_reference": "ROLLBACK-7BU-001",
            "dry_run": True,
            "persistence_requested": True,
            "persistence_performed": False,
            "db_write_performed": False,
            "runtime_mutation_requested": False,
            "phase4i_mutation_requested": False,
            "created_at": "2026-05-16T00:00:00Z",
            "notes": "metadata only",
        }
        values.update(overrides)
        return module.GovernedWorkflowPersistenceRequest(**values)

    def test_module_import_safety(self) -> None:
        module = self.module()
        self.assertTrue(hasattr(module, "GovernedWorkflowPersistenceRequest"))
        self.assertTrue(hasattr(module, "GovernedWorkflowAuditRecord"))

        imports = imported_modules(MODULE_PATH)
        for forbidden in FORBIDDEN_IMPORT_PREFIXES:
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        imported == forbidden or imported.startswith(f"{forbidden}.")
                        for imported in imports
                    )
                )

    def test_docs_exist_and_contain_boundary_phrases(self) -> None:
        for path in (BOUNDARY_DOC, PERSISTENCE_DOC, TRANSITION_DOC):
            self.assertTrue(path.is_file(), path)

        text = (
            read_text(BOUNDARY_DOC)
            + "\n"
            + read_text(PERSISTENCE_DOC)
            + "\n"
            + read_text(TRANSITION_DOC)
        ).lower()
        for phrase in (
            "no db persistence occurs in 7bu",
            "persistence_performed=false",
            "db_write_performed=false",
            "runtime_mutation_requested=false",
            "phase4i_mutation_requested=false",
            "idempotency key",
            "rollback reference",
            "metadata only",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_workflow_record_types_and_validation_statuses(self) -> None:
        module = self.module()
        self.assertEqual(
            set(module.WORKFLOW_RECORD_TYPES),
            {
                "diagnostic_review",
                "evidence_review",
                "screen3_reanalysis_request",
                "screen3_comparison_artifact",
                "recommendation_decision",
                "action_tracking",
                "outcome_capture",
                "feedback_intent",
                "parser_unknown_review",
                "parser_mapping_intent",
                "knowledge_artifact_review",
                "historical_review",
                "baseline_selection",
                "trend_anomaly_review",
                "learning_candidate_review",
                "materialization_review",
                "model_registry_review",
                "runtime_gate_review",
                "governance_audit",
                "output_artifact",
            },
        )
        self.assertIn("valid_metadata_only", module.PERSISTENCE_VALIDATION_STATUSES)
        self.assertIn("needs_idempotency_key", module.PERSISTENCE_VALIDATION_STATUSES)
        self.assertIn("needs_rollback_reference", module.PERSISTENCE_VALIDATION_STATUSES)

    def test_request_validation_and_evaluation(self) -> None:
        module = self.module()
        request = self.make_request()
        self.assertIs(module.validate_governed_workflow_persistence_request(request), request)

        validation = module.evaluate_governed_workflow_persistence_request(request)
        self.assertTrue(validation.valid)
        self.assertEqual("valid_metadata_only", validation.validation_status)
        self.assertTrue(validation.can_persist_later)
        self.assertFalse(validation.persistence_performed)
        self.assertFalse(validation.db_write_performed)
        self.assertFalse(validation.runtime_mutation_requested)
        self.assertFalse(validation.phase4i_mutation_requested)

        unsupported = self.make_request(workflow_record_type="dashboard_html")
        unsupported_validation = module.evaluate_governed_workflow_persistence_request(
            unsupported
        )
        self.assertFalse(unsupported_validation.valid)
        self.assertEqual(
            "unsupported_record_type",
            unsupported_validation.validation_status,
        )
        with self.assertRaises(module.GovernedWorkflowPersistenceError):
            module.validate_governed_workflow_persistence_request(unsupported)

    def test_validation_result_validation(self) -> None:
        module = self.module()
        validation = module.evaluate_governed_workflow_persistence_request(
            self.make_request()
        )
        self.assertIs(
            module.validate_governed_workflow_persistence_validation(validation),
            validation,
        )
        with self.assertRaises(module.GovernedWorkflowPersistenceError):
            module.GovernedWorkflowPersistenceValidation(
                persistence_validation_id=validation.persistence_validation_id,
                persistence_request_id=validation.persistence_request_id,
                valid=True,
                validation_status="valid_metadata_only",
                workflow_record_type="learning_candidate_review",
                actor_present=True,
                idempotency_key_present=True,
                rollback_reference_present=True,
                payload_present=True,
                can_persist_later=True,
                persistence_performed=True,
                db_write_performed=False,
            )

    def test_audit_record_validation(self) -> None:
        module = self.module()
        request = self.make_request()
        validation = module.evaluate_governed_workflow_persistence_request(request)
        record = module.create_governed_workflow_audit_record(
            request,
            validation,
            notes="audit metadata only",
        )
        self.assertIs(module.validate_governed_workflow_audit_record(record), record)
        self.assertFalse(record.persisted)
        self.assertFalse(record.db_write_performed)
        self.assertFalse(record.runtime_mutation_performed)
        self.assertFalse(record.phase4i_mutation_performed)
        self.assertEqual(64, len(record.payload_hash))

        values = module.governed_workflow_audit_record_to_dict(record)
        values["persisted"] = True
        with self.assertRaises(module.GovernedWorkflowPersistenceError):
            module.governed_workflow_audit_record_from_dict(values)

    def test_transaction_metadata_validation(self) -> None:
        module = self.module()
        metadata = module.create_transaction_metadata(
            "IDEMP-7BU-001",
            rollback_reference="ROLLBACK-7BU-001",
            requested_operations=["validate_metadata", "create_audit_metadata"],
        )
        self.assertIs(module.validate_transaction_metadata(metadata), metadata)
        self.assertFalse(metadata.committed)
        self.assertFalse(metadata.rolled_back)
        self.assertFalse(metadata.db_write_performed)

        missing_rollback = module.create_transaction_metadata("IDEMP-7BU-002")
        with self.assertRaises(module.GovernedWorkflowPersistenceError):
            module.validate_transaction_metadata(missing_rollback)

        values = module.governed_workflow_transaction_metadata_to_dict(metadata)
        values["committed"] = True
        with self.assertRaises(module.GovernedWorkflowPersistenceError):
            module.governed_workflow_transaction_metadata_from_dict(values)

    def test_idempotency_payload_and_rollback_required(self) -> None:
        module = self.module()
        missing_idempotency = self.make_request(idempotency_key=None)
        idempotency_validation = module.evaluate_governed_workflow_persistence_request(
            missing_idempotency
        )
        self.assertEqual(
            "needs_idempotency_key",
            idempotency_validation.validation_status,
        )
        with self.assertRaises(module.GovernedWorkflowPersistenceError):
            module.validate_governed_workflow_persistence_request(missing_idempotency)

        missing_rollback = self.make_request(rollback_reference=None)
        self.assertEqual(
            "needs_rollback_reference",
            module.evaluate_governed_workflow_persistence_request(
                missing_rollback
            ).validation_status,
        )

        missing_payload = self.make_request(payload={})
        self.assertEqual(
            "needs_payload",
            module.evaluate_governed_workflow_persistence_request(
                missing_payload
            ).validation_status,
        )

    def test_dry_run_and_no_mutation_flags_are_enforced(self) -> None:
        module = self.module()
        with self.assertRaises(module.GovernedWorkflowPersistenceError):
            self.make_request(dry_run=False)
        for field_name in (
            "persistence_performed",
            "db_write_performed",
            "runtime_mutation_requested",
            "phase4i_mutation_requested",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaises(module.GovernedWorkflowPersistenceError):
                    self.make_request(**{field_name: True})

    def test_serialization_round_trip(self) -> None:
        module = self.module()
        request = self.make_request()
        validation = module.evaluate_governed_workflow_persistence_request(request)
        audit = module.create_governed_workflow_audit_record(request, validation)
        transaction = module.create_transaction_metadata(
            request.idempotency_key,
            rollback_reference=request.rollback_reference,
        )

        self.assertEqual(
            request,
            module.governed_workflow_persistence_request_from_dict(
                module.governed_workflow_persistence_request_to_dict(request)
            ),
        )
        self.assertEqual(
            validation,
            module.governed_workflow_persistence_validation_from_dict(
                module.governed_workflow_persistence_validation_to_dict(validation)
            ),
        )
        self.assertEqual(
            audit,
            module.governed_workflow_audit_record_from_dict(
                module.governed_workflow_audit_record_to_dict(audit)
            ),
        )
        self.assertEqual(
            transaction,
            module.governed_workflow_transaction_metadata_from_dict(
                module.governed_workflow_transaction_metadata_to_dict(transaction)
            ),
        )

    def test_deterministic_ids(self) -> None:
        module = self.module()
        self.assertEqual(
            module.create_persistence_request_id("runtime_gate_review", "Gate 1"),
            module.create_persistence_request_id("runtime_gate_review", "Gate 1"),
        )
        self.assertEqual(
            "GOVERNED-WORKFLOW-PERSISTENCE-REQUEST-RUNTIME-GATE-REVIEW-GATE-1",
            module.create_persistence_request_id("runtime_gate_review", "Gate 1"),
        )
        request_id = module.create_persistence_request_id(
            "model_registry_review",
            "MODEL-1",
        )
        self.assertEqual(
            module.create_persistence_validation_id(request_id),
            module.create_persistence_validation_id(request_id),
        )
        self.assertEqual(
            module.create_transaction_group_id("idem-001", "workflow_record"),
            module.create_transaction_group_id("idem-001", "workflow_record"),
        )

    def test_no_forbidden_imports_or_functions(self) -> None:
        functions = function_names(MODULE_PATH)
        for forbidden in FORBIDDEN_FUNCTION_NAMES:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, functions)


if __name__ == "__main__":
    unittest.main()
