"""Phase 7BW scoring runtime config activation metadata.

This module defines local-only scoring runtime config package, activation
manifest, eligibility, rollback, and regression evidence metadata. It validates
future scoring activation envelopes without importing runtime scoring modules,
changing scoring code or config, applying weights or thresholds, mutating score
output, activating runtime scoring, or mutating Phase 4I.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any


SCORE_SCALE = "0_100"
CONFIDENCE_SCALE = "0_1"

SCORING_RUNTIME_PACKAGE_STATUSES = (
    "proposed",
    "under_review",
    "validation_required",
    "regression_ready",
    "eligible_for_runtime_review",
    "rejected",
    "superseded",
    "closed",
)

SCORING_RUNTIME_ELIGIBILITY_STATUSES = (
    "not_eligible",
    "eligible_metadata_only",
    "needs_regression_reference",
    "needs_before_after_reference",
    "needs_phase4i_score_contract",
    "needs_rollback_reference",
    "needs_runtime_gate",
    "invalid_score_scale",
    "invalid_confidence_scale",
    "blocked_by_safety",
)

SCORING_RUNTIME_ACTIVATION_MODES = (
    "disabled",
    "manual_review_required",
    "future_runtime_manifest",
    "emergency_disabled",
)

ELIGIBILITY_PACKAGE_STATUS = "eligible_for_runtime_review"
DEFAULT_ACTIVATION_MODE = "manual_review_required"


class ScoringRuntimeActivationError(ValueError):
    """Raised when Phase 7BW scoring activation metadata is invalid."""


@dataclass(frozen=True)
class ScoringRuntimeConfigPackage:
    """Local metadata package for future scoring runtime config eligibility."""

    package_id: str
    source_scoring_review_id: str
    source_materialization_id: str
    scoring_config_version: str
    affected_domains: list[str] = field(default_factory=list)
    affected_components: list[str] = field(default_factory=list)
    proposed_config_summary: str = ""
    score_scale: str = SCORE_SCALE
    confidence_scale: str = CONFIDENCE_SCALE
    weight_changes: dict[str, Any] = field(default_factory=dict)
    threshold_changes: dict[str, Any] = field(default_factory=dict)
    severity_cutoff_changes: dict[str, Any] = field(default_factory=dict)
    confidence_rule_changes: dict[str, Any] = field(default_factory=dict)
    trend_sensitivity_changes: dict[str, Any] = field(default_factory=dict)
    anomaly_sensitivity_changes: dict[str, Any] = field(default_factory=dict)
    before_after_reference: str | None = None
    regression_reference: str | None = None
    phase4i_score_contract_reference: str | None = None
    rollback_reference: str | None = None
    package_status: str = "proposed"
    runtime_eligible: bool = False
    runtime_active: bool = False
    scoring_config_applied: bool = False
    score_output_mutation_performed: bool = False
    phase4i_mutation_performed: bool = False
    created_by: str | None = None
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.package_id, "package_id")
        _require_nonempty_string(
            self.source_scoring_review_id,
            "source_scoring_review_id",
        )
        _require_nonempty_string(
            self.source_materialization_id,
            "source_materialization_id",
        )
        _require_nonempty_string(self.scoring_config_version, "scoring_config_version")
        _require_list_of_strings(self.affected_domains, "affected_domains")
        _require_list_of_strings(self.affected_components, "affected_components")
        _require_nonempty_string(
            self.proposed_config_summary,
            "proposed_config_summary",
        )
        _require_score_scale(self.score_scale)
        _require_confidence_scale(self.confidence_scale)
        _require_mapping(self.weight_changes, "weight_changes")
        _require_mapping(self.threshold_changes, "threshold_changes")
        _require_mapping(self.severity_cutoff_changes, "severity_cutoff_changes")
        _require_mapping(self.confidence_rule_changes, "confidence_rule_changes")
        _require_mapping(self.trend_sensitivity_changes, "trend_sensitivity_changes")
        _require_mapping(
            self.anomaly_sensitivity_changes,
            "anomaly_sensitivity_changes",
        )
        _require_optional_string(self.before_after_reference, "before_after_reference")
        _require_optional_string(self.regression_reference, "regression_reference")
        _require_optional_string(
            self.phase4i_score_contract_reference,
            "phase4i_score_contract_reference",
        )
        _require_optional_string(self.rollback_reference, "rollback_reference")
        _require_supported(
            self.package_status,
            SCORING_RUNTIME_PACKAGE_STATUSES,
            "package_status",
        )
        _require_boolean(self.runtime_eligible, "runtime_eligible")
        _require_false(self.runtime_active, "runtime_active")
        _require_false(self.scoring_config_applied, "scoring_config_applied")
        _require_false(
            self.score_output_mutation_performed,
            "score_output_mutation_performed",
        )
        _require_false(
            self.phase4i_mutation_performed,
            "phase4i_mutation_performed",
        )
        _require_optional_string(self.created_by, "created_by")
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")
        if self.package_status in ("regression_ready", "eligible_for_runtime_review"):
            _require_nonempty_string(self.rollback_reference, "rollback_reference")
        if self.runtime_eligible and not _package_has_all_eligibility_metadata(self):
            raise ScoringRuntimeActivationError(
                "runtime_eligible metadata requires all validation references, "
                "rollback reference, supported scales, and eligible status."
            )


@dataclass(frozen=True)
class ScoringActivationManifest:
    """Local manifest metadata for future scoring config activation review."""

    manifest_id: str
    package_id: str
    manifest_version: str
    activation_mode: str = DEFAULT_ACTIVATION_MODE
    explicit_activation_required: bool = True
    validation_reference: str | None = None
    rollback_reference: str | None = None
    runtime_gate_reference: str | None = None
    deterministic_fallback_available: bool = True
    phase4i_score_contract_preserved: bool = True
    runtime_activation_requested: bool = False
    runtime_activation_approved: bool = False
    runtime_active: bool = False
    scoring_config_applied: bool = False
    created_by: str | None = None
    created_at: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.manifest_id, "manifest_id")
        _require_nonempty_string(self.package_id, "package_id")
        _require_nonempty_string(self.manifest_version, "manifest_version")
        _require_supported(
            self.activation_mode,
            SCORING_RUNTIME_ACTIVATION_MODES,
            "activation_mode",
        )
        _require_true(
            self.explicit_activation_required,
            "explicit_activation_required",
        )
        _require_optional_string(self.validation_reference, "validation_reference")
        _require_optional_string(self.rollback_reference, "rollback_reference")
        _require_optional_string(self.runtime_gate_reference, "runtime_gate_reference")
        _require_true(
            self.deterministic_fallback_available,
            "deterministic_fallback_available",
        )
        _require_true(
            self.phase4i_score_contract_preserved,
            "phase4i_score_contract_preserved",
        )
        _require_false(
            self.runtime_activation_requested,
            "runtime_activation_requested",
        )
        _require_false(
            self.runtime_activation_approved,
            "runtime_activation_approved",
        )
        _require_false(self.runtime_active, "runtime_active")
        _require_false(self.scoring_config_applied, "scoring_config_applied")
        _require_optional_string(self.created_by, "created_by")
        _require_optional_string(self.created_at, "created_at")
        _require_optional_string(self.notes, "notes")


@dataclass(frozen=True)
class ScoringRuntimeEligibilityRecord:
    """Local eligibility result for a scoring runtime config package."""

    eligibility_id: str
    package_id: str
    manifest_id: str
    eligible: bool
    eligibility_status: str
    required_validation_present: bool
    regression_reference_present: bool
    before_after_reference_present: bool
    phase4i_score_contract_reference_present: bool
    rollback_reference_present: bool
    runtime_gate_reference_present: bool
    deterministic_fallback_available: bool
    score_scale_valid: bool
    confidence_scale_valid: bool
    runtime_active: bool = False
    scoring_config_applied: bool = False
    denied_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_next_steps: list[str] = field(default_factory=list)
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.eligibility_id, "eligibility_id")
        _require_nonempty_string(self.package_id, "package_id")
        _require_nonempty_string(self.manifest_id, "manifest_id")
        _require_boolean(self.eligible, "eligible")
        _require_supported(
            self.eligibility_status,
            SCORING_RUNTIME_ELIGIBILITY_STATUSES,
            "eligibility_status",
        )
        _require_boolean(
            self.required_validation_present,
            "required_validation_present",
        )
        _require_boolean(
            self.regression_reference_present,
            "regression_reference_present",
        )
        _require_boolean(
            self.before_after_reference_present,
            "before_after_reference_present",
        )
        _require_boolean(
            self.phase4i_score_contract_reference_present,
            "phase4i_score_contract_reference_present",
        )
        _require_boolean(
            self.rollback_reference_present,
            "rollback_reference_present",
        )
        _require_boolean(
            self.runtime_gate_reference_present,
            "runtime_gate_reference_present",
        )
        _require_true(
            self.deterministic_fallback_available,
            "deterministic_fallback_available",
        )
        _require_true(self.score_scale_valid, "score_scale_valid")
        _require_true(self.confidence_scale_valid, "confidence_scale_valid")
        _require_false(self.runtime_active, "runtime_active")
        _require_false(self.scoring_config_applied, "scoring_config_applied")
        _require_list_of_strings(self.denied_reasons, "denied_reasons")
        _require_list_of_strings(self.warnings, "warnings")
        _require_list_of_strings(self.required_next_steps, "required_next_steps")
        _require_optional_string(self.notes, "notes")
        if self.eligible:
            if self.eligibility_status != "eligible_metadata_only":
                raise ScoringRuntimeActivationError(
                    "eligible metadata must use eligible_metadata_only status."
                )
            missing = [
                not self.required_validation_present,
                not self.regression_reference_present,
                not self.before_after_reference_present,
                not self.phase4i_score_contract_reference_present,
                not self.rollback_reference_present,
                not self.runtime_gate_reference_present,
            ]
            if any(missing):
                raise ScoringRuntimeActivationError(
                    "eligible metadata requires all validation references."
                )


@dataclass(frozen=True)
class ScoringRollbackReference:
    """Local rollback metadata for a future scoring runtime config update."""

    rollback_id: str
    package_id: str
    rollback_strategy: str
    rollback_reference: str
    rollback_validated: bool = False
    rollback_executed: bool = False
    scoring_config_reverted: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.rollback_id, "rollback_id")
        _require_nonempty_string(self.package_id, "package_id")
        _require_nonempty_string(self.rollback_strategy, "rollback_strategy")
        _require_nonempty_string(self.rollback_reference, "rollback_reference")
        _require_boolean(self.rollback_validated, "rollback_validated")
        _require_false(self.rollback_executed, "rollback_executed")
        _require_false(self.scoring_config_reverted, "scoring_config_reverted")
        _require_optional_string(self.notes, "notes")


@dataclass(frozen=True)
class ScoringRegressionEvidence:
    """Local regression evidence metadata for future scoring config review."""

    regression_id: str
    package_id: str
    test_suite_reference: str
    before_after_reference: str
    score_contract_reference: str
    regression_passed: bool
    score_scale_valid: bool
    confidence_scale_valid: bool
    phase4i_contract_preserved: bool
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_nonempty_string(self.regression_id, "regression_id")
        _require_nonempty_string(self.package_id, "package_id")
        _require_nonempty_string(self.test_suite_reference, "test_suite_reference")
        _require_nonempty_string(self.before_after_reference, "before_after_reference")
        _require_nonempty_string(self.score_contract_reference, "score_contract_reference")
        _require_boolean(self.regression_passed, "regression_passed")
        _require_true(self.score_scale_valid, "score_scale_valid")
        _require_true(self.confidence_scale_valid, "confidence_scale_valid")
        _require_true(
            self.phase4i_contract_preserved,
            "phase4i_contract_preserved",
        )
        _require_optional_string(self.notes, "notes")


def create_scoring_runtime_package_id(
    source_scoring_review_id: str,
    scoring_config_version: str,
) -> str:
    """Create a deterministic scoring runtime package id."""

    _require_nonempty_string(source_scoring_review_id, "source_scoring_review_id")
    _require_nonempty_string(scoring_config_version, "scoring_config_version")
    return (
        "SCORING-RUNTIME-PACKAGE-"
        f"{_normalize_token(source_scoring_review_id)}-"
        f"{_normalize_token(scoring_config_version)}"
    )


def create_scoring_activation_manifest_id(
    package_id: str,
    manifest_version: str,
) -> str:
    """Create a deterministic scoring activation manifest id."""

    _require_nonempty_string(package_id, "package_id")
    _require_nonempty_string(manifest_version, "manifest_version")
    return (
        "SCORING-RUNTIME-MANIFEST-"
        f"{_normalize_token(package_id)}-"
        f"{_normalize_token(manifest_version)}"
    )


def create_scoring_runtime_eligibility_id(
    package_id: str,
    manifest_id: str,
) -> str:
    """Create a deterministic scoring runtime eligibility id."""

    _require_nonempty_string(package_id, "package_id")
    _require_nonempty_string(manifest_id, "manifest_id")
    return (
        "SCORING-RUNTIME-ELIGIBILITY-"
        f"{_normalize_token(package_id)}-"
        f"{_normalize_token(manifest_id)}"
    )


def create_scoring_rollback_id(package_id: str, rollback_strategy: str) -> str:
    """Create a deterministic scoring rollback id."""

    _require_nonempty_string(package_id, "package_id")
    _require_nonempty_string(rollback_strategy, "rollback_strategy")
    return (
        "SCORING-RUNTIME-ROLLBACK-"
        f"{_normalize_token(package_id)}-"
        f"{_normalize_token(rollback_strategy)}"
    )


def create_scoring_regression_id(package_id: str, reference: str) -> str:
    """Create a deterministic scoring regression evidence id."""

    _require_nonempty_string(package_id, "package_id")
    _require_nonempty_string(reference, "reference")
    return (
        "SCORING-REGRESSION-"
        f"{_normalize_token(package_id)}-"
        f"{_normalize_token(reference)}"
    )


def validate_scoring_runtime_config_package(
    package: ScoringRuntimeConfigPackage,
) -> ScoringRuntimeConfigPackage:
    """Validate scoring runtime config package metadata without applying it."""

    if not isinstance(package, ScoringRuntimeConfigPackage):
        raise ScoringRuntimeActivationError(
            "package must be a ScoringRuntimeConfigPackage instance."
        )
    package.__post_init__()
    return package


def validate_scoring_activation_manifest(
    manifest: ScoringActivationManifest,
) -> ScoringActivationManifest:
    """Validate scoring activation manifest metadata without activation."""

    if not isinstance(manifest, ScoringActivationManifest):
        raise ScoringRuntimeActivationError(
            "manifest must be a ScoringActivationManifest instance."
        )
    manifest.__post_init__()
    return manifest


def validate_scoring_runtime_eligibility_record(
    record: ScoringRuntimeEligibilityRecord,
) -> ScoringRuntimeEligibilityRecord:
    """Validate scoring runtime eligibility metadata without activation."""

    if not isinstance(record, ScoringRuntimeEligibilityRecord):
        raise ScoringRuntimeActivationError(
            "record must be a ScoringRuntimeEligibilityRecord instance."
        )
    record.__post_init__()
    return record


def validate_scoring_rollback_reference(
    rollback: ScoringRollbackReference,
) -> ScoringRollbackReference:
    """Validate scoring rollback metadata without executing rollback."""

    if not isinstance(rollback, ScoringRollbackReference):
        raise ScoringRuntimeActivationError(
            "rollback must be a ScoringRollbackReference instance."
        )
    rollback.__post_init__()
    return rollback


def validate_scoring_regression_evidence(
    evidence: ScoringRegressionEvidence,
) -> ScoringRegressionEvidence:
    """Validate scoring regression evidence metadata without running tests."""

    if not isinstance(evidence, ScoringRegressionEvidence):
        raise ScoringRuntimeActivationError(
            "evidence must be a ScoringRegressionEvidence instance."
        )
    evidence.__post_init__()
    return evidence


def evaluate_scoring_runtime_eligibility(
    package: ScoringRuntimeConfigPackage,
    manifest: ScoringActivationManifest,
) -> ScoringRuntimeEligibilityRecord:
    """Evaluate scoring package eligibility as metadata only."""

    package = validate_scoring_runtime_config_package(package)
    manifest = validate_scoring_activation_manifest(manifest)

    denied_reasons: list[str] = []
    warnings = [
        "Phase 7BW eligibility is metadata only; scoring_config_applied=false.",
        "Runtime scoring remains inactive; runtime_active=false.",
        "Deterministic scoring fallback remains required.",
    ]
    required_next_steps: list[str] = []

    regression_reference_present = bool(_optional_text(package.regression_reference))
    before_after_reference_present = bool(
        _optional_text(package.before_after_reference)
    )
    phase4i_score_contract_reference_present = bool(
        _optional_text(package.phase4i_score_contract_reference)
    )
    rollback_reference_present = bool(
        _optional_text(package.rollback_reference)
        and _optional_text(manifest.rollback_reference)
    )
    runtime_gate_reference_present = bool(
        _optional_text(manifest.runtime_gate_reference)
    )
    required_validation_present = bool(_optional_text(manifest.validation_reference))
    score_scale_valid = package.score_scale == SCORE_SCALE
    confidence_scale_valid = package.confidence_scale == CONFIDENCE_SCALE

    eligibility_status = "eligible_metadata_only"
    if package.package_status != ELIGIBILITY_PACKAGE_STATUS:
        eligibility_status = "not_eligible"
        denied_reasons.append(
            "package_status must be eligible_for_runtime_review for metadata eligibility"
        )
        required_next_steps.append("advance package metadata through governance review")
    elif not score_scale_valid:
        eligibility_status = "invalid_score_scale"
        denied_reasons.append("score_scale must be 0_100")
        required_next_steps.append("preserve 0_100 score scale")
    elif not confidence_scale_valid:
        eligibility_status = "invalid_confidence_scale"
        denied_reasons.append("confidence_scale must be 0_1")
        required_next_steps.append("preserve 0_1 confidence scale")
    elif not regression_reference_present:
        eligibility_status = "needs_regression_reference"
        denied_reasons.append("regression_reference is required")
        required_next_steps.append("attach scoring regression evidence reference")
    elif not before_after_reference_present:
        eligibility_status = "needs_before_after_reference"
        denied_reasons.append("before_after_reference is required")
        required_next_steps.append("attach before/after comparison reference")
    elif not phase4i_score_contract_reference_present:
        eligibility_status = "needs_phase4i_score_contract"
        denied_reasons.append("phase4i_score_contract_reference is required")
        required_next_steps.append("attach Phase 4I score contract evidence")
    elif not rollback_reference_present:
        eligibility_status = "needs_rollback_reference"
        denied_reasons.append("rollback_reference is required on package and manifest")
        required_next_steps.append("attach rollback reference metadata")
    elif not runtime_gate_reference_present:
        eligibility_status = "needs_runtime_gate"
        denied_reasons.append("runtime_gate_reference is required")
        required_next_steps.append("attach runtime gate review reference")
    elif not required_validation_present:
        eligibility_status = "needs_phase4i_score_contract"
        denied_reasons.append("manifest validation_reference is required")
        required_next_steps.append("attach manifest validation reference")
    else:
        required_next_steps.append("future runtime review may consider this package")
        required_next_steps.append("explicit activation remains required in a future phase")

    eligible = eligibility_status == "eligible_metadata_only"
    return validate_scoring_runtime_eligibility_record(
        ScoringRuntimeEligibilityRecord(
            eligibility_id=create_scoring_runtime_eligibility_id(
                package.package_id,
                manifest.manifest_id,
            ),
            package_id=package.package_id,
            manifest_id=manifest.manifest_id,
            eligible=eligible,
            eligibility_status=eligibility_status,
            required_validation_present=required_validation_present,
            regression_reference_present=regression_reference_present,
            before_after_reference_present=before_after_reference_present,
            phase4i_score_contract_reference_present=(
                phase4i_score_contract_reference_present
            ),
            rollback_reference_present=rollback_reference_present,
            runtime_gate_reference_present=runtime_gate_reference_present,
            deterministic_fallback_available=True,
            score_scale_valid=True,
            confidence_scale_valid=True,
            runtime_active=False,
            scoring_config_applied=False,
            denied_reasons=denied_reasons,
            warnings=warnings,
            required_next_steps=required_next_steps,
            notes=package.notes,
        )
    )


def scoring_runtime_config_package_to_dict(
    package: ScoringRuntimeConfigPackage,
) -> dict[str, Any]:
    """Serialize scoring runtime config package metadata."""

    package.__post_init__()
    return {
        "package_id": package.package_id,
        "source_scoring_review_id": package.source_scoring_review_id,
        "source_materialization_id": package.source_materialization_id,
        "scoring_config_version": package.scoring_config_version,
        "affected_domains": list(package.affected_domains),
        "affected_components": list(package.affected_components),
        "proposed_config_summary": package.proposed_config_summary,
        "score_scale": package.score_scale,
        "confidence_scale": package.confidence_scale,
        "weight_changes": dict(package.weight_changes),
        "threshold_changes": dict(package.threshold_changes),
        "severity_cutoff_changes": dict(package.severity_cutoff_changes),
        "confidence_rule_changes": dict(package.confidence_rule_changes),
        "trend_sensitivity_changes": dict(package.trend_sensitivity_changes),
        "anomaly_sensitivity_changes": dict(package.anomaly_sensitivity_changes),
        "before_after_reference": package.before_after_reference,
        "regression_reference": package.regression_reference,
        "phase4i_score_contract_reference": (
            package.phase4i_score_contract_reference
        ),
        "rollback_reference": package.rollback_reference,
        "package_status": package.package_status,
        "runtime_eligible": package.runtime_eligible,
        "runtime_active": package.runtime_active,
        "scoring_config_applied": package.scoring_config_applied,
        "score_output_mutation_performed": (
            package.score_output_mutation_performed
        ),
        "phase4i_mutation_performed": package.phase4i_mutation_performed,
        "created_by": package.created_by,
        "created_at": package.created_at,
        "notes": package.notes,
    }


def scoring_runtime_config_package_from_dict(
    data: dict[str, Any],
) -> ScoringRuntimeConfigPackage:
    """Deserialize scoring runtime config package metadata."""

    _require_mapping(data, "data")
    return ScoringRuntimeConfigPackage(
        package_id=str(data["package_id"]),
        source_scoring_review_id=str(data["source_scoring_review_id"]),
        source_materialization_id=str(data["source_materialization_id"]),
        scoring_config_version=str(data["scoring_config_version"]),
        affected_domains=list(data.get("affected_domains") or []),
        affected_components=list(data.get("affected_components") or []),
        proposed_config_summary=str(data["proposed_config_summary"]),
        score_scale=str(data.get("score_scale", SCORE_SCALE)),
        confidence_scale=str(data.get("confidence_scale", CONFIDENCE_SCALE)),
        weight_changes=dict(data.get("weight_changes") or {}),
        threshold_changes=dict(data.get("threshold_changes") or {}),
        severity_cutoff_changes=dict(data.get("severity_cutoff_changes") or {}),
        confidence_rule_changes=dict(data.get("confidence_rule_changes") or {}),
        trend_sensitivity_changes=dict(data.get("trend_sensitivity_changes") or {}),
        anomaly_sensitivity_changes=dict(
            data.get("anomaly_sensitivity_changes") or {}
        ),
        before_after_reference=_optional_text(data.get("before_after_reference")),
        regression_reference=_optional_text(data.get("regression_reference")),
        phase4i_score_contract_reference=_optional_text(
            data.get("phase4i_score_contract_reference")
        ),
        rollback_reference=_optional_text(data.get("rollback_reference")),
        package_status=str(data.get("package_status", "proposed")),
        runtime_eligible=_bool_from_mapping(data, "runtime_eligible", False),
        runtime_active=_bool_from_mapping(data, "runtime_active", False),
        scoring_config_applied=_bool_from_mapping(
            data,
            "scoring_config_applied",
            False,
        ),
        score_output_mutation_performed=_bool_from_mapping(
            data,
            "score_output_mutation_performed",
            False,
        ),
        phase4i_mutation_performed=_bool_from_mapping(
            data,
            "phase4i_mutation_performed",
            False,
        ),
        created_by=_optional_text(data.get("created_by")),
        created_at=_optional_text(data.get("created_at")),
        notes=_optional_text(data.get("notes")),
    )


def scoring_activation_manifest_to_dict(
    manifest: ScoringActivationManifest,
) -> dict[str, Any]:
    """Serialize scoring activation manifest metadata."""

    manifest.__post_init__()
    return {
        "manifest_id": manifest.manifest_id,
        "package_id": manifest.package_id,
        "manifest_version": manifest.manifest_version,
        "activation_mode": manifest.activation_mode,
        "explicit_activation_required": manifest.explicit_activation_required,
        "validation_reference": manifest.validation_reference,
        "rollback_reference": manifest.rollback_reference,
        "runtime_gate_reference": manifest.runtime_gate_reference,
        "deterministic_fallback_available": (
            manifest.deterministic_fallback_available
        ),
        "phase4i_score_contract_preserved": (
            manifest.phase4i_score_contract_preserved
        ),
        "runtime_activation_requested": manifest.runtime_activation_requested,
        "runtime_activation_approved": manifest.runtime_activation_approved,
        "runtime_active": manifest.runtime_active,
        "scoring_config_applied": manifest.scoring_config_applied,
        "created_by": manifest.created_by,
        "created_at": manifest.created_at,
        "notes": manifest.notes,
    }


def scoring_activation_manifest_from_dict(
    data: dict[str, Any],
) -> ScoringActivationManifest:
    """Deserialize scoring activation manifest metadata."""

    _require_mapping(data, "data")
    return ScoringActivationManifest(
        manifest_id=str(data["manifest_id"]),
        package_id=str(data["package_id"]),
        manifest_version=str(data["manifest_version"]),
        activation_mode=str(data.get("activation_mode", DEFAULT_ACTIVATION_MODE)),
        explicit_activation_required=_bool_from_mapping(
            data,
            "explicit_activation_required",
            True,
        ),
        validation_reference=_optional_text(data.get("validation_reference")),
        rollback_reference=_optional_text(data.get("rollback_reference")),
        runtime_gate_reference=_optional_text(data.get("runtime_gate_reference")),
        deterministic_fallback_available=_bool_from_mapping(
            data,
            "deterministic_fallback_available",
            True,
        ),
        phase4i_score_contract_preserved=_bool_from_mapping(
            data,
            "phase4i_score_contract_preserved",
            True,
        ),
        runtime_activation_requested=_bool_from_mapping(
            data,
            "runtime_activation_requested",
            False,
        ),
        runtime_activation_approved=_bool_from_mapping(
            data,
            "runtime_activation_approved",
            False,
        ),
        runtime_active=_bool_from_mapping(data, "runtime_active", False),
        scoring_config_applied=_bool_from_mapping(
            data,
            "scoring_config_applied",
            False,
        ),
        created_by=_optional_text(data.get("created_by")),
        created_at=_optional_text(data.get("created_at")),
        notes=_optional_text(data.get("notes")),
    )


def scoring_runtime_eligibility_record_to_dict(
    record: ScoringRuntimeEligibilityRecord,
) -> dict[str, Any]:
    """Serialize scoring runtime eligibility metadata."""

    record.__post_init__()
    return {
        "eligibility_id": record.eligibility_id,
        "package_id": record.package_id,
        "manifest_id": record.manifest_id,
        "eligible": record.eligible,
        "eligibility_status": record.eligibility_status,
        "required_validation_present": record.required_validation_present,
        "regression_reference_present": record.regression_reference_present,
        "before_after_reference_present": record.before_after_reference_present,
        "phase4i_score_contract_reference_present": (
            record.phase4i_score_contract_reference_present
        ),
        "rollback_reference_present": record.rollback_reference_present,
        "runtime_gate_reference_present": record.runtime_gate_reference_present,
        "deterministic_fallback_available": record.deterministic_fallback_available,
        "score_scale_valid": record.score_scale_valid,
        "confidence_scale_valid": record.confidence_scale_valid,
        "runtime_active": record.runtime_active,
        "scoring_config_applied": record.scoring_config_applied,
        "denied_reasons": list(record.denied_reasons),
        "warnings": list(record.warnings),
        "required_next_steps": list(record.required_next_steps),
        "notes": record.notes,
    }


def scoring_runtime_eligibility_record_from_dict(
    data: dict[str, Any],
) -> ScoringRuntimeEligibilityRecord:
    """Deserialize scoring runtime eligibility metadata."""

    _require_mapping(data, "data")
    return ScoringRuntimeEligibilityRecord(
        eligibility_id=str(data["eligibility_id"]),
        package_id=str(data["package_id"]),
        manifest_id=str(data["manifest_id"]),
        eligible=_bool_from_mapping(data, "eligible", False),
        eligibility_status=str(data["eligibility_status"]),
        required_validation_present=_bool_from_mapping(
            data,
            "required_validation_present",
            False,
        ),
        regression_reference_present=_bool_from_mapping(
            data,
            "regression_reference_present",
            False,
        ),
        before_after_reference_present=_bool_from_mapping(
            data,
            "before_after_reference_present",
            False,
        ),
        phase4i_score_contract_reference_present=_bool_from_mapping(
            data,
            "phase4i_score_contract_reference_present",
            False,
        ),
        rollback_reference_present=_bool_from_mapping(
            data,
            "rollback_reference_present",
            False,
        ),
        runtime_gate_reference_present=_bool_from_mapping(
            data,
            "runtime_gate_reference_present",
            False,
        ),
        deterministic_fallback_available=_bool_from_mapping(
            data,
            "deterministic_fallback_available",
            True,
        ),
        score_scale_valid=_bool_from_mapping(data, "score_scale_valid", True),
        confidence_scale_valid=_bool_from_mapping(
            data,
            "confidence_scale_valid",
            True,
        ),
        runtime_active=_bool_from_mapping(data, "runtime_active", False),
        scoring_config_applied=_bool_from_mapping(
            data,
            "scoring_config_applied",
            False,
        ),
        denied_reasons=list(data.get("denied_reasons") or []),
        warnings=list(data.get("warnings") or []),
        required_next_steps=list(data.get("required_next_steps") or []),
        notes=_optional_text(data.get("notes")),
    )


def scoring_rollback_reference_to_dict(
    rollback: ScoringRollbackReference,
) -> dict[str, Any]:
    """Serialize scoring rollback metadata."""

    rollback.__post_init__()
    return {
        "rollback_id": rollback.rollback_id,
        "package_id": rollback.package_id,
        "rollback_strategy": rollback.rollback_strategy,
        "rollback_reference": rollback.rollback_reference,
        "rollback_validated": rollback.rollback_validated,
        "rollback_executed": rollback.rollback_executed,
        "scoring_config_reverted": rollback.scoring_config_reverted,
        "notes": rollback.notes,
    }


def scoring_rollback_reference_from_dict(
    data: dict[str, Any],
) -> ScoringRollbackReference:
    """Deserialize scoring rollback metadata."""

    _require_mapping(data, "data")
    return ScoringRollbackReference(
        rollback_id=str(data["rollback_id"]),
        package_id=str(data["package_id"]),
        rollback_strategy=str(data["rollback_strategy"]),
        rollback_reference=str(data["rollback_reference"]),
        rollback_validated=_bool_from_mapping(data, "rollback_validated", False),
        rollback_executed=_bool_from_mapping(data, "rollback_executed", False),
        scoring_config_reverted=_bool_from_mapping(
            data,
            "scoring_config_reverted",
            False,
        ),
        notes=_optional_text(data.get("notes")),
    )


def scoring_regression_evidence_to_dict(
    evidence: ScoringRegressionEvidence,
) -> dict[str, Any]:
    """Serialize scoring regression evidence metadata."""

    evidence.__post_init__()
    return {
        "regression_id": evidence.regression_id,
        "package_id": evidence.package_id,
        "test_suite_reference": evidence.test_suite_reference,
        "before_after_reference": evidence.before_after_reference,
        "score_contract_reference": evidence.score_contract_reference,
        "regression_passed": evidence.regression_passed,
        "score_scale_valid": evidence.score_scale_valid,
        "confidence_scale_valid": evidence.confidence_scale_valid,
        "phase4i_contract_preserved": evidence.phase4i_contract_preserved,
        "notes": evidence.notes,
    }


def scoring_regression_evidence_from_dict(
    data: dict[str, Any],
) -> ScoringRegressionEvidence:
    """Deserialize scoring regression evidence metadata."""

    _require_mapping(data, "data")
    return ScoringRegressionEvidence(
        regression_id=str(data["regression_id"]),
        package_id=str(data["package_id"]),
        test_suite_reference=str(data["test_suite_reference"]),
        before_after_reference=str(data["before_after_reference"]),
        score_contract_reference=str(data["score_contract_reference"]),
        regression_passed=_bool_from_mapping(data, "regression_passed", False),
        score_scale_valid=_bool_from_mapping(data, "score_scale_valid", True),
        confidence_scale_valid=_bool_from_mapping(
            data,
            "confidence_scale_valid",
            True,
        ),
        phase4i_contract_preserved=_bool_from_mapping(
            data,
            "phase4i_contract_preserved",
            True,
        ),
        notes=_optional_text(data.get("notes")),
    )


def _package_has_all_eligibility_metadata(
    package: ScoringRuntimeConfigPackage,
) -> bool:
    return (
        package.package_status == ELIGIBILITY_PACKAGE_STATUS
        and package.score_scale == SCORE_SCALE
        and package.confidence_scale == CONFIDENCE_SCALE
        and bool(_optional_text(package.regression_reference))
        and bool(_optional_text(package.before_after_reference))
        and bool(_optional_text(package.phase4i_score_contract_reference))
        and bool(_optional_text(package.rollback_reference))
    )


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _bool_from_mapping(data: dict[str, Any], field_name: str, default: bool) -> bool:
    value = data.get(field_name, default)
    if isinstance(value, bool):
        return value
    raise ScoringRuntimeActivationError(f"{field_name} must be a boolean.")


def _require_mapping(value: Any, field_name: str) -> None:
    if not isinstance(value, dict):
        raise ScoringRuntimeActivationError(f"{field_name} must be a mapping.")


def _require_nonempty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ScoringRuntimeActivationError(
            f"{field_name} must be a non-empty string."
        )


def _require_optional_string(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise ScoringRuntimeActivationError(f"{field_name} must be a string or None.")


def _require_supported(value: Any, supported: tuple[str, ...], field_name: str) -> None:
    if value not in supported:
        raise ScoringRuntimeActivationError(
            f"{field_name} must be one of: {', '.join(supported)}."
        )


def _require_boolean(value: Any, field_name: str) -> None:
    if not isinstance(value, bool):
        raise ScoringRuntimeActivationError(f"{field_name} must be a boolean.")


def _require_true(value: Any, field_name: str) -> None:
    _require_boolean(value, field_name)
    if not value:
        raise ScoringRuntimeActivationError(
            f"{field_name} must remain true in Phase 7BW."
        )


def _require_false(value: Any, field_name: str) -> None:
    _require_boolean(value, field_name)
    if value:
        raise ScoringRuntimeActivationError(
            f"{field_name} must remain false in Phase 7BW."
        )


def _require_list_of_strings(value: Any, field_name: str) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise ScoringRuntimeActivationError(
            f"{field_name} must be a list of strings."
        )


def _require_score_scale(value: Any) -> None:
    if value != SCORE_SCALE:
        raise ScoringRuntimeActivationError("score_scale must be 0_100.")


def _require_confidence_scale(value: Any) -> None:
    if value != CONFIDENCE_SCALE:
        raise ScoringRuntimeActivationError("confidence_scale must be 0_1.")


def _normalize_token(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text).strip("-")
    return text or "NONE"
