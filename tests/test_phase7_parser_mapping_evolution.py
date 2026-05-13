from __future__ import annotations

import ast
from copy import deepcopy
import importlib
import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
PARSER_MAPPING_EVOLUTION_DOC = DOCS / "phase7_parser_mapping_evolution.md"
PARSER_EVOLUTION_MODEL_DOC = DOCS / "phase7_parser_evolution_model.md"
MODULE_PATH = ROOT / "src" / "learning" / "parser_mapping_evolution.py"

REQUIRED_EVOLUTION_TYPES = (
    "new_section_mapping",
    "section_mapping_refinement",
    "unknown_signal_mapping",
    "regex_pattern_review",
    "normalization_rule_review",
    "field_extraction_review",
    "unit_conversion_review",
    "parser_confidence_metadata_review",
    "section_registry_review",
    "parser_regression_test_addition",
)

REQUIRED_CHANGE_TYPES = (
    "parser_code_change",
    "parser_config_change",
    "regex_mapping_change",
    "section_registry_change",
    "normalization_rule_change",
    "field_extraction_change",
    "unit_conversion_change",
    "test_only_change",
    "documentation_change",
)

RUNTIME_PATHS = (
    "scripts/run_analysis.py",
    "src/parser",
    "src/parsing",
    "src/scoring",
    "src/decision",
    "src/recommendation",
    "src/recommendations",
    "src/analysis",
)

FORBIDDEN_ACTIVE_FUNCTIONS = (
    "apply_parser_mapping",
    "activate_parser_mapping",
    "mutate_parser",
    "update_runtime_parser",
    "update_parser_regex",
    "auto_apply",
    "autonomous_apply",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def lower_text(path: Path) -> str:
    return read_text(path).lower()


def evolution_module():
    return importlib.import_module("src.learning.parser_mapping_evolution")


def artifact_module():
    return importlib.import_module("src.learning.materialization_artifact")


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


class Phase7ParserMappingEvolutionTests(unittest.TestCase):
    def test_01_module_import_safety(self) -> None:
        before_environment = dict(os.environ)

        module = evolution_module()

        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(module, "ParserMappingEvolution"))
        imports = imported_modules(MODULE_PATH)
        for forbidden in (
            "oracledb",
            "requests",
            "socket",
            "urllib",
            "http.client",
            "httpx",
            "oci",
            "oracle_agent_memory",
            "src.parser",
            "src.parsing",
            "src.scoring",
            "src.decision",
            "src.recommendation",
            "src.recommendations",
            "src.reporting",
            "scripts.run_analysis",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        imported == forbidden or imported.startswith(f"{forbidden}.")
                        for imported in imports
                    )
                )

    def test_docs_exist(self) -> None:
        self.assertTrue(PARSER_MAPPING_EVOLUTION_DOC.is_file(), PARSER_MAPPING_EVOLUTION_DOC)
        self.assertTrue(PARSER_EVOLUTION_MODEL_DOC.is_file(), PARSER_EVOLUTION_MODEL_DOC)

    def test_docs_contain_required_boundary_phrases(self) -> None:
        combined = (
            f"{lower_text(PARSER_MAPPING_EVOLUTION_DOC)}\n"
            f"{lower_text(PARSER_EVOLUTION_MODEL_DOC)}"
        )
        for phrase in (
            "proposal-only",
            "no runtime parser changes are applied",
            "runtime_influence_granted=false",
            "parser backlog items are inactive",
            "implemented does not mean runtime active",
            "validated does not mean runtime active by itself",
            "existing parser remains authoritative",
            "no automatic parser mutation",
            "semantic context is not parser truth",
            "dashboard and cli are not parser mutation paths",
            "phase 4i contract must be preserved",
            "scoring regression validation is required",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, combined)

    def test_supported_evolution_types(self) -> None:
        module = evolution_module()
        self.assertEqual(set(module.PARSER_EVOLUTION_TYPES), set(REQUIRED_EVOLUTION_TYPES))
        for evolution_type in REQUIRED_EVOLUTION_TYPES:
            with self.subTest(evolution_type=evolution_type):
                self.assertTrue(module.is_supported_parser_evolution_type(evolution_type))
                self.assertIn(
                    "parser tests",
                    module.required_parser_validation_requirements(evolution_type),
                )
        self.assertFalse(module.is_supported_parser_evolution_type("scoring_review"))
        with self.assertRaises(module.ParserMappingEvolutionError):
            module.required_parser_validation_requirements("scoring_review")

    def test_supported_parser_change_types(self) -> None:
        module = evolution_module()
        self.assertEqual(set(module.PARSER_CHANGE_TYPES), set(REQUIRED_CHANGE_TYPES))
        for change_type in REQUIRED_CHANGE_TYPES:
            with self.subTest(change_type=change_type):
                self.assertTrue(module.is_supported_parser_change_type(change_type))
        self.assertFalse(module.is_supported_parser_change_type("runtime_activation"))
        with self.assertRaises(module.ParserMappingEvolutionError):
            self.create_evolution(proposed_parser_change_type="runtime_activation")

    def test_source_artifact_requirement(self) -> None:
        module = evolution_module()

        evolution = self.create_evolution()
        self.assertEqual(
            evolution.source_materialization_id,
            self.make_source_artifact().materialization_id,
        )

        for candidate_type in (
            "scoring_weight_review_candidate",
            "recommendation_rule_candidate",
        ):
            with self.subTest(candidate_type=candidate_type):
                with self.assertRaises(module.ParserMappingEvolutionError):
                    self.create_evolution(
                        source=self.make_source_artifact(candidate_type=candidate_type)
                    )

        for status in ("REJECTED", "ROLLED_BACK", "CLOSED"):
            with self.subTest(status=status):
                with self.assertRaises(module.ParserMappingEvolutionError):
                    self.create_evolution(source=self.make_source_artifact(status=status))

        source_data = self.make_source_artifact_data()
        source_data["runtime_influence_granted"] = True
        with self.assertRaises(module.ParserMappingEvolutionError):
            self.create_evolution(source=source_data)

    def test_evolution_creation(self) -> None:
        module = evolution_module()
        source = self.make_source_artifact()
        evolution = self.create_evolution(source=source)

        expected_id = module.create_parser_evolution_id(
            source.materialization_id,
            "new_section_mapping",
            parser_section="SQL ordered by Elapsed Time",
            signal_name="elapsed_time",
        )
        self.assertEqual(evolution.evolution_id, expected_id)
        self.assertTrue(evolution.evolution_id.startswith("PARSER-EVO-NEW-SECTION-MAPPING-"))
        self.assertNotRegex(
            evolution.evolution_id,
            re.compile(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                re.IGNORECASE,
            ),
        )
        self.assertTrue(evolution.phase4i_contract_required)
        self.assertTrue(evolution.awr_regression_required)
        self.assertTrue(evolution.scoring_regression_required)
        self.assertFalse(evolution.runtime_influence_granted)
        self.assertEqual(evolution.status, "PROPOSED")
        self.assertEqual(evolution.semantic_context, {"summary": "Reviewer-assist context only."})

        for kwargs in (
            {"actor": ""},
            {"proposed_mapping": {}},
            {"proposed_mapping": None},
            {"proposed_mapping_summary": ""},
            {"rollback_plan": ""},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(module.ParserMappingEvolutionError):
                    self.create_evolution(**kwargs)

        data = module.parser_mapping_evolution_to_dict(evolution)
        data["phase4i_contract_required"] = False
        with self.assertRaises(module.ParserMappingEvolutionError):
            module.parser_mapping_evolution_from_dict(data)

        data = module.parser_mapping_evolution_to_dict(evolution)
        data["awr_regression_required"] = False
        with self.assertRaises(module.ParserMappingEvolutionError):
            module.parser_mapping_evolution_from_dict(data)

        data = module.parser_mapping_evolution_to_dict(evolution)
        data["scoring_regression_required"] = False
        with self.assertRaises(module.ParserMappingEvolutionError):
            module.parser_mapping_evolution_from_dict(data)

    def test_validation_requirements(self) -> None:
        module = evolution_module()
        with self.assertRaises(module.ParserMappingEvolutionError):
            self.create_evolution(validation_requirements=["parser tests"])

        evolution = self.create_evolution()
        requirements = "\n".join(evolution.validation_requirements).lower()
        for phrase in (
            "parser tests",
            "awr regression validation",
            "phase 4i contract validation",
            "unknown signal safety",
            "scoring regression check",
            "rollback plan",
            "deterministic runtime remains authoritative",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, requirements)

        data = module.parser_mapping_evolution_to_dict(evolution)
        data["runtime_influence_granted"] = True
        with self.assertRaises(module.ParserMappingEvolutionError):
            module.parser_mapping_evolution_from_dict(data)

    def test_evolution_type_specific_validation(self) -> None:
        module = evolution_module()
        cases = {
            "new_section_mapping": "section detection validation",
            "section_mapping_refinement": "old/new section comparison",
            "unknown_signal_mapping": "unknown signal safety validation",
            "regex_pattern_review": "regex regression validation",
            "normalization_rule_review": "normalization regression validation",
            "field_extraction_review": "field extraction validation",
            "unit_conversion_review": "unit conversion validation",
            "parser_confidence_metadata_review": "parser confidence metadata validation",
            "section_registry_review": "registry compatibility validation",
            "parser_regression_test_addition": "test coverage validation",
        }
        for evolution_type, required_phrase in cases.items():
            with self.subTest(evolution_type=evolution_type):
                evolution = self.create_evolution(evolution_type=evolution_type)
                self.assertIn(required_phrase, "\n".join(evolution.validation_requirements))

                requirements = module.required_parser_validation_requirements(evolution_type)
                requirements.remove(required_phrase)
                with self.assertRaises(module.ParserMappingEvolutionError):
                    self.create_evolution(
                        evolution_type=evolution_type,
                        validation_requirements=requirements,
                    )

    def test_parser_backlog_item(self) -> None:
        module = evolution_module()
        evolution = self.create_evolution()
        item = module.create_parser_backlog_item(evolution)

        self.assertFalse(item.runtime_active)
        self.assertFalse(item.runtime_influence_granted)
        self.assertEqual(item.source_evolution_id, evolution.evolution_id)
        self.assertEqual(item.source_materialization_id, evolution.source_materialization_id)
        self.assertEqual(item.source_candidate_id, evolution.source_candidate_id)
        self.assertEqual(
            item.backlog_id,
            f"PARSER-BACKLOG-{evolution.evolution_id}",
        )

        data = module.parser_backlog_item_to_dict(item)
        data["runtime_active"] = True
        with self.assertRaises(module.ParserMappingEvolutionError):
            module.parser_backlog_item_from_dict(data)

        data = module.parser_backlog_item_to_dict(item)
        data["runtime_influence_granted"] = True
        with self.assertRaises(module.ParserMappingEvolutionError):
            module.parser_backlog_item_from_dict(data)

    def test_serialization(self) -> None:
        module = evolution_module()
        evolution = self.create_evolution()
        evolution_data = module.parser_mapping_evolution_to_dict(evolution)
        self.assertEqual(tuple(evolution_data.keys()), module.PARSER_MAPPING_EVOLUTION_FIELDS)
        self.assertEqual(module.parser_mapping_evolution_from_dict(evolution_data), evolution)
        self.assertEqual(
            module.parser_mapping_evolutions_to_dicts([evolution, evolution]),
            [evolution_data, evolution_data],
        )

        item = module.create_parser_backlog_item(evolution)
        item_data = module.parser_backlog_item_to_dict(item)
        self.assertEqual(tuple(item_data.keys()), module.PARSER_BACKLOG_ITEM_FIELDS)
        self.assertEqual(module.parser_backlog_item_from_dict(item_data), item)
        self.assertEqual(
            module.parser_backlog_items_to_dicts([item, item]),
            [item_data, item_data],
        )

        evolution_data["source_evidence"][0]["source_id"] = "mutated"
        self.assertEqual(evolution.source_evidence[0]["source_id"], "SRC-1")

    def test_no_source_mutation(self) -> None:
        source_data = self.make_source_artifact_data()
        original = deepcopy(source_data)

        self.create_evolution(source=source_data)

        self.assertEqual(source_data, original)

    def test_runtime_import_isolation(self) -> None:
        for path in python_files(RUNTIME_PATHS):
            imports = imported_modules(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.parser_mapping_evolution", imports)
                self.assertNotIn("learning.parser_mapping_evolution", imports)
                self.assertNotIn("parser_mapping_evolution", imports)

    def test_no_active_mutation_functions(self) -> None:
        tree = ast.parse(read_text(MODULE_PATH), filename=str(MODULE_PATH))
        function_names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }
        for forbidden_name in FORBIDDEN_ACTIVE_FUNCTIONS:
            with self.subTest(function_name=forbidden_name):
                self.assertNotIn(forbidden_name, function_names)

    def create_evolution(self, source=None, **overrides):
        module = evolution_module()
        kwargs = {
            "materialization_artifact": self.make_source_artifact() if source is None else source,
            "actor": "parser-owner@example.com",
            "evolution_type": "new_section_mapping",
            "proposed_mapping": self.proposed_mapping(),
            "proposed_mapping_summary": (
                "Review a proposed parser mapping for SQL elapsed time section coverage."
            ),
            "parser_section": "SQL ordered by Elapsed Time",
            "signal_name": "elapsed_time",
            "proposed_parser_change_type": None,
            "implementation_reference": "parser-backlog/sql-elapsed-time",
            "validation_requirements": None,
            "rollback_plan": (
                "Keep current runtime parser mappings and discard this proposal."
            ),
            "runtime_influence_requested": True,
        }
        kwargs.update(overrides)
        return module.create_parser_mapping_evolution(**kwargs)

    def make_source_artifact(
        self,
        candidate_type: str = "parser_mapping_candidate",
        status: str = "MATERIALIZED",
    ):
        artifact = artifact_module().create_materialization_artifact(
            self.make_candidate_data(candidate_type=candidate_type),
            actor="materialization-owner@example.com",
            proposed_change_summary="Prepare a controlled materialization artifact.",
            rollback_plan="Restore the previous governed runtime-sensitive configuration.",
        )
        data = artifact_module().materialization_artifact_to_dict(artifact)
        data["status"] = status
        return artifact_module().materialization_artifact_from_dict(data)

    def make_source_artifact_data(
        self,
        candidate_type: str = "parser_mapping_candidate",
        status: str = "MATERIALIZED",
    ) -> dict[str, object]:
        return artifact_module().materialization_artifact_to_dict(
            self.make_source_artifact(candidate_type=candidate_type, status=status)
        )

    def proposed_mapping(self) -> dict[str, object]:
        return {
            "section_key": "sql_ordered_by_elapsed_time",
            "section_title": "SQL ordered by Elapsed Time",
            "fields": ["sql_id", "elapsed_time", "executions"],
            "normalization": {
                "elapsed_time": "seconds",
                "executions": "count",
            },
            "review_only": True,
        }

    def make_candidate_data(
        self,
        candidate_type: str = "parser_mapping_candidate",
        status: str = "APPROVED_FOR_IMPLEMENTATION",
    ) -> dict[str, object]:
        component_by_type = {
            "parser_mapping_candidate": "parser",
            "scoring_weight_review_candidate": "scoring",
            "recommendation_rule_candidate": "recommendation",
        }
        return {
            "candidate_id": f"CANDIDATE-{candidate_type.upper().replace('_', '-')}-1",
            "candidate_type": candidate_type,
            "title": f"Candidate for {candidate_type}",
            "description": "Approved governed learning candidate.",
            "source_evidence": [{"source_type": "unit_test", "source_id": "SRC-1"}],
            "structured_sources": [{"source_type": "outcome_pattern", "pattern_id": "P-1"}],
            "semantic_context": {"summary": "Reviewer-assist context only."},
            "affected_component": component_by_type[candidate_type],
            "affected_domain": "sql",
            "confidence": 0.5,
            "rationale": "Human-reviewed candidate for controlled materialization.",
            "requires_human_review": True,
            "runtime_influence": False,
            "status": status,
            "created_at": None,
            "created_by": "candidate-engine",
            "reviewed_by": "reviewer@example.com",
            "review_notes": "Approved for implementation consideration only.",
            "materialization_reference": None,
        }


if __name__ == "__main__":
    unittest.main()
