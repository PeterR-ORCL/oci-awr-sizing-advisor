"""Phase 7BW tests for scoring runtime activation metadata."""

from __future__ import annotations

import ast
import importlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "learning" / "scoring_runtime_activation.py"
DOCS = ROOT / "docs" / "architecture"
ACTIVATION_DOC = DOCS / "phase7bw_scoring_runtime_config_activation.md"
MODEL_DOC = DOCS / "phase7bw_scoring_runtime_config_model.md"

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
    "src.scoring",
    "src.parser",
    "src.parsing",
    "src.decision",
    "src.recommendation",
    "src.recommendations",
    "src.reporting",
    "scripts.run_analysis",
    "scripts.awr_memory_cli",
)

FORBIDDEN_FUNCTION_NAMES = (
    "apply_scoring_config",
    "activate_scoring_config",
    "update_runtime_scoring",
    "modify_scoring_weights",
    "modify_thresholds",
    "mutate_score_output",
    "invoke_scoring_runtime",
    "run_scoring_engine",
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


class Phase7BWScoringRuntimeActivationTests(unittest.TestCase):
    @staticmethod
    def module():
        return importlib.import_module("src.learning.scoring_runtime_activation")

    def make_package(self, **overrides):
        module = self.module()
        review_id = overrides.get("source_scoring_review_id", "SCORING-REVIEW-001")
        version = overrides.get("scoring_config_version", "v1")
        values = {
            "package_id": module.create_scoring_runtime_package_id(review_id, version),
            "source_scoring_review_id": review_id,
            "source_materialization_id": "MAT-SCORING-001",
            "scoring_config_version": version,
            "affected_domains": ["CPU", "IO"],
            "affected_components": ["domain_weights", "thresholds"],
            "proposed_config_summary": "Review scoring weight and threshold metadata",
            "score_scale": module.SCORE_SCALE,
            "confidence_scale": module.CONFIDENCE_SCALE,
            "weight_changes": {"CPU": {"from": 1.0, "to": 1.1}},
            "threshold_changes": {"critical": {"from": 90, "to": 92}},
            "severity_cutoff_changes": {"high": {"from": 70, "to": 75}},
            "confidence_rule_changes": {"min_evidence": 2},
            "trend_sensitivity_changes": {"CPU": "metadata-only"},
            "anomaly_sensitivity_changes": {"IO": "metadata-only"},
            "before_after_reference": "before-after://phase7bw",
            "regression_reference": "regression://phase7bw",
            "phase4i_score_contract_reference": "phase4i-score://phase7bw",
            "rollback_reference": "rollback://phase7bw",
            "package_status": "eligible_for_runtime_review",
            "runtime_eligible": False,
            "runtime_active": False,
            "scoring_config_applied": False,
            "score_output_mutation_performed": False,
            "phase4i_mutation_performed": False,
            "created_by": "unit-test",
            "created_at": "2026-05-16T00:00:00Z",
            "notes": "metadata only",
        }
        values.update(overrides)
        return module.ScoringRuntimeConfigPackage(**values)

    def make_manifest(self, package_id=None, **overrides):
        module = self.module()
        package_id = package_id or self.make_package().package_id
        manifest_version = overrides.get("manifest_version", "v1")
        values = {
            "manifest_id": module.create_scoring_activation_manifest_id(
                package_id,
                manifest_version,
            ),
            "package_id": package_id,
            "manifest_version": manifest_version,
            "activation_mode": "manual_review_required",
            "explicit_activation_required": True,
            "validation_reference": "manifest-validation://phase7bw",
            "rollback_reference": "rollback://phase7bw",
            "runtime_gate_reference": "runtime-gate://phase7bw",
            "deterministic_fallback_available": True,
            "phase4i_score_contract_preserved": True,
            "runtime_activation_requested": False,
            "runtime_activation_approved": False,
            "runtime_active": False,
            "scoring_config_applied": False,
            "created_by": "unit-test",
            "created_at": "2026-05-16T00:00:00Z",
            "notes": "metadata only",
        }
        values.update(overrides)
        return module.ScoringActivationManifest(**values)

    def make_rollback(self, package_id=None, **overrides):
        module = self.module()
        package_id = package_id or self.make_package().package_id
        strategy = overrides.get("rollback_strategy", "restore_current_scoring_config")
        values = {
            "rollback_id": module.create_scoring_rollback_id(package_id, strategy),
            "package_id": package_id,
            "rollback_strategy": strategy,
            "rollback_reference": "rollback://phase7bw",
            "rollback_validated": True,
            "rollback_executed": False,
            "scoring_config_reverted": False,
            "notes": "rollback metadata only",
        }
        values.update(overrides)
        return module.ScoringRollbackReference(**values)

    def make_regression(self, package_id=None, **overrides):
        module = self.module()
        package_id = package_id or self.make_package().package_id
        reference = overrides.get("test_suite_reference", "scoring-suite://phase7bw")
        values = {
            "regression_id": module.create_scoring_regression_id(package_id, reference),
            "package_id": package_id,
            "test_suite_reference": reference,
            "before_after_reference": "before-after://phase7bw",
            "score_contract_reference": "phase4i-score://phase7bw",
            "regression_passed": True,
            "score_scale_valid": True,
            "confidence_scale_valid": True,
            "phase4i_contract_preserved": True,
            "notes": "regression metadata only",
        }
        values.update(overrides)
        return module.ScoringRegressionEvidence(**values)

    def test_import_safety_no_runtime_imports(self) -> None:
        module = self.module()
        self.assertTrue(hasattr(module, "ScoringRuntimeConfigPackage"))
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
        self.assertTrue(ACTIVATION_DOC.is_file(), ACTIVATION_DOC)
        self.assertTrue(MODEL_DOC.is_file(), MODEL_DOC)
        combined = f"{read_text(ACTIVATION_DOC)}\n{read_text(MODEL_DOC)}".lower()
        for phrase in (
            "no scoring modules are modified",
            "no scoring config is applied",
            "no score output is changed",
            "eligible means metadata eligible, not active",
            "runtime_active=false",
            "scoring_config_applied=false",
            "score scale remains 0-100",
            "confidence scale remains 0-1",
            "deterministic fallback required",
            "phase 4i preserved",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

    def test_supported_statuses_and_activation_modes(self) -> None:
        module = self.module()
        self.assertEqual(module.SCORE_SCALE, "0_100")
        self.assertEqual(module.CONFIDENCE_SCALE, "0_1")
        self.assertIn(
            "eligible_for_runtime_review",
            module.SCORING_RUNTIME_PACKAGE_STATUSES,
        )
        self.assertIn(
            "eligible_metadata_only",
            module.SCORING_RUNTIME_ELIGIBILITY_STATUSES,
        )
        self.assertEqual(
            set(module.SCORING_RUNTIME_ACTIVATION_MODES),
            {
                "disabled",
                "manual_review_required",
                "future_runtime_manifest",
                "emergency_disabled",
            },
        )

    def test_package_validation(self) -> None:
        module = self.module()
        package = self.make_package()
        self.assertIs(module.validate_scoring_runtime_config_package(package), package)
        self.assertFalse(package.runtime_eligible)
        self.assertFalse(package.runtime_active)
        self.assertFalse(package.scoring_config_applied)

        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_package(package_status="regression_ready", rollback_reference=None)
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_package(score_scale="0_1")

    def test_manifest_validation(self) -> None:
        module = self.module()
        manifest = self.make_manifest()
        self.assertIs(module.validate_scoring_activation_manifest(manifest), manifest)
        self.assertTrue(manifest.explicit_activation_required)
        self.assertTrue(manifest.deterministic_fallback_available)
        self.assertTrue(manifest.phase4i_score_contract_preserved)
        self.assertFalse(manifest.runtime_active)

    def test_eligibility_validation(self) -> None:
        module = self.module()
        package = self.make_package()
        manifest = self.make_manifest(package.package_id)
        record = module.evaluate_scoring_runtime_eligibility(package, manifest)
        self.assertIs(module.validate_scoring_runtime_eligibility_record(record), record)
        self.assertTrue(record.eligible)
        self.assertEqual("eligible_metadata_only", record.eligibility_status)
        self.assertFalse(record.runtime_active)
        self.assertFalse(record.scoring_config_applied)

        with self.assertRaises(module.ScoringRuntimeActivationError):
            module.ScoringRuntimeEligibilityRecord(
                eligibility_id=record.eligibility_id,
                package_id=record.package_id,
                manifest_id=record.manifest_id,
                eligible=True,
                eligibility_status="eligible_metadata_only",
                required_validation_present=True,
                regression_reference_present=False,
                before_after_reference_present=True,
                phase4i_score_contract_reference_present=True,
                rollback_reference_present=True,
                runtime_gate_reference_present=True,
                deterministic_fallback_available=True,
                score_scale_valid=True,
                confidence_scale_valid=True,
            )

    def test_rollback_validation(self) -> None:
        module = self.module()
        rollback = self.make_rollback()
        self.assertIs(module.validate_scoring_rollback_reference(rollback), rollback)
        self.assertFalse(rollback.rollback_executed)
        self.assertFalse(rollback.scoring_config_reverted)

    def test_regression_evidence_validation(self) -> None:
        module = self.module()
        evidence = self.make_regression()
        self.assertIs(module.validate_scoring_regression_evidence(evidence), evidence)
        self.assertTrue(evidence.regression_passed)
        self.assertTrue(evidence.score_scale_valid)
        self.assertTrue(evidence.confidence_scale_valid)
        self.assertTrue(evidence.phase4i_contract_preserved)

    def test_eligibility_evaluation_missing_references(self) -> None:
        module = self.module()
        manifest = self.make_manifest()

        package = self.make_package(regression_reference=None)
        record = module.evaluate_scoring_runtime_eligibility(package, manifest)
        self.assertFalse(record.eligible)
        self.assertEqual("needs_regression_reference", record.eligibility_status)

        package = self.make_package(before_after_reference=None)
        record = module.evaluate_scoring_runtime_eligibility(package, manifest)
        self.assertFalse(record.eligible)
        self.assertEqual("needs_before_after_reference", record.eligibility_status)

        package = self.make_package(phase4i_score_contract_reference=None)
        record = module.evaluate_scoring_runtime_eligibility(package, manifest)
        self.assertFalse(record.eligible)
        self.assertEqual("needs_phase4i_score_contract", record.eligibility_status)

    def test_eligible_metadata_requires_all_validation_refs(self) -> None:
        module = self.module()
        package = self.make_package()
        manifest = self.make_manifest(package.package_id, runtime_gate_reference=None)
        record = module.evaluate_scoring_runtime_eligibility(package, manifest)
        self.assertFalse(record.eligible)
        self.assertEqual("needs_runtime_gate", record.eligibility_status)

        manifest = self.make_manifest(package.package_id, rollback_reference=None)
        record = module.evaluate_scoring_runtime_eligibility(package, manifest)
        self.assertFalse(record.eligible)
        self.assertEqual("needs_rollback_reference", record.eligibility_status)

    def test_score_scale_must_be_0_100(self) -> None:
        module = self.module()
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_package(score_scale="0_1")
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_regression(score_scale_valid=False)

    def test_confidence_scale_must_be_0_1(self) -> None:
        module = self.module()
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_package(confidence_scale="0_100")
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_regression(confidence_scale_valid=False)

    def test_runtime_active_true_fails(self) -> None:
        module = self.module()
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_package(runtime_active=True)
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_manifest(runtime_active=True)
        record = module.evaluate_scoring_runtime_eligibility(
            self.make_package(),
            self.make_manifest(),
        )
        values = module.scoring_runtime_eligibility_record_to_dict(record)
        values["runtime_active"] = True
        with self.assertRaises(module.ScoringRuntimeActivationError):
            module.scoring_runtime_eligibility_record_from_dict(values)

    def test_scoring_config_applied_true_fails(self) -> None:
        module = self.module()
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_package(scoring_config_applied=True)
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_manifest(scoring_config_applied=True)

    def test_score_output_mutation_performed_true_fails(self) -> None:
        module = self.module()
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_package(score_output_mutation_performed=True)

    def test_phase4i_mutation_performed_true_fails(self) -> None:
        module = self.module()
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_package(phase4i_mutation_performed=True)

    def test_runtime_activation_requested_or_approved_true_fails(self) -> None:
        module = self.module()
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_manifest(runtime_activation_requested=True)
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_manifest(runtime_activation_approved=True)

    def test_rollback_executed_true_fails(self) -> None:
        module = self.module()
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_rollback(rollback_executed=True)
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_rollback(scoring_config_reverted=True)

    def test_deterministic_fallback_false_fails(self) -> None:
        module = self.module()
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_manifest(deterministic_fallback_available=False)
        record = module.evaluate_scoring_runtime_eligibility(
            self.make_package(),
            self.make_manifest(),
        )
        values = module.scoring_runtime_eligibility_record_to_dict(record)
        values["deterministic_fallback_available"] = False
        with self.assertRaises(module.ScoringRuntimeActivationError):
            module.scoring_runtime_eligibility_record_from_dict(values)
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_manifest(phase4i_score_contract_preserved=False)
        with self.assertRaises(module.ScoringRuntimeActivationError):
            self.make_regression(phase4i_contract_preserved=False)

    def test_serialization_round_trip(self) -> None:
        module = self.module()
        package = self.make_package()
        manifest = self.make_manifest(package.package_id)
        record = module.evaluate_scoring_runtime_eligibility(package, manifest)
        rollback = self.make_rollback(package.package_id)
        evidence = self.make_regression(package.package_id)

        self.assertEqual(
            package,
            module.scoring_runtime_config_package_from_dict(
                module.scoring_runtime_config_package_to_dict(package)
            ),
        )
        self.assertEqual(
            manifest,
            module.scoring_activation_manifest_from_dict(
                module.scoring_activation_manifest_to_dict(manifest)
            ),
        )
        self.assertEqual(
            record,
            module.scoring_runtime_eligibility_record_from_dict(
                module.scoring_runtime_eligibility_record_to_dict(record)
            ),
        )
        self.assertEqual(
            rollback,
            module.scoring_rollback_reference_from_dict(
                module.scoring_rollback_reference_to_dict(rollback)
            ),
        )
        self.assertEqual(
            evidence,
            module.scoring_regression_evidence_from_dict(
                module.scoring_regression_evidence_to_dict(evidence)
            ),
        )

    def test_deterministic_ids(self) -> None:
        module = self.module()
        package_id = module.create_scoring_runtime_package_id(
            "SCORING-REVIEW-1",
            "v1",
        )
        self.assertEqual(
            "SCORING-RUNTIME-PACKAGE-SCORING-REVIEW-1-V1",
            package_id,
        )
        self.assertEqual(
            module.create_scoring_activation_manifest_id(package_id, "v1"),
            module.create_scoring_activation_manifest_id(package_id, "v1"),
        )
        manifest_id = module.create_scoring_activation_manifest_id(package_id, "v1")
        self.assertEqual(
            module.create_scoring_runtime_eligibility_id(package_id, manifest_id),
            module.create_scoring_runtime_eligibility_id(package_id, manifest_id),
        )
        self.assertEqual(
            module.create_scoring_rollback_id(package_id, "restore_current"),
            module.create_scoring_rollback_id(package_id, "restore_current"),
        )
        self.assertEqual(
            module.create_scoring_regression_id(package_id, "suite-1"),
            module.create_scoring_regression_id(package_id, "suite-1"),
        )

    def test_no_mutation_or_apply_functions(self) -> None:
        functions = function_names(MODULE_PATH)
        for forbidden in FORBIDDEN_FUNCTION_NAMES:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, functions)


if __name__ == "__main__":
    unittest.main()
