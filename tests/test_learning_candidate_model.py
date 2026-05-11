from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
MODEL_PATH = ROOT / "src" / "learning" / "learning_candidate_model.py"


REQUIRED_TYPES = (
    "parser_mapping_candidate",
    "recommendation_rule_candidate",
    "scoring_weight_review_candidate",
    "dashboard_wording_candidate",
    "dashboard_interaction_candidate",
    "governance_workflow_candidate",
    "semantic_summary_candidate",
    "documentation_candidate",
    "validation_candidate",
)

REQUIRED_STATUSES = (
    "PROPOSED",
    "UNDER_REVIEW",
    "APPROVED_FOR_IMPLEMENTATION",
    "REJECTED",
    "NEEDS_REVISION",
    "IMPLEMENTED",
    "VALIDATED",
    "CLOSED",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def model_module():
    return importlib.import_module("src.learning.learning_candidate_model")


@dataclass
class MockOutcomePattern:
    pattern_id: str = "PATTERN-REPEATED-UNKNOWN-SIGNAL-SQL-PX"
    pattern_type: str = "repeated_unknown_signal"
    title: str = "Repeated unknown signal: SQL / PX"
    description: str = "The same normalized parser unknown signal appears repeatedly."
    source_records: list[dict[str, object]] | None = None
    affected_domain: str | None = None
    affected_component: str | None = "parser"
    confidence: float = 0.65
    rationale: str = "3 source records share normalized unknown-signal key 'sql_px'."
    suggested_candidate_type: str | None = "parser_mapping_candidate"

    def __post_init__(self) -> None:
        if self.source_records is None:
            self.source_records = [
                {
                    "source_type": "unknown_signal",
                    "source_id": "u1",
                    "normalized_key": "sql_px",
                },
                {
                    "source_type": "unknown_signal",
                    "source_id": "u2",
                    "normalized_key": "sql_px",
                },
            ]


class LearningCandidateModelTests(unittest.TestCase):
    def test_01_import_safety(self) -> None:
        before_environment = dict(os.environ)

        module = model_module()

        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(module, "LearningCandidate"))
        self.assertTrue(hasattr(module, "candidate_from_pattern"))

    def test_supported_candidate_types(self) -> None:
        module = model_module()

        self.assertEqual(set(module.SUPPORTED_CANDIDATE_TYPES), set(REQUIRED_TYPES))
        for candidate_type in REQUIRED_TYPES:
            self.assertTrue(module.is_supported_candidate_type(candidate_type))
            candidate = self.make_candidate(candidate_type=candidate_type)
            self.assertEqual(candidate.candidate_type, candidate_type)

        self.assertFalse(module.is_supported_candidate_type("unsupported_candidate"))
        with self.assertRaises(ValueError):
            self.make_candidate(candidate_type="unsupported_candidate")

    def test_supported_candidate_statuses(self) -> None:
        module = model_module()

        self.assertEqual(set(module.SUPPORTED_CANDIDATE_STATUSES), set(REQUIRED_STATUSES))
        for status in REQUIRED_STATUSES:
            self.assertTrue(module.is_supported_candidate_status(status))
            candidate = self.make_candidate(status=status)
            self.assertEqual(candidate.status, status)

        self.assertFalse(module.is_supported_candidate_status("ACTIVATED"))
        with self.assertRaises(ValueError):
            self.make_candidate(status="ACTIVATED")

    def test_default_candidate_behavior(self) -> None:
        module = model_module()
        candidate = module.LearningCandidate(
            candidate_id="CANDIDATE-PARSER-MAPPING-CANDIDATE-DEFAULT",
            candidate_type="parser_mapping_candidate",
            title="Review parser signal",
            description="Review repeated unknown parser signal.",
            rationale="Repeated governed records justify human review.",
        )

        self.assertEqual(candidate.source_evidence, [])
        self.assertEqual(candidate.structured_sources, [])
        self.assertIsNone(candidate.semantic_context)
        self.assertEqual(candidate.status, "PROPOSED")
        self.assertTrue(candidate.requires_human_review)
        self.assertFalse(candidate.runtime_influence)
        self.assertEqual(candidate.confidence, 0.0)
        self.assertIsNone(candidate.reviewed_by)
        self.assertIsNone(candidate.review_notes)
        self.assertIsNone(candidate.materialization_reference)

    def test_confidence_validation(self) -> None:
        self.assertEqual(self.make_candidate(confidence=0.0).confidence, 0.0)
        self.assertEqual(self.make_candidate(confidence=0.95).confidence, 0.95)

        for confidence in (-0.01, 0.96, 1.0):
            with self.subTest(confidence=confidence):
                with self.assertRaises(ValueError):
                    self.make_candidate(confidence=confidence)

    def test_collection_and_semantic_context_validation(self) -> None:
        with self.assertRaises(ValueError):
            self.make_candidate(source_evidence={"not": "a list"})
        with self.assertRaises(ValueError):
            self.make_candidate(structured_sources={"not": "a list"})
        with self.assertRaises(ValueError):
            self.make_candidate(semantic_context=["not", "a", "dict"])
        with self.assertRaises(ValueError):
            self.make_candidate(title="")
        with self.assertRaises(ValueError):
            self.make_candidate(description="")
        with self.assertRaises(ValueError):
            self.make_candidate(rationale="")

    def test_runtime_influence_safety(self) -> None:
        module = model_module()

        with self.assertRaises(ValueError):
            self.make_candidate(runtime_influence=True)

        for status in (
            "APPROVED_FOR_IMPLEMENTATION",
            "IMPLEMENTED",
            "VALIDATED",
            "CLOSED",
        ):
            transitioned = module.transition_candidate_status(
                self.make_candidate(),
                status,
                actor="reviewer@example.com",
                review_notes=f"Move to {status}.",
            )
            self.assertEqual(transitioned.status, status)
            self.assertFalse(transitioned.runtime_influence)
            self.assertTrue(transitioned.requires_human_review)

    def test_serialization(self) -> None:
        module = model_module()
        candidate = self.make_candidate(
            source_evidence=[{"source_type": "unknown_signal", "source_id": "u1"}],
            structured_sources=[{"source_type": "outcome_pattern", "pattern_id": "p1"}],
            semantic_context={"summary": "Reviewer assist only."},
            reviewed_by="reviewer@example.com",
        )

        data = candidate.to_dict()

        self.assertEqual(tuple(data.keys()), module.CANDIDATE_FIELDS)
        self.assertEqual(module.to_dict(candidate), data)
        self.assertEqual(module.from_dict(data), candidate)
        self.assertEqual(module.LearningCandidate.from_dict(data), candidate)
        self.assertEqual(module.candidates_to_dicts([candidate, candidate]), [data, data])

        data["source_evidence"][0]["source_id"] = "mutated"
        self.assertEqual(candidate.source_evidence[0]["source_id"], "u1")

    def test_deterministic_id(self) -> None:
        module = model_module()
        source_evidence = [{"source_type": "unknown_signal", "source_id": "u1"}]

        first = module.create_candidate_id(
            "parser_mapping_candidate",
            "Repeated unknown signal",
            affected_component="parser",
            source_evidence=source_evidence,
            pattern_id="PATTERN-1",
        )
        second = module.create_candidate_id(
            "parser_mapping_candidate",
            "Repeated unknown signal",
            affected_component="parser",
            source_evidence=deepcopy(source_evidence),
            pattern_id="PATTERN-1",
        )
        different_title = module.create_candidate_id(
            "parser_mapping_candidate",
            "Different unknown signal",
            affected_component="parser",
            source_evidence=source_evidence,
            pattern_id="PATTERN-1",
        )
        different_type = module.create_candidate_id(
            "documentation_candidate",
            "Repeated unknown signal",
            affected_component="parser",
            source_evidence=source_evidence,
            pattern_id="PATTERN-1",
        )
        different_source = module.create_candidate_id(
            "parser_mapping_candidate",
            "Repeated unknown signal",
            affected_component="parser",
            source_evidence=[{"source_type": "unknown_signal", "source_id": "u2"}],
            pattern_id="PATTERN-1",
        )

        self.assertEqual(first, second)
        self.assertNotEqual(first, different_title)
        self.assertNotEqual(first, different_type)
        self.assertNotEqual(first, different_source)
        self.assertTrue(first.startswith("CANDIDATE-PARSER-MAPPING-CANDIDATE-"))
        self.assertIsNone(re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-", first))

    def test_pattern_conversion(self) -> None:
        module = model_module()
        pattern = MockOutcomePattern()
        original_source_records = deepcopy(pattern.source_records)

        candidate = module.candidate_from_pattern(pattern)

        self.assertIsInstance(candidate, module.LearningCandidate)
        self.assertEqual(candidate.candidate_type, "parser_mapping_candidate")
        self.assertEqual(candidate.source_evidence, original_source_records)
        self.assertEqual(candidate.structured_sources[0]["source_type"], "outcome_pattern")
        self.assertEqual(candidate.structured_sources[0]["pattern_id"], pattern.pattern_id)
        self.assertEqual(
            candidate.structured_sources[0]["source_records"],
            original_source_records,
        )
        self.assertFalse(candidate.runtime_influence)
        self.assertTrue(candidate.requires_human_review)
        self.assertEqual(candidate.status, "PROPOSED")
        self.assertEqual(pattern.source_records, original_source_records)

        explicit = module.candidate_from_pattern(pattern, candidate_type="documentation_candidate")
        self.assertEqual(explicit.candidate_type, "documentation_candidate")

        missing_type = MockOutcomePattern(suggested_candidate_type=None)
        with self.assertRaises(ValueError):
            module.candidate_from_pattern(missing_type)

    def test_status_transition(self) -> None:
        module = model_module()
        candidate = self.make_candidate()

        for status in module.STATUSES_REQUIRING_ACTOR:
            with self.subTest(status=status):
                with self.assertRaises(ValueError):
                    module.transition_candidate_status(candidate, status)

        with self.assertRaises(ValueError):
            module.transition_candidate_status(candidate, "ACTIVATED", actor="reviewer@example.com")

        transitioned = module.transition_candidate_status(
            candidate,
            "UNDER_REVIEW",
            actor="reviewer@example.com",
            review_notes="Ready for model-level review.",
        )

        self.assertEqual(candidate.status, "PROPOSED")
        self.assertEqual(transitioned.status, "UNDER_REVIEW")
        self.assertEqual(transitioned.reviewed_by, "reviewer@example.com")
        self.assertEqual(transitioned.review_notes, "Ready for model-level review.")
        self.assertFalse(transitioned.runtime_influence)
        self.assertTrue(transitioned.requires_human_review)

    def test_materialization_reference(self) -> None:
        module = model_module()
        candidate = self.make_candidate(status="APPROVED_FOR_IMPLEMENTATION")

        with self.assertRaises(ValueError):
            module.attach_materialization_reference(candidate, "PR-123")
        with self.assertRaises(ValueError):
            module.attach_materialization_reference(candidate, "", actor="reviewer@example.com")

        attached = module.attach_materialization_reference(
            candidate,
            "PR-123",
            actor="reviewer@example.com",
            review_notes="Implementation reference attached for audit only.",
        )

        self.assertEqual(attached.materialization_reference, "PR-123")
        self.assertEqual(attached.status, "APPROVED_FOR_IMPLEMENTATION")
        self.assertFalse(attached.runtime_influence)
        self.assertTrue(attached.requires_human_review)
        self.assertIsNone(candidate.materialization_reference)

    def test_no_input_mutation(self) -> None:
        module = model_module()
        pattern = MockOutcomePattern()
        pattern_before = deepcopy(pattern)

        candidate = module.candidate_from_pattern(pattern)
        transitioned = module.transition_candidate_status(
            candidate,
            "NEEDS_REVISION",
            actor="reviewer@example.com",
            review_notes="Needs clearer rationale.",
        )

        self.assertEqual(pattern, pattern_before)
        self.assertEqual(candidate.status, "PROPOSED")
        self.assertEqual(candidate.reviewed_by, None)
        self.assertEqual(transitioned.status, "NEEDS_REVISION")

    def test_no_autonomous_function_names_exist(self) -> None:
        text = read_text(MODEL_PATH).lower()
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

    def test_runtime_import_isolation(self) -> None:
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
            self.assert_no_learning_imports(path)

    def test_documentation_exists_and_contains_required_boundaries(self) -> None:
        path = DOCS / "phase7_learning_candidate_model.md"

        self.assertTrue(path.is_file())
        text = read_text(path).lower()
        for phrase in (
            "candidate model is not a candidate generation engine",
            "proposals only",
            "runtime_influence=false",
            "requires_human_review=true",
            "semantic_context is optional and non-authoritative",
            "candidate generation remains future phase 7d",
            "governance bridge remains future phase 7f",
            "dashboard interactivity remains future phase 7h",
        ):
            self.assertIn(phrase, text)

    def make_candidate(self, **overrides):
        module = model_module()
        data = {
            "candidate_id": "CANDIDATE-PARSER-MAPPING-CANDIDATE-TEST",
            "candidate_type": "parser_mapping_candidate",
            "title": "Review repeated unknown parser signal",
            "description": "A repeated unknown parser signal should be reviewed by a human.",
            "source_evidence": [],
            "structured_sources": [],
            "semantic_context": None,
            "affected_component": "parser",
            "affected_domain": None,
            "confidence": 0.0,
            "rationale": "Repeated governed records justify a proposal for human review.",
            "requires_human_review": True,
            "runtime_influence": False,
            "status": "PROPOSED",
            "created_at": None,
            "created_by": None,
            "reviewed_by": None,
            "review_notes": None,
            "materialization_reference": None,
        }
        data.update(overrides)
        return module.LearningCandidate(**data)

    def assert_no_learning_imports(self, path: Path) -> None:
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
