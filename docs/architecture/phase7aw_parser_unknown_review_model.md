# Phase 7AW Parser Unknown Review Model

## 1. Purpose

Phase 7AW defines local deterministic object shapes and validation rules for Screen 1 parser unknown review workflow metadata.

The model supports future review, routing, and intent capture without persistence or runtime mutation.

## 2. ParserUnknownReviewRecord Object Shape

`ParserUnknownReviewRecord` contains:

- `review_id`
- `unknown_signal_id`
- `source_run_id`
- `source_awr_id`
- `parser_section`
- `signal_name`
- `raw_text`
- `review_decision`
- `review_status`
- `reviewer_actor_id`
- `actor_audit_context`
- `review_notes`
- `parser_mapping_intent_id`
- `parser_backlog_intent_id`
- `candidate_intent_id`
- `write_performed`
- `runtime_influence`
- `parser_output_mutation_requested`
- `phase4i_mutation_requested`
- `created_at`
- `notes`

It is local metadata only. No parser unknown classification is persisted.

## 3. ParserUnknownReviewRequest Object Shape

`ParserUnknownReviewRequest` contains:

- `request_id`
- `unknown_signal_id`
- `requested_decision`
- `actor_id`
- `actor_audit_context`
- `payload`
- `validation_status`
- `can_route_to_write_path`
- `write_performed`
- `runtime_influence`
- `parser_output_mutation_requested`
- `phase4i_mutation_requested`
- `notes`

`can_route_to_write_path` is future eligibility only and does not invoke a write path.

## 4. ParserMappingIntent Object Shape

`ParserMappingIntent` contains:

- `intent_id`
- `unknown_signal_id`
- `parser_section`
- `signal_name`
- `mapping_intent_type`
- `proposed_mapping_summary`
- `candidate_type`
- `requires_human_review`
- `candidate_created`
- `parser_mapping_created`
- `runtime_influence`
- `parser_output_mutation_requested`
- `phase4i_mutation_requested`
- `notes`

Parser mapping intent is not parser mapping. No parser mapping is created and no parser candidate is created automatically.

## 5. ParserBacklogIntent Object Shape

`ParserBacklogIntent` contains:

- `backlog_intent_id`
- `unknown_signal_id`
- `parser_section`
- `signal_name`
- `backlog_action`
- `backlog_summary`
- `backlog_item_created`
- `runtime_influence`
- `parser_output_mutation_requested`
- `phase4i_mutation_requested`
- `notes`

Backlog intent is not backlog item. No backlog item is created.

## 6. ParserUnknownReviewValidation Object Shape

`ParserUnknownReviewValidation` contains:

- `validation_id`
- `request_id`
- `valid`
- `validation_status`
- `requested_decision`
- `actor_present`
- `unknown_signal_present`
- `can_route_to_write_path`
- `write_performed`
- `denied_reasons`
- `warnings`
- `required_next_steps`
- `runtime_influence`
- `parser_output_mutation_requested`
- `phase4i_mutation_requested`
- `notes`

Validation is metadata-only. It does not persist review state.

## 7. Review Decisions

Supported review decisions are:

- `parser_gap`
- `source_gap`
- `false_positive`
- `not_applicable`
- `needs_mapping`
- `needs_backlog`
- `needs_human_review`
- `add_review_note`

Unsupported decisions fail validation.

## 8. Review Statuses

Supported review statuses are:

- `proposed`
- `under_review`
- `reviewed`
- `routed_to_mapping`
- `routed_to_backlog`
- `false_positive`
- `not_applicable`
- `closed`

Unsupported statuses fail validation.

## 9. Mapping Intent Types

Supported mapping intent types are:

- `new_section_mapping`
- `section_mapping_refinement`
- `unknown_signal_mapping`
- `regex_pattern_review`
- `normalization_rule_review`
- `field_extraction_review`
- `parser_confidence_metadata_review`

Unsupported mapping intent types fail validation.

## 10. Backlog Actions

Supported backlog actions are:

- `create_backlog_item`
- `link_to_existing_backlog`
- `request_parser_test`
- `request_regression_validation`
- `close_without_action`

Unsupported backlog actions fail validation.

## 11. Validation Rules

Review records require a review id, unknown signal id, supported decision, supported status, list-based review notes, and runtime safety flags set to false.

Review requests require a request id, supported decision, payload dictionary, and actor metadata for workflow validation.

Mapping intents require a supported mapping intent type, `requires_human_review=true`, `candidate_created=false`, `parser_mapping_created=false`, and runtime safety flags set to false.

Backlog intents require a supported backlog action, `backlog_item_created=false`, and runtime safety flags set to false.

Validation results require supported validation status, supported decision, list-based denied reasons, list-based warnings, list-based required next steps, `write_performed=false`, `runtime_influence=false`, `parser_output_mutation_requested=false`, and `phase4i_mutation_requested=false`.

## 12. Serialization Rules

All object models serialize to plain dictionaries and deserialize back to equivalent deterministic dataclass records.

Serialization does not persist records. Deserialization validates metadata shape only.

## 13. Deterministic ID Rules

IDs are deterministic and use normalized request metadata. They do not use random UUIDs, timestamps, database sequences, or external services.

Identifier shapes include:

- `SCREEN1-PARSER-UNKNOWN-REVIEW-<UNKNOWN_SIGNAL>-<DECISION>`
- `SCREEN1-PARSER-UNKNOWN-REQUEST-<UNKNOWN_SIGNAL>-<DECISION>`
- `SCREEN1-PARSER-MAPPING-INTENT-<UNKNOWN_SIGNAL>-<MAPPING_TYPE>`
- `SCREEN1-PARSER-BACKLOG-INTENT-<UNKNOWN_SIGNAL>-<BACKLOG_ACTION>`
- `SCREEN1-PARSER-UNKNOWN-VALIDATION-<REQUEST_ID>`

## 14. Runtime Safety Rules

Runtime safety flags must remain false:

- `write_performed=false`
- `runtime_influence=false`
- `candidate_created=false`
- `parser_mapping_created=false`
- `backlog_item_created=false`
- `parser_output_mutation_requested=false`
- `phase4i_mutation_requested=false`

No parser output is changed. No Phase 4I mutation occurs. Deterministic runtime remains authoritative.

## 15. Non-Goals

Phase 7AW does not persist review records, modify stored unknown signal state, classify unknown signals at runtime, create actual parser mappings, create actual parser candidates, create actual backlog items, invoke governed write path, call parser modules, call backend execution, call `run_analysis.py`, modify dashboard submit behavior, add CLI commands, implement knowledge artifact workflow, implement source intake execution, or implement Phase 8 sizing/TCO.

## 16. Acceptance Criteria

Phase 7AW model work is accepted when all object shapes exist, supported decisions/statuses/mapping intent types/backlog actions validate, unsupported values fail, deterministic IDs are stable, serialization round trips are deterministic, decision routing creates mapping intents only for parser_gap and needs_mapping, decision routing creates backlog intents only for needs_backlog, parser mapping intent is not parser mapping, backlog intent is not backlog item, no parser unknown classification is persisted, no parser mapping is created, no parser candidate is created automatically, no backlog item is created, no parser output is changed, no Phase 4I mutation occurs, deterministic runtime remains authoritative, and Phase 8 sizing/TCO is not implemented.
