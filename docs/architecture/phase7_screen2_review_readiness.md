# Phase 7 Screen 2 Review Readiness

## 1. Purpose

This document defines readiness for the Phase 7AP-7AT Screen 2 Diagnostic Review / Approval Workflow block.

Readiness means the completed 7AP-7AS work is validated, isolated, documented, and certified as governed/preview-only at the UI layer.

## 2. Readiness Scope

The readiness scope covers the Screen 2 review boundary, diagnostic review object model, evidence availability review model, governance bridge route previews, disabled review panel UI, import isolation, runtime safety, documentation completeness, and optional broader Phase 7 / Phase 6 regression.

## 3. Completed Subphases

Completed subphases are 7AP Screen 2 Review Workflow Boundary, 7AQ Diagnostic Review Object Model, 7AQ.1 Evidence Availability / Missing Metric Review Model, 7AR Screen 2 Workflow Bridge to Governance, and 7AS Screen 2 Approval UI / Review Panel.

## 4. Readiness Categories

Readiness categories are review boundary, diagnostic review model, governance bridge, review panel, diagnostic exploration regression, runtime isolation, documentation complete, optional Phase 7 regression, and optional Phase 6 regression.

## 5. Boundary Readiness

Boundary readiness is true when 7AP proves Screen 2 deterministic diagnosis remains authoritative and review is not mutation.

Future review writes require actor identity, audit trail, and governed write path.

## 6. Object Model Readiness

Object model readiness is true when 7AQ local diagnostic review records, evidence review records, approval decisions, and review requests validate and serialize safely.

Review records remain local object models only in this block.

## 7. Evidence Availability Readiness

Evidence availability readiness is true when 7AQ.1 classifies missing, unavailable, unsupported, parser gap, source gap, unreliable, not applicable, and unknown evidence without changing diagnosis or scoring.

## 8. Governance Bridge Readiness

Governance bridge readiness is true when 7AR creates route previews and candidate request intents only.

Candidate intents are not candidates, and no candidate is created automatically.

## 9. Review Panel Readiness

Review panel readiness is true when 7AS displays disabled/preview-only Screen 2 review controls and request preview safety flags.

Screen 2 review is governed and preview-only at the UI layer.

## 10. Runtime Isolation Readiness

Runtime isolation readiness is true when `scripts/run_analysis.py` and parser/scoring/decision/recommendation paths do not import Screen 2 review workflow modules.

No deterministic diagnostic truth mutation occurs.

## 11. Documentation Readiness

Documentation readiness is true when 7AP-7AT docs exist, the architecture README links the 7AT docs, and the documentation states the review workflow is governed, preview-only, non-mutating, and not Phase 8 sizing/TCO.

## 12. Required Commands

Required commands are:

```bash
python3 scripts/run_phase7_screen2_review_validation.py
python3 scripts/run_phase7_screen2_review_validation.py --json
python3 scripts/run_phase7_screen2_review_readiness_check.py
python3 scripts/run_phase7_screen2_review_readiness_check.py --json
python3 -m unittest tests/test_dashboard_screen2_review_panel.py
python3 -m unittest tests/test_phase7aq_diagnostic_review_model.py
```

## 13. Readiness Criteria

screen2_review_ready=true only when checks pass.

The readiness check must show no review records persisted, no governance action executed, no candidate created, no diagnostic truth changed, no Phase 4I mutation, deterministic runtime remains authoritative, and Phase 8 sizing/TCO is not implemented.

## 14. Screen 2 Review Ready Statement

The Screen 2 diagnostic review workflow is ready when `screen2_review_ready=true`, the review panel remains disabled/preview-only, object models and governance bridge route previews validate locally, runtime imports remain isolated, and no deterministic diagnostic truth mutation occurs.
