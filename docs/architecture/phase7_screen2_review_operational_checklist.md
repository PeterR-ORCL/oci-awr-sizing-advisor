# Phase 7 Screen 2 Review Operational Checklist

## 1. Purpose

This checklist supports local operation of the Phase 7AP-7AT Screen 2 Diagnostic Review / Approval Workflow validation and readiness layer.

It is used to confirm that the review workflow remains governed, preview-only, and non-mutating.

## 2. Pre-Run Checklist

- Confirm the branch is `phase7-screen2-diagnostic-review-workflow`.
- Confirm the working tree contains only expected Phase 7AP-7AT validation/certification changes.
- Confirm no generated dashboard files are changed.
- Confirm no parser, scoring, decision, recommendation, schema, CLI, or `run_analysis.py` changes are present.

## 3. Validation Checklist

Run:

```bash
python3 scripts/run_phase7_screen2_review_validation.py
python3 scripts/run_phase7_screen2_review_validation.py --json
```

The validation should report `screen2_review_ready=true`, review panel preview-only, no review records persisted, no governance action executed, no candidate created, no diagnostic truth changed, and no Phase 4I mutation.

## 4. Review Boundary Checklist

- 7AP boundary docs exist.
- Review is not mutation.
- Future actor identity, audit trail, and governed write path are required.
- Deterministic diagnostic truth remains authoritative.

## 5. Review Model Checklist

Run:

```bash
python3 -m unittest tests/test_phase7aq_diagnostic_review_model.py
```

Confirm local diagnostic review records, evidence review records, diagnostic approval decisions, and diagnostic review requests validate without persistence.

## 6. Governance Bridge Checklist

- Confirm route previews exist.
- Confirm candidate request intents are intents only.
- Confirm no governance action executes.
- Confirm no candidate is created automatically.

## 7. Review Panel Checklist

Run:

```bash
python3 -m unittest tests/test_dashboard_screen2_review_panel.py
```

Confirm the Screen 2 review panel exists, all controls are disabled/preview-only, no backend calls are present, and no deterministic diagnostic truth mutation occurs.

## 8. Runtime Isolation Checklist

- Confirm `scripts/run_analysis.py` does not import Screen 2 review workflow modules.
- Confirm parser/scoring/decision/recommendation paths do not import Screen 2 review workflow modules.
- Confirm no active mutation functions exist for persistence, governance execution, candidate creation, diagnostic truth mutation, parser output updates, recommendation updates, or Phase 4I mutation.

## 9. Documentation Checklist

- Confirm the validation matrix exists.
- Confirm readiness documentation exists.
- Confirm release certification exists.
- Confirm this operational checklist exists.
- Confirm the architecture README links all 7AT documents.

## 10. Failure Handling

If validation fails, do not certify the block.

Inspect the failing validation group, fix only the scoped issue, rerun validation, and preserve the boundaries: no review execution, no governed write path execution, no candidate creation, no diagnostic truth mutation, and no Phase 8 implementation.

## 11. Acceptance Checklist

Run:

```bash
python3 scripts/run_phase7_screen2_review_readiness_check.py
python3 scripts/run_phase7_screen2_review_readiness_check.py --json
```

Accept the block only when `screen2_review_ready=true`, review workflow is not runtime mutation, review panel is preview-only, no review records are persisted, no candidate is created automatically, no diagnostic truth changes, no severity/confidence/score changes, no parser output changes, no recommendation truth changes, no Phase 4I mutation occurs, deterministic runtime remains authoritative, and Phase 8 sizing/TCO is not implemented.
