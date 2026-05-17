# Phase 7BW Scoring Runtime Config Activation

## 1. Purpose

Phase 7BW defines the controlled scoring runtime config activation metadata path for the Agentic AI AWR Advisor project. It creates local models for scoring runtime config packages, activation manifests, runtime eligibility records, rollback references, and regression evidence before any future controlled scoring activation can be considered.

## 2. Scope

The scope is metadata only. 7BW models the future package and validation layer between approved scoring review artifacts and any future scoring runtime activation path. It adds no scoring implementation, no scoring configuration change, no scoring engine execution, no Phase 4I score mutation, and no runtime activation.

## 3. Non-Goals

7BW does not modify scoring source code, scoring weights, thresholds, severity cutoffs, confidence rules, trend/anomaly sensitivity, runtime scoring config, parser behavior, decision behavior, recommendation behavior, dashboard UI, CLI behavior, database schema, or generated dashboard HTML. It does not call `run_analysis.py`, does not run scoring, does not persist scoring config, does not create DB rows, does not mutate Phase 4I, and does not implement Phase 8.

## 4. Scoring Runtime Config Activation Is Not Runtime Scoring Mutation

Scoring runtime config activation metadata is not runtime scoring mutation. no scoring modules are modified, no scoring config is applied, no score output is changed, and runtime scoring is not invoked. `runtime_active=false`, `scoring_config_applied=false`, `score_output_mutation_performed=false`, and `phase4i_mutation_performed=false` remain mandatory.

## 5. ScoringRuntimeConfigPackage

`ScoringRuntimeConfigPackage` describes a future scoring configuration update candidate. It includes package identity, source scoring review and materialization references, config version, affected domains, affected components, proposed config summary, score scale, confidence scale, weight changes, threshold changes, severity cutoff changes, confidence rule changes, trend sensitivity changes, anomaly sensitivity changes, before/after reference, regression reference, Phase 4I score contract reference, rollback reference, package status, and safety flags. `runtime_eligible=false` by default, `runtime_active=false`, `scoring_config_applied=false`, `score_output_mutation_performed=false`, and `phase4i_mutation_performed=false`.

## 6. ScoringActivationManifest

`ScoringActivationManifest` describes future activation review metadata. It includes manifest identity, package reference, manifest version, activation mode, validation reference, rollback reference, runtime gate reference, deterministic fallback posture, Phase 4I score contract preservation, and activation flags. It always requires explicit activation, deterministic fallback, and Phase 4I score contract preservation. `runtime_activation_requested=false`, `runtime_activation_approved=false`, `runtime_active=false`, and `scoring_config_applied=false`.

## 7. ScoringRuntimeEligibilityRecord

`ScoringRuntimeEligibilityRecord` evaluates package and manifest metadata for future runtime review. eligible means metadata eligible, not active. An eligible record must have regression evidence, before/after comparison evidence, Phase 4I score contract evidence, rollback reference, runtime gate reference, manifest validation reference, deterministic fallback, score scale 0-100, confidence scale 0-1, and inactive runtime flags.

## 8. ScoringRollbackReference

`ScoringRollbackReference` records rollback strategy metadata for a future scoring runtime config update. It does not execute rollback. `rollback_executed=false` and `scoring_config_reverted=false` remain mandatory.

## 9. ScoringRegressionEvidence

`ScoringRegressionEvidence` records local metadata for regression evidence. It can say a regression passed as metadata, but 7BW does not run regression tests. It requires score scale validity, confidence scale validity, and Phase 4I contract preservation.

## 10. Score Scale Requirement

score scale remains 0-100. The package score scale must be `0_100`, and eligibility records require `score_scale_valid=true`. A scoring package with any other score scale is rejected.

## 11. Confidence Scale Requirement

confidence scale remains 0-1. The package confidence scale must be `0_1`, and eligibility records require `confidence_scale_valid=true`. A scoring package with any other confidence scale is rejected.

## 12. Before / After Comparison Requirement

A before/after comparison reference is required before metadata eligibility. The reference is evidence metadata only and does not cause score recomputation.

## 13. Regression Requirement

A regression reference is required before metadata eligibility. Regression evidence metadata can be recorded, but the model does not execute scoring tests.

## 14. Phase 4I Score Contract Requirement

A Phase 4I score contract reference is required. phase 4i preserved is mandatory: scoring activation metadata must not alter validated Phase 4I score semantics, score scale, confidence scale, or output contract.

## 15. Rollback Requirement

Rollback reference metadata is required for regression-ready and eligible packages. Rollback metadata is local only. 7BW does not execute rollback and does not revert scoring config.

## 16. Runtime Gate Requirement

A runtime gate reference is required before metadata eligibility. The gate reference is a future review link, not approval for activation.

## 17. Deterministic Fallback Requirement

deterministic fallback required: every manifest and eligibility record must keep deterministic scoring fallback available. If deterministic fallback is not available, validation fails.

## 18. Relationship to 7BU

7BU created the runtime materialization execution boundary, persistence/audit metadata, transaction metadata, and status transition metadata. 7BW builds on that posture by defining scoring-specific package metadata without performing persistence, status transition, scoring mutation, runtime activation, or Phase 4I mutation.

## 19. Relationship to 7O / 7AA.3 / 7BE-7BJ

7O defined proposal-only adaptive scoring review and inactive proposed scoring configs. 7AA.3 defined advisory scoring integration where deterministic scoring remains authoritative. 7BE-7BJ defined Screen 5 recommendation/action/outcome workflow metadata. 7BW creates the scoring runtime config package layer after review and materialization records but before any future scoring config is applied.

## 20. Relationship to Future 7BX-7BZ

7BX recommendation runtime rule activation, 7BY ML runtime eligibility, and 7BZ final validation are future phases. 7BW does not implement them and does not jump ahead into recommendation, ML, or certification work.

## 21. Acceptance Criteria

7BW is accepted when scoring runtime config package, activation manifest, eligibility, rollback, and regression evidence metadata models exist; deterministic IDs exist; serialization and deserialization helpers exist; validation rejects runtime activation, scoring config application, score output mutation, Phase 4I mutation, rollback execution, missing deterministic fallback, missing Phase 4I preservation, invalid score scale, and invalid confidence scale; tests prove no scoring runtime imports; no scoring code or config is modified; no scoring output is changed; no scoring config is applied; deterministic runtime remains authoritative; and Phase 8 is not implemented.
