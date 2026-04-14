from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.models.decision import AwrDecision
from src.models.recommendation import ActionRecommendation

OUTPUT_VERSION = "phase4.1"
OUTPUT_SOURCE = "phase4"
CLI_DIVIDER = "=" * 48


def build_analysis_output(
    decision: AwrDecision,
    recommendations: list[ActionRecommendation],
    generated_at: datetime | None = None,
    output_version: str = OUTPUT_VERSION,
    source: str = OUTPUT_SOURCE,
) -> dict[str, Any]:
    """Build the machine-readable final analysis payload."""

    timestamp = _format_timestamp(generated_at or datetime.now(timezone.utc))
    return {
        "awr_id": decision.awr_id,
        "decision": decision.to_dict(),
        "recommendations": [
            recommendation.to_dict() for recommendation in recommendations
        ],
        "metadata": {
            "generated_at": timestamp,
            "output_version": output_version,
            "source": source,
        },
    }


def render_analysis_json(
    decision: AwrDecision,
    recommendations: list[ActionRecommendation],
    generated_at: datetime | None = None,
    output_version: str = OUTPUT_VERSION,
    source: str = OUTPUT_SOURCE,
) -> str:
    """Render the final analysis payload as formatted JSON."""

    payload = build_analysis_output(
        decision=decision,
        recommendations=recommendations,
        generated_at=generated_at,
        output_version=output_version,
        source=source,
    )
    return json.dumps(payload, indent=2, sort_keys=False)


def render_analysis_cli(
    decision: AwrDecision,
    recommendations: list[ActionRecommendation],
) -> str:
    """Render the final deterministic analysis in a human-readable CLI format."""

    lines = [
        CLI_DIVIDER,
        "AWR ANALYSIS RESULT",
        CLI_DIVIDER,
        f"AWR ID: {decision.awr_id}",
        "",
        f"STATUS: {decision.overall_status}",
        f"PRIMARY ISSUE: {decision.primary_issue}",
    ]
    if decision.secondary_issues:
        lines.append(
            "SECONDARY ISSUES: " + ", ".join(decision.secondary_issues)
        )
    lines.extend(
        [
            f"SEVERITY SCORE: {decision.severity_score:.2f}",
            f"CONFIDENCE: {decision.confidence:.2f}",
            "",
            "TOP RECOMMENDATIONS:",
        ]
    )
    for recommendation in recommendations:
        lines.append(f"{recommendation.priority}. {recommendation.action}")
    lines.append("")
    lines.append(CLI_DIVIDER)
    return "\n".join(lines)


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value_utc = value.astimezone(timezone.utc)
    return value_utc.isoformat(timespec="seconds").replace("+00:00", "Z")
