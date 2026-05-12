from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
README = DOCS / "README.md"

FINAL_DOCS = {
    "architecture": DOCS / "phase7_learning_architecture.md",
    "operational": DOCS / "phase7_operational_model.md",
    "inventory": DOCS / "phase7_component_inventory.md",
    "repository_map": DOCS / "phase7_repository_map.md",
    "release_notes": DOCS / "phase7_release_notes.md",
    "demo": DOCS / "phase7_demo_walkthrough.md",
    "acceptance": DOCS / "phase7_acceptance_criteria.md",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


class Phase7DocumentationFinalizationTests(unittest.TestCase):
    def test_required_final_docs_exist(self) -> None:
        for path in FINAL_DOCS.values():
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), path)

    def test_readme_links_final_docs(self) -> None:
        text = read_text(README)
        for title, filename in (
            ("Phase 7 Learning Architecture", "phase7_learning_architecture.md"),
            ("Phase 7 Operational Model", "phase7_operational_model.md"),
            ("Phase 7 Component Inventory", "phase7_component_inventory.md"),
            ("Phase 7 Repository Map", "phase7_repository_map.md"),
            ("Phase 7 Release Notes", "phase7_release_notes.md"),
            ("Phase 7 Demo Walkthrough", "phase7_demo_walkthrough.md"),
            ("Phase 7 Acceptance Criteria", "phase7_acceptance_criteria.md"),
        ):
            with self.subTest(title=title):
                self.assertIn(title, text)
                self.assertIn(filename, text)

    def test_architecture_doc_contains_required_boundary_phrases(self) -> None:
        text = read_text(FINAL_DOCS["architecture"]).lower()
        for phrase in (
            "deterministic runtime remains authoritative",
            "candidate-based",
            "human-governed",
            "semantic context is reviewer-assist only",
            "dashboard interactivity is read-only",
            "cli learning commands are local and actor-gated",
            "no runtime activation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_operational_doc_contains_required_commands(self) -> None:
        text = read_text(FINAL_DOCS["operational"])
        for command in (
            "scripts/run_phase7_validation.py",
            "scripts/run_phase7_validation.py --json",
            "scripts/run_phase7h_dashboard_validation.py",
            "scripts/awr_memory_cli.py learning validate --json",
        ):
            with self.subTest(command=command):
                self.assertIn(command, text)

    def test_component_inventory_references_key_modules(self) -> None:
        text = read_text(FINAL_DOCS["inventory"])
        for module in (
            "outcome_pattern_miner.py",
            "learning_candidate_model.py",
            "learning_candidate_engine.py",
            "semantic_candidate_context.py",
            "learning_governance_bridge.py",
            "html_dashboard.py",
            "awr_memory_cli.py",
            "run_phase7_validation.py",
        ):
            with self.subTest(module=module):
                self.assertIn(module, text)

    def test_repository_map_preserves_isolation_language(self) -> None:
        text = read_text(FINAL_DOCS["repository_map"])
        for phrase in (
            "parser/scoring/decision/recommendation runtime paths remain isolated",
            "run_analysis.py remains protected",
            "Phase 7 learning modules are not imported by runtime truth paths",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_release_notes_contain_safety_guarantees(self) -> None:
        text = read_text(FINAL_DOCS["release_notes"]).lower()
        for phrase in (
            "no runtime activation",
            "no autonomous parser/scoring/recommendation changes",
            "semantic context is non-authoritative",
            "dashboard interactivity is read-only",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_demo_walkthrough_contains_demo_commands_and_safety_talking_points(self) -> None:
        text = read_text(FINAL_DOCS["demo"])
        for phrase in (
            "python3 scripts/run_phase7_validation.py",
            "python3 scripts/awr_memory_cli.py learning status",
            "python3 scripts/awr_memory_cli.py learning patterns --input examples/phase7_memory_sample.json --json",
            "python3 scripts/awr_memory_cli.py learning candidates --input examples/phase7_patterns_sample.json --json",
            "python3 scripts/awr_memory_cli.py learning review --input examples/phase7_candidates_sample.json --candidate-id ... --action approve-for-implementation --actor reviewer@example.com --json",
            "Safety Talking Points",
            "Deterministic runtime remains authoritative",
            "Dashboard interactivity is read-only",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_acceptance_criteria_contains_required_validation_gates(self) -> None:
        text = read_text(FINAL_DOCS["acceptance"])
        for phrase in (
            "run_phase7_validation.py",
            "run_phase7h_dashboard_validation.py",
            "learning validate --json",
            "Phase 6 validation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_final_docs_do_not_claim_unsupported_behavior(self) -> None:
        combined = "\n".join(read_text(path).lower() for path in FINAL_DOCS.values())
        unsupported_positive_claims = (
            "autonomous learning is enabled",
            "enables autonomous learning",
            "supports autonomous learning",
            "automatic parser updates are enabled",
            "automatic scoring updates are enabled",
            "automatic recommendation updates are enabled",
            "runtime activation is enabled",
            "activates candidates at runtime",
            "updates parser automatically",
            "updates scoring automatically",
            "updates recommendations automatically",
        )
        for claim in unsupported_positive_claims:
            with self.subTest(claim=claim):
                self.assertNotIn(claim, combined)


if __name__ == "__main__":
    unittest.main()
