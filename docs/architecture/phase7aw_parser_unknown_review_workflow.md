# Phase 7AW Parser Unknown Review Workflow

## 1. Purpose

Phase 7AW defines the local parser unknown review workflow and intention model for future Screen 1 ingestion and parser governance workflows.

Parser unknown review creates local review and intention models only. It does not change parser behavior.

## 2. Scope

The scope is local parser unknown review records, review request metadata, parser mapping intents, parser backlog intents, review validation metadata, deterministic decision routing helpers, serialization helpers, deserialization helpers, validation helpers, and architecture documentation.

Phase 7AW supports future review of parser unknown signals by defining how a reviewer may express intent to classify an unknown signal, request parser mapping work, route parser backlog work, or add parser review notes.

## 3. Non-Goals

Phase 7AW does not persist parser unknown review records. No parser unknown classification is persisted.

Phase 7AW does not classify unknown signals at runtime, modify unknown signal stored state, create parser mapping records, create parser candidates, create backlog items, approve or reject parser mappings, invoke governed write path, call parser modules, call backend actions, call `run_analysis.py`, mutate parser behavior, mutate parser output, mutate Phase 4I, mutate scoring, mutate decision, mutate recommendation, add active dashboard submit behavior, add CLI commands, implement knowledge artifact workflow, implement source intake execution, or implement Phase 8 sizing/TCO.

No parser mapping is created. No parser candidate is created automatically. No backlog item is created. No parser output is changed. No Phase 4I mutation occurs.

## 4. Parser Unknown Review Is Not Parser Mutation

Parser unknown review is governed review metadata.

A review record, review request, mapping intent, backlog intent, validation result, or routed preview does not update parser code, parser configuration, parser section recognition, parser unknown signal storage, parser confidence, parser diagnostics, extracted metrics, feature vectors, scoring, decisions, recommendations, dashboard payloads, or Phase 4I.

Deterministic runtime remains authoritative.

## 5. ParserUnknownReviewRecord

`ParserUnknownReviewRecord` is a local review record for a parser unknown signal.

Fields are:

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

The required safety flags are `write_performed=false`, `runtime_influence=false`, `parser_output_mutation_requested=false`, and `phase4i_mutation_requested=false`.

## 6. ParserUnknownReviewRequest

`ParserUnknownReviewRequest` is a future request object for parser unknown review workflow.

Fields are:

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

`can_route_to_write_path` is future eligibility only. It does not invoke the governed write path and does not persist review state.

## 7. ParserMappingIntent

`ParserMappingIntent` is a local intent to request parser mapping work.

Fields are:

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

Parser mapping intent is not parser mapping. It creates no parser mapping and creates no parser candidate automatically.

## 8. ParserBacklogIntent

`ParserBacklogIntent` is a local intent to route parser work to backlog.

Fields are:

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

Backlog intent is not backlog item. It creates no parser backlog item and has no runtime influence.

## 9. ParserUnknownReviewValidation

`ParserUnknownReviewValidation` is a validation result for parser unknown review requests.

Fields are:

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

The required safety flags are `write_performed=false`, `runtime_influence=false`, `parser_output_mutation_requested=false`, and `phase4i_mutation_requested=false`.

## 10. Review Decisions

Supported review decisions are:

- `parser_gap`
- `source_gap`
- `false_positive`
- `not_applicable`
- `needs_mapping`
- `needs_backlog`
- `needs_human_review`
- `add_review_note`

These decisions are local review intent. They are not runtime classification.

## 11. Review Statuses

Supported review statuses are:

- `proposed`
- `under_review`
- `reviewed`
- `routed_to_mapping`
- `routed_to_backlog`
- `false_positive`
- `not_applicable`
- `closed`

Statuses are local review state. They are not parser runtime state.

## 12. Mapping Intent Types

Supported mapping intent types are:

- `new_section_mapping`
- `section_mapping_refinement`
- `unknown_signal_mapping`
- `regex_pattern_review`
- `normalization_rule_review`
- `field_extraction_review`
- `parser_confidence_metadata_review`

Mapping intent type selection does not create parser mapping records.

## 13. Backlog Actions

Supported backlog actions are:

- `create_backlog_item`
- `link_to_existing_backlog`
- `request_parser_test`
- `request_regression_validation`
- `close_without_action`

Backlog actions are local intent values. They do not create actual backlog items.

## 14. Decision Routing Rules

Decision routing is deterministic and metadata-only:

- `parser_gap` routes to `ParserMappingIntent` with `parser_mapping_candidate`.
- `needs_mapping` routes to `ParserMappingIntent` with `parser_mapping_candidate`.
- `needs_backlog` routes to `ParserBacklogIntent`.
- `source_gap` creates no parser mapping intent and recommends source review.
- `false_positive` creates no parser mapping intent and routes to false_positive closure state.
- `not_applicable` creates no parser mapping intent and routes to not_applicable closure state.
- `needs_human_review` remains under_review.
- `add_review_note` records note intent only.

No actual candidate, backlog, or parser mapping records are created.

## 15. Runtime Parser Boundary

Parser runtime remains authoritative.

Phase 7AW does not invoke parser modules, update parser mappings, update parser config, update parser code, alter unknown signal output, alter parser confidence, alter parser diagnostics, or alter parser extraction behavior.

No parser output is changed.

## 16. Phase 4I Boundary

Phase 4I remains protected.

Parser unknown review metadata does not alter Phase 4I payload shape, parser output inside Phase 4I, scoring output, decision output, recommendation output, or dashboard contract.

No Phase 4I mutation occurs.

## 17. Candidate Creation Boundary

Parser mapping intent may reference `parser_mapping_candidate` as future target type.

That intent is not a candidate. No parser candidate is created automatically.

## 18. Backlog Creation Boundary

Parser backlog intent may request future backlog routing.

That intent is not a backlog item. No backlog item is created.

## 19. Relationship to 7AU

Phase 7AU defined the Screen 1 ingestion/parser governance workflow boundary.

Phase 7AW implements the local parser unknown review and intention model allowed by that boundary. It preserves the 7AU rules that parser unknown review is governed and that review state does not mutate parser output.

## 20. Relationship to 7AV

Phase 7AV defined source intake request, validation, and preview models.

Phase 7AW may reference source run or AWR identifiers in review metadata, but it does not perform source intake, load sources, call object storage, query databases, or execute backend analysis.

## 21. Relationship to Future 7AX

Future 7AX may define knowledge artifact review workflow.

Phase 7AW does not review knowledge artifacts, approve artifacts, reject artifacts, request artifact revision, link artifacts to candidates, materialize artifacts, or activate artifacts.

## 22. Relationship to Future 7AY

Future 7AY may validate and certify the Screen 1 workflow block.

Phase 7AW adds only local parser unknown review and intent models plus tests and documentation. It does not implement final block readiness or certification.

## 23. Relationship to Phase 8

Phase 8 sizing/TCO and what-if advisory are not implemented.

Phase 7AW does not implement EM Extract, capacity planning, cost modeling, sizing recommendations, or what-if advisory.

## 24. Acceptance Criteria

Phase 7AW is accepted when parser unknown review records, parser unknown review requests, parser mapping intents, parser backlog intents, review validation metadata, deterministic routing helpers, validation helpers, serialization helpers, deserialization helpers, documentation, and tests exist; no parser unknown classification is persisted; no parser mapping is created; no parser candidate is created automatically; no backlog item is created; parser mapping intent is not parser mapping; backlog intent is not backlog item; no parser output is changed; no Phase 4I mutation occurs; deterministic runtime remains authoritative; and Phase 8 sizing/TCO is not implemented.
