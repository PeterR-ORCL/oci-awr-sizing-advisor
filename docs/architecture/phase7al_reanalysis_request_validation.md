# Phase 7AL Re-Analysis Request Validation

## 1. Purpose

Phase 7AL defines metadata-only validation for future Screen 3 backend re-analysis requests.

Validation is not execution.

## 2. Validation Flow

The validation flow checks request metadata in a deterministic order:

1. Requested action support
2. Selected state support
3. Execution mode support
4. Actor metadata presence
5. Source selection metadata presence
6. Source validation metadata presence
7. Backend execution validation metadata presence
8. Phase 4I contract requirement
9. Phase 7AL execution blocking

No backend action is executed.

## 3. Actor Validation

All supported requested actions require actor/audit metadata.

When actor audit context is missing, validation returns `NEEDS_ACTOR`. Browser state, URL state, source state, and selected state cannot substitute for actor identity.

## 4. Source Selection Validation

Requests require source selection metadata from Phase 7AK.

When source selection metadata is missing, validation returns `NEEDS_SOURCE_SELECTION`. When source validation metadata is absent, validation returns `NEEDS_SOURCE_VALIDATION`.

Source selection and source validation remain metadata only.

## 5. Backend Execution Mode Validation

Requests require supported execution mode metadata.

Supported execution modes are `static_read_only`, `local_command_generation`, `local_backend_execution`, and `future_api_server_execution`.

Unsupported execution mode metadata is rejected. Supported execution mode metadata still does not execute anything in Phase 7AL.

## 6. Execution Blocking in Phase 7AL

Execution remains blocked in Phase 7AL.

`can_execute=false in Phase 7AL` and `execution_blocked=true in Phase 7AL`.

No backend action is executed. No `run_analysis.py` call is made. No object storage call is made. No file read is made. No DB lookup is made.

## 7. Validation Statuses

Supported validation statuses are:

- `VALID_METADATA_ONLY`
- `INVALID`
- `NEEDS_ACTOR`
- `NEEDS_SOURCE_SELECTION`
- `NEEDS_SOURCE_VALIDATION`
- `NEEDS_BACKEND_EXECUTION_VALIDATION`
- `UNSUPPORTED_ACTION`
- `UNSUPPORTED_EXECUTION_MODE`
- `UNSUPPORTED_SOURCE_MODE`
- `EXECUTION_NOT_ALLOWED_IN_THIS_PHASE`

`EXECUTION_NOT_ALLOWED_IN_THIS_PHASE` is returned when metadata is otherwise valid but Phase 7AL still blocks execution.

## 8. Denied Reasons

Denied reasons explain why execution cannot proceed.

Every Phase 7AL validation result includes execution denial because request validation is not execution. Additional denied reasons may include missing actor context, missing source selection, missing source validation, or missing backend execution validation.

## 9. Required Next Steps

Required next steps identify what a future phase must supply.

Examples include providing actor audit context, providing source selection metadata, providing source validation metadata, providing backend execution validation metadata, and deferring actual execution to a future controller phase.

## 10. Runtime Safety Flags

Runtime safety flags must preserve:

- `runtime_execution_performed=false`
- `run_analysis_called=false`
- `object_storage_called=false`
- `local_file_read_performed=false`
- `db_lookup_performed=false`

Any validation record that sets these flags to true is invalid.

## 11. Phase 4I Boundary

Phase 4I contract preservation is required.

`phase4i_contract_required=true` must be preserved. Validation cannot authorize Phase 4I mutation, parser behavior changes, scoring changes, decision changes, recommendation changes, dashboard payload changes, or generated dashboard replacement.

## 12. Non-Goals

Phase 7AL validation does not execute analysis, call `run_analysis.py`, call object storage, read local files, query databases, generate dashboards, mutate Phase 4I, modify runtime behavior, add dashboard UI, add CLI commands, implement a backend execution controller, implement comparison, implement missing metric handling, or implement Phase 8 sizing/TCO.

Invalid requests fail safely.

## 13. Acceptance Criteria

Phase 7AL request validation is accepted when:

- Validation is not execution.
- No backend action is executed.
- No `run_analysis.py` call is made.
- No object storage call is made.
- No file read is made.
- No DB lookup is made.
- Invalid requests fail safely.
- `can_execute=false in Phase 7AL`.
- `execution_blocked=true in Phase 7AL`.
- Runtime safety flags remain false.
- Phase 4I contract preservation is required.
- No dashboard behavior is changed.
- No CLI behavior is changed.
- Phase 8 sizing/TCO is not implemented.
