"""Deterministic display helpers for AI provider, model, and learning metadata."""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from copy import deepcopy
from typing import Any


LEARNING_VISIBILITY_SAFETY_LABELS = (
    "Read-only",
    "Human review required",
    "runtime_influence=false",
    "requires_human_review=true",
    "Not diagnostic evidence",
    "Not recommendation truth",
    "Not automatically applied",
    "Approved for implementation only, not runtime activation",
    "Semantic context is reviewer-assist only",
)

LEARNING_EMPTY_STATE_MESSAGES = (
    "No learning candidates available",
    "Learning visibility is read-only",
    "No runtime influence",
)

ML_EXPLAINABILITY_VISIBILITY_SAFETY_LABELS = (
    "Read-only",
    "Advisory / shadow only",
    "Not diagnostic evidence",
    "Not recommendation truth",
    "Deterministic runtime remains authoritative",
    "runtime_active=false",
    "runtime_influence=false",
    "runtime_influence_granted=false",
    "runtime_eligibility_granted=false",
    "No runtime activation",
    "No backend writes",
    "No approval controls",
    "No rollback execution",
)

ML_EXPLAINABILITY_EMPTY_STATE_MESSAGES = (
    "No ML/adaptive visibility payload supplied",
    "ML/adaptive visibility is read-only",
    "Deterministic runtime remains authoritative",
    "No runtime activation",
)

_CANDIDATE_STATUS_ORDER = {
    "PROPOSED": 0,
    "UNDER_REVIEW": 1,
    "NEEDS_REVISION": 2,
    "APPROVED_FOR_IMPLEMENTATION": 3,
    "IMPLEMENTED": 4,
    "VALIDATED": 5,
    "REJECTED": 6,
    "CLOSED": 7,
}


def format_ai_provider_display_name(provider: Any) -> str:
    """Return the human-facing provider name without changing runtime routing."""

    normalized = str(provider or os.getenv("AI_PROVIDER") or "").strip().lower()
    if normalized == "oci":
        return "OCI Generative AI"
    if normalized == "openai":
        return "OpenAI"
    return str(provider or "LLM provider not available").strip()


def format_ai_model_display_name(
    provider: Any,
    raw_model: Any,
    alias: str | None = None,
) -> str:
    """Return the human-facing model name without changing backend identifiers."""

    configured_model = _runtime_model_config_value(provider, raw_model)
    return _format_model_display_name(configured_model, alias=alias)


def build_learning_visibility_metadata(
    learning_visibility: Any | None = None,
    *,
    candidates: Iterable[Any] | None = None,
    governance_records: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Build read-only Phase 7G dashboard metadata from optional local records.

    The helper accepts dictionaries, dataclasses, and objects with ``to_dict`` or
    ``model_dump`` methods without importing learning modules. It only prepares
    display metadata and never approves, applies, activates, or persists records.
    """

    source = _object_to_mapping(learning_visibility)
    candidate_records = _record_list(
        candidates
        if candidates is not None
        else _first_present(
            source.get("candidates"),
            source.get("learning_candidates"),
            source.get("candidate_records"),
        )
    )
    governance_source = source.get("governance")
    governance_mapping = _object_to_mapping(governance_source)
    governance_record_values = _record_list(
        governance_records
        if governance_records is not None
        else _first_present(
            source.get("governance_records"),
            source.get("governance_decisions"),
            source.get("learning_governance"),
            governance_mapping.get("records"),
            governance_mapping.get("decisions"),
        )
    )

    normalized_candidates = sorted(
        (_normalize_learning_candidate(record) for record in candidate_records),
        key=_learning_candidate_sort_key,
    )
    normalized_governance = sorted(
        (_normalize_learning_governance_record(record) for record in governance_record_values),
        key=_learning_governance_sort_key,
    )

    return {
        "title": "Learning Visibility",
        "read_only": True,
        "runtime_influence": False,
        "requires_human_review": True,
        "diagnostic_evidence": False,
        "recommendation_truth": False,
        "automatically_applied": False,
        "approved_for_implementation_only": True,
        "semantic_context_reviewer_assist_only": True,
        "safety_labels": list(LEARNING_VISIBILITY_SAFETY_LABELS),
        "empty_state_messages": list(LEARNING_EMPTY_STATE_MESSAGES),
        "candidate_count": len(normalized_candidates),
        "status_counts": _count_by_key(normalized_candidates, "status"),
        "type_counts": _count_by_key(normalized_candidates, "candidate_type"),
        "affected_component_counts": _count_by_key(
            normalized_candidates,
            "affected_component",
        ),
        "affected_domain_counts": _count_by_key(normalized_candidates, "affected_domain"),
        "semantic_context_count": sum(
            1 for candidate in normalized_candidates if candidate["semantic_context_present"]
        ),
        "candidates": normalized_candidates,
        "governance": {
            "records": normalized_governance,
            "status_counts": _count_by_key(normalized_governance, "status"),
            "runtime_influence": False,
            "approved_for_implementation_only": True,
        },
    }


def build_ml_explainability_visibility_metadata(
    *,
    explanations: Iterable[Any] | None = None,
    model_registry_entries: Iterable[Any] | None = None,
    shadow_ml_outputs: Iterable[Any] | None = None,
    trend_aware_results: Iterable[Any] | None = None,
    adaptive_runtime_context: Any | None = None,
    gate_results: Iterable[Any] | None = None,
    scoring_integration_results: Iterable[Any] | None = None,
    recommendation_integration_results: Iterable[Any] | None = None,
    parser_integration_results: Iterable[Any] | None = None,
    fallback_decisions: Iterable[Any] | None = None,
    readiness_summary: Any | None = None,
) -> dict[str, Any]:
    """Build read-only Phase 7AB ML/adaptive dashboard metadata.

    This helper accepts local dictionaries, dataclasses, and simple objects. It
    prepares display metadata only; it does not import runtime parser/scoring
    modules, call services, approve models, execute rollback, or mutate state.
    """

    explanation_rows = [_normalize_ml_explanation(record) for record in _record_list(explanations)]
    feature_rows = _feature_contribution_rows(explanation_rows)
    model_rows = [
        _normalize_model_registry_entry(record)
        for record in _record_list(model_registry_entries)
    ]
    score_delta_rows = _score_delta_rows(
        trend_aware_results=trend_aware_results,
        shadow_ml_outputs=shadow_ml_outputs,
        scoring_integration_results=scoring_integration_results,
    )
    gate_rows = [_normalize_runtime_gate_row(record) for record in _record_list(gate_results)]
    adapter_rows = _adapter_rows(
        scoring_integration_results=scoring_integration_results,
        recommendation_integration_results=recommendation_integration_results,
        parser_integration_results=parser_integration_results,
    )
    fallback_rows = [
        _normalize_fallback_row(record)
        for record in _record_list(fallback_decisions)
    ]
    runtime_context = _object_to_mapping(adaptive_runtime_context)
    readiness = _object_to_mapping(readiness_summary)
    empty_state = not any(
        (
            explanation_rows,
            feature_rows,
            model_rows,
            score_delta_rows,
            gate_rows,
            adapter_rows,
            fallback_rows,
            runtime_context,
            readiness,
        )
    )
    summary = {
        "explanation_count": len(explanation_rows),
        "feature_contribution_count": len(feature_rows),
        "model_registry_count": len(model_rows),
        "score_delta_count": len(score_delta_rows),
        "runtime_gate_count": len(gate_rows),
        "adapter_result_count": len(adapter_rows),
        "fallback_decision_count": len(fallback_rows),
        "runtime_context_available": bool(runtime_context),
        "readiness_available": bool(readiness),
        "readiness_success": bool(
            readiness.get("success")
            or readiness.get("runtime_integration_ready")
            or readiness.get("ml_ready")
        ),
    }

    return {
        "enabled": True,
        "read_only": True,
        "advisory_only": True,
        "deterministic_runtime_authoritative": True,
        "runtime_active": False,
        "runtime_influence": False,
        "runtime_influence_granted": False,
        "runtime_eligibility_granted": False,
        "summary": summary,
        "score_deltas": score_delta_rows,
        "explanation_rows": explanation_rows,
        "feature_contribution_rows": feature_rows,
        "model_registry_rows": model_rows,
        "runtime_gate_rows": gate_rows,
        "adapter_rows": adapter_rows,
        "fallback_rows": fallback_rows,
        "runtime_context": deepcopy(runtime_context),
        "readiness_summary": deepcopy(readiness),
        "safety_labels": list(ML_EXPLAINABILITY_VISIBILITY_SAFETY_LABELS),
        "empty_state_messages": list(ML_EXPLAINABILITY_EMPTY_STATE_MESSAGES),
        "empty_state": empty_state,
    }


def _runtime_model_config_value(provider: Any, raw_model: Any) -> str:
    normalized_provider = str(provider or os.getenv("AI_PROVIDER") or "").strip().lower()
    if normalized_provider == "oci":
        return (
            str(os.getenv("OCI_MODEL", "") or "").strip()
            or str(raw_model or "").strip()
            or str(os.getenv("OCI_MODEL_ID", "") or "").strip()
        )
    if normalized_provider == "openai":
        return (
            str(os.getenv("OPENAI_MODEL", "") or "").strip()
            or str(raw_model or "").strip()
            or "gpt-5.4-mini"
        )
    return str(raw_model or "").strip()


def _normalize_learning_candidate(record: Any) -> dict[str, Any]:
    data = _object_to_mapping(record)
    source_evidence = _record_list(data.get("source_evidence"))
    semantic_context = data.get("semantic_context")
    semantic_context_present = bool(_object_to_mapping(semantic_context) or _record_list(semantic_context))
    status = _display_text(data.get("status"), "PROPOSED").upper()
    materialization_reference = _optional_display_text(data.get("materialization_reference"))
    return {
        "candidate_id": _display_text(data.get("candidate_id"), "unknown-candidate"),
        "candidate_type": _display_text(data.get("candidate_type"), "unknown_candidate_type"),
        "status": status,
        "affected_component": _optional_display_text(data.get("affected_component")),
        "affected_domain": _optional_display_text(data.get("affected_domain")),
        "confidence": _safe_confidence(data.get("confidence")),
        "requires_human_review": True,
        "runtime_influence": False,
        "title": _display_text(data.get("title"), "Untitled learning candidate"),
        "source_evidence_count": len(source_evidence),
        "semantic_context_present": semantic_context_present,
        "semantic_context_label": (
            "Semantic context is reviewer-assist only"
            if semantic_context_present
            else "No semantic context"
        ),
        "materialization_reference": materialization_reference,
        "materialization_reference_label": (
            f"Reference only: {materialization_reference}"
            if materialization_reference
            else None
        ),
        "reviewed_by": _optional_display_text(data.get("reviewed_by")),
        "review_notes": _optional_display_text(data.get("review_notes")),
        "approved_for_implementation_only": status == "APPROVED_FOR_IMPLEMENTATION",
    }


def _normalize_learning_governance_record(record: Any) -> dict[str, Any]:
    data = _object_to_mapping(record)
    status = _display_text(
        _first_present(data.get("status"), data.get("to_status"), data.get("from_status")),
        "UNKNOWN",
    ).upper()
    materialization_reference = _optional_display_text(data.get("materialization_reference"))
    approved_only = bool(data.get("approved_for_implementation_only")) or status == "APPROVED_FOR_IMPLEMENTATION"
    return {
        "status": status,
        "reviewed_by": _optional_display_text(_first_present(data.get("reviewed_by"), data.get("actor"))),
        "review_notes": _optional_display_text(data.get("review_notes")),
        "materialization_reference": materialization_reference,
        "materialization_reference_label": (
            f"Reference only: {materialization_reference}"
            if materialization_reference
            else None
        ),
        "approved_for_implementation_only": approved_only,
        "runtime_influence": False,
        "status_label": (
            "APPROVED_FOR_IMPLEMENTATION - Approved for implementation only, not runtime activation"
            if status == "APPROVED_FOR_IMPLEMENTATION"
            else status
        ),
    }


def _normalize_ml_explanation(record: Any) -> dict[str, Any]:
    data = _object_to_mapping(record)
    feature_values = _first_present(
        data.get("feature_contributions"),
        data.get("features"),
        data.get("contributions"),
    )
    return {
        "explanation_id": _display_text(
            _first_present(data.get("explanation_id"), data.get("id")),
            "unknown-explanation",
        ),
        "model_id": _optional_display_text(data.get("model_id")),
        "domain": _optional_display_text(data.get("domain")),
        "summary": _display_text(
            _first_present(data.get("summary"), data.get("rationale"), data.get("explanation")),
            "No explanation summary supplied",
        ),
        "confidence": _safe_confidence(_first_present(data.get("confidence"), data.get("score_confidence"))),
        "uncertainty": _safe_confidence(_first_present(data.get("uncertainty"), data.get("uncertainty_score"))),
        "feature_contributions": [
            _normalize_feature_contribution(item)
            for item in _record_list(feature_values)
        ],
        "diagnostic_evidence": False,
        "recommendation_truth": False,
        "advisory_only": True,
    }


def _normalize_feature_contribution(record: Any) -> dict[str, Any]:
    data = _object_to_mapping(record)
    return {
        "feature": _display_text(
            _first_present(data.get("feature"), data.get("feature_name"), data.get("name")),
            "unknown-feature",
        ),
        "contribution": _optional_display_text(
            _first_present(data.get("contribution"), data.get("contribution_value"), data.get("value"))
        ),
        "direction": _optional_display_text(data.get("direction")),
        "evidence_reference": _optional_display_text(data.get("evidence_reference")),
        "advisory_only": True,
    }


def _feature_contribution_rows(explanation_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for explanation in explanation_rows:
        explanation_id = explanation.get("explanation_id")
        for contribution in explanation.get("feature_contributions", []):
            row = dict(contribution)
            row["explanation_id"] = explanation_id
            row["model_id"] = explanation.get("model_id")
            row["domain"] = explanation.get("domain")
            rows.append(row)
    return rows


def _normalize_model_registry_entry(record: Any) -> dict[str, Any]:
    data = _object_to_mapping(record)
    return {
        "model_id": _display_text(data.get("model_id"), "unknown-model"),
        "model_family": _display_text(
            _first_present(data.get("model_family"), data.get("family")),
            "unknown-family",
        ),
        "governance_status": _display_text(
            _first_present(data.get("governance_status"), data.get("status")),
            "UNKNOWN",
        ),
        "shadow_eligible": bool(data.get("shadow_eligible")),
        "runtime_eligibility_requested": bool(data.get("runtime_eligibility_requested")),
        "runtime_eligibility_granted": False,
        "runtime_active": False,
        "runtime_influence_granted": False,
    }


def _score_delta_rows(
    *,
    trend_aware_results: Iterable[Any] | None,
    shadow_ml_outputs: Iterable[Any] | None,
    scoring_integration_results: Iterable[Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in _record_list(scoring_integration_results):
        data = _object_to_mapping(record)
        rows.append(
            _score_delta_row(
                data,
                source=_display_text(data.get("selected_score_source"), "scoring_integration"),
                advisory_score=_first_present(
                    data.get("selected_advisory_score"),
                    data.get("proposed_score"),
                    data.get("shadow_ml_score"),
                    data.get("trend_aware_score"),
                ),
            )
        )
    for record in _record_list(shadow_ml_outputs):
        data = _object_to_mapping(record)
        rows.append(
            _score_delta_row(
                data,
                source="shadow_ml",
                advisory_score=_first_present(data.get("shadow_ml_score"), data.get("score")),
            )
        )
    for record in _record_list(trend_aware_results):
        data = _object_to_mapping(record)
        rows.append(
            _score_delta_row(
                data,
                source="trend_aware",
                advisory_score=_first_present(data.get("trend_aware_score"), data.get("score")),
            )
        )
    return rows


def _score_delta_row(
    data: Mapping[str, Any],
    *,
    source: str,
    advisory_score: Any,
) -> dict[str, Any]:
    deterministic_score = _safe_score(
        _first_present(data.get("deterministic_score"), data.get("baseline_score"))
    )
    selected_score = _safe_score(advisory_score)
    delta = None
    if deterministic_score is not None and selected_score is not None:
        delta = round(selected_score - deterministic_score, 3)
    return {
        "domain": _optional_display_text(data.get("domain")),
        "source": source,
        "deterministic_score": deterministic_score,
        "advisory_score": selected_score,
        "score_delta": delta,
        "advisory_only": True,
        "runtime_active": False,
    }


def _normalize_runtime_gate_row(record: Any) -> dict[str, Any]:
    data = _object_to_mapping(record)
    denied = _record_list(data.get("denied_reasons"))
    return {
        "gate_id": _display_text(data.get("gate_id"), "unknown-gate"),
        "component_type": _optional_display_text(data.get("component_type")),
        "allowed_for_consideration": bool(data.get("allowed") or data.get("allowed_for_consideration")),
        "denied_reasons": [
            str(reason).strip()
            for reason in denied
            if str(reason).strip()
        ],
        "runtime_active": False,
        "runtime_influence_granted": False,
    }


def _adapter_rows(
    *,
    scoring_integration_results: Iterable[Any] | None,
    recommendation_integration_results: Iterable[Any] | None,
    parser_integration_results: Iterable[Any] | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in _record_list(scoring_integration_results):
        data = _object_to_mapping(record)
        rows.append(
            {
                "adapter_type": "scoring",
                "result_id": _optional_display_text(data.get("result_id")),
                "selected_source": _optional_display_text(data.get("selected_score_source")),
                "gate_allowed_for_consideration": bool(data.get("gate_allowed_for_consideration")),
                "fallback_required": bool(data.get("fallback_to_deterministic")),
                "runtime_active": False,
                "runtime_mutation_performed": False,
            }
        )
    for record in _record_list(recommendation_integration_results):
        data = _object_to_mapping(record)
        rows.append(
            {
                "adapter_type": "recommendation",
                "result_id": _optional_display_text(data.get("result_id")),
                "selected_source": _optional_display_text(data.get("selected_recommendation_source")),
                "gate_allowed_for_consideration": bool(data.get("gate_allowed_for_consideration")),
                "fallback_required": bool(data.get("fallback_to_deterministic")),
                "runtime_active": False,
                "runtime_mutation_performed": False,
            }
        )
    for record in _record_list(parser_integration_results):
        data = _object_to_mapping(record)
        rows.append(
            {
                "adapter_type": "parser",
                "result_id": _optional_display_text(data.get("result_id")),
                "selected_source": _optional_display_text(data.get("selected_parser_source")),
                "selected_action": _optional_display_text(data.get("selected_parser_action")),
                "gate_allowed_for_consideration": bool(data.get("gate_allowed_for_consideration")),
                "fallback_required": bool(data.get("fallback_to_current_parser")),
                "runtime_active": False,
                "runtime_mutation_performed": False,
            }
        )
    return rows


def _normalize_fallback_row(record: Any) -> dict[str, Any]:
    data = _object_to_mapping(record)
    return {
        "decision_id": _optional_display_text(data.get("decision_id")),
        "final_runtime_posture": _display_text(
            data.get("final_runtime_posture"),
            "deterministic_fallback",
        ),
        "fallback_required": bool(_first_present(data.get("fallback_required"), True)),
        "rollback_required": bool(data.get("rollback_required")),
        "rollback_available": bool(data.get("rollback_available")),
        "rollback_reference": _optional_display_text(data.get("rollback_reference")),
        "runtime_mutation_detected": False,
        "runtime_influence_detected": False,
    }


def _safe_score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score < 0.0 or score > 100.0:
        return None
    return round(score, 3)


def _learning_candidate_sort_key(candidate: Mapping[str, Any]) -> tuple[int, float, str]:
    status = str(candidate.get("status") or "").upper()
    confidence = candidate.get("confidence")
    return (
        _CANDIDATE_STATUS_ORDER.get(status, 99),
        -float(confidence if isinstance(confidence, int | float) else 0.0),
        str(candidate.get("candidate_id") or ""),
    )


def _learning_governance_sort_key(record: Mapping[str, Any]) -> tuple[int, str]:
    status = str(record.get("status") or "").upper()
    return (
        _CANDIDATE_STATUS_ORDER.get(status, 99),
        str(record.get("reviewed_by") or ""),
    )


def _count_by_key(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = _optional_display_text(record.get(key))
        if not value:
            continue
        counts[value] = int(counts.get(value, 0)) + 1
    return {name: counts[name] for name in sorted(counts)}


def _object_to_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "to_dict"):
        try:
            converted = value.to_dict()
        except Exception:  # noqa: BLE001
            converted = None
        if isinstance(converted, Mapping):
            return dict(converted)
    if hasattr(value, "model_dump"):
        try:
            converted = value.model_dump()
        except Exception:  # noqa: BLE001
            converted = None
        if isinstance(converted, Mapping):
            return dict(converted)
    if hasattr(value, "__dict__"):
        return {
            key: deepcopy(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return {}


def _record_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        for nested_key in (
            "records",
            "decisions",
            "candidates",
            "learning_candidates",
            "governance_records",
            "governance_decisions",
        ):
            nested_value = value.get(nested_key)
            if nested_value is not None:
                return _record_list(nested_value)
        return [dict(value)]
    if isinstance(value, (str, bytes)):
        return []
    if isinstance(value, Iterable):
        return list(value)
    return []


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, (list, tuple, set, dict)) and not value:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _safe_confidence(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _display_text(value: Any, fallback: str) -> str:
    text = _optional_display_text(value)
    return text if text is not None else fallback


def _optional_display_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    return text


def _format_model_display_name(raw_model: str, alias: str | None = None) -> str:
    if _has_display_value(alias):
        return str(alias).strip()
    model_name = str(raw_model or "").strip()
    if not model_name:
        return "Model not identified in current runtime"
    mappings = {
        "xai.grok-4-1-fast-reasoning": "Grok 4.1 Fast (Reasoning)",
        "xai.grok-4-1-fast": "Grok 4.1 Fast",
        "xai.grok-4-fast-reasoning": "Grok 4 Fast (Reasoning)",
        "xai.grok-4.20-reasoning": "Grok 4.20 Reasoning",
        "gpt-5.4-mini": "GPT-5.4 Mini",
    }
    if model_name in mappings:
        return mappings[model_name]
    if model_name.startswith("ocid1.generativeaimodel."):
        return model_name
    if len(model_name) > 40:
        return model_name[:40] + "..."
    return model_name


def _has_display_value(value: Any) -> bool:
    return value is not None and str(value).strip() not in {"", "None", "null"}
