"""Phase 7E reviewer-assist semantic context for learning candidates.

This module enriches existing Phase 7C ``LearningCandidate`` records with
optional, non-authoritative context supplied explicitly by the caller. It does
not generate, approve, reject, persist, or activate candidates.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from src.learning.learning_candidate_model import LearningCandidate, validate_candidate


DEFAULT_CONTEXT_RECORD_LIMIT = 10

CONTEXT_FIELDS = (
    "context_id",
    "candidate_id",
    "summary",
    "semantic_records",
    "related_cases",
    "related_unknown_signals",
    "related_feedback",
    "related_artifacts",
    "reviewer_assist",
    "non_authoritative",
    "runtime_influence",
    "source",
    "rationale",
)

_ID_ALIASES = (
    "id",
    "record_id",
    "memory_id",
    "case_id",
    "artifact_id",
    "feedback_id",
    "unknown_signal_id",
)
_CANDIDATE_ID_ALIASES = ("candidate_id", "related_candidate_id")
_CANDIDATE_TYPE_ALIASES = ("candidate_type", "type")
_COMPONENT_ALIASES = ("affected_component", "component")
_DOMAIN_ALIASES = ("affected_domain", "domain")
_TEXT_ALIASES = (
    "summary",
    "text",
    "description",
    "note",
    "rationale",
    "content",
    "title",
)
_CATEGORY_ALIASES = ("category", "source_type", "record_type", "type")
_SCORE_ALIASES = ("similarity", "relevance", "score")
_REFERENCE_KEYS = (
    "id",
    "record_id",
    "memory_id",
    "case_id",
    "artifact_id",
    "feedback_id",
    "unknown_signal_id",
    "source_id",
    "pattern_id",
    "normalized_key",
)
_STOPWORDS = {
    "about",
    "after",
    "again",
    "candidate",
    "context",
    "from",
    "into",
    "only",
    "proposal",
    "repeated",
    "review",
    "same",
    "that",
    "this",
    "with",
}


@dataclass(frozen=True)
class SemanticCandidateContext:
    """Reviewer-assist context attached to a learning candidate."""

    context_id: str
    candidate_id: str
    summary: str
    semantic_records: list[Any] = field(default_factory=list)
    related_cases: list[Any] = field(default_factory=list)
    related_unknown_signals: list[Any] = field(default_factory=list)
    related_feedback: list[Any] = field(default_factory=list)
    related_artifacts: list[Any] = field(default_factory=list)
    reviewer_assist: bool = True
    non_authoritative: bool = True
    runtime_influence: bool = False
    source: str | None = None
    rationale: str = ""

    def __post_init__(self) -> None:
        _require_text(self.context_id, "context_id")
        _require_text(self.candidate_id, "candidate_id")
        _require_text(self.summary, "summary")

        if self.reviewer_assist is not True:
            raise ValueError("semantic candidate context must be reviewer-assist only.")
        if self.non_authoritative is not True:
            raise ValueError("semantic candidate context must be non-authoritative.")
        if self.runtime_influence is not False:
            raise ValueError("semantic candidate context cannot influence runtime behavior.")

        for field_name in (
            "semantic_records",
            "related_cases",
            "related_unknown_signals",
            "related_feedback",
            "related_artifacts",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, list):
                raise ValueError(f"{field_name} must be a list.")
            object.__setattr__(self, field_name, deepcopy(value))

        if self.source is not None:
            object.__setattr__(self, "source", str(self.source).strip() or None)
        object.__setattr__(self, "rationale", str(self.rationale or "").strip())


class SemanticCandidateContextBuilder:
    """Build and attach deterministic reviewer-assist context."""

    def __init__(self, max_records: int = DEFAULT_CONTEXT_RECORD_LIMIT) -> None:
        if isinstance(max_records, bool) or not isinstance(max_records, int) or max_records <= 0:
            raise ValueError("max_records must be a positive integer.")
        self.max_records = max_records

    def build_context(
        self,
        candidate: LearningCandidate,
        semantic_records: Sequence[Mapping[str, Any]],
    ) -> SemanticCandidateContext | None:
        """Return reviewer-assist context for matching in-memory records.

        ``None`` is returned when no meaningful records match. No external
        recall, database, network, file, or model service is consulted.
        """

        validate_candidate(candidate)
        matched_records = self._matched_records(candidate, semantic_records)
        if not matched_records:
            return None

        semantic_records_list = [record for _, record in matched_records[: self.max_records]]
        related_cases = [
            record for record in semantic_records_list if _record_kind(record) == "case"
        ]
        related_unknown_signals = [
            record for record in semantic_records_list if _record_kind(record) == "unknown_signal"
        ]
        related_feedback = [
            record for record in semantic_records_list if _record_kind(record) == "feedback"
        ]
        related_artifacts = [
            record for record in semantic_records_list if _record_kind(record) == "artifact"
        ]

        context_id = _create_context_id(candidate.candidate_id, semantic_records_list)
        summary = (
            f"Reviewer-assist semantic context only for {candidate.candidate_id}: "
            f"{len(semantic_records_list)} related in-memory record(s) matched. "
            "This context is optional, non-authoritative, and has runtime_influence=false."
        )
        rationale = _context_rationale(semantic_records_list)

        return SemanticCandidateContext(
            context_id=context_id,
            candidate_id=candidate.candidate_id,
            summary=summary,
            semantic_records=semantic_records_list,
            related_cases=related_cases,
            related_unknown_signals=related_unknown_signals,
            related_feedback=related_feedback,
            related_artifacts=related_artifacts,
            reviewer_assist=True,
            non_authoritative=True,
            runtime_influence=False,
            source="in_memory_semantic_records",
            rationale=rationale,
        )

    def attach_context(
        self,
        candidate: LearningCandidate,
        semantic_records: Sequence[Mapping[str, Any]],
    ) -> LearningCandidate:
        """Return a candidate copy with semantic context attached when present."""

        validate_candidate(candidate)
        context = self.build_context(candidate, semantic_records)
        data = candidate.to_dict()

        if context is not None:
            data["semantic_context"] = semantic_context_to_dict(context)

        data["requires_human_review"] = True
        data["runtime_influence"] = False
        return LearningCandidate.from_dict(data)

    def _matched_records(
        self,
        candidate: LearningCandidate,
        semantic_records: Sequence[Mapping[str, Any]],
    ) -> list[tuple[float, dict[str, Any]]]:
        source_references = _candidate_source_references(candidate)
        matches: list[tuple[float, dict[str, Any]]] = []

        for record in _record_mappings(semantic_records):
            reasons = _match_reasons(candidate, record, source_references)
            if not reasons:
                continue
            match_score = _match_score(record, reasons)
            canonical = _canonical_record(record, reasons, match_score)
            matches.append((match_score, canonical))

        return sorted(
            matches,
            key=lambda item: (
                -item[0],
                _normalized_identifier(item[1]["record_id"]),
                _stable_json(item[1]["record"]),
            ),
        )


def build_semantic_candidate_context(
    candidate: LearningCandidate,
    semantic_records: Sequence[Mapping[str, Any]],
) -> SemanticCandidateContext | None:
    """Convenience wrapper for ``SemanticCandidateContextBuilder.build_context``."""

    return SemanticCandidateContextBuilder().build_context(candidate, semantic_records)


def attach_semantic_context(
    candidate: LearningCandidate,
    semantic_records: Sequence[Mapping[str, Any]],
) -> LearningCandidate:
    """Convenience wrapper for ``SemanticCandidateContextBuilder.attach_context``."""

    return SemanticCandidateContextBuilder().attach_context(candidate, semantic_records)


def semantic_context_to_dict(context: SemanticCandidateContext) -> dict[str, Any]:
    """Return a deterministic dictionary representation of semantic context."""

    if not isinstance(context, SemanticCandidateContext):
        raise ValueError("context must be a SemanticCandidateContext.")
    return {field_name: deepcopy(getattr(context, field_name)) for field_name in CONTEXT_FIELDS}


def semantic_context_from_dict(data: Mapping[str, Any]) -> SemanticCandidateContext:
    """Reconstruct semantic candidate context from a dictionary."""

    if not isinstance(data, Mapping):
        raise ValueError("semantic context data must be a mapping.")
    values = {
        "context_id": data.get("context_id"),
        "candidate_id": data.get("candidate_id"),
        "summary": data.get("summary"),
        "semantic_records": deepcopy(data.get("semantic_records", [])),
        "related_cases": deepcopy(data.get("related_cases", [])),
        "related_unknown_signals": deepcopy(data.get("related_unknown_signals", [])),
        "related_feedback": deepcopy(data.get("related_feedback", [])),
        "related_artifacts": deepcopy(data.get("related_artifacts", [])),
        "reviewer_assist": data.get("reviewer_assist", True),
        "non_authoritative": data.get("non_authoritative", True),
        "runtime_influence": data.get("runtime_influence", False),
        "source": data.get("source"),
        "rationale": data.get("rationale", ""),
    }
    return SemanticCandidateContext(**values)


def _record_mappings(
    semantic_records: Sequence[Mapping[str, Any]] | None,
) -> list[Mapping[str, Any]]:
    if semantic_records is None:
        return []
    if isinstance(semantic_records, (str, bytes)) or not isinstance(semantic_records, Sequence):
        raise ValueError("semantic_records must be a sequence of mappings.")
    return [record for record in semantic_records if isinstance(record, Mapping)]


def _match_reasons(
    candidate: LearningCandidate,
    record: Mapping[str, Any],
    candidate_source_references: set[str],
) -> list[str]:
    reasons: list[str] = []

    if _contains_normalized(record, _CANDIDATE_ID_ALIASES, candidate.candidate_id):
        reasons.append("candidate_id")
    if _contains_normalized(record, _CANDIDATE_TYPE_ALIASES, candidate.candidate_type):
        reasons.append("candidate_type")
    if candidate.affected_component and _contains_normalized(
        record,
        _COMPONENT_ALIASES,
        candidate.affected_component,
    ):
        reasons.append("affected_component")
    if candidate.affected_domain and _contains_normalized(
        record,
        _DOMAIN_ALIASES,
        candidate.affected_domain,
    ):
        reasons.append("affected_domain")

    record_references = _reference_values(record)
    if candidate_source_references.intersection(record_references):
        reasons.append("source_reference")

    overlap = _title_keyword_overlap(candidate.title, _record_search_text(record))
    if overlap:
        reasons.append(f"title_keyword:{','.join(overlap)}")

    return reasons


def _match_score(record: Mapping[str, Any], reasons: Sequence[str]) -> float:
    score = 0.0
    for reason in reasons:
        if reason == "candidate_id":
            score += 1000.0
        elif reason == "source_reference":
            score += 800.0
        elif reason == "candidate_type":
            score += 300.0
        elif reason == "affected_component":
            score += 200.0
        elif reason == "affected_domain":
            score += 200.0
        elif reason.startswith("title_keyword:"):
            keywords = [keyword for keyword in reason.split(":", 1)[1].split(",") if keyword]
            score += 100.0 + (10.0 * len(keywords))

    explicit_score = _numeric_record_score(record)
    if explicit_score is not None:
        score += explicit_score
    return score


def _canonical_record(
    record: Mapping[str, Any],
    reasons: Sequence[str],
    match_score: float,
) -> dict[str, Any]:
    safe_record = _json_safe(record)
    record_id = _record_id(safe_record)
    category = _record_category(safe_record)
    summary = _record_summary(safe_record)

    return {
        "record_id": record_id,
        "category": category,
        "summary": summary,
        "match_reasons": list(reasons),
        "match_score": round(float(match_score), 6),
        "record": safe_record,
    }


def _record_id(record: Mapping[str, Any]) -> str:
    value = _first_value(record, _ID_ALIASES)
    if value is not None:
        return str(value).strip()
    digest = hashlib.sha256(_stable_json(record).encode("utf-8")).hexdigest()[:12].upper()
    return f"RECORD-{digest}"


def _record_category(record: Mapping[str, Any]) -> str | None:
    value = _first_value(record, _CATEGORY_ALIASES)
    if value is None:
        return None
    return str(value).strip() or None


def _record_summary(record: Mapping[str, Any]) -> str:
    value = _first_value(record, _TEXT_ALIASES)
    if value is not None and str(value).strip():
        return str(value).strip()
    return f"Semantic record {_record_id(record)} matched this candidate."


def _record_kind(record: Mapping[str, Any]) -> str | None:
    category = str(record.get("category") or "").lower()
    raw_record = record.get("record")
    raw_keys = set(raw_record.keys()) if isinstance(raw_record, Mapping) else set()

    if "unknown" in category or "unknown_signal_id" in raw_keys:
        return "unknown_signal"
    if "feedback" in category or "feedback_id" in raw_keys:
        return "feedback"
    if (
        "artifact" in category
        or "knowledge" in category
        or "document" in category
        or "doc" == category
        or "artifact_id" in raw_keys
    ):
        return "artifact"
    if "case" in category or "case_id" in raw_keys:
        return "case"
    return None


def _candidate_source_references(candidate: LearningCandidate) -> set[str]:
    references: set[str] = set()
    for source in candidate.source_evidence:
        references.update(_reference_values(source))
    for source in candidate.structured_sources:
        references.update(_reference_values(source))
    return references


def _reference_values(value: Any) -> set[str]:
    references: set[str] = set()

    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in _REFERENCE_KEYS and _scalar_reference(item):
                references.add(_normalize(item))
            references.update(_reference_values(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            references.update(_reference_values(item))

    return references


def _scalar_reference(value: Any) -> bool:
    return isinstance(value, (str, int, float)) and not isinstance(value, bool) and str(value).strip()


def _contains_normalized(
    record: Mapping[str, Any],
    aliases: Sequence[str],
    expected: str,
) -> bool:
    normalized_expected = _normalize(expected)
    for alias in aliases:
        if alias in record and _normalize(record[alias]) == normalized_expected:
            return True
    return False


def _numeric_record_score(record: Mapping[str, Any]) -> float | None:
    value = _first_value(record, _SCORE_ALIASES)
    if isinstance(value, bool) or value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return numeric


def _record_search_text(record: Mapping[str, Any]) -> str:
    chunks = []
    for alias in _TEXT_ALIASES:
        value = record.get(alias)
        if value is not None:
            chunks.append(str(value))
    return " ".join(chunks)


def _title_keyword_overlap(title: str, record_text: str) -> list[str]:
    title_tokens = _tokens(title)
    record_tokens = _tokens(record_text)
    overlap = sorted(title_tokens.intersection(record_tokens))
    if len(overlap) < 2:
        return []
    return overlap[:5]


def _tokens(text: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", str(text or "").lower())
        if len(token) >= 2 and token not in _STOPWORDS
    }
    return tokens


def _context_rationale(records: Sequence[Mapping[str, Any]]) -> str:
    reason_counts: dict[str, int] = {}
    for record in records:
        for reason in record.get("match_reasons", []):
            reason_name = str(reason).split(":", 1)[0]
            reason_counts[reason_name] = reason_counts.get(reason_name, 0) + 1

    reasons = ", ".join(
        f"{reason}={count}" for reason, count in sorted(reason_counts.items())
    )
    return (
        "Matched explicit in-memory semantic records for reviewer understanding only. "
        f"Match reasons: {reasons}. "
        "The context can explain but cannot decide candidate validity."
    )


def _create_context_id(candidate_id: str, records: Sequence[Mapping[str, Any]]) -> str:
    seed = {
        "candidate_id": candidate_id,
        "records": [
            {
                "record_id": record.get("record_id"),
                "match_reasons": record.get("match_reasons", []),
                "record": record.get("record", {}),
            }
            for record in records
        ],
    }
    digest = hashlib.sha256(_stable_json(seed).encode("utf-8")).hexdigest()[:12].upper()
    return f"SEMCTX-{_identifier_fragment(candidate_id)}-{digest}"


def _first_value(record: Mapping[str, Any], aliases: Sequence[str]) -> Any:
    for alias in aliases:
        value = record.get(alias)
        if value is not None and str(value).strip():
            return value
    return None


def _require_text(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def _identifier_fragment(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "UNKNOWN"


def _normalized_identifier(value: Any) -> str:
    return _identifier_fragment(value).lower()


def _normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _stable_json(value: Any) -> str:
    return json.dumps(_json_safe(value), sort_keys=True, separators=(",", ":"))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _json_safe(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
