# Phase 7 Screen 4 Workflow Operational Checklist

## 1. Purpose

This checklist defines the local operational validation steps for Phase 7AZ-7BD Screen 4 Historical Review Workflow.

## 2. Pre-Run Checklist

- Confirm the branch is `phase7-screen4-historical-review-workflow`.
- Confirm the working tree is clean before starting certification changes.
- Confirm no Phase 8 sizing/TCO work is being introduced.
- Confirm no runtime behavior modules are being modified.

## 3. Validation Checklist

- Run `python3 scripts/run_phase7_screen4_workflow_validation.py`.
- Run `python3 scripts/run_phase7_screen4_workflow_validation.py --json`.
- Confirm text output reports validation passed.
- Confirm JSON output reports `screen4_workflow_ready=true`.

## 4. Baseline Selection Checklist

- Confirm baseline selection is metadata only.
- Confirm no baseline is made official.
- Confirm no baseline records are persisted.
- Confirm baseline validation tests pass.

## 5. Trend / Anomaly Review Checklist

- Confirm trend/anomaly review is local model only.
- Confirm no trend review records are persisted.
- Confirm no anomaly review records are persisted.
- Confirm no historical/trend/anomaly truth changes occur.

## 6. Historical Learning Bridge Checklist

- Run `python3 -m unittest tests/test_phase7bc_historical_learning_bridge.py`.
- Confirm candidate intents are not candidates.
- Confirm learning signal intents are not dataset labels.
- Confirm no candidate is created automatically.

## 7. Historical Review Panel Checklist

- Confirm the Screen 4 historical review panel remains preview-only.
- Confirm the panel has no active submit behavior.
- Confirm the panel has no form POST, fetch/XMLHttpRequest, API calls, or backend calls.

## 8. Historical Execution Metadata Checklist

- Run `python3 -m unittest tests/test_phase7bc3_historical_review_execution.py`.
- Confirm governed execution is metadata-only.
- Confirm actor metadata, governed write-path metadata, audit metadata, and output artifact metadata are validated.
- Confirm no execution records are persisted.

## 9. Runtime Isolation Checklist

- Confirm `scripts/run_analysis.py` does not import Screen 4 workflow modules.
- Confirm parser/scoring/decision/recommendation paths do not import Screen 4 workflow modules.
- Confirm no scoring truth changes, recommendation truth changes, parser output changes, or Phase 4I mutation occurs.

## 10. Documentation Checklist

- Confirm validation matrix, readiness doc, release certification, and operational checklist exist.
- Confirm README links all Screen 4 workflow certification docs.
- Confirm docs state `screen4_workflow_ready=true only when checks pass`.

## 11. Failure Handling

If validation fails, inspect the failing group, fix only the validation/documentation issue in scope, and rerun the focused command.

Do not modify dashboard behavior, parser behavior, scoring behavior, decision behavior, recommendation behavior, or Phase 4I to satisfy certification.

## 12. Acceptance Checklist

- Run `python3 scripts/run_phase7_screen4_workflow_readiness_check.py`.
- Run `python3 scripts/run_phase7_screen4_workflow_readiness_check.py --json`.
- Confirm `screen4_workflow_ready=true`.
- Confirm no persistence occurs.
- Confirm no historical/trend/anomaly/scoring truth changes occur.
- Confirm no Phase 4I mutation occurs.
- Confirm deterministic runtime remains authoritative.
- Confirm Phase 8 sizing/TCO is not implemented.
