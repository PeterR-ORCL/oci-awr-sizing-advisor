# Phase 7BC.3 Historical Review Execution

## 1. Purpose

Phase 7BC.3 defines governed Screen 4 historical review execution metadata.

It turns Screen 4 historical review actions into local request, validation, result, audit, and output artifact records that can be reviewed by governed workflow code without changing runtime truth.

## 2. Scope

The scope is local deterministic metadata only. Phase 7BC.3 adds governed execution request records, validation records, result records, audit envelopes, output artifact metadata, serialization helpers, validation helpers, documentation, tests, and architecture index links.

The layer may create review metadata, candidate intents, learning signal intents, governance route metadata, audit metadata, and output artifact metadata. It does not persist those records to a database or activate runtime behavior.

## 3. Non-Goals

Phase 7BC.3 does not mutate historical truth, trend truth, anomaly truth, scoring, trend-aware scoring, recommendations, parser output, Phase 4I, dashboard generated artifacts, or runtime behavior.

It does not create actual learning candidates, create actual dataset labels, persist to DB, call backend APIs, call `run_analysis.py`, call parser/scoring/trend/anomaly runtime modules, call recommendation modules, add network calls, add OCI calls, implement Phase 7BD, or implement Phase 8 sizing/TCO.

## 4. Governed Execution Is Not Runtime Mutation

Governed execution is metadata-only.

Screen 4 historical review execution creates governed workflow records and audit/output metadata only. There are no runtime truth changes, no candidate creation, no dataset label creation, no trend/anomaly/scoring mutation, and no Phase 4I mutation.

## 5. HistoricalReviewExecutionRequest

`HistoricalReviewExecutionRequest` is the local request envelope for a Screen 4 historical review action.

It records `execution_request_id`, `review_action`, `review_target_type`, `review_target_id`, `actor_id`, `actor_audit_context`, `governed_write_request`, trend/anomaly/baseline/bridge payloads, dry-run and gate fields, safety flags, creation metadata, and notes.

Requests require actor metadata, audit metadata, and governed write-path metadata for governed actions. `dry_run=true`, `write_performed=false`, `runtime_influence=false`, and `phase4i_mutation_requested=false`.

## 6. HistoricalReviewExecutionValidation

`HistoricalReviewExecutionValidation` records validation outcome for a request.

It records whether actor metadata is present, governed write validation is valid, the target is present, a governed metadata action can be recorded, denied reasons, warnings, required next steps, and safety flags.

`can_execute_governed_action=true` means metadata-only governed workflow execution is valid. It does not mean runtime truth mutation is allowed.

## 7. HistoricalReviewExecutionResult

`HistoricalReviewExecutionResult` records the metadata outcome of a governed historical review action.

It may include local trend review metadata, anomaly review metadata, baseline selection request metadata, candidate intents, learning signal intents, governance routes, an audit envelope, and output artifact metadata.

Result rules require `candidate_created=false`, `dataset_label_created=false`, `historical_truth_changed=false`, `trend_truth_changed=false`, `anomaly_truth_changed=false`, `scoring_changed=false`, `phase4i_mutated=false`, and `runtime_influence=false`.

## 8. HistoricalReviewAuditEnvelope

`HistoricalReviewAuditEnvelope` records local audit metadata for the governed action.

It links request id, actor id, action, target type, target id, governed write validation id, output artifact id, audit summary, and safety flags.

Audit envelopes do not persist audit rows and do not authorize runtime mutation. `runtime_influence=false` and `phase4i_mutation_requested=false`.

## 9. Supported Actions

Phase 7BC.3 supports the Screen 4 historical review actions already exposed by the preview panel:

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

These actions become governed metadata execution requests and results only.

## 10. Actor Requirement

Every governed historical review action requires 7AE actor identity metadata.

Missing actor metadata blocks execution validation with `needs_actor`. Actor metadata is copied into audit envelopes but does not by itself authorize runtime mutation.

## 11. Governed Write-Path Requirement

Every governed historical review action requires 7AG governed write-path validation metadata.

Missing or invalid governed write-path metadata blocks execution validation with `needs_governed_write_path`. The write path remains dry-run metadata and performs no database write.

## 12. Output Artifact Requirement

Phase 7BC.3 creates 7AH output artifact metadata for the execution result.

Output artifact metadata is a validation response reference only. It does not write files, regenerate dashboards, mutate Phase 4I, or perform runtime mutation.

## 13. Candidate Intent Boundary

Candidate intents are not candidates.

Phase 7BC.3 may produce candidate intent metadata through the 7BC.1 bridge. It does not create learning candidates automatically and does not materialize candidate records.

## 14. Learning Signal Boundary

Learning signal intents are not dataset labels.

Phase 7BC.3 may produce learning signal intent metadata. It does not create dataset labels, training rows, feature labels, or model labels.

## 15. Trend / Anomaly Truth Boundary

No trend/anomaly truth is changed.

Trend and anomaly review records describe reviewer assessment only. Approving, disputing, marking insufficient evidence, or marking false positive does not change deterministic trend/anomaly interpretation.

## 16. Scoring Boundary

No scoring behavior is changed.

Trend-aware scoring review, anomaly sensitivity review, and scoring threshold review actions create governed metadata and candidate intents only. They do not change deterministic score, confidence, scoring weights, or trend-aware scoring behavior.

## 17. Phase 4I Boundary

No Phase 4I mutation occurs.

Historical review execution does not alter Phase 4I payload shape, scoring output, trend/anomaly output, decision output, recommendation output, or runtime contract.

## 18. Relationship to 7AZ

Phase 7AZ established the Screen 4 historical review boundary. Phase 7BC.3 stays inside that boundary by creating governed metadata records only.

## 19. Relationship to 7BA

Phase 7BA defined baseline selection metadata. Phase 7BC.3 may carry baseline payload metadata, but it does not make baselines official and does not persist baseline selections.

## 20. Relationship to 7BB

Phase 7BB defined local trend/anomaly review objects. Phase 7BC.3 may create those review objects as execution result metadata, with all runtime mutation flags false.

## 21. Relationship to 7BC.1

Phase 7BC.1 defined the historical review to learning candidate bridge. Phase 7BC.3 may route review records through that bridge to create candidate intents, learning signal intents, and governance routes only.

## 22. Relationship to 7BC.2

Phase 7BC.2 exposed a disabled Screen 4 preview panel. Phase 7BC.3 defines the local metadata execution layer behind those actions, but it does not activate dashboard submission or backend calls.

## 23. Relationship to Future 7BD

Future 7BD will validate and certify the complete Screen 4 historical review workflow block.

Phase 7BC.3 does not implement 7BD readiness/certification and does not perform broad final readiness checks.

## 24. Acceptance Criteria

Acceptance requires local governed execution request, validation, result, and audit envelope models; deterministic IDs; validation helpers; serialization helpers; actor and governed write-path gates; output artifact metadata; tests; and documentation.

Acceptance also requires these guarantees: governed execution is metadata-only, no runtime truth changes, no candidate creation, no dataset label creation, no trend/anomaly/scoring mutation, no Phase 4I mutation, deterministic runtime remains authoritative, and Phase 8 sizing/TCO is not implemented.
