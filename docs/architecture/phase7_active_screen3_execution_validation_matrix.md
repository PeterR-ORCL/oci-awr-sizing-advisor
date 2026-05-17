# Phase 7 Active Screen 3 Execution Validation Matrix

## 1. Purpose

This matrix certifies the Phase 7CA-7CF Active Screen 3 Backend Execution / Submit Workflow block. It validates that active execution metadata, persistence, idempotency, audit, output artifacts, Object Storage loading, comparison execution, deterministic execution, and dashboard refresh handling are ready as governed Screen 3 backend capabilities.

## 2. Scope

The scope covers Phase 7CA, 7CB, 7CC, 7CD, 7CE, and 7CF validation only. It verifies metadata persistence, injected execution boundaries, runtime isolation, Object Storage source conventions, and final readiness for the certified active Screen 3 execution path.

## 3. Non-Goals

This validation does not implement new execution behavior, does not modify run_analysis.py, does not add subprocess execution, does not mutate parser/scoring/decision/recommendation semantics, does not mutate Phase 4I, does not enable adaptive runtime by default, does not commit generated dashboard artifacts, does not hard-code Object Storage names, and confirms Phase 8 is not implemented.

## 4. Validation Categories

Validation categories are `governed_workflow_repository`, `deterministic_execution`, `comparison_execution`, `object_storage_load_execution`, `dashboard_output_refresh`, `screen3_reanalysis_validation`, `import_isolation`, `runtime_safety`, `object_storage_path_convention`, and `documentation`.

## 5. 7CA Persistence Validation

7CA is validated by schema and repository tests. The required criteria are that governed workflow DB persistence exists, idempotency works, audit persistence works, transaction metadata works, output artifact persistence works, failure metadata is recorded, and DB-backed validation passes where available.

## 6. 7CB Deterministic Execution Validation

7CB is validated by deterministic execution tests. The required criteria are that deterministic execution service works, actor/audit/idempotency/transaction metadata are required, injected runner behavior works, no direct run_analysis.py invocation occurs, no subprocess execution occurs, no adaptive runtime is used by default, no Object Storage call occurs, no dashboard regeneration occurs, and no Phase 4I mutation occurs.

## 7. 7CC Comparison Execution Validation

7CC is validated by comparison execution tests. The required criteria are that comparison execution works on structured in-memory payloads, staged/raw/unstructured inputs are blocked, missing structured payloads are denied, no file read occurs, no Object Storage call occurs, no DB report lookup occurs, no parser call occurs, no dashboard regeneration occurs, no Phase 4I mutation occurs, and Phase 8 sizing/TCO comparison remains excluded.

## 8. 7CD Object Storage Load Validation

7CD is validated by Object Storage load execution tests. The required criteria are that Object Storage load execution works with injected clients, metadata-only mode makes no client call, fake client head/get/list modes work, idempotency prevents repeated client calls, DB metadata persistence works where available, live Object Storage validation is optional, no file write occurs, no parser invocation occurs, no run_analysis.py call occurs, no dashboard regeneration occurs, no Phase 4I mutation occurs, and no credentials are persisted.

## 9. 7CE Dashboard Output Refresh Validation

7CE is validated by dashboard output refresh tests. The required criteria are that dashboard output refresh metadata works, injected renderer behavior works, metadata-only default is safe, idempotency prevents repeated renderer calls, output artifact references persist, no run_analysis.py call occurs, no parser/scoring/recommendation invocation occurs, no Object Storage call occurs, no Phase 4I mutation occurs, no dashboard regeneration occurs by default, and no generated dashboard artifacts are committed.

## 10. Object Storage Path Convention Validation

The certified Object Storage path convention is documented, configurable, and not hard-coded. The required pattern is:

bucket = configurable

prefix = awr/raw/<DB_NAME>/<YYYY-MM-DD>/

object_name = <file>.out OR <source_system_id>/<fingerprint>/<file>.out

source_system_id is optional

fingerprint is optional

database_name and snapshot_date remain explicit metadata where available

source-selection and loader logic support flat and nested objects under the selected prefix.

## 11. Import Isolation Validation

Import isolation validation checks the 7CA-7CE execution modules for unsafe imports. The certified path does not import run_analysis.py, subprocess, parser modules, scoring modules, decision modules, recommendation modules, Object Storage SDK modules, dashboard rendering modules, DB helpers at import time, or CLI behavior modules in the active execution modules.

## 12. Runtime Safety Validation

Runtime safety validation asserts no direct run_analysis.py invocation, no subprocess execution, no parser/scoring/recommendation semantic mutation, no adaptive runtime by default, no Phase 4I mutation, no dashboard regeneration by default, no generated dashboard artifacts committed, and deterministic runtime remains authoritative.

## 13. Phase 4I Boundary Validation

Phase 4I is referenced only through metadata. Phase 4I references are not rewritten, regenerated, or mutated by 7CA-7CF. Persisted Phase 4I payload references are not runtime truth mutation.

## 14. Phase 8 Exclusion

Phase 8 is not implemented. EM Extract, sizing/TCO, target platform comparison, and what-if advisory remain outside this block.

## 15. Acceptance Criteria

Phase 7CA-7CF is accepted when `python3 scripts/run_phase7_active_screen3_execution_validation.py` passes, `active_screen3_execution_ready=true`, all required validation groups pass, DB-backed validation passes where available, live Object Storage remains opt-in, no direct run_analysis.py invocation occurs, no subprocess execution occurs, no adaptive runtime by default is enabled, no Phase 4I mutation occurs, no generated dashboard artifacts are committed, Object Storage path convention is documented, deterministic runtime remains authoritative, and Phase 8 is not implemented.
