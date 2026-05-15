# Phase 7AP Screen 2 Review Lifecycle

## 1. Purpose

Phase 7AP defines the lifecycle boundary that future Screen 2 diagnostic review actions must follow before any review, approval, routing, audit, governance linkage, or learning candidate behavior can be implemented.

This lifecycle is documentation-only. No lifecycle stage is implemented in 7AP.

## 2. Lifecycle Overview

Future Screen 2 diagnostic review workflows must move through controlled lifecycle stages:

1. Read-only diagnostic stage
2. Review target selection stage
3. Actor identification stage
4. Review decision stage
5. Request validation stage
6. Governed write-path stage
7. Governance routing stage
8. Candidate linkage stage
9. Audit trail stage
10. Closure stage

No lifecycle stage is implemented in 7AP. The lifecycle defines required boundaries before future Screen 2 review workflows can exist.

## 3. Read-Only Diagnostic Stage

The lifecycle begins with the existing read-only diagnostic stage. Screen 2 displays deterministic diagnosis, evidence, scoring context, confidence context, severity context, and recommendation context for exploration.

Read-only diagnostic exploration is not review state, not governance state, not backend truth mutation, and not runtime mutation. It cannot create records, write records, execute analysis, change parser output, change scoring output, change decision output, change recommendation output, modify Phase 4I, or bypass runtime gates.

## 4. Review Target Selection Stage

Future review target selection identifies what a reviewer intends to review, such as primary issue, secondary issue, severity, confidence, domain score, evidence group, metric group, wait event group, SQL signal group, diagnostic section, parser-derived evidence, trend reference, anomaly reference, missing metric, unavailable evidence, or recommendation context.

Review target selection is not mutation. Selecting a target cannot confirm, dispute, route, create records, write governance state, change diagnosis, change severity, change confidence, change score, change evidence, change parser output, or change recommendation truth.

## 5. Actor Identification Stage

Future review cannot skip actor.

Before any future Screen 2 review decision can be accepted, a human actor identity from Phase 7AE must be present. Browser state, URL hash state, selected evidence state, dashboard local state, semantic context, learning metadata, or anonymous metadata cannot replace actor identity.

Phase 7AP does not implement actor identification.

## 6. Review Decision Stage

Future review decisions may include confirm, dispute, insufficient evidence, needs parser review, needs scoring review, needs recommendation review, needs learning candidate, and add reviewer note.

A review decision is an intent to create governed review state later. It is not diagnostic truth, not runtime truth, and not Phase 4I mutation.

Future parser/scoring/recommendation review requests cannot mutate runtime.

## 7. Request Validation Stage

Future review cannot skip validation.

Validation must prove that the target type is supported, target reference is present, actor identity is present, decision type is supported, requested status transition is legal, audit fields are available, governed write-path requirements are satisfied, diagnostic truth is protected, Phase 4I is protected, and failure behavior is safe.

Invalid actions must fail safely and must not create silent state changes.

## 8. Governed Write-Path Stage

Future review cannot bypass governed write path.

Any future non-read-only Screen 2 review action must enter the Phase 7AG governed write-path framework before review state can be created. The governed write path must validate and audit the request envelope before any persistence, routing, candidate linkage, or closure behavior exists.

Phase 7AP does not perform governed writes and does not invoke the write path.

## 9. Governance Routing Stage

Future governance routing may route confirmed disputes, insufficient evidence findings, parser review requests, scoring review requests, recommendation review requests, missing metric findings, unavailable evidence findings, or learning candidate requests to later governance workflows.

Routing is future work. Phase 7AP does not route to governance, write governance records, create governance tasks, or alter governance state.

## 10. Candidate Linkage Stage

Future candidate linkage may link a governed review action to parser candidates, scoring review candidates, recommendation review candidates, or learning candidate generation requests.

Candidate linkage is future work. A candidate link cannot mutate runtime parser output, scoring behavior, recommendation truth, diagnosis, Phase 4I, or dashboard truth by itself.

Missing evidence must be handled through future 7AQ.1.

## 11. Audit Trail Stage

Future review cannot skip audit.

The audit trail must identify actor, target type, target reference, decision, requested status, validation result, governed write-path result, governance routing result when applicable, candidate linkage reference when applicable, reviewer note when applicable, and closure state.

Reviewer notes are audit records and require actor/audit. Phase 7AP does not create audit records.

## 12. Closure Stage

Closure records the final state of a future Screen 2 review workflow action, such as rejected before validation, rejected by governed write-path validation, proposed, under review, confirmed, disputed, insufficient evidence, needs revision, routed to governance, or closed.

Closure state is governed review state. Closure state is not runtime diagnosis state.

Phase 7AP does not implement closure.

## 13. Forbidden Shortcuts

Forbidden shortcuts include skipping actor, skipping validation, skipping audit, bypassing governed write path, creating review records directly from a dashboard click, treating target selection as mutation, treating review decision as diagnostic truth, mutating parser output from review state, mutating score from review state, mutating confidence from review state, mutating severity from review state, mutating recommendation truth from review state, mutating Phase 4I from review state, creating learning candidates without governance, calling `run_analysis.py`, executing backend code, adding Screen 2 approval UI, and implementing Phase 8 sizing/TCO inside Phase 7AP.

Future parser/scoring/recommendation review requests cannot mutate runtime.

## 14. Required Validation Evidence

Future validation evidence must include supported target type validation, target reference validation, actor presence validation, decision validation, status transition validation, governed write-path validation, audit field validation, diagnostic truth protection validation, Phase 4I contract protection validation, parser/scoring/recommendation runtime isolation validation, missing metric/evidence availability validation through future 7AQ.1, safe failure validation, and forbidden shortcut rejection.

Missing evidence must be handled through future 7AQ.1.

## 15. Acceptance Criteria

Phase 7AP lifecycle acceptance requires this lifecycle document, explicit stage boundaries, forbidden shortcut language, required validation evidence, and tests proving the lifecycle remains boundary-only.

Acceptance also requires these guarantees: no lifecycle stage is implemented in 7AP, review target selection is not mutation, future review cannot skip actor, future review cannot skip validation, future review cannot skip audit, future review cannot bypass governed write path, future parser/scoring/recommendation review requests cannot mutate runtime, missing evidence must be handled through future 7AQ.1, deterministic runtime remains authoritative, and Phase 8 sizing/TCO is not implemented.
