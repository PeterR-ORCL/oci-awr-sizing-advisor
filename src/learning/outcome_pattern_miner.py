"""Deterministic Phase 7B outcome pattern mining.

This module is intentionally read-only. It inspects caller-provided in-memory
records and returns observational pattern records for later human review.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Mapping, Sequence


ID_ALIASES = (
    "id",
    "run_id",
    "run_history_id",
    "record_id",
    "recommendation_id",
    "recommendation_history_id",
    "action_id",
    "action_history_id",
    "outcome_id",
    "outcome_history_id",
    "action_outcome_id",
    "feedback_id",
    "unknown_signal_id",
)

DOMAIN_ALIASES = (
    "domain",
    "issue_domain",
    "primary_issue",
    "affected_domain",
    "primary_domain",
    "before_primary_domain",
    "after_primary_domain",
    "secondary_domains",
)

LABEL_ALIASES = (
    "recommendation",
    "recommendation_text",
    "recommendation_type",
    "action",
    "action_type",
    "action_label",
    "title",
    "action_description",
    "action_summary",
)

STATUS_ALIASES = (
    "status",
    "feedback_status",
    "recommendation_status",
    "outcome_status",
    "result",
    "disposition",
    "feedback_rating",
    "feedback_rating_label",
)

OUTCOME_ALIASES = (
    "observed_effect",
    "effect",
    "outcome",
    "result",
    "posture",
    "status",
    "outcome_status",
    "outcome_summary",
    "after_posture",
)

UNKNOWN_SIGNAL_ALIASES = (
    "section",
    "section_name",
    "signal_key",
    "key",
    "signature",
    "raw_signature",
    "name",
    "raw_header_text",
)

UNKNOWN_SIGNAL_KEY_ALIASES = (
    "signal_key",
    "key",
    "signature",
    "raw_signature",
    "name",
    "raw_header_text",
)

FEEDBACK_ALIASES = (
    "feedback",
    "feedback_text",
    "feedback_summary",
    "feedback_detail",
    "theme",
    "category",
    "reason",
    "comment",
)

POOR_OUTCOME_TERMS = (
    "poor",
    "worse",
    "worsened",
    "failed",
    "failure",
    "regressed",
    "regression",
    "unresolved",
    "not improved",
    "no improvement",
    "remained poor",
    "still poor",
    "partial",
)

REJECTION_TERMS = (
    "rejected",
    "declined",
    "dismissed",
    "not accepted",
    "not useful",
    "not_useful",
    "negative",
    "false positive",
)

ACCEPTANCE_TERMS = (
    "accepted",
    "approved",
    "implemented",
    "success",
    "successful",
    "positive",
)

DOMAIN_CANONICALS = {
    "adg": "ADG",
    "active_data_guard": "ADG",
    "commit": "COMMIT",
    "cpu": "CPU",
    "db_cpu": "CPU",
    "io": "IO",
    "i_o": "IO",
    "user_io": "IO",
    "user_i_o": "IO",
    "memory": "MEMORY",
    "pga": "MEMORY",
    "sga": "MEMORY",
    "rac": "RAC",
}

PATTERN_ORDER = {
    "repeated_rejected_recommendation": 10,
    "poor_outcome_after_action": 20,
    "recurring_issue_after_action": 30,
    "repeated_unknown_signal": 40,
    "repeated_feedback_theme": 50,
    "recurring_domain_issue": 60,
}


@dataclass
class OutcomePattern:
    """Serializable, observational Phase 7B pattern record."""

    pattern_id: str
    pattern_type: str
    title: str
    description: str
    source_records: list[dict[str, Any]]
    affected_domain: str | None
    affected_component: str | None
    recurrence_count: int
    observed_effect: str | None
    confidence: float
    rationale: str
    requires_human_review: bool
    runtime_influence: bool
    suggested_candidate_type: str | None


class OutcomePatternMiner:
    """Read-only miner for repeated governed-memory outcome patterns."""

    def mine_patterns(
        self,
        memory_records: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    ) -> list[OutcomePattern]:
        """Return deterministic observational patterns from in-memory records."""

        if not memory_records:
            return []

        runs = _records(memory_records, "runs")
        recommendations = _records(memory_records, "recommendations")
        actions = _records(memory_records, "actions")
        outcomes = _records(memory_records, "outcomes")
        feedback = _records(memory_records, "feedback")
        unknown_signals = _records(memory_records, "unknown_signals")

        action_lookup = _label_lookup(actions, "action")
        run_domain_lookup = _run_domain_lookup(runs)

        patterns: list[OutcomePattern] = []
        patterns.extend(self._mine_repeated_rejected_recommendations(recommendations, feedback))
        patterns.extend(self._mine_poor_outcomes_after_actions(outcomes, action_lookup))
        patterns.extend(
            self._mine_recurring_issues_after_actions(
                outcomes,
                action_lookup,
                run_domain_lookup,
            )
        )
        patterns.extend(self._mine_repeated_unknown_signals(unknown_signals))
        patterns.extend(self._mine_repeated_feedback_themes(feedback))
        patterns.extend(self._mine_recurring_domain_issues(runs, recommendations, outcomes))

        return sorted(
            patterns,
            key=lambda pattern: (
                PATTERN_ORDER.get(pattern.pattern_type, 999),
                pattern.pattern_id,
            ),
        )

    def _mine_repeated_rejected_recommendations(
        self,
        recommendations: list[tuple[int, Mapping[str, Any]]],
        feedback: list[tuple[int, Mapping[str, Any]]],
    ) -> list[OutcomePattern]:
        groups: dict[str, dict[str, Any]] = {}

        for index, record in recommendations:
            label = _first_text(record, LABEL_ALIASES)
            if not label or not _is_rejected(record):
                continue
            key = normalize_key(label)
            groups.setdefault(key, {"label": label, "sources": []})["sources"].append(
                _source_ref(
                    "recommendation",
                    index,
                    record,
                    key,
                    LABEL_ALIASES + STATUS_ALIASES + DOMAIN_ALIASES,
                )
            )

        for index, record in feedback:
            label = _first_text(record, LABEL_ALIASES)
            if not label or not _is_rejected(record):
                continue
            key = normalize_key(label)
            groups.setdefault(key, {"label": label, "sources": []})["sources"].append(
                _source_ref(
                    "feedback",
                    index,
                    record,
                    key,
                    LABEL_ALIASES + STATUS_ALIASES + FEEDBACK_ALIASES,
                )
            )

        patterns: list[OutcomePattern] = []
        for key in sorted(groups):
            group = groups[key]
            count = len(group["sources"])
            if count < 2:
                continue
            label = group["label"]
            patterns.append(
                OutcomePattern(
                    pattern_id=f"PATTERN-REJECTED-RECOMMENDATION-{key}",
                    pattern_type="repeated_rejected_recommendation",
                    title=f"Repeated rejected recommendation: {label}",
                    description=(
                        "The same normalized recommendation label appears with "
                        "rejected or negative disposition multiple times."
                    ),
                    source_records=group["sources"],
                    affected_domain=_dominant_domain(group["sources"]),
                    affected_component="recommendation",
                    recurrence_count=count,
                    observed_effect="rejected",
                    confidence=_confidence(count),
                    rationale=(
                        f"{count} source records share normalized recommendation key "
                        f"'{key}' and rejected disposition."
                    ),
                    requires_human_review=True,
                    runtime_influence=False,
                    suggested_candidate_type="recommendation_rule_candidate",
                )
            )
        return patterns

    def _mine_poor_outcomes_after_actions(
        self,
        outcomes: list[tuple[int, Mapping[str, Any]]],
        action_lookup: Mapping[str, str],
    ) -> list[OutcomePattern]:
        groups: dict[str, dict[str, Any]] = {}

        for index, record in outcomes:
            effect = _all_text(record, OUTCOME_ALIASES + STATUS_ALIASES)
            if not _is_poor_outcome(effect):
                continue
            action_label = _action_label_for_outcome(record, action_lookup)
            if not action_label:
                continue
            key = normalize_key(action_label)
            groups.setdefault(key, {"label": action_label, "effect": effect, "sources": []})[
                "sources"
            ].append(
                _source_ref(
                    "outcome",
                    index,
                    record,
                    key,
                    LABEL_ALIASES + OUTCOME_ALIASES + STATUS_ALIASES + DOMAIN_ALIASES,
                )
            )

        patterns: list[OutcomePattern] = []
        for key in sorted(groups):
            group = groups[key]
            count = len(group["sources"])
            if count < 2:
                continue
            label = group["label"]
            patterns.append(
                OutcomePattern(
                    pattern_id=f"PATTERN-POOR-OUTCOME-AFTER-ACTION-{key}",
                    pattern_type="poor_outcome_after_action",
                    title=f"Poor outcomes after action: {label}",
                    description=(
                        "The same normalized action appears multiple times with "
                        "poor, worse, failed, or unresolved outcomes."
                    ),
                    source_records=group["sources"],
                    affected_domain=_dominant_domain(group["sources"]),
                    affected_component="recommendation",
                    recurrence_count=count,
                    observed_effect="poor_outcome",
                    confidence=_confidence(count),
                    rationale=(
                        f"{count} outcome records link action key '{key}' to poor "
                        "or worsened effects."
                    ),
                    requires_human_review=True,
                    runtime_influence=False,
                    suggested_candidate_type="recommendation_rule_candidate",
                )
            )
        return patterns

    def _mine_recurring_issues_after_actions(
        self,
        outcomes: list[tuple[int, Mapping[str, Any]]],
        action_lookup: Mapping[str, str],
        run_domain_lookup: Mapping[str, str],
    ) -> list[OutcomePattern]:
        groups: dict[str, dict[str, Any]] = {}

        for index, record in outcomes:
            action_label = _action_label_for_outcome(record, action_lookup)
            if not action_label:
                continue
            domain = _domain_for_outcome(record, run_domain_lookup)
            if not domain:
                continue
            action_key = normalize_key(action_label)
            domain_key = normalize_key(domain)
            key = f"{action_key}_{domain_key}"
            groups.setdefault(
                key,
                {
                    "action_label": action_label,
                    "domain": domain,
                    "sources": [],
                },
            )["sources"].append(
                _source_ref(
                    "outcome",
                    index,
                    record,
                    key,
                    LABEL_ALIASES + OUTCOME_ALIASES + STATUS_ALIASES + DOMAIN_ALIASES,
                )
            )

        patterns: list[OutcomePattern] = []
        for key in sorted(groups):
            group = groups[key]
            count = len(group["sources"])
            if count < 2:
                continue
            domain = group["domain"]
            action_label = group["action_label"]
            patterns.append(
                OutcomePattern(
                    pattern_id=f"PATTERN-RECURRING-ISSUE-AFTER-ACTION-{key}",
                    pattern_type="recurring_issue_after_action",
                    title=f"Recurring {domain} issue after action: {action_label}",
                    description=(
                        "The same normalized issue domain appears repeatedly after "
                        "the same normalized action type."
                    ),
                    source_records=group["sources"],
                    affected_domain=domain,
                    affected_component="recommendation",
                    recurrence_count=count,
                    observed_effect="recurring_issue_after_action",
                    confidence=_confidence(count),
                    rationale=(
                        f"{count} outcome records share action/domain key '{key}'."
                    ),
                    requires_human_review=True,
                    runtime_influence=False,
                    suggested_candidate_type="recommendation_rule_candidate",
                )
            )
        return patterns

    def _mine_repeated_unknown_signals(
        self,
        unknown_signals: list[tuple[int, Mapping[str, Any]]],
    ) -> list[OutcomePattern]:
        groups: dict[str, dict[str, Any]] = {}

        for index, record in unknown_signals:
            section = _first_text(record, ("section", "section_name")) or "unknown_section"
            signal = _first_text(record, UNKNOWN_SIGNAL_KEY_ALIASES) or "unknown_signal"
            key = f"{normalize_key(section)}_{normalize_key(signal)}"
            recurrence = _positive_int(record.get("frequency_count"), default=1)
            group = groups.setdefault(
                key,
                {
                    "section": section,
                    "signal": signal,
                    "sources": [],
                    "count": 0,
                },
            )
            group["count"] += recurrence
            group["sources"].append(
                _source_ref(
                    "unknown_signal",
                    index,
                    record,
                    key,
                    UNKNOWN_SIGNAL_ALIASES
                    + ("unknown_type", "detection_reason", "frequency_count"),
                )
            )

        patterns: list[OutcomePattern] = []
        for key in sorted(groups):
            group = groups[key]
            count = int(group["count"])
            if count < 2:
                continue
            patterns.append(
                OutcomePattern(
                    pattern_id=f"PATTERN-REPEATED-UNKNOWN-SIGNAL-{key}",
                    pattern_type="repeated_unknown_signal",
                    title=f"Repeated unknown signal: {group['section']} / {group['signal']}",
                    description=(
                        "The same normalized parser unknown signal appears repeatedly "
                        "by section and signature."
                    ),
                    source_records=group["sources"],
                    affected_domain=None,
                    affected_component="parser",
                    recurrence_count=count,
                    observed_effect="repeated_unknown_signal",
                    confidence=_confidence(count),
                    rationale=(
                        f"{count} occurrences share normalized unknown-signal key '{key}'."
                    ),
                    requires_human_review=True,
                    runtime_influence=False,
                    suggested_candidate_type="parser_mapping_candidate",
                )
            )
        return patterns

    def _mine_repeated_feedback_themes(
        self,
        feedback: list[tuple[int, Mapping[str, Any]]],
    ) -> list[OutcomePattern]:
        groups: dict[str, dict[str, Any]] = {}

        for index, record in feedback:
            theme = _feedback_theme(record)
            if not theme:
                continue
            key = normalize_key(theme)
            groups.setdefault(key, {"theme": theme, "sources": []})["sources"].append(
                _source_ref(
                    "feedback",
                    index,
                    record,
                    key,
                    FEEDBACK_ALIASES + STATUS_ALIASES + LABEL_ALIASES,
                )
            )

        patterns: list[OutcomePattern] = []
        for key in sorted(groups):
            group = groups[key]
            count = len(group["sources"])
            if count < 2:
                continue
            theme = group["theme"]
            patterns.append(
                OutcomePattern(
                    pattern_id=f"PATTERN-REPEATED-FEEDBACK-THEME-{key}",
                    pattern_type="repeated_feedback_theme",
                    title=f"Repeated feedback theme: {theme}",
                    description=(
                        "The same normalized reviewer feedback theme appears repeatedly."
                    ),
                    source_records=group["sources"],
                    affected_domain=_dominant_domain(group["sources"]),
                    affected_component=_feedback_component_for_theme(key),
                    recurrence_count=count,
                    observed_effect=theme,
                    confidence=_confidence(count),
                    rationale=f"{count} feedback records share theme '{theme}'.",
                    requires_human_review=True,
                    runtime_influence=False,
                    suggested_candidate_type=_candidate_type_for_feedback_theme(key),
                )
            )
        return patterns

    def _mine_recurring_domain_issues(
        self,
        runs: list[tuple[int, Mapping[str, Any]]],
        recommendations: list[tuple[int, Mapping[str, Any]]],
        outcomes: list[tuple[int, Mapping[str, Any]]],
    ) -> list[OutcomePattern]:
        groups: dict[str, dict[str, Any]] = {}

        for source_type, records in (
            ("run", runs),
            ("recommendation", recommendations),
            ("outcome", outcomes),
        ):
            for index, record in records:
                for domain in _domains_from_record(record):
                    key = normalize_key(domain)
                    groups.setdefault(key, {"domain": domain, "sources": []})[
                        "sources"
                    ].append(
                        _source_ref(
                            source_type,
                            index,
                            record,
                            key,
                            DOMAIN_ALIASES
                            + LABEL_ALIASES
                            + OUTCOME_ALIASES
                            + STATUS_ALIASES,
                        )
                    )

        patterns: list[OutcomePattern] = []
        for key in sorted(groups):
            group = groups[key]
            count = len(group["sources"])
            if count < 2:
                continue
            domain = group["domain"]
            patterns.append(
                OutcomePattern(
                    pattern_id=f"PATTERN-RECURRING-DOMAIN-ISSUE-{key}",
                    pattern_type="recurring_domain_issue",
                    title=f"Recurring domain issue: {domain}",
                    description=(
                        "The same normalized issue domain appears repeatedly across "
                        "governed run, recommendation, or outcome records."
                    ),
                    source_records=group["sources"],
                    affected_domain=domain,
                    affected_component="scoring",
                    recurrence_count=count,
                    observed_effect="recurring_domain_issue",
                    confidence=_confidence(count),
                    rationale=f"{count} source records mention canonical domain '{domain}'.",
                    requires_human_review=True,
                    runtime_influence=False,
                    suggested_candidate_type="scoring_weight_review_candidate",
                )
            )
        return patterns


def patterns_to_dicts(patterns: Sequence[OutcomePattern]) -> list[dict[str, Any]]:
    """Return serializable dictionaries for pattern records."""

    return [asdict(pattern) for pattern in patterns]


def mine_outcome_patterns(
    memory_records: Mapping[str, Sequence[Mapping[str, Any]]] | None,
) -> list[dict[str, Any]]:
    """Convenience wrapper returning serializable pattern dictionaries."""

    return patterns_to_dicts(OutcomePatternMiner().mine_patterns(memory_records))


def normalize_key(value: Any) -> str:
    """Normalize grouping keys into stable lowercase identifier fragments."""

    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "unknown"


def _records(
    memory_records: Mapping[str, Sequence[Mapping[str, Any]]],
    key: str,
) -> list[tuple[int, Mapping[str, Any]]]:
    value = memory_records.get(key) or []
    if isinstance(value, Mapping):
        value = [value]
    if isinstance(value, (str, bytes)):
        return []

    records: list[tuple[int, Mapping[str, Any]]] = []
    for index, record in enumerate(value):
        if isinstance(record, Mapping):
            records.append((index, record))
    return records


def _first_text(record: Mapping[str, Any], aliases: Sequence[str]) -> str | None:
    for alias in aliases:
        value = record.get(alias)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set, dict)):
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _all_text(record: Mapping[str, Any], aliases: Sequence[str]) -> str:
    parts: list[str] = []
    for alias in aliases:
        value = record.get(alias)
        if value is None:
            continue
        if isinstance(value, Mapping):
            parts.extend(str(item) for item in value.values() if item is not None)
        elif isinstance(value, (list, tuple, set)):
            parts.extend(str(item) for item in value if item is not None)
        else:
            parts.append(str(value))
    return " ".join(part.strip() for part in parts if part.strip())


def _label_lookup(records: list[tuple[int, Mapping[str, Any]]], source_type: str) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for _, record in records:
        source_id = _record_id(record)
        label = _first_text(record, LABEL_ALIASES)
        if source_id is not None and label:
            lookup[str(source_id)] = label
        if source_type == "action":
            action_id = record.get("action_history_id") or record.get("action_id")
            if action_id is not None and label:
                lookup[str(action_id)] = label
    return lookup


def _run_domain_lookup(records: list[tuple[int, Mapping[str, Any]]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for _, record in records:
        source_id = _record_id(record)
        domains = _domains_from_record(record)
        if source_id is not None and domains:
            lookup[str(source_id)] = domains[0]
        run_history_id = record.get("run_history_id") or record.get("run_id")
        if run_history_id is not None and domains:
            lookup[str(run_history_id)] = domains[0]
    return lookup


def _record_id(record: Mapping[str, Any]) -> Any | None:
    for alias in ID_ALIASES:
        value = record.get(alias)
        if value is not None and str(value).strip():
            return value
    return None


def _source_ref(
    source_type: str,
    source_index: int,
    record: Mapping[str, Any],
    normalized_key: str,
    field_aliases: Sequence[str],
) -> dict[str, Any]:
    source_id = _record_id(record)
    fields: dict[str, Any] = {}
    for alias in field_aliases:
        if alias in record and record[alias] is not None:
            fields[alias] = _serializable_value(record[alias])

    reference: dict[str, Any] = {
        "source_type": source_type,
        "source_index": source_index,
        "normalized_key": normalized_key,
        "fields": fields,
    }
    if source_id is not None:
        reference["source_id"] = _serializable_value(source_id)
    return reference


def _serializable_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _serializable_value(nested)
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_serializable_value(item) for item in value]
    if isinstance(value, set):
        return [_serializable_value(item) for item in sorted(value, key=str)]
    return str(value)


def _is_rejected(record: Mapping[str, Any]) -> bool:
    status_text = _all_text(record, STATUS_ALIASES + FEEDBACK_ALIASES).lower()
    if not status_text:
        return False
    if any(term in status_text for term in REJECTION_TERMS):
        return True
    if any(term in status_text for term in ACCEPTANCE_TERMS):
        return False
    return False


def _is_poor_outcome(effect: str | None) -> bool:
    if not effect:
        return False
    text = effect.lower()
    return any(term in text for term in POOR_OUTCOME_TERMS)


def _action_label_for_outcome(
    record: Mapping[str, Any],
    action_lookup: Mapping[str, str],
) -> str | None:
    direct = _first_text(record, LABEL_ALIASES)
    if direct:
        return direct
    for alias in ("action_history_id", "action_id"):
        value = record.get(alias)
        if value is not None and str(value) in action_lookup:
            return action_lookup[str(value)]
    action_id = record.get("action_history_id") or record.get("action_id")
    if action_id is not None:
        return f"action_{action_id}"
    return None


def _domain_for_outcome(
    record: Mapping[str, Any],
    run_domain_lookup: Mapping[str, str],
) -> str | None:
    domains = _domains_from_record(record)
    if domains:
        return domains[0]
    for alias in ("after_run_history_id", "run_history_id", "run_id"):
        value = record.get(alias)
        if value is not None and str(value) in run_domain_lookup:
            return run_domain_lookup[str(value)]
    return None


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _feedback_theme(record: Mapping[str, Any]) -> str | None:
    text = _all_text(record, FEEDBACK_ALIASES + STATUS_ALIASES).lower()
    if not text:
        return None

    normalized = normalize_key(text)
    if "confusing" in text or "unclear wording" in text or "wording" in text:
        return "confusing wording"
    if "insufficient evidence" in text or "not enough evidence" in text:
        return "insufficient evidence"
    if "lack evidence" in text or "missing evidence" in text:
        return "insufficient evidence"
    if "recommendation not useful" in text or "not useful" in text:
        return "recommendation not useful"
    if "not actionable" in text:
        return "recommendation not useful"
    if "false positive" in text or "false_positive" in normalized:
        return "false positive"
    return None


def _feedback_component_for_theme(theme_key: str) -> str:
    if theme_key in {"confusing_wording", "insufficient_evidence"}:
        return "dashboard"
    return "recommendation"


def _candidate_type_for_feedback_theme(theme_key: str) -> str:
    if theme_key in {"confusing_wording", "insufficient_evidence"}:
        return "dashboard_wording_candidate"
    return "recommendation_rule_candidate"


def _domains_from_record(record: Mapping[str, Any]) -> list[str]:
    domains: list[str] = []
    for alias in DOMAIN_ALIASES:
        if alias not in record:
            continue
        for value in _flatten_domain_value(record[alias]):
            canonical = _canonical_domain(value)
            if canonical and canonical not in domains:
                domains.append(canonical)
    return domains


def _flatten_domain_value(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return list(value.values())
    if isinstance(value, (list, tuple, set)):
        values = list(value)
        if isinstance(value, set):
            values = sorted(values, key=str)
        return values
    text = str(value)
    if "," in text:
        return [part.strip() for part in text.split(",")]
    return [value]


def _canonical_domain(value: Any) -> str | None:
    key = normalize_key(value)
    if key in DOMAIN_CANONICALS:
        return DOMAIN_CANONICALS[key]
    for known_key, canonical in DOMAIN_CANONICALS.items():
        if re.search(rf"(^|_){re.escape(known_key)}($|_)", key):
            return canonical
    return None


def _dominant_domain(source_records: Sequence[Mapping[str, Any]]) -> str | None:
    counts: dict[str, int] = {}
    for source in source_records:
        fields = source.get("fields")
        if not isinstance(fields, Mapping):
            continue
        for domain in _domains_from_record(fields):
            counts[domain] = counts.get(domain, 0) + 1
    if not counts:
        return None
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _confidence(recurrence_count: int) -> float:
    if recurrence_count >= 5:
        confidence = 0.85
    elif recurrence_count == 4:
        confidence = 0.75
    elif recurrence_count == 3:
        confidence = 0.65
    elif recurrence_count == 2:
        confidence = 0.50
    else:
        confidence = 0.0
    return min(max(confidence, 0.0), 0.95)


__all__ = [
    "OutcomePattern",
    "OutcomePatternMiner",
    "mine_outcome_patterns",
    "normalize_key",
    "patterns_to_dicts",
]
