# Phase 7AM Backend Re-Analysis Execution Controller

## 1. Purpose

Phase 7AM defines the local deterministic execution-controller model for future Screen 3 backend re-analysis.

The controller produces execution plan metadata, blocked execution results, command-preview metadata, and in-memory comparison results. The controller does not execute analysis.

## 2. Scope

The scope is local controller metadata only:

- `ReAnalysisExecutionPlan`
- `ReAnalysisExecutionResult`
- execution status values
- deterministic execution plan/result identifiers
- command-preview metadata
- blocked execution result metadata
- in-memory comparison result linkage
- serialization and deserialization helpers

Phase 7AM also includes Phase 7AM.1 AWR / Report Comparison Engine for supplied in-memory report/run summary payloads only.

## 3. Non-Goals

The controller does not execute analysis.

The controller does not call `run_analysis.py`.

The controller does not call run_analysis.py.

The controller does not read files.

The controller does not call object storage.

The controller does not query DB.

The controller does not regenerate dashboards.

The controller does not mutate Phase 4I.

Phase 7AM does not call subprocesses, parser modules, scoring modules, decision modules, recommendation modules, OCI SDK, network services, DB dependencies, dashboard modules, or CLI modules. It does not write output artifacts, change runtime scoring, change recommendations, change parser output, add Screen 3 UI, add CLI commands, implement missing metric handling, or implement Phase 8 sizing/TCO.

## 4. Execution Controller Is Not Runtime Execution

Execution controller metadata is not runtime execution.

An execution plan describes what a future phase would need to validate and run. An execution result records the controller decision. Neither record executes backend analysis, reads sources, calls services, writes artifacts, refreshes dashboards, or changes runtime truth.

Actual execution is future work.

## 5. ReAnalysisExecutionPlan

`ReAnalysisExecutionPlan` describes future execution intent:

- `execution_plan_id`
- `request_id`
- `requested_action`
- `execution_mode`
- `source_mode`
- `deterministic_default`
- `adaptive_runtime_requested`
- `phase4i_contract_required`
- `validation_reference`
- `command_preview`
- `execution_steps`
- `execution_allowed_for_future`
- `execution_performed`
- `run_analysis_called`
- `object_storage_called`
- `local_file_read_performed`
- `db_lookup_performed`
- `dashboard_regenerated`
- `output_written`
- `notes`

Safety flags must remain false. The plan is metadata only.

## 6. ReAnalysisExecutionResult

`ReAnalysisExecutionResult` records the controller decision:

- `execution_result_id`
- `request_id`
- `requested_action`
- `execution_status`
- `execution_plan`
- `comparison_artifact`
- `validation_status`
- `denied_reasons`
- `warnings`
- `required_next_steps`
- `output_artifact_reference`
- `phase4i_reference`
- `dashboard_reference`
- `runtime_execution_performed`
- `phase4i_mutated`
- `dashboard_regenerated`
- `output_written`
- `deterministic_runtime_authoritative`
- `notes`

Runtime flags must remain false and deterministic runtime remains authoritative.

## 7. Supported Actions

Supported actions are:

- `analyze_selection`
- `rerun_analysis`
- `build_comparison`
- `load_from_object_storage`

`analyze_selection` creates a non-executing plan/result. `rerun_analysis` creates a non-executing plan/result. `load_from_object_storage` creates a blocked result and does not call object storage. `build_comparison` can only compare supplied in-memory payloads.

## 8. Command Preview Boundary

Command preview metadata is descriptive only.

Command preview text does not authorize local execution, subprocess execution, dashboard refresh, file access, object storage access, DB lookup, or Phase 4I mutation.

## 9. Execution Blocking in Phase 7AM

Execution remains blocked in Phase 7AM.

Plans and results preserve:

- `execution_performed=false`
- `runtime_execution_performed=false`
- `run_analysis_called=false`
- `object_storage_called=false`
- `local_file_read_performed=false`
- `db_lookup_performed=false`
- `dashboard_regenerated=false`
- `output_written=false`
- `phase4i_mutated=false`

No execution status means real backend execution occurred.

## 10. Source Boundary

Source references are metadata from Phase 7AK and Phase 7AL.

Phase 7AM does not load local files, read AWR files, call object storage, validate object storage credentials, query existing run databases, or implement EM Extract behavior.

## 11. Runtime Truth Boundary

Deterministic runtime remains authoritative.

Controller records do not change parser output, scoring output, decision output, recommendation output, trend/anomaly output, runtime gate state, Phase 4I payloads, dashboard payloads, generated dashboard HTML, memory state, or CLI behavior.

## 12. Phase 4I Boundary

Phase 4I is not mutated in Phase 7AM.

Future execution must preserve or explicitly version and validate the Phase 4I contract. Phase 7AM only records `phase4i_contract_required=true` metadata.

## 13. Dashboard Output Boundary

Phase 7AM does not regenerate dashboards and does not write output artifacts.

Future dashboard output refresh remains governed by later workflow and output lifecycle phases.

## 14. Relationship to 7AJ

Phase 7AJ defined the Screen 3 backend re-analysis boundary and established that selection is not execution.

Phase 7AM follows that boundary by keeping controller behavior non-executing.

## 15. Relationship to 7AK

Phase 7AK defined source selection metadata.

Phase 7AM consumes source mode metadata from requests but does not load selected sources, validate real source availability, call object storage, read local files, or query databases.

## 16. Relationship to 7AL

Phase 7AL defined backend re-analysis request metadata and validation metadata.

Phase 7AM evaluates those request records into controller plans/results, while preserving the rule that request/controller metadata is not execution.

## 17. Relationship to 7AM.1

Phase 7AM.1 is included in this task as an in-memory AWR / Report Comparison Engine.

`build_comparison` can only compare supplied in-memory payloads. It does not parse AWR files, read reports, query DB, call object storage, call `run_analysis.py`, or generate dashboards.

## 18. Relationship to Future 7AN

Future 7AN may add Screen 3 submit/action UI.

Phase 7AM adds no Screen 3 buttons, forms, JavaScript backend calls, dashboard action handlers, dashboard behavior changes, or dashboard write controls.

## 19. Relationship to Future 7AO

Future 7AO may add block validation/readiness for Screen 3 backend re-analysis.

Phase 7AM adds focused controller and comparison tests only. It does not implement 7AO readiness, missing metric handling, or execution certification.

## 20. Acceptance Criteria

Phase 7AM is accepted when execution controller metadata, execution plan metadata, execution result metadata, in-memory comparison artifacts, deterministic IDs, serialization helpers, documentation, and focused tests exist.

Acceptance requires:

- The controller does not execute analysis.
- The controller does not call `run_analysis.py`.
- The controller does not read files.
- The controller does not call object storage.
- The controller does not query DB.
- The controller does not regenerate dashboards.
- The controller does not mutate Phase 4I.
- `build_comparison` can only compare supplied in-memory payloads.
- Actual execution is future work.
- No dashboard behavior is changed.
- No CLI behavior is changed.
- Deterministic runtime remains authoritative.
- Phase 8 sizing/TCO is not implemented.
