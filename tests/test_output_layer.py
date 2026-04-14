from __future__ import annotations

import json
from datetime import datetime, timezone
import unittest

from src.analysis.output_layer import build_analysis_output, render_analysis_cli, render_analysis_json
from src.models.decision import AwrDecision
from src.models.recommendation import ActionRecommendation


class OutputLayerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generated_at = datetime(2026, 4, 13, 15, 30, 0, tzinfo=timezone.utc)

    def _decision(
        self,
        secondary_issues: list[str] | None = None,
    ) -> AwrDecision:
        return AwrDecision(
            awr_id=501,
            overall_status="CRITICAL",
            primary_issue="CPU",
            secondary_issues=secondary_issues or [],
            severity_score=78.5,
            confidence=0.87,
            evidence={"domain_scores": {"CPU": 0.91}},
        )

    def _recommendations(self) -> list[ActionRecommendation]:
        return [
            ActionRecommendation(
                priority=1,
                issue="CPU",
                action="Investigate Top SQL",
                impact="HIGH",
                confidence=0.87,
                evidence={},
            ),
            ActionRecommendation(
                priority=2,
                issue="IO",
                action="Analyze storage / read latency",
                impact="HIGH",
                confidence=0.82,
                evidence={},
            ),
        ]

    def test_json_structure_correctness(self) -> None:
        payload = build_analysis_output(
            decision=self._decision(["IO"]),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )

        self.assertEqual(payload["awr_id"], 501)
        self.assertIn("decision", payload)
        self.assertIn("recommendations", payload)
        self.assertIn("metadata", payload)
        self.assertEqual(payload["decision"]["primary_issue"], "CPU")
        self.assertEqual(payload["recommendations"][0]["priority"], 1)

    def test_cli_rendering_with_primary_issue_only(self) -> None:
        rendered = render_analysis_cli(
            decision=self._decision(),
            recommendations=self._recommendations()[:1],
        )

        self.assertIn("AWR ANALYSIS RESULT", rendered)
        self.assertIn("PRIMARY ISSUE: CPU", rendered)
        self.assertNotIn("SECONDARY ISSUES:", rendered)
        self.assertIn("1. Investigate Top SQL", rendered)

    def test_cli_rendering_with_secondary_issues(self) -> None:
        rendered = render_analysis_cli(
            decision=self._decision(["IO", "MEMORY"]),
            recommendations=self._recommendations(),
        )

        self.assertIn("SECONDARY ISSUES: IO, MEMORY", rendered)

    def test_empty_secondary_issues_handled_cleanly(self) -> None:
        rendered = render_analysis_cli(
            decision=self._decision([]),
            recommendations=self._recommendations()[:1],
        )

        self.assertNotIn("SECONDARY ISSUES:", rendered)
        self.assertIn("SEVERITY SCORE: 78.50", rendered)

    def test_recommendation_list_rendering_in_deterministic_order(self) -> None:
        rendered = render_analysis_cli(
            decision=self._decision(["IO"]),
            recommendations=self._recommendations(),
        )

        self.assertLess(
            rendered.index("1. Investigate Top SQL"),
            rendered.index("2. Analyze storage / read latency"),
        )

    def test_metadata_presence_in_json_output(self) -> None:
        rendered = render_analysis_json(
            decision=self._decision(["IO"]),
            recommendations=self._recommendations(),
            generated_at=self.generated_at,
        )
        payload = json.loads(rendered)

        self.assertEqual(payload["metadata"]["generated_at"], "2026-04-13T15:30:00Z")
        self.assertEqual(payload["metadata"]["output_version"], "phase4.1")
        self.assertEqual(payload["metadata"]["source"], "phase4")


if __name__ == "__main__":
    unittest.main()
