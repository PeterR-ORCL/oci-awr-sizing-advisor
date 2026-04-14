from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class AwrDecision:
    awr_id: int
    overall_status: str
    primary_issue: str
    secondary_issues: list[str]
    severity_score: float
    confidence: float
    evidence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
