from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel


class Recommendation(BaseModel):
    issue_type: str
    severity: str
    recommendation: str
    rationale: str
    actions: List[str]
    evidence: Dict[str, Any]
