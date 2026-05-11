# Architecture Documentation

This directory contains architecture, governance, validation, and operational documentation for the Agentic AI AWR Advisor project.

## Recommended Reading Order

1. [Phase 7 Learning Boundary](phase7_learning_boundary.md)
2. [Phase 7 Candidate Lifecycle](phase7_candidate_lifecycle.md)
3. [Phase 7 Outcome Pattern Mining](phase7_outcome_pattern_mining.md)
4. [Phase 7 Learning Candidate Model](phase7_learning_candidate_model.md)
5. [Phase 7 Candidate Generation Engine](phase7_candidate_generation_engine.md)
6. [Phase 7 Semantic Candidate Context](phase7_semantic_candidate_context.md)
7. [Phase 7 Roadmap](phase7_roadmap.md)
8. [Phase 6 Release Notes](phase6_release_notes.md)
9. [Phase 6 Memory Architecture](phase6_memory_architecture.md)
10. [Phase 6 Component Inventory](phase6_component_inventory.md)
11. [Phase 6 Repository Map](phase6_repository_map.md)
12. [Phase 6 Operational Model](phase6_operational_model.md)
13. [Phase 6 CLI Operations](phase6_cli_operations.md)
14. [Phase 6 Validation Matrix](phase6_validation_matrix.md)
15. [Phase 6 Production Readiness](phase6_production_readiness.md)
16. [Phase 6 Demo Walkthrough](phase6_demo_walkthrough.md)

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
- [Phase 7 Roadmap](phase7_roadmap.md)

These documents define Phase 7A learning as boundary-only, Phase 7B outcome pattern mining as deterministic and observational only, Phase 7C learning candidates as proposal-only serializable records, Phase 7D candidate generation as deterministic proposal-only conversion from outcome patterns to candidate records, and Phase 7E semantic candidate context as optional reviewer-assist context with `runtime_influence=false`, `requires_human_review=true`, and no runtime activation. Dashboard interactivity is documented as future Phase 7H work only.

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

Phase 7A is boundary-only and introduces no runtime learning behavior. Phase 7B adds observational outcome pattern mining only. Phase 7C adds the deterministic learning candidate model only. Phase 7D adds deterministic candidate generation only. Phase 7E adds optional reviewer-assist semantic candidate context only.

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
- Dashboard interactivity is deferred to future Phase 7H work and remains exploratory/read-only.
- No autonomous learning behavior exists in Phase 7A, Phase 7B, Phase 7C, Phase 7D, or Phase 7E.
