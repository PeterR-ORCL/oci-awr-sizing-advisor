from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import scripts.awr_memory_cli as cli


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def run_cli(argv: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = cli.main(argv)
    return code, stdout.getvalue(), stderr.getvalue()


def write_json(directory: Path, name: str, data: object) -> Path:
    path = directory / name
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


class LearningCliMLVisibilityTests(unittest.TestCase):
    def test_learning_help_includes_ml_visibility_commands(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                cli.main(["learning", "--help"])
        self.assertEqual(raised.exception.code, 0)
        help_text = stdout.getvalue()
        for command in (
            "ml-status",
            "ml-explain",
            "ml-models",
            "adaptive-runtime-status",
        ):
            with self.subTest(command=command):
                self.assertIn(command, help_text)

    def test_learning_ml_status_is_read_only(self) -> None:
        code, stdout, _ = run_cli(["learning", "ml-status"])

        self.assertEqual(code, 0)
        self.assertIn("read-only", stdout)
        self.assertIn("deterministic runtime remains authoritative", stdout)
        self.assertIn("no runtime activation", stdout)
        self.assertIn("runtime_active=false", stdout)

    def test_learning_ml_explain_empty_and_json_input(self) -> None:
        code, stdout, _ = run_cli(["learning", "ml-explain", "--json"])
        self.assertEqual(code, 0)
        empty_payload = json.loads(stdout)
        self.assertEqual(empty_payload["count"], 0)
        self.assertTrue(empty_payload["read_only"])
        self.assertTrue(empty_payload["no_runtime_activation"])

        with tempfile.TemporaryDirectory() as tempdir:
            input_path = write_json(
                Path(tempdir),
                "explanations.json",
                {
                    "explanations": [
                        {
                            "explanation_id": "EXP-CLI",
                            "model_id": "MODEL-CLI",
                            "summary": "Shadow explanation",
                            "feature_contributions": [
                                {"feature": "db_time_pct", "contribution": 0.25}
                            ],
                        }
                    ]
                },
            )
            before = read_text(input_path)
            code, stdout, _ = run_cli(
                ["learning", "ml-explain", "--input", str(input_path), "--json"]
            )
            after = read_text(input_path)

        self.assertEqual(code, 0)
        self.assertEqual(before, after)
        payload = json.loads(stdout)
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["explanations"][0]["explanation_id"], "EXP-CLI")
        self.assertFalse(payload["runtime_influence"])
        self.assertTrue(payload["deterministic_runtime_remains_authoritative"])

    def test_learning_ml_models_empty_and_json_input(self) -> None:
        code, stdout, _ = run_cli(["learning", "ml-models", "--json"])
        self.assertEqual(code, 0)
        empty_payload = json.loads(stdout)
        self.assertEqual(empty_payload["count"], 0)
        self.assertFalse(empty_payload["runtime_active"])
        self.assertFalse(empty_payload["runtime_eligibility_granted"])

        with tempfile.TemporaryDirectory() as tempdir:
            input_path = write_json(
                Path(tempdir),
                "models.json",
                {
                    "model_registry_entries": [
                        {
                            "model_id": "MODEL-CLI",
                            "model_family": "shadow",
                            "governance_status": "REGISTERED",
                            "shadow_eligible": True,
                            "runtime_eligibility_requested": True,
                            "runtime_active": True,
                            "runtime_eligibility_granted": True,
                        }
                    ]
                },
            )
            before = read_text(input_path)
            code, stdout, _ = run_cli(
                ["learning", "ml-models", "--input", str(input_path), "--json"]
            )
            after = read_text(input_path)

        self.assertEqual(code, 0)
        self.assertEqual(before, after)
        payload = json.loads(stdout)
        model = payload["models"][0]
        self.assertEqual(model["model_id"], "MODEL-CLI")
        self.assertFalse(model["runtime_active"])
        self.assertFalse(model["runtime_eligibility_granted"])
        self.assertFalse(model["runtime_influence_granted"])

    def test_learning_adaptive_runtime_status_empty_and_json_input(self) -> None:
        code, stdout, _ = run_cli(["learning", "adaptive-runtime-status", "--json"])
        self.assertEqual(code, 0)
        empty_payload = json.loads(stdout)
        self.assertFalse(empty_payload["runtime_active"])
        self.assertFalse(empty_payload["runtime_influence_granted"])
        self.assertTrue(empty_payload["fallback_to_deterministic"])

        with tempfile.TemporaryDirectory() as tempdir:
            input_path = write_json(
                Path(tempdir),
                "runtime.json",
                {
                    "runtime_context": {"context_id": "CTX-1", "runtime_mode": "shadow_only"},
                    "gate_results": [
                        {
                            "gate_id": "GATE-1",
                            "component_type": "scoring",
                            "allowed": True,
                            "runtime_active": False,
                        }
                    ],
                    "fallback_decision": {
                        "decision_id": "FB-1",
                        "final_runtime_posture": "adaptive_consideration_ready",
                        "rollback_available": True,
                    },
                },
            )
            code, stdout, _ = run_cli(
                ["learning", "adaptive-runtime-status", "--input", str(input_path), "--json"]
            )

        self.assertEqual(code, 0)
        payload = json.loads(stdout)
        self.assertEqual(payload["gate_results"][0]["gate_id"], "GATE-1")
        self.assertEqual(
            payload["fallback_decisions"][0]["final_runtime_posture"],
            "adaptive_consideration_ready",
        )
        self.assertFalse(payload["runtime_active"])
        self.assertTrue(payload["no_runtime_activation"])

    def test_commands_report_no_unsafe_dependencies(self) -> None:
        for command in ("ml-status", "ml-explain", "ml-models", "adaptive-runtime-status"):
            with self.subTest(command=command):
                code, stdout, _ = run_cli(["learning", command, "--json"])
                self.assertEqual(code, 0)
                payload = json.loads(stdout)
                self.assertFalse(payload["network_dependency"])
                self.assertFalse(payload["oracle_agent_memory_dependency"])
                self.assertFalse(payload["database_dependency"])

    def test_no_write_or_mutation_commands_added(self) -> None:
        source = read_text(ROOT / "scripts" / "awr_memory_cli.py")
        for forbidden in (
            "ml-approve",
            "ml-reject",
            "ml-activate",
            "ml-apply",
            "adaptive-runtime-activate",
            "adaptive-runtime-rollback",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)
        for argv in (
            ["learning", "ml-explain", "--help"],
            ["learning", "ml-models", "--help"],
            ["learning", "adaptive-runtime-status", "--help"],
        ):
            stdout = io.StringIO()
            stderr = io.StringIO()
            with self.assertRaises(SystemExit) as raised:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    cli.main(argv)
            self.assertEqual(raised.exception.code, 0)
            self.assertNotIn("--output", stdout.getvalue())

    def test_cli_docs_exist_and_contain_boundary_phrases(self) -> None:
        doc_path = DOCS / "phase7ab_cli_ml_visibility.md"
        self.assertTrue(doc_path.is_file(), doc_path)
        text = read_text(doc_path).lower()
        for phrase in (
            "cli visibility is read-only",
            "commands do not write",
            "commands do not activate runtime",
            "commands do not change registry/governance state",
            "commands do not call live services",
            "local/deterministic",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
