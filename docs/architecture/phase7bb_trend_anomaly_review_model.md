# Phase 7BB Trend / Anomaly Review Object Model

## 1. Purpose

Phase 7BB defines local, deterministic object models for future Screen 4 trend and anomaly review workflows.

The model lets future workflows describe reviewer assessment of historical trends, anomaly findings, review requests, review validation, decision metadata, actor/audit linkage, baseline/context linkage, and routing intent metadata without changing deterministic historical truth.

## 2. Scope

Phase 7BB adds local trend review records, anomaly review records, historical review request records, historical review validation records, deterministic ID helpers, routing intent helpers, validation helpers, serialization/deserialization helpers, documentation, tests, and architecture index links.

The scope is object modeling only. Review records describe reviewer assessment. They do not write records, create learning candidates, invoke governed write path, change runtime truth, or alter Phase 4I.

## 3. Non-Goals

Phase 7BB adds no Screen 4 UI, no buttons, no forms, no backend calls, no CLI commands, no persisted review records, no learning candidates, no scoring review records, no recommendation review records, no governed write path invocation, no backend execution, and no Phase 8 sizing/TCO.

Review records do not mutate trend truth. Review records do not mutate anomaly truth. Review records do not change scoring. Review records do not create learning candidates.

write_performed=false in 7BB. runtime_influence=false. Phase 4I mutation is forbidden. Deterministic runtime remains authoritative.

## 4. HistoricalTrendReviewRecord

`HistoricalTrendReviewRecord` is local reviewer assessment metadata for a trend.

Fields include `trend_review_id`, `run_id`, `awr_id`, `baseline_candidate_id`, `comparison_context_id`, `trend_id`, `trend_name`, `domain`, `trend_direction`, `trend_strength`, `review_decision`, `review_status`, `reviewer_actor_id`, `actor_audit_context`, `review_notes`, `linked_scoring_review_id`, `linked_candidate_intent_id`, `write_performed`, `trend_truth_changed`, `scoring_mutation_requested`, `runtime_influence`, `phase4i_mutation_requested`, `created_at`, and `notes`.

Rules require trend review id, a run or AWR reference, trend id, supported review decision, supported review status, actor for actionable decisions, and trend strength between 0.0 and 1.0 when supplied.

`write_performed=false`, `trend_truth_changed=false`, `scoring_mutation_requested=false`, `runtime_influence=false`, and `phase4i_mutation_requested=false` are mandatory.

## 5. HistoricalAnomalyReviewRecord

`HistoricalAnomalyReviewRecord` is local reviewer assessment metadata for an anomaly.

Fields include `anomaly_review_id`, `run_id`, `awr_id`, `baseline_candidate_id`, `comparison_context_id`, `anomaly_id`, `anomaly_name`, `domain`, `anomaly_pattern`, `anomaly_severity`, `review_decision`, `review_status`, `reviewer_actor_id`, `actor_audit_context`, `review_notes`, `linked_scoring_review_id`, `linked_candidate_intent_id`, `write_performed`, `anomaly_truth_changed`, `scoring_mutation_requested`, `runtime_influence`, `phase4i_mutation_requested`, `created_at`, and `notes`.

Rules require anomaly review id, a run or AWR reference, anomaly id, supported review decision, supported review status, actor for actionable decisions, and anomaly severity between 0.0 and 1.0 when supplied.

`write_performed=false`, `anomaly_truth_changed=false`, `scoring_mutation_requested=false`, `runtime_influence=false`, and `phase4i_mutation_requested=false` are mandatory.

## 6. HistoricalReviewRequest

`HistoricalReviewRequest` is future request metadata for Screen 4 historical review workflow.

Fields include `request_id`, `review_target_type`, `review_target_id`, `requested_decision`, `actor_id`, `actor_audit_context`, `baseline_candidate_id`, `comparison_context_id`, `payload`, `validation_status`, `can_route_to_governance`, `write_performed`, `truth_mutation_requested`, `scoring_mutation_requested`, `runtime_influence`, `phase4i_mutation_requested`, and `notes`.

`can_route_to_governance` is future eligibility only. It does not execute governance routing in 7BB.

## 7. HistoricalReviewValidation

`HistoricalReviewValidation` is validation result metadata for a historical review request.

Fields include `validation_id`, `request_id`, `valid`, `validation_status`, `requested_decision`, `actor_present`, `target_present`, `baseline_context_present`, `can_route_to_governance`, `write_performed`, `truth_mutation_requested`, `scoring_mutation_requested`, `denied_reasons`, `warnings`, `required_next_steps`, `runtime_influence`, `phase4i_mutation_requested`, and `notes`.

Review validation is not persistence. It does not write records or alter trend/anomaly/scoring truth.

## 8. Review Target Types

Supported review target types are:

- `trend_summary`
- `trend_metric`
- `anomaly_group`
- `anomaly_event`
- `historical_baseline`
- `comparison_baseline`
- `recurrence_pattern`
- `historical_confidence`
- `missing_historical_evidence`
- `trend_aware_scoring_reference`
- `learning_candidate_intent`

## 9. Review Decisions

Supported review decisions are:

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

## 10. Review Statuses

Supported review statuses are:

- `proposed`
- `under_review`
- `approved`
- `disputed`
- `insufficient_evidence`
- `false_positive`
- `routed_to_governance`
- `linked_to_candidate`
- `closed`

Statuses are governed review metadata. They are not runtime trend/anomaly state.

## 11. Validation Statuses

Supported validation statuses are:

- `valid`
- `invalid`
- `needs_actor`
- `needs_target`
- `needs_baseline_context`
- `unsupported_decision`
- `write_not_allowed_in_this_phase`

## 12. Routing Intent Metadata

Routing intent metadata maps review decisions to future intent categories:

- `request_trend_aware_scoring_review` -> `scoring_review_intent`
- `request_anomaly_sensitivity_review` -> `scoring_review_intent`
- `request_scoring_threshold_review` -> `scoring_review_intent`
- `request_learning_candidate` -> `learning_candidate_intent`
- `mark_anomaly_false_positive` -> `validation_intent`
- `dispute_trend` -> `human_review_intent`
- `mark_trend_insufficient` -> `evidence_validation_intent`

These are intent names only. They do not create candidate objects in 7BB.

## 13. Actor / Audit Requirements

Actionable review decisions require actor identity and audit context. Actor identity comes from the future governed workflow path and must not be replaced by browser state, selected dashboard state, semantic recall, or anonymous metadata.

Phase 7BB models actor/audit fields only. It does not implement authentication, authorization, audit persistence, or governed writes.

## 14. Runtime Truth Boundary

Review records are local metadata only. They do not change historical truth, dashboard truth, parser output, recommendation truth, or runtime behavior.

Deterministic runtime remains authoritative.

## 15. Trend Truth Boundary

Review records do not mutate trend truth.

Approving, disputing, or marking a trend insufficient evidence creates reviewer assessment metadata only. It does not recalculate trends, replace trend output, alter trend direction, or change trend-aware scoring behavior.

## 16. Anomaly Truth Boundary

Review records do not mutate anomaly truth.

Approving an anomaly, marking an anomaly false positive, or marking anomaly evidence insufficient creates reviewer assessment metadata only. It does not reclassify anomalies, alter anomaly detection sensitivity, or change anomaly output.

## 17. Scoring Boundary

Review records do not change scoring.

Requests for trend-aware scoring review, anomaly sensitivity review, or scoring threshold review are routing intent metadata only. They do not create scoring review records, alter deterministic score, change confidence, or activate trend-aware scoring.

## 18. Phase 4I Boundary

Phase 4I mutation is forbidden.

Trend/anomaly review metadata cannot change Phase 4I payload shape, historical output, trend/anomaly output, scoring output, decision output, recommendation output, or generated dashboard artifacts.

## 19. Relationship to 7AZ

Phase 7AZ established the Screen 4 historical review workflow boundary. Phase 7BB stays inside that boundary by defining local review models only.

Phase 7BB does not add Screen 4 UI, invoke write paths, mutate truth, or create learning candidates.

## 20. Relationship to 7BA

Phase 7BA defined baseline candidate, selection request, validation, and comparison context metadata.

Phase 7BB can reference `baseline_candidate_id` and `comparison_context_id` as metadata links. Those links do not make a baseline official, do not persist records, and do not change historical truth.

## 21. Relationship to Future 7BC

Future 7BC may define the historical review to learning candidate bridge.

Phase 7BB does not implement that bridge, create learning candidate intents beyond string metadata references, create learning candidates, approve candidates, materialize candidates, or activate runtime behavior.

## 22. Relationship to Future 7BD

Future 7BD may define Screen 4 workflow validation, readiness, release certification, and operational documentation.

Phase 7BB adds only subphase model validation and directly related tests.

## 23. Acceptance Criteria

Phase 7BB acceptance requires local trend review, anomaly review, review request, and validation models; deterministic IDs; routing intent metadata; validation helpers; serialization/deserialization helpers; documentation; and tests.

Acceptance also requires these guarantees: review records do not mutate trend truth, review records do not mutate anomaly truth, review records do not change scoring, review records do not create learning candidates, write_performed=false in 7BB, runtime_influence=false, Phase 4I mutation is forbidden, deterministic runtime remains authoritative, and Phase 8 sizing/TCO is not implemented.
