# Phase 7AL Backend Re-Analysis Request Model

## 1. Purpose

Phase 7AL defines the local deterministic backend re-analysis request model for future Screen 3 submit/actions.

The model captures what the user selected, which source mode is selected, which execution mode is requested, which action is requested, who requested it, whether validation metadata is present, and what remains blocked.

The request model is not execution.

## 2. Scope

The scope is metadata records, deterministic identifiers, validation metadata, and serialization helpers for future Screen 3 backend re-analysis requests.

Phase 7AL covers:

- `Screen3SelectedState`
- `BackendReAnalysisRequest`
- `BackendReAnalysisRequestValidation`
- supported requested actions
- supported execution modes
- supported source modes
- actor linkage
- source selection linkage
- backend execution validation linkage
- Phase 4I contract requirement
- deterministic ID rules
- serialization rules

## 3. Non-Goals

Phase 7AL does not execute analysis. No backend action is executed.

Phase 7AL does not call `run_analysis.py`. `run_analysis.py is not called`.

Phase 7AL does not call object storage. Object storage is not called.

Phase 7AL does not read local files. Local files are not read.

Phase 7AL does not query databases. DB lookup is not performed.

Phase 7AL does not generate dashboard output, mutate Phase 4I, modify runtime behavior, change parser output, change scoring behavior, change decision behavior, change recommendation behavior, add dashboard buttons/forms, add CLI commands, implement a backend execution controller, implement AWR/report comparison, implement missing metric handling, or implement Phase 8 sizing/TCO.

## 4. Backend Re-Analysis Request Is Not Execution

The request model is not execution.

A backend re-analysis request describes intent only. It is not a command runner, backend controller, object storage loader, local file reader, database lookup, dashboard generator, or Phase 4I mutation path.

In Phase 7AL, `can_execute=false in Phase 7AL` and `execution_blocked=true in Phase 7AL`.

## 5. Screen3SelectedState Object Shape

`Screen3SelectedState` captures selected Screen 3 metadata:

- `selected_state_id`
- `selected_awr`
- `selected_run`
- `selected_database`
- `selected_system`
- `selected_snapshot`
- `selected_comparison_baseline`
- `selected_issue_domain`
- `selected_severity_status`
- `selected_source_mode`
- `selected_execution_mode`
- `selected_object_storage_reference`
- `selected_local_source_reference`
- `selected_existing_run_reference`
- `selected_future_em_extract_reference`
- `notes`

Selected values are metadata only. Supported issue domains are CPU, IO, MEMORY, COMMIT, RAC, and ADG, allowing normalized equivalents.

## 6. BackendReAnalysisRequest Object Shape

`BackendReAnalysisRequest` captures future request metadata:

- `request_id`
- `requested_action`
- `selected_state`
- `source_selection`
- `backend_execution_request`
- `actor_audit_context`
- `execution_mode`
- `adaptive_runtime_requested`
- `deterministic_default`
- `requires_validation`
- `requires_actor`
- `requires_source_validation`
- `requires_backend_execution_validation`
- `phase4i_contract_required`
- `created_at`
- `notes`

Defaults preserve `deterministic_default=true`, `requires_validation=true`, `requires_actor=true`, `requires_source_validation=true`, `requires_backend_execution_validation=true`, and `phase4i_contract_required=true`.

## 7. BackendReAnalysisRequestValidation Object Shape

`BackendReAnalysisRequestValidation` captures validation metadata:

- `validation_id`
- `request_id`
- `valid`
- `validation_status`
- `requested_action`
- `source_mode`
- `execution_mode`
- `actor_present`
- `source_validation_present`
- `backend_execution_validation_present`
- `can_execute`
- `execution_blocked`
- `denied_reasons`
- `warnings`
- `required_next_steps`
- `phase4i_contract_required`
- `deterministic_default`
- `adaptive_runtime_requested`
- `runtime_execution_performed`
- `run_analysis_called`
- `object_storage_called`
- `local_file_read_performed`
- `db_lookup_performed`
- `created_at`
- `notes`

Runtime safety flags remain false. `can_execute=false in Phase 7AL` and `execution_blocked=true in Phase 7AL`.

## 8. Supported Requested Actions

Supported requested actions are:

- `analyze_selection`
- `rerun_analysis`
- `build_comparison`
- `load_from_object_storage`

Actions are metadata only. No action executes in Phase 7AL.

## 9. Supported Execution Modes

Supported execution modes are:

- `static_read_only`
- `local_command_generation`
- `local_backend_execution`
- `future_api_server_execution`

All modes are metadata only in Phase 7AL. No mode executes analysis.

## 10. Supported Source Modes

Supported source modes are:

- `none`
- `local_staged`
- `local_file`
- `existing_run`
- `object_storage`
- `future_upload`
- `future_em_extract`

Object storage requires source metadata and future source validation. Future EM extract remains placeholder only. No source executes in Phase 7AL.

## 11. Actor Requirement

All future requested actions require actor/audit metadata.

Evaluation returns `NEEDS_ACTOR` when actor audit context is missing. Actor metadata is required before any future execution path can proceed.

## 12. Source Validation Requirement

Requests require source selection metadata and source validation metadata.

Evaluation returns `NEEDS_SOURCE_SELECTION` when source selection metadata is absent and `NEEDS_SOURCE_VALIDATION` when source validation metadata is absent.

Phase 7AL does not read local files, call object storage, query databases, or validate real source availability.

## 13. Backend Execution Validation Requirement

Requests require backend execution validation metadata before future execution can be considered.

Evaluation returns `NEEDS_BACKEND_EXECUTION_VALIDATION` when backend execution validation metadata is missing.

Phase 7AL does not implement the backend execution controller.

## 14. Phase 4I Contract Requirement

Every request requires Phase 4I contract preservation.

`phase4i_contract_required=true` must be preserved. A request cannot silently mutate Phase 4I, parser output, scoring output, decision output, recommendation output, dashboard payload shape, or generated dashboard artifacts.

## 15. Deterministic ID Rules

IDs are deterministic. They do not use random UUIDs, timestamps, database sequences, or external services.

Identifier shapes include:

- `SCREEN3-SELECTED-STATE-<RUN_OR_AWR>-<SNAPSHOT>`
- `SCREEN3-REANALYSIS-REQUEST-<ACTION>-<STATE>-<MODE>`
- `SCREEN3-REANALYSIS-VALIDATION-<REQUEST_ID>`

The same input creates the same ID.

## 16. Serialization Rules

Selected state records, re-analysis request records, and validation records serialize to plain dictionaries and deserialize back to equivalent deterministic dataclass records.

Serialization does not execute requests, call `run_analysis.py`, call object storage, read files, query databases, or mutate runtime state.

## 17. Relationship to 7AJ

Phase 7AJ defined the Screen 3 backend re-analysis boundary and established that selection is not execution.

Phase 7AL creates request metadata that follows that boundary. The request model is not execution.

## 18. Relationship to 7AK

Phase 7AK defined source selection and source validation metadata.

Phase 7AL links to source selection metadata. It does not add source loading, object storage access, file reading, database lookup, or source execution.

## 19. Relationship to Future 7AM

Future 7AM may implement the backend re-analysis execution controller.

Phase 7AL does not execute analysis, dispatch backend work, call `run_analysis.py`, generate output, refresh dashboards, or create run records.

## 20. Relationship to Future 7AM.1

AWR/report comparison is future 7AM.1.

Phase 7AL may represent `build_comparison` as requested action metadata, but it does not compare AWR reports, compare runs, compute score changes, compare waits, compare SQL concentration, compare trends/anomalies, or create comparison artifacts.

## 21. Relationship to Future 7AO.1 / 7AQ.1

Missing metric handling is future 7AO.1 / 7AQ.1.

Phase 7AL does not inspect source contents, detect missing metrics, adjust confidence, model evidence availability, or create parser/source review candidates.

## 22. Relationship to Phase 8

Phase 8 sizing/TCO is not implemented.

Phase 7AL does not implement sizing, TCO, what-if advisory, EM Extract adapter behavior, cost modeling, or capacity planning.

## 23. Acceptance Criteria

Phase 7AL is accepted when selected state metadata, backend re-analysis request metadata, request validation metadata, deterministic IDs, serialization helpers, documentation, tests, and README links exist.

Acceptance requires:

- The request model is not execution.
- `can_execute=false in Phase 7AL`.
- `execution_blocked=true in Phase 7AL`.
- `run_analysis.py is not called`.
- Object storage is not called.
- Local files are not read.
- DB lookup is not performed.
- AWR/report comparison is future 7AM.1.
- Missing metric handling is future 7AO.1 / 7AQ.1.
- No dashboard behavior is changed.
- No CLI behavior is changed.
- Deterministic runtime remains authoritative.
- Phase 8 sizing/TCO is not implemented.
