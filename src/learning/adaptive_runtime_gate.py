"""Phase 7AA.1 controlled adaptive runtime integration gate.

This module defines local deterministic records for deciding whether an
adaptive component may be considered for future runtime integration. It does
not apply adaptive behavior, mutate runtime scoring, change parser output,
change decisions, change recommendations, call services, or write databases.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence


ADAPTIVE_RUNTIME_MODES = (
    "deterministic_only",
    "shadow_only",
    "advisory_only",
    "controlled_runtime_candidate",
)

ADAPTIVE_COMPONENT_TYPES = (
    "scoring",
    "recommendation",
    "parser",
    "trend_aware_scoring",
    "shadow_ml",
    "model_registry",
    "materialization_artifact",
)

REQUIRED_RUNTIME_GATES = (
    "adaptive_runtime_enabled",
    "component_integration_enabled",
    "certification",
    "runtime_eligibility",
    "runtime_influence_allowed",
    "runtime_influence_granted",
    "fallback_to_deterministic",
    "rollback_reference",
    "validation_reference",
    "deterministic_runtime_authoritative",
    "phase4i_contract_preservation",
    "runtime_active_false",
)

ADAPTIVE_RUNTIME_CONFIG_FIELDS = (
    "config_id",
    "mode",
    "adaptive_runtime_enabled",
    "scoring_integration_enabled",
    "recommendation_integration_enabled",
    "parser_integration_enabled",
    "trend_aware_scoring_enabled",
    "shadow_ml_enabled",
    "model_registry_enabled",
    "materialization_artifact_enabled",
    "require_certification",
    "require_runtime_eligibility",
    "require_rollback_reference",
    "require_phase4i_contract_preservation",
    "fallback_to_deterministic",
    "runtime_influence_allowed",
    "deterministic_runtime_authoritative",
    "created_by",
    "notes",
)

ADAPTIVE_COMPONENT_ELIGIBILITY_FIELDS = (
    "component_id",
    "component_type",
    "artifact_id",
    "model_id",
    "certified",
    "runtime_eligible",
    "runtime_influence_granted",
    "runtime_active",
    "rollback_reference",
    "validation_reference",
    "phase4i_contract_preserved",
    "notes",
)

ADAPTIVE_RUNTIME_GATE_RESULT_FIELDS = (
    "gate_id",
    "config_id",
    "component_id",
    "component_type",
    "allowed",
    "denied_reasons",
    "warnings",
    "required_next_steps",
    "deterministic_runtime_authoritative",
    "runtime_influence_allowed",
    "fallback_to_deterministic",
    "phase4i_contract_preserved",
    "runtime_active",
    "runtime_influence_granted",
)

_COMPONENT_FLAG_BY_TYPE = {
    "scoring": "scoring_integration_enabled",
    "recommendation": "recommendation_integration_enabled",
    "parser": "parser_integration_enabled",
    "trend_aware_scoring": "trend_aware_scoring_enabled",
    "shadow_ml": "shadow_ml_enabled",
    "model_registry": "model_registry_enabled",
    "materialization_artifact": "materialization_artifact_enabled",
}


class AdaptiveRuntimeGateError(ValueError):
    """Raised when Phase 7AA.1 runtime gate rules are violated."""


@dataclass(frozen=True)
class AdaptiveRuntimeConfig:
    """Local configuration for adaptive runtime consideration only."""

    config_id: str
    mode: str = "deterministic_only"
    adaptive_runtime_enabled: bool = False
    scoring_integration_enabled: bool = False
    recommendation_integration_enabled: bool = False
    parser_integration_enabled: bool = False
    trend_aware_scoring_enabled: bool = False
    shadow_ml_enabled: bool = False
    model_registry_enabled: bool = False
    materialization_artifact_enabled: bool = False
    require_certification: bool = True
    require_runtime_eligibility: bool = True
    require_rollback_reference: bool = True
    require_phase4i_contract_preservation: bool = True
    fallback_to_deterministic: bool = True
    runtime_influence_allowed: bool = False
    deterministic_runtime_authoritative: bool = True
    created_by: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.config_id, "config_id")
        mode = _normalize_mode(self.mode)
        for field_name in (
            "adaptive_runtime_enabled",
            "scoring_integration_enabled",
            "recommendation_integration_enabled",
            "parser_integration_enabled",
            "trend_aware_scoring_enabled",
            "shadow_ml_enabled",
            "model_registry_enabled",
            "materialization_artifact_enabled",
            "require_certification",
            "require_runtime_eligibility",
            "require_rollback_reference",
            "require_phase4i_contract_preservation",
            "fallback_to_deterministic",
            "runtime_influence_allowed",
            "deterministic_runtime_authoritative",
        ):
            _validate_bool(getattr(self, field_name), field_name)
        _require_true(
            self.deterministic_runtime_authoritative,
            "deterministic_runtime_authoritative",
        )
        if self.adaptive_runtime_enabled and not self.fallback_to_deterministic:
            raise AdaptiveRuntimeGateError(
                "fallback_to_deterministic=false is not allowed when "
                "adaptive_runtime_enabled=true."
            )
        if mode == "deterministic_only" and self.runtime_influence_allowed:
            raise AdaptiveRuntimeGateError(
                "deterministic_only mode cannot allow runtime influence."
            )
        _validate_optional_string(self.created_by, "created_by")
        _validate_optional_string(self.notes, "notes")

        object.__setattr__(self, "config_id", self.config_id.strip())
        object.__setattr__(self, "mode", mode)
        object.__setattr__(
            self,
            "created_by",
            _normalize_optional_string(self.created_by),
        )
        object.__setattr__(self, "notes", _normalize_optional_string(self.notes))


@dataclass(frozen=True)
class AdaptiveComponentEligibility:
    """Local eligibility record for one adaptive component or artifact."""

    component_id: str
    component_type: str
    artifact_id: str | None = None
    model_id: str | None = None
    certified: bool = False
    runtime_eligible: bool = False
    runtime_influence_granted: bool = False
    runtime_active: bool = False
    rollback_reference: str | None = None
    validation_reference: str | None = None
    phase4i_contract_preserved: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        _require_non_empty_string(self.component_id, "component_id")
        component_type = _normalize_component_type(self.component_type)
        _validate_optional_string(self.artifact_id, "artifact_id")
        _validate_optional_string(self.model_id, "model_id")
        for field_name in (
            "certified",
            "runtime_eligible",
            "runtime_influence_granted",
            "runtime_active",
            "phase4i_contract_preserved",
        ):
            _validate_bool(getattr(self, field_name), field_name)
        _require_false(self.runtime_active, "runtime_active")
        _validate_optional_string(self.rollback_reference, "rollback_reference")
        _validate_optional_string(self.validation_reference, "validation_reference")
        _validate_optional_string(self.notes, "notes")

        object.__setattr__(self, "component_id", self.component_id.strip())
        object.__setattr__(self, "component_type", component_type)
        object.__setattr__(
            self,
            "artifact_id",
            _normalize_optional_string(self.artifact_id),
        )
        object.__setattr__(self, "model_id", _normalize_optional_string(self.model_id))
        object.__setattr__(
            self,
            "rollback_reference",
            _normalize_optional_string(self.rollback_reference),
        )
        object.__setattr__(
            self,
            "validation_reference",
            _normalize_optional_string(self.validation_reference),
        )
        object.__setattr__(self, "notes", _normalize_optional_string(self.notes))


@dataclass(frozen=True)
class AdaptiveRuntimeGateResult:
    """Deterministic gate result for consideration, not activation."""

    gate_id: str
    config_id: str
    component_id: str
    component_type: str
    allowed: bool = False
    denied_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    required_next_steps: list[str] = field(default_factory=list)
    deterministic_runtime_authoritative: bool = True
    runtime_influence_allowed: bool = False
    fallback_to_deterministic: bool = True
    phase4i_contract_preserved: bool = False
    runtime_active: bool = False
    runtime_influence_granted: bool = False

    @property
    def allowed_for_consideration(self) -> bool:
        """Return true when every 7AA.1 gate passed for future consideration."""

        return self.allowed

    def __post_init__(self) -> None:
        _require_non_empty_string(self.gate_id, "gate_id")
        _require_non_empty_string(self.config_id, "config_id")
        _require_non_empty_string(self.component_id, "component_id")
        component_type = _normalize_component_type(self.component_type)
        for field_name in (
            "allowed",
            "deterministic_runtime_authoritative",
            "runtime_influence_allowed",
            "fallback_to_deterministic",
            "phase4i_contract_preserved",
            "runtime_active",
            "runtime_influence_granted",
        ):
            _validate_bool(getattr(self, field_name), field_name)
        _require_true(
            self.deterministic_runtime_authoritative,
            "deterministic_runtime_authoritative",
        )
        _require_false(self.runtime_active, "runtime_active")
        if self.allowed and not self.fallback_to_deterministic:
            raise AdaptiveRuntimeGateError(
                "allowed gate results require fallback_to_deterministic=true."
            )
        if self.allowed and not self.runtime_influence_allowed:
            raise AdaptiveRuntimeGateError(
                "allowed gate results require runtime_influence_allowed=true."
            )
        if self.allowed and not self.runtime_influence_granted:
            raise AdaptiveRuntimeGateError(
                "allowed gate results require runtime_influence_granted=true."
            )
        object.__setattr__(self, "gate_id", self.gate_id.strip())
        object.__setattr__(self, "config_id", self.config_id.strip())
        object.__setattr__(self, "component_id", self.component_id.strip())
        object.__setattr__(self, "component_type", component_type)
        object.__setattr__(
            self,
            "denied_reasons",
            _normalize_string_list(self.denied_reasons, "denied_reasons"),
        )
        object.__setattr__(
            self,
            "warnings",
            _normalize_string_list(self.warnings, "warnings"),
        )
        object.__setattr__(
            self,
            "required_next_steps",
            _normalize_string_list(self.required_next_steps, "required_next_steps"),
        )


def create_adaptive_runtime_config_id(
    mode: str,
    created_by: str | None = None,
) -> str:
    """Create a deterministic adaptive runtime config identifier."""

    normalized_mode = _normalize_mode(mode)
    if created_by is not None:
        _validate_optional_string(created_by, "created_by")
    actor = created_by if _has_text(created_by) else "system"
    return (
        f"ADAPTIVE-RUNTIME-CONFIG-{_identifier_fragment(normalized_mode)}-"
        f"{_identifier_fragment(actor)}"
    )


def create_component_eligibility_id(
    component_type: str,
    artifact_id: str | None = None,
    model_id: str | None = None,
) -> str:
    """Create a deterministic adaptive component eligibility identifier."""

    normalized_type = _normalize_component_type(component_type)
    _validate_optional_string(artifact_id, "artifact_id")
    _validate_optional_string(model_id, "model_id")
    source = artifact_id if _has_text(artifact_id) else model_id
    source = source if _has_text(source) else "unscoped"
    return (
        f"ADAPTIVE-COMPONENT-{_identifier_fragment(normalized_type)}-"
        f"{_identifier_fragment(source)}"
    )


def create_gate_result_id(config_id: str, component_id: str) -> str:
    """Create a deterministic adaptive runtime gate result identifier."""

    _require_non_empty_string(config_id, "config_id")
    _require_non_empty_string(component_id, "component_id")
    return (
        f"ADAPTIVE-GATE-{_identifier_fragment(config_id)}-"
        f"{_identifier_fragment(component_id)}"
    )


def validate_adaptive_runtime_config(
    config: AdaptiveRuntimeConfig | Mapping[str, Any],
) -> AdaptiveRuntimeConfig:
    """Validate and return an adaptive runtime config."""

    if isinstance(config, Mapping):
        return adaptive_runtime_config_from_dict(config)
    if not isinstance(config, AdaptiveRuntimeConfig):
        raise AdaptiveRuntimeGateError("config must be AdaptiveRuntimeConfig.")
    return AdaptiveRuntimeConfig(**adaptive_runtime_config_to_dict(config))


def validate_component_eligibility(
    eligibility: AdaptiveComponentEligibility | Mapping[str, Any],
) -> AdaptiveComponentEligibility:
    """Validate and return component eligibility."""

    if isinstance(eligibility, Mapping):
        return component_eligibility_from_dict(eligibility)
    if not isinstance(eligibility, AdaptiveComponentEligibility):
        raise AdaptiveRuntimeGateError(
            "eligibility must be AdaptiveComponentEligibility."
        )
    return AdaptiveComponentEligibility(**component_eligibility_to_dict(eligibility))


def evaluate_adaptive_runtime_gate(
    config: AdaptiveRuntimeConfig | Mapping[str, Any],
    eligibility: AdaptiveComponentEligibility | Mapping[str, Any],
) -> AdaptiveRuntimeGateResult:
    """Evaluate whether a component may be considered for future integration."""

    current_config = validate_adaptive_runtime_config(config)
    current_eligibility = validate_component_eligibility(eligibility)
    denied_reasons: list[str] = []
    warnings: list[str] = []
    required_next_steps: list[str] = []

    _deny_unless(
        current_config.adaptive_runtime_enabled,
        "adaptive_runtime_disabled",
        "Enable adaptive_runtime_enabled explicitly.",
        denied_reasons,
        required_next_steps,
    )
    _deny_unless(
        current_config.runtime_influence_allowed,
        "runtime_influence_not_allowed",
        "Set runtime_influence_allowed only after governance approval.",
        denied_reasons,
        required_next_steps,
    )
    _deny_unless(
        current_config.fallback_to_deterministic,
        "fallback_to_deterministic_required",
        "Provide deterministic fallback before runtime consideration.",
        denied_reasons,
        required_next_steps,
    )
    _deny_unless(
        current_config.deterministic_runtime_authoritative,
        "deterministic_runtime_authority_required",
        "Keep deterministic runtime authoritative.",
        denied_reasons,
        required_next_steps,
    )

    component_flag = _COMPONENT_FLAG_BY_TYPE[current_eligibility.component_type]
    _deny_unless(
        bool(getattr(current_config, component_flag)),
        f"{component_flag}_disabled",
        f"Enable {component_flag} for this component type.",
        denied_reasons,
        required_next_steps,
    )
    if current_config.require_certification:
        _deny_unless(
            current_eligibility.certified,
            "certification_required",
            "Attach certified component approval.",
            denied_reasons,
            required_next_steps,
        )
    if current_config.require_runtime_eligibility:
        _deny_unless(
            current_eligibility.runtime_eligible,
            "runtime_eligibility_required",
            "Mark the component explicitly runtime eligible.",
            denied_reasons,
            required_next_steps,
        )
    _deny_unless(
        current_eligibility.runtime_influence_granted
        and current_config.runtime_influence_allowed,
        "runtime_influence_grant_required",
        "Grant runtime influence only after the global gate allows it.",
        denied_reasons,
        required_next_steps,
    )
    if current_config.require_rollback_reference:
        _deny_unless(
            _has_text(current_eligibility.rollback_reference),
            "rollback_reference_required",
            "Attach rollback reference before runtime consideration.",
            denied_reasons,
            required_next_steps,
        )
    _deny_unless(
        _has_text(current_eligibility.validation_reference),
        "validation_reference_required",
        "Attach validation reference before runtime consideration.",
        denied_reasons,
        required_next_steps,
    )
    if current_config.require_phase4i_contract_preservation:
        _deny_unless(
            current_eligibility.phase4i_contract_preserved,
            "phase4i_contract_preservation_required",
            "Preserve or explicitly version the Phase 4I contract.",
            denied_reasons,
            required_next_steps,
        )
    _deny_unless(
        current_eligibility.runtime_active is False,
        "runtime_active_must_remain_false",
        "Keep runtime_active=false in Phase 7AA.1.",
        denied_reasons,
        required_next_steps,
    )

    if current_config.mode == "deterministic_only":
        warnings.append(
            "deterministic_only mode records denial context and does not activate runtime."
        )
    if not _has_text(current_eligibility.artifact_id) and not _has_text(
        current_eligibility.model_id
    ):
        warnings.append(
            "component eligibility has no artifact_id or model_id reference."
        )

    allowed = not denied_reasons
    gate_id = create_gate_result_id(
        current_config.config_id,
        current_eligibility.component_id,
    )
    return AdaptiveRuntimeGateResult(
        gate_id=gate_id,
        config_id=current_config.config_id,
        component_id=current_eligibility.component_id,
        component_type=current_eligibility.component_type,
        allowed=allowed,
        denied_reasons=denied_reasons,
        warnings=warnings,
        required_next_steps=required_next_steps,
        deterministic_runtime_authoritative=(
            current_config.deterministic_runtime_authoritative
        ),
        runtime_influence_allowed=current_config.runtime_influence_allowed,
        fallback_to_deterministic=current_config.fallback_to_deterministic,
        phase4i_contract_preserved=(
            current_eligibility.phase4i_contract_preserved
        ),
        runtime_active=False,
        runtime_influence_granted=(
            current_eligibility.runtime_influence_granted
            and current_config.runtime_influence_allowed
        ),
    )


def validate_gate_result(
    result: AdaptiveRuntimeGateResult | Mapping[str, Any],
) -> AdaptiveRuntimeGateResult:
    """Validate and return an adaptive runtime gate result."""

    if isinstance(result, Mapping):
        return gate_result_from_dict(result)
    if not isinstance(result, AdaptiveRuntimeGateResult):
        raise AdaptiveRuntimeGateError("result must be AdaptiveRuntimeGateResult.")
    return AdaptiveRuntimeGateResult(**gate_result_to_dict(result))


def adaptive_runtime_config_to_dict(config: AdaptiveRuntimeConfig) -> dict[str, Any]:
    """Serialize an adaptive runtime config to a deterministic dictionary."""

    if not isinstance(config, AdaptiveRuntimeConfig):
        raise AdaptiveRuntimeGateError("config must be AdaptiveRuntimeConfig.")
    return {
        "config_id": config.config_id,
        "mode": config.mode,
        "adaptive_runtime_enabled": config.adaptive_runtime_enabled,
        "scoring_integration_enabled": config.scoring_integration_enabled,
        "recommendation_integration_enabled": config.recommendation_integration_enabled,
        "parser_integration_enabled": config.parser_integration_enabled,
        "trend_aware_scoring_enabled": config.trend_aware_scoring_enabled,
        "shadow_ml_enabled": config.shadow_ml_enabled,
        "model_registry_enabled": config.model_registry_enabled,
        "materialization_artifact_enabled": config.materialization_artifact_enabled,
        "require_certification": config.require_certification,
        "require_runtime_eligibility": config.require_runtime_eligibility,
        "require_rollback_reference": config.require_rollback_reference,
        "require_phase4i_contract_preservation": (
            config.require_phase4i_contract_preservation
        ),
        "fallback_to_deterministic": config.fallback_to_deterministic,
        "runtime_influence_allowed": config.runtime_influence_allowed,
        "deterministic_runtime_authoritative": (
            config.deterministic_runtime_authoritative
        ),
        "created_by": config.created_by,
        "notes": config.notes,
    }


def adaptive_runtime_config_from_dict(
    data: Mapping[str, Any],
) -> AdaptiveRuntimeConfig:
    """Reconstruct and validate an adaptive runtime config from dictionary data."""

    if not isinstance(data, Mapping):
        raise AdaptiveRuntimeGateError("adaptive runtime config data must be a mapping.")
    values = _values_from_mapping(
        data,
        ADAPTIVE_RUNTIME_CONFIG_FIELDS,
        optional_defaults={
            "mode": "deterministic_only",
            "adaptive_runtime_enabled": False,
            "scoring_integration_enabled": False,
            "recommendation_integration_enabled": False,
            "parser_integration_enabled": False,
            "trend_aware_scoring_enabled": False,
            "shadow_ml_enabled": False,
            "model_registry_enabled": False,
            "materialization_artifact_enabled": False,
            "require_certification": True,
            "require_runtime_eligibility": True,
            "require_rollback_reference": True,
            "require_phase4i_contract_preservation": True,
            "fallback_to_deterministic": True,
            "runtime_influence_allowed": False,
            "deterministic_runtime_authoritative": True,
            "created_by": None,
            "notes": None,
        },
    )
    return AdaptiveRuntimeConfig(**values)


def component_eligibility_to_dict(
    eligibility: AdaptiveComponentEligibility,
) -> dict[str, Any]:
    """Serialize component eligibility to a deterministic dictionary."""

    if not isinstance(eligibility, AdaptiveComponentEligibility):
        raise AdaptiveRuntimeGateError(
            "eligibility must be AdaptiveComponentEligibility."
        )
    return {
        "component_id": eligibility.component_id,
        "component_type": eligibility.component_type,
        "artifact_id": eligibility.artifact_id,
        "model_id": eligibility.model_id,
        "certified": eligibility.certified,
        "runtime_eligible": eligibility.runtime_eligible,
        "runtime_influence_granted": eligibility.runtime_influence_granted,
        "runtime_active": eligibility.runtime_active,
        "rollback_reference": eligibility.rollback_reference,
        "validation_reference": eligibility.validation_reference,
        "phase4i_contract_preserved": eligibility.phase4i_contract_preserved,
        "notes": eligibility.notes,
    }


def component_eligibility_from_dict(
    data: Mapping[str, Any],
) -> AdaptiveComponentEligibility:
    """Reconstruct and validate component eligibility from dictionary data."""

    if not isinstance(data, Mapping):
        raise AdaptiveRuntimeGateError("component eligibility data must be a mapping.")
    values = _values_from_mapping(
        data,
        ADAPTIVE_COMPONENT_ELIGIBILITY_FIELDS,
        optional_defaults={
            "artifact_id": None,
            "model_id": None,
            "certified": False,
            "runtime_eligible": False,
            "runtime_influence_granted": False,
            "runtime_active": False,
            "rollback_reference": None,
            "validation_reference": None,
            "phase4i_contract_preserved": False,
            "notes": None,
        },
    )
    return AdaptiveComponentEligibility(**values)


def gate_result_to_dict(result: AdaptiveRuntimeGateResult) -> dict[str, Any]:
    """Serialize an adaptive runtime gate result to a deterministic dictionary."""

    if not isinstance(result, AdaptiveRuntimeGateResult):
        raise AdaptiveRuntimeGateError("result must be AdaptiveRuntimeGateResult.")
    return {
        "gate_id": result.gate_id,
        "config_id": result.config_id,
        "component_id": result.component_id,
        "component_type": result.component_type,
        "allowed": result.allowed,
        "denied_reasons": deepcopy(result.denied_reasons),
        "warnings": deepcopy(result.warnings),
        "required_next_steps": deepcopy(result.required_next_steps),
        "deterministic_runtime_authoritative": (
            result.deterministic_runtime_authoritative
        ),
        "runtime_influence_allowed": result.runtime_influence_allowed,
        "fallback_to_deterministic": result.fallback_to_deterministic,
        "phase4i_contract_preserved": result.phase4i_contract_preserved,
        "runtime_active": result.runtime_active,
        "runtime_influence_granted": result.runtime_influence_granted,
    }


def gate_result_from_dict(data: Mapping[str, Any]) -> AdaptiveRuntimeGateResult:
    """Reconstruct and validate an adaptive runtime gate result from dictionary data."""

    if not isinstance(data, Mapping):
        raise AdaptiveRuntimeGateError("gate result data must be a mapping.")
    values = _values_from_mapping(
        data,
        ADAPTIVE_RUNTIME_GATE_RESULT_FIELDS,
        optional_defaults={
            "allowed": False,
            "denied_reasons": [],
            "warnings": [],
            "required_next_steps": [],
            "deterministic_runtime_authoritative": True,
            "runtime_influence_allowed": False,
            "fallback_to_deterministic": True,
            "phase4i_contract_preserved": False,
            "runtime_active": False,
            "runtime_influence_granted": False,
        },
    )
    return AdaptiveRuntimeGateResult(**values)


def default_deterministic_runtime_config() -> AdaptiveRuntimeConfig:
    """Return the Phase 7AA.1 default deny-all deterministic runtime config."""

    return AdaptiveRuntimeConfig(
        config_id=create_adaptive_runtime_config_id(
            "deterministic_only",
            created_by="system",
        ),
        mode="deterministic_only",
        adaptive_runtime_enabled=False,
        scoring_integration_enabled=False,
        recommendation_integration_enabled=False,
        parser_integration_enabled=False,
        trend_aware_scoring_enabled=False,
        shadow_ml_enabled=False,
        model_registry_enabled=False,
        materialization_artifact_enabled=False,
        require_certification=True,
        require_runtime_eligibility=True,
        require_rollback_reference=True,
        require_phase4i_contract_preservation=True,
        fallback_to_deterministic=True,
        runtime_influence_allowed=False,
        deterministic_runtime_authoritative=True,
        created_by="system",
        notes="Phase 7AA.1 default denies adaptive runtime integration.",
    )


def _deny_unless(
    condition: bool,
    reason: str,
    next_step: str,
    denied_reasons: list[str],
    required_next_steps: list[str],
) -> None:
    if not condition:
        denied_reasons.append(reason)
        required_next_steps.append(next_step)


def _normalize_mode(value: Any) -> str:
    _require_non_empty_string(value, "mode")
    normalized = str(value).strip().lower().replace("-", "_")
    if normalized not in ADAPTIVE_RUNTIME_MODES:
        raise AdaptiveRuntimeGateError(f"Unsupported adaptive runtime mode: {value}.")
    return normalized


def _normalize_component_type(value: Any) -> str:
    _require_non_empty_string(value, "component_type")
    normalized = str(value).strip().lower().replace("-", "_")
    if normalized not in ADAPTIVE_COMPONENT_TYPES:
        raise AdaptiveRuntimeGateError(f"Unsupported adaptive component type: {value}.")
    return normalized


def _values_from_mapping(
    data: Mapping[str, Any],
    fields: Sequence[str],
    optional_defaults: Mapping[str, Any],
) -> dict[str, Any]:
    missing = [
        field_name
        for field_name in fields
        if field_name not in data and field_name not in optional_defaults
    ]
    if missing:
        raise AdaptiveRuntimeGateError(
            "Missing required fields: " + ", ".join(missing) + "."
        )
    return {
        field_name: deepcopy(data[field_name])
        if field_name in data
        else deepcopy(optional_defaults[field_name])
        for field_name in fields
    }


def _normalize_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise AdaptiveRuntimeGateError(f"{field_name} must be a list.")
    normalized: list[str] = []
    for item in value:
        _require_non_empty_string(item, field_name)
        normalized.append(str(item).strip())
    return normalized


def _require_true(value: Any, field_name: str) -> None:
    if value is not True:
        raise AdaptiveRuntimeGateError(
            f"Phase 7AA.1 runtime gate records require {field_name}=true."
        )


def _require_false(value: Any, field_name: str) -> None:
    if value is not False:
        raise AdaptiveRuntimeGateError(
            f"Phase 7AA.1 runtime gate records require {field_name}=false."
        )


def _validate_bool(value: Any, field_name: str) -> None:
    if not isinstance(value, bool):
        raise AdaptiveRuntimeGateError(f"{field_name} must be a boolean.")


def _require_non_empty_string(value: Any, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AdaptiveRuntimeGateError(f"{field_name} must be a non-empty string.")


def _validate_optional_string(value: Any, field_name: str) -> None:
    if value is not None and not isinstance(value, str):
        raise AdaptiveRuntimeGateError(f"{field_name} must be None or a string.")
    if isinstance(value, str) and not value.strip():
        raise AdaptiveRuntimeGateError(f"{field_name} must not be blank.")


def _normalize_optional_string(value: str | None) -> str | None:
    return None if value is None else value.strip()


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _identifier_fragment(value: Any) -> str:
    text = str(value or "").strip().upper()
    text = re.sub(r"[^A-Z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "UNSPECIFIED"
