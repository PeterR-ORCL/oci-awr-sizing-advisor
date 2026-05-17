# Phase 7 Active Screen 3 Execution Release Certification

## 1. Certification Purpose

This release certification records that Phase 7CA-7CF provides a governed, controlled, auditable Active Screen 3 backend execution foundation. It certifies the execution metadata boundary, not uncontrolled UI activation.

## 2. Certified Scope

Certified scope includes governed workflow persistence, deterministic re-analysis execution service metadata, active in-memory comparison execution, controlled Object Storage load execution, dashboard output refresh metadata handling, validation/readiness scripts, and operational documentation.

## 3. Certified Capabilities

Certified capabilities include DB-backed workflow metadata persistence, idempotency, transaction metadata, audit persistence, output artifact references, injected deterministic runner support, staged/raw comparison blocking, injected Object Storage client support, optional live Object Storage validation, injected dashboard renderer support, and metadata-only default refresh behavior.

## 4. Certified Non-Goals

Certified non-goals are no new execution behavior in 7CF, no run_analysis.py modification, no direct run_analysis.py invocation, no subprocess execution, no parser/scoring/decision/recommendation semantic mutation, no adaptive runtime by default, no Phase 4I mutation, no generated dashboard artifacts committed, no hard-coded Object Storage bucket or object names, no EM Extract, and Phase 8 is not implemented.

## 5. Certified DB Persistence

7CA certifies that governed workflow DB persistence exists. The persistence schema and repository record workflow transactions, requests, validations, audits, idempotency, output artifacts, failure metadata, and rollback references. DB-backed validation passes where available.

## 6. Certified Deterministic Execution

7CB certifies deterministic execution service works through an injected runner and governed repository metadata. No direct run_analysis.py invocation occurs, no subprocess execution occurs, no Object Storage call occurs, no adaptive runtime by default is enabled, no dashboard regeneration occurs, and no Phase 4I mutation occurs.

## 7. Certified Comparison Execution

7CC certifies comparison execution works for supplied structured in-memory payloads and blocks staged/raw/unstructured comparison inputs. It does not read files, call Object Storage, query DB report content, call parser modules, regenerate dashboards, mutate Phase 4I, or implement Phase 8 sizing/TCO comparison.

## 8. Certified Object Storage Load Execution

7CD certifies Object Storage load execution works with injected clients and metadata persistence. The service supports metadata-only, head object, get object in memory, and prefix listing modes. It does not write files, parse content, call run_analysis.py, regenerate dashboards, mutate Phase 4I, or persist credentials.

## 9. Certified Dashboard Output Refresh

7CE certifies dashboard output refresh metadata works. The default path is metadata-only. Dashboard generation happens only through an injected renderer. Idempotency prevents repeated renderer calls. No generated dashboard HTML is committed.

## 10. Certified Object Storage Path Convention

The Object Storage path convention is certified as configurable and flexible:

bucket = configurable

prefix = awr/raw/<DB_NAME>/<YYYY-MM-DD>/

object_name = <file>.out OR <source_system_id>/<fingerprint>/<file>.out

source_system_id is optional

fingerprint is optional

database_name and snapshot_date remain explicit metadata where available

source-selection and loader logic support flat and nested objects under the selected prefix.

No bucket, prefix, DB name, date, source_system_id, fingerprint, or object name is hard-coded.

## 11. Certified Runtime Boundaries

The certified block preserves deterministic runtime authority. Persistence is workflow metadata, not runtime truth mutation. Output artifact references are metadata, not generated dashboard files by default. Phase 4I references are preserved and not mutated. Adaptive runtime remains disabled by default.

## 12. Risks / Follow-Ups

Future work should enable Screen 3 UI actions only through the certified execution path, keep live Object Storage validation explicit and opt-in, and continue to keep generated dashboard artifacts out of commits. 7CF does not certify Phase 8, EM Extract, sizing/TCO, or uncontrolled runtime mutation.

## 13. Release Certification Statement

Phase 7CA-7CF is certified when `python3 scripts/run_phase7_active_screen3_execution_validation.py` and `python3 scripts/run_phase7_active_screen3_execution_readiness_check.py` pass with `active_screen3_execution_ready=true`. The certified result is that the active Screen 3 execution block is ready, no direct run_analysis.py invocation occurs, no subprocess execution occurs, no adaptive runtime by default is enabled, no Phase 4I mutation occurs, Object Storage path convention is documented, deterministic runtime remains authoritative, and Phase 8 is not implemented.
