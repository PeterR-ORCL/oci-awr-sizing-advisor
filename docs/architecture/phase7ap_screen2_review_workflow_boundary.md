# Phase 7AP Screen 2 Review Workflow Boundary

## 1. Purpose

Phase 7AP defines the architecture boundary for future Screen 2 diagnostic review and approval workflows in the Agentic AI AWR Advisor project.

This phase is boundary-only. It documents how reviewers may later review diagnostic evidence without changing deterministic diagnostic truth, backend runtime truth, or the Phase 4I contract.

Screen 2 deterministic diagnosis remains authoritative. Review actions do not overwrite diagnosis.

## 2. Scope

The scope is documentation, lifecycle definition, optional inert local boundary metadata, validation tests, and architecture index updates for future Screen 2 diagnostic review workflow boundaries.

Phase 7AP defines:

- what Screen 2 diagnostic review may later target
- what future review decisions may exist
- what future review statuses may exist
- what actor, audit, and governed write-path gates are required
- why review state is separate from diagnostic truth
- how parser, scoring, recommendation, missing metric, and evidence availability review requests remain governed
- what shortcuts are forbidden before future workflow phases exist

No Screen 2 review workflow is implemented in Phase 7AP.

## 3. Non-Goals

Phase 7AP adds no Screen 2 approval UI. No Screen 2 approval UI is added.

Phase 7AP adds no Screen 2 review panel UI, approval buttons, dispute buttons, evidence confirmation controls, forms, dashboard write controls, JavaScript backend calls, API routes, CLI commands, or backend calls.

Phase 7AP creates no review records. No review records are created.

Phase 7AP invokes no backend write path. No backend write path is invoked.

Phase 7AP does not call `scripts/run_analysis.py`, wire into backend execution, write database records, write governance records, create learning candidates, or create evidence review records.

Phase 7AP changes no diagnostic truth. No diagnostic truth is changed. No severity is changed. No confidence is changed. No score is changed. No evidence is changed. No parser output is changed. No recommendation truth is changed. No Phase 4I mutation is added.

Phase 7AP does not implement missing metric review model, Screen 2 workflow bridge to governance, Screen 2 approval UI, validation certification, or Phase 8 sizing/TCO.

Phase 8 sizing/TCO is not implemented.

## 4. Why Screen 2 Needs Review Workflow

Screen 2 is the diagnostic evidence screen. It shows deterministic diagnosis, evidence groups, scoring context, confidence context, and recommendation context that a reviewer may need to inspect before accepting operational conclusions.

Future reviewers may need to say that CPU evidence is confirmed, wait event evidence is misleading, a metric is missing, evidence is insufficient, parser extraction appears wrong, scoring should be reviewed, a recommendation needs review, or a learning candidate should be considered.

Those future review actions are useful only if they remain governed review state. A review action is not a shortcut for changing primary issue, secondary issues, severity, confidence, domain scores, evidence, parser output, recommendation truth, or Phase 4I output.

## 5. Existing Screen 2 Diagnostic Boundary

Existing Screen 2 behavior provides deterministic diagnostic snapshot and read-only diagnostic exploration.

Screen 2 may help a reviewer inspect evidence, issue context, confidence context, severity context, score context, recommendation context, and related read-only dashboard selections. That exploration does not create records, write governance state, execute analysis, change diagnosis, change severity, change confidence, change score, change evidence, change parser output, change recommendations, or mutate Phase 4I.

Phase 7AP preserves the existing read-only diagnostic boundary.

## 6. Review Is Not Mutation

Review is not mutation.

Future Screen 2 review creates governed review state later, not runtime changes. A future confirm, dispute, insufficient evidence flag, parser review request, scoring review request, recommendation review request, learning candidate request, or reviewer note is review metadata and audit context only until a later governed path explicitly handles it.

No future review decision may directly mutate diagnostic truth, parser output, scoring output, recommendation truth, dashboard truth, runtime state, or Phase 4I.

## 7. Diagnostic Truth Boundary

Deterministic diagnostic truth remains authoritative. Screen 2 review state is not diagnostic truth.

Future review targets may reference primary issue, secondary issue, severity, confidence, domain score, evidence group, metric group, wait event group, SQL signal group, diagnostic section, parser-derived evidence, trend reference, anomaly reference, missing metric, unavailable evidence, or recommendation context.

Those references do not give review state authority to modify the referenced diagnostic artifact. No Screen 2 review action can directly change primary issue, secondary issue, severity, confidence, domain score, evidence, parser output, scoring behavior, decision behavior, recommendation behavior, Phase 4I, or generated dashboard truth.

## 8. Evidence Review Boundary

Future evidence review may let reviewers confirm evidence, dispute evidence, mark evidence insufficient, identify unreliable evidence, identify missing evidence, request parser review, request scoring review, request recommendation review, request learning candidate generation, and add reviewer notes.

Evidence review is governed review state, not evidence mutation. It may point to diagnostic evidence, but it cannot rewrite evidence, delete evidence, add runtime evidence, alter parser extraction, adjust confidence, change score, or change recommendation truth.

## 9. Actor Requirement

Future review actions require actor identity.

Actor identity is required through the Phase 7AE actor/reviewer identity model before any future Screen 2 review action can be accepted. Browser state, URL hash state, selected card state, dashboard local state, semantic context, or learning metadata cannot stand in for a human actor.

Phase 7AP does not implement actor identity and does not wire actor identity into Screen 2.

## 10. Governed Write-Path Requirement

Future review actions require governed write path.

Any future non-read-only Screen 2 review action must use the Phase 7AG governed write-path framework. The future write path must validate request shape, actor identity, authorization posture, target reference, decision type, audit fields, diagnostic truth protection, Phase 4I protection, failure behavior, and closure state before review state can be created.

Phase 7AP does not implement a governed write path and does not invoke one.

## 11. Audit Requirement

Future review actions require audit trail.

Future audit records must identify the actor, target type, target reference, decision, status transition, source diagnostic payload reference, validation result, authorization result, governed write-path result, timestamp or sequence marker supplied by the future audit layer, notes when present, routed governance references when present, and closure state.

Reviewer notes are audit records. Future notes require actor/audit.

Phase 7AP does not create audit records.

## 12. Phase 4I Contract Boundary

Phase 4I contract is protected.

No Screen 2 review action can directly change Phase 4I. Phase 7AP adds no Phase 4I mutation and no Phase 4I contract change.

Any future workflow that proposes a Phase 4I-affecting correction must use a separately versioned, validated, governed backend contract. Review state alone cannot update Phase 4I, parser output, scoring output, decision output, recommendation output, dashboard payload shape, or generated dashboard artifacts.

## 13. Parser Review Request Boundary

Parser review requests are governed.

A future parser review request may create or link parser review candidates through a governed workflow, but it cannot mutate parser output. A reviewer may indicate that parser-derived evidence looks incomplete, misleading, missing, unavailable, or extracted from the wrong section. That indication remains governed review state until later parser governance phases handle it.

Phase 7AP does not create parser candidates, parser mappings, parser backlog items, parser review records, or parser output changes.

## 14. Scoring Review Request Boundary

Scoring review requests are governed.

A future scoring review request may create or link scoring review candidates through a governed workflow, but it cannot mutate score. A reviewer may indicate that severity, confidence, domain score, evidence weight, trend influence, or anomaly influence needs scoring review. That indication remains governed review state until later scoring governance phases handle it.

Phase 7AP does not create scoring review records, scoring candidates, score overrides, confidence adjustments, severity adjustments, or scoring behavior changes.

## 15. Recommendation Review Request Boundary

Recommendation review requests are governed.

A future recommendation review request may create or link recommendation review candidates through a governed workflow, but it cannot mutate recommendation truth. A reviewer may indicate that recommendation context, rationale, ranking, applicability, or supporting evidence needs review. That indication remains governed review state until later recommendation governance phases handle it.

Phase 7AP does not create recommendation review records, recommendation candidates, recommendation overrides, action records, outcome records, or recommendation behavior changes.

## 16. Missing Metric / Evidence Availability Boundary

Evidence availability matters.

Future Screen 2 review must support missing/unreliable evidence classification through 7AQ.1. Missing metric/evidence review is future 7AQ.1.

Future review may need to distinguish available evidence, missing metrics, unavailable evidence, unsupported evidence, parser gaps, unreliable values, insufficient context, and not-applicable evidence. Phase 7AP documents this boundary only and does not implement the missing metric review model.

Missing evidence must not directly adjust confidence, score, severity, diagnosis, parser output, or recommendation truth in Phase 7AP.

## 17. Future Review Target Types

Future Screen 2 review target types are boundary concepts only in Phase 7AP:

- `primary_issue`
- `secondary_issue`
- `severity`
- `confidence`
- `domain_score`
- `evidence_group`
- `metric_group`
- `wait_event_group`
- `sql_signal_group`
- `diagnostic_section`
- `parser_derived_evidence`
- `trend_reference`
- `anomaly_reference`
- `missing_metric`
- `unavailable_evidence`
- `recommendation_context`

These target types are references for future review state. They are not mutable runtime artifacts.

## 18. Future Review Decisions

Future Screen 2 review decisions are boundary concepts only in Phase 7AP:

- `confirm`
- `dispute`
- `insufficient_evidence`
- `needs_parser_review`
- `needs_scoring_review`
- `needs_recommendation_review`
- `needs_learning_candidate`
- `add_reviewer_note`

All future decisions require actor. All future decisions require audit. None directly mutate diagnostic truth. None directly mutate runtime.

## 19. Future Review Statuses

Future Screen 2 review statuses are boundary concepts only in Phase 7AP:

- `proposed`
- `under_review`
- `confirmed`
- `disputed`
- `insufficient_evidence`
- `needs_revision`
- `routed_to_governance`
- `closed`

Statuses are governed review state. Statuses are not runtime diagnosis state.

## 20. Relationship to 7AD-7AI

Phase 7AD-7AI established dashboard workflow infrastructure:

- 7AD defined workflow boundaries.
- 7AE defined actor/reviewer identity metadata.
- 7AF defined backend execution mode metadata.
- 7AG defined governed write-path metadata.
- 7AH defined output artifact lifecycle metadata.
- 7AI validated the workflow infrastructure block.

Phase 7AP depends on those boundaries for future Screen 2 review workflows. It does not replace them and does not activate a workflow.

## 21. Relationship to Future 7AQ

Future 7AQ may define the diagnostic review object model.

Phase 7AP only defines target types, decisions, statuses, and required gates as boundary concepts. It does not create diagnostic review records, evidence review records, schemas, serialization contracts, request models, or persistence models.

## 22. Relationship to Future 7AQ.1

Future 7AQ.1 may define the evidence availability / missing metric review model.

Phase 7AP only states that missing metric/evidence review is future 7AQ.1. It does not implement missing metric classification, unreliable evidence classification, confidence impact modeling, parser gap handling, source review handling, or missing evidence workflow records.

## 23. Relationship to Future 7AR

Future 7AR may define the Screen 2 workflow bridge to governance.

Phase 7AP does not bridge Screen 2 to governance, does not write governance records, does not route review decisions, does not create learning candidates, and does not link parser, scoring, or recommendation candidates.

## 24. Relationship to Future 7AS

Future 7AS may define Screen 2 approval UI and review panel behavior.

Phase 7AP adds no Screen 2 approval UI, no review panel UI, no forms, no buttons, no disabled preview controls, no dashboard JavaScript workflow, and no dashboard write controls.

## 25. Relationship to Future 7AT

Future 7AT may validate and certify the Screen 2 diagnostic review / approval workflow block.

Phase 7AP only introduces boundary documentation, lifecycle documentation, architecture index links, and boundary tests for the first subtask in the block. It does not run final block readiness checks.

## 26. Relationship to Phase 8

Phase 8 sizing/TCO is not implemented.

Phase 7AP does not add sizing, TCO, what-if advisory, capacity planning, cost modeling, EM Extract implementation, or sizing recommendation workflows. Recommendation review in this boundary is diagnostic recommendation governance only, not Phase 8 advisory.

## 27. Acceptance Criteria

Phase 7AP is accepted when Screen 2 review workflow boundary documentation exists, Screen 2 review lifecycle documentation exists, optional inert local boundary metadata is boundary-only when present, boundary validation tests exist, architecture index links exist when the README is updated, future review target types are documented, future review decisions are documented, future review statuses are documented, future review actions require actor identity, future review actions require governed write path, future review actions require audit trail, Screen 2 deterministic diagnosis remains authoritative, review is not mutation, no Screen 2 approval UI is added, no review records are created, no backend write path is invoked, no diagnostic truth is changed, no severity is changed, no confidence is changed, no score is changed, no parser output is changed, no recommendation truth is changed, no Phase 4I mutation is added, missing metric/evidence review is future 7AQ.1, deterministic runtime remains authoritative, and Phase 8 sizing/TCO is not implemented.
