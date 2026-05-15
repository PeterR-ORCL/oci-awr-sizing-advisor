# Phase 7BB Trend / Anomaly Review Lifecycle

## 1. Purpose

Phase 7BB defines the lifecycle boundary for future Screen 4 trend/anomaly review workflows.

The lifecycle is documentation-only for this subphase. No lifecycle stage writes records in 7BB.

## 2. Lifecycle Overview

Future Screen 4 trend/anomaly review workflow moves through controlled stages:

1. Read-only historical review stage
2. Trend / anomaly review request stage
3. Actor identification stage
4. Review validation stage
5. Routing intent stage
6. Future governed write-path stage
7. Future learning candidate bridge stage
8. Audit trail stage

No lifecycle stage writes records in 7BB. Review validation is not persistence. Routing intent is metadata only.

## 3. Read-Only Historical Review Stage

The lifecycle begins with existing Screen 4 read-only historical review. The screen may display trend summaries, trend metrics, anomaly groups, anomaly events, baseline context, comparison context, recurrence patterns, historical confidence, missing historical evidence, and trend-aware scoring references.

Read-only review does not create records, write records, execute analysis, mutate historical truth, mutate trend truth, mutate anomaly truth, change scoring, create learning candidates, or mutate Phase 4I.

## 4. Trend / Anomaly Review Request Stage

Future review request metadata may identify a supported target, requested decision, actor, baseline candidate, comparison context, and payload.

The request stage is metadata only. It does not persist review records, make decisions authoritative, create candidates, route governance, or execute backend behavior.

## 5. Actor Identification Stage

Future workflows cannot skip actor.

Actionable trend/anomaly review decisions require a human actor identity before they can be accepted by a future workflow. Anonymous dashboard state, URL hash state, selected historical state, semantic context, or local browser state cannot replace actor identity.

Phase 7BB stores actor fields only and does not implement authentication or authorization.

## 6. Review Validation Stage

Review validation checks whether actor identity is present, the target is present, supported decision metadata is used, and baseline/comparison context is present when required.

Review validation is not persistence. It does not write records, invoke governed write path, create candidates, change trend truth, change anomaly truth, change scoring, or mutate Phase 4I.

## 7. Routing Intent Stage

Routing intent maps review decisions to future metadata intent names such as scoring review intent, learning candidate intent, validation intent, human review intent, evidence validation intent, and note intent.

Routing intent is metadata only. It does not create scoring review records, does not create learning candidates, does not route governance, and does not execute workflow behavior in 7BB.

## 8. Future Governed Write-Path Stage

Future workflows cannot skip governed write path.

Any future non-read-only Screen 4 trend/anomaly review workflow must enter the Phase 7AG governed write-path framework before review state can be persisted or routed.

Phase 7BB does not invoke the governed write path and keeps `write_performed=false`.

## 9. Future Learning Candidate Bridge Stage

Future 7BC may convert approved historical review intent into a learning candidate intent or bridge result.

Phase 7BB does not implement the bridge, does not create learning candidates, and does not convert review metadata into candidate objects.

## 10. Audit Trail Stage

Future audit trail must capture actor, target, requested decision, validation result, baseline/context references, routing intent, future governed write-path outcome, and closure state.

Phase 7BB models audit context fields only. It does not persist audit records.

## 11. Forbidden Shortcuts

Forbidden shortcuts include skipping actor, skipping validation, skipping governed write path, treating routing intent as execution, treating review validation as persistence, creating learning candidates from review metadata, creating scoring review records from review metadata, mutating trend truth, mutating anomaly truth, changing scoring, changing trend-aware scoring, changing anomaly detection behavior, changing recommendation behavior, changing parser behavior, mutating Phase 4I, adding Screen 4 UI, calling backend execution, and implementing Phase 8 sizing/TCO.

Future workflows cannot skip actor. Future workflows cannot skip governed write path. Trend/anomaly review cannot mutate historical truth.

## 12. Acceptance Criteria

Phase 7BB lifecycle acceptance requires lifecycle documentation, explicit stage boundaries, forbidden shortcut language, local review object models, validation tests, and direct subphase regression tests.

Acceptance also requires these guarantees: no lifecycle stage writes records in 7BB, review validation is not persistence, routing intent is metadata only, future workflows cannot skip actor, future workflows cannot skip governed write path, trend/anomaly review cannot mutate historical truth, review records do not mutate trend truth, review records do not mutate anomaly truth, review records do not change scoring, review records do not create learning candidates, deterministic runtime remains authoritative, and Phase 8 sizing/TCO is not implemented.
