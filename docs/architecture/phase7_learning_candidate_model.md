# Phase 7C Learning Candidate Model

## 1. Purpose

Phase 7C defines a deterministic, serializable learning candidate model for the Agentic AI AWR Advisor project. A learning candidate is a governed proposal for possible future improvement, not a runtime change.

The candidate model is not a candidate generation engine. It only defines the object shape, validation rules, serialization helpers, deterministic identifier rules, explicit pattern conversion boundary, and model-level status helpers needed before later Phase 7 work.

## 2. Scope

Phase 7C adds a local Python standard-library model under `src/learning`. The model can represent parser mapping proposals, recommendation rule proposals, scoring weight review proposals, dashboard wording proposals, dashboard interaction proposals, governance workflow proposals, semantic summary proposals, documentation proposals, and validation proposals.

All candidate records are proposals only. They carry `runtime_influence=false`, `requires_human_review=true`, and default to `PROPOSED`.

## 3. Non-Goals

Phase 7C does not change parser behavior, parser output, scoring logic, scoring weights, trend or anomaly logic, decision logic, recommendation logic, Phase 4I output contracts, `run_analysis.py` behavior, dashboard diagnostic truth, Screen 2 diagnostic evidence, or Screen 5 recommendation truth.

Phase 7C does not generate candidates from outcome patterns, persist candidates, approve candidates through a governance bridge, materialize candidates into runtime behavior, activate candidates, add dashboard learning visibility, add dashboard interactivity, add CLI learning commands, write to a database, require OCI, require ADB wallet access, require Oracle Agent Memory, call an LLM, call the network, or require environment variables.

## 4. Candidate Object Shape

The `LearningCandidate` record contains `candidate_id`, `candidate_type`, `title`, `description`, `source_evidence`, `structured_sources`, `semantic_context`, `affected_component`, `affected_domain`, `confidence`, `rationale`, `requires_human_review`, `runtime_influence`, `status`, `created_at`, `created_by`, `reviewed_by`, `review_notes`, and `materialization_reference`.

Default candidate records use empty lists for `source_evidence` and `structured_sources`, `semantic_context=None`, `confidence=0.0`, `requires_human_review=true`, `runtime_influence=false`, `status=PROPOSED`, and no reviewer or materialization reference.

## 5. Candidate Types

Supported candidate types are `parser_mapping_candidate`, `recommendation_rule_candidate`, `scoring_weight_review_candidate`, `dashboard_wording_candidate`, `dashboard_interaction_candidate`, `governance_workflow_candidate`, `semantic_summary_candidate`, `documentation_candidate`, and `validation_candidate`.

Unsupported candidate types are rejected by validation.

## 6. Candidate Statuses

Supported statuses are `PROPOSED`, `UNDER_REVIEW`, `APPROVED_FOR_IMPLEMENTATION`, `REJECTED`, `NEEDS_REVISION`, `IMPLEMENTED`, `VALIDATED`, and `CLOSED`.

`PROPOSED` is the default status. `APPROVED_FOR_IMPLEMENTATION` does not mean activated. `IMPLEMENTED` does not mean runtime influence is enabled by this model.

## 7. Validation Rules

Validation requires a supported candidate type, supported status, non-empty title, non-empty description, non-empty rationale, list-valued `source_evidence`, list-valued `structured_sources`, and `semantic_context` that is either `None` or a dictionary.

Confidence must be between `0.0` and `0.95` inclusive. Confidence must never be `1.0`.

Every candidate created by this model keeps `requires_human_review=true` and `runtime_influence=false`. `APPROVED_FOR_IMPLEMENTATION`, `IMPLEMENTED`, `VALIDATED`, and `CLOSED` still keep `runtime_influence=false`. This model must not represent runtime activation.

## 8. Deterministic ID Rules

Candidate identifiers use deterministic local inputs only. The identifier format is `CANDIDATE-<TYPE>-<STABLE_KEY>`, where the type is normalized consistently and the stable key is derived from deterministic fields such as candidate type, title, affected component, affected domain, source evidence, and a pattern id when supplied.

The model does not use random UUIDs, current timestamps, database sequences, external services, network calls, or environment-dependent values to create candidate identifiers.

## 9. Serialization Rules

Candidates serialize to plain dictionaries and reconstruct from plain dictionaries. Serialization preserves the candidate fields, keeps list and dictionary values copied, and remains deterministic for the same candidate input.

`candidates_to_dicts` returns deterministic serialized records for a supplied sequence of candidates. Serialization does not persist records and does not write files.

## 10. Pattern Conversion Boundary

`candidate_from_pattern` may convert one explicitly supplied Phase 7B outcome pattern into one `LearningCandidate`. It uses `suggested_candidate_type` when an explicit candidate type is not provided, requires a valid candidate type, preserves `source_records` as candidate evidence, sets `requires_human_review=true`, sets `runtime_influence=false`, and sets `status=PROPOSED`.

This conversion helper does not mine patterns, rank patterns, decide which patterns become candidates, approve candidates, persist candidates, or apply candidates. The candidate model is not a candidate generation engine, and candidate generation remains future Phase 7D work.

## 11. Status Transition Boundary

The status transition helper performs model-level validation only. It can return a candidate copy with a new supported status, reviewer identity, and review notes.

Actor identity is required for review statuses such as `UNDER_REVIEW`, `APPROVED_FOR_IMPLEMENTATION`, `REJECTED`, `NEEDS_REVISION`, `IMPLEMENTED`, `VALIDATED`, and `CLOSED`. Status transition keeps `runtime_influence=false` and `requires_human_review=true`.

## 12. Materialization Reference Boundary

A materialization reference may be attached for audit traceability only. The helper requires an actor and a non-empty reference.

Attaching a materialization reference does not change status, does not set `runtime_influence=true`, does not activate runtime behavior, and does not replace the separate controlled implementation, testing, validation, and contract-preservation work required outside this model.

## 13. Runtime Isolation Boundary

Phase 7C is isolated from deterministic runtime diagnosis. Parser, scoring, trend, anomaly, decision, recommendation, dashboard truth, and `run_analysis.py` paths must not import `src.learning`.

Deterministic runtime remains authoritative. Phase 7C does not alter parser/scoring/decision/recommendation behavior and does not change runtime analysis outputs.

## 14. Semantic Recall Boundary

`semantic_context` is optional and non-authoritative; semantic_context is optional and non-authoritative by design. It may support future reviewer-assist context, but it is not evidence, not a source of runtime truth, and not allowed to decide candidate validity.

Semantic recall remains non-authoritative. Semantic recall is not used as evidence by the candidate model.

## 15. Governance Boundary

Candidates require human review. Candidate approval does not modify runtime behavior, candidate approval does not equal runtime activation, and candidate records remain proposals only.

The governance bridge remains future Phase 7F work. Phase 7C does not implement approval workflows, governance bridge persistence, or runtime activation.

## 16. Dashboard Boundary

Phase 7C does not change dashboard diagnostic truth, recommendation truth, evidence truth, Screen 2 diagnostic evidence, or Screen 5 recommendation truth.

Dashboard learning visibility remains future Phase 7G work. Dashboard interactivity remains future Phase 7H work.

## 17. Relationship To Phase 7B Outcome Pattern Mining

Phase 7B outcome pattern mining produces observational pattern records. Pattern records are not learning candidates.

Phase 7C can explicitly convert one supplied pattern into one candidate proposal when called, but it does not decide whether patterns should become candidates. Phase 7B remains observational and Phase 7C remains proposal-model-only.

## 18. Relationship To Future Phase 7D Candidate Generation

Candidate generation remains future Phase 7D. Phase 7D may later decide how to generate candidates from mined patterns, but Phase 7C intentionally avoids mining, ranking, candidate selection, and generation workflows.

The existence of a candidate model does not imply autonomous learning, autonomous approval, runtime materialization, or runtime activation.

## 19. Validation Requirements

Validation must prove import safety, supported candidate type validation, supported status validation, default safety, confidence bounds, runtime influence safety, serialization determinism, deterministic ID stability, explicit pattern conversion behavior, status transition actor requirements, materialization reference safety, input non-mutation, absence of autonomous runtime-update function names, runtime import isolation, and documentation boundary coverage.

Validation must also preserve Phase 7A learning boundary tests, Phase 7B outcome pattern mining tests, and Phase 6 validation where the local environment supports it.

## 20. Acceptance Criteria

Phase 7C is accepted when the learning candidate model exists, candidate types are defined, candidate statuses are defined, validation exists, serialization exists, deterministic candidate ID creation exists, explicit pattern-to-candidate conversion exists only as a caller-invoked conversion helper, status transition validation exists, optional materialization reference attachment remains audit-only, all candidates keep `runtime_influence=false`, all candidates keep `requires_human_review=true`, no candidate generation engine exists, no governance bridge exists, no runtime learning exists, semantic recall remains non-authoritative, semantic recall is not used as evidence, dashboard interactivity remains future Phase 7H work, and deterministic runtime remains authoritative.

Phase 7C must not modify parser/scoring/decision/recommendation behavior, dashboard truth, Phase 4I contracts, generated dashboard files, governed memory persistence, or `run_analysis.py` behavior.
