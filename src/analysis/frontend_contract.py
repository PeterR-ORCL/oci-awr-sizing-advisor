from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from typing import Any

from src.models.decision import AwrDecision
from src.models.recommendation import ActionRecommendation

OUTPUT_VERSION = "phase4.frontend.v1"
OUTPUT_SOURCE = "phase4"

_METRIC_FIELD_MAP: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("cpu_pct", ("DB_CPU_PCT_DB_TIME", "CPU_UTIL_AVG", "CPU_UTIL_P95")),
    ("read_latency_ms", ("READ_LATENCY_MS", "CELL_SINGLE_BLOCK_LATENCY_MS")),
    ("user_io_pressure", ("USER_IO_PRESSURE",)),
    ("hard_parses_per_sec", ("HARD_PARSES_PER_SEC",)),
    ("log_file_sync_ms", ("LOG_FILE_SYNC_MS",)),
    ("cluster_wait_pct_db_time", ("CLUSTER_WAIT_PCT_DB_TIME",)),
    ("transport_lag_sec", ("TRANSPORT_LAG_SEC", "APPLY_LAG_SEC")),
)


def build_frontend_contract(
    decision: AwrDecision,
    recommendations: list[ActionRecommendation],
    generated_at: datetime | None = None,
    output_version: str = OUTPUT_VERSION,
    source: str = OUTPUT_SOURCE,
) -> dict[str, Any]:
    timestamp = _format_timestamp(generated_at or datetime.now(timezone.utc))
    evidence = decision.evidence or {}
    flattened_features = _flatten_feature_evidence(evidence.get("feature_evidence"))

    return {
        "awr_id": decision.awr_id,
        "analysis": {
            "status": decision.overall_status,
            "primary_issue": decision.primary_issue,
            "secondary_issues": list(decision.secondary_issues),
            "severity_score": decision.severity_score,
            "confidence": decision.confidence,
        },
        "evidence": {
            "domain_scores": dict(evidence.get("domain_scores") or {}),
            "top_signals": list(evidence.get("primary_reasons") or []),
            "feature_evidence": dict(evidence.get("feature_evidence") or {}),
            "score_evidence": dict(evidence.get("score_evidence") or {}),
        },
        "metrics": _build_metrics_snapshot(flattened_features),
        "anomalies": _flatten_anomalies(evidence.get("anomaly_evidence")),
        "recommendations": [
            recommendation.to_dict() for recommendation in recommendations
        ],
        "metadata": {
            "generated_at": timestamp,
            "output_version": output_version,
            "source": source,
        },
    }


def render_frontend_contract_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=False)


def build_analysis_screen_model(
    canonical_payload: dict[str, Any],
    report_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Screen 2 from canonical diagnosis, evidence, trends, and explanation."""

    report_data = report_data or {}
    product = _as_dict(canonical_payload.get("product"))
    metadata = _as_dict(canonical_payload.get("metadata"))
    decision = _as_dict(canonical_payload.get("decision"))
    scores = _as_dict(canonical_payload.get("scores"))
    trends = _as_dict(canonical_payload.get("trends"))
    anomalies = _as_dict(canonical_payload.get("anomalies"))
    grouped_findings = _as_dict(canonical_payload.get("grouped_deterministic_findings"))
    llm_explanation = _as_dict(canonical_payload.get("llm_explanation"))
    analysis_context = _as_dict(report_data.get("analysis_context"))
    analysis_information = _build_analysis_information(
        metadata,
        analysis_context,
        canonical_payload=canonical_payload,
        report_data=report_data,
    )
    health_check = _build_analysis_health_check(
        canonical_payload,
        report_data=report_data,
    )
    normalized_decision = _build_normalized_display_decision(
        canonical_payload,
        report_data=report_data,
        health_check=health_check,
    )
    primary_evidence = _as_dict(grouped_findings.get("primary_evidence"))
    recommendation_summary = _as_dict(grouped_findings.get("recommendation_summary"))
    ingestion_context = _as_dict(report_data.get("ingestion_context"))
    intake_summary = _as_dict(ingestion_context.get("intake_summary"))
    technical_sections = _build_analysis_technical_sections(
        report_data=report_data,
        trends=trends,
        anomalies=anomalies,
        grouped_findings=grouped_findings,
        analysis_context=analysis_context,
        topology_detected=analysis_information.get("topology_detected"),
        platform_detected=analysis_information.get("platform_detected"),
    )

    return {
        # Screen 2 consumes canonical diagnosis and evidence.
        "screen": "analysis",
        "scope_note": _analysis_scope_note(
            metadata,
            report_data=report_data,
        ),
        "normalized_decision": normalized_decision,
        "header": {
            "title": product.get("title"),
            "db_name": metadata.get("db_name"),
            "dbid": metadata.get("dbid"),
            "instance_name": metadata.get("instance_name"),
            "host_name": metadata.get("host_name"),
            "snapshot_begin": metadata.get("snapshot_begin"),
            "snapshot_end": metadata.get("snapshot_end"),
        },
        "ingestion_header": {
            "title": product.get("title"),
            "run_label": ingestion_context.get("run_label") or metadata.get("generated_at"),
            "source_mode": ingestion_context.get("source_mode") or "LOCAL",
            "total_files": intake_summary.get("total_files"),
            "succeeded": intake_summary.get("succeeded"),
            "skipped": intake_summary.get("skipped"),
        },
        "analysis_information": analysis_information,
        "decision_summary": {
            "overall_status": normalized_decision.get("overall_status"),
            "primary_issue": normalized_decision.get("primary_issue"),
            "secondary_issues": list(normalized_decision.get("secondary_issues") or []),
            "confidence": normalized_decision.get("confidence"),
            "severity_score": normalized_decision.get("severity_score"),
            "display_severity_label": normalized_decision.get("display_severity_label"),
            "decision_posture": normalized_decision.get("decision_posture"),
            "health_summary": normalized_decision.get("health_summary"),
            "historical_posture": normalized_decision.get("historical_posture"),
            "primary_issue_display_score": normalized_decision.get(
                "primary_issue_display_score"
            ),
        },
        "visual_summary": _build_analysis_visual_summary(report_data),
        "evidence_panel": {
            "primary_evidence": primary_evidence,
            "secondary_evidence": list(
                grouped_findings.get("secondary_evidence") or []
            ),
            "domain_scores": normalized_decision.get("domain_scores") or {},
            "decision_evidence": _as_dict(decision.get("evidence")),
        },
        "scores_panel": {
            **scores,
            "domain_scores": normalized_decision.get("domain_scores") or {},
        },
        "health_check": health_check,
        "trend_context": {
            "trends": trends,
            "trend_summary": grouped_findings.get("trend_summary") or {},
        },
        "anomaly_context": {
            "anomalies": anomalies,
            "anomaly_summary": grouped_findings.get("anomaly_summary") or {},
        },
        "technical_sections": technical_sections,
        "root_cause_interpretation": {
            "summary": _build_analysis_root_cause_summary(
                normalized_decision=normalized_decision,
                primary_evidence=primary_evidence,
            ),
            "reasons": list(primary_evidence.get("reasons") or []),
        },
        "recommended_action_plan": {
            "summary": _build_analysis_orientation_summary(
                normalized_decision=normalized_decision,
                primary_evidence=primary_evidence,
            ),
            "items": [],
            "normalized_decision": normalized_decision,
        },
        "explanation_panel": {
            "technical_explanation": llm_explanation.get("technical_explanation"),
            "executive_explanation": llm_explanation.get("executive_explanation"),
            "action_oriented_explanation": _build_analysis_orientation_summary(
                normalized_decision=normalized_decision,
                primary_evidence=primary_evidence,
            ),
            "technical_recap": _build_analysis_explanation_recap(
                normalized_decision=normalized_decision,
                technical_sections=technical_sections,
                trend_summary=_as_dict(grouped_findings.get("trend_summary")),
                anomaly_summary=_as_dict(grouped_findings.get("anomaly_summary")),
            ),
            "executive_recap": _build_analysis_executive_recap(
                normalized_decision=normalized_decision,
                primary_evidence=primary_evidence,
            ),
            "authoritative": False,
        },
        "engineering_view": _build_engineering_view(
            normalized_decision=normalized_decision,
            primary_evidence=primary_evidence,
            secondary_evidence=list(grouped_findings.get("secondary_evidence") or []),
            anomaly_summary=_as_dict(grouped_findings.get("anomaly_summary")),
        ),
    }


def build_ingestion_screen_model(
    canonical_payload: dict[str, Any],
    report_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Screen 1 from deterministic intake and validation runtime state."""

    report_data = report_data or {}
    product = _as_dict(canonical_payload.get("product"))
    metadata = _as_dict(canonical_payload.get("metadata"))
    ingestion_context = _as_dict(report_data.get("ingestion_context"))
    intake_summary = _as_dict(ingestion_context.get("intake_summary"))
    analysis_context = _as_dict(report_data.get("analysis_context"))
    environment_context = _build_analysis_information(
        metadata,
        analysis_context,
        canonical_payload=canonical_payload,
        report_data=report_data,
    )
    report_rows = [
        _as_dict(row) for row in (ingestion_context.get("report_rows") or [])
    ]
    validation_notes = list(ingestion_context.get("validation_notes") or [])
    warning_count = sum(
        len(row.get("validation_notes") or [])
        for row in report_rows
    )
    topology_hints = sorted(
        {
            str(row.get("topology_hints") or "").strip()
            for row in report_rows
            if str(row.get("topology_hints") or "").strip()
        }
    )
    unknown_capture_count = sum(
        1
        for note in validation_notes
        if "unknown section header" in str(note).lower()
    )
    if not intake_summary:
        snapshot_count = len(report_data.get("snapshot_labels") or [])
        intake_summary = {
            "total_files": snapshot_count,
            "processed": snapshot_count,
            "succeeded": snapshot_count,
            "failed": 0,
            "skipped": 0,
            "manifest_status": (
                "Runtime input directory processed."
                if snapshot_count
                else "No runtime inputs were recorded."
            ),
        }

    return {
        # Screen 1 is intake/validation truth for the 5-screen product architecture.
        "screen": "ingestion",
        "header": {
            "title": product.get("title"),
            "run_label": ingestion_context.get("run_label") or metadata.get("generated_at"),
            "source_mode": ingestion_context.get("source_mode") or "LOCAL",
        },
        "intake_summary": intake_summary,
        "environment_context": {
            **environment_context,
            "source_mode": ingestion_context.get("source_mode") or "LOCAL",
        },
        "environment_scope_note": _analysis_scope_note(
            metadata,
            report_data=report_data,
        ),
        "report_rows": report_rows,
        "parse_confidence_adaptation": {
            "parse_completeness_score": None,
            "warnings_count": warning_count,
            "sections_detected": None,
            "sections_missing": None,
            "unknowns_captured": unknown_capture_count,
            "alias_fallback_matching": None,
            "topology_hints": topology_hints,
            "version_platform_topology_hints": topology_hints,
            "adaptation_summary": (
                "The parser handled the observed AWR inputs across the current runtime scope."
                if report_rows
                else "No parsed AWR reports were available to assess parser adaptation."
            ),
        },
        "validation_notes": {
            "notes": validation_notes,
            "summary": (
                f"{len(validation_notes)} intake or validation notes captured."
                if validation_notes
                else "No intake or validation warnings were recorded."
            ),
        },
        "supportive_explanation": {
            "authoritative": False,
            "text": _build_ingestion_supportive_explanation(
                report_rows=report_rows,
                environment_scope_note=_analysis_scope_note(
                    metadata,
                    report_data=report_data,
                ),
                validation_notes=validation_notes,
            ),
        },
    }


def build_recommendation_screen_model(
    canonical_payload: dict[str, Any],
    report_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Screen 4 from canonical recommendations and action explanation."""

    report_data = report_data or {}
    decision = _as_dict(canonical_payload.get("decision"))
    recommendations = canonical_payload.get("recommendations") or []
    grouped_findings = _as_dict(canonical_payload.get("grouped_deterministic_findings"))
    llm_explanation = _as_dict(canonical_payload.get("llm_explanation"))
    compatibility = _as_dict(report_data.get("compatibility"))
    oci_guidance = _as_dict(report_data.get("oci_guidance"))
    health_check = _build_analysis_health_check(
        canonical_payload,
        report_data=report_data,
    )
    normalized_decision = _build_normalized_display_decision(
        canonical_payload,
        report_data=report_data,
        health_check=health_check,
    )

    recommendation_cards: list[dict[str, Any]] = []
    for recommendation in recommendations:
        recommendation_dict = _as_dict(recommendation)
        display_priority = _normalize_display_priority(
            recommendation_dict.get("priority"),
            normalized_decision,
        )
        recommendation_cards.append(
            {
                "priority": display_priority,
                "issue": recommendation_dict.get("domain"),
                "action": recommendation_dict.get("action"),
                "impact": recommendation_dict.get("impact"),
                "confidence": recommendation_dict.get("confidence"),
                "rationale": recommendation_dict.get("rationale"),
                "category": recommendation_dict.get("category"),
                "category_label": _recommendation_category_label(
                    recommendation_dict.get("category"),
                    recommendation_dict.get("action"),
                ),
                "source_signals": recommendation_dict.get("source_signals") or {},
            }
        )
    if len(recommendation_cards) < 3:
        recommendation_summary = _as_dict(grouped_findings.get("recommendation_summary"))
        for item in recommendation_summary.get("items") or []:
            item_dict = _as_dict(item)
            action = _clean_context_value(item_dict.get("action"))
            if not action:
                continue
            if any(
                str(card.get("action") or "").strip().lower() == action.lower()
                for card in recommendation_cards
            ):
                continue
            recommendation_cards.append(
                {
                    "priority": normalized_decision.get("recommendation_priority"),
                    "issue": _recommendation_issue_label(
                        action,
                        normalized_decision.get("primary_issue"),
                    ),
                    "action": action,
                    "impact": None,
                    "confidence": normalized_decision.get("confidence"),
                    "rationale": item_dict.get("rationale") or recommendation_summary.get("summary"),
                    "category": item_dict.get("title") or "deterministic",
                    "category_label": _recommendation_category_label(
                        item_dict.get("title") or "deterministic",
                        action,
                    ),
                    "source_signals": item_dict.get("source_signals") or {},
                }
            )
    if len(recommendation_cards) < 4:
        for recommendation in compatibility.get("recommendations") or []:
            recommendation_dict = _as_dict(recommendation)
            action = _clean_context_value(recommendation_dict.get("recommendation"))
            issue = _clean_context_value(recommendation_dict.get("issue_type"))
            if not action or not issue:
                continue
            if any(
                str(card.get("action") or "").strip().lower() == action.lower()
                for card in recommendation_cards
            ):
                continue
            recommendation_cards.append(
                {
                    "priority": _normalize_display_priority(
                        recommendation_dict.get("severity"),
                        normalized_decision,
                    ),
                    "issue": issue.replace("_", " "),
                    "action": action,
                    "impact": None,
                    "confidence": normalized_decision.get("confidence"),
                    "rationale": recommendation_dict.get("rationale"),
                    "category": "supplemental",
                    "category_label": _recommendation_category_label(
                        "supplemental",
                        action,
                    ),
                    "source_signals": recommendation_dict.get("evidence") or {},
                }
            )
    if len(recommendation_cards) < 4:
        agentic_decision = (
            compatibility.get("agentic_decision")
            if isinstance(compatibility.get("agentic_decision"), dict)
            else report_data.get("agentic_decision")
        )
        agentic_decision = _as_dict(agentic_decision)
        for action in agentic_decision.get("execution_plan") or []:
            action_text = _clean_context_value(action)
            if not action_text:
                continue
            if any(
                str(card.get("action") or "").strip().lower() == action_text.lower()
                for card in recommendation_cards
            ):
                continue
            recommendation_cards.append(
                {
                    "priority": normalized_decision.get("recommendation_priority"),
                    "issue": _recommendation_issue_label(
                        action_text,
                        normalized_decision.get("primary_issue"),
                    ),
                    "action": action_text,
                    "impact": None,
                    "confidence": normalized_decision.get("confidence"),
                    "rationale": "Execution-plan guidance derived from the deterministic decision layer.",
                    "category": "execution-plan",
                    "category_label": _recommendation_category_label(
                        "execution-plan",
                        action_text,
                    ),
                    "source_signals": {},
                }
            )
    recommendation_cards.sort(
        key=lambda item: _priority_sort_key(item.get("priority")),
        reverse=True,
    )
    recommendation_cards = _dedupe_recommendation_cards(recommendation_cards)
    recommendation_cards = _tighten_recommendation_cards(recommendation_cards)
    recommendation_groups = _build_recommendation_groups(recommendation_cards)
    sizing_guidance_text = _join_display_lines(
        [
            oci_guidance.get("current_state_assessment"),
            oci_guidance.get("scaling_trigger_conditions"),
            oci_guidance.get("oci_architecture_guidance"),
        ]
    )

    return {
        # Screen 5 consumes canonical recommendations and action explanation.
        "screen": "recommendation_action",
        "normalized_decision": normalized_decision,
        "header": {
            "primary_issue": normalized_decision.get("primary_issue"),
            "overall_status": normalized_decision.get("overall_status"),
            "confidence": normalized_decision.get("confidence"),
            "decision_posture": normalized_decision.get("decision_posture"),
            "health_summary": normalized_decision.get("health_summary"),
            "historical_posture": normalized_decision.get("historical_posture"),
            "display_severity_label": normalized_decision.get("display_severity_label"),
            "primary_issue_display_score": normalized_decision.get(
                "primary_issue_display_score"
            ),
            "secondary_issue": (
                list(normalized_decision.get("secondary_issues") or [None])[0]
            ),
        },
        "recommendation_list": recommendation_cards,
        "recommendation_groups": recommendation_groups,
        "recommendation_evidence_tie_back": {
            "recommendation_summary": grouped_findings.get("recommendation_summary")
            or {},
            "primary_evidence": grouped_findings.get("primary_evidence") or {},
            "secondary_evidence": list(
                grouped_findings.get("secondary_evidence") or []
            ),
        },
        "action_explanation": (
            llm_explanation.get("action_explanation")
            or _as_dict(grouped_findings.get("recommendation_summary")).get("summary")
        ),
        "future_extension": {
            "oci_sizing_guidance": sizing_guidance_text,
            "sizing_guidance_blocks": _build_sizing_guidance_blocks(
                oci_guidance,
                sizing_guidance_text,
            ),
            "remediation_options": _join_display_lines(
                [card.get("action") for card in recommendation_cards[1:3]]
            ),
            "operational_next_steps": (
                "Complete the first tuning pass, then reassess residual pressure."
                if recommendation_cards
                and _normalize_issue_key(normalized_decision.get("primary_issue")) == "CPU"
                else _join_display_lines([card.get("action") for card in recommendation_cards[:1]])
            ),
            "cost_impact_guidance": compatibility.get("agentic_decision", {}).get("scaling_decision")
            if isinstance(compatibility.get("agentic_decision"), dict)
            else None,
        },
        "engineering_view": _build_engineering_view(
            normalized_decision=normalized_decision,
            primary_evidence=_as_dict(grouped_findings.get("primary_evidence")),
            secondary_evidence=list(grouped_findings.get("secondary_evidence") or []),
            anomaly_summary=_as_dict(grouped_findings.get("anomaly_summary")),
            recommendation_cards=recommendation_cards,
        ),
    }


def build_review_comparison_screen_model(
    canonical_payload: dict[str, Any],
    report_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Screen 4 from deterministic historical review and comparison context."""

    report_data = report_data or {}
    metadata = _as_dict(canonical_payload.get("metadata"))
    trends = _as_dict(canonical_payload.get("trends"))
    anomalies = _as_dict(canonical_payload.get("anomalies"))
    grouped_findings = _as_dict(canonical_payload.get("grouped_deterministic_findings"))
    llm_explanation = _as_dict(canonical_payload.get("llm_explanation"))
    analysis_context = _as_dict(report_data.get("analysis_context"))
    comparison_context = _as_dict(report_data.get("comparison_context"))
    decision = _as_dict(canonical_payload.get("decision"))
    decision_evidence = _as_dict(decision.get("evidence"))
    feature_values = _flatten_domain_feature_values(
        decision_evidence.get("feature_evidence")
    )
    scope_stats = _scope_stats(report_data)
    instance_count = _resolve_display_instance_count(
        report_data,
        analysis_context,
        feature_values,
        metadata=metadata,
        selected_scope_only=False,
    )
    health_check = _build_analysis_health_check(
        canonical_payload,
        report_data=report_data,
    )
    normalized_decision = _build_normalized_display_decision(
        canonical_payload,
        report_data=report_data,
        health_check=health_check,
    )
    historical_topology = _build_historical_topology_platform_review(
        analysis_context=analysis_context,
        report_data=report_data,
        feature_values=feature_values,
        instance_count=instance_count,
    )
    snapshot_count = comparison_context.get("snapshot_count")
    if snapshot_count is None:
        snapshot_count = len(report_data.get("snapshot_labels") or [])

    host_instance_notes = [
        note
        for note in [
            (
                f"Host scope: {metadata.get('host_name')}"
                if metadata.get("host_name")
                else None
            ),
            (
                f"Instance scope: {metadata.get('instance_name')}"
                if metadata.get("instance_name")
                else None
            ),
        ]
        if note
    ]
    anomaly_summary = grouped_findings.get("anomaly_summary") or {}
    trend_summary = grouped_findings.get("trend_summary") or {}
    trend_summary = {
        **_as_dict(trend_summary),
        "summary": (
            _compact_narrative_caveat(
                _as_dict(trend_summary).get("summary"),
                normalized_decision.get("primary_issue"),
            )
            or _as_dict(trend_summary).get("summary")
        ),
    }
    if _normalize_issue_key(normalized_decision.get("primary_issue")) == "CPU":
        trend_summary["summary"] = re.sub(
            r"CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim\.?",
            "CPU remained dominant across the window, but the pattern was intermittent rather than continuous.",
            str(trend_summary.get("summary") or ""),
            flags=re.IGNORECASE,
        )
    historical_posture = (
        normalized_decision.get("historical_posture")
        or normalized_decision.get("decision_posture")
    )
    visual_support = _build_visual_support_summary(report_data)
    analysis_visual_summary = _build_analysis_visual_summary(report_data)
    visual_story = _build_screen_4_visual_story(
        normalized_decision=normalized_decision,
        report_data=report_data,
        historical_topology=historical_topology,
        analysis_visual_summary=analysis_visual_summary,
    )
    historical_summary_text = _build_historical_summary_text(
        normalized_decision=normalized_decision,
        trend_summary=_as_dict(trend_summary),
        anomaly_summary=_as_dict(anomaly_summary),
        visual_support=visual_support,
        fallback_summary=(
            comparison_context.get("drift_summary")
            or report_data.get("multi_snapshot_summary")
        ),
        visual_story=visual_story,
    )
    scope_label = _format_scope_label(
        metadata.get("db_name"),
        metadata.get("dbid"),
        fallback=(
            comparison_context.get("analysis_scope_label")
            or analysis_context.get("source_database")
        ),
    )

    return {
        # Screen 4 is temporal/comparative truth for the 5-screen product architecture.
        "screen": "historical_review",
        "normalized_decision": normalized_decision,
        "header": {
            "db_name": metadata.get("db_name"),
            "dbid": metadata.get("dbid"),
            "instance_name": metadata.get("instance_name"),
            "host_name": metadata.get("host_name"),
            "comparison_window": (
                comparison_context.get("comparison_window")
                or analysis_context.get("awr_count_and_window")
            ),
            "snapshot_count": snapshot_count,
            "scope_label": scope_label,
        },
        "current_selection_summary": {
            "scope": scope_label,
            "current_window": comparison_context.get("comparison_window"),
            "comparison_mode": (
                "multi-snapshot comparison"
                if snapshot_count and snapshot_count > 1
                else "single-window review"
            ),
            "latest_vs_prior": _compact_selector_summary(
                comparison_context.get("latest_vs_trend"),
                limit=160,
            ),
        },
        "historical_verdict": {
            "dominant_pattern": normalized_decision.get("primary_issue"),
            "historical_stability": trend_summary.get("summary"),
            "trend_posture": historical_posture,
            "anomaly_burden": anomaly_summary.get("count"),
            "historical_posture": historical_posture,
            "display_severity_label": normalized_decision.get("display_severity_label"),
            "primary_issue_display_score": normalized_decision.get(
                "primary_issue_display_score"
            ),
        },
        "historical_summary": {
            "summary": historical_summary_text,
            "key_findings": list(trends.get("findings") or []),
        },
        "trend_review": {
            "trends": trends,
            "trend_summary": trend_summary,
        },
        "anomaly_review": {
            "anomalies": anomalies,
            "anomaly_summary": anomaly_summary,
        },
        "comparison_review": {
            "latest_interval": _compact_selector_summary(
                comparison_context.get("latest_snapshot_summary")
                or report_data.get("latest_snapshot_summary"),
                limit=72,
            ),
            "worst_interval": _compact_selector_summary(
                comparison_context.get("worst_snapshot_summary"),
                limit=72,
            ),
            "latest_vs_trend": _compact_selector_summary(
                comparison_context.get("latest_vs_trend"),
                limit=160,
            ),
            "drift_summary": _build_historical_drift_summary(
                comparison_context=comparison_context,
                normalized_decision=normalized_decision,
                anomaly_summary=_as_dict(anomaly_summary),
            ),
        },
        "topology_platform_review": {
            "rac_summary": historical_topology.get("rac_summary"),
            "data_guard_summary": historical_topology.get("data_guard_summary"),
            "exadata_summary": historical_topology.get("exadata_summary"),
            "host_instance_notes": host_instance_notes,
        },
        "visual_analysis": {
            "time_series_available": any(
                _as_dict(family).get("data_quality") == "ok"
                for family in _as_dict(visual_story.get("time_series_families")).values()
            ),
            "distribution_available": any(
                _as_dict(group).get("data_quality") == "ok"
                for group in _as_dict(visual_story.get("violin_groups")).values()
            ),
            "grouped_metrics_available": bool(report_data.get("derived_scalar_metrics")),
            "story": visual_story,
            "summary": _build_visual_analysis_summary(
                normalized_decision=normalized_decision,
                report_data=report_data,
                historical_topology=historical_topology,
                visual_story=visual_story,
            ),
        },
        "explanation_panel": {
            "authoritative": False,
            "executive_summary": _build_historical_executive_explanation(
                normalized_decision=normalized_decision,
                visual_support=visual_support,
                fallback_text=llm_explanation.get("executive_explanation"),
                visual_story=visual_story,
            ),
            "historical_interpretation": _build_historical_interpretation(
                normalized_decision=normalized_decision,
                trend_summary=_as_dict(trend_summary),
                anomaly_summary=_as_dict(anomaly_summary),
                visual_story=visual_story,
                visual_support=visual_support,
            ),
            "action_context": _build_historical_action_explanation(
                normalized_decision=normalized_decision,
                action_text=llm_explanation.get("action_explanation"),
                recommendation_summary=_as_dict(grouped_findings.get("recommendation_summary")),
            ),
            "technical_context": _build_historical_technical_explanation(
                normalized_decision=normalized_decision,
                visual_support=visual_support,
                trend_summary=_as_dict(trend_summary),
                anomaly_summary=_as_dict(anomaly_summary),
                visual_story=visual_story,
            ),
        },
        "historical_scope_memory": _build_historical_memory_review(
            normalized_decision=normalized_decision,
            analysis_visual_summary=analysis_visual_summary,
            visual_story=visual_story,
        ),
        "engineering_view": _build_engineering_view(
            normalized_decision=normalized_decision,
            primary_evidence=_as_dict(grouped_findings.get("primary_evidence")),
            secondary_evidence=list(grouped_findings.get("secondary_evidence") or []),
            anomaly_summary=_as_dict(anomaly_summary),
            visual_story=visual_story,
        ),
    }


def build_history_selector_screen_model(
    canonical_payload: dict[str, Any],
    report_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build Screen 3 as a dedicated history selector and filter page."""

    report_data = report_data or {}
    metadata = _as_dict(canonical_payload.get("metadata"))
    analysis_context = _as_dict(report_data.get("analysis_context"))
    comparison_context = _as_dict(report_data.get("comparison_context"))
    snapshot_count = comparison_context.get("snapshot_count")
    if snapshot_count is None:
        snapshot_count = len(report_data.get("snapshot_labels") or [])
    scope = (
        comparison_context.get("analysis_scope_label")
        or analysis_context.get("source_database")
    )
    comparison_window = (
        comparison_context.get("comparison_window")
        or analysis_context.get("awr_count_and_window")
    )
    review_modes = [
        "historical trend view",
        "period comparison",
        "anomaly review",
        "cross-run review",
        "future memory / similarity view",
    ]
    latest_snapshot_summary = _compact_selector_summary(
        comparison_context.get("latest_snapshot_summary")
    )
    worst_snapshot_summary = _compact_selector_summary(
        comparison_context.get("worst_snapshot_summary")
    )
    latest_vs_prior = _compact_selector_summary(
        comparison_context.get("latest_vs_trend")
    )
    scope_label = _format_scope_label(
        metadata.get("db_name"),
        metadata.get("dbid"),
        fallback=scope,
    )
    return {
        # Screen 3 defines historical scope and timeframe before results are reviewed.
        "screen": "history_selector",
        "header": {
            "db_name": metadata.get("db_name"),
            "instance_name": metadata.get("instance_name"),
            "host_name": metadata.get("host_name"),
            "window": comparison_window,
        },
        "scope_selection": {
            "options": ["DBID", "DB name", "INSTANCE_NAME", "HOST_NAME", "fleet/global"],
            "active_scope": scope_label,
        },
        "timeframe_selection": {
            "comparison_window": _compact_selector_summary(
                comparison_context.get("comparison_window")
            ),
            "start_end_period": (
                f"{analysis_context.get('analysis_start')} -> {analysis_context.get('analysis_end')}"
                if analysis_context.get("analysis_start") or analysis_context.get("analysis_end")
                else None
            ),
            "window_a": latest_snapshot_summary,
            "window_b": worst_snapshot_summary,
            "comparison_mode": (
                "Latest interval vs broader comparison window"
                if snapshot_count and snapshot_count > 1
                else "Single-window review"
            ),
            "latest_vs_prior": latest_vs_prior,
        },
        "review_mode": {
            "options": review_modes,
            "active_mode": (
                "historical trend view"
                if snapshot_count and snapshot_count > 1
                else "period comparison"
            ),
        },
        "current_selection_summary": {
            "scope": scope_label,
            "timeframe": comparison_window,
            "review_mode": (
                "historical trend view"
                if snapshot_count and snapshot_count > 1
                else "period comparison"
            ),
        },
    }


def build_phase5_screen_models(
    canonical_payload: dict[str, Any],
    report_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build canonical UI view models for the 5-screen product architecture."""

    return {
        "screen_1_ingestion": build_ingestion_screen_model(
            canonical_payload,
            report_data=report_data,
        ),
        "screen_2_analysis": build_analysis_screen_model(
            canonical_payload,
            report_data=report_data,
        ),
        "screen_3_history_selector": build_history_selector_screen_model(
            canonical_payload,
            report_data=report_data,
        ),
        "screen_4_historical_review": build_review_comparison_screen_model(
            canonical_payload,
            report_data=report_data,
        ),
        "screen_5_recommendation_action": build_recommendation_screen_model(
            canonical_payload,
            report_data=report_data,
        ),
    }


def _build_metrics_snapshot(
    feature_values: dict[str, float],
) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for output_name, source_names in _METRIC_FIELD_MAP:
        for source_name in source_names:
            value = feature_values.get(source_name)
            if value is None:
                continue
            metrics[output_name] = value
            break
    return metrics


def _build_analysis_information(
    metadata: dict[str, Any],
    analysis_context: dict[str, Any],
    canonical_payload: dict[str, Any] | None = None,
    report_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_data = report_data or {}
    canonical_payload = canonical_payload or {}
    decision = _as_dict(canonical_payload.get("decision"))
    decision_evidence = _as_dict(decision.get("evidence"))
    feature_values = _flatten_domain_feature_values(
        decision_evidence.get("feature_evidence")
    )
    platform_metrics = _parse_platform_capacity_metrics(
        analysis_context.get("operating_system")
    )
    scope_stats = _selected_scope_stats(metadata, report_data)
    instance_count = _resolve_display_instance_count(
        report_data,
        analysis_context,
        feature_values,
        metadata=metadata,
        selected_scope_only=True,
    )
    if not instance_count and _clean_context_value(metadata.get("instance_name")):
        instance_count = "1"
    source_database = _clean_source_database(
        metadata.get("db_name") or analysis_context.get("source_database"),
        metadata.get("dbid"),
    )
    return {
        "hostname": _derive_display_hostname(
            metadata,
            analysis_context,
            scope_stats,
        ),
        "operating_system": _clean_operating_system(
            analysis_context.get("operating_system")
        ),
        "source_database": source_database,
        "instance_count": instance_count,
        "db_version": _clean_context_value(analysis_context.get("db_version")),
        "database_role": _clean_database_role(analysis_context.get("database_role")),
        "ocpus_cores": _derive_display_ocpus_cores(
            analysis_context.get("ocpus_cores"),
            platform_metrics,
            instance_count,
            scope_stats,
        ),
        "memory_per_instance": _derive_display_memory_per_instance(
            analysis_context.get("memory_per_instance"),
            platform_metrics,
            scope_stats,
        ),
        "platform_detected": (
            _derive_display_platform(
                analysis_context.get("platform_detected"),
                feature_values,
                scope_stats,
                report_data=report_data,
                selected_scope_only=True,
            )
            or "Not Established"
        ),
        "topology_detected": _derive_display_topology(
            analysis_context,
            feature_values,
            instance_count,
            report_data=report_data,
            selected_scope_only=True,
        ),
        "snapshot_start": analysis_context.get("analysis_start")
        or metadata.get("snapshot_begin"),
        "snapshot_end": analysis_context.get("analysis_end")
        or metadata.get("snapshot_end"),
        "total_reports_snapshot_window": analysis_context.get("awr_count_and_window"),
        "last_snapshot": analysis_context.get("latest_snapshot_interval"),
        "dbid": metadata.get("dbid"),
        "host_name": metadata.get("host_name"),
        "instance_name": metadata.get("instance_name"),
    }


def _derive_display_hostname(
    metadata: dict[str, Any],
    analysis_context: dict[str, Any],
    scope_stats: dict[str, int],
) -> str | None:
    selected_scope_host = _clean_context_value(metadata.get("host_name"))
    if selected_scope_host:
        return selected_scope_host
    current_host = _clean_context_value(analysis_context.get("hostname"))
    if not current_host:
        return None
    if scope_stats.get("host_count", 0) > 1:
        return f"Mixed runtime context ({scope_stats['host_count']} hosts)"
    return current_host


def _resolve_display_instance_count(
    report_data: dict[str, Any],
    analysis_context: dict[str, Any],
    feature_values: dict[str, float],
    metadata: dict[str, Any] | None = None,
    selected_scope_only: bool = False,
) -> str | None:
    raw_count = _safe_float(analysis_context.get("instance_count"))
    if metadata and selected_scope_only:
        report_rows = _selected_scope_report_rows(report_data, metadata)
    else:
        report_rows = _as_dict(report_data.get("ingestion_context")).get("report_rows") or []
    observed_instances = {
        str(_as_dict(row).get("instance_name") or "").strip()
        for row in report_rows
        if str(_as_dict(row).get("instance_name") or "").strip()
    }
    observed_hosts = {
        str(_as_dict(row).get("host_name") or "").strip()
        for row in report_rows
        if str(_as_dict(row).get("host_name") or "").strip()
    }
    observed_count = len(observed_instances)
    observed_host_count = len(observed_hosts)
    rac_evidence = any(
        (_safe_float(feature_values.get(metric_name)) or 0.0) > 0.0
        for metric_name in (
            "CLUSTER_WAIT_PCT_DB_TIME",
            "GC_CR_WAIT_PCT_DB_TIME",
            "GC_CURRENT_WAIT_PCT_DB_TIME",
            "GC_BUFFER_BUSY_PCT_DB_TIME",
        )
    )
    valid_raw_count = (
        int(raw_count)
        if raw_count is not None and raw_count >= 1.0 and raw_count <= 8.0
        else None
    )
    if rac_evidence:
        if 1 < observed_count <= 8:
            return str(observed_count)
        if 1 < observed_host_count <= 8:
            return str(observed_host_count)
        if valid_raw_count and valid_raw_count > 1:
            return str(valid_raw_count)
        return None
    if valid_raw_count:
        return str(valid_raw_count)
    if observed_count == 1 or observed_host_count == 1:
        return "1"
    if observed_count and observed_count <= 2:
        return str(observed_count)
    return "1"


def _scope_stats(report_data: dict[str, Any]) -> dict[str, int]:
    report_rows = _as_dict(report_data.get("ingestion_context")).get("report_rows") or []
    return _scope_stats_from_rows(report_rows)


def _scope_stats_from_rows(report_rows: list[dict[str, Any]]) -> dict[str, int]:
    db_names = {
        str(_as_dict(row).get("db_name") or "").strip()
        for row in report_rows
        if str(_as_dict(row).get("db_name") or "").strip()
    }
    dbids = {
        str(_as_dict(row).get("dbid") or "").strip()
        for row in report_rows
        if str(_as_dict(row).get("dbid") or "").strip()
    }
    hosts = {
        str(_as_dict(row).get("host_name") or "").strip()
        for row in report_rows
        if str(_as_dict(row).get("host_name") or "").strip()
    }
    return {
        "db_count": len(db_names or dbids),
        "host_count": len(hosts),
    }


def _selected_scope_report_rows(
    report_data: dict[str, Any],
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    report_rows = _as_dict(report_data.get("ingestion_context")).get("report_rows") or []
    normalized_rows = [_as_dict(row) for row in report_rows]
    if not normalized_rows:
        return []

    dbid = _clean_context_value(metadata.get("dbid"))
    db_name = _clean_context_value(metadata.get("db_name"))
    host_name = _clean_context_value(metadata.get("host_name"))
    instance_name = _clean_context_value(metadata.get("instance_name"))

    scoped_rows = normalized_rows
    if dbid:
        matching_dbid = [
            row for row in scoped_rows
            if _clean_context_value(row.get("dbid")) == dbid
        ]
        if matching_dbid:
            scoped_rows = matching_dbid
    elif db_name:
        matching_db_name = [
            row for row in scoped_rows
            if _clean_context_value(row.get("db_name")) == db_name
        ]
        if matching_db_name:
            scoped_rows = matching_db_name

    if host_name:
        matching_host = [
            row for row in scoped_rows
            if _clean_context_value(row.get("host_name")) == host_name
        ]
        if matching_host:
            scoped_rows = matching_host

    if instance_name:
        matching_instance = [
            row for row in scoped_rows
            if _clean_context_value(row.get("instance_name")) == instance_name
        ]
        if matching_instance:
            scoped_rows = matching_instance

    return scoped_rows


def _selected_scope_stats(
    metadata: dict[str, Any],
    report_data: dict[str, Any],
) -> dict[str, int]:
    selected_rows = _selected_scope_report_rows(report_data, metadata)
    if selected_rows:
        return _scope_stats_from_rows(selected_rows)
    return _scope_stats(report_data)


def _analysis_scope_note(
    metadata: dict[str, Any],
    report_data: dict[str, Any] | None = None,
) -> str | None:
    report_data = report_data or {}
    scope_stats = _selected_scope_stats(metadata, report_data)
    db_name = _clean_context_value(metadata.get("db_name"))
    dbid = _clean_context_value(metadata.get("dbid"))
    host_name = _clean_context_value(metadata.get("host_name"))
    if db_name or dbid:
        scope_label = _format_scope_label(
            db_name,
            dbid,
            fallback=db_name or dbid,
        )
        return (
            f"Selected decision scope: {scope_label}"
            + (f" on {host_name}" if host_name else "")
            + "."
        )
    if scope_stats["db_count"] > 1 or scope_stats["host_count"] > 1:
        return (
            "Mixed multi-report runtime detected. Environment fields are shown only when "
            "they can be scoped cleanly to the selected decision interval."
        )
    if db_name or host_name:
        return (
            f"Selected decision scope: {db_name or 'database scope'}"
            + (f" on {host_name}" if host_name else "")
            + "."
        )
    return None


def _build_analysis_executive_recap(
    normalized_decision: dict[str, Any],
    primary_evidence: dict[str, Any],
) -> str:
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "The primary domain"
    summary = _clean_context_value(primary_evidence.get("summary"))
    if summary and not _summary_conflicts_with_primary_issue(summary, normalized_decision):
        return summary
    recap = _governing_issue_statement(primary_issue, "in the selected scope")
    supporting = _supporting_issue_phrase(normalized_decision.get("secondary_issues"))
    if supporting:
        recap += f" {supporting}"
    return recap


def _build_analysis_root_cause_summary(
    normalized_decision: dict[str, Any],
    primary_evidence: dict[str, Any],
) -> str:
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "The primary domain"
    if _normalize_issue_key(primary_issue) == "CPU":
        return "CPU is the governing workload driver in the selected scope."
    summary = _clean_context_value(primary_evidence.get("summary"))
    if summary and not _summary_conflicts_with_primary_issue(summary, normalized_decision):
        return summary
    return _governing_issue_statement(primary_issue, "in the selected scope")


def _build_analysis_orientation_summary(
    normalized_decision: dict[str, Any],
    primary_evidence: dict[str, Any],
) -> str:
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "The primary domain"
    if _normalize_issue_key(primary_issue) == "CPU":
        return "The observed pattern is most consistent with a CPU-led workload, not an I/O-, memory-, or topology-led one."
    issue_label = _issue_product_label(primary_issue)
    display_label = "CPU" if _normalize_issue_key(primary_issue) == "CPU" else issue_label.capitalize()
    return (
        f"{display_label} remains the dominant constraint in the selected scope. "
        f"The current evidence supports a {display_label}-led diagnosis."
    )


def _build_historical_memory_review(
    normalized_decision: dict[str, Any],
    analysis_visual_summary: dict[str, Any],
    visual_story: dict[str, Any],
) -> dict[str, Any]:
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "the dominant workload pattern"
    memory_card = _as_dict(analysis_visual_summary.get("memory"))
    card_statuses = _as_dict(visual_story.get("card_statuses"))
    memory_status = (
        _clean_context_value(memory_card.get("status"))
        or _clean_context_value(card_statuses.get("MEMORY"))
        or "empty"
    ).lower()
    memory_label = (
        _clean_context_value(memory_card.get("selected_label"))
        or _clean_context_value(memory_card.get("card_subtitle"))
        or "Memory history"
    )

    if _normalize_issue_key(primary_issue) == "MEMORY":
        return {
            "summary": (
                "Memory remains the governing historical pattern across the selected window, "
                "so it is reviewed as first-order evidence rather than a secondary signal."
            ),
            "items": [
                f"{memory_label} remains the clearest memory-domain measure in this window."
            ],
        }

    if memory_status == "ok":
        return {
            "summary": "Memory was reviewed and remains non-governing in this window.",
            "items": [
                f"{memory_label} is historically present, but it does not materially influence the dominant workload pattern."
            ],
        }

    if memory_status == "weak":
        return {
            "summary": "Memory was reviewed and remains non-governing in this window.",
            "items": [
                f"{memory_label} is present only as a weak secondary signal relative to the dominant {_issue_product_label(primary_issue)} pattern."
            ],
        }

    return {
        "summary": "Memory was reviewed and no sustained memory pressure is established relative to the dominant CPU-led evidence in this window.",
        "items": [
            "Available memory signals remain below the threshold needed to change the historical interpretation."
        ],
    }


def _build_analysis_explanation_recap(
    normalized_decision: dict[str, Any],
    technical_sections: list[dict[str, Any]],
    trend_summary: dict[str, Any],
    anomaly_summary: dict[str, Any],
) -> str:
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "The selected domain"
    section_titles = [
        _clean_context_value(section.get("title"))
        for section in technical_sections
        if _clean_context_value(section.get("title"))
    ]
    section_text = ", ".join(section_titles[:4]) if section_titles else "the boxed deterministic sections above"
    trend_text = _compact_narrative_caveat(
        trend_summary.get("summary"),
        primary_issue,
    )
    anomaly_count = int(_safe_float(anomaly_summary.get("count")) or 0.0)
    recap = (
        f"The boxed analysis above establishes {_issue_product_label(primary_issue)} as "
        f"the governing issue for the selected scope and grounds that conclusion in {section_text}."
    )
    supporting = _supporting_issue_phrase(normalized_decision.get("secondary_issues"))
    if supporting:
        recap += f" {supporting}"
    if trend_text:
        recap += " Trend context remains supportive rather than decisive across the reviewed window."
    if anomaly_count > 0:
        recap += f" Anomaly review adds {anomaly_count} window(s) of corroborating context."
    return recap


def _build_analysis_visual_summary(
    report_data: dict[str, Any],
) -> dict[str, Any]:
    time_series = _as_dict(report_data.get("time_series_charts"))
    analysis_context = _as_dict(report_data.get("analysis_context"))
    metadata = _as_dict(report_data.get("metadata"))
    decision = _as_dict(report_data.get("decision"))
    feature_values = _flatten_domain_feature_values(
        _as_dict(decision.get("evidence")).get("feature_evidence")
    )
    labels = list(time_series.get("snapshot_labels") or [])
    instance_count = _resolve_display_instance_count(
        report_data,
        analysis_context,
        feature_values,
        metadata=metadata,
        selected_scope_only=True,
    )
    topology_detected = str(
        _derive_display_topology(
            analysis_context,
            feature_values,
            instance_count,
            report_data=report_data,
            selected_scope_only=True,
        )
        or ""
    ).strip().lower()
    has_rac = "rac" in topology_detected
    return {
        "cpu": _select_visual_summary_card(
            card_title="CPU Trend",
            labels=labels,
            domain="cpu",
            candidates=[
                {
                    "selected_key": "db_cpu_pct_db_time_trend",
                    "series_key": "cpu_trend",
                    "card_subtitle": "DB CPU % DB Time",
                    "selected_label": "DB CPU % DB Time",
                    "reason": "This trend reflects the clearest CPU measure available in this window.",
                },
                {
                    "selected_key": "cpu_util_p95_trend",
                    "series_key": "cpu_util_p95_trend",
                    "card_subtitle": "CPU Util P95",
                    "selected_label": "CPU Util P95",
                    "reason": "This trend reflects the clearest CPU measure available in this window.",
                },
                {
                    "selected_key": "cpu_pressure_proxy_trend",
                    "series_key": "cpu_pressure_proxy_trend",
                    "card_subtitle": "CPU Pressure Proxy",
                    "selected_label": "CPU Pressure Proxy",
                    "reason": "This trend reflects the clearest CPU measure available in this window.",
                },
            ],
            empty_subtitle="No Material CPU Pressure",
            empty_reason="No meaningful CPU signal is available for this window.",
            time_series=time_series,
        ),
        "io": _select_visual_summary_card(
            card_title="I/O Trend",
            labels=labels,
            domain="io",
            candidates=[
                {
                    "selected_key": "user_io_pressure_trend",
                    "series_key": "io_trend",
                    "card_subtitle": "User I/O Pressure",
                    "selected_label": "User I/O Pressure",
                    "reason": "This trend reflects the clearest I/O measure available in this window.",
                },
                {
                    "selected_key": "read_latency_ms_trend",
                    "series_key": "read_latency_ms_trend",
                    "card_subtitle": "Read Latency",
                    "selected_label": "Read Latency",
                    "reason": "This trend reflects the clearest I/O measure available in this window.",
                },
                {
                    "selected_key": "log_file_sync_ms_trend",
                    "series_key": "log_file_sync_trend",
                    "card_subtitle": "Commit / Log File Sync",
                    "selected_label": "Commit / Log File Sync",
                    "reason": "This trend reflects the clearest I/O measure available in this window.",
                },
                {
                    "selected_key": "top_sql_load_concentration_trend",
                    "series_key": "sql_concentration_trend",
                    "card_subtitle": "Top SQL Load Concentration",
                    "selected_label": "Top SQL Load Concentration",
                    "reason": "This trend reflects the clearest workload-access measure available in this window.",
                },
            ],
            empty_subtitle="No Material I/O Pressure",
            empty_reason="No meaningful I/O signal is available for this window.",
            time_series=time_series,
        ),
        "memory": _select_visual_summary_card(
            card_title="Memory Trend",
            labels=labels,
            domain="memory",
            candidates=[
                {
                    "selected_key": "pga_spill_pressure_trend",
                    "series_key": "pga_spill_trend",
                    "card_subtitle": "PGA Spill Pressure",
                    "selected_label": "PGA Spill Pressure",
                    "reason": "This trend reflects the clearest memory-related measure available in this window.",
                },
                {
                    "selected_key": "concurrency_pressure_trend",
                    "series_key": "concurrency_trend",
                    "card_subtitle": "Concurrency Pressure",
                    "selected_label": "Concurrency Pressure",
                    "reason": "This trend reflects the clearest memory-related measure available in this window.",
                },
                {
                    "selected_key": "temp_io_pressure_trend",
                    "series_key": "temp_io_trend",
                    "card_subtitle": "Temp I/O Pressure",
                    "selected_label": "Temp I/O Pressure",
                    "reason": "This trend reflects the clearest memory/workarea measure available in this window.",
                },
                {
                    "selected_key": "hard_parses_per_sec_trend",
                    "series_key": "hard_parses_trend",
                    "card_subtitle": "Hard Parses / Second",
                    "selected_label": "Hard Parses / Second",
                    "reason": "This trend reflects the clearest memory-adjacent measure available in this window.",
                },
            ],
            empty_subtitle="No Material Memory Pressure",
            empty_reason="No meaningful memory signal is available for this window.",
            time_series=time_series,
        ),
        "cluster": (
            _select_visual_summary_card(
                card_title="Cluster Trend",
                labels=labels,
                domain="cluster",
                candidates=[
                    {
                        "selected_key": "cluster_wait_pct_db_time_trend",
                        "series_key": "cluster_wait_trend",
                        "card_subtitle": "Cluster Wait %",
                        "selected_label": "Cluster Wait %",
                        "reason": "This trend reflects the clearest cluster measure available in this window.",
                    },
                    {
                        "selected_key": "gc_current_wait_pct_db_time_trend",
                        "series_key": "gc_current_wait_trend",
                        "card_subtitle": "GC Current Wait %",
                        "selected_label": "GC Current Wait %",
                        "reason": "This trend reflects the clearest cluster measure available in this window.",
                    },
                    {
                        "selected_key": "gc_cr_wait_pct_db_time_trend",
                        "series_key": "gc_cr_wait_trend",
                        "card_subtitle": "GC CR Wait %",
                        "selected_label": "GC CR Wait %",
                        "reason": "This trend reflects the clearest cluster measure available in this window.",
                    },
                ],
                empty_subtitle="No Material Cluster Pressure",
                empty_reason="No meaningful cluster signal is available for this window.",
                time_series=time_series,
            )
            if has_rac
            else None
        ),
        "hint": "View full historical analysis in Screen 4",
    }


def _select_visual_summary_card(
    *,
    card_title: str,
    labels: list[Any],
    domain: str,
    candidates: list[dict[str, str]],
    empty_subtitle: str,
    empty_reason: str,
    time_series: dict[str, Any],
) -> dict[str, Any]:
    for candidate in candidates:
        series_values = _numeric_series(time_series.get(candidate["series_key"]))
        if not series_values:
            continue
        status = _series_signal_status(
            series_values,
            domain=domain,
            selected_key=str(candidate.get("selected_key") or ""),
        )
        return {
            "card_title": card_title,
            "card_subtitle": candidate["card_subtitle"],
            "selected_key": candidate["selected_key"],
            "selected_label": candidate.get("selected_label"),
            "labels": list(labels),
            "series": series_values,
            "status": status,
            "reason": candidate["reason"],
        }
    return {
        "card_title": card_title,
        "card_subtitle": empty_subtitle,
        "selected_key": None,
        "selected_label": None,
        "labels": list(labels),
        "series": [],
        "status": "empty",
        "reason": empty_reason,
    }


def _numeric_series(values: Any) -> list[float]:
    if not isinstance(values, list):
        return []
    series: list[float] = []
    for value in values:
        numeric = _safe_float(value)
        if numeric is None:
            continue
        series.append(float(numeric))
    return series


def _series_signal_status(
    series: list[float],
    *,
    domain: str,
    selected_key: str,
) -> str:
    if len(series) < 2:
        return "empty"
    latest_value = abs(series[-1])
    max_value = max(abs(value) for value in series)
    spread = max(series) - min(series)
    non_zero_points = sum(1 for value in series if abs(value) > 0.0)

    if domain == "memory":
        if max_value <= 0.0:
            return "empty"
        if (
            len(series) < 4
            or non_zero_points < 3
            or (latest_value < 0.5 and max_value < 1.0 and spread < 0.5)
        ):
            return "weak"
        return "ok"

    if domain == "cluster":
        if len(series) < 3:
            return "weak"
        if latest_value < 5.0 and max_value < 10.0 and spread < 5.0:
            return "weak"
        return "ok"

    if domain == "cpu":
        if latest_value < 5.0 and max_value < 10.0 and spread < 5.0:
            return "weak"
        return "ok"

    if domain == "io":
        if latest_value < 2.0 and max_value < 5.0 and spread < 3.0:
            return "weak"
        return "ok"

    if max_value <= 0.0 or spread <= 0.05:
        return "weak"
    return "ok"


def _summary_conflicts_with_primary_issue(
    summary: str,
    normalized_decision: dict[str, Any],
) -> bool:
    primary_issue = str(normalized_decision.get("primary_issue") or "").strip().upper()
    text = summary.strip()
    if not primary_issue or not text:
        return False
    if primary_issue == "CPU":
        return bool(
            re.search(r"\bCPU\b.*\binsufficient signal\b", text, flags=re.IGNORECASE)
            or re.search(r"\binsufficient signal\b.*\bCPU\b", text, flags=re.IGNORECASE)
            or re.search(r"\bCPU\b.*\bUnavailable\b", text, flags=re.IGNORECASE)
            or re.search(r"\bUnavailable\b.*\bCPU\b", text, flags=re.IGNORECASE)
            or re.search(r"\bCPU\b.*\bscore 0(?:\.0+)?\b", text, flags=re.IGNORECASE)
        )
    return False


def _issue_product_label(issue: Any) -> str:
    normalized = _normalize_issue_key(issue)
    return {
        "CPU": "CPU",
        "IO": "I/O",
        "MEMORY": "memory pressure",
        "COMMIT": "commit latency",
        "RAC": "cluster coordination",
        "ADG": "Data Guard lag",
    }.get(normalized, str(issue or "the selected domain").strip() or "the selected domain")


def _governing_issue_statement(issue: Any, scope_text: str) -> str:
    normalized = _normalize_issue_key(issue)
    label = _issue_product_label(issue)
    if normalized in {"CPU", "IO"}:
        return f"{label} remains the primary workload driver {scope_text}."
    return f"{label.capitalize()} remains the governing pressure pattern {scope_text}."


def _supporting_issue_phrase(issues: Any) -> str | None:
    labels = [
        _issue_product_label(issue)
        for issue in (issues or [])
        if _clean_context_value(issue)
    ]
    if not labels:
        return None
    unique_labels: list[str] = []
    for label in labels:
        if label not in unique_labels:
            unique_labels.append(label)
    if len(unique_labels) == 1:
        return f"{unique_labels[0]} remains visible as a supporting factor."
    return (
        f"{', '.join(unique_labels[:-1])} and {unique_labels[-1]} remain visible as "
        "supporting factors."
    )


def _compact_narrative_caveat(text: Any, primary_issue: Any = None) -> str | None:
    cleaned = _clean_context_value(text)
    if not cleaned:
        return None
    compacted = cleaned
    replacements = (
        (
            r"CPU pressure had insufficient history for a trend call over the period reviewed\.?",
            "CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim.",
        ),
        (
            r"Concurrency had insufficient history for a trend call across the interval series\.?",
            "Concurrency history is too thin to treat as a material driver in this window.",
        ),
        (
            r"Top SQL concentration had insufficient history for a trend call over the analysis window\.?",
            "Top SQL history is not strong enough to anchor the historical story in this window.",
        ),
        (
            r"Available populated intervals suggest commit latency remained broadly steady\.?",
            "Commit latency remained broadly steady where historical samples were available.",
        ),
        (
            r"Sparse populated intervals suggest cluster waits worsened\.?",
            "Sparse cluster samples point to intermittent coordination pressure in the broader window.",
        ),
        (
            r"Sparse populated intervals suggest combined GC wait pressure, defined as GC Current \+ GC CR, worsened\.?",
            "Sparse GC samples point to intermittent cluster coordination pressure in the broader window.",
        ),
    )
    for pattern, replacement in replacements:
        compacted = re.sub(pattern, replacement, compacted, flags=re.IGNORECASE)
    compacted = re.sub(r"\s+", " ", compacted).strip()
    if (
        primary_issue
        and _normalize_issue_key(primary_issue) == "CPU"
        and re.search(r"\bCPU\b", compacted, flags=re.IGNORECASE)
        and "limited" in compacted.lower()
    ):
        return "Historical CPU trend continuity is limited in this window."
    return compacted or None


def _compact_selector_summary(value: Any, limit: int = 88) -> str | None:
    text = _clean_context_value(value)
    if not text:
        return None
    first_line = text.splitlines()[0].strip()
    snapshot_match = re.search(
        r"Latest snapshot\s*\(([^)]+)\)",
        first_line,
        flags=re.IGNORECASE,
    )
    if snapshot_match:
        return f"Latest snapshot ({snapshot_match.group(1)})"
    first_sentence = re.split(r"(?<=[.!?])\s+", first_line, maxsplit=1)[0].strip()
    if "," in first_sentence:
        first_sentence = first_sentence.split(",", 1)[0].strip()
    compact = first_sentence or first_line
    compact = re.sub(
        r"The latest interval departs from the worst interval and should be read in broader context\.?",
        "The latest interval differs from the worst interval and should be interpreted in broader historical context.",
        compact,
        flags=re.IGNORECASE,
    )
    compact = re.sub(r"\s+", " ", compact).strip()
    if len(compact) <= limit:
        return compact
    shortened = compact[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-")
    if not shortened:
        shortened = compact[:limit].rstrip(" ,;:-")
    if not shortened.endswith((".", "!", "?")):
        shortened += "."
    return shortened


def _build_analysis_technical_sections(
    report_data: dict[str, Any],
    trends: dict[str, Any],
    anomalies: dict[str, Any],
    grouped_findings: dict[str, Any],
    analysis_context: dict[str, Any],
    topology_detected: Any = None,
    platform_detected: Any = None,
) -> list[dict[str, Any]]:
    anomaly_windows = list(_as_dict(grouped_findings.get("anomaly_summary")).get("windows") or [])
    trend_findings = list(trends.get("findings") or [])
    topology_text = str(topology_detected or "").strip()
    platform_text = str(platform_detected or "").strip()
    has_rac = "RAC" in topology_text
    has_dataguard = "Data Guard" in topology_text
    has_exadata = platform_text.lower() == "exadata"
    sections = [
        {
            "title": "Multi-Snapshot Summary",
            "summary": report_data.get("multi_snapshot_summary"),
            "items": [],
        },
        {
            "title": "Trend Findings",
            "summary": _as_dict(grouped_findings.get("trend_summary")).get("summary"),
            "items": trend_findings,
        },
        {
            "title": "Anomaly Windows",
            "summary": _as_dict(grouped_findings.get("anomaly_summary")).get("summary"),
            "items": [
                f"{item.get('snapshot_label')}: {item.get('metric')} - {item.get('reason')}"
                for item in anomaly_windows
                if _as_dict(item)
            ],
        },
        {
            "title": "Topology Assessment",
            "summary": topology_text,
            "items": [],
        },
        {
            "title": "RAC / Cluster Findings",
            "summary": None,
            "items": _filter_matching_findings(
                trend_findings,
                anomaly_windows,
                ("rac", "cluster", "gc "),
            ),
            "enabled": has_rac,
        },
        {
            "title": "Data Guard Findings",
            "summary": None,
            "items": _filter_matching_findings(
                trend_findings,
                anomaly_windows,
                ("data guard", "transport lag", "apply lag", "adg"),
            ),
            "enabled": has_dataguard,
        },
        {
            "title": "Exadata Findings",
            "summary": platform_text,
            "items": _filter_matching_findings(
                trend_findings,
                anomaly_windows,
                ("exadata", "cell", "smart scan", "offload"),
            ),
            "enabled": has_exadata,
        },
        {
            "title": "Latest Snapshot Assessment",
            "summary": report_data.get("latest_snapshot_summary"),
            "items": [],
        },
    ]
    return [
        section
        for section in sections
        if section.get("enabled", True) and (section.get("summary") or section.get("items"))
    ]


def _clean_context_value(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.upper() in {"UNKNOWN", "UNAVAILABLE", "N/A", "NONE"}:
        return None
    return text


def _format_display_score_text(value: Any) -> str | None:
    numeric = _safe_float(value)
    if numeric is None:
        return None
    return f"{numeric:.1f}".rstrip("0").rstrip(".")


def _join_display_lines(values: list[Any]) -> str | None:
    lines: list[str] = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            for nested in value:
                text = _clean_context_value(nested)
                if text:
                    lines.append(text)
            continue
        text = _clean_context_value(value)
        if text:
            lines.append(text)
    if not lines:
        return None
    return "\n".join(lines)


def _has_numeric_samples(values: Any, minimum: int = 1) -> bool:
    if not isinstance(values, list):
        return False
    count = 0
    for value in values:
        numeric = _safe_float(value)
        if numeric is None:
            continue
        count += 1
    return count >= minimum


def _build_visual_support_summary(report_data: dict[str, Any]) -> dict[str, bool]:
    time_series = _as_dict(report_data.get("time_series_charts"))
    violin_panel = _as_dict(report_data.get("violin_panel"))
    workload = _as_dict(violin_panel.get("workload"))
    cpu_supported = _has_numeric_samples(time_series.get("cpu_trend"), minimum=3) or _has_numeric_samples(
        workload.get("cluster_cpu_pct_db_time"),
        minimum=4,
    )
    sql_supported = bool(report_data.get("top_sql")) or _has_numeric_samples(
        time_series.get("sql_concentration_trend"),
        minimum=3,
    ) or _has_numeric_samples(
        workload.get("cluster_top_sql_concentration_pct"),
        minimum=4,
    )
    return {
        "cpu_supported": cpu_supported,
        "sql_supported": sql_supported,
        "time_series_supported": _has_non_empty_mapping(time_series),
        "distribution_supported": _has_non_empty_mapping(violin_panel),
    }


def _build_visual_analysis_summary(
    normalized_decision: dict[str, Any],
    report_data: dict[str, Any],
    historical_topology: dict[str, Any],
    visual_story: dict[str, Any] | None = None,
) -> str:
    visual_story = visual_story or {}
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "the dominant issue"
    primary_proof = [
        _clean_context_value(item.get("label"))
        for item in (visual_story.get("primary_visual_proof") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    supporting_proof = [
        _clean_context_value(item.get("label"))
        for item in (visual_story.get("supporting_visual_proof") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    contextual_proof = [
        _clean_context_value(item.get("label"))
        for item in (visual_story.get("contextual_visual_proof") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    if not (primary_proof or supporting_proof or contextual_proof):
        return "No supporting visual layers are currently available for this scope and timeframe."
    summary = f"{primary_issue} remains the dominant pattern across the historical window."
    if primary_proof:
        summary += f" Primary evidence is observed in {', '.join(primary_proof[:3])}."
    if supporting_proof:
        summary += f" Supporting evidence stays with {', '.join(supporting_proof[:3])}."
    if contextual_proof:
        summary += (
            " Contextual RAC, Data Guard, or platform signals remain subordinate to "
            "selected-scope truth."
        )
    return summary


def _merge_numeric_metrics(target: dict[str, float], values: Any) -> None:
    if not isinstance(values, dict):
        return
    for key, value in values.items():
        numeric = _safe_float(value)
        if numeric is None:
            continue
        target[str(key)] = numeric


def _build_engineering_view(
    *,
    normalized_decision: dict[str, Any],
    primary_evidence: dict[str, Any] | None = None,
    secondary_evidence: list[dict[str, Any]] | None = None,
    anomaly_summary: dict[str, Any] | None = None,
    visual_story: dict[str, Any] | None = None,
    recommendation_cards: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    primary_evidence = primary_evidence or {}
    secondary_evidence = secondary_evidence or []
    anomaly_summary = anomaly_summary or {}
    visual_story = visual_story or {}
    recommendation_cards = recommendation_cards or []

    scoring_detail = [
        ("Primary Issue Score", normalized_decision.get("primary_issue_display_score")),
        ("Confidence Score", normalized_decision.get("confidence")),
        ("Severity Score", normalized_decision.get("severity_score")),
    ]
    supporting_metrics: dict[str, float] = {}
    _merge_numeric_metrics(supporting_metrics, primary_evidence.get("feature_values") or {})
    for evidence in secondary_evidence:
        _merge_numeric_metrics(supporting_metrics, _as_dict(evidence).get("evidence") or {})
    for recommendation in recommendation_cards:
        _merge_numeric_metrics(
            supporting_metrics,
            _as_dict(recommendation).get("source_signals") or {},
        )

    notes: list[str] = []
    anomaly_count = int(_safe_float(anomaly_summary.get("count")) or 0.0)
    if anomaly_count > 0:
        notes.append(f"Anomaly windows in scope: {anomaly_count}")
    suppressed_groups = list(visual_story.get("suppressed_visual_groups") or [])
    if suppressed_groups:
        suppressed_labels: list[str] = []
        for group in suppressed_groups:
            group_dict = _as_dict(group)
            label = _clean_context_value(group_dict.get("label") or group_dict.get("key"))
            if not label:
                continue
            suppressed_labels.append(label)
        if suppressed_labels:
            notes.append(
                "Suppressed historical families: " + ", ".join(suppressed_labels)
            )

    return {
        "scoring_detail": scoring_detail,
        "supporting_metrics": supporting_metrics,
        "domain_scores": normalized_decision.get("domain_scores") or {},
        "notes": notes,
    }


def _normalize_issue_key(value: Any) -> str:
    text = str(value or "").strip().upper()
    if text in {"I/O", "IO_PRESSURE"}:
        return "IO"
    if text in {"CPU_PRESSURE"}:
        return "CPU"
    if text in {"MEMORY_PRESSURE"}:
        return "MEMORY"
    if text in {"COMMIT_PRESSURE"}:
        return "COMMIT"
    if text in {"CLUSTER", "RAC_CONTENTION"}:
        return "RAC"
    if text in {"DATA GUARD", "DG", "ADG", "DG_REPLICATION_STATE"}:
        return "ADG"
    return text


def _numeric_sample_count(values: Any) -> int:
    if not isinstance(values, list):
        return 0
    return sum(
        1
        for value in values
        if isinstance(value, (int, float)) and math.isfinite(float(value))
    )


def _distinct_numeric_count(values: Any) -> int:
    if not isinstance(values, list):
        return 0
    return len(
        {
            round(float(value), 6)
            for value in values
            if isinstance(value, (int, float)) and math.isfinite(float(value))
        }
    )


def _time_series_data_quality(values: Any) -> str:
    sample_count = _numeric_sample_count(values)
    if sample_count >= 3:
        return "ok"
    if sample_count >= 2:
        return "weak"
    return "empty"


def _violin_data_quality(values: Any) -> str:
    sample_count = _numeric_sample_count(values)
    distinct_count = _distinct_numeric_count(values)
    if sample_count >= 4 and distinct_count >= 2:
        return "ok"
    if sample_count >= 2:
        return "weak"
    return "empty"


def _best_family_quality(payload: dict[str, Any], keys: list[str], *, violin: bool = False) -> str:
    qualities = []
    for key in keys:
        quality = _violin_data_quality(payload.get(key)) if violin else _time_series_data_quality(
            payload.get(key)
        )
        qualities.append(quality)
    if "ok" in qualities:
        return "ok"
    if "weak" in qualities:
        return "weak"
    return "empty"


def _visual_group_entry(
    *,
    kind: str,
    key: str,
    label: str,
    reason: str,
    data_quality: str,
    display_tier: str | None = None,
    suppression_reason: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "key": key,
        "label": label,
        "reason": reason,
        "data_quality": data_quality,
        "display_tier": display_tier,
        "suppression_reason": suppression_reason,
    }


def _build_screen_4_visual_story(
    normalized_decision: dict[str, Any],
    report_data: dict[str, Any],
    historical_topology: dict[str, Any],
    analysis_visual_summary: dict[str, Any],
) -> dict[str, Any]:
    primary_issue = _normalize_issue_key(normalized_decision.get("primary_issue"))
    time_series = _as_dict(report_data.get("time_series_charts"))
    violin_panel = _as_dict(report_data.get("violin_panel"))
    workload_violin = _as_dict(violin_panel.get("workload"))
    topology_violin = _as_dict(violin_panel.get("topology"))
    rac_violin = _as_dict(violin_panel.get("rac_instance"))
    platform_violin = _as_dict(violin_panel.get("platform"))
    top_sql_available = bool(report_data.get("top_sql"))
    visual_support = _build_visual_support_summary(report_data)
    has_rac_context = bool(historical_topology.get("rac_summary"))
    has_adg_context = bool(historical_topology.get("data_guard_summary"))
    has_exadata_context = bool(historical_topology.get("exadata_summary"))
    card_statuses = {
        "CPU": _as_dict(analysis_visual_summary.get("cpu")).get("status") or "empty",
        "IO": _as_dict(analysis_visual_summary.get("io")).get("status") or "empty",
        "MEMORY": _as_dict(analysis_visual_summary.get("memory")).get("status") or "empty",
        "RAC": _as_dict(analysis_visual_summary.get("cluster")).get("status") or "suppressed",
    }
    supporting_issues: list[str] = []
    for issue in normalized_decision.get("secondary_issues") or []:
        normalized = _normalize_issue_key(issue)
        if normalized and normalized != primary_issue and normalized not in supporting_issues:
            supporting_issues.append(normalized)
    for issue_key, status in card_statuses.items():
        if (
            issue_key != primary_issue
            and status == "ok"
            and issue_key not in supporting_issues
            and issue_key not in {"RAC"}
        ):
            supporting_issues.append(issue_key)
    if (
        primary_issue != "COMMIT"
        and _has_numeric_samples(time_series.get("commit_trend"), minimum=3)
        and "COMMIT" not in supporting_issues
    ):
        supporting_issues.append("COMMIT")

    time_series_families = {
        "cpu": _visual_group_entry(
            kind="time_series",
            key="cpu",
            label="CPU history",
            reason="CPU history is promoted when deterministic CPU pressure remains dominant.",
            data_quality=card_statuses.get("CPU") or "empty",
            display_tier="primary" if primary_issue == "CPU" else "supporting",
            suppression_reason=(
                "Suppressed because no material CPU history is available."
                if card_statuses.get("CPU") == "empty"
                else None
            ),
        ),
        "io": _visual_group_entry(
            kind="time_series",
            key="io",
            label="I/O history",
            reason="I/O history stays visible when it materially supports the dominant workload story.",
            data_quality=card_statuses.get("IO") or "empty",
            display_tier="primary" if primary_issue == "IO" else "supporting",
            suppression_reason=(
                "Suppressed because no material I/O history is available."
                if card_statuses.get("IO") == "empty"
                else None
            ),
        ),
        "memory": _visual_group_entry(
            kind="time_series",
            key="memory",
            label="Memory history",
            reason="Memory history is promoted only when a real memory-domain signal is established.",
            data_quality=card_statuses.get("MEMORY") or "empty",
            display_tier="primary" if primary_issue == "MEMORY" else "supporting",
            suppression_reason=(
                "Suppressed because memory-domain signals are weak or absent for this window."
                if card_statuses.get("MEMORY") != "ok"
                else None
            ),
        ),
        "commit": _visual_group_entry(
            kind="time_series",
            key="commit",
            label="Commit history",
            reason="Commit history remains a supporting family when log file sync pressure is present.",
            data_quality=_best_family_quality(time_series, ["commit_trend", "log_file_sync_trend"]),
            display_tier="primary" if primary_issue == "COMMIT" else "supporting",
        ),
        "rac": _visual_group_entry(
            kind="time_series",
            key="rac",
            label="RAC / cluster context",
            reason="Cluster history is contextual only and should remain subordinate to selected-scope truth.",
            data_quality=(
                _best_family_quality(
                    time_series,
                    ["cluster_wait_trend", "gc_wait_trend", "gc_current_wait_trend", "gc_cr_wait_trend"],
                )
                if has_rac_context
                else "suppressed"
            ),
            display_tier="primary" if primary_issue == "RAC" else "contextual",
            suppression_reason=(
                None
                if has_rac_context
                else "Suppressed because RAC is not established for the selected scope."
            ),
        ),
        "adg": _visual_group_entry(
            kind="time_series",
            key="adg",
            label="Data Guard context",
            reason="Transport/apply lag history remains supportive only when real historical DG evidence exists.",
            data_quality=(
                _best_family_quality(time_series, ["dg_transport_lag_trend", "dg_apply_lag_trend"])
                if has_adg_context
                else "suppressed"
            ),
            display_tier="primary" if primary_issue == "ADG" else "contextual",
            suppression_reason=(
                None
                if has_adg_context
                else "Suppressed because Data Guard is not established for the selected scope."
            ),
        ),
        "exadata": _visual_group_entry(
            kind="time_series",
            key="exadata",
            label="Platform history",
            reason="Engineered-system history is shown only when real platform evidence exists.",
            data_quality=(
                _best_family_quality(
                    time_series,
                    ["exa_cell_io_trend", "exa_offload_efficiency_trend"],
                )
                if has_exadata_context
                else "suppressed"
            ),
            display_tier="contextual",
            suppression_reason=(
                None
                if has_exadata_context
                else "Suppressed because platform evidence is not established."
            ),
        ),
    }
    violin_groups = {
        "workload": _visual_group_entry(
            kind="violin",
            key="workload",
            label="Workload distributions",
            reason="Workload distributions provide the strongest supporting distribution evidence for CPU, I/O, and commit pressure.",
            data_quality=_best_family_quality(
                workload_violin,
                [
                    "cluster_cpu_pct_db_time",
                    "cluster_user_io_pct_db_time",
                    "cluster_log_file_sync_ms",
                    "cluster_top_sql_concentration_pct",
                    "cluster_pga_spill_pressure",
                    "cluster_temp_io_pressure",
                ],
                violin=True,
            ),
            display_tier="primary" if primary_issue in {"CPU", "IO", "MEMORY", "COMMIT"} else "supporting",
        ),
        "topology": _visual_group_entry(
            kind="violin",
            key="topology",
            label="Topology distributions",
            reason="Topology distributions remain contextual and should appear only when cluster or DG evidence is real.",
            data_quality=(
                _best_family_quality(
                    topology_violin,
                    [
                        "cluster_wait_pct_db_time",
                        "gc_current_wait_pct_db_time",
                        "gc_cr_wait_pct_db_time",
                        "transport_lag_sec",
                        "apply_lag_sec",
                    ],
                    violin=True,
                )
                if (has_rac_context or has_adg_context)
                else "suppressed"
            ),
            display_tier="primary" if primary_issue in {"RAC", "ADG"} else "contextual",
            suppression_reason=(
                None
                if (has_rac_context or has_adg_context)
                else "Suppressed because scoped or supporting topology evidence is not established."
            ),
        ),
        "rac_instance": _visual_group_entry(
            kind="violin",
            key="rac_instance",
            label="Per-instance RAC distributions",
            reason="Per-instance RAC distributions remain tertiary supporting context only.",
            data_quality=(
                _best_family_quality(
                    rac_violin,
                    [
                        "per_instance_cpu_pct_db_time",
                        "per_instance_cluster_wait_pct_db_time",
                        "per_instance_gc_current_wait_pct_db_time",
                        "per_instance_gc_cr_wait_pct_db_time",
                    ],
                    violin=True,
                )
                if has_rac_context
                else "suppressed"
            ),
            display_tier="primary" if primary_issue == "RAC" else "contextual",
            suppression_reason=(
                None
                if has_rac_context
                else "Suppressed because RAC is not established for the selected scope."
            ),
        ),
        "platform": _visual_group_entry(
            kind="violin",
            key="platform",
            label="Platform distributions",
            reason="Platform distributions appear only when real engineered-system evidence exists.",
            data_quality=(
                _best_family_quality(
                    platform_violin,
                    ["exa_single_block_read_pct"],
                    violin=True,
                )
                if has_exadata_context
                else "suppressed"
            ),
            display_tier="contextual",
            suppression_reason=(
                None
                if has_exadata_context
                else "Suppressed because platform evidence is not established."
            ),
        ),
    }
    performance_panels = {
        "db_time_breakdown": _visual_group_entry(
            kind="performance",
            key="db_time_breakdown",
            label="DB Time Breakdown",
            reason="Primary issue visual proof starts from deterministic DB time contribution.",
            data_quality="ok",
            display_tier="primary",
        ),
        "top_sql_contribution": _visual_group_entry(
            kind="performance",
            key="top_sql_contribution",
            label="Top SQL Contributors",
            reason="Top SQL stays in the visual story only when real contributor payload exists or workload concentration is explicitly part of the supporting narrative.",
            data_quality=(
                "ok"
                if top_sql_available
                else (
                    "weak"
                    if visual_support.get("sql_supported") and primary_issue in {"CPU", "IO"}
                    else "suppressed"
                )
            ),
            display_tier="supporting",
            suppression_reason=(
                None
                if top_sql_available or (visual_support.get("sql_supported") and primary_issue in {"CPU", "IO"})
                else "Suppressed because scoped Top SQL contributor payload is absent."
            ),
        ),
    }

    section_order = {
        "CPU": ["performance", "time_series", "violin", "scalar"],
        "IO": ["performance", "time_series", "violin", "scalar"],
        "MEMORY": ["time_series", "violin", "performance", "scalar"],
        "COMMIT": ["time_series", "violin", "performance", "scalar"],
        "RAC": ["time_series", "violin", "performance", "scalar"],
        "ADG": ["time_series", "violin", "performance", "scalar"],
    }.get(primary_issue, ["performance", "time_series", "violin", "scalar"])

    time_series_priority_map = {
        "CPU": ["cpu", "io", "commit"],
        "IO": ["io", "cpu", "commit"],
        "MEMORY": ["memory", "cpu", "io"],
        "COMMIT": ["commit", "io", "cpu"],
        "RAC": ["rac", "io", "cpu"],
        "ADG": ["adg", "io", "cpu"],
    }
    violin_group_priority_map = {
        "CPU": ["workload", "topology", "rac_instance"],
        "IO": ["workload", "topology", "rac_instance"],
        "MEMORY": ["workload", "topology", "rac_instance"],
        "COMMIT": ["workload", "topology", "rac_instance"],
        "RAC": ["topology", "rac_instance", "workload"],
        "ADG": ["topology", "workload", "rac_instance"],
    }
    preferred_violin_metrics_map = {
        "CPU": {
            "workload": [
                "cluster_cpu_pct_db_time",
                "cluster_top_sql_concentration_pct",
                "cluster_user_io_pct_db_time",
                "cluster_log_file_sync_ms",
            ],
            "topology": [
                "cluster_wait_pct_db_time",
                "gc_current_wait_pct_db_time",
                "gc_cr_wait_pct_db_time",
            ],
            "rac_instance": [
                "per_instance_cpu_pct_db_time",
                "per_instance_cluster_wait_pct_db_time",
                "per_instance_gc_current_wait_pct_db_time",
                "per_instance_gc_cr_wait_pct_db_time",
            ],
        },
        "IO": {
            "workload": [
                "cluster_user_io_pct_db_time",
                "cluster_read_iops",
                "cluster_read_mb_per_sec",
                "cluster_top_sql_concentration_pct",
                "cluster_log_file_sync_ms",
            ],
            "topology": [
                "cluster_wait_pct_db_time",
                "gc_current_wait_pct_db_time",
                "gc_cr_wait_pct_db_time",
            ],
        },
        "MEMORY": {
            "workload": [
                "cluster_pga_spill_pressure",
                "cluster_temp_io_pressure",
                "cluster_hard_parses_per_sec",
                "cluster_log_file_sync_ms",
            ],
        },
        "COMMIT": {
            "workload": [
                "cluster_log_file_sync_ms",
                "cluster_user_io_pct_db_time",
                "cluster_top_sql_concentration_pct",
            ],
        },
        "RAC": {
            "topology": [
                "cluster_wait_pct_db_time",
                "gc_current_wait_pct_db_time",
                "gc_cr_wait_pct_db_time",
            ],
            "rac_instance": [
                "per_instance_cluster_wait_pct_db_time",
                "per_instance_gc_current_wait_pct_db_time",
                "per_instance_gc_cr_wait_pct_db_time",
                "per_instance_cpu_pct_db_time",
            ],
        },
        "ADG": {
            "topology": [
                "transport_lag_sec",
                "apply_lag_sec",
                "cluster_wait_pct_db_time",
            ],
        },
    }

    time_series_priority = list(time_series_priority_map.get(primary_issue, ["cpu", "io", "commit"]))
    if card_statuses.get("MEMORY") == "ok" and "memory" not in time_series_priority:
        time_series_priority.append("memory")
    if has_rac_context and "rac" not in time_series_priority:
        time_series_priority.append("rac")
    if has_adg_context and "adg" not in time_series_priority:
        time_series_priority.append("adg")
    if has_exadata_context:
        time_series_priority.append("exadata")

    suppressed_time_series = {
        family_key
        for family_key, family_state in time_series_families.items()
        if family_state.get("data_quality") in {"empty", "suppressed"}
        or (
            family_key == "memory"
            and primary_issue != "MEMORY"
            and card_statuses.get("MEMORY") != "ok"
        )
    } | {"network"}

    violin_group_priority = list(
        violin_group_priority_map.get(primary_issue, ["workload", "topology", "rac_instance"])
    )
    suppressed_violin_groups = {
        group_key
        for group_key, group_state in violin_groups.items()
        if group_state.get("data_quality") in {"empty", "suppressed"}
        or (
            group_key == "platform"
            and group_state.get("data_quality") != "ok"
        )
    }

    if primary_issue != "MEMORY" and card_statuses.get("MEMORY") != "ok":
        preferred_violin_metrics_map.setdefault(primary_issue or "CPU", {}).setdefault(
            "workload",
            [],
        )

    primary_visual_groups = [
        performance_panels["db_time_breakdown"],
        _visual_group_entry(
            kind="time_series",
            key=time_series_priority[0],
            label=f"{(time_series_priority[0] or 'primary').upper()} history",
            reason="Primary issue history is promoted first.",
            data_quality=_as_dict(time_series_families.get(time_series_priority[0])).get("data_quality") or "empty",
            suppression_reason=_as_dict(time_series_families.get(time_series_priority[0])).get("suppression_reason"),
        ),
        _visual_group_entry(
            kind="violin",
            key=violin_group_priority[0],
            label=f"{violin_group_priority[0].replace('_', ' ').title()} distributions",
            reason="Primary issue distributions are promoted first.",
            data_quality=_as_dict(violin_groups.get(violin_group_priority[0])).get("data_quality") or "empty",
            suppression_reason=_as_dict(violin_groups.get(violin_group_priority[0])).get("suppression_reason"),
        ),
    ]
    if performance_panels["top_sql_contribution"]["data_quality"] in {"ok", "weak"}:
        primary_visual_groups.append(performance_panels["top_sql_contribution"])

    supporting_visual_groups = [
        _visual_group_entry(
            kind="time_series",
            key=domain.lower(),
            label=f"{domain.title()} history",
            reason="Supporting history remains visible because it materially contributes to the deterministic posture.",
            data_quality=_as_dict(time_series_families.get(domain.lower())).get("data_quality") or "empty",
            suppression_reason=_as_dict(time_series_families.get(domain.lower())).get("suppression_reason"),
        )
        for domain in supporting_issues[:3]
        if domain.lower() in {"cpu", "io", "memory", "commit"}
        and _as_dict(time_series_families.get(domain.lower())).get("data_quality") in {"ok", "weak"}
    ]

    contextual_visual_groups = []
    for context_key in ("rac", "adg"):
        context_state = _as_dict(time_series_families.get(context_key))
        if context_state.get("data_quality") in {"ok", "weak"}:
            contextual_visual_groups.append(context_state)
    for context_group_key in ("topology", "rac_instance", "platform"):
        context_group_state = _as_dict(violin_groups.get(context_group_key))
        if context_group_state.get("data_quality") in {"ok", "weak"}:
            contextual_visual_groups.append(context_group_state)

    story_section_order_map = {
        "CPU": [
            "historical_summary",
            "historical_scope_memory",
            "visual_analysis",
            "trend_review",
            "anomaly_review",
            "period_comparison",
            "topology_platform_review",
            "explanation",
        ],
        "IO": [
            "historical_summary",
            "historical_scope_memory",
            "visual_analysis",
            "trend_review",
            "anomaly_review",
            "period_comparison",
            "topology_platform_review",
            "explanation",
        ],
        "MEMORY": [
            "historical_summary",
            "historical_scope_memory",
            "visual_analysis",
            "trend_review",
            "period_comparison",
            "anomaly_review",
            "topology_platform_review",
            "explanation",
        ],
        "COMMIT": [
            "historical_summary",
            "historical_scope_memory",
            "visual_analysis",
            "trend_review",
            "anomaly_review",
            "period_comparison",
            "topology_platform_review",
            "explanation",
        ],
        "RAC": [
            "historical_summary",
            "historical_scope_memory",
            "visual_analysis",
            "topology_platform_review",
            "trend_review",
            "anomaly_review",
            "period_comparison",
            "explanation",
        ],
        "ADG": [
            "historical_summary",
            "historical_scope_memory",
            "visual_analysis",
            "topology_platform_review",
            "period_comparison",
            "trend_review",
            "anomaly_review",
            "explanation",
        ],
    }
    explanation_section_order = {
        "CPU": ["executive_summary", "historical_interpretation", "action_context", "technical_context"],
        "IO": ["executive_summary", "historical_interpretation", "action_context", "technical_context"],
        "MEMORY": ["executive_summary", "historical_interpretation", "technical_context", "action_context"],
        "COMMIT": ["executive_summary", "historical_interpretation", "action_context", "technical_context"],
        "RAC": ["executive_summary", "historical_interpretation", "technical_context", "action_context"],
        "ADG": ["executive_summary", "historical_interpretation", "technical_context", "action_context"],
    }.get(
        primary_issue,
        ["executive_summary", "historical_interpretation", "action_context", "technical_context"],
    )

    suppressed_visual_groups = [
        _visual_group_entry(
            kind="time_series",
            key=domain,
            label=f"{domain.upper()} family",
            reason="Suppressed because the selected issue story did not establish this family as material for the current scope.",
            data_quality=_as_dict(time_series_families.get(domain)).get("data_quality") or "suppressed",
            suppression_reason=(
                _as_dict(time_series_families.get(domain)).get("suppression_reason")
                or "Suppressed because the selected issue story did not establish this family as material for the current scope."
            ),
        )
        for domain in sorted(suppressed_time_series)
    ] + [
        _visual_group_entry(
            kind="violin",
            key=group_key,
            label=group_key.replace("_", " ").title(),
            reason="Suppressed because scoped or supporting evidence was not established.",
            data_quality=_as_dict(violin_groups.get(group_key)).get("data_quality") or "suppressed",
            suppression_reason=(
                _as_dict(violin_groups.get(group_key)).get("suppression_reason")
                or "Suppressed because scoped or supporting evidence was not established."
            ),
        )
        for group_key in sorted(suppressed_violin_groups)
    ]

    return {
        "primary_issue": primary_issue,
        "supporting_issues": supporting_issues,
        "primary_visual_proof": primary_visual_groups,
        "supporting_visual_proof": supporting_visual_groups,
        "contextual_visual_proof": contextual_visual_groups,
        "card_statuses": card_statuses,
        "section_order": section_order,
        "story_section_order": story_section_order_map.get(
            primary_issue,
            story_section_order_map["CPU"],
        ),
        "explanation_section_order": explanation_section_order,
        "time_series_priority": time_series_priority,
        "time_series_suppressed": sorted(suppressed_time_series),
        "time_series_families": time_series_families,
        "violin_group_priority": violin_group_priority,
        "violin_group_suppressed": sorted(suppressed_violin_groups),
        "violin_groups": violin_groups,
        "preferred_violin_metrics": preferred_violin_metrics_map.get(primary_issue, {}),
        "performance_panels": performance_panels,
        "primary_visual_groups": primary_visual_groups,
        "supporting_visual_groups": supporting_visual_groups,
        "contextual_visual_groups": contextual_visual_groups,
        "suppressed_visual_groups": suppressed_visual_groups,
    }


def _build_ingestion_supportive_explanation(
    report_rows: list[dict[str, Any]],
    environment_scope_note: str | None,
    validation_notes: list[str],
) -> str:
    report_count = len(report_rows)
    warning_count = len([note for note in validation_notes if _clean_context_value(note)])
    scope_text = environment_scope_note or "Runtime scope is limited to the parsed AWR inputs shown above."
    return (
        f"This page is intake-oriented and confirms how the platform understood {report_count} parsed report(s). "
        f"{scope_text} "
        + (
            f"{warning_count} validation note(s) remain in scope for operator review."
            if warning_count
            else "No intake contradictions were detected in the current runtime scope."
        )
    )


def _build_historical_summary_text(
    normalized_decision: dict[str, Any],
    trend_summary: dict[str, Any],
    anomaly_summary: dict[str, Any],
    visual_support: dict[str, bool],
    fallback_summary: Any,
    visual_story: dict[str, Any] | None = None,
) -> str:
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "The selected domain"
    visual_story = visual_story or {}
    anomaly_count = int(_safe_float(anomaly_summary.get("count")) or 0.0)
    if _normalize_issue_key(primary_issue) == "CPU":
        summary_parts = [
            "CPU remains dominant across the selected window, indicating sustained compute pressure rather than a transient external bottleneck."
        ]
    else:
        summary_parts = [_governing_issue_statement(primary_issue, "across the selected window")]
    primary_labels = [
        _clean_context_value(item.get("label"))
        for item in (visual_story.get("primary_visual_proof") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    if primary_labels:
        summary_parts.append(
            f"Primary evidence comes from {', '.join(primary_labels[:3])}, keeping the broader window aligned to the same governing pattern."
        )
    if anomaly_count > 0:
        summary_parts.append(
            f"Anomaly burden remains visible in {anomaly_count} window(s), but it does not displace {_issue_product_label(primary_issue)} as the governing pattern."
        )
    return " ".join(summary_parts)


def _build_historical_executive_explanation(
    normalized_decision: dict[str, Any],
    visual_support: dict[str, bool],
    fallback_text: Any,
    visual_story: dict[str, Any] | None = None,
) -> str:
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "The selected domain"
    primary_proof = [
        _clean_context_value(item.get("label"))
        for item in ((visual_story or {}).get("primary_visual_proof") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    supporting_proof = [
        _clean_context_value(item.get("label"))
        for item in ((visual_story or {}).get("supporting_visual_proof") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    explanation = _governing_issue_statement(primary_issue, "across the selected window")
    if primary_proof:
        explanation += (
            f" The page leads with {', '.join(primary_proof[:3])} as the strongest "
            "historical proof."
        )
    if supporting_proof:
        explanation += f" Supporting evidence stays with {', '.join(supporting_proof[:2])}."
    elif not visual_support.get("cpu_supported") and str(primary_issue).upper() == "CPU":
        explanation += " CPU still anchors the historical interpretation, but direct trend coverage is limited in this window."
    return explanation


def _build_historical_technical_explanation(
    normalized_decision: dict[str, Any],
    visual_support: dict[str, bool],
    trend_summary: dict[str, Any],
    anomaly_summary: dict[str, Any],
    visual_story: dict[str, Any],
) -> str:
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "The selected domain"
    card_statuses = _as_dict(visual_story.get("card_statuses"))
    promoted = [
        _clean_context_value(item.get("label"))
        for item in (visual_story.get("primary_visual_proof") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    supporting = [
        _clean_context_value(item.get("label"))
        for item in (visual_story.get("supporting_visual_proof") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    contextual = [
        _clean_context_value(item.get("label"))
        for item in (visual_story.get("contextual_visual_proof") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    suppressed = [
        _clean_context_value(item.get("label"))
        for item in (visual_story.get("suppressed_visual_groups") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    lines = [
        f"The historical review is organized around {_issue_product_label(primary_issue)}-first evidence."
    ]
    if promoted:
        lines.append(f"Primary support comes from {', '.join(promoted[:3])}.")
    if _normalize_issue_key(primary_issue) != "MEMORY":
        if card_statuses.get("MEMORY") == "ok":
            lines.append(
                "Memory is reviewed explicitly between the primary proof and the supporting trend layer because it is present historically but remains non-governing in this window."
            )
        else:
            lines.append(
                "Memory is reviewed explicitly between the primary proof and the supporting trend layer, but no sustained memory pressure is established relative to the CPU-led evidence."
            )
    if supporting:
        lines.append(f"Supporting evidence then follows with {', '.join(supporting[:3])}.")
    if contextual:
        lines.append(
            f"Contextual signals ({', '.join(contextual[:3])}) remain comparison context."
        )
    filtered_suppressed = []
    for label in suppressed:
        label_text = str(label or "").strip()
        if "MEMORY" in label_text.upper():
            continue
        if label_text.lower() == "platform":
            filtered_suppressed.append("platform-level signals")
        else:
            filtered_suppressed.append(label_text)
    if filtered_suppressed:
        lines.append(
            "Lower-value or unsupported families were not promoted: "
            + ", ".join(filtered_suppressed[:4])
            + "."
        )
    return " ".join(lines)


def _build_historical_interpretation(
    normalized_decision: dict[str, Any],
    trend_summary: dict[str, Any],
    anomaly_summary: dict[str, Any],
    visual_story: dict[str, Any],
    visual_support: dict[str, bool],
) -> str:
    trend_text = _compact_narrative_caveat(
        trend_summary.get("summary"),
        normalized_decision.get("primary_issue"),
    )
    anomaly_count = int(_safe_float(anomaly_summary.get("count")) or 0.0)
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "The selected domain"
    card_statuses = _as_dict(visual_story.get("card_statuses"))
    contextual = [
        _clean_context_value(item.get("label"))
        for item in (visual_story.get("contextual_visual_proof") or [])
        if _clean_context_value(_as_dict(item).get("label"))
    ]
    parts = []
    if trend_text:
        if re.search(r"\bCPU\b", trend_text, flags=re.IGNORECASE):
            parts.append(
                "Primary evidence keeps the historical story CPU-led, supporting a compute-bound interpretation over I/O-, memory-, or topology-led alternatives."
            )
            parts.append("The pattern is directionally consistent, but intermittent rather than continuous.")
        else:
            parts.append(trend_text)
    if card_statuses.get("MEMORY") == "weak":
        parts.append(
            "Memory was reviewed and remains non-governing in this window."
        )
    elif card_statuses.get("MEMORY") == "ok":
        parts.append(
            "Memory is historically present, but it does not materially influence the dominant workload pattern."
        )
    if contextual:
        parts.append(
            "Contextual cluster and platform signals remain comparison context and do not alter the selected single-instance posture."
        )
    if not parts:
        parts.append(
            f"Historical interpretation stays anchored on {primary_issue} without overstating weaker or missing signals."
        )
    return " ".join(parts)


def _build_historical_action_explanation(
    normalized_decision: dict[str, Any],
    action_text: Any,
    recommendation_summary: dict[str, Any],
) -> str:
    posture = _clean_context_value(normalized_decision.get("decision_posture"))
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "the selected domain"
    if posture:
        return (
            f"The historical record aligns with {posture} because "
            f"{_issue_product_label(primary_issue)} remains the dominant constraint after supporting and contextual signals are considered."
        )
    return (
        f"Observed patterns remain consistent with the {_issue_product_label(primary_issue)}-led posture."
    )


def _recommendation_category_label(category: Any, action: Any) -> str:
    category_text = _clean_context_value(category)
    action_text = str(action or "").lower()
    if category_text and category_text.lower() not in {"deterministic", "supplemental"}:
        return category_text.replace("_", " ")
    if any(token in action_text for token in ("sql", "plan", "row-source", "execution")):
        return "execution-plan"
    if any(token in action_text for token in ("capacity", "cpu", "host capacity", "saturation")):
        return "capacity"
    if any(token in action_text for token in ("commit", "log file sync", "transaction")):
        return "commit behavior"
    if any(token in action_text for token in ("concurrency", "latch", "lock")):
        return "concurrency"
    if any(token in action_text for token in ("i/o", "io", "read", "access-path")):
        return "i/o"
    return category_text or "general"


def _dedupe_recommendation_cards(
    recommendation_cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for card in recommendation_cards:
        category = str(card.get("category_label") or card.get("category") or "").strip().lower()
        fingerprint = _recommendation_action_fingerprint(card.get("action"), category)
        if fingerprint in seen_keys:
            continue
        seen_keys.add(fingerprint)
        deduped.append(card)
    return _merge_cpu_recommendation_cards(deduped)


def _merge_cpu_recommendation_cards(
    recommendation_cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    capacity_index: int | None = None
    sql_index: int | None = None

    for index, card in enumerate(recommendation_cards):
        category = str(card.get("category_label") or card.get("category") or "").strip().lower()
        fingerprint = _recommendation_action_fingerprint(card.get("action"), category)
        issue_text = str(card.get("issue") or "").strip().lower()
        if fingerprint == "capacity-posture" and "cpu" in issue_text:
            capacity_index = index
        elif fingerprint == "sql-execution-optimization":
            sql_index = index

    if capacity_index is None or sql_index is None:
        return recommendation_cards

    merged = dict(recommendation_cards[capacity_index])
    merged["action"] = (
        "Reduce sustained CPU pressure by prioritizing high-load SQL and validating "
        "execution efficiency before scaling."
    )
    merged["rationale"] = (
        "CPU pressure is best reduced by tuning the highest-load SQL paths and validating "
        "execution efficiency before considering additional capacity."
    )

    return [
        merged if index == capacity_index else card
        for index, card in enumerate(recommendation_cards)
        if index != sql_index
    ]


def _tighten_recommendation_cards(
    recommendation_cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    tightened: list[dict[str, Any]] = []
    for card in recommendation_cards:
        updated = dict(card)
        action_text = str(updated.get("action") or "").strip()
        issue_text = str(updated.get("issue") or "").strip().lower()
        category_text = str(updated.get("category_label") or updated.get("category") or "").strip().lower()
        if action_text == "Tighten commit frequency and commit-processing behavior in the application flow.":
            updated["action"] = (
                "As a secondary optimization, review and tighten commit frequency and "
                "commit-processing behavior in the application flow."
            )
            if not _clean_context_value(updated.get("rationale")) or "execution-plan guidance" in str(updated.get("rationale") or "").lower():
                updated["rationale"] = (
                    "Secondary optimization after the dominant CPU and SQL actions."
                )
        elif "commit" in issue_text or "commit" in category_text:
            updated["rationale"] = (
                _clean_context_value(updated.get("rationale"))
                or "Secondary optimization after the dominant CPU and SQL actions."
            )
        tightened.append(updated)
    return tightened


def _recommendation_action_fingerprint(action: Any, category: str) -> str:
    action_text = str(action or "").strip().lower()
    if any(
        token in action_text
        for token in ("sql", "statement", "elapsed-time", "execution", "plan", "row-source")
    ):
        return "sql-execution-optimization"
    if category == "capacity":
        return "capacity-posture"
    if category == "commit behavior":
        return "commit-behavior"
    if category == "concurrency":
        return "concurrency-posture"
    if category == "i/o":
        return "io-access-path"
    normalized = re.sub(r"[^a-z0-9]+", " ", action_text)
    return " ".join(normalized.split()[:6]) or category or "general"


def _build_recommendation_groups(
    recommendation_cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    bucket_order = [
        "Immediate Actions",
        "SQL / Execution Plan Actions",
        "Transaction / Commit Actions",
        "Capacity / Scaling Actions",
        "Concurrency / Workload Actions",
        "I/O / Access Path Actions",
        "Additional Actions",
    ]
    grouped_cards: dict[str, list[dict[str, Any]]] = {bucket: [] for bucket in bucket_order}
    for card in recommendation_cards:
        bucket = _recommendation_bucket(card)
        grouped_cards[bucket].append(card)
    for bucket in bucket_order:
        items = grouped_cards[bucket]
        if not items:
            continue
        groups.append(
            {
                "title": bucket,
                "items": items,
            }
        )
    return groups


def _recommendation_bucket(card: dict[str, Any]) -> str:
    priority = str(card.get("priority") or "").strip().upper()
    category = str(card.get("category_label") or card.get("category") or "").strip().lower()
    if priority in {"CRITICAL", "HIGH"}:
        return "Immediate Actions"
    if category == "execution-plan":
        return "SQL / Execution Plan Actions"
    if category == "commit behavior":
        return "Transaction / Commit Actions"
    if category == "capacity":
        return "Capacity / Scaling Actions"
    if category == "concurrency":
        return "Concurrency / Workload Actions"
    if category == "i/o":
        return "I/O / Access Path Actions"
    return "Additional Actions"


def _build_sizing_guidance_blocks(
    oci_guidance: dict[str, Any],
    fallback_text: Any,
) -> list[dict[str, str]]:
    current_posture = _clean_context_value(oci_guidance.get("current_state_assessment"))
    scaling_trigger = _clean_context_value(oci_guidance.get("scaling_trigger_conditions"))
    architecture_guidance = _clean_context_value(oci_guidance.get("oci_architecture_guidance"))
    if current_posture:
        current_posture = (
            "The current evidence still supports tuning before scaling because the dominant pressure is internal to workload efficiency rather than a clear capacity shortfall."
        )
    if scaling_trigger:
        scaling_trigger = (
            "Scaling becomes appropriate only if CPU- and SQL-heavy inefficiencies have been reduced and the same governing constraint still remains afterward."
        )
    if architecture_guidance:
        architecture_guidance = (
            "Keep the architecture aligned to a compute-first tuning path so residual pressure can be re-evaluated cleanly before any broader capacity change."
        )
    blocks = [
        {
            "title": "Current Posture",
            "text": current_posture,
        },
        {
            "title": "When Scaling Becomes Appropriate",
            "text": scaling_trigger,
        },
        {
            "title": "Architectural Guidance",
            "text": architecture_guidance,
        },
    ]
    filtered = [block for block in blocks if block.get("text")]
    if filtered:
        return filtered
    text = _clean_context_value(fallback_text)
    return (
        [{"title": "Current Posture", "text": text}]
        if text
        else []
    )


def _build_historical_drift_summary(
    comparison_context: dict[str, Any],
    normalized_decision: dict[str, Any],
    anomaly_summary: dict[str, Any],
) -> str:
    latest_vs_trend = _compact_selector_summary(
        comparison_context.get("latest_vs_trend"),
        limit=180,
    )
    primary_issue = _clean_context_value(normalized_decision.get("primary_issue")) or "the selected domain"
    parts = [
        f"Period comparison should be read through the deterministic {primary_issue} posture."
    ]
    if latest_vs_trend:
        parts.append(latest_vs_trend)
    return " ".join(parts)


def _recommendation_issue_label(action_text: Any, default_issue: Any) -> str:
    action = str(action_text or "").strip().lower()
    default_label = _clean_context_value(default_issue) or "Action"
    if any(token in action for token in ("sql", "execution plan", "row-source", "statement")):
        return "SQL / execution path"
    if any(token in action for token in ("commit", "log file sync", "transaction")):
        return "Commit behavior"
    if any(token in action for token in ("read", "i/o", "access path", "physical")):
        return "I/O access path"
    if any(token in action for token in ("concurrency", "scheduling", "session")):
        return "Concurrency / workload shape"
    if any(token in action for token in ("capacity", "cpu", "host")):
        return "CPU / capacity posture"
    return default_label


def _clean_operating_system(value: Any) -> str | None:
    text = _clean_context_value(value)
    if not text:
        return None
    parsed = _parse_platform_capacity_metrics(text)
    os_name = parsed.get("os_name")
    if not os_name:
        return None
    os_name = re.sub(r"\bx86\s+64(?:-bit)?\b", "x86-64", os_name, flags=re.IGNORECASE)
    os_name = re.sub(r"\b64-bit\b", "x86-64", os_name, flags=re.IGNORECASE)
    os_name = re.sub(r"\s+", " ", os_name).strip()
    return os_name


def _clean_source_database(source_database: Any, dbid: Any) -> str | None:
    text = _clean_context_value(source_database)
    if not text:
        return _clean_context_value(dbid)
    text = re.split(r"\s*\|\s*DBID\b", text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    return text or _clean_context_value(dbid)


def _format_scope_label(
    db_name: Any,
    dbid: Any,
    fallback: Any = None,
) -> str | None:
    db_name_text = _clean_context_value(db_name)
    dbid_text = _clean_context_value(dbid)
    if db_name_text and dbid_text:
        return f"{db_name_text} / {dbid_text}"
    if db_name_text:
        return db_name_text
    if dbid_text:
        return dbid_text
    return _clean_context_value(fallback)


def _clean_database_role(value: Any) -> str | None:
    text = _clean_context_value(value)
    if not text or text.upper() == "UNKNOWN":
        return None
    return text


def _parse_platform_capacity_metrics(value: Any) -> dict[str, float | str | None]:
    text = _clean_context_value(value)
    if not text:
        return {
            "os_name": None,
            "cpu_count": None,
            "core_count": None,
            "socket_count": None,
            "memory_gb": None,
        }
    normalized = re.sub(r"\s+", " ", text).strip()
    match = re.search(
        r"^(?P<os>.+?)\s+(?P<cpu>\d+(?:\.\d+)?)\s+(?P<core>\d+(?:\.\d+)?)\s+"
        r"(?P<socket>\d+(?:\.\d+)?)\s+(?P<memory>\d+(?:\.\d+)?)$",
        normalized,
    )
    if not match:
        return {
            "os_name": normalized,
            "cpu_count": None,
            "core_count": None,
            "socket_count": None,
            "memory_gb": None,
        }
    return {
        "os_name": match.group("os"),
        "cpu_count": float(match.group("cpu")),
        "core_count": float(match.group("core")),
        "socket_count": float(match.group("socket")),
        "memory_gb": float(match.group("memory")),
    }


def _derive_display_ocpus_cores(
    current_value: Any,
    platform_metrics: dict[str, float | str | None],
    instance_count: Any,
    scope_stats: dict[str, int],
) -> str | None:
    current_text = _clean_context_value(current_value)
    if current_text and scope_stats.get("db_count", 0) <= 1:
        return current_text
    instance_multiplier = max(int(_safe_float(instance_count) or 1.0), 1)
    core_count = _safe_float(platform_metrics.get("core_count"))
    cpu_count = _safe_float(platform_metrics.get("cpu_count"))
    if core_count is not None and core_count > 0:
        total_cores = core_count * instance_multiplier
        return (
            f"{int(total_cores)} cores"
            if float(total_cores).is_integer()
            else f"{total_cores:.1f} cores"
        )
    if cpu_count is not None and cpu_count > 0:
        total_cpus = cpu_count * instance_multiplier
        return (
            f"{int(total_cpus)} CPUs"
            if float(total_cpus).is_integer()
            else f"{total_cpus:.1f} CPUs"
        )
    return None


def _derive_display_memory_per_instance(
    current_value: Any,
    platform_metrics: dict[str, float | str | None],
    scope_stats: dict[str, int],
) -> str | None:
    current_text = _clean_context_value(current_value)
    if current_text and scope_stats.get("db_count", 0) <= 1:
        return current_text
    memory_gb = _safe_float(platform_metrics.get("memory_gb"))
    if memory_gb is None or memory_gb <= 0:
        return None
    return (
        f"{int(memory_gb)} GB"
        if float(memory_gb).is_integer()
        else f"{memory_gb:.1f} GB"
    )


def _derive_display_platform(
    current_value: Any,
    feature_values: dict[str, float],
    scope_stats: dict[str, int],
    report_data: dict[str, Any] | None = None,
    selected_scope_only: bool = False,
) -> str | None:
    has_exadata_feature_evidence = _has_selected_scope_exadata_evidence(
        feature_values,
        report_data=report_data,
    )
    if has_exadata_feature_evidence:
        return "Exadata"
    current_text = _clean_context_value(current_value)
    if current_text and not selected_scope_only and scope_stats.get("db_count", 0) <= 1:
        return current_text
    return None


def _derive_display_topology(
    analysis_context: dict[str, Any],
    feature_values: dict[str, float],
    instance_count: Any,
    report_data: dict[str, Any] | None = None,
    selected_scope_only: bool = False,
) -> str | None:
    instance_total = int(_safe_float(instance_count) or 0.0)
    database_role = str(analysis_context.get("database_role") or "").strip().lower()
    if selected_scope_only:
        has_rac = _has_selected_scope_rac_evidence(
            feature_values,
            instance_total,
        )
        has_dataguard = _has_selected_scope_dataguard_evidence(
            feature_values,
            database_role,
        )
    else:
        has_rac = _has_historical_rac_support(
            report_data or {},
            feature_values,
            instance_total,
        )
        has_dataguard = _has_historical_dataguard_support(
            report_data or {},
            feature_values,
            database_role,
        )
    labels: list[str] = []
    if has_rac:
        labels.append("RAC")
    if has_dataguard:
        labels.append("Data Guard")
    if not labels:
        return "Single Instance"
    return ", ".join(labels)


def _has_selected_scope_rac_evidence(
    feature_values: dict[str, float],
    instance_total: int,
) -> bool:
    if instance_total > 1:
        return True
    return any(
        (_safe_float(feature_values.get(metric_name)) or 0.0) > 0.0
        for metric_name in (
            "CLUSTER_WAIT_PCT_DB_TIME",
            "GC_CR_WAIT_PCT_DB_TIME",
            "GC_CURRENT_WAIT_PCT_DB_TIME",
            "GC_BUFFER_BUSY_PCT_DB_TIME",
        )
    )


def _has_selected_scope_dataguard_evidence(
    feature_values: dict[str, float],
    database_role: str,
) -> bool:
    if any(token in database_role for token in ("standby", "far sync")):
        return True
    return any(
        (_safe_float(feature_values.get(metric_name)) or 0.0) > 0.0
        for metric_name in ("TRANSPORT_LAG_SEC", "APPLY_LAG_SEC")
    )


def _has_selected_scope_exadata_evidence(
    feature_values: dict[str, float],
    report_data: dict[str, Any] | None = None,
) -> bool:
    exadata_metrics = (
        "CELL_SINGLE_BLOCK_READ_PCT_DB_TIME",
        "CELL_SINGLE_BLOCK_LATENCY_MS",
        "SMART_SCAN_PCT_DB_TIME",
        "EXA_CELL_IO_PCT_DB_TIME",
    )
    if any(
        (_safe_float(feature_values.get(metric_name)) or 0.0) > 0.0
        for metric_name in exadata_metrics
    ):
        return True
    report_data = report_data or {}
    time_series = _as_dict(report_data.get("time_series_charts"))
    violin_panel = _as_dict(report_data.get("violin_panel"))
    platform_violin = _as_dict(violin_panel.get("platform"))
    return any(
        _has_numeric_samples(time_series.get(series_key), minimum=2)
        for series_key in ("exa_cell_io_trend", "exa_offload_efficiency_trend")
    ) or any(
        _has_numeric_samples(platform_violin.get(series_key), minimum=2)
        for series_key in (
            "cell_single_block_read_pct_db_time",
            "smart_scan_pct_db_time",
        )
    )


def _has_historical_rac_support(
    report_data: dict[str, Any],
    feature_values: dict[str, float],
    instance_total: int,
) -> bool:
    if _has_selected_scope_rac_evidence(feature_values, instance_total):
        return True
    time_series = _as_dict(report_data.get("time_series_charts"))
    violin_panel = _as_dict(report_data.get("violin_panel"))
    topology_violin = _as_dict(violin_panel.get("topology"))
    anomalies = _as_dict(report_data.get("anomalies"))
    anomaly_windows = list(anomalies.get("windows") or report_data.get("anomaly_windows") or [])
    return any(
        _has_numeric_samples(time_series.get(series_key), minimum=2)
        for series_key in ("cluster_wait_trend", "gc_wait_trend")
    ) or any(
        _has_numeric_samples(topology_violin.get(series_key), minimum=2)
        for series_key in (
            "cluster_wait_pct_db_time",
            "gc_current_wait_pct_db_time",
            "gc_cr_wait_pct_db_time",
        )
    ) or any(
        "interconnect stress" in str(_as_dict(window).get("metric") or "").lower()
        for window in anomaly_windows
    )


def _has_historical_dataguard_support(
    report_data: dict[str, Any],
    feature_values: dict[str, float],
    database_role: str,
) -> bool:
    if _has_selected_scope_dataguard_evidence(feature_values, database_role):
        return True
    time_series = _as_dict(report_data.get("time_series_charts"))
    violin_panel = _as_dict(report_data.get("violin_panel"))
    topology_violin = _as_dict(violin_panel.get("topology"))
    anomalies = _as_dict(report_data.get("anomalies"))
    anomaly_windows = list(anomalies.get("windows") or report_data.get("anomaly_windows") or [])
    return any(
        _has_numeric_samples(time_series.get(series_key), minimum=2)
        for series_key in ("dg_transport_lag_trend", "dg_apply_lag_trend")
    ) or any(
        _has_numeric_samples(topology_violin.get(series_key), minimum=2)
        for series_key in ("transport_lag_sec", "apply_lag_sec")
    ) or any(
        "transport lag" in str(_as_dict(window).get("metric") or "").lower()
        or "apply lag" in str(_as_dict(window).get("metric") or "").lower()
        for window in anomaly_windows
    )


def _build_historical_topology_platform_review(
    analysis_context: dict[str, Any],
    report_data: dict[str, Any],
    feature_values: dict[str, float],
    instance_count: Any,
) -> dict[str, str | None]:
    instance_total = int(_safe_float(instance_count) or 0.0)
    database_role = str(analysis_context.get("database_role") or "").strip().lower()
    time_series = _as_dict(report_data.get("time_series_charts"))
    violin_panel = _as_dict(report_data.get("violin_panel"))
    topology_violin = _as_dict(violin_panel.get("topology"))

    rac_supported = _has_historical_rac_support(
        report_data,
        feature_values,
        instance_total,
    )
    dataguard_supported = _has_historical_dataguard_support(
        report_data,
        feature_values,
        database_role,
    )
    exadata_supported = _has_selected_scope_exadata_evidence(
        feature_values,
        report_data=report_data,
    )

    cluster_sample_count = max(
        sum(1 for value in (time_series.get("cluster_wait_trend") or []) if _safe_float(value) is not None),
        sum(1 for value in (topology_violin.get("cluster_wait_pct_db_time") or []) if _safe_float(value) is not None),
    )
    dg_sample_count = max(
        sum(1 for value in (time_series.get("dg_transport_lag_trend") or []) if _safe_float(value) is not None),
        sum(1 for value in (topology_violin.get("transport_lag_sec") or []) if _safe_float(value) is not None),
        sum(1 for value in (topology_violin.get("apply_lag_sec") or []) if _safe_float(value) is not None),
    )

    rac_summary = None
    if rac_supported:
        if cluster_sample_count < 3 and instance_total <= 1:
            rac_summary = (
                "Historical window contains sparse cluster-wait and GC samples. "
                "Treat RAC coordination as supportive context rather than selected-scope topology truth."
            )
        else:
            rac_summary = (
                "Historical window contains repeated cluster-wait or GC evidence, "
                "so RAC coordination remains part of the supporting comparison context."
            )

    data_guard_summary = None
    if dataguard_supported:
        if dg_sample_count < 3 and not any(token in database_role for token in ("standby", "far sync")):
            data_guard_summary = (
                "Historical window contains limited transport/apply lag evidence. "
                "Treat Data Guard as supportive window context rather than selected-scope topology truth."
            )
        else:
            data_guard_summary = (
                "Historical window contains explicit transport/apply lag evidence, "
                "so Data Guard remains part of the supporting comparison context."
            )

    exadata_summary = (
        "Historical window contains real Exadata-specific cell or offload evidence."
        if exadata_supported
        else None
    )

    return {
        "rac_summary": rac_summary,
        "data_guard_summary": data_guard_summary,
        "exadata_summary": exadata_summary,
    }


def _build_analysis_health_check(
    canonical_payload: dict[str, Any],
    report_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact deterministic health check from canonical evidence."""

    report_data = report_data or {}
    metadata = _as_dict(canonical_payload.get("metadata"))
    decision = _as_dict(canonical_payload.get("decision"))
    scores = _as_dict(canonical_payload.get("scores"))
    trends = _as_dict(canonical_payload.get("trends"))
    anomalies = _as_dict(canonical_payload.get("anomalies"))
    grouped_findings = _as_dict(canonical_payload.get("grouped_deterministic_findings"))
    decision_evidence = _as_dict(decision.get("evidence"))
    domain_scores = _as_dict(scores.get("domain_scores")) or _as_dict(
        decision_evidence.get("domain_scores")
    )
    feature_values = _flatten_domain_feature_values(
        decision_evidence.get("feature_evidence")
    )
    primary_evidence = _as_dict(grouped_findings.get("primary_evidence"))
    anomaly_count = int(anomalies.get("count") or 0)
    trend_findings = list(trends.get("findings") or [])
    rows = [
        _domain_health_row(
            "CPU",
            "CPU",
            domain_scores,
            feature_values,
            ("DB_CPU_PCT_DB_TIME", "CPU_UTIL_P95", "CPU_UTIL_AVG"),
        ),
        _domain_health_row(
            "I/O",
            "IO",
            domain_scores,
            feature_values,
            ("READ_LATENCY_MS", "USER_IO_PRESSURE"),
        ),
        _domain_health_row(
            "MEMORY",
            "MEMORY",
            domain_scores,
            feature_values,
            ("PGA_SPILL_PRESSURE", "TEMP_IO_PRESSURE"),
        ),
        _domain_health_row(
            "COMMIT",
            "COMMIT",
            domain_scores,
            feature_values,
            ("LOG_FILE_SYNC_MS", "COMMIT_PRESSURE"),
        ),
        _domain_health_row(
            "RAC",
            "RAC",
            domain_scores,
            feature_values,
            ("CLUSTER_WAIT_PCT_DB_TIME",),
            not_applicable_when_missing=True,
        ),
        _domain_health_row(
            "ADG",
            "ADG",
            domain_scores,
            feature_values,
            ("TRANSPORT_LAG_SEC", "APPLY_LAG_SEC"),
            not_applicable_when_missing=True,
        ),
        _sql_concentration_health_row(feature_values),
        _trend_stability_health_row(trend_findings),
        _anomaly_burden_health_row(anomaly_count),
        _data_completeness_health_row(
            metadata,
            primary_evidence,
            report_data=report_data,
        ),
    ]
    rows = _align_health_check_rows(
        rows,
        primary_issue=str(decision.get("primary_issue") or ""),
        anomaly_count=anomaly_count,
    )
    summary_status = "PASS"
    if any(row["status"] == "FAIL" for row in rows):
        summary_status = "FAIL"
    elif any(row["status"] == "MARGINAL" for row in rows):
        summary_status = "MARGINAL"
    elif all(row["status"] == "N/A" for row in rows):
        summary_status = "N/A"
    fail_checks = [str(row.get("check") or "") for row in rows if row.get("status") == "FAIL"]
    summary_reason = None
    if summary_status == "FAIL" and fail_checks:
        if set(fail_checks) == {"Anomaly burden"}:
            summary_reason = (
                "Overall FAIL is driven by anomaly burden across the selected window, "
                "while domain pressure remains mixed rather than uniformly critical."
            )
        else:
            summary_reason = "Overall FAIL reflects the highest-severity deterministic checks on this page."
    return {
        "summary_status": summary_status,
        "summary_reason": summary_reason,
        "rows": rows,
    }


def _align_health_check_rows(
    rows: list[dict[str, Any]],
    primary_issue: str,
    anomaly_count: int,
) -> list[dict[str, Any]]:
    domain_checks = {"CPU", "I/O", "MEMORY", "COMMIT", "RAC", "ADG"}
    if any(str(row.get("check") or "") in domain_checks and row.get("status") == "FAIL" for row in rows):
        return rows
    if anomaly_count < 2:
        return rows
    primary_check = {
        "CPU": "CPU",
        "IO": "I/O",
        "I/O": "I/O",
        "MEMORY": "MEMORY",
        "COMMIT": "COMMIT",
        "RAC": "RAC",
        "ADG": "ADG",
    }.get(str(primary_issue or "").upper())
    if not primary_check:
        return rows
    aligned_rows: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("check") or "") != primary_check:
            aligned_rows.append(row)
            continue
        current_status = str(row.get("status") or "N/A").upper()
        if current_status == "PASS":
            aligned_rows.append(
                {
                    **row,
                    "status": "MARGINAL",
                    "reason": (
                        "Anomaly burden materially affects the primary domain, "
                        "so this row is shown as mixed rather than fully PASS."
                    ),
                }
            )
        else:
            aligned_rows.append(row)
    return aligned_rows


def _build_normalized_display_decision(
    canonical_payload: dict[str, Any],
    report_data: dict[str, Any] | None = None,
    health_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize cross-screen decision fields for consistent presentation.

    Display posture is normalized for presentation consistency only. The
    deterministic source findings remain authoritative; raw domain scores should
    not surface in ways that contradict the selected primary issue.
    """

    report_data = report_data or {}
    health_check = health_check or {}
    decision = _as_dict(canonical_payload.get("decision"))
    scores = _as_dict(canonical_payload.get("scores"))
    anomalies = _as_dict(canonical_payload.get("anomalies"))
    grouped_findings = _as_dict(canonical_payload.get("grouped_deterministic_findings"))
    decision_evidence = _as_dict(decision.get("evidence"))
    feature_values = _flatten_domain_feature_values(
        decision_evidence.get("feature_evidence")
    )
    decision_posture = _as_dict(report_data.get("decision_posture"))
    raw_domain_scores = _as_dict(scores.get("domain_scores"))
    primary_issue = decision.get("primary_issue")
    normalized_domain_scores = _normalize_domain_scores(
        raw_domain_scores,
        primary_issue=primary_issue,
        severity_score=decision.get("severity_score"),
        feature_values=feature_values,
        primary_evidence=_as_dict(grouped_findings.get("primary_evidence")),
    )
    overall_status = str(decision.get("overall_status") or "OK").upper()
    anomaly_count = int(anomalies.get("count") or 0)
    health_summary = str(health_check.get("summary_status") or "N/A").upper()
    if overall_status == "OK" and (
        anomaly_count >= 2 or health_summary in {"FAIL", "MARGINAL"}
    ):
        overall_status = "WARNING"
    severity_score = _safe_float(decision.get("severity_score")) or 0.0
    if overall_status == "CRITICAL" and severity_score < 0.85:
        severity_score = 0.85
    elif overall_status == "WARNING" and severity_score < 0.4:
        severity_score = 0.4
    primary_issue_display_score = normalized_domain_scores.get(str(primary_issue or ""))
    return {
        "primary_issue": primary_issue,
        "secondary_issues": list(decision.get("secondary_issues") or []),
        "overall_status": overall_status,
        "severity_score": severity_score,
        "display_severity_label": _display_severity_label(overall_status, severity_score),
        "decision_posture": decision_posture.get("posture"),
        "confidence": decision.get("confidence"),
        "health_summary": health_summary,
        "historical_posture": decision_posture.get("posture"),
        "domain_scores": normalized_domain_scores,
        "primary_issue_display_score": primary_issue_display_score,
        "recommendation_priority": _display_priority_from_decision(
            overall_status,
            severity_score,
            health_summary,
        ),
    }


def _flatten_domain_feature_values(raw_feature_evidence: Any) -> dict[str, float]:
    flattened: dict[str, float] = {}
    if not isinstance(raw_feature_evidence, dict):
        return flattened
    for domain_metrics in raw_feature_evidence.values():
        metrics = _as_dict(domain_metrics)
        for metric_name, metric_value in metrics.items():
            numeric_value = _safe_float(metric_value)
            if numeric_value is None:
                continue
            flattened[str(metric_name)] = numeric_value
    return flattened


def _normalize_domain_scores(
    domain_scores: dict[str, Any],
    primary_issue: Any,
    severity_score: Any,
    feature_values: dict[str, float],
    primary_evidence: dict[str, Any],
) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for domain, score in domain_scores.items():
        numeric_score = _safe_float(score)
        if numeric_score is None:
            continue
        normalized[str(domain)] = numeric_score
    primary_issue_key = str(primary_issue or "").strip()
    if primary_issue_key and normalized.get(primary_issue_key, 0.0) <= 0.0:
        evidence_score = _safe_float(primary_evidence.get("score"))
        inferred_score = _infer_display_score_from_features(
            primary_issue_key,
            feature_values,
        )
        severity_floor = _display_score_floor_for_severity(
            _safe_float(severity_score),
        )
        normalized[primary_issue_key] = max(
            score
            for score in (
                evidence_score,
                inferred_score,
                severity_floor,
                0.4,
            )
            if score is not None
        )
    return normalized


def _domain_health_row(
    check: str,
    domain: str,
    domain_scores: dict[str, Any],
    feature_values: dict[str, float],
    observed_metric_names: tuple[str, ...],
    not_applicable_when_missing: bool = False,
) -> dict[str, Any]:
    score = _safe_float(domain_scores.get(domain))
    observed_label = None
    observed_value = None
    for metric_name in observed_metric_names:
        metric_value = _safe_float(feature_values.get(metric_name))
        if metric_value is None:
            continue
        observed_label = metric_name
        observed_value = metric_value
        break
    if score is None and observed_value is None and not_applicable_when_missing:
        return {
            "check": check,
            "observed_value": "No topology evidence",
            "status": "N/A",
            "reason": f"{check} is not materially present in the current deterministic evidence.",
        }
    score_status = _status_for_domain_score(score)
    observed_status = _status_from_observed_metric(
        domain,
        feature_values,
        observed_metric_names,
    )
    status = _max_status(score_status, observed_status)
    if score is None and observed_value is None:
        status = "PASS"
    observed_text = (
        f"{_metric_display_label(observed_label)}: {_format_metric_value(observed_value)}"
        if observed_label is not None and observed_value is not None
        else "No material signal observed"
    )
    if observed_status == "FAIL":
        score_text = (
            "Observed deterministic evidence indicates elevated pressure for this domain."
        )
    elif observed_status == "MARGINAL":
        score_text = (
            "Observed deterministic evidence indicates moderate pressure for this domain."
        )
    elif score is not None and score > 0.0:
        score_text = (
            "Decision contribution is present and aligns with the observed evidence."
        )
    else:
        score_text = "No material deterministic pressure was identified for this domain."
    return {
        "check": check,
        "observed_value": observed_text,
        "status": status,
        "reason": score_text,
    }


def _sql_concentration_health_row(feature_values: dict[str, float]) -> dict[str, Any]:
    sql_concentration = _safe_float(feature_values.get("TOP_SQL_LOAD_CONCENTRATION"))
    if sql_concentration is None:
        return {
            "check": "SQL concentration",
            "observed_value": "Not evaluated",
            "status": "N/A",
            "reason": "Excluded from deterministic health scoring for this selected scope.",
        }
    if sql_concentration >= 30.0:
        status = "FAIL"
    elif sql_concentration >= 15.0:
        status = "MARGINAL"
    else:
        status = "PASS"
    return {
        "check": "SQL concentration",
        "observed_value": f"{_metric_display_label('TOP_SQL_LOAD_CONCENTRATION')}: {_format_metric_value(sql_concentration)}",
        "status": status,
        "reason": "Top SQL concentration is derived directly from the current feature evidence.",
    }


def _trend_stability_health_row(trend_findings: list[Any]) -> dict[str, Any]:
    findings = [str(item).strip() for item in trend_findings if str(item).strip()]
    if not findings:
        return {
            "check": "Trend stability",
            "observed_value": "No trend findings",
            "status": "N/A",
            "reason": "No deterministic multi-interval trend findings were available.",
        }
    volatile_findings = [
        finding
        for finding in findings
        if any(
            token in finding.lower()
            for token in ("rising", "increase", "accelerat", "volatile", "spike")
        )
    ]
    if len(volatile_findings) >= 2:
        status = "FAIL"
    elif volatile_findings:
        status = "MARGINAL"
    else:
        status = "PASS"
    return {
        "check": "Trend stability",
        "observed_value": f"{len(findings)} trend finding(s)",
        "status": status,
        "reason": (
            "Historical support is present, but trend evidence is not uniformly strong across all domains."
            if re.search(
                r"cpu remained historically visible|cpu pressure had insufficient history|continuity across the full window was too mixed",
                findings[0],
                flags=re.IGNORECASE,
            )
            else findings[0]
        ),
    }


def _anomaly_burden_health_row(anomaly_count: int) -> dict[str, Any]:
    if anomaly_count >= 3:
        status = "FAIL"
    elif anomaly_count >= 1:
        status = "MARGINAL"
    else:
        status = "PASS"
    return {
        "check": "Anomaly burden",
        "observed_value": f"{anomaly_count} anomaly window(s)",
        "status": status,
        "reason": "Anomaly burden summarizes the current deterministic anomaly window count.",
    }


def _data_completeness_health_row(
    metadata: dict[str, Any],
    primary_evidence: dict[str, Any],
    report_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report_data = report_data or {}
    analysis_context = _as_dict(report_data.get("analysis_context"))
    checks = [
        bool(metadata.get("db_name")),
        bool(metadata.get("dbid")),
        bool(metadata.get("snapshot_begin")),
        bool(metadata.get("snapshot_end")),
        bool(primary_evidence.get("feature_values")),
        bool(analysis_context.get("source_database")),
    ]
    present_count = sum(1 for item in checks if item)
    if present_count >= 5:
        status = "PASS"
    elif present_count >= 3:
        status = "MARGINAL"
    else:
        status = "FAIL"
    return {
        "check": "Data completeness",
        "observed_value": f"{present_count}/{len(checks)} completeness signals present",
        "status": status,
        "reason": "Completeness reflects whether core metadata and deterministic evidence are available.",
    }


def _status_for_domain_score(score: float | None) -> str:
    if score is None:
        return "N/A"
    if score >= 0.7:
        return "FAIL"
    if score >= 0.4:
        return "MARGINAL"
    return "PASS"


def _status_from_observed_metric(
    domain: str,
    feature_values: dict[str, float],
    observed_metric_names: tuple[str, ...],
) -> str:
    observed_status = "N/A"
    for metric_name in observed_metric_names:
        metric_value = _safe_float(feature_values.get(metric_name))
        if metric_value is None:
            continue
        threshold_status = _status_for_metric_threshold(domain, metric_name, metric_value)
        observed_status = _max_status(observed_status, threshold_status)
    return observed_status


def _status_for_metric_threshold(domain: str, metric_name: str, value: float) -> str:
    metric_key = metric_name.upper()
    domain_key = domain.upper()
    threshold_map: dict[str, tuple[float, float]] = {
        "DB_CPU_PCT_DB_TIME": (35.0, 65.0),
        "CPU_UTIL_P95": (35.0, 65.0),
        "CPU_UTIL_AVG": (35.0, 65.0),
        "READ_LATENCY_MS": (10.0, 20.0),
        "USER_IO_PRESSURE": (25.0, 50.0),
        "PGA_SPILL_PRESSURE": (10.0, 25.0),
        "TEMP_IO_PRESSURE": (10.0, 25.0),
        "LOG_FILE_SYNC_MS": (3.0, 8.0),
        "COMMIT_PRESSURE": (10.0, 30.0),
        "CLUSTER_WAIT_PCT_DB_TIME": (5.0, 20.0),
        "TRANSPORT_LAG_SEC": (0.1, 60.0),
        "APPLY_LAG_SEC": (0.1, 60.0),
    }
    marginal_threshold, fail_threshold = threshold_map.get(metric_key, (None, None))
    if marginal_threshold is None or fail_threshold is None:
        if domain_key == "ADG":
            marginal_threshold, fail_threshold = (0.1, 60.0)
        else:
            return "N/A"
    if value >= fail_threshold:
        return "FAIL"
    if value >= marginal_threshold:
        return "MARGINAL"
    return "PASS"


def _max_status(left: str, right: str) -> str:
    return left if _status_rank(left) >= _status_rank(right) else right


def _status_rank(status: str) -> int:
    return {
        "N/A": 0,
        "PASS": 1,
        "MARGINAL": 2,
        "FAIL": 3,
    }.get(str(status or "N/A").upper(), 0)


def _display_score_floor_for_severity(severity_score: float | None) -> float | None:
    if severity_score is None:
        return None
    if severity_score >= 0.85:
        return 0.85
    if severity_score >= 0.7:
        return 0.71
    if severity_score >= 0.4:
        return 0.55
    return 0.4


def _infer_display_score_from_features(
    primary_issue: str,
    feature_values: dict[str, float],
) -> float | None:
    issue_key = str(primary_issue or "").upper()
    if issue_key == "CPU":
        cpu = max(
            _safe_float(feature_values.get("DB_CPU_PCT_DB_TIME")) or 0.0,
            _safe_float(feature_values.get("CPU_UTIL_P95")) or 0.0,
        )
        if cpu >= 65.0:
            return 0.85
        if cpu >= 35.0:
            return 0.55
    if issue_key == "IO":
        latency = _safe_float(feature_values.get("READ_LATENCY_MS")) or 0.0
        if latency >= 20.0:
            return 0.85
        if latency >= 10.0:
            return 0.55
    if issue_key == "COMMIT":
        commit_latency = _safe_float(feature_values.get("LOG_FILE_SYNC_MS")) or 0.0
        if commit_latency >= 8.0:
            return 0.85
        if commit_latency >= 3.0:
            return 0.55
    if issue_key == "RAC":
        cluster_wait = _safe_float(feature_values.get("CLUSTER_WAIT_PCT_DB_TIME")) or 0.0
        if cluster_wait >= 20.0:
            return 0.85
        if cluster_wait >= 5.0:
            return 0.55
    return None


def _display_severity_label(overall_status: str, severity_score: float) -> str:
    normalized_status = str(overall_status or "OK").upper()
    if normalized_status == "CRITICAL" or severity_score >= 0.85:
        return "CRITICAL"
    if normalized_status == "WARNING" or severity_score >= 0.4:
        return "WARNING"
    return "OK"


def _display_priority_from_decision(
    overall_status: str,
    severity_score: float,
    health_summary: str,
) -> str:
    normalized_status = str(overall_status or "OK").upper()
    normalized_health = str(health_summary or "N/A").upper()
    if normalized_status == "CRITICAL" or severity_score >= 0.85:
        return "CRITICAL"
    if (
        normalized_status == "WARNING"
        or severity_score >= 0.55
        or normalized_health in {"FAIL", "MARGINAL"}
    ):
        return "HIGH"
    if severity_score >= 0.4:
        return "MEDIUM"
    return "LOW"


def _normalize_display_priority(
    recommendation_priority: Any,
    normalized_decision: dict[str, Any],
) -> str:
    current = str(recommendation_priority or "").upper()
    fallback = _display_priority_from_decision(
        str(normalized_decision.get("overall_status") or "OK"),
        _safe_float(normalized_decision.get("severity_score")) or 0.0,
        str(normalized_decision.get("health_summary") or "N/A"),
    )
    if _priority_sort_key(current) >= _priority_sort_key(fallback):
        return current or fallback
    return fallback


def _priority_sort_key(priority: Any) -> int:
    return {
        "LOW": 1,
        "MEDIUM": 2,
        "HIGH": 3,
        "CRITICAL": 4,
    }.get(str(priority or "LOW").upper(), 1)


def _filter_matching_findings(
    trend_findings: list[Any],
    anomaly_windows: list[dict[str, Any]],
    tokens: tuple[str, ...],
) -> list[str]:
    matches: list[str] = []
    lower_tokens = tuple(token.lower() for token in tokens)
    for finding in trend_findings:
        text = str(finding or "").strip()
        if text and any(token in text.lower() for token in lower_tokens):
            matches.append(text)
    for anomaly in anomaly_windows:
        reason = str(_as_dict(anomaly).get("reason") or "").strip()
        if reason and any(token in reason.lower() for token in lower_tokens):
            matches.append(reason)
    deduped: list[str] = []
    seen: set[str] = set()
    for item in matches:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _format_metric_value(value: Any) -> str:
    numeric_value = _safe_float(value)
    if numeric_value is None:
        return "Limited signal available"
    if abs(numeric_value) >= 100:
        return f"{numeric_value:.0f}"
    if abs(numeric_value) >= 10:
        return f"{numeric_value:.1f}"
    return f"{numeric_value:.3f}".rstrip("0").rstrip(".")


def _flatten_feature_evidence(raw_feature_evidence: Any) -> dict[str, float]:
    flattened: dict[str, float] = {}
    if not isinstance(raw_feature_evidence, dict):
        return flattened
    for domain in raw_feature_evidence:
        metrics = raw_feature_evidence.get(domain)
        if not isinstance(metrics, dict):
            continue
        for metric_name, metric_value in metrics.items():
            numeric_value = _safe_float(metric_value)
            if numeric_value is None:
                continue
            flattened[str(metric_name)] = numeric_value
    return flattened


def _metric_display_label(metric_name: Any) -> str:
    labels = {
        "DB_CPU_PCT_DB_TIME": "DB CPU % DB Time",
        "CPU_UTIL_P95": "CPU Util P95",
        "CPU_UTIL_AVG": "CPU Util Avg",
        "READ_LATENCY_MS": "Read Latency (ms)",
        "USER_IO_PRESSURE": "User I/O Pressure",
        "PGA_SPILL_PRESSURE": "PGA Spill Pressure",
        "TEMP_IO_PRESSURE": "Temp I/O Pressure",
        "LOG_FILE_SYNC_MS": "Log File Sync (ms)",
        "COMMIT_PRESSURE": "Commit Pressure",
        "CLUSTER_WAIT_PCT_DB_TIME": "Cluster Wait % DB Time",
        "TRANSPORT_LAG_SEC": "Transport Lag (sec)",
        "APPLY_LAG_SEC": "Apply Lag (sec)",
        "TOP_SQL_LOAD_CONCENTRATION": "Top SQL Concentration",
    }
    return labels.get(str(metric_name or "").upper(), str(metric_name or "Metric"))


def _flatten_anomalies(raw_anomaly_evidence: Any) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    if not isinstance(raw_anomaly_evidence, dict):
        return anomalies
    for domain, entries in raw_anomaly_evidence.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            anomaly = dict(entry)
            anomaly["issue"] = domain
            anomalies.append(anomaly)
    return anomalies


def _safe_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    return {}


def _has_non_empty_mapping(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return any(bool(item) for item in value.values())


def _format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    value_utc = value.astimezone(timezone.utc)
    return value_utc.isoformat(timespec="seconds").replace("+00:00", "Z")
