from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scripts import record_action as record_action_cli
from src.memory import memory_orchestrator


class ActionTrackingTests(unittest.TestCase):
    def test_memory_disabled_does_not_call_insert(self) -> None:
        with patch.dict(os.environ, {"AWR_MEMORY_ENABLED": "false"}, clear=False):
            with patch.object(
                memory_orchestrator.memory_agent,
                "insert_action_history",
            ) as insert_action:
                result = memory_orchestrator.record_action(
                    run_history_id=1,
                    action_type="SQL_TUNING",
                    action_summary="Reviewed SQL access path.",
                )

        insert_action.assert_not_called()
        self.assertFalse(result["enabled"])
        self.assertTrue(result["success"])
        self.assertEqual(result["skipped"], ["memory_disabled"])

    def test_missing_run_history_id_fails_validation(self) -> None:
        with patch.dict(os.environ, {"AWR_MEMORY_ENABLED": "true"}, clear=False):
            result = memory_orchestrator.record_action(
                run_history_id=0,
                action_type="SQL_TUNING",
                action_summary="Reviewed SQL access path.",
            )

        self.assertFalse(result["success"])
        self.assertIn("run_history_id is required", result["errors"][0])

    def test_missing_action_type_fails_validation(self) -> None:
        with patch.dict(os.environ, {"AWR_MEMORY_ENABLED": "true"}, clear=False):
            result = memory_orchestrator.record_action(
                run_history_id=1,
                action_type="",
                action_summary="Reviewed SQL access path.",
            )

        self.assertFalse(result["success"])
        self.assertIn("action_type is required", result["errors"])

    def test_missing_action_summary_fails_validation(self) -> None:
        with patch.dict(os.environ, {"AWR_MEMORY_ENABLED": "true"}, clear=False):
            result = memory_orchestrator.record_action(
                run_history_id=1,
                action_type="SQL_TUNING",
                action_summary="",
            )

        self.assertFalse(result["success"])
        self.assertIn("action_summary is required", result["errors"])

    def test_successful_record_action_returns_action_history_id(self) -> None:
        with patch.dict(os.environ, {"AWR_MEMORY_ENABLED": "true"}, clear=False):
            with patch.object(
                memory_orchestrator.memory_agent,
                "insert_action_history",
                return_value=99,
            ) as insert_action:
                result = memory_orchestrator.record_action(
                    run_history_id=1,
                    action_type="sql tuning",
                    action_status="completed",
                    action_summary="Reviewed SQL access path.",
                    actor="tester",
                    notes="manual review",
                )

        self.assertTrue(result["success"])
        self.assertEqual(result["action_history_id"], 99)
        self.assertEqual(result["action_type"], "SQL_TUNING")
        self.assertEqual(result["action_status"], "COMPLETED")
        insert_action.assert_called_once()

    def test_insert_exception_returns_failure_without_raising(self) -> None:
        with patch.dict(os.environ, {"AWR_MEMORY_ENABLED": "true"}, clear=False):
            with patch.object(
                memory_orchestrator.memory_agent,
                "insert_action_history",
                side_effect=RuntimeError("insert failed"),
            ):
                result = memory_orchestrator.record_action(
                    run_history_id=1,
                    action_type="SQL_TUNING",
                    action_summary="Reviewed SQL access path.",
                )

        self.assertFalse(result["success"])
        self.assertIn("RuntimeError: insert failed", result["errors"])

    def test_cli_argument_parsing_handles_required_fields(self) -> None:
        parser = record_action_cli.build_parser()
        args = parser.parse_args(
            [
                "--run-history-id",
                "1",
                "--action-type",
                "INVESTIGATION_ONLY",
                "--action-summary",
                "Validated advisor output.",
            ]
        )

        self.assertEqual(args.run_history_id, 1)
        self.assertEqual(args.action_type, "INVESTIGATION_ONLY")
        self.assertEqual(args.action_summary, "Validated advisor output.")


if __name__ == "__main__":
    unittest.main()
