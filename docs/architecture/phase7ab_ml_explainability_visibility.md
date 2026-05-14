# Phase 7AB ML Explainability Visibility

## 1. Purpose

Phase 7AB exposes existing Phase 7 ML/adaptive scoring and runtime-integration state through read-only dashboard visibility.

## 2. Scope

The scope is dashboard visibility for deterministic score, trend-aware score, shadow ML score, score deltas, ML explanation summaries, feature contributions, model registry posture, runtime gate posture, adapter result posture, fallback posture, and readiness/certification posture.

## 3. Non-Goals

Phase 7AB does not activate runtime behavior, does not change scoring, does not change recommendations, does not change parser behavior, does not change Phase 4I, does not add write controls, and does not implement Phase 8 sizing/TCO.

## 4. Dashboard Visibility

Dashboard visibility is read-only. It displays ML/adaptive state only and does not apply, approve, reject, activate, deploy, or roll back anything.

## 5. Screen 6 Placement

The ML / Adaptive Explainability Visibility section is placed on Screen 6 - Fleet / Governance / Semantic / Learning. It is not added to Screen 2 as diagnostic evidence and is not added to Screen 5 as recommendation truth.

## 6. ML Explanation Visibility

ML explanations are not diagnostic evidence. ML explanations are not recommendation truth. They explain advisory and shadow outputs only.

## 7. Model Registry Visibility

Model registry visibility does not deploy models. It shows governance metadata such as model id, model family, governance status, shadow eligibility, runtime eligibility request state, runtime eligibility grant state, and runtime active state.

## 8. Runtime Gate Visibility

Runtime gate visibility does not activate runtime. It shows whether a component was allowed for consideration, denied, or still default-denied.

## 9. Adapter Result Visibility

Adapter result visibility is advisory/result-only. It can show scoring, recommendation, and parser integration result summaries, but cannot apply them to runtime.

## 10. Fallback / Rollback Visibility

Fallback visibility does not execute rollback. It shows final runtime posture, fallback requirement, rollback requirement, rollback availability, and deterministic fallback posture.

## 11. Safety Labels

The dashboard section must show: Read-only, Advisory / shadow only, Not diagnostic evidence, Not recommendation truth, Deterministic runtime remains authoritative, runtime_active=false, runtime_influence=false, runtime_influence_granted=false, runtime_eligibility_granted=false, No runtime activation, No backend writes, No approval controls, and No rollback execution.

## 12. Runtime Truth Boundary

Deterministic runtime remains authoritative. ML/adaptive visibility is not runtime truth, does not change runtime scoring, and does not change Phase 4I output.

## 13. Diagnostic Evidence Boundary

ML explanations are not diagnostic evidence. Diagnostic truth continues to come from deterministic backend contracts.

## 14. Recommendation Truth Boundary

ML explanations are not recommendation truth. Recommendation truth continues to come from deterministic recommendation output.

## 15. Dashboard Write-Control Boundary

No dashboard approval controls, write controls, activation controls, apply controls, or rollback controls are added in Phase 7AB.

## 16. Relationship to 7AA.1-7AA.7

Phase 7AB reads and displays the 7AA gate, context, adapter result, fallback, validation, and readiness posture. It does not alter those records or make them active runtime behavior.

## 17. Relationship to Phase 7S-7Z

Phase 7AB makes existing ML/adaptive scoring intelligence visible. It does not train models, deploy models, grant runtime eligibility, or replace deterministic scoring.

## 18. Relationship to Phase 8

Phase 8 sizing/TCO is not implemented. Phase 7AB does not add what-if, sizing, cost, or capacity advisory behavior.

## 19. Acceptance Criteria

Acceptance requires read-only Screen 6 visibility, safe empty state, safety labels, no write controls, no runtime activation, no rollback execution, no diagnostic evidence change, no recommendation truth change, and no runtime behavior changes are made.
