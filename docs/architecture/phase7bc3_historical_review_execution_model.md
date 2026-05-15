# Phase 7BC.3 Historical Review Execution Model

## 1. Purpose

Phase 7BC.3 defines the concrete local object model for governed Screen 4 historical review execution metadata.

The model exists so Screen 4 actions can be represented as governed workflow records while deterministic runtime remains authoritative.

## 2. Object Shapes

`HistoricalReviewExecutionRequest` carries action, target, actor, governed write request, review payload, dry-run gates, safety flags, and notes.

`HistoricalReviewExecutionValidation` carries validation status, actor presence, governed write validation, target presence, execution eligibility, denied reasons, warnings, next steps, and safety flags.

`HistoricalReviewExecutionResult` carries result status, optional trend/anomaly/baseline metadata, candidate intents, learning signal intents, governance routes, audit envelope metadata, output artifact metadata, and hard runtime safety flags.

`HistoricalReviewAuditEnvelope` carries request id, actor id, action, target, governed write validation id, output artifact id, audit summary, and safety flags.

## 3. Validation Statuses

Supported validation statuses are:

- `valid`
- `invalid`
- `needs_actor`
- `needs_governed_write_path`
- `needs_target`
- `unsupported_action`
- `execution_metadata_only`
- `blocked_by_safety`

No validation status grants runtime mutation.

## 4. Execution Statuses

Supported execution statuses are:

- `proposed`
- `validated`
- `recorded_metadata_only`
- `blocked`
- `invalid`

No execution status means runtime mutation.

## 5. Supported Actions

Supported actions are:

- `approve_trend`
- `dispute_trend`
- `mark_trend_insufficient`
- `approve_anomaly`
- `mark_anomaly_false_positive`
- `mark_anomaly_insufficient`
- `request_trend_aware_scoring_review`
- `request_anomaly_sensitivity_review`
- `request_scoring_threshold_review`
- `request_learning_candidate`
- `add_historical_review_note`

Each action is represented as governed metadata only.

## 6. Validation Rules

Requests require supported action, supported target type, actor metadata for governed actions, governed write-path metadata, audit requirement, `dry_run=true`, `write_performed=false`, `runtime_influence=false`, and `phase4i_mutation_requested=false`.

Validation records require supported validation status, consistent execution eligibility, `write_performed=false`, `runtime_influence=false`, and `phase4i_mutation_requested=false`.

Result records require supported execution status and action, valid nested metadata records when present, `candidate_created=false`, `dataset_label_created=false`, `historical_truth_changed=false`, `trend_truth_changed=false`, `anomaly_truth_changed=false`, `scoring_changed=false`, `phase4i_mutated=false`, and `runtime_influence=false`.

Audit envelopes require supported action and target type, audit summary, `runtime_influence=false`, and `phase4i_mutation_requested=false`.

## 7. Serialization Rules

All 7BC.3 objects serialize to deterministic dictionaries with explicit fields.

Deserialization reconstructs the dataclass records and reruns validation. Serialization is not persistence and does not write files, database rows, output artifacts, dashboard state, or runtime state.

## 8. Deterministic ID Rules

IDs are deterministic and based only on supplied metadata:

- `SCREEN4-HIST-EXEC-REQUEST-<ACTION>-<TARGET_TYPE>-<TARGET_ID>`
- `SCREEN4-HIST-EXEC-VALIDATION-<REQUEST_ID>`
- `SCREEN4-HIST-EXEC-RESULT-<REQUEST_ID>-<ACTION>`
- `SCREEN4-HIST-EXEC-AUDIT-<REQUEST_ID>-<ACTION>`

IDs use no random UUID, no timestamp, no database sequence, and no external service. The same input creates the same ID.

## 9. Runtime Safety Rules

Runtime safety requires metadata-only execution. No runtime truth changes are allowed.

The hard safety flags remain false: `candidate_created=false`, `dataset_label_created=false`, `historical_truth_changed=false`, `trend_truth_changed=false`, `anomaly_truth_changed=false`, `scoring_changed=false`, `phase4i_mutated=false`, `runtime_influence=false`, `write_performed=false`, and `phase4i_mutation_requested=false`.

## 10. Non-Goals

Phase 7BC.3 does not persist records, write databases, call backend APIs, call `run_analysis.py`, invoke parser/scoring/trend/anomaly runtime modules, invoke recommendation modules, create actual learning candidates, create actual dataset labels, mutate Phase 4I, mutate deterministic runtime, implement Phase 7BD, or implement Phase 8 sizing/TCO.

## 11. Acceptance Criteria

Acceptance requires deterministic object models, supported constants, validation helpers, metadata execution helper, audit envelope helper, output artifact metadata, serialization/deserialization helpers, documentation, and tests.

Acceptance also requires these guarantees: governed execution is metadata-only, no runtime truth changes, no candidate creation, no dataset label creation, no trend/anomaly/scoring mutation, no Phase 4I mutation, deterministic runtime remains authoritative, and Phase 8 sizing/TCO is not implemented.
