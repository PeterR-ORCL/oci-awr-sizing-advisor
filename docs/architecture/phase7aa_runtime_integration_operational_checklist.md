# Phase 7AA Runtime Integration Operational Checklist

## 1. Purpose

This checklist defines the operator flow for validating and certifying Phase 7AA controlled adaptive runtime integration scaffolding.

## 2. Pre-Run Checklist

- Confirm the branch is `phase7-controlled-runtime-integration`.
- Confirm the working tree is clean before certification.
- Confirm no runtime wiring has been added to `run_analysis.py`.
- Confirm Phase 8 sizing/TCO is not implemented.

## 3. Validation Checklist

Run:

```bash
python3 scripts/run_phase7aa_runtime_integration_validation.py
python3 scripts/run_phase7aa_runtime_integration_validation.py --json
```

Do not certify if validation fails.

## 4. Runtime Gate Checklist

- Adaptive runtime is opt-in only.
- Default config denies integration.
- Deterministic runtime remains authoritative.
- Fallback and rollback references remain required.

## 5. Context Builder Checklist

- Context is read-only.
- Context is not runtime activation.
- `runtime_influence_applied=false`.
- `runtime_mutation_performed=false`.

## 6. Scoring Adapter Checklist

- Adapter does not replace runtime scoring.
- Selected advisory score is not runtime score.
- `runtime_score_applied=false`.
- Deterministic scoring remains authoritative.

## 7. Recommendation Adapter Checklist

- Adapter does not replace runtime recommendations.
- Selected advisory recommendation is not runtime recommendation.
- `runtime_recommendation_applied=false`.
- Deterministic recommendations remain authoritative.

## 8. Parser Adapter Checklist

- Adapter does not modify runtime parser.
- Selected parser action is consideration only.
- `runtime_parser_applied=false`.
- Current parser remains authoritative.

## 9. Fallback / Rollback Checklist

- Fallback/rollback is decision-only.
- No rollback execution exists.
- Deterministic fallback is default.
- `adaptive_consideration_ready` is not runtime active.

## 10. Runtime Isolation Checklist

- Do not bypass runtime isolation boundaries.
- Do not wire run_analysis.py until explicitly scoped.
- Parser/scoring/decision/recommendation modules must not import Phase 7AA adaptive runtime modules.
- No runtime mutation is allowed.

## 11. Documentation Checklist

- Validation matrix exists.
- Runtime integration readiness document exists.
- Release certification document exists.
- Operational checklist exists.
- README links the 7AA readiness and certification documents.

## 12. Failure Handling

If validation fails, stop certification, inspect the failing validation group, and keep deterministic runtime authoritative. Do not bypass runtime isolation boundaries. Use `.venv/bin/python` if system Python lacks project dependencies such as dotenv.

## 13. Acceptance Checklist

Run all certification commands:

```bash
python3 scripts/run_phase7aa_runtime_integration_validation.py
python3 scripts/run_phase7aa_runtime_integration_validation.py --json
python3 scripts/run_phase7aa_runtime_integration_readiness_check.py
python3 scripts/run_phase7aa_runtime_integration_readiness_check.py --json
python3 scripts/run_phase7_ml_validation.py
python3 scripts/run_phase7_materialization_validation.py
python3 scripts/run_phase7_validation.py
PYTHONPATH=. .venv/bin/python scripts/run_phase6_validation.py
```

Acceptance requires `runtime_integration_ready=true`, no rollback execution, no run_analysis.py integration, no runtime mutation, deterministic runtime remains authoritative, and Phase 8 is not implemented.
