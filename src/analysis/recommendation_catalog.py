from __future__ import annotations

from dataclasses import dataclass

DOMAIN_ORDER = ("CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG")


@dataclass(frozen=True, slots=True)
class RecommendationTemplate:
    issue: str
    action: str
    impact: str
    impact_rank: int


RECOMMENDATION_TEMPLATES: dict[str, RecommendationTemplate] = {
    "CPU": RecommendationTemplate(
        issue="CPU",
        action=(
            "Investigate Top SQL driving CPU saturation and validate "
            "execution plans for the highest DB CPU consumers."
        ),
        impact="HIGH",
        impact_rank=6,
    ),
    "IO": RecommendationTemplate(
        issue="IO",
        action=(
            "Analyze storage and read-latency pressure, starting with the "
            "statements and objects generating the hottest physical I/O."
        ),
        impact="HIGH",
        impact_rank=5,
    ),
    "MEMORY": RecommendationTemplate(
        issue="MEMORY",
        action=(
            "Analyze memory pressure and advisory signals, focusing on PGA "
            "spills, workarea execution mode, and cache efficiency."
        ),
        impact="MEDIUM",
        impact_rank=4,
    ),
    "COMMIT": RecommendationTemplate(
        issue="COMMIT",
        action=(
            "Review redo behavior and log file sync latency, including "
            "commit frequency, redo path latency, and log sizing."
        ),
        impact="MEDIUM",
        impact_rank=3,
    ),
    "RAC": RecommendationTemplate(
        issue="RAC",
        action=(
            "Investigate gc waits and cross-instance access patterns to "
            "reduce RAC coordination and interconnect pressure."
        ),
        impact="HIGH",
        impact_rank=5,
    ),
    "ADG": RecommendationTemplate(
        issue="ADG",
        action=(
            "Analyze transport lag and apply lag, validating redo shipping "
            "health, standby recovery throughput, and role state."
        ),
        impact="HIGH",
        impact_rank=5,
    ),
}
