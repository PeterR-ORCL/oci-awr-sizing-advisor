# Phase 7B Outcome Pattern Mining

## 1. Purpose

Phase 7B introduces deterministic outcome pattern mining for governed Phase 6 memory-style records. The miner may inspect in-memory records for runs, recommendations, actions, outcomes, feedback, unknown signals, knowledge requests, and knowledge artifacts, then summarize repeated learning-relevant patterns.

Outcome pattern mining is observational only. Pattern records are not learning candidates yet, do not approve anything, do not apply anything, and do not modify runtime truth.

## 2. Scope

Phase 7B adds a local, deterministic, read-only pattern miner that accepts plain dictionaries and lists supplied by the caller. It produces structured pattern records for later review and possible future candidate generation.

The miner may identify repeated rejected recommendations, poor outcomes after actions, recurring issues after actions, repeated unknown parser signals, repeated feedback themes, and recurring domain issues.

## 3. Non-Goals

Phase 7B does not change parser behavior, parser output, scoring logic, scoring weights, trend or anomaly logic, decision logic, recommendation logic, Phase 4I output contracts, run_analysis.py behavior, dashboard diagnostic truth, Screen 2 diagnostic evidence, or Screen 5 recommendation truth.

Phase 7B does not implement the candidate model, candidate persistence, candidate approval, candidate generation, semantic candidate context, governance bridge, dashboard learning visibility, dashboard interactivity, CLI learning commands, database writes, OCI calls, ADB access, Oracle Agent Memory calls, LLM calls, network calls, or environment-variable-dependent behavior.

## 4. Inputs

The miner accepts caller-provided in-memory records grouped by optional keys such as `runs`, `recommendations`, `actions`, `outcomes`, `feedback`, `unknown_signals`, `knowledge_requests`, and `knowledge_artifacts`.

All categories are optional. Missing categories are treated as empty. Flexible record shapes are supported through tolerant aliases for identifiers, domains, recommendation and action labels, statuses, outcomes, unknown signals, and feedback text.

## 5. Output Pattern Shape

Each pattern record contains `pattern_id`, `pattern_type`, `title`, `description`, `source_records`, `affected_domain`, `affected_component`, `recurrence_count`, `observed_effect`, `confidence`, `rationale`, `requires_human_review`, `runtime_influence`, and `suggested_candidate_type`.

Every pattern record must keep `runtime_influence=false` and `requires_human_review=true`. Source records must include structured audit references such as source type, source id when available, normalized grouping key, and relevant fields used for grouping.

## 6. Pattern Types

`repeated_rejected_recommendation` identifies a recommendation or action label that appears rejected multiple times.

`poor_outcome_after_action` identifies repeated cases where an action was taken and the later outcome remained poor, worsened, failed, or unresolved.

`recurring_issue_after_action` identifies repeated cases where the same issue domain appears after the same action type.

`repeated_unknown_signal` identifies repeated parser unknown signals by section and signature.

`repeated_feedback_theme` identifies repeated feedback themes such as confusing wording, insufficient evidence, recommendation not useful, or false positive.

`recurring_domain_issue` identifies repeated CPU, IO, MEMORY, COMMIT, RAC, or ADG issue domains across governed run, recommendation, or outcome records.

## 7. Deterministic Mining Rules

The miner uses normalized keys, stable sorting, and deterministic pattern ids. It does not use random UUIDs, timestamps, live database state, semantic search, LLM output, or external services.

The same input must produce the same output order and values. The miner must not mutate input records, write files, call a database, call the network, require OCI, require ADB wallet configuration, or require Oracle Agent Memory.

## 8. Confidence Rules

Confidence is advisory only. It does not approve a candidate, create a candidate, trigger runtime changes, or influence deterministic analysis.

The deterministic mapping is recurrence count 2 to 0.50, recurrence count 3 to 0.65, recurrence count 4 to 0.75, and recurrence count 5 or higher to 0.85. Confidence is clamped below 1.0 and must never be returned as 1.0.

## 9. Suggested Candidate Type Mapping

Pattern records may include `suggested_candidate_type` for later phases only.

`repeated_rejected_recommendation`, `poor_outcome_after_action`, and `recurring_issue_after_action` map to `recommendation_rule_candidate`.

`repeated_unknown_signal` maps to `parser_mapping_candidate`.

`repeated_feedback_theme` maps to `dashboard_wording_candidate` for wording or evidence themes and to `recommendation_rule_candidate` for recommendation usefulness or false-positive themes.

`recurring_domain_issue` maps to `scoring_weight_review_candidate` or may inform a future `recommendation_rule_candidate`.

These suggestions do not create candidates, approve candidates, or apply candidates.

## 10. Runtime Isolation Boundary

Phase 7B is outside deterministic runtime diagnosis. It must not be imported by parser, scoring, trend, anomaly, decision, recommendation, run_analysis.py, or dashboard truth paths.

Deterministic runtime remains authoritative. Phase 7B does not alter parser/scoring/decision/recommendation behavior and does not change runtime analysis outputs.

## 11. Semantic Recall Boundary

Semantic recall is not used as evidence for Phase 7B mining. The miner does not call semantic recall, semantic search, Oracle Agent Memory, embeddings, vector search, or LLMs.

Semantic recall remains non-authoritative and reviewer-assist only. Pattern records may be reviewed by humans later, but semantic recall cannot decide pattern validity or runtime truth.

## 12. Governance Boundary

Human review remains required for every pattern. Pattern records require `requires_human_review=true` and are only observational summaries.

The candidate model is future Phase 7C. Candidate generation is future Phase 7D. Governance review, approval, materialization, and activation are separate future work and are not implemented in Phase 7B.

## 13. Dashboard Boundary

Phase 7B does not change dashboard diagnostic truth, recommendation truth, evidence truth, or displayed backend conclusions.

Dashboard learning visibility is future Phase 7G. Dashboard interactivity remains future Phase 7H. Dashboard interactivity remains future Phase 7H work and is not implemented by outcome pattern mining.

## 14. Validation Requirements

Validation must prove the miner is safe to import, handles empty input and missing optional categories, detects each supported pattern type deterministically, produces stable serialized output, includes source evidence, preserves `runtime_influence=false`, preserves `requires_human_review=true`, does not mutate input records, and does not introduce isolated runtime imports.

Validation must also preserve Phase 7A learning boundary tests and Phase 6 validation where the local environment supports it.

## 15. Acceptance Criteria

Phase 7B is accepted when the outcome pattern miner exists, is deterministic, is read-only, uses only in-memory caller-provided records, produces structured and auditable pattern records, keeps `runtime_influence=false`, requires human review, creates no learning candidates, implements no runtime learning, uses no semantic recall as evidence, and leaves deterministic runtime truth authoritative.

Phase 7B must not modify parser/scoring/decision/recommendation behavior, dashboard truth, Phase 4I contracts, generated dashboard files, governed memory persistence, or run_analysis.py behavior.
