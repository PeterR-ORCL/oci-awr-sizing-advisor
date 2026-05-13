from __future__ import annotations

import ast
import importlib
import os
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
BOUNDARY_DOC = DOCS / "phase7aa_runtime_integration_boundary.md"
CONFIG_GATE_DOC = DOCS / "phase7aa_runtime_config_gate.md"
MODULE_PATH = ROOT / "src" / "learning" / "adaptive_runtime_gate.py"

RUNTIME_PATHS = (
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
    "oracledb",
    "oci",
    "requests",
    "socket",
    "urllib",
    "http.client",
    "httpx",
    "sqlite3",
    "src.parser",
    "src.parsing",
    "src.scoring",
    "src.decision",
    "src.recommendation",
    "src.recommendations",
    "src.analysis",
    "src.reporting",
    "src.memory",
)

FORBIDDEN_FUNCTION_NAMES = (
    "apply_adaptive_runtime",
    "activate_runtime",
    "update_runtime_scoring",
    "update_runtime_parser",
    "update_runtime_recommendation",
    "replace_scoring_engine",
    "auto_apply",
    "autonomous_apply",
)

EXPECTED_MODES = (
    "deterministic_only",
    "shadow_only",
    "advisory_only",
    "controlled_runtime_candidate",
)

EXPECTED_COMPONENT_TYPES = (
    "scoring",
    "recommendation",
    "parser",
    "trend_aware_scoring",
    "shadow_ml",
    "model_registry",
    "materialization_artifact",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


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
            imports.update(f"{node.module}.{alias.name}" for alias in node.names)
    return imports


def function_names(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


class Phase7AARuntimeIntegrationGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = importlib.import_module("src.learning.adaptive_runtime_gate")

    def config(self, component_type: str = "scoring", **overrides):
        module = self.module
        mode = overrides.pop("mode", "controlled_runtime_candidate")
        created_by = overrides.pop("created_by", "unit-test")
        values = {
            "config_id": module.create_adaptive_runtime_config_id(mode, created_by),
            "mode": mode,
            "adaptive_runtime_enabled": True,
            "scoring_integration_enabled": component_type == "scoring",
            "recommendation_integration_enabled": component_type == "recommendation",
            "parser_integration_enabled": component_type == "parser",
            "trend_aware_scoring_enabled": component_type == "trend_aware_scoring",
            "shadow_ml_enabled": component_type == "shadow_ml",
            "model_registry_enabled": component_type == "model_registry",
            "materialization_artifact_enabled": component_type == "materialization_artifact",
            "require_certification": True,
            "require_runtime_eligibility": True,
            "require_rollback_reference": True,
            "require_phase4i_contract_preservation": True,
            "fallback_to_deterministic": True,
            "runtime_influence_allowed": True,
            "deterministic_runtime_authoritative": True,
            "created_by": created_by,
            "notes": "unit test config",
        }
        values.update(overrides)
        return module.AdaptiveRuntimeConfig(**values)

    def eligibility(self, component_type: str = "scoring", **overrides):
        module = self.module
        artifact_id = overrides.pop("artifact_id", f"artifact://{component_type}/unit")
        model_id = overrides.pop(
            "model_id",
            f"model://{component_type}/unit" if component_type in ("shadow_ml", "model_registry") else None,
        )
        values = {
            "component_id": module.create_component_eligibility_id(
                component_type,
                artifact_id=artifact_id,
                model_id=model_id,
            ),
            "component_type": component_type,
            "artifact_id": artifact_id,
            "model_id": model_id,
            "certified": True,
            "runtime_eligible": True,
            "runtime_influence_granted": True,
            "runtime_active": False,
            "rollback_reference": "rollback://unit-test",
            "validation_reference": "validation://unit-test",
            "phase4i_contract_preserved": True,
            "notes": "unit test eligibility",
        }
        values.update(overrides)
        return module.AdaptiveComponentEligibility(**values)

    def test_module_import_safety(self) -> None:
        before_environment = dict(os.environ)
        module = importlib.import_module("src.learning.adaptive_runtime_gate")
        self.assertEqual(before_environment, dict(os.environ))

        imports = imported_modules(MODULE_PATH)
        for forbidden in FORBIDDEN_IMPORT_PREFIXES:
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        imported == forbidden or imported.startswith(f"{forbidden}.")
                        for imported in imports
                    )
                )
        for forbidden in ("uuid", "datetime", "time"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, imports)
        for forbidden_name in FORBIDDEN_FUNCTION_NAMES:
            with self.subTest(function_name=forbidden_name):
                self.assertFalse(hasattr(module, forbidden_name))

    def test_docs_exist(self) -> None:
        self.assertTrue(BOUNDARY_DOC.is_file(), BOUNDARY_DOC)
        self.assertTrue(CONFIG_GATE_DOC.is_file(), CONFIG_GATE_DOC)

    def test_docs_contain_required_boundary_phrases(self) -> None:
        combined = f"{read_text(BOUNDARY_DOC)}\n{read_text(CONFIG_GATE_DOC)}".lower()
        for phrase in (
            "adaptive runtime is opt-in only",
            "default config denies integration",
            "deterministic runtime remains authoritative",
            "fallback to deterministic runtime is required",
            "rollback reference is required",
            "phase 4i contract preservation is required",
            "allowed means allowed for consideration, not runtime activation",
            "no runtime behavior changes are made in 7aa.1",
            "scoring/recommendation/parser adapters are future work",
            "phase 8 sizing/tco is not implemented",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

    def test_default_config_denies_all_component_types(self) -> None:
        module = self.module
        config = module.default_deterministic_runtime_config()
        self.assertEqual(config.mode, "deterministic_only")
        self.assertFalse(config.adaptive_runtime_enabled)
        self.assertFalse(config.runtime_influence_allowed)
        self.assertTrue(config.deterministic_runtime_authoritative)
        self.assertTrue(config.fallback_to_deterministic)

        for component_type in EXPECTED_COMPONENT_TYPES:
            with self.subTest(component_type=component_type):
                eligibility = self.eligibility(component_type)
                result = module.evaluate_adaptive_runtime_gate(config, eligibility)
                self.assertFalse(result.allowed)
                self.assertFalse(result.allowed_for_consideration)
                self.assertFalse(result.runtime_active)
                self.assertTrue(result.deterministic_runtime_authoritative)
                self.assertTrue(result.fallback_to_deterministic)

    def test_supported_modes(self) -> None:
        module = self.module
        self.assertEqual(set(EXPECTED_MODES), set(module.ADAPTIVE_RUNTIME_MODES))
        for mode in EXPECTED_MODES:
            with self.subTest(mode=mode):
                config = module.AdaptiveRuntimeConfig(
                    config_id=module.create_adaptive_runtime_config_id(mode, "unit-test"),
                    mode=mode,
                    created_by="unit-test",
                )
                self.assertEqual(config.mode, mode)
        with self.assertRaises(module.AdaptiveRuntimeGateError):
            module.AdaptiveRuntimeConfig(config_id="CONFIG", mode="runtime_active")

    def test_supported_component_types(self) -> None:
        module = self.module
        self.assertEqual(set(EXPECTED_COMPONENT_TYPES), set(module.ADAPTIVE_COMPONENT_TYPES))
        for component_type in EXPECTED_COMPONENT_TYPES:
            with self.subTest(component_type=component_type):
                eligibility = module.AdaptiveComponentEligibility(
                    component_id=module.create_component_eligibility_id(
                        component_type,
                        artifact_id=f"artifact://{component_type}",
                    ),
                    component_type=component_type,
                    artifact_id=f"artifact://{component_type}",
                )
                self.assertEqual(eligibility.component_type, component_type)
        with self.assertRaises(module.AdaptiveRuntimeGateError):
            module.AdaptiveComponentEligibility(
                component_id="ADAPTIVE-COMPONENT-UNSUPPORTED-X",
                component_type="unsupported",
            )

    def test_gate_denies_when_required_conditions_are_missing(self) -> None:
        module = self.module
        baseline_config = self.config("scoring")
        baseline_eligibility = self.eligibility("scoring")
        cases = (
            (
                "adaptive_runtime_disabled",
                module.AdaptiveRuntimeConfig(
                    **{
                        **module.adaptive_runtime_config_to_dict(baseline_config),
                        "adaptive_runtime_enabled": False,
                    }
                ),
                baseline_eligibility,
                "adaptive_runtime_disabled",
            ),
            (
                "runtime_influence_not_allowed",
                module.AdaptiveRuntimeConfig(
                    **{
                        **module.adaptive_runtime_config_to_dict(baseline_config),
                        "runtime_influence_allowed": False,
                    }
                ),
                baseline_eligibility,
                "runtime_influence_not_allowed",
            ),
            (
                "component_flag_disabled",
                module.AdaptiveRuntimeConfig(
                    **{
                        **module.adaptive_runtime_config_to_dict(baseline_config),
                        "scoring_integration_enabled": False,
                    }
                ),
                baseline_eligibility,
                "scoring_integration_enabled_disabled",
            ),
            (
                "certification_missing",
                baseline_config,
                module.AdaptiveComponentEligibility(
                    **{
                        **module.component_eligibility_to_dict(baseline_eligibility),
                        "certified": False,
                    }
                ),
                "certification_required",
            ),
            (
                "runtime_eligibility_missing",
                baseline_config,
                module.AdaptiveComponentEligibility(
                    **{
                        **module.component_eligibility_to_dict(baseline_eligibility),
                        "runtime_eligible": False,
                    }
                ),
                "runtime_eligibility_required",
            ),
            (
                "runtime_influence_grant_missing",
                baseline_config,
                module.AdaptiveComponentEligibility(
                    **{
                        **module.component_eligibility_to_dict(baseline_eligibility),
                        "runtime_influence_granted": False,
                    }
                ),
                "runtime_influence_grant_required",
            ),
            (
                "rollback_reference_missing",
                baseline_config,
                module.AdaptiveComponentEligibility(
                    **{
                        **module.component_eligibility_to_dict(baseline_eligibility),
                        "rollback_reference": None,
                    }
                ),
                "rollback_reference_required",
            ),
            (
                "validation_reference_missing",
                baseline_config,
                module.AdaptiveComponentEligibility(
                    **{
                        **module.component_eligibility_to_dict(baseline_eligibility),
                        "validation_reference": None,
                    }
                ),
                "validation_reference_required",
            ),
            (
                "phase4i_contract_not_preserved",
                baseline_config,
                module.AdaptiveComponentEligibility(
                    **{
                        **module.component_eligibility_to_dict(baseline_eligibility),
                        "phase4i_contract_preserved": False,
                    }
                ),
                "phase4i_contract_preservation_required",
            ),
            (
                "fallback_disabled_without_runtime_enablement",
                module.AdaptiveRuntimeConfig(
                    **{
                        **module.adaptive_runtime_config_to_dict(baseline_config),
                        "adaptive_runtime_enabled": False,
                        "fallback_to_deterministic": False,
                    }
                ),
                baseline_eligibility,
                "fallback_to_deterministic_required",
            ),
        )
        for name, config, eligibility, expected_reason in cases:
            with self.subTest(name=name):
                result = module.evaluate_adaptive_runtime_gate(config, eligibility)
                self.assertFalse(result.allowed)
                self.assertIn(expected_reason, result.denied_reasons)
                self.assertFalse(result.runtime_active)

        with self.subTest(name="deterministic_runtime_authority_disabled"):
            invalid = module.adaptive_runtime_config_to_dict(baseline_config)
            invalid["deterministic_runtime_authoritative"] = False
            with self.assertRaises(module.AdaptiveRuntimeGateError):
                module.evaluate_adaptive_runtime_gate(invalid, baseline_eligibility)

    def test_gate_allows_consideration_only_when_all_gates_pass(self) -> None:
        module = self.module
        config = self.config("scoring")
        eligibility = self.eligibility("scoring")
        result = module.evaluate_adaptive_runtime_gate(config, eligibility)
        self.assertTrue(result.allowed)
        self.assertTrue(result.allowed_for_consideration)
        self.assertFalse(result.runtime_active)
        self.assertTrue(result.deterministic_runtime_authoritative)
        self.assertTrue(result.runtime_influence_allowed)
        self.assertTrue(result.fallback_to_deterministic)
        self.assertTrue(result.phase4i_contract_preserved)
        self.assertTrue(result.runtime_influence_granted)

    def test_component_flag_mapping_for_all_supported_types(self) -> None:
        module = self.module
        for component_type in EXPECTED_COMPONENT_TYPES:
            with self.subTest(component_type=component_type):
                result = module.evaluate_adaptive_runtime_gate(
                    self.config(component_type),
                    self.eligibility(component_type),
                )
                self.assertTrue(result.allowed)
                self.assertFalse(result.runtime_active)

    def test_serialization_round_trips_are_deterministic(self) -> None:
        module = self.module
        config = self.config("model_registry")
        eligibility = self.eligibility("model_registry")
        result = module.evaluate_adaptive_runtime_gate(config, eligibility)

        config_dict = module.adaptive_runtime_config_to_dict(config)
        eligibility_dict = module.component_eligibility_to_dict(eligibility)
        result_dict = module.gate_result_to_dict(result)

        self.assertEqual(
            config_dict,
            module.adaptive_runtime_config_to_dict(
                module.adaptive_runtime_config_from_dict(config_dict)
            ),
        )
        self.assertEqual(
            eligibility_dict,
            module.component_eligibility_to_dict(
                module.component_eligibility_from_dict(eligibility_dict)
            ),
        )
        self.assertEqual(
            result_dict,
            module.gate_result_to_dict(module.gate_result_from_dict(result_dict)),
        )

    def test_deterministic_ids(self) -> None:
        module = self.module
        config_id_a = module.create_adaptive_runtime_config_id(
            "controlled_runtime_candidate",
            "reviewer@example.com",
        )
        config_id_b = module.create_adaptive_runtime_config_id(
            "controlled_runtime_candidate",
            "reviewer@example.com",
        )
        component_id_a = module.create_component_eligibility_id(
            "scoring",
            artifact_id="artifact://score-review",
        )
        component_id_b = module.create_component_eligibility_id(
            "scoring",
            artifact_id="artifact://score-review",
        )
        gate_id_a = module.create_gate_result_id(config_id_a, component_id_a)
        gate_id_b = module.create_gate_result_id(config_id_a, component_id_a)

        self.assertEqual(config_id_a, config_id_b)
        self.assertEqual(component_id_a, component_id_b)
        self.assertEqual(gate_id_a, gate_id_b)
        self.assertTrue(config_id_a.startswith("ADAPTIVE-RUNTIME-CONFIG-"))
        self.assertTrue(component_id_a.startswith("ADAPTIVE-COMPONENT-"))
        self.assertTrue(gate_id_a.startswith("ADAPTIVE-GATE-"))
        for identifier in (config_id_a, component_id_a, gate_id_a):
            with self.subTest(identifier=identifier):
                self.assertNotRegex(identifier, re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-"))
                self.assertNotRegex(identifier, re.compile(r"\d{4}-\d{2}-\d{2}"))
                self.assertNotIn("T00", identifier)

    def test_runtime_safety_validation_rejects_unsafe_records(self) -> None:
        module = self.module
        eligibility_dict = module.component_eligibility_to_dict(self.eligibility("scoring"))
        eligibility_dict["runtime_active"] = True
        with self.assertRaises(module.AdaptiveRuntimeGateError):
            module.component_eligibility_from_dict(eligibility_dict)

        config_dict = module.adaptive_runtime_config_to_dict(self.config("scoring"))
        config_dict["deterministic_runtime_authoritative"] = False
        with self.assertRaises(module.AdaptiveRuntimeGateError):
            module.adaptive_runtime_config_from_dict(config_dict)

        config_dict = module.adaptive_runtime_config_to_dict(self.config("scoring"))
        config_dict["fallback_to_deterministic"] = False
        with self.assertRaises(module.AdaptiveRuntimeGateError):
            module.adaptive_runtime_config_from_dict(config_dict)

        result_dict = module.gate_result_to_dict(
            module.evaluate_adaptive_runtime_gate(
                self.config("scoring"),
                self.eligibility("scoring"),
            )
        )
        result_dict["runtime_active"] = True
        with self.assertRaises(module.AdaptiveRuntimeGateError):
            module.gate_result_from_dict(result_dict)

    def test_no_mutation_functions(self) -> None:
        module = self.module
        names = function_names(MODULE_PATH)
        for forbidden_name in FORBIDDEN_FUNCTION_NAMES:
            with self.subTest(function_name=forbidden_name):
                self.assertNotIn(forbidden_name, names)
                self.assertFalse(hasattr(module, forbidden_name))

    def test_runtime_import_isolation(self) -> None:
        for path in python_files(RUNTIME_PATHS):
            imports = imported_modules(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.adaptive_runtime_gate", imports)
                self.assertNotIn("learning.adaptive_runtime_gate", imports)
                self.assertNotIn("adaptive_runtime_gate", imports)

    def test_existing_phase7_validation_entrypoints_still_exist(self) -> None:
        for relative_path in (
            "scripts/run_phase7_ml_validation.py",
            "scripts/run_phase7_ml_readiness_check.py",
            "scripts/run_phase7_materialization_validation.py",
            "scripts/run_phase7_materialization_readiness_check.py",
            "scripts/run_phase7_validation.py",
            "scripts/run_phase7_readiness_check.py",
            "scripts/run_phase7h_dashboard_validation.py",
            "scripts/awr_memory_cli.py",
            "scripts/run_phase6_validation.py",
        ):
            with self.subTest(relative_path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file(), relative_path)


if __name__ == "__main__":
    unittest.main()
