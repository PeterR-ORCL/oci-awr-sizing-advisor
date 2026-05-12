# Architecture Documentation

This directory contains architecture, governance, validation, and operational documentation for the Agentic AI AWR Advisor project.

## Recommended Reading Order

1. [Phase 7 Learning Boundary](phase7_learning_boundary.md)
2. [Phase 7 Candidate Lifecycle](phase7_candidate_lifecycle.md)
3. [Phase 7 Outcome Pattern Mining](phase7_outcome_pattern_mining.md)
4. [Phase 7 Learning Candidate Model](phase7_learning_candidate_model.md)
5. [Phase 7 Candidate Generation Engine](phase7_candidate_generation_engine.md)
6. [Phase 7 Semantic Candidate Context](phase7_semantic_candidate_context.md)
7. [Phase 7 Learning Governance Bridge](phase7_learning_governance_bridge.md)
8. [Phase 7 Dashboard Learning Visibility](phase7_dashboard_learning_visibility.md)
9. [Phase 7 Dashboard Interactivity Foundation](phase7_dashboard_interactivity_foundation.md)
10. [Phase 7 Screen 3 Control Center](phase7_screen3_control_center.md)
11. [Phase 7 Screen 2 Diagnostic Exploration](phase7_screen2_diagnostic_exploration.md)
12. [Phase 7 Screen 4 Historical Review Exploration](phase7_screen4_historical_review_exploration.md)
13. [Phase 7 Screen 5 Recommendation / Action Exploration](phase7_screen5_recommendation_action_exploration.md)
14. [Phase 7 Screen 1 Governance / Parser Exploration](phase7_screen1_governance_parser_exploration.md)
15. [Phase 7 Screen 6 Fleet / Governance / Semantic / Learning Exploration](phase7_screen6_fleet_governance_learning_exploration.md)
16. [Phase 7 Cross-Screen Selection Propagation](phase7_cross_screen_selection_propagation.md)
17. [Phase 7 Roadmap](phase7_roadmap.md)
18. [Phase 6 Release Notes](phase6_release_notes.md)
19. [Phase 6 Memory Architecture](phase6_memory_architecture.md)
20. [Phase 6 Component Inventory](phase6_component_inventory.md)
21. [Phase 6 Repository Map](phase6_repository_map.md)
22. [Phase 6 Operational Model](phase6_operational_model.md)
23. [Phase 6 CLI Operations](phase6_cli_operations.md)
24. [Phase 6 Validation Matrix](phase6_validation_matrix.md)
25. [Phase 6 Production Readiness](phase6_production_readiness.md)
26. [Phase 6 Demo Walkthrough](phase6_demo_walkthrough.md)

## Runtime And Architecture

- [Phase 6 Memory Architecture](phase6_memory_architecture.md)
- [Phase 6 Operational Model](phase6_operational_model.md)
- [Phase 6 Component Inventory](phase6_component_inventory.md)
- [Phase 6 Repository Map](phase6_repository_map.md)
- [Phase 6 Acceptance Criteria](phase6_acceptance_criteria.md)

These documents define deterministic runtime truth, governed memory, structured recall, governance workflows, semantic recall isolation, dashboard visibility, and operational boundaries.

## Phase 7 Learning Boundary

- [Phase 7 Learning Boundary](phase7_learning_boundary.md)
- [Phase 7 Candidate Lifecycle](phase7_candidate_lifecycle.md)
- [Phase 7 Outcome Pattern Mining](phase7_outcome_pattern_mining.md)
- [Phase 7 Learning Candidate Model](phase7_learning_candidate_model.md)
- [Phase 7 Candidate Generation Engine](phase7_candidate_generation_engine.md)
- [Phase 7 Semantic Candidate Context](phase7_semantic_candidate_context.md)
- [Phase 7 Learning Governance Bridge](phase7_learning_governance_bridge.md)
- [Phase 7 Dashboard Learning Visibility](phase7_dashboard_learning_visibility.md)
- [Phase 7 Dashboard Interactivity Foundation](phase7_dashboard_interactivity_foundation.md)
- [Phase 7 Screen 3 Control Center](phase7_screen3_control_center.md)
- [Phase 7 Screen 2 Diagnostic Exploration](phase7_screen2_diagnostic_exploration.md)
- [Phase 7 Screen 4 Historical Review Exploration](phase7_screen4_historical_review_exploration.md)
- [Phase 7 Screen 5 Recommendation / Action Exploration](phase7_screen5_recommendation_action_exploration.md)
- [Phase 7 Screen 1 Governance / Parser Exploration](phase7_screen1_governance_parser_exploration.md)
- [Phase 7 Screen 6 Fleet / Governance / Semantic / Learning Exploration](phase7_screen6_fleet_governance_learning_exploration.md)
- [Phase 7 Cross-Screen Selection Propagation](phase7_cross_screen_selection_propagation.md)
- [Phase 7 Roadmap](phase7_roadmap.md)

These documents define Phase 7A learning as boundary-only, Phase 7B outcome pattern mining as deterministic and observational only, Phase 7C learning candidates as proposal-only serializable records, Phase 7D candidate generation as deterministic proposal-only conversion from outcome patterns to candidate records, Phase 7E semantic candidate context as optional reviewer-assist context with `runtime_influence=false`, `requires_human_review=true`, and no runtime activation, Phase 7F learning governance bridge as local deterministic review transitions that are approved for implementation only and not runtime integration, Phase 7G dashboard learning visibility as read-only Screen 6 visibility only, Phase 7H.1 dashboard interactivity foundation as browser-side read-only selection state only, Phase 7H.2 Screen 3 Control Center as read-only exploratory selectors only, Phase 7H.3 Screen 2 Diagnostic Exploration as read-only deterministic evidence exploration only, Phase 7H.4 Screen 4 Historical Review Exploration as read-only deterministic historical context exploration only, Phase 7H.5 Screen 5 Recommendation / Action Exploration as read-only deterministic/governed recommendation/action context exploration only, Phase 7H.6 Screen 1 Governance / Parser Exploration as read-only parser/governance context exploration only, Phase 7H.7 Screen 6 Fleet / Governance / Semantic / Learning Exploration as read-only fleet/governance/semantic/learning context exploration only, and Phase 7H.8 Cross-Screen Selection Propagation as browser-side read-only selection synchronization only.

## Governance And Semantic Memory

- [Oracle Agent Memory Boundary](oracle_agent_memory_boundary.md)

These documents define the non-authoritative semantic recall boundary, reviewer-assist model, governance assistance constraints, and Oracle Agent Memory isolation rules.

## CLI And Operations

- [Phase 6 CLI Operations](phase6_cli_operations.md)
- [Phase 6 Operational Checklist](phase6_operational_checklist.md)
- [Phase 6 Demo Walkthrough](phase6_demo_walkthrough.md)

These documents support operator onboarding, demo execution, read-only versus write-command discipline, and repository handoff.

## Validation And Readiness

- [Phase 6 Validation Matrix](phase6_validation_matrix.md)
- [Phase 6 Production Readiness](phase6_production_readiness.md)
- [Phase 6 Release Certification](phase6_release_certification.md)

These documents certify isolation guarantees, validation coverage, operational readiness, release posture, and production-readiness criteria.

## Release Package

- [Phase 6 Release Notes](phase6_release_notes.md)
- [Phase 6 Release Certification](phase6_release_certification.md)
- [Phase 6 Production Readiness](phase6_production_readiness.md)
- [Phase 6 Operational Checklist](phase6_operational_checklist.md)

## Repository Governance

- [Repository Structure and Naming Policy](repository_structure_and_naming.md)

This document defines architectural naming semantics, generated artifact policy, data pack policy, schema organization, adapter naming, and rename/refactor guardrails.

## Phase Boundary Summary

Phase 7A is boundary-only and introduces no runtime learning behavior. Phase 7B adds observational outcome pattern mining only. Phase 7C adds the deterministic learning candidate model only. Phase 7D adds deterministic candidate generation only. Phase 7E adds optional reviewer-assist semantic candidate context only. Phase 7F adds local deterministic governance transitions only. Phase 7G adds read-only dashboard learning visibility only. Phase 7H.1 adds read-only dashboard interactivity foundation only. Phase 7H.2 adds read-only Screen 3 Control Center selectors only. Phase 7H.3 adds read-only Screen 2 Diagnostic Exploration only. Phase 7H.4 adds read-only Screen 4 Historical Review Exploration only. Phase 7H.5 adds read-only Screen 5 Recommendation / Action Exploration only. Phase 7H.6 adds read-only Screen 1 Governance / Parser Exploration only. Phase 7H.7 adds read-only Screen 6 Fleet / Governance / Semantic / Learning Exploration only. Phase 7H.8 adds browser-side only Cross-Screen Selection Propagation.

- Deterministic runtime remains authoritative.
- Semantic recall remains non-authoritative.
- Semantic recall is not used as evidence for Phase 7B outcome pattern mining.
- Governance remains human-controlled.
- Dashboard truth remains deterministic.
- Learning is candidate-based and human-reviewed.
- Learning candidates do not modify runtime behavior.
- Pattern records are not learning candidates.
- Outcome pattern records keep `runtime_influence=false`.
- Learning candidate records keep `runtime_influence=false` and `requires_human_review=true`.
- The Phase 7D candidate generation engine is proposal-only and does not approve, implement, or activate candidates.
- Phase 7E semantic candidate context is optional, reviewer-assist only, non-authoritative, not source evidence, and cannot change confidence or status.
- Phase 7F governance is approved for implementation only, is not runtime integration, and does not activate runtime behavior.
- Phase 7G dashboard learning visibility is read-only, keeps learning candidates out of diagnostic evidence and recommendation truth, adds no approval controls and no write controls, shows `runtime_influence=false` and `requires_human_review=true`, and keeps full dashboard interactivity in future Phase 7H.
- Phase 7H.1 dashboard interactivity foundation is read-only, exploratory only, adds no backend writes, adds no approval controls and no write controls, does not change diagnostic truth, does not change recommendation truth, keeps screen-specific selection behavior in later Phase 7H subtasks, and defers full cross-screen propagation to Phase 7H.8.
- Phase 7H.2 Screen 3 Control Center is read-only, exploratory only, adds no backend writes, adds no approval controls and no write controls, does not change diagnostic truth, does not change recommendation truth, does not change primary issue, does not change severity, and defers full cross-screen propagation to Phase 7H.8.
- Phase 7H.3 Screen 2 Diagnostic Exploration is read-only, exploratory only, adds no backend writes, adds no approval controls and no write controls, does not change diagnostic truth, does not change primary issue, does not change severity, does not change confidence, does not change recommendation truth, keeps semantic/learning context out of diagnostic evidence, and defers full cross-screen propagation to Phase 7H.8.
- Phase 7H.4 Screen 4 Historical Review Exploration is read-only, exploratory only, adds no backend writes, adds no approval controls and no write controls, does not change historical truth, does not recalculate trends, does not reclassify anomalies, does not change baseline, does not change similarity results, does not change diagnostic truth, does not change recommendation truth, keeps semantic/learning context out of historical evidence, and defers full cross-screen propagation to Phase 7H.8.
- Phase 7H.5 Screen 5 Recommendation / Action Exploration is read-only, exploratory only, adds no backend writes, adds no approval controls and no write controls, does not change recommendation truth, does not change recommendation priority or rank, does not change recommendation rationale, does not change supporting evidence, does not change diagnostic truth, does not change historical truth, keeps learning candidates out of recommendation evidence, keeps semantic context out of recommendation evidence, does not mutate action/outcome/feedback records, and defers full cross-screen propagation to Phase 7H.8.
- Phase 7H.6 Screen 1 Governance / Parser Exploration is read-only, exploratory only, adds no backend writes, adds no approval controls and no write controls, does not change loader behavior, does not change parser output, does not classify unknown signals, does not approve mappings, does not materialize artifacts, does not change governance state, does not create/update knowledge requests, does not change diagnostic truth, does not change recommendation truth, keeps semantic/learning context out of parser evidence, and defers full cross-screen propagation to Phase 7H.8.
- Phase 7H.7 Screen 6 Fleet / Governance / Semantic / Learning Exploration is read-only, exploratory only, adds no backend writes, adds no approval controls and no write controls, does not change fleet posture, does not change governance state, does not classify unknown signals, does not materialize artifacts, does not change diagnostic truth, does not change recommendation truth, keeps semantic context reviewer-assist only, keeps semantic context out of diagnostic evidence and recommendation truth, keeps learning candidates proposal/review context only, keeps learning candidates out of diagnostic evidence and recommendation truth, keeps pattern records from becoming candidates, and defers full cross-screen propagation to Phase 7H.8.
- Phase 7H.8 Cross-Screen Selection Propagation is browser-side only, read-only, exploratory only, adds no backend writes, adds no API calls, adds no approval controls and no write controls, keeps URL hash/localStorage state non-authoritative, does not change parser output, diagnostic truth, historical truth, recommendation truth, governance state, or candidate status, keeps semantic context reviewer-assist only, keeps learning candidates proposal/review context only, and adds no Phase 7I CLI learning commands.
- No autonomous learning behavior exists in Phase 7A, Phase 7B, Phase 7C, Phase 7D, Phase 7E, Phase 7F, Phase 7G, Phase 7H.1, Phase 7H.2, Phase 7H.3, Phase 7H.4, Phase 7H.5, Phase 7H.6, Phase 7H.7, or Phase 7H.8.
