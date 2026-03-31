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


class RecommendationWithNextStep(Recommendation):
    next_step: str


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
        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation="Reduce CPU demand immediately by tuning the highest-load SQL and execution paths. CPU saturation is limiting throughput and must be treated as the primary performance constraint.",
            rationale=f"DB CPU is consuming {pct_db_time} of total DB time, which shows CPU is saturated enough to cap workload throughput.",
            actions=[
                "Tune the top CPU-consuming SQL statements first and remove avoidable row processing.",
                "Validate execution plans and eliminate inefficient plan regressions on the busiest statements.",
                "Reduce unnecessary parse, execute, and fetch activity in the highest-volume application paths.",
            ],
            next_step="Start with the SQL statements and code paths consuming the most DB CPU.",
            evidence=evidence,
        )

    if issue_type == "sql_concentration":
        combined_pct_total = _format_pct(evidence.get("combined_pct_total"))
        modules = _extract_modules(evidence)
        if len(modules) == 1:
            recommendation = (
                f"Prioritize SQL tuning in module '{modules[0]}' immediately. "
                "A small number of statements are dominating the workload and will deliver the fastest performance gain."
            )
            rationale = (
                f"The top 2 SQL statements from module '{modules[0]}' account for {combined_pct_total} "
                "of total elapsed SQL time."
            )
        else:
            recommendation = (
                "Prioritize the top elapsed-time SQL statements immediately. "
                "A small number of statements dominate the workload and are the correct first tuning target."
            )
            rationale = (
                f"The top 2 SQL statements account for {combined_pct_total} of total elapsed SQL time."
            )

        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation=recommendation,
            rationale=rationale,
            actions=[
                "Review execution plans for the top elapsed-time SQL IDs first.",
                "Tune the dominant statements before spending time on lower-impact workload areas.",
                "Stabilize plan quality and remove inefficient access paths, joins, or repeated executions.",
            ],
            next_step="Start with the top elapsed-time SQL IDs and the module that owns the highest elapsed-time share.",
            evidence=evidence,
        )

    if issue_type == "io_pressure":
        event_name = str(evidence.get("event_name") or "the dominant User I/O event")
        pct_db_time = _format_pct(evidence.get("pct_db_time"))
        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation="Reduce physical read demand by correcting SQL and access paths before escalating storage as the primary cause. The first priority is to remove unnecessary I/O from the workload itself.",
            rationale=f"'{event_name}' is consuming {pct_db_time} of DB time, which makes User I/O a material performance constraint driven by read demand.",
            actions=[
                "Tune the SQL statements driving the highest physical read volume first.",
                "Validate indexing, join strategy, and access path quality for the hottest objects.",
                "Review storage latency only after SQL and object access patterns have been validated.",
            ],
            next_step="Start with the SQL statements and objects responsible for the highest physical read demand.",
            evidence=evidence,
        )

    if issue_type == "commit_pressure":
        pct_db_time = _format_pct(evidence.get("pct_db_time"))
        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation="Reduce commit frequency and tighten redo path performance immediately. Commit processing is gating throughput and must be shortened at the application and redo layers.",
            rationale=f"log file sync is consuming {pct_db_time} of DB time, which shows commit processing is materially gating workload throughput.",
            actions=[
                "Review commit frequency in the application flow and batch small transactions where appropriate.",
                "Validate redo log sizing, switch behavior, and redo device latency.",
                "Remove unnecessary commit calls inside tight execution loops.",
            ],
            next_step="Start by reviewing commit frequency in the application transaction flow.",
            evidence=evidence,
        )

    if issue_type == "concurrency_pressure":
        combined_pct_db_time = _format_pct(evidence.get("combined_pct_db_time"))
        if severity == "medium":
            recommendation = (
                "Address concurrency after the primary bottlenecks are underway. "
                "It is a secondary constraint, but the current contention still warrants targeted cleanup."
            )
        else:
            recommendation = (
                "Reduce contention on shared resources and hot execution paths immediately. "
                "Concurrency pressure is materially contributing to response time and throughput loss."
            )

        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation=recommendation,
            rationale=f"Concurrency-related waits are consuming {combined_pct_db_time} of DB time, which indicates measurable contention on shared database resources.",
            actions=[
                "Identify the specific objects, SQL statements, or code paths behind the dominant concurrency waits.",
                "Reduce hotspot access patterns and shorten high-contention transaction paths.",
                "Validate whether latch, cursor, or block-level contention is the primary driver.",
            ],
            next_step="Start by isolating the specific hot objects or execution paths that sessions are colliding on.",
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
