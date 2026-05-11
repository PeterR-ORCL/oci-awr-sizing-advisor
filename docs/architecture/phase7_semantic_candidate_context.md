# Phase 7E Semantic Candidate Context

## 1. Purpose

Phase 7E adds optional semantic candidate context for Phase 7 learning candidates. The context is reviewer-assist only, optional, non-authoritative, and always keeps `runtime_influence=false`.

Semantic context can explain but cannot decide. It may help a human reviewer understand similar prior cases, repeated language or themes, related unknown signals, related knowledge artifacts, related feedback summaries, related recommendations, or related domains. It does not decide candidate validity and does not alter deterministic runtime truth.

## 2. Scope

Phase 7E accepts an existing Phase 7C `LearningCandidate` and caller-provided in-memory semantic records. It may build a `SemanticCandidateContext` record and attach that record to the candidate's `semantic_context` field.

The module is deterministic, local-only, safe to import, and uses Python standard library behavior plus the local Phase 7 learning candidate model. It performs no persistence, no file writes, no database calls, no network calls, no LLM calls, and no environment-variable lookup.

## 3. Non-Goals

Phase 7E does not generate candidates, approve candidates, reject candidates, change candidate status, change candidate type, change candidate confidence, change candidate source evidence, or make semantic context diagnostic evidence.

Phase 7E does not alter parser behavior, parser output, scoring logic, scoring weights, trend or anomaly logic, decision logic, recommendation logic, Phase 4I output contracts, `run_analysis.py`, dashboard diagnostic truth, Screen 2 diagnostic evidence, Screen 5 recommendation truth, dashboard interactivity, CLI learning commands, governed memory persistence, OCI, ADB, Oracle Agent Memory, semantic recall services, or LLM behavior.

## 4. Semantic Candidate Context Shape

`SemanticCandidateContext` contains `context_id`, `candidate_id`, `summary`, `semantic_records`, `related_cases`, `related_unknown_signals`, `related_feedback`, `related_artifacts`, `reviewer_assist`, `non_authoritative`, `runtime_influence`, `source`, and `rationale`.

The safety fields are fixed to `reviewer_assist=true`, `non_authoritative=true`, and `runtime_influence=false`. These values mean the context is reviewer-assist only, optional, and non-authoritative.

## 5. Semantic Record Inputs

Semantic records are in-memory mappings supplied explicitly by the caller. They may represent prior similar cases, reviewer notes, semantic recall summaries, related parser unknowns, related knowledge artifacts, feedback summaries, related recommendations, or related domains.

Record shapes are flexible. Supported aliases include `id`, `record_id`, `memory_id`, `case_id`, `artifact_id`, `feedback_id`, and `unknown_signal_id` for identity; `candidate_id`, `related_candidate_id`, `affected_component`, `component`, `affected_domain`, `domain`, `candidate_type`, and `type` for linkage; `summary`, `text`, `description`, `note`, `rationale`, and `content` for text; `category`, `source_type`, `record_type`, and `type` for category; and `similarity`, `relevance`, and `score` for deterministic ordering.

## 6. Deterministic Matching Rules

Matching uses only explicit in-memory records. A record may match through exact `candidate_id`, exact `candidate_type`, exact `affected_component`, exact `affected_domain`, candidate title keyword overlap, or source record references that are already present in candidate source evidence or structured sources.

The module does not use embeddings, semantic search, LLM inference, randomness, current timestamps, database sequences, or external services. Matched records are sorted deterministically and limited to a bounded record count.

Context ids are stable and use the form `SEMCTX-<CANDIDATE_ID>-<STABLE_KEY>`. The stable key is derived from normalized candidate and matched-record content, not from random UUIDs, timestamps, databases, or external services.

## 7. Attachment Rules

Attaching semantic context returns a new `LearningCandidate` object when practical. Attachment preserves `candidate_id`, `candidate_type`, `source_evidence`, `structured_sources`, `confidence`, `status`, `requires_human_review=true`, `runtime_influence=false`, `reviewed_by`, and `materialization_reference`.

Semantic context is attached only to the `semantic_context` field. It is not source_evidence. It is not diagnostic evidence. It must not approve/reject candidates, validate candidates, implement candidates, close candidates, or decide candidate validity.

If no meaningful semantic records match, `build_context` returns no context. In that case attachment leaves any existing candidate fields unchanged except for returning a validated candidate copy that still has `requires_human_review=true` and `runtime_influence=false`.

## 8. Runtime Isolation Boundary

Phase 7E is isolated from deterministic runtime behavior. Runtime parser, scoring, trend, anomaly, decision, recommendation, dashboard truth, and `run_analysis.py` paths must not import `src.learning`.

No parser/scoring/decision/recommendation behavior changes are made. Deterministic runtime remains authoritative.

## 9. Semantic Recall Boundary

Semantic recall concepts may be represented only by local in-memory records passed explicitly by the caller. Phase 7E has no live Oracle Agent Memory dependency, no live semantic recall service dependency, and no semantic recall service call is required.

Semantic recall remains non-authoritative. Semantic context can explain but cannot decide.

## 10. Source Evidence Boundary

Semantic candidate context is not source_evidence. It must never be copied into `source_evidence`, must never replace `source_evidence`, and must never become diagnostic evidence.

Source evidence continues to come from Phase 7B and Phase 7D governed pattern inputs. Phase 7E only adds optional reviewer-assist context.

## 11. Confidence Boundary

Semantic context must not change confidence. It must not raise confidence, lower confidence, clamp confidence, rank candidate validity, or otherwise influence the candidate confidence field.

## 12. Status Boundary

Semantic context must not change status. It must not move a candidate into `UNDER_REVIEW`, `APPROVED_FOR_IMPLEMENTATION`, `REJECTED`, `NEEDS_REVISION`, `IMPLEMENTED`, `VALIDATED`, or `CLOSED`.

## 13. Governance Boundary

Phase 7E does not implement governance workflow. It does not approve/reject candidates and does not create a materialization path.

The governance bridge remains future Phase 7F. Human governance remains required before any candidate can be implemented outside this semantic context layer.

## 14. Dashboard Boundary

Phase 7E does not change dashboard diagnostic truth, generated dashboard files, Screen 2 diagnostic evidence, Screen 5 recommendation truth, dashboard controls, or dashboard runtime behavior.

Dashboard learning visibility remains future Phase 7G. Dashboard interactivity remains future Phase 7H.

## 15. Relationship to Phase 7C Candidate Model

Phase 7C defines the `LearningCandidate` model, supported candidate types, supported statuses, serialization behavior, and safety invariants. Phase 7E uses that model and attaches context through the existing `semantic_context` field.

Phase 7E does not loosen Phase 7C validation. Candidates still require human review and still keep `runtime_influence=false`.

## 16. Relationship to Phase 7D Candidate Generation

Phase 7D creates proposal-only learning candidates from deterministic outcome patterns. Phase 7E consumes existing candidates and optional in-memory semantic records to provide reviewer-assist context.

Phase 7E does not generate candidates. It does not alter Phase 7D candidate generation rules, source evidence rules, confidence rules, status rules, or deterministic output rules.

## 17. Relationship to Future Phase 7F Governance Bridge

Governance bridge remains future Phase 7F. Phase 7E does not create approval workflow, review workflow, persistence bridge, implementation workflow, materialization, activation, or runtime learning.

## 18. Relationship to Future Phase 7G Dashboard Learning Visibility

Dashboard learning visibility remains future Phase 7G. Phase 7E does not add dashboard panels, dashboard tables, dashboard badges, dashboard links, or dashboard summaries for learning candidates.

## 19. Relationship to Future Phase 7H Dashboard Interactivity

Dashboard interactivity remains future Phase 7H. Phase 7E does not add reviewer controls, candidate actions, interactive approval, interactive rejection, dashboard editing, or dashboard mutation behavior.

## 20. Validation Requirements

Validation must prove import safety, empty input behavior, deterministic matching, context safety fields, attachment safety, stable context ids, stable ordering, serialization, no input mutation, no live dependency, absence of forbidden autonomous function names, runtime import isolation, and documentation boundary coverage.

Validation must also preserve Phase 7A learning boundary tests, Phase 7B outcome pattern mining tests, Phase 7C learning candidate model tests, Phase 7D candidate generation tests, and Phase 6 validation when the environment supports it.

## 21. Acceptance Criteria

Phase 7E is accepted when semantic candidate context is reviewer-assist only, optional, non-authoritative, and always `runtime_influence=false`; semantic context can explain but cannot decide; semantic context is not source_evidence; semantic context must not change confidence; semantic context must not change status; semantic context must not approve/reject candidates; semantic context must not modify runtime truth; no live Oracle Agent Memory dependency is required; no semantic recall service call is required; governance bridge remains future Phase 7F; dashboard learning visibility remains future Phase 7G; dashboard interactivity remains future Phase 7H; no runtime learning is implemented; and deterministic runtime remains authoritative.

Phase 7E must not alter parser/scoring/decision/recommendation behavior, dashboard truth, Phase 4I contracts, generated dashboard files, governed memory persistence, or `run_analysis.py` behavior.
