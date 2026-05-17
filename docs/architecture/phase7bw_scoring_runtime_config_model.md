# Phase 7BW Scoring Runtime Config Model

## Object Shapes

`ScoringRuntimeConfigPackage` includes `package_id`, `source_scoring_review_id`, `source_materialization_id`, `scoring_config_version`, `affected_domains`, `affected_components`, `proposed_config_summary`, `score_scale`, `confidence_scale`, `weight_changes`, `threshold_changes`, `severity_cutoff_changes`, `confidence_rule_changes`, `trend_sensitivity_changes`, `anomaly_sensitivity_changes`, `before_after_reference`, `regression_reference`, `phase4i_score_contract_reference`, `rollback_reference`, `package_status`, `runtime_eligible`, `runtime_active`, `scoring_config_applied`, `score_output_mutation_performed`, `phase4i_mutation_performed`, `created_by`, `created_at`, and `notes`.

`ScoringActivationManifest` includes `manifest_id`, `package_id`, `manifest_version`, `activation_mode`, `explicit_activation_required`, `validation_reference`, `rollback_reference`, `runtime_gate_reference`, `deterministic_fallback_available`, `phase4i_score_contract_preserved`, `runtime_activation_requested`, `runtime_activation_approved`, `runtime_active`, `scoring_config_applied`, `created_by`, `created_at`, and `notes`.

`ScoringRuntimeEligibilityRecord` includes `eligibility_id`, `package_id`, `manifest_id`, `eligible`, `eligibility_status`, `required_validation_present`, `regression_reference_present`, `before_after_reference_present`, `phase4i_score_contract_reference_present`, `rollback_reference_present`, `runtime_gate_reference_present`, `deterministic_fallback_available`, `score_scale_valid`, `confidence_scale_valid`, `runtime_active`, `scoring_config_applied`, `denied_reasons`, `warnings`, `required_next_steps`, and `notes`.

`ScoringRollbackReference` includes `rollback_id`, `package_id`, `rollback_strategy`, `rollback_reference`, `rollback_validated`, `rollback_executed`, `scoring_config_reverted`, and `notes`.

`ScoringRegressionEvidence` includes `regression_id`, `package_id`, `test_suite_reference`, `before_after_reference`, `score_contract_reference`, `regression_passed`, `score_scale_valid`, `confidence_scale_valid`, `phase4i_contract_preserved`, and `notes`.

## Package Statuses

The supported package statuses are `proposed`, `under_review`, `validation_required`, `regression_ready`, `eligible_for_runtime_review`, `rejected`, `superseded`, and `closed`. No status means active. Package status is governance metadata only.

## Eligibility Statuses

The supported eligibility statuses are `not_eligible`, `eligible_metadata_only`, `needs_regression_reference`, `needs_before_after_reference`, `needs_phase4i_score_contract`, `needs_rollback_reference`, `needs_runtime_gate`, `invalid_score_scale`, `invalid_confidence_scale`, and `blocked_by_safety`.

## Activation Modes

The supported activation modes are `disabled`, `manual_review_required`, `future_runtime_manifest`, and `emergency_disabled`. No activation mode activates scoring config in 7BW.

## Validation Rules

Packages require a package id, source scoring review id, source materialization id, scoring config version, list-shaped affected domains, list-shaped affected components, proposed config summary, `score_scale=0_100`, and `confidence_scale=0_1`. `regression_ready` and `eligible_for_runtime_review` packages require a rollback reference. `runtime_eligible=true` can only be metadata eligibility and requires all validation references plus eligible status. `runtime_active=false`, `scoring_config_applied=false`, `score_output_mutation_performed=false`, and `phase4i_mutation_performed=false` are mandatory.

Manifests require a manifest id, package id, manifest version, supported activation mode, `explicit_activation_required=true`, `deterministic_fallback_available=true`, and `phase4i_score_contract_preserved=true`. `runtime_activation_requested=false`, `runtime_activation_approved=false`, `runtime_active=false`, and `scoring_config_applied=false` are mandatory.

Eligibility records require an eligibility id, package id, manifest id, supported eligibility status, deterministic fallback, valid score scale, and valid confidence scale. If `eligible=true`, then regression reference, before/after reference, Phase 4I score contract reference, rollback reference, runtime gate reference, and manifest validation reference must all be present. eligible means metadata eligible, not active. `runtime_active=false` and `scoring_config_applied=false` are mandatory.

Rollback references require rollback id, package id, rollback strategy, and rollback reference. `rollback_executed=false` and `scoring_config_reverted=false` are mandatory.

Regression evidence requires regression id, package id, test suite reference, before/after reference, score contract reference, `score_scale_valid=true`, `confidence_scale_valid=true`, and `phase4i_contract_preserved=true`. It records evidence metadata and does not run tests.

## Serialization Rules

Each object has explicit to/from dictionary helpers. Serialization preserves all safety flags and references. Deserialization re-runs dataclass validation, so serialized data cannot bypass `runtime_active=false`, `scoring_config_applied=false`, deterministic fallback, Phase 4I preservation, rollback execution, score scale, or confidence scale guards.

## Deterministic IDs

Scoring package IDs follow `SCORING-RUNTIME-PACKAGE-<SCORING_REVIEW_ID>-<VERSION>`. Scoring manifest IDs follow `SCORING-RUNTIME-MANIFEST-<PACKAGE_ID>-<VERSION>`. Scoring eligibility IDs follow `SCORING-RUNTIME-ELIGIBILITY-<PACKAGE_ID>-<MANIFEST_ID>`. Scoring rollback IDs follow `SCORING-RUNTIME-ROLLBACK-<PACKAGE_ID>-<STRATEGY>`. Scoring regression IDs follow `SCORING-REGRESSION-<PACKAGE_ID>-<REFERENCE>`. IDs use no random UUID, timestamp, DB sequence, or external service.

## Runtime Safety

no scoring modules are modified, no scoring config is applied, no score output is changed, `runtime_active=false`, `scoring_config_applied=false`, score scale remains 0-100, confidence scale remains 0-1, deterministic fallback required, and phase 4i preserved. The model does not import scoring, parser, decision, recommendation, dashboard, CLI, database, network, or OCI runtime modules.

## Non-Goals

7BW does not edit scoring modules, scoring weights, scoring thresholds, severity cutoffs, confidence rules, trend/anomaly sensitivity, runtime scoring config, score output, parser modules, decision modules, recommendation modules, dashboard modules, CLI modules, database schema, generated dashboard HTML, or Phase 4I. It does not call `run_analysis.py`, invoke scoring runtime, persist scoring config, activate scoring config, implement 7BX, implement 7BY, implement 7BZ, or implement Phase 8.
