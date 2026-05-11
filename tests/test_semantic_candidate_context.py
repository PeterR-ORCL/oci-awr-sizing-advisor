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
CONTEXT_PATH = ROOT / "src" / "learning" / "semantic_candidate_context.py"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def context_module():
    return importlib.import_module("src.learning.semantic_candidate_context")


def model_module():
    return importlib.import_module("src.learning.learning_candidate_model")


class SemanticCandidateContextTests(unittest.TestCase):
    def test_01_import_safety(self) -> None:
        before_environment = dict(os.environ)

        module = context_module()

        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(module, "SemanticCandidateContext"))
        self.assertTrue(hasattr(module, "SemanticCandidateContextBuilder"))
        self.assertTrue(hasattr(module, "attach_semantic_context"))

    def test_empty_input_returns_no_context_and_preserves_candidate(self) -> None:
        module = context_module()
        candidate = self.make_candidate()
        original = candidate.to_dict()

        context = module.build_semantic_candidate_context(candidate, [])
        attached = module.attach_semantic_context(candidate, [])

        self.assertIsNone(context)
        self.assertEqual(candidate.to_dict(), original)
        self.assertIsNot(attached, candidate)
        self.assertIsNone(attached.semantic_context)
        self.assertEqual(attached.source_evidence, candidate.source_evidence)
        self.assertEqual(attached.structured_sources, candidate.structured_sources)
        self.assertEqual(attached.confidence, candidate.confidence)
        self.assertEqual(attached.status, candidate.status)
        self.assertEqual(attached.candidate_type, candidate.candidate_type)
        self.assertTrue(attached.requires_human_review)
        self.assertFalse(attached.runtime_influence)

    def test_context_matching_uses_allowed_deterministic_signals(self) -> None:
        module = context_module()
        candidate = self.make_candidate()

        context = module.build_semantic_candidate_context(
            candidate,
            self.semantic_records(candidate),
        )

        self.assertIsNotNone(context)
        matched_ids = [record["record_id"] for record in context.semantic_records]

        self.assertIn("case-exact", matched_ids)
        self.assertIn("case-type", matched_ids)
        self.assertIn("artifact-component", matched_ids)
        self.assertIn("feedback-domain", matched_ids)
        self.assertIn("unknown-title", matched_ids)
        self.assertIn("case-source", matched_ids)
        self.assertNotIn("unrelated", matched_ids)

        self.assertEqual(
            {record["record_id"] for record in context.related_cases},
            {"case-exact", "case-type", "case-source"},
        )
        self.assertEqual(
            {record["record_id"] for record in context.related_unknown_signals},
            {"unknown-title"},
        )
        self.assertEqual(
            {record["record_id"] for record in context.related_feedback},
            {"feedback-domain"},
        )
        self.assertEqual(
            {record["record_id"] for record in context.related_artifacts},
            {"artifact-component"},
        )

    def test_context_safety_fields(self) -> None:
        module = context_module()
        candidate = self.make_candidate()

        context = module.build_semantic_candidate_context(
            candidate,
            self.semantic_records(candidate),
        )

        self.assertTrue(context.reviewer_assist)
        self.assertTrue(context.non_authoritative)
        self.assertFalse(context.runtime_influence)
        self.assertIn("Reviewer-assist semantic context only", context.summary)
        self.assertIn("runtime_influence=false", context.summary)

    def test_attachment_safety(self) -> None:
        module = context_module()
        candidate = self.make_candidate(status="UNDER_REVIEW", reviewed_by="reviewer@example.com")
        original_source_evidence = deepcopy(candidate.source_evidence)
        original_structured_sources = deepcopy(candidate.structured_sources)

        attached = module.attach_semantic_context(candidate, self.semantic_records(candidate))

        self.assertIsNot(attached, candidate)
        self.assertIsNotNone(attached.semantic_context)
        self.assertNotIn("semantic_context", repr(attached.source_evidence))
        self.assertEqual(attached.source_evidence, original_source_evidence)
        self.assertEqual(attached.structured_sources, original_structured_sources)
        self.assertEqual(attached.confidence, candidate.confidence)
        self.assertEqual(attached.status, "UNDER_REVIEW")
        self.assertEqual(attached.candidate_type, candidate.candidate_type)
        self.assertEqual(attached.candidate_id, candidate.candidate_id)
        self.assertTrue(attached.requires_human_review)
        self.assertFalse(attached.runtime_influence)
        self.assertEqual(attached.reviewed_by, "reviewer@example.com")
        self.assertEqual(attached.materialization_reference, candidate.materialization_reference)

        semantic_context = attached.semantic_context
        self.assertTrue(semantic_context["reviewer_assist"])
        self.assertTrue(semantic_context["non_authoritative"])
        self.assertFalse(semantic_context["runtime_influence"])

    def test_deterministic_output_and_stable_order(self) -> None:
        module = context_module()
        candidate = self.make_candidate()
        records = self.semantic_records(candidate)

        first = module.semantic_context_to_dict(
            module.build_semantic_candidate_context(candidate, records)
        )
        second = module.semantic_context_to_dict(
            module.build_semantic_candidate_context(candidate, deepcopy(records))
        )
        reversed_input = module.semantic_context_to_dict(
            module.build_semantic_candidate_context(candidate, list(reversed(records)))
        )

        self.assertEqual(first, second)
        self.assertEqual(first, reversed_input)
        self.assertEqual(first["context_id"], second["context_id"])
        self.assertTrue(first["context_id"].startswith(f"SEMCTX-{candidate.candidate_id}-"))
        self.assertIsNone(re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-", first["context_id"]))
        self.assertEqual(
            [record["record_id"] for record in first["semantic_records"]],
            [record["record_id"] for record in second["semantic_records"]],
        )

    def test_serialization_round_trip(self) -> None:
        module = context_module()
        candidate = self.make_candidate()
        context = module.build_semantic_candidate_context(candidate, self.semantic_records(candidate))

        data = module.semantic_context_to_dict(context)
        reconstructed = module.semantic_context_from_dict(data)

        self.assertEqual(tuple(data.keys()), module.CONTEXT_FIELDS)
        self.assertEqual(module.semantic_context_to_dict(reconstructed), data)
        self.assertEqual(reconstructed, context)

    def test_no_input_mutation(self) -> None:
        module = context_module()
        candidate = self.make_candidate()
        original_candidate = candidate.to_dict()
        records = self.semantic_records(candidate)
        original_records = deepcopy(records)

        module.build_semantic_candidate_context(candidate, records)
        module.attach_semantic_context(candidate, records)

        self.assertEqual(candidate.to_dict(), original_candidate)
        self.assertEqual(records, original_records)

    def test_no_live_dependency(self) -> None:
        tree = ast.parse(read_text(CONTEXT_PATH), filename=str(CONTEXT_PATH))
        imported_modules: list[str] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.append(node.module or "")

        for module_name in imported_modules:
            self.assertFalse(module_name.startswith("oracle_agent_memory"))
            self.assertFalse(module_name.startswith("oci"))
            self.assertFalse(module_name.startswith("requests"))
            self.assertFalse(module_name.startswith("socket"))
            self.assertFalse(module_name.startswith("urllib"))
            self.assertFalse(module_name.startswith("sqlite3"))

        text = read_text(CONTEXT_PATH)
        self.assertNotIn("os.environ", text)
        self.assertNotIn("LLM", text)

    def test_no_forbidden_autonomous_function_names(self) -> None:
        text = read_text(CONTEXT_PATH).lower()
        for name in (
            "auto_apply",
            "autonomous_apply",
            "self_modify",
            "mutate_runtime",
            "update_parser_automatically",
            "update_scoring_automatically",
            "update_recommendations_automatically",
        ):
            self.assertNotIn(name, text)

    def test_runtime_import_isolation(self) -> None:
        self.assert_no_learning_imports(ROOT / "scripts" / "run_analysis.py")
        runtime_paths = [
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

        self.assertTrue(checked_files, "expected runtime files to inspect")
        for path in checked_files:
            self.assert_no_learning_imports(path)

    def test_documentation_exists_and_contains_required_boundary_phrases(self) -> None:
        doc_path = DOCS / "phase7_semantic_candidate_context.md"
        self.assertTrue(doc_path.is_file())
        text = read_text(doc_path).lower()

        for phrase in (
            "reviewer-assist only",
            "optional",
            "non-authoritative",
            "runtime_influence=false",
            "can explain but cannot decide",
            "is not source_evidence",
            "must not change confidence",
            "must not change status",
            "must not approve/reject candidates",
            "no live oracle agent memory dependency",
            "governance bridge remains future phase 7f",
            "dashboard learning visibility remains future phase 7g",
            "dashboard interactivity remains future phase 7h",
        ):
            self.assertIn(phrase, text)

    def make_candidate(
        self,
        status: str = "PROPOSED",
        reviewed_by: str | None = None,
    ):
        model = model_module()
        return model.LearningCandidate(
            candidate_id="CANDIDATE-PARSER-MAPPING-CANDIDATE-SEMCTX",
            candidate_type="parser_mapping_candidate",
            title="Review repeated SQL PX unknown signal",
            description="Review repeated parser unknown signal in SQL sections.",
            source_evidence=[
                {
                    "source_type": "unknown_signal",
                    "source_id": "unknown-1",
                    "normalized_key": "sql_px",
                }
            ],
            structured_sources=[
                {
                    "source_type": "outcome_pattern",
                    "pattern_id": "PATTERN-SQL-PX",
                    "source_records": [
                        {
                            "source_type": "unknown_signal",
                            "source_id": "unknown-1",
                        }
                    ],
                }
            ],
            affected_component="parser",
            affected_domain="SQL",
            confidence=0.72,
            rationale="Repeated unknown SQL PX signal requires human review.",
            requires_human_review=True,
            runtime_influence=False,
            status=status,
            reviewed_by=reviewed_by,
        )

    def semantic_records(self, candidate) -> list[dict[str, object]]:
        return [
            {
                "record_id": "case-exact",
                "source_type": "case",
                "candidate_id": candidate.candidate_id,
                "summary": "Prior reviewer case for the same learning candidate.",
            },
            {
                "record_id": "case-type",
                "source_type": "case",
                "candidate_type": "parser_mapping_candidate",
                "summary": "Prior parser mapping candidate discussion.",
            },
            {
                "record_id": "artifact-component",
                "category": "knowledge_artifact",
                "component": "parser",
                "description": "Parser mapping notes for normalized unknown signals.",
            },
            {
                "record_id": "feedback-domain",
                "source_type": "feedback",
                "domain": "SQL",
                "text": "Reviewer feedback about SQL diagnostics wording.",
            },
            {
                "record_id": "unknown-title",
                "source_type": "unknown_signal",
                "text": "PX unknown signal appeared in another SQL report.",
            },
            {
                "record_id": "case-source",
                "source_type": "case",
                "source_id": "unknown-1",
                "summary": "Prior case references the same parser source record.",
            },
            {
                "record_id": "unrelated",
                "category": "artifact",
                "component": "dashboard",
                "domain": "visualization",
                "summary": "Dashboard color and layout notes.",
            },
        ]

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
