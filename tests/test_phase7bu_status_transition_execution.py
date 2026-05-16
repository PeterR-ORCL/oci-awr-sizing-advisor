"""Phase 7BU tests for governed status transition execution metadata."""

from __future__ import annotations

import ast
import importlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "learning" / "governance_status_transition.py"
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
    "persist_status_transition",
    "update_candidate_status",
    "update_materialization_status",
    "update_model_registry_status",
    "update_runtime_gate_state",
    "set_runtime_active",
    "activate_runtime",
    "deploy_model",
    "apply_parser_mapping",
    "apply_scoring_config",
    "apply_recommendation_rule",
    "run_analysis",
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


class Phase7BUGovernanceStatusTransitionTests(unittest.TestCase):
    @staticmethod
    def module():
        return importlib.import_module("src.learning.governance_status_transition")

    def make_request(self, **overrides):
        module = self.module()
        entity_type = overrides.get("entity_type", "learning_candidate")
        entity_id = overrides.get("entity_id", "LC-001")
        transition_action = overrides.get(
            "transition_action",
            "approve_for_implementation",
        )
        if (
            entity_type in module.GOVERNANCE_ENTITY_TYPES
            and transition_action in module.GOVERNANCE_TRANSITION_ACTIONS
        ):
            request_id = module.create_transition_request_id(
                entity_type,
                entity_id,
                transition_action,
            )
        else:
            request_id = "GOVERNANCE-STATUS-TRANSITION-REQUEST-LOCAL-TEST"
        values = {
            "transition_request_id": request_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "from_status": "under_review",
            "to_status": "approved_for_implementation",
            "transition_action": transition_action,
            "actor_id": "ACTOR-LOCAL-JANE-REVIEWER",
            "actor_audit_context": {"actor_id": "ACTOR-LOCAL-JANE-REVIEWER"},
            "validation_reference": "VALIDATION-REF-001",
            "rollback_reference": "ROLLBACK-REF-001",
            "idempotency_key": "IDEMP-TRANSITION-001",
            "payload": {"reason": "approved by reviewer"},
            "transition_requested": True,
            "transition_performed": False,
            "status_changed": False,
            "db_write_performed": False,
            "runtime_activation_requested": False,
            "runtime_active": False,
            "phase4i_mutation_requested": False,
            "created_at": "2026-05-16T00:00:00Z",
            "notes": "metadata only",
        }
        values.update(overrides)
        return module.GovernanceStatusTransitionRequest(**values)

    def test_module_import_safety(self) -> None:
        module = self.module()
        self.assertTrue(hasattr(module, "GovernanceStatusTransitionRequest"))
        self.assertTrue(hasattr(module, "GovernanceStatusTransitionResult"))

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
            "no status transition is performed in 7bu",
            "transition_performed=false",
            "status_changed=false",
            "runtime_active=false",
            "phase4i_mutation_requested=false",
            "allowed transition metadata",
            "valid_for_future_persistence",
            "metadata only",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_entity_action_and_status_values(self) -> None:
        module = self.module()
        self.assertEqual(
            set(module.GOVERNANCE_ENTITY_TYPES),
            {
                "learning_candidate",
                "materialization_artifact",
                "model_registry_entry",
                "runtime_gate",
                "parser_mapping_candidate",
                "scoring_review_candidate",
                "recommendation_rule_candidate",
                "governance_item",
                "workflow_record",
            },
        )
        self.assertIn(
            "approve_for_implementation",
            module.GOVERNANCE_TRANSITION_ACTIONS,
        )
        self.assertIn("approve_for_shadow", module.GOVERNANCE_TRANSITION_ACTIONS)
        self.assertIn(
            "valid_metadata_only",
            module.GOVERNANCE_TRANSITION_VALIDATION_STATUSES,
        )
        self.assertIn(
            "valid_for_future_persistence",
            module.GOVERNANCE_TRANSITION_RESULT_STATUSES,
        )

    def test_allowed_transition_metadata(self) -> None:
        module = self.module()
        self.assertTrue(module.is_allowed_status_transition("proposed", "under_review"))
        self.assertTrue(
            module.is_allowed_status_transition(
                "under_review",
                "approved_for_implementation",
            )
        )
        self.assertTrue(module.is_allowed_status_transition("implemented", "validated"))
        self.assertTrue(module.is_allowed_status_transition("validated", "closed"))
        self.assertTrue(module.is_allowed_status_transition("under_review", "retired"))
        self.assertTrue(module.is_allowed_status_transition("validated", "superseded"))
        self.assertFalse(module.is_allowed_status_transition("proposed", "validated"))

    def test_request_validation_and_evaluation(self) -> None:
        module = self.module()
        request = self.make_request()
        self.assertIs(module.validate_governance_status_transition_request(request), request)

        validation = module.evaluate_governance_status_transition_request(request)
        self.assertTrue(validation.valid)
        self.assertEqual("valid_metadata_only", validation.validation_status)
        self.assertTrue(validation.allowed_transition)
        self.assertTrue(validation.can_transition_later)
        self.assertFalse(validation.transition_performed)
        self.assertFalse(validation.status_changed)
        self.assertFalse(validation.db_write_performed)
        self.assertFalse(validation.runtime_active)

        unsupported = self.make_request(entity_type="dashboard_widget")
        unsupported_validation = module.evaluate_governance_status_transition_request(
            unsupported
        )
        self.assertFalse(unsupported_validation.valid)
        self.assertEqual(
            "unsupported_entity_type",
            unsupported_validation.validation_status,
        )

    def test_validation_result_validation(self) -> None:
        module = self.module()
        validation = module.evaluate_governance_status_transition_request(
            self.make_request()
        )
        self.assertIs(
            module.validate_governance_status_transition_validation(validation),
            validation,
        )
        with self.assertRaises(module.GovernanceStatusTransitionError):
            module.GovernanceStatusTransitionValidation(
                transition_validation_id=validation.transition_validation_id,
                transition_request_id=validation.transition_request_id,
                valid=True,
                validation_status="valid_metadata_only",
                entity_type="learning_candidate",
                transition_action="approve_for_implementation",
                actor_present=True,
                validation_reference_present=True,
                rollback_reference_present=True,
                idempotency_key_present=True,
                allowed_transition=True,
                can_transition_later=True,
                transition_performed=True,
                status_changed=False,
                db_write_performed=False,
                runtime_active=False,
            )

    def test_transition_result_validation(self) -> None:
        module = self.module()
        request = self.make_request()
        validation = module.evaluate_governance_status_transition_request(request)
        result = module.create_governance_status_transition_result(
            request,
            validation,
            audit_record={"audit_record_id": "AUDIT-001"},
            transaction_metadata={"transaction_group_id": "TX-001"},
        )
        self.assertIs(module.validate_governance_status_transition_result(result), result)
        self.assertEqual("valid_for_future_persistence", result.result_status)
        self.assertFalse(result.transition_performed)
        self.assertFalse(result.status_changed)
        self.assertFalse(result.db_write_performed)
        self.assertFalse(result.runtime_active)
        self.assertFalse(result.phase4i_mutation_requested)

        values = module.governance_status_transition_result_to_dict(result)
        values["status_changed"] = True
        with self.assertRaises(module.GovernanceStatusTransitionError):
            module.governance_status_transition_result_from_dict(values)

    def test_validation_rollback_and_idempotency_required(self) -> None:
        module = self.module()
        missing_idempotency = self.make_request(idempotency_key=None)
        self.assertEqual(
            "needs_idempotency_key",
            module.evaluate_governance_status_transition_request(
                missing_idempotency
            ).validation_status,
        )
        with self.assertRaises(module.GovernanceStatusTransitionError):
            module.validate_governance_status_transition_request(missing_idempotency)

        missing_rollback = self.make_request(rollback_reference=None)
        self.assertEqual(
            "needs_rollback_reference",
            module.evaluate_governance_status_transition_request(
                missing_rollback
            ).validation_status,
        )

        missing_validation = self.make_request(validation_reference=None)
        self.assertEqual(
            "needs_validation_reference",
            module.evaluate_governance_status_transition_request(
                missing_validation
            ).validation_status,
        )

    def test_no_status_change_db_write_or_runtime_active_flags(self) -> None:
        module = self.module()
        for field_name in (
            "transition_performed",
            "status_changed",
            "db_write_performed",
            "runtime_activation_requested",
            "runtime_active",
            "phase4i_mutation_requested",
        ):
            with self.subTest(field_name=field_name):
                with self.assertRaises(module.GovernanceStatusTransitionError):
                    self.make_request(**{field_name: True})

    def test_serialization_round_trip(self) -> None:
        module = self.module()
        request = self.make_request()
        validation = module.evaluate_governance_status_transition_request(request)
        result = module.create_governance_status_transition_result(
            request,
            validation,
            audit_record={"audit_record_id": "AUDIT-001"},
            transaction_metadata={"transaction_group_id": "TX-001"},
        )

        self.assertEqual(
            request,
            module.governance_status_transition_request_from_dict(
                module.governance_status_transition_request_to_dict(request)
            ),
        )
        self.assertEqual(
            validation,
            module.governance_status_transition_validation_from_dict(
                module.governance_status_transition_validation_to_dict(validation)
            ),
        )
        self.assertEqual(
            result,
            module.governance_status_transition_result_from_dict(
                module.governance_status_transition_result_to_dict(result)
            ),
        )

    def test_deterministic_ids(self) -> None:
        module = self.module()
        self.assertEqual(
            module.create_transition_request_id(
                "model_registry_entry",
                "Model 1",
                "approve_for_shadow",
            ),
            module.create_transition_request_id(
                "model_registry_entry",
                "Model 1",
                "approve_for_shadow",
            ),
        )
        self.assertEqual(
            (
                "GOVERNANCE-STATUS-TRANSITION-REQUEST-"
                "MODEL-REGISTRY-ENTRY-MODEL-1-APPROVE-FOR-SHADOW"
            ),
            module.create_transition_request_id(
                "model_registry_entry",
                "Model 1",
                "approve_for_shadow",
            ),
        )
        request_id = module.create_transition_request_id(
            "runtime_gate",
            "Gate 1",
            "close",
        )
        self.assertEqual(
            module.create_transition_validation_id(request_id),
            module.create_transition_validation_id(request_id),
        )
        self.assertEqual(
            module.create_transition_result_id(request_id),
            module.create_transition_result_id(request_id),
        )

    def test_no_forbidden_imports_or_functions(self) -> None:
        functions = function_names(MODULE_PATH)
        for forbidden in FORBIDDEN_FUNCTION_NAMES:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, functions)


if __name__ == "__main__":
    unittest.main()
