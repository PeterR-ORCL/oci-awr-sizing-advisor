from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from src.analysis.recommendation_catalog import (
    DOMAIN_ORDER as DECISION_DOMAIN_ORDER,
    RECOMMENDATION_TEMPLATES,
)
from src.models.decision import AwrDecision
from src.models.recommendation import ActionRecommendation, Recommendation
from src.recommendation.recommendation_engine import (
    Recommendation as Phase6Recommendation,
    generate_recommendations as generate_phase6_recommendations,
)

RECOMMENDATION_ORDER = (
    "topology_event",
    "dg_replication_state",
    "cluster_contention",
    "cpu_pressure",
    "sql_concentration",
    "io_pressure",
    "commit_pressure",
    "concurrency_pressure",
)
MAX_DECISION_RECOMMENDATIONS = 3


@dataclass(slots=True)
class RecommendationWithNextStep(Recommendation):
    next_step: str


def generate_recommendations(
    issues: List[Dict[str, Any]],
) -> List[Recommendation]:
    issue_by_type = {str(issue.get("issue_type") or ""): issue for issue in issues}
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
            recommendation=(
                "Reduce CPU demand immediately by tuning the highest-load SQL "
                "and execution paths. CPU saturation is limiting throughput and "
                "must be treated as the primary performance constraint."
            ),
            rationale=(
                f"DB CPU is consuming {pct_db_time} of total DB time, which "
                "shows CPU is saturated enough to cap workload throughput."
            ),
            actions=[
                (
                    "Tune the top CPU-consuming SQL statements first and remove "
                    "avoidable row processing."
                ),
                (
                    "Validate execution plans and eliminate inefficient plan "
                    "regressions on the busiest statements."
                ),
                (
                    "Reduce unnecessary parse, execute, and fetch activity in "
                    "the highest-volume application paths."
                ),
            ],
            next_step=(
                "Start with the SQL statements and code paths consuming the "
                "most DB CPU."
            ),
            evidence=evidence,
        )

    if issue_type == "topology_event":
        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation=(
                "Treat the current snapshot as an operational transition event "
                "first. Validate failover, role-transition, and recovery state "
                "before interpreting the interval as a pure workload-sizing signal."
            ),
            rationale=(
                "Failover, switchover, or post-failover recovery evidence is "
                "present, so topology state must be stabilized before generic "
                "scaling conclusions are trusted."
            ),
            actions=[
                "Validate current database role and cluster/replication state first.",
                (
                    "Check whether the interval sits inside failover or "
                    "role-transition recovery activity."
                ),
                (
                    "Delay sizing actions until the platform has returned to a "
                    "steady operating state."
                ),
            ],
            next_step=(
                "Start by confirming whether the interval is inside failover or "
                "role-transition recovery behavior."
            ),
            evidence=evidence,
        )

    if issue_type == "dg_replication_state":
        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation=(
                "Treat the dominant issue as Data Guard replication health, not "
                "generic workload scaling. Replication-state pressure should be "
                "resolved before the interval is used to justify capacity changes."
            ),
            rationale=(
                "Replication-state evidence is present, which points to Data "
                "Guard health or recovery state rather than to a simple CPU or "
                "storage shortfall."
            ),
            actions=[
                (
                    "Validate redo transport health, network path quality, and "
                    "standby recovery progress."
                ),
                (
                    "Check whether apply lag is driven by backlog, transport "
                    "delay, or post-transition catch-up."
                ),
                (
                    "Separate primary workload symptoms from replication-lag "
                    "symptoms before sizing decisions are made."
                ),
            ],
            next_step=(
                "Start by validating Data Guard role, redo shipping health, and "
                "standby recovery state for the current role."
            ),
            evidence=evidence,
        )

    if issue_type == "cluster_contention":
        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation=(
                "Treat the dominant issue as RAC coordination pressure before "
                "treating it as generic CPU or storage pressure. Global-cache "
                "and cluster waits should be reduced through access-pattern and "
                "instance-affinity tuning first."
            ),
            rationale=(
                "Cluster wait pressure is materially visible, which points to RAC "
                "coordination and interconnect behavior rather than to a generic "
                "single-instance bottleneck."
            ),
            actions=[
                (
                    "Identify objects and SQL paths driving the hottest "
                    "global-cache traffic."
                ),
                (
                    "Review service placement, instance affinity, and "
                    "cross-instance access patterns."
                ),
                (
                    "Check whether interconnect stress or GC buffer busy "
                    "behavior is amplifying the response-time profile."
                ),
            ],
            next_step=(
                "Start by identifying the SQL and objects generating the highest "
                "cross-instance global-cache traffic."
            ),
            evidence=evidence,
        )

    if issue_type == "sql_concentration":
        combined_pct_total = _format_pct(evidence.get("combined_pct_total"))
        modules = _extract_modules(evidence)
        if len(modules) == 1:
            recommendation = (
                f"Prioritize SQL tuning in module '{modules[0]}' immediately. "
                "A small number of statements are dominating the workload and "
                "will deliver the fastest performance gain."
            )
            rationale = (
                f"The top 3 SQL statements from module '{modules[0]}' account "
                f"for {combined_pct_total} of total elapsed SQL time."
            )
        else:
            recommendation = (
                "Prioritize the top elapsed-time SQL statements immediately. "
                "A small number of statements dominate the workload and are the "
                "correct first tuning target."
            )
            rationale = (
                f"The top 3 SQL statements account for {combined_pct_total} of "
                "total elapsed SQL time."
            )

        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation=recommendation,
            rationale=rationale,
            actions=[
                "Review execution plans for the top elapsed-time SQL IDs first.",
                (
                    "Tune the dominant statements before spending time on "
                    "lower-impact workload areas."
                ),
                (
                    "Stabilize plan quality and remove inefficient access paths, "
                    "joins, or repeated executions."
                ),
            ],
            next_step=(
                "Start with the top elapsed-time SQL IDs and the module that "
                "owns the highest elapsed-time share."
            ),
            evidence=evidence,
        )

    if issue_type == "io_pressure":
        event_name = str(evidence.get("event_name") or "the dominant User I/O event")
        pct_db_time = _format_pct(evidence.get("pct_db_time"))
        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation=(
                "Reduce physical read demand by correcting SQL and access paths "
                "before escalating storage as the primary cause. The first "
                "priority is to remove unnecessary I/O from the workload itself."
            ),
            rationale=(
                f"'{event_name}' is consuming {pct_db_time} of DB time, which "
                "makes User I/O a material performance constraint driven by "
                "read demand."
            ),
            actions=[
                (
                    "Tune the SQL statements driving the highest physical read "
                    "volume first."
                ),
                (
                    "Validate indexing, join strategy, and access path quality "
                    "for the hottest objects."
                ),
                (
                    "Review storage latency only after SQL and object access "
                    "patterns have been validated."
                ),
            ],
            next_step=(
                "Start with the SQL statements and objects responsible for the "
                "highest physical read demand."
            ),
            evidence=evidence,
        )

    if issue_type == "commit_pressure":
        pct_db_time = _format_pct(evidence.get("pct_db_time"))
        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation=(
                "Reduce commit frequency and tighten redo path performance "
                "immediately. Commit processing is gating throughput and must "
                "be shortened at the application and redo layers."
            ),
            rationale=(
                f"log file sync is consuming {pct_db_time} of DB time, which "
                "shows commit processing is materially gating workload throughput."
            ),
            actions=[
                (
                    "Review commit frequency in the application flow and batch "
                    "small transactions where appropriate."
                ),
                (
                    "Validate redo log sizing, switch behavior, and redo device "
                    "latency."
                ),
                "Remove unnecessary commit calls inside tight execution loops.",
            ],
            next_step=(
                "Start by reviewing commit frequency in the application "
                "transaction flow."
            ),
            evidence=evidence,
        )

    if issue_type == "concurrency_pressure":
        combined_pct_db_time = _format_pct(evidence.get("combined_pct_db_time"))
        if severity == "medium":
            recommendation = (
                "Address concurrency after the primary bottlenecks are underway. "
                "It is a secondary constraint, but the current contention still "
                "warrants targeted cleanup."
            )
        else:
            recommendation = (
                "Reduce contention on shared resources and hot execution paths "
                "immediately. Concurrency pressure is materially contributing to "
                "response time and throughput loss."
            )

        return RecommendationWithNextStep(
            issue_type=issue_type,
            severity=severity,
            recommendation=recommendation,
            rationale=(
                "Concurrency-related waits are consuming "
                f"{combined_pct_db_time} of DB time, which indicates measurable "
                "contention on shared database resources."
            ),
            actions=[
                (
                    "Identify the specific objects, SQL statements, or code "
                    "paths behind the dominant concurrency waits."
                ),
                (
                    "Reduce hotspot access patterns and shorten high-contention "
                    "transaction paths."
                ),
                (
                    "Validate whether latch, cursor, or block-level contention "
                    "is the primary driver."
                ),
            ],
            next_step=(
                "Start by isolating the specific hot objects or execution paths "
                "that sessions are colliding on."
            ),
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


def generate_decision_recommendations(
    decision: AwrDecision,
) -> list[Phase6Recommendation]:
    """Generate deterministic Phase 6 recommendations from one decision object."""

    return generate_phase6_recommendations(
        primary_issue=decision.primary_issue,
        secondary_issues=list(decision.secondary_issues),
        overall_status=decision.overall_status,
        severity=decision.severity_score,
        feature_vector=decision.evidence.get("feature_evidence") if decision.evidence else {},
    )


def _ordered_unique_issues(decision: AwrDecision) -> list[str]:
    requested_issues = [decision.primary_issue] + list(decision.secondary_issues)
    ordered_issues: list[str] = []
    for domain in DECISION_DOMAIN_ORDER:
        if domain in requested_issues and domain not in ordered_issues:
            ordered_issues.append(domain)
    if decision.primary_issue in ordered_issues:
        ordered_issues.remove(decision.primary_issue)
    return [decision.primary_issue] + ordered_issues


def _rank_recommendation_candidates(
    issues: list[str],
    decision: AwrDecision,
) -> list[str]:
    return sorted(
        issues,
        key=lambda issue: (
            -_candidate_rank_score(issue, decision),
            DECISION_DOMAIN_ORDER.index(issue),
        ),
    )


def _candidate_rank_score(issue: str, decision: AwrDecision) -> float:
    template = RECOMMENDATION_TEMPLATES[issue]
    primary_bonus = 1000.0 if issue == decision.primary_issue else 0.0
    secondary_discount = 0.0 if issue == decision.primary_issue else 10.0
    return (
        primary_bonus
        + decision.severity_score
        + (template.impact_rank * 10.0)
        - secondary_discount
    )


def _recommendation_confidence(base_confidence: float, priority: int) -> float:
    normalized_base = min(max(float(base_confidence), 0.0), 1.0)
    adjustment = 0.05 * max(priority - 1, 0)
    return round(min(max(normalized_base - adjustment, 0.0), 1.0), 4)


def _recommendation_evidence(
    decision: AwrDecision,
    issue: str,
) -> dict[str, Any]:
    evidence = decision.evidence or {}
    return {
        "severity_score": decision.severity_score,
        "overall_status": decision.overall_status,
        "domain_score": (evidence.get("domain_scores") or {}).get(issue),
        "feature_evidence": (evidence.get("feature_evidence") or {}).get(
            issue,
            {},
        ),
        "anomaly_evidence": (evidence.get("anomaly_evidence") or {}).get(
            issue,
            [],
        ),
        "score_evidence": (evidence.get("score_evidence") or {}).get(issue, {}),
    }
