from __future__ import annotations

from typing import Any, Dict, List

from src.models.recommendation import Recommendation


RECOMMENDATION_ORDER = (
    "cpu_pressure",
    "sql_concentration",
    "io_pressure",
    "commit_pressure",
    "concurrency_pressure",
)


def generate_recommendations(
    issues: List[Dict[str, Any]],
) -> List[Recommendation]:
    issue_by_type = {
        str(issue.get("issue_type") or ""): issue
        for issue in issues
    }
    recommendations: List[Recommendation] = []

    for issue_type in RECOMMENDATION_ORDER:
        issue = issue_by_type.get(issue_type)
        if issue is None:
            continue

        recommendation = _build_recommendation(issue)
        if recommendation is not None:
            recommendations.append(recommendation)

    return recommendations


def _build_recommendation(issue: Dict[str, Any]) -> Recommendation | None:
    issue_type = str(issue.get("issue_type") or "")
    severity = str(issue.get("severity") or "medium")
    evidence = issue.get("evidence", {})

    if issue_type == "cpu_pressure":
        pct_db_time = _format_pct(evidence.get("pct_db_time"))
        return Recommendation(
            issue_type=issue_type,
            severity=severity,
            recommendation="Reduce CPU demand by tuning the highest-load SQL and execution paths.",
            rationale=f"DB CPU is consuming {pct_db_time} of total DB time, which indicates CPU is the dominant bottleneck.",
            actions=[
                "Tune the highest CPU-consuming SQL statements first.",
                "Validate execution plans and remove inefficient plan regressions.",
                "Reduce avoidable parse, execute, and fetch activity in the busiest code paths.",
            ],
            evidence=evidence,
        )

    if issue_type == "sql_concentration":
        combined_pct_total = _format_pct(evidence.get("combined_pct_total"))
        modules = _extract_modules(evidence)
        if len(modules) == 1:
            recommendation = f"Prioritize SQL tuning in module '{modules[0]}' because elapsed time is concentrated in a small number of statements."
            rationale = (
                f"The top 2 SQL statements from module '{modules[0]}' account for {combined_pct_total} "
                "of total elapsed SQL time."
            )
        else:
            recommendation = "Prioritize the top elapsed-time SQL statements because a small number of statements dominate total SQL time."
            rationale = f"The top 2 SQL statements account for {combined_pct_total} of total elapsed SQL time."

        return Recommendation(
            issue_type=issue_type,
            severity=severity,
            recommendation=recommendation,
            rationale=rationale,
            actions=[
                "Review execution plans for the top elapsed-time SQL IDs.",
                "Tune the dominant SQL statements before lower-impact workload areas.",
                "Stabilize plan quality and remove inefficient access paths or repeated executions.",
            ],
            evidence=evidence,
        )

    if issue_type == "io_pressure":
        event_name = str(evidence.get("event_name") or "the dominant User I/O event")
        pct_db_time = _format_pct(evidence.get("pct_db_time"))
        return Recommendation(
            issue_type=issue_type,
            severity=severity,
            recommendation="Reduce physical reads and improve access paths for the SQL and objects driving the dominant I/O waits.",
            rationale=f"'{event_name}' is consuming {pct_db_time} of DB time, which makes User I/O a material performance constraint.",
            actions=[
                "Tune the SQL statements driving the highest physical read demand.",
                "Validate indexing and access path quality for the hottest objects.",
                "Review storage latency and throughput for the affected workload window.",
            ],
            evidence=evidence,
        )

    if issue_type == "commit_pressure":
        pct_db_time = _format_pct(evidence.get("pct_db_time"))
        return Recommendation(
            issue_type=issue_type,
            severity=severity,
            recommendation="Reduce commit frequency and tighten redo path performance.",
            rationale=f"log file sync is consuming {pct_db_time} of DB time, which shows commit processing is materially affecting throughput.",
            actions=[
                "Review application commit frequency and batch small transactions where appropriate.",
                "Validate redo log sizing and redo device latency.",
                "Remove unnecessary commit calls in tight execution loops.",
            ],
            evidence=evidence,
        )

    if issue_type == "concurrency_pressure":
        combined_pct_db_time = _format_pct(evidence.get("combined_pct_db_time"))
        return Recommendation(
            issue_type=issue_type,
            severity=severity,
            recommendation="Reduce contention on shared resources and hot execution paths.",
            rationale=f"Concurrency-related waits are consuming {combined_pct_db_time} of DB time, which indicates measurable contention on shared database resources.",
            actions=[
                "Identify the specific objects or code paths behind the dominant concurrency waits.",
                "Reduce hotspot access patterns and shorten high-contention transaction paths.",
                "Validate whether latch, cursor, or block-level contention is the primary driver.",
            ],
            evidence=evidence,
        )

    return None


def _extract_modules(evidence: Dict[str, Any]) -> List[str]:
    modules = evidence.get("modules")
    if isinstance(modules, list):
        return [str(module).strip() for module in modules if str(module).strip()]

    return []


def _format_pct(value: Any) -> str:
    numeric_value = _to_float(value)
    if numeric_value is None:
        return "0.0%"

    return f"{numeric_value:.1f}%"


def _to_float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None

    return None
