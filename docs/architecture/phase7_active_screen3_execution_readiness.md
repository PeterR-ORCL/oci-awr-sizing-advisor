# Phase 7 Active Screen 3 Execution Readiness

## 1. Purpose

This document defines readiness for the Phase 7CA-7CF Active Screen 3 Backend Execution / Submit Workflow block. It consolidates the readiness criteria for persistence, deterministic execution, comparison execution, Object Storage load execution, dashboard output refresh, runtime safety, and certification.

## 2. Readiness Scope

Readiness covers 7CA through 7CE capabilities and 7CF validation/readiness only. It does not add new execution behavior and does not enable Screen 3 UI buttons outside the certified execution path.

## 3. Completed Subphases

Completed subphases are 7CA Active Backend Execution Boundary + Persistence Prerequisites, 7CB Deterministic Re-Analysis Execution, 7CC Active AWR / Report Comparison Execution, 7CD Object Storage Load Execution, 7CE Dashboard Output Refresh / Regenerated Artifact Handling, and 7CF Active Screen 3 Execution Validation / Certification.

## 4. Readiness Categories

Readiness categories are governed workflow repository, deterministic execution, comparison execution, Object Storage load execution, dashboard output refresh, Screen 3 re-analysis validation, runtime isolation, documentation completeness, optional Phase 7 regression, optional Phase 6 regression, and optional live Object Storage validation.

## 5. DB Persistence Readiness

governed workflow db persistence exists. The 7CA repository/schema tests validate transactions, requests, validations, audits, output artifacts, idempotency, failure metadata, and DB-backed persistence where ADB is available.

## 6. Deterministic Execution Readiness

deterministic execution service works. The 7CB service validates governed request envelopes, actor/audit metadata, idempotency, injected runner behavior, safe no-runner behavior, output artifact references, and repository integration without direct run_analysis.py invocation or subprocess execution.

## 7. Comparison Execution Readiness

comparison execution works. The 7CC service compares structured in-memory payloads only, blocks staged/raw/unstructured inputs, records comparison artifact metadata, and preserves all no file read, no Object Storage call, no DB lookup, no dashboard regeneration, and no Phase 4I mutation safety flags.

## 8. Object Storage Load Readiness

object storage load execution works. The 7CD service supports injected clients, metadata-only/head/get/list modes, fake-client tests, idempotent replay, source validation artifact metadata, Object Storage load artifact metadata, and DB persistence where available. It does not parse loaded objects, write files, call run_analysis.py, regenerate dashboards, or mutate Phase 4I.

## 9. Dashboard Output Refresh Readiness

dashboard output refresh metadata works. The 7CE service supports metadata-only refresh, linked dashboard references, injected renderer metadata handling, validation responses, error artifacts, output artifact persistence, idempotent replay, and safe renderer validation. No dashboard regeneration occurs by default.

## 10. Live Object Storage Optional Readiness

Live Object Storage validation is optional and requires explicit configuration and opt-in flags. Normal readiness does not require live Object Storage. The certified Object Storage path convention is:

bucket = configurable

prefix = awr/raw/<DB_NAME>/<YYYY-MM-DD>/

object_name = <file>.out OR <source_system_id>/<fingerprint>/<file>.out

source_system_id is optional

fingerprint is optional

database_name and snapshot_date remain explicit metadata where available

source-selection and loader logic support flat and nested objects under the selected prefix.

## 11. Required Commands

Required readiness commands are:

```bash
python3 scripts/run_phase7_active_screen3_execution_validation.py
python3 scripts/run_phase7_active_screen3_execution_validation.py --json
python3 scripts/run_phase7_active_screen3_execution_readiness_check.py
python3 scripts/run_phase7_active_screen3_execution_readiness_check.py --json
python3 -m unittest tests/test_phase7ca_governed_workflow_schema.py
python3 -m unittest tests/test_phase7ca_governed_workflow_repository.py
python3 -m unittest tests/test_phase7cb_deterministic_execution.py
python3 -m unittest tests/test_phase7cc_comparison_execution.py
python3 -m unittest tests/test_phase7cd_object_storage_load_execution.py
python3 -m unittest tests/test_phase7ce_dashboard_output_refresh.py
```

## 12. Readiness Criteria

Readiness requires all 7CA-7CE focused suites to pass, validation/readiness scripts to pass, DB-backed validation to pass where available, live Object Storage validation to remain opt-in, no direct run_analysis.py invocation, no subprocess execution, no adaptive runtime by default, no Phase 4I mutation, no generated dashboard artifacts committed, deterministic runtime remains authoritative, and Phase 8 is not implemented.

## 13. Active Screen 3 Execution Ready Statement

active_screen3_execution_ready=true when the validation and readiness scripts pass. Screen 3 buttons are eligible to be enabled only through the certified execution path and only after the future UI enablement/certification step accepts that path.
