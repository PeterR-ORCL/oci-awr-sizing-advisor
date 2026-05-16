# Phase 7BU Status Transition Execution Model

## Purpose

Phase 7BU.2 defines local metadata for future governed status transition execution. It describes candidate, materialization artifact, model registry entry, runtime gate, and related governance transition requests/results before any durable persistence or actual state change is allowed.

## Object Shapes

`GovernanceStatusTransitionRequest` includes `transition_request_id`, `entity_type`, `entity_id`, `from_status`, `to_status`, `transition_action`, `actor_id`, `actor_audit_context`, `validation_reference`, `rollback_reference`, `idempotency_key`, `payload`, `transition_requested`, `transition_performed`, `status_changed`, `db_write_performed`, `runtime_activation_requested`, `runtime_active`, `phase4i_mutation_requested`, `created_at`, and `notes`.

`GovernanceStatusTransitionValidation` includes `transition_validation_id`, `transition_request_id`, `valid`, `validation_status`, `entity_type`, `transition_action`, `actor_present`, `validation_reference_present`, `rollback_reference_present`, `idempotency_key_present`, `allowed_transition`, `can_transition_later`, `transition_performed`, `status_changed`, `db_write_performed`, `runtime_active`, `denied_reasons`, `warnings`, `required_next_steps`, `phase4i_mutation_requested`, and `notes`.

`GovernanceStatusTransitionResult` includes `transition_result_id`, `transition_request_id`, `transition_validation_id`, `entity_type`, `entity_id`, `from_status`, `to_status`, `transition_action`, `result_status`, `transition_performed`, `status_changed`, `db_write_performed`, `runtime_active`, `audit_record`, `transaction_metadata`, `rollback_reference`, `denied_reasons`, `warnings`, `required_next_steps`, `phase4i_mutation_requested`, and `notes`.

## Supported Entity Types

The supported entity types are `learning_candidate`, `materialization_artifact`, `model_registry_entry`, `runtime_gate`, `parser_mapping_candidate`, `scoring_review_candidate`, `recommendation_rule_candidate`, `governance_item`, and `workflow_record`.

## Supported Transition Actions

The supported transition actions are `mark_under_review`, `approve_for_implementation`, `approve_for_validation`, `reject`, `request_revision`, `mark_implemented`, `mark_validated`, `retire`, `supersede`, `close`, `request_runtime_review`, `approve_for_shadow`, and `attach_reference`.

## Allowed Transition Metadata

The allowed transition metadata is conservative and local only. It includes `proposed -> under_review`, `under_review -> approved_for_implementation`, `under_review -> approved_for_validation`, `under_review -> rejected`, `under_review -> needs_revision`, `approved_for_implementation -> approved_for_validation`, `approved_for_validation -> implemented`, `implemented -> validated`, `validated -> closed`, and any applicable state to `retired` or `superseded`.

## Validation Rules

Requests require a deterministic request id, supported entity type, entity id, supported transition action, actor id, idempotency key, and an allowed transition pair. State-changing transitions require a rollback reference. Approval, implementation, validation, runtime review, and shadow approval transitions require a validation reference. no status transition is performed in 7bu.

Validation records are metadata only. A valid record means `valid_metadata_only` and `can_transition_later=true`, not that state changed. `transition_performed=false`, `status_changed=false`, `db_write_performed=false`, `runtime_active=false`, and `phase4i_mutation_requested=false` are mandatory.

Results are metadata only. A result can be `valid_for_future_persistence`, but `transition_performed=false`, `status_changed=false`, `db_write_performed=false`, `runtime_active=false`, and `phase4i_mutation_requested=false` remain mandatory.

## Runtime Safety

Status transition execution metadata cannot change candidate status, materialization status, model registry status, runtime gate state, runtime eligibility, shadow eligibility, or runtime activation state. It cannot set `runtime_active=true`, cannot request runtime activation, cannot mutate Phase 4I, and cannot apply parser/scoring/recommendation behavior changes.

## Candidate Boundary

Candidate transitions are represented as metadata only. Future transitions can be validated for idempotency, actor, rollback, and allowed transition metadata, but no candidate status is changed in 7BU.

## Materialization Boundary

Materialization transitions are represented as metadata only. Future validation and rollback references can be modeled, but no materialization status is changed and no runtime materialization is executed.

## Model Registry Boundary

Model registry transitions are represented as metadata only. No model registry status is changed, no shadow eligibility is granted, no runtime eligibility is granted, and no model deployment occurs.

## Runtime Gate Boundary

Runtime gate transitions are represented as metadata only. No runtime gate state is changed, adaptive runtime remains disabled, and `runtime_active=false`.

## Non-Goals

7BU.2 does not persist transition records, update actual status, open a database transaction, write schema or migrations, call DB adapters, activate runtime, grant runtime eligibility, deploy ML models, apply parser mappings, activate scoring configuration, activate recommendation rules, mutate Phase 4I, change dashboard UI, change CLI behavior, call `run_analysis.py`, or implement Phase 8 sizing/TCO.
