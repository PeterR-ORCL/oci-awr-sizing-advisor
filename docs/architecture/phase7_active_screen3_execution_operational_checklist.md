# Phase 7 Active Screen 3 Execution Operational Checklist

## 1. Purpose

This checklist provides the operational commands and acceptance checks for Phase 7CA-7CF Active Screen 3 Backend Execution / Submit Workflow certification.

## 2. Pre-Run Checklist

- Confirm the branch is `phase7-active-screen3-backend-execution`.
- Confirm the working tree is clean before starting certification work.
- Confirm no `.env`, wallet files, credentials, private keys, Object Storage secrets, or generated dashboard artifacts are staged.
- Confirm generated dashboard artifacts should not be committed.
- Confirm Phase 8 is not implemented.

## 3. DB Validation Checklist

Run DB-backed validation where ADB is available:

```bash
AWR_PHASE7CA_DB_TEST=1 .venv/bin/python -m unittest tests/test_phase7ca_governed_workflow_repository.py
AWR_PHASE7CB_DB_TEST=1 .venv/bin/python -m unittest tests/test_phase7cb_deterministic_execution.py
AWR_PHASE7CC_DB_TEST=1 .venv/bin/python -m unittest tests/test_phase7cc_comparison_execution.py
AWR_PHASE7CD_DB_TEST=1 .venv/bin/python -m unittest tests/test_phase7cd_object_storage_load_execution.py
AWR_PHASE7CE_DB_TEST=1 .venv/bin/python -m unittest tests/test_phase7ce_dashboard_output_refresh.py
```

If DB connectivity is unavailable, skip honestly and do not claim DB validation passed.

## 4. Deterministic Execution Checklist

- Confirm deterministic execution service works.
- Confirm actor, audit, idempotency, transaction, and rollback metadata are required.
- Confirm injected runner path works.
- Confirm no direct run_analysis.py invocation.
- Confirm no subprocess execution.
- Confirm no adaptive runtime by default.
- Confirm no Phase 4I mutation.

## 5. Comparison Execution Checklist

- Confirm comparison execution works with already-loaded structured in-memory payloads.
- Confirm staged/raw/unstructured comparison inputs are blocked.
- Confirm missing structured payloads are denied.
- Confirm no file read, no Object Storage call, no DB report lookup, no parser call, no dashboard regeneration, no Phase 4I mutation, and no Phase 8 sizing/TCO comparison.

## 6. Object Storage Load Checklist

- Confirm Object Storage load execution works through an injected client.
- Confirm metadata-only mode performs no client call.
- Confirm fake client head/get/list modes work.
- Confirm idempotency prevents repeated client calls.
- Confirm no file write, no parser invocation, no run_analysis.py call, no dashboard regeneration, no Phase 4I mutation, and no credentials persisted.
- Confirm the path convention is documented:

bucket = configurable

prefix = awr/raw/<DB_NAME>/<YYYY-MM-DD>/

object_name = <file>.out OR <source_system_id>/<fingerprint>/<file>.out

source_system_id is optional

fingerprint is optional

database_name and snapshot_date remain explicit metadata where available

source-selection and loader logic support flat and nested objects under the selected prefix.

## 7. Dashboard Output Refresh Checklist

- Confirm dashboard output refresh metadata works.
- Confirm metadata-only default path works.
- Confirm injected renderer behavior works.
- Confirm idempotency prevents repeated renderer calls.
- Confirm no Object Storage call, no run_analysis.py call, no parser/scoring/recommendation invocation, no Phase 4I mutation, no default dashboard regeneration, and no generated dashboard artifacts committed.

## 8. Live Object Storage Optional Checklist

Live Object Storage validation is optional and requires explicit env/config. Run only when configured:

```bash
AWR_PHASE7CD_OBJECT_STORAGE_TEST=1 .venv/bin/python -m unittest tests/test_phase7cd_object_storage_load_execution.py
```

Do not hard-code bucket, prefix, DB name, date, source_system_id, fingerprint, or object name. Do not print secrets.

## 9. Failure Handling

- If local tests fail, fix the failing 7CA-7CE behavior or certification check before proceeding.
- If DB validation fails due connectivity, report it as blocked or skipped honestly.
- If live Object Storage validation is not configured, report it as optional skipped.
- If any safety flag indicates run_analysis.py, subprocess, parser/scoring/recommendation mutation, Object Storage calls outside 7CD, dashboard regeneration by default, or Phase 4I mutation, block certification.

## 10. Acceptance Checklist

Run:

```bash
python3 scripts/run_phase7_active_screen3_execution_validation.py
python3 scripts/run_phase7_active_screen3_execution_validation.py --json
python3 scripts/run_phase7_active_screen3_execution_readiness_check.py
python3 scripts/run_phase7_active_screen3_execution_readiness_check.py --json
python3 -m unittest tests/test_phase7_active_screen3_execution_validation.py
python3 -m unittest tests/test_phase7_active_screen3_execution_readiness_check.py
```

Certification is accepted when those commands pass, `active_screen3_execution_ready=true`, DB-backed validation passes where available, live Object Storage validation is optional, no direct run_analysis.py invocation occurs, no subprocess execution occurs, no adaptive runtime by default is enabled, no Phase 4I mutation occurs, no generated dashboard artifacts are committed, Object Storage path convention is documented, deterministic runtime remains authoritative, and Phase 8 is not implemented.
