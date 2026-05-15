# Phase 7AV Source Intake Validation

## 1. Purpose

Phase 7AV source intake validation defines how local deterministic request metadata is evaluated for future Screen 1 source intake workflows.

Validation is not intake.

## 2. Validation Flow

The validation flow is metadata-only:

1. Validate request shape.
2. Validate source mode.
3. Validate actor metadata presence.
4. Validate source reference metadata presence.
5. Validate backend validation metadata presence.
6. Validate object storage configuration hints when source mode is object_storage.
7. Block future_upload and future_em_extract as future source placeholders.
8. Return `INTAKE_NOT_ALLOWED_IN_THIS_PHASE` for otherwise valid metadata.

No source is loaded during validation.

## 3. Source Mode Validation

Supported source modes are `none`, `local_staged`, `local_file`, `existing_run`, `object_storage`, `future_upload`, and `future_em_extract`.

Unsupported source modes fail safely as invalid metadata. Supported source modes do not imply source availability or execution permission.

## 4. Actor Validation

Future source intake actions require actor identity.

The validation model checks whether `actor_id` or `actor_audit_context` is present. Missing actor metadata returns `NEEDS_ACTOR` when the request requires actor identity.

Actor validation does not authenticate, authorize, execute, or write records.

## 5. Backend Validation Metadata

Future source intake requires backend execution validation metadata.

The validation model checks whether backend validation metadata is present. Missing backend metadata returns `NEEDS_BACKEND_VALIDATION`.

Backend validation metadata is a reference only. Phase 7AV does not execute backend work, call local commands, call APIs, or call run_analysis.py.

## 6. Local Source Metadata

Local source metadata is descriptive only.

The validation model can check whether local source metadata exists. It does not check filesystem existence, open files, read files, parse files, compute checksums, or validate AWR contents.

No file read is made.

## 7. Object Storage Metadata

Object storage metadata is descriptive only.

The validation model can check whether object storage metadata and configuration hints are present. It does not import OCI SDK, validate credentials, list buckets, download objects, inspect object metadata, or load object contents.

No object storage call is made.

## 8. Existing Run Metadata

Existing run metadata is descriptive only.

The validation model can check whether existing run source metadata exists. It does not query databases, inspect run history, load prior Phase 4I payloads, or validate generated dashboard artifacts.

No DB lookup is made.

## 9. Future EM Extract Metadata

`future_em_extract is placeholder only`.

Future EM Extract metadata may validate as representable intent, but it returns `FUTURE_SOURCE_NOT_IMPLEMENTED` in Phase 7AV. EM Extract implementation belongs to Phase 8. Phase 8 sizing/TCO is not implemented.

## 10. Intake Blocking in Phase 7AV

All validation results keep intake blocked.

The required safety posture is `can_intake=false in 7AV` and `intake_blocked=true in 7AV`. Even otherwise valid metadata returns `INTAKE_NOT_ALLOWED_IN_THIS_PHASE`.

## 11. Denied Reasons

Denied reasons explain why intake cannot occur.

Expected denied reasons include missing actor metadata, missing source reference metadata, missing backend validation metadata, unconfirmed object storage configuration, future source placeholders, and the Phase 7AV rule that intake is not allowed in this phase.

Denied reasons are metadata only. They do not create governance records.

## 12. Required Next Steps

Required next steps describe future work needed before intake can be considered.

Expected next steps include providing actor identity through Phase 7AE, providing source reference metadata, providing backend execution validation metadata, validating object storage configuration later, waiting for a future source implementation phase, and routing through a future governed source intake workflow.

Required next steps do not perform actions.

## 13. Runtime Safety Flags

Runtime safety flags must remain false:

- `intake_performed=false`
- `file_read_performed=false`
- `object_storage_called=false`
- `db_lookup_performed=false`
- `parser_invoked=false`
- `run_analysis_called=false`

No parser invocation occurs.

## 14. Non-Goals

Phase 7AV validation does not add Screen 1 UI, dashboard forms, dashboard buttons, CLI commands, API routes, governed write-path invocation, backend execution, source intake, local file reads, object storage calls, database lookups, parser calls, ingestion run records, parser unknown review, knowledge artifact review, EM Extract adapter, Phase 4I mutation, or Phase 8 sizing/TCO.

Invalid requests fail safely.

## 15. Acceptance Criteria

Phase 7AV validation is accepted when request validation rejects unsafe flags, source mode and action validation are deterministic, missing actor metadata returns `NEEDS_ACTOR`, missing source metadata returns `NEEDS_SOURCE_REFERENCE`, missing backend metadata returns `NEEDS_BACKEND_VALIDATION`, object storage without configuration hints returns `NEEDS_OBJECT_STORAGE_CONFIG`, future source placeholders return `FUTURE_SOURCE_NOT_IMPLEMENTED`, otherwise valid metadata returns `INTAKE_NOT_ALLOWED_IN_THIS_PHASE`, `can_intake=false in 7AV`, `intake_blocked=true in 7AV`, no file read is made, no object storage call is made, no DB lookup is made, no parser invocation occurs, run_analysis.py is not called, invalid requests fail safely, future_em_extract remains placeholder only, EM Extract implementation belongs to Phase 8, and Phase 8 sizing/TCO is not implemented.
