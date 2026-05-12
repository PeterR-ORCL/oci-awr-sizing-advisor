# Phase 7 Component Inventory

## Purpose

This inventory lists the Phase 7 learning, dashboard, CLI, test, and documentation components. Each entry identifies purpose, phase introduced, runtime influence, dependencies, and validation coverage.

All Phase 7 components preserve the locked boundary: deterministic runtime remains authoritative, learning is candidate-based and human-governed, semantic context is reviewer-assist only, dashboard interactivity is read-only, CLI learning commands are local and actor-gated, and no runtime activation exists.

## Learning Modules

| Component | Purpose | Phase Introduced | Runtime Influence | Dependencies | Validation Coverage |
| --- | --- | --- | --- | --- | --- |
| `src/learning/outcome_pattern_miner.py` | Mines deterministic observational outcome patterns from local memory-shaped records. | 7B | None; emits records with `runtime_influence=false`. | Python standard library and local input records. | `tests/test_outcome_pattern_miner.py`, `scripts/run_phase7_validation.py`. |
| `src/learning/learning_candidate_model.py` | Defines proposal-only learning candidate records, lifecycle states, serialization, and safety flags. | 7C | None; candidates are proposal/review context only. | Python standard library. | `tests/test_learning_candidate_model.py`, `scripts/run_phase7_validation.py`. |
| `src/learning/learning_candidate_engine.py` | Converts local outcome patterns into deterministic proposal-only learning candidates. | 7D | None; does not approve, implement, persist, or activate candidates. | `learning_candidate_model.py`, `outcome_pattern_miner.py` data shapes. | `tests/test_learning_candidate_engine.py`, `scripts/run_phase7_validation.py`. |
| `src/learning/semantic_candidate_context.py` | Attaches optional local semantic reviewer-assist context to candidates. | 7E | None; semantic context is non-authoritative and reviewer-assist only. | `learning_candidate_model.py`, local semantic JSON records. | `tests/test_semantic_candidate_context.py`, `scripts/run_phase7_validation.py`. |
| `src/learning/learning_governance_bridge.py` | Applies local actor-gated candidate lifecycle transitions. | 7F | None; approval is approved for implementation only. | `learning_candidate_model.py`. | `tests/test_learning_governance_bridge.py`, `tests/test_learning_cli_commands.py`, `scripts/run_phase7_validation.py`. |

## Reporting And Dashboard Modules

| Component | Purpose | Phase Introduced | Runtime Influence | Dependencies | Validation Coverage |
| --- | --- | --- | --- | --- | --- |
| `src/reporting/html_dashboard.py` | Renders deterministic dashboard output and Phase 7 read-only learning/interactivity views. | 7G, 7H | None; presentation and browser-side exploration only. | Existing Phase 4I/Phase 6 dashboard payload contracts. | `tests/test_dashboard_learning_visibility.py`, Phase 7H dashboard tests, `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |
| `src/reporting/ai_display_metadata.py` | Provides deterministic display metadata used by the dashboard. | Existing reporting layer, referenced by 7J validation | None; display metadata only. | Python standard library. | Static compile in `scripts/run_phase7_validation.py`. |

## CLI And Scripts

| Component | Purpose | Phase Introduced | Runtime Influence | Dependencies | Validation Coverage |
| --- | --- | --- | --- | --- | --- |
| `scripts/awr_memory_cli.py` | Hosts local Phase 7I `learning` commands for status, patterns, candidates, semantic context, review, export, and validation. | 7I | None; local JSON operations only, review actions actor-gated. | `src/learning/*`, Python standard library. | `tests/test_learning_cli_commands.py`, `tests/test_awr_memory_cli.py`, `scripts/run_phase7_validation.py`, `python3 scripts/awr_memory_cli.py learning validate --json`. |
| `scripts/run_phase7_validation.py` | Consolidated local Phase 7 validation harness. | 7J | None; validation only. | Python standard library, local unittest modules. | `tests/test_phase7_validation_harness.py`, direct text and JSON runs. |
| `scripts/run_phase7h_dashboard_validation.py` | Focused Phase 7H dashboard interactivity validation runner. | 7H.9 | None; validation only. | Python standard library, dashboard unittest modules. | `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |

## Tests

| Component | Purpose | Phase Introduced | Runtime Influence | Dependencies | Validation Coverage |
| --- | --- | --- | --- | --- | --- |
| `tests/test_phase7_learning_boundary.py` | Validates Phase 7A boundaries and import isolation from runtime paths. | 7A | None. | `ast`, local files. | Run directly and through `scripts/run_phase7_validation.py`. |
| `tests/test_outcome_pattern_miner.py` | Validates observational outcome pattern mining. | 7B | None. | `src/learning/outcome_pattern_miner.py`. | Run directly and through `scripts/run_phase7_validation.py`. |
| `tests/test_learning_candidate_model.py` | Validates candidate model serialization, lifecycle, and safety flags. | 7C | None. | `src/learning/learning_candidate_model.py`. | Run directly and through `scripts/run_phase7_validation.py`. |
| `tests/test_learning_candidate_engine.py` | Validates deterministic proposal-only candidate generation. | 7D | None. | `src/learning/learning_candidate_engine.py`. | Run directly and through `scripts/run_phase7_validation.py`. |
| `tests/test_semantic_candidate_context.py` | Validates semantic context as optional non-authoritative reviewer assistance. | 7E | None. | `src/learning/semantic_candidate_context.py`. | Run directly and through `scripts/run_phase7_validation.py`. |
| `tests/test_learning_governance_bridge.py` | Validates actor-gated candidate review transitions. | 7F | None. | `src/learning/learning_governance_bridge.py`. | Run directly and through `scripts/run_phase7_validation.py`. |
| `tests/test_dashboard_learning_visibility.py` | Validates read-only dashboard learning visibility. | 7G | None. | `src/reporting/html_dashboard.py`. | Run directly and through `scripts/run_phase7_validation.py`. |
| `tests/test_dashboard_interactivity_foundation.py` | Validates the Phase 7H read-only dashboard interactivity foundation. | 7H.1 | None. | `src/reporting/html_dashboard.py`. | `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |
| `tests/test_dashboard_screen3_control_center.py` | Validates Screen 3 read-only control center exploration. | 7H.2 | None. | `src/reporting/html_dashboard.py`. | `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |
| `tests/test_dashboard_screen2_diagnostic_exploration.py` | Validates Screen 2 read-only diagnostic exploration. | 7H.3 | None. | `src/reporting/html_dashboard.py`. | `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |
| `tests/test_dashboard_screen4_historical_review_exploration.py` | Validates Screen 4 read-only historical review exploration. | 7H.4 | None. | `src/reporting/html_dashboard.py`. | `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |
| `tests/test_dashboard_screen5_recommendation_action_exploration.py` | Validates Screen 5 read-only recommendation/action exploration. | 7H.5 | None. | `src/reporting/html_dashboard.py`. | `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |
| `tests/test_dashboard_screen1_governance_parser_exploration.py` | Validates Screen 1 read-only governance/parser exploration. | 7H.6 | None. | `src/reporting/html_dashboard.py`. | `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |
| `tests/test_dashboard_screen6_fleet_governance_learning_exploration.py` | Validates Screen 6 read-only fleet/governance/semantic/learning exploration. | 7H.7 | None. | `src/reporting/html_dashboard.py`. | `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |
| `tests/test_dashboard_cross_screen_selection_propagation.py` | Validates browser-side read-only cross-screen selection propagation. | 7H.8 | None. | `src/reporting/html_dashboard.py`. | `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |
| `tests/test_dashboard_interactivity_phase7h_acceptance.py` | Validates Phase 7H acceptance boundaries. | 7H.9 | None. | `src/reporting/html_dashboard.py`, docs. | `scripts/run_phase7h_dashboard_validation.py`, `scripts/run_phase7_validation.py`. |
| `tests/test_learning_cli_commands.py` | Validates Phase 7I learning CLI commands. | 7I | None. | `scripts/awr_memory_cli.py`, `src/learning/*`. | Direct unittest, CLI validate command, `scripts/run_phase7_validation.py`. |
| `tests/test_awr_memory_cli.py` | Validates unified memory CLI safety, including learning command integration. | 7I coverage over existing CLI | None. | `scripts/awr_memory_cli.py`. | `scripts/run_phase7_validation.py`. |
| `tests/test_phase7_validation_harness.py` | Validates the consolidated Phase 7J validation harness. | 7J | None. | `scripts/run_phase7_validation.py`, docs. | Direct unittest. |

## Documentation

| Component | Purpose | Phase Introduced | Runtime Influence | Dependencies | Validation Coverage |
| --- | --- | --- | --- | --- | --- |
| `docs/architecture/phase7_learning_boundary.md` | Defines Phase 7A learning boundaries. | 7A | None. | Existing phase model. | `tests/test_phase7_learning_boundary.py`. |
| `docs/architecture/phase7_candidate_lifecycle.md` | Defines candidate lifecycle states and safety fields. | 7A | None. | Candidate model concepts. | `tests/test_phase7_learning_boundary.py`. |
| `docs/architecture/phase7_roadmap.md` | Lists Phase 7 roadmap and deferred boundaries. | 7A | None. | Phase plan. | `tests/test_phase7_learning_boundary.py`. |
| `docs/architecture/phase7_outcome_pattern_mining.md` | Documents outcome pattern mining. | 7B | None. | `outcome_pattern_miner.py`. | Phase 7 validation documentation checks. |
| `docs/architecture/phase7_learning_candidate_model.md` | Documents candidate model. | 7C | None. | `learning_candidate_model.py`. | Phase 7 validation documentation checks. |
| `docs/architecture/phase7_candidate_generation_engine.md` | Documents candidate generation. | 7D | None. | `learning_candidate_engine.py`. | Phase 7 validation documentation checks. |
| `docs/architecture/phase7_semantic_candidate_context.md` | Documents semantic reviewer-assist context. | 7E | None. | `semantic_candidate_context.py`. | Phase 7 validation documentation checks. |
| `docs/architecture/phase7_learning_governance_bridge.md` | Documents actor-gated governance bridge. | 7F | None. | `learning_governance_bridge.py`. | Phase 7 validation documentation checks. |
| `docs/architecture/phase7_dashboard_learning_visibility.md` | Documents dashboard learning visibility. | 7G | None. | `html_dashboard.py`. | `tests/test_dashboard_learning_visibility.py`. |
| `docs/architecture/phase7_dashboard_interactivity_foundation.md` | Documents Phase 7H.1 interactivity foundation. | 7H.1 | None. | `html_dashboard.py`. | Phase 7H tests. |
| `docs/architecture/phase7_screen3_control_center.md` | Documents Screen 3 read-only selectors. | 7H.2 | None. | `html_dashboard.py`. | Phase 7H tests. |
| `docs/architecture/phase7_screen2_diagnostic_exploration.md` | Documents Screen 2 read-only diagnostic exploration. | 7H.3 | None. | `html_dashboard.py`. | Phase 7H tests. |
| `docs/architecture/phase7_screen4_historical_review_exploration.md` | Documents Screen 4 read-only historical review exploration. | 7H.4 | None. | `html_dashboard.py`. | Phase 7H tests. |
| `docs/architecture/phase7_screen5_recommendation_action_exploration.md` | Documents Screen 5 read-only recommendation/action exploration. | 7H.5 | None. | `html_dashboard.py`. | Phase 7H tests. |
| `docs/architecture/phase7_screen1_governance_parser_exploration.md` | Documents Screen 1 read-only governance/parser exploration. | 7H.6 | None. | `html_dashboard.py`. | Phase 7H tests. |
| `docs/architecture/phase7_screen6_fleet_governance_learning_exploration.md` | Documents Screen 6 read-only fleet/governance/semantic/learning exploration. | 7H.7 | None. | `html_dashboard.py`. | Phase 7H tests. |
| `docs/architecture/phase7_cross_screen_selection_propagation.md` | Documents browser-side cross-screen selection propagation. | 7H.8 | None. | `html_dashboard.py`. | Phase 7H tests. |
| `docs/architecture/phase7_dashboard_interactivity_architecture.md` | Consolidates Phase 7H dashboard interactivity architecture. | 7H.9 | None. | Phase 7H docs. | `tests/test_dashboard_interactivity_phase7h_acceptance.py`. |
| `docs/architecture/phase7_dashboard_interactivity_validation_matrix.md` | Documents Phase 7H validation coverage. | 7H.9 | None. | Phase 7H tests. | `tests/test_dashboard_interactivity_phase7h_acceptance.py`. |
| `docs/architecture/phase7_dashboard_interactivity_acceptance_criteria.md` | Documents Phase 7H acceptance criteria. | 7H.9 | None. | Phase 7H docs and tests. | `tests/test_dashboard_interactivity_phase7h_acceptance.py`. |
| `docs/architecture/phase7_learning_cli_operations.md` | Documents local Phase 7I CLI operations. | 7I | None. | `scripts/awr_memory_cli.py`. | `tests/test_learning_cli_commands.py`. |
| `docs/architecture/phase7_validation_matrix.md` | Documents Phase 7J validation groups. | 7J | None. | `scripts/run_phase7_validation.py`. | `tests/test_phase7_validation_harness.py`. |
| `docs/architecture/phase7_validation_harness.md` | Documents the Phase 7J validation harness. | 7J | None. | `scripts/run_phase7_validation.py`. | `tests/test_phase7_validation_harness.py`. |

## Acceptance Summary

This component inventory is accepted when it shows every Phase 7 component as documentation-only, validation-only, local-only, read-only, or proposal-only as applicable; identifies validation coverage; and preserves the rule that no Phase 7 component activates runtime behavior or changes parser/scoring/decision/recommendation truth.
