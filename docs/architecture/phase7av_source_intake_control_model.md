# Phase 7AV Source Intake Control Model

## 1. Purpose

Phase 7AV defines the local deterministic source intake control model for future Screen 1 ingestion and parser governance workflows.

The model lets future Screen 1 workflows describe source intake intent, validate source intake metadata, and preview future intake routing without loading a source or changing runtime behavior.

Source intake is not execution.

## 2. Scope

The scope is local source intake request metadata, source intake validation metadata, source intake preview metadata, supported source modes, supported intake actions, validation statuses, deterministic identifiers, serialization helpers, deserialization helpers, and metadata-only validation rules.

Phase 7AV covers:

- `SourceIntakeRequest`
- `SourceIntakeValidation`
- `SourceIntakePreview`
- supported source modes aligned with 7AK
- supported intake actions
- validation statuses
- actor linkage
- audit linkage
- backend execution validation linkage
- source safety flags
- deterministic ID rules

## 3. Non-Goals

Phase 7AV does not add Screen 1 source intake UI, dashboard buttons, dashboard forms, API routes, CLI commands, backend calls, governed write-path invocation, or backend execution.

Phase 7AV performs no source intake. No files are read. No object storage calls are made. No DB lookup is made. Parser is not invoked. run_analysis.py is not called.

Phase 7AV does not open local files, validate local file contents, list buckets, download objects, import OCI SDK, query existing runs from a database, create ingestion run records, create parser review records, classify parser unknowns, create parser mapping records, create parser candidates, mutate parser output, mutate Phase 4I, change scoring behavior, change decision behavior, or change recommendation behavior.

Phase 7AV does not implement parser unknown review, knowledge artifact review, EM Extract adapter, or Phase 8 sizing/TCO.

## 4. Source Intake Is Not Execution

Source intake request is metadata only in Phase 7AV.

A request may be valid enough for future consideration, but it cannot load, parse, execute, or persist a source. The required validation posture is `can_intake=false in 7AV` and `intake_blocked=true in 7AV`.

No action performs intake in 7AV.

## 5. SourceIntakeRequest Object Shape

`SourceIntakeRequest` describes a future request to intake a source for analysis or parser workflows.

Fields are:

- `intake_request_id`
- `source_mode`
- `source_reference`
- `requested_action`
- `actor_id`
- `actor_audit_context`
- `backend_execution_request`
- `expected_file_type`
- `target_screen`
- `source_label`
- `dry_run`
- `requires_actor`
- `requires_source_validation`
- `requires_backend_validation`
- `requires_audit`
- `intake_performed`
- `file_read_performed`
- `object_storage_called`
- `db_lookup_performed`
- `parser_invoked`
- `run_analysis_called`
- `created_at`
- `notes`

Defaults keep `dry_run=true`, `requires_actor=true`, `requires_source_validation=true`, `requires_backend_validation=true`, `requires_audit=true`, `intake_performed=false`, `file_read_performed=false`, `object_storage_called=false`, `db_lookup_performed=false`, `parser_invoked=false`, and `run_analysis_called=false`.

## 6. SourceIntakeValidation Object Shape

`SourceIntakeValidation` describes metadata-only validation for a source intake request.

Fields are:

- `validation_id`
- `intake_request_id`
- `valid`
- `validation_status`
- `source_mode`
- `source_metadata_valid`
- `actor_present`
- `backend_validation_present`
- `can_intake`
- `intake_blocked`
- `denied_reasons`
- `warnings`
- `required_next_steps`
- `file_read_performed`
- `object_storage_called`
- `db_lookup_performed`
- `parser_invoked`
- `run_analysis_called`
- `notes`

Phase 7AV requires `can_intake=false in 7AV`, `intake_blocked=true in 7AV`, and all execution flags false.

## 7. SourceIntakePreview Object Shape

`SourceIntakePreview` describes a read-only preview for a future intake workflow.

Fields are:

- `preview_id`
- `intake_request_id`
- `source_mode`
- `source_label`
- `expected_file_type`
- `target_screen`
- `preview_summary`
- `source_available_hint`
- `source_validation_required`
- `backend_execution_required`
- `actor_required`
- `audit_required`
- `intake_performed`
- `notes`

The preview is not an intake record. Its default posture is `intake_performed=false`.

## 8. Supported Source Modes

Supported source modes are aligned with Phase 7AK:

- `none`
- `local_staged`
- `local_file`
- `existing_run`
- `object_storage`
- `future_upload`
- `future_em_extract`

`local_file` and `local_staged` are metadata only. `object_storage` is metadata only. `existing_run` is metadata only. `future_upload` and `future_em_extract` are placeholders only.

## 9. Supported Intake Actions

Supported intake actions are:

- `validate_source`
- `request_source_intake`
- `preview_source_intake`
- `prepare_for_reanalysis`
- `prepare_for_parser_review`
- `prepare_for_existing_run_review`
- `prepare_for_object_storage_load`
- `prepare_for_future_em_extract`

Actions are metadata only. No action performs intake in 7AV.

## 10. Validation Statuses

Supported validation statuses are:

- `VALID_METADATA_ONLY`
- `INVALID`
- `NEEDS_ACTOR`
- `NEEDS_SOURCE_REFERENCE`
- `NEEDS_BACKEND_VALIDATION`
- `NEEDS_OBJECT_STORAGE_CONFIG`
- `FUTURE_SOURCE_NOT_IMPLEMENTED`
- `INTAKE_NOT_ALLOWED_IN_THIS_PHASE`

`VALID_METADATA_ONLY` means request metadata can be represented. It does not mean intake can occur. `INTAKE_NOT_ALLOWED_IN_THIS_PHASE` is the expected status for an otherwise valid request because intake remains blocked in Phase 7AV.

## 11. Actor Requirement

Future source intake actions require actor identity.

Phase 7AV request metadata carries `actor_id` and `actor_audit_context`, but it does not authenticate actors and does not authorize action. Actor identity is linked to the Phase 7AE actor identity model.

Requests that require actor metadata and do not include it evaluate to `NEEDS_ACTOR`.

## 12. Backend Validation Requirement

Future source intake must use backend execution mode validation before execution can be considered.

Phase 7AV request metadata may carry backend validation metadata or a backend execution request reference. It does not execute that request. Missing backend validation metadata evaluates to `NEEDS_BACKEND_VALIDATION`.

## 13. Source Validation Requirement

Future source intake must use source validation before intake can be considered.

Phase 7AV validates metadata shape only. Source validation is not source loading. Missing source reference metadata evaluates to `NEEDS_SOURCE_REFERENCE`.

## 14. Local Source Boundary

Local source metadata may describe a staged file id, local path, file name, expected file type, checksum, or availability hint.

Local source metadata does not prove the file exists. Phase 7AV does not check filesystem existence, open files, read files, parse files, compute checksums, or validate local AWR contents.

No files are read.

## 15. Object Storage Boundary

Object storage metadata may describe namespace, bucket, object name, region, compartment, credential mode, URI, configured hint, or availability hint.

Object storage metadata does not prove credentials or object availability. Phase 7AV does not import OCI SDK, validate credentials, list buckets, download objects, inspect object metadata, or load object contents.

No object storage calls are made.

## 16. Existing Run Boundary

Existing run metadata may describe run id, AWR id, DBID, database name, snapshot label, or availability hint.

Existing run metadata does not prove a run record exists. Phase 7AV does not query databases, inspect run history, load prior Phase 4I payloads, or validate prior dashboard artifacts.

No DB lookup is made.

## 17. Future EM Extract Boundary

`future_em_extract is placeholder only`.

Future EM Extract metadata may describe future extract intent, but Phase 7AV does not implement EM Extract collection, parsing, conversion, source loading, or analysis.

EM Extract implementation belongs to Phase 8. Phase 8 sizing/TCO is not implemented.

## 18. Parser Boundary

Source intake request metadata does not invoke parser behavior.

Phase 7AV does not call parser modules, change parser mappings, create parser candidates, classify parser unknowns, change parser diagnostics, change parser confidence, change parser output, or mutate parser runtime.

Parser is not invoked.

## 19. Runtime Truth Boundary

Source intake metadata is not runtime truth.

Phase 7AV changes no parser output, scoring output, decision output, recommendation output, Phase 4I payload, dashboard payload, generated dashboard HTML, CLI behavior, database state, memory state, or runtime adapter state.

Deterministic runtime remains authoritative.

## 20. Relationship to 7AU

Phase 7AU defined the Screen 1 ingestion/parser governance workflow boundary.

Phase 7AV implements the local deterministic source intake request, validation, and preview model allowed by that boundary. It preserves the 7AU rule that source intake request is not ingestion behavior and that Screen 1 workflows do not directly change parser behavior.

## 21. Relationship to 7AK

Phase 7AK defined source selection metadata for Screen 3.

Phase 7AV aligns source modes with 7AK so future Screen 1 source validation and Screen 3 re-analysis can share source intent concepts. Source selection remains distinct from source intake, and source intake remains blocked in Phase 7AV.

## 22. Relationship to Future 7AW

Future 7AW may define parser unknown review UI and workflow.

Phase 7AV may prepare source metadata for future parser review, but it does not classify parser unknowns, create parser review records, create mapping records, link candidates, or modify parser output.

## 23. Relationship to Future 7AX

Future 7AX may define knowledge artifact review workflow.

Phase 7AV does not create artifact review records, approve artifacts, reject artifacts, request revisions, materialize artifacts, or link artifacts to parser/scoring/recommendation candidates.

## 24. Relationship to Phase 8 EM Extract

Phase 8 may later define EM Extract support, sizing/TCO, and what-if advisory features.

Phase 7AV includes `future_em_extract` as placeholder metadata only. EM Extract implementation belongs to Phase 8. Phase 8 sizing/TCO is not implemented.

## 25. Acceptance Criteria

Phase 7AV is accepted when source intake request, validation, and preview models exist; supported source modes and intake actions are defined; deterministic IDs exist; serialization and deserialization helpers exist; validation rejects unsafe flags; evaluation keeps `can_intake=false in 7AV` and `intake_blocked=true in 7AV`; source intake is not execution; no files are read; no object storage calls are made; no DB lookup is made; parser is not invoked; run_analysis.py is not called; future_em_extract is placeholder only; EM Extract implementation belongs to Phase 8; Phase 8 sizing/TCO is not implemented; and deterministic runtime remains authoritative.
