from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from src.memory import memory_orchestrator


def _phase4i_payload() -> dict:
    return {
        "metadata": {},
        "decision": {},
        "scores": {},
        "trends": {},
        "similarity_intelligence": {},
        "recommendations": [],
    }


class MemoryOrchestratorTests(unittest.TestCase):
    def test_memory_disabled_does_not_call_memory_agent(self) -> None:
        with patch.dict(os.environ, {"AWR_MEMORY_ENABLED": "false"}, clear=False):
            with patch.object(
                memory_orchestrator.memory_agent,
                "persist_analysis",
            ) as persist_analysis:
                result = memory_orchestrator.persist_run_memory(
                    _phase4i_payload(),
                    {},
                    None,
                )

        persist_analysis.assert_not_called()
        self.assertFalse(result["enabled"])
        self.assertTrue(result["success"])
        self.assertEqual(result["skipped"], ["memory_disabled"])

    def test_successful_persistence_returns_run_history_id(self) -> None:
        with patch.dict(os.environ, {"AWR_MEMORY_ENABLED": "true"}, clear=False):
            with patch.object(
                memory_orchestrator.memory_agent,
                "persist_analysis",
                return_value=42,
            ):
                result = memory_orchestrator.persist_run_memory(
                    _phase4i_payload(),
                    {"source_files": []},
                    None,
                )

        self.assertTrue(result["enabled"])
        self.assertTrue(result["success"])
        self.assertEqual(result["run_history_id"], 42)
        self.assertTrue(result["persisted"]["run_history"])
        self.assertTrue(result["persisted"]["recommendations"])
        self.assertTrue(result["persisted"]["unknown_signals"])

    def test_memory_agent_exception_returns_failure_without_raising(self) -> None:
        with patch.dict(os.environ, {"AWR_MEMORY_ENABLED": "true"}, clear=False):
            with patch.object(
                memory_orchestrator.memory_agent,
                "persist_analysis",
                side_effect=RuntimeError("database unavailable"),
            ):
                result = memory_orchestrator.persist_run_memory(
                    _phase4i_payload(),
                    {},
                    None,
                )

        self.assertTrue(result["enabled"])
        self.assertFalse(result["success"])
        self.assertIsNone(result["run_history_id"])
        self.assertIn("RuntimeError: database unavailable", result["errors"])

    def test_missing_phase4i_keys_warns_without_crashing(self) -> None:
        with patch.dict(os.environ, {"AWR_MEMORY_ENABLED": "true"}, clear=False):
            with patch.object(
                memory_orchestrator.memory_agent,
                "persist_analysis",
                return_value=7,
            ):
                result = memory_orchestrator.persist_run_memory(
                    {"metadata": {}},
                    {},
                    None,
                )

        self.assertTrue(result["success"])
        self.assertEqual(result["run_history_id"], 7)
        self.assertTrue(
            any("phase4i_output missing key: decision" == warning for warning in result["warnings"])
        )


if __name__ == "__main__":
    unittest.main()
