# Phase 7 Repository Map

## 1. Purpose

This repository map documents the files and areas intentionally changed by Phase 7. It helps reviewers understand where learning, dashboard visibility, dashboard interactivity, CLI operations, validation, and documentation live without confusing those areas with deterministic runtime truth paths.

## 2. Repository Areas Changed By Phase 7

Phase 7 intentionally changed these areas:

| Area | Role | Runtime Influence |
| --- | --- | --- |
| `src/learning/` | Local learning pattern, candidate, semantic context, and governance modules. | None. |
| `src/reporting/` | Read-only dashboard learning visibility and dashboard interactivity rendering. | None. |
| `scripts/` | Local learning CLI and validation runners. | None. |
| `tests/` | Phase 7 local deterministic validation. | None. |
| `docs/architecture/` | Phase 7 architecture, operations, validation, and final documentation. | None. |

parser/scoring/decision/recommendation runtime paths remain isolated.

## 3. src/learning Map

`src/learning/` contains Phase 7 learning support modules:

| File | Purpose | Boundary |
| --- | --- | --- |
| `outcome_pattern_miner.py` | Mines observational local outcome patterns. | Pattern records are not candidates and have no runtime influence. |
| `learning_candidate_model.py` | Defines proposal-only learning candidates and lifecycle state. | Candidates require human review and do not activate runtime behavior. |
| `learning_candidate_engine.py` | Converts local patterns into proposal-only candidates. | Generation is deterministic and proposal-only. |
| `semantic_candidate_context.py` | Attaches optional local semantic reviewer-assist context. | Semantic context is reviewer-assist only and non-authoritative. |
| `learning_governance_bridge.py` | Applies local actor-gated candidate review transitions. | Approval is approved for implementation only. |

Phase 7 learning modules are not imported by runtime truth paths.

## 4. src/reporting Map

`src/reporting/html_dashboard.py` contains the dashboard rendering surface that displays Phase 7 learning visibility and Phase 7H read-only interactivity. `src/reporting/ai_display_metadata.py` remains deterministic display metadata.

Dashboard behavior is presentation-only and read-only for Phase 7 learning. Dashboard interactivity cannot change parser output, diagnostic truth, historical truth, recommendation truth, governance state, candidate status, or runtime behavior.

## 5. scripts Map

`scripts/awr_memory_cli.py` hosts the local Phase 7I learning command group. It reads local JSON, emits local text or JSON, and requires an actor for review transitions.

`scripts/run_phase7_validation.py` hosts the consolidated Phase 7J validation harness. `scripts/run_phase7h_dashboard_validation.py` hosts focused Phase 7H dashboard validation.

scripts/run_analysis.py remains protected. It is not changed by Phase 7K and is not a learning activation entrypoint.

## 6. tests Map

Phase 7 tests live in `tests/` and cover:

| Test File | Scope |
| --- | --- |
| `test_phase7_learning_boundary.py` | Phase 7A boundary, docs, and import isolation. |
| `test_outcome_pattern_miner.py` | Phase 7B outcome pattern mining. |
| `test_learning_candidate_model.py` | Phase 7C candidate model. |
| `test_learning_candidate_engine.py` | Phase 7D candidate generation. |
| `test_semantic_candidate_context.py` | Phase 7E semantic candidate context. |
| `test_learning_governance_bridge.py` | Phase 7F governance bridge. |
| `test_dashboard_learning_visibility.py` | Phase 7G dashboard learning visibility. |
| `test_dashboard_interactivity_foundation.py` | Phase 7H.1 interactivity foundation. |
| `test_dashboard_screen3_control_center.py` | Phase 7H.2 Screen 3 exploration. |
| `test_dashboard_screen2_diagnostic_exploration.py` | Phase 7H.3 Screen 2 exploration. |
| `test_dashboard_screen4_historical_review_exploration.py` | Phase 7H.4 Screen 4 exploration. |
| `test_dashboard_screen5_recommendation_action_exploration.py` | Phase 7H.5 Screen 5 exploration. |
| `test_dashboard_screen1_governance_parser_exploration.py` | Phase 7H.6 Screen 1 exploration. |
| `test_dashboard_screen6_fleet_governance_learning_exploration.py` | Phase 7H.7 Screen 6 exploration. |
| `test_dashboard_cross_screen_selection_propagation.py` | Phase 7H.8 cross-screen propagation. |
| `test_dashboard_interactivity_phase7h_acceptance.py` | Phase 7H acceptance. |
| `test_learning_cli_commands.py` | Phase 7I learning CLI. |
| `test_phase7_validation_harness.py` | Phase 7J validation harness. |
| `test_phase7_documentation_finalization.py` | Phase 7K documentation finalization. |

## 7. docs/architecture Map

Phase 7 architecture documentation lives in `docs/architecture/`:

| Document | Scope |
| --- | --- |
| `phase7_learning_boundary.md` | Learning boundary. |
| `phase7_candidate_lifecycle.md` | Candidate lifecycle. |
| `phase7_roadmap.md` | Phase 7 roadmap. |
| `phase7_outcome_pattern_mining.md` | Outcome pattern mining. |
| `phase7_learning_candidate_model.md` | Candidate model. |
| `phase7_candidate_generation_engine.md` | Candidate generation. |
| `phase7_semantic_candidate_context.md` | Semantic candidate context. |
| `phase7_learning_governance_bridge.md` | Learning governance bridge. |
| `phase7_dashboard_learning_visibility.md` | Dashboard learning visibility. |
| `phase7_dashboard_interactivity_foundation.md` | Dashboard interactivity foundation. |
| `phase7_screen3_control_center.md` | Screen 3 interactivity. |
| `phase7_screen2_diagnostic_exploration.md` | Screen 2 interactivity. |
| `phase7_screen4_historical_review_exploration.md` | Screen 4 interactivity. |
| `phase7_screen5_recommendation_action_exploration.md` | Screen 5 interactivity. |
| `phase7_screen1_governance_parser_exploration.md` | Screen 1 interactivity. |
| `phase7_screen6_fleet_governance_learning_exploration.md` | Screen 6 interactivity. |
| `phase7_cross_screen_selection_propagation.md` | Cross-screen selection propagation. |
| `phase7_dashboard_interactivity_architecture.md` | Phase 7H interactivity architecture. |
| `phase7_dashboard_interactivity_validation_matrix.md` | Phase 7H validation matrix. |
| `phase7_dashboard_interactivity_acceptance_criteria.md` | Phase 7H acceptance criteria. |
| `phase7_learning_cli_operations.md` | Phase 7I CLI operations. |
| `phase7_validation_matrix.md` | Phase 7J validation matrix. |
| `phase7_validation_harness.md` | Phase 7J validation harness. |
| `phase7_learning_architecture.md` | Phase 7K final architecture summary. |
| `phase7_operational_model.md` | Phase 7K operational model. |
| `phase7_component_inventory.md` | Phase 7K component inventory. |
| `phase7_repository_map.md` | Phase 7K repository map. |
| `phase7_release_notes.md` | Phase 7K release notes. |
| `phase7_demo_walkthrough.md` | Phase 7K demo walkthrough. |
| `phase7_acceptance_criteria.md` | Phase 7K acceptance criteria. |

## 8. Files Not Intentionally Modified

Phase 7K does not intentionally modify parser modules, scoring modules, decision modules, recommendation modules, database schema, generated dashboard HTML, `scripts/run_analysis.py`, runtime configuration, dashboard behavior code, CLI behavior code, OCI integration, ADB integration, Oracle Agent Memory integration, semantic recall live service integration, or LLM integration.

## 9. Runtime Isolation Notes

parser/scoring/decision/recommendation runtime paths remain isolated. scripts/run_analysis.py remains protected. Phase 7 learning modules are not imported by runtime truth paths.

Learning candidates keep `runtime_influence=false`. Semantic context remains reviewer-assist only. Dashboard interactivity remains read-only. CLI learning commands remain local and actor-gated.

## 10. Generated Artifact Notes

Generated dashboard HTML should not be modified unless explicitly regenerated by the normal dashboard generation path. Phase 7K does not modify generated dashboard HTML.

Documentation and tests may inspect generated artifacts where existing validation requires it, but Phase 7K does not add generated artifacts and does not change dashboard rendering behavior.

## 11. Acceptance Summary

This repository map is accepted when Phase 7 changes are limited to learning support, read-only dashboard visibility/interactivity, local CLI operations, local validation, and documentation; runtime truth paths remain isolated; `run_analysis.py` remains protected; generated dashboard HTML is untouched; and no parser/scoring/decision/recommendation behavior changes are introduced.
