# Phase 7BU Governed Workflow Persistence / Audit Store

## Purpose

Phase 7BU.1 defines local metadata for future governed workflow persistence and audit storage. The model prepares the shape of future persistence without implementing a repository, database connection, migration, SQL statement, file persistence path, or durable audit store.

## Object Shapes

`GovernedWorkflowPersistenceRequest` describes a future workflow persistence request. It includes `persistence_request_id`, `workflow_record_type`, `workflow_record_id`, `source_screen`, `actor_id`, `actor_audit_context`, `payload`, `idempotency_key`, `transaction_group_id`, `rollback_reference`, `dry_run`, `persistence_requested`, `persistence_performed`, `db_write_performed`, `runtime_mutation_requested`, `phase4i_mutation_requested`, `created_at`, and `notes`.

`GovernedWorkflowPersistenceValidation` describes local validation of the request. It includes `persistence_validation_id`, `persistence_request_id`, `valid`, `validation_status`, `workflow_record_type`, `actor_present`, `idempotency_key_present`, `rollback_reference_present`, `payload_present`, `can_persist_later`, `persistence_performed`, `db_write_performed`, `denied_reasons`, `warnings`, `required_next_steps`, `runtime_mutation_requested`, `phase4i_mutation_requested`, and `notes`.

`GovernedWorkflowAuditRecord` describes local audit metadata. It includes `audit_record_id`, `workflow_record_type`, `workflow_record_id`, `actor_id`, `action`, `source_screen`, `transaction_group_id`, `idempotency_key`, `audit_summary`, `payload_hash`, `persisted`, `db_write_performed`, `runtime_mutation_performed`, `phase4i_mutation_performed`, `created_at`, and `notes`.

`GovernedWorkflowTransactionMetadata` describes local transaction metadata. It includes `transaction_group_id`, `idempotency_key`, `transaction_scope`, `requested_operations`, `rollback_reference`, `retry_allowed`, `duplicate_handling`, `committed`, `rolled_back`, `db_write_performed`, and `notes`.

## Supported Workflow Record Types

The supported record types are `diagnostic_review`, `evidence_review`, `screen3_reanalysis_request`, `screen3_comparison_artifact`, `recommendation_decision`, `action_tracking`, `outcome_capture`, `feedback_intent`, `parser_unknown_review`, `parser_mapping_intent`, `knowledge_artifact_review`, `historical_review`, `baseline_selection`, `trend_anomaly_review`, `learning_candidate_review`, `materialization_review`, `model_registry_review`, `runtime_gate_review`, `governance_audit`, and `output_artifact`.

## Validation Rules

Requests require a deterministic request id, a supported workflow record type, a workflow record id, an actor id, an idempotency key, a rollback reference, and a non-empty payload dictionary before `can_persist_later=true` can be returned. `dry_run=true` is mandatory. `persistence_performed=false`, `db_write_performed=false`, `runtime_mutation_requested=false`, and `phase4i_mutation_requested=false` are mandatory.

Validation records are metadata only. `valid=true` means `valid_metadata_only`, not that persistence has occurred. `persistence_performed=false`, `db_write_performed=false`, `runtime_mutation_requested=false`, and `phase4i_mutation_requested=false` remain mandatory.

Audit records are metadata only. `persisted=false`, `db_write_performed=false`, `runtime_mutation_performed=false`, and `phase4i_mutation_performed=false` remain mandatory.

Transaction metadata is metadata only. `committed=false`, `rolled_back=false`, and `db_write_performed=false` remain mandatory.

## Idempotency

Each valid request must include an idempotency key. The key is used to derive deterministic transaction group metadata and prepare future duplicate handling. 7BU does not enforce uniqueness against a database because no db persistence occurs in 7bu.

## Transaction Metadata

Transaction metadata describes future transaction scope, requested operations, retry posture, duplicate handling, rollback reference, and idempotency linkage. It does not start, commit, or roll back a transaction.

## Audit Boundary

The audit store record provides a deterministic local audit envelope and payload hash for future durable audit storage. It does not write an audit row, does not write a file, and does not persist any record.

## Runtime Safety

The persistence model is metadata only. It cannot request runtime mutation, cannot request Phase 4I mutation, cannot perform a database write, and cannot activate runtime. Deterministic runtime remains authoritative.

## Non-Goals

7BU.1 does not connect to a database, import database drivers, write SQL, create migrations, persist workflow records, persist audit records, write files, invoke dashboard modules, invoke CLI modules, call `run_analysis.py`, change parser/scoring/decision/recommendation behavior, mutate Phase 4I, activate runtime, or implement Phase 8 sizing/TCO.
