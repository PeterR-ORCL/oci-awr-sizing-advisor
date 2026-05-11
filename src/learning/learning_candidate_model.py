"""Deterministic Phase 7C learning candidate model.

Learning candidates are governed proposals only. They are serializable records
for later human review and cannot activate or modify runtime behavior.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


PARSER_MAPPING_CANDIDATE = "parser_mapping_candidate"
RECOMMENDATION_RULE_CANDIDATE = "recommendation_rule_candidate"
SCORING_WEIGHT_REVIEW_CANDIDATE = "scoring_weight_review_candidate"
DASHBOARD_WORDING_CANDIDATE = "dashboard_wording_candidate"
DASHBOARD_INTERACTION_CANDIDATE = "dashboard_interaction_candidate"
GOVERNANCE_WORKFLOW_CANDIDATE = "governance_workflow_candidate"
SEMANTIC_SUMMARY_CANDIDATE = "semantic_summary_candidate"
DOCUMENTATION_CANDIDATE = "documentation_candidate"
VALIDATION_CANDIDATE = "validation_candidate"

SUPPORTED_CANDIDATE_TYPES = (
    PARSER_MAPPING_CANDIDATE,
    RECOMMENDATION_RULE_CANDIDATE,
    SCORING_WEIGHT_REVIEW_CANDIDATE,
    DASHBOARD_WORDING_CANDIDATE,
    DASHBOARD_INTERACTION_CANDIDATE,
    GOVERNANCE_WORKFLOW_CANDIDATE,
    SEMANTIC_SUMMARY_CANDIDATE,
    DOCUMENTATION_CANDIDATE,
    VALIDATION_CANDIDATE,
)

PROPOSED = "PROPOSED"
UNDER_REVIEW = "UNDER_REVIEW"
APPROVED_FOR_IMPLEMENTATION = "APPROVED_FOR_IMPLEMENTATION"
REJECTED = "REJECTED"
NEEDS_REVISION = "NEEDS_REVISION"
IMPLEMENTED = "IMPLEMENTED"
VALIDATED = "VALIDATED"
CLOSED = "CLOSED"

SUPPORTED_CANDIDATE_STATUSES = (
    PROPOSED,
    UNDER_REVIEW,
    APPROVED_FOR_IMPLEMENTATION,
    REJECTED,
    NEEDS_REVISION,
    IMPLEMENTED,
    VALIDATED,
    CLOSED,
)

STATUSES_REQUIRING_ACTOR = (
    UNDER_REVIEW,
    APPROVED_FOR_IMPLEMENTATION,
    REJECTED,
    NEEDS_REVISION,
    IMPLEMENTED,
    VALIDATED,
    CLOSED,
)

CANDIDATE_FIELDS = (
    "candidate_id",
    "candidate_type",
    "title",
    "description",
    "source_evidence",
    "structured_sources",
    "semantic_context",
    "affected_component",
    "affected_domain",
    "confidence",
    "rationale",
    "requires_human_review",
    "runtime_influence",
    "status",
    "created_at",
    "created_by",
    "reviewed_by",
    "review_notes",
    "materialization_reference",
)

MAX_CANDIDATE_CONFIDENCE = 0.95


class LearningCandidateValidationError(ValueError):
    """Raised when a learning candidate violates Phase 7C model rules."""


@dataclass(frozen=True)
class LearningCandidate:
    """Serializable proposal record for governed future learning work."""

    candidate_id: str
    candidate_type: str
    title: str
    description: str
    rationale: str
    source_evidence: list[Any] = field(default_factory=list)
    structured_sources: list[Any] = field(default_factory=list)
    semantic_context: dict[str, Any] | None = None
    affected_component: str | None = None
    affected_domain: str | None = None
    confidence: float = 0.0
    requires_human_review: bool = True
    runtime_influence: bool = False
    status: str = PROPOSED
    created_at: str | None = None
    created_by: str | None = None
    reviewed_by: str | None = None
    review_notes: str | None = None
    materialization_reference: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.candidate_id, "candidate_id")
        _validate_candidate_type(self.candidate_type)
        _validate_candidate_status(self.status)
        _require_non_empty_string(self.title, "title")
        _require_non_empty_string(self.description, "description")
        _require_non_empty_string(self.rationale, "rationale")
        _validate_confidence(self.confidence)

        if self.requires_human_review is not True:
            raise LearningCandidateValidationError(
                "Learning candidates must require human review."
            )
        if self.runtime_influence is not False:
            raise LearningCandidateValidationError(
                "Learning candidates created by this model cannot influence runtime behavior."
            )
        if not isinstance(self.source_evidence, list):
            raise LearningCandidateValidationError("source_evidence must be a list.")
        if not isinstance(self.structured_sources, list):
            raise LearningCandidateValidationError("structured_sources must be a list.")
        if self.semantic_context is not None and not isinstance(self.semantic_context, dict):
            raise LearningCandidateValidationError("semantic_context must be None or a dict.")

        object.__setattr__(self, "confidence", float(self.confidence))
        object.__setattr__(self, "source_evidence", deepcopy(self.source_evidence))
        object.__setattr__(self, "structured_sources", deepcopy(self.structured_sources))
        object.__setattr__(self, "semantic_context", deepcopy(self.semantic_context))

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic serializable dictionary for this candidate."""

        return {field_name: deepcopy(getattr(self, field_name)) for field_name in CANDIDATE_FIELDS}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LearningCandidate":
        """Reconstruct and validate a candidate from a dictionary."""

        if not isinstance(data, Mapping):
            raise LearningCandidateValidationError("candidate data must be a mapping.")
        values = {
            field_name: deepcopy(data[field_name])
            for field_name in CANDIDATE_FIELDS
            if field_name in data
        }
        return cls(**values)


def is_supported_candidate_type(candidate_type: str) -> bool:
    """Return True when the candidate type is allowed by Phase 7C."""

    return candidate_type in SUPPORTED_CANDIDATE_TYPES


def is_supported_candidate_status(status: str) -> bool:
    """Return True when the candidate status is allowed by Phase 7C."""

    return status in SUPPORTED_CANDIDATE_STATUSES


def validate_candidate(candidate: LearningCandidate) -> LearningCandidate:
    """Validate a candidate and return it unchanged when valid."""

    if not isinstance(candidate, LearningCandidate):
        raise LearningCandidateValidationError("candidate must be a LearningCandidate.")
    LearningCandidate.from_dict(candidate.to_dict())
    return candidate


def to_dict(candidate: LearningCandidate) -> dict[str, Any]:
    """Return a serializable dictionary for one candidate."""

    return validate_candidate(candidate).to_dict()


def from_dict(data: Mapping[str, Any]) -> LearningCandidate:
    """Reconstruct and validate one candidate from dictionary data."""

    return LearningCandidate.from_dict(data)


def candidates_to_dicts(candidates: Sequence[LearningCandidate]) -> list[dict[str, Any]]:
    """Return deterministic dictionaries for candidate records."""

    return [to_dict(candidate) for candidate in candidates]


def create_candidate_id(
    candidate_type: str,
    title: str,
    affected_component: str | None = None,
    affected_domain: str | None = None,
    source_evidence: Sequence[Any] | None = None,
    pattern_id: str | None = None,
) -> str:
    """Create a stable candidate identifier from deterministic inputs."""

    _validate_candidate_type(candidate_type)
    _require_non_empty_string(title, "title")
    seed = {
        "candidate_type": candidate_type,
        "title": str(title).strip(),
        "affected_component": affected_component or "",
        "affected_domain": affected_domain or "",
        "pattern_id": pattern_id or "",
        "source_evidence": _stable_source_identity(source_evidence or []),
    }
    seed_text = json.dumps(_json_safe(seed), sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16].upper()
    return f"CANDIDATE-{_identifier_fragment(candidate_type)}-{digest}"


def candidate_from_pattern(
    pattern: Any,
    candidate_type: str | None = None,
) -> LearningCandidate:
    """Convert one explicitly supplied Phase 7B pattern into a proposal record.

    This helper does not mine, rank, select, approve, persist, or apply
    candidates. It only converts the one pattern object provided by the caller.
    """

    selected_type = candidate_type or _pattern_value(pattern, "suggested_candidate_type")
    _validate_candidate_type(selected_type)

    source_records = _pattern_value(pattern, "source_records", [])
    if source_records is None:
        source_records = []
    if not isinstance(source_records, list):
        raise LearningCandidateValidationError("pattern source_records must be a list.")

    pattern_id = _optional_text(_pattern_value(pattern, "pattern_id"))
    pattern_type = _optional_text(_pattern_value(pattern, "pattern_type"))
    title = _required_pattern_text(pattern, "title")
    description = _required_pattern_text(pattern, "description")
    rationale = _required_pattern_text(pattern, "rationale")
    affected_component = _optional_text(_pattern_value(pattern, "affected_component"))
    affected_domain = _optional_text(_pattern_value(pattern, "affected_domain"))

    source_evidence = deepcopy(source_records)
    structured_sources = [
        {
            "source_type": "outcome_pattern",
            "pattern_id": pattern_id,
            "pattern_type": pattern_type,
            "source_records": deepcopy(source_records),
        }
    ]

    return LearningCandidate(
        candidate_id=create_candidate_id(
            selected_type,
            title,
            affected_component=affected_component,
            affected_domain=affected_domain,
            source_evidence=source_evidence,
            pattern_id=pattern_id,
        ),
        candidate_type=selected_type,
        title=title,
        description=description,
        source_evidence=source_evidence,
        structured_sources=structured_sources,
        semantic_context=None,
        affected_component=affected_component,
        affected_domain=affected_domain,
        confidence=_pattern_value(pattern, "confidence", 0.0),
        rationale=rationale,
        requires_human_review=True,
        runtime_influence=False,
        status=PROPOSED,
    )


def transition_candidate_status(
    candidate: LearningCandidate,
    new_status: str,
    actor: str | None = None,
    review_notes: str | None = None,
) -> LearningCandidate:
    """Return a validated candidate copy with a new model-level status."""

    validate_candidate(candidate)
    _validate_candidate_status(new_status)
    if new_status in STATUSES_REQUIRING_ACTOR:
        _require_non_empty_string(actor, "actor")

    data = candidate.to_dict()
    data["status"] = new_status
    data["runtime_influence"] = False
    data["requires_human_review"] = True
    if actor is not None:
        data["reviewed_by"] = actor
    if review_notes is not None:
        data["review_notes"] = review_notes
    return LearningCandidate.from_dict(data)


def attach_materialization_reference(
    candidate: LearningCandidate,
    reference: str,
    actor: str | None = None,
    review_notes: str | None = None,
) -> LearningCandidate:
    """Return a candidate copy with an implementation reference attached."""

    validate_candidate(candidate)
    _require_non_empty_string(reference, "reference")
    _require_non_empty_string(actor, "actor")

    data = candidate.to_dict()
    data["materialization_reference"] = str(reference).strip()
    data["reviewed_by"] = actor
    data["runtime_influence"] = False
    data["requires_human_review"] = True
    if review_notes is not None:
        data["review_notes"] = review_notes
    return LearningCandidate.from_dict(data)


def _validate_candidate_type(candidate_type: Any) -> None:
    if candidate_type not in SUPPORTED_CANDIDATE_TYPES:
        raise LearningCandidateValidationError(f"Unsupported candidate_type: {candidate_type!r}.")


def _validate_candidate_status(status: Any) -> None:
    if status not in SUPPORTED_CANDIDATE_STATUSES:
        raise LearningCandidateValidationError(f"Unsupported status: {status!r}.")


def _validate_confidence(confidence: Any) -> None:
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise LearningCandidateValidationError("confidence must be numeric.")
    numeric = float(confidence)
    if numeric == 1.0 or numeric < 0.0 or numeric > MAX_CANDIDATE_CONFIDENCE:
        raise LearningCandidateValidationError(
            "confidence must be between 0.0 and 0.95 inclusive and never 1.0."
        )


def _require_non_empty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise LearningCandidateValidationError(f"{field_name} must be a non-empty string.")


def _pattern_value(pattern: Any, field_name: str, default: Any = None) -> Any:
    if isinstance(pattern, Mapping):
        return pattern.get(field_name, default)
    return getattr(pattern, field_name, default)


def _required_pattern_text(pattern: Any, field_name: str) -> str:
    value = _optional_text(_pattern_value(pattern, field_name))
    _require_non_empty_string(value, field_name)
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _identifier_fragment(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "UNKNOWN"


def _stable_source_identity(source_evidence: Sequence[Any]) -> list[Any]:
    identities = [_json_safe(source) for source in source_evidence]
    return sorted(
        identities,
        key=lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")),
    )


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
