# Phase 7 Parser Evolution Model

## Purpose

The Phase 7Q parser evolution model defines local proposal records for parser mapping evolution. It represents proposed parser changes and inactive parser backlog items without changing runtime parser behavior. No parser mapping is applied to runtime, no parser module is modified, no Phase 4I contract is changed, and no scoring regression may be ignored.

## ParserMappingEvolution Object Shape

ParserMappingEvolution contains evolution_id, source_materialization_id, source_candidate_id, evolution_type, parser_section, signal_name, affected_component, proposed_mapping_summary, proposed_parser_change_type, proposed_mapping, implementation_reference, validation_requirements, rollback_plan, phase4i_contract_required, awr_regression_required, scoring_regression_required, runtime_influence_requested, runtime_influence_granted, status, actor, created_at, validation_reference, source_evidence, and semantic_context.

evolution_id is deterministic. source_materialization_id and source_candidate_id link the evolution back to the Phase 7N materialization artifact and original candidate. proposed_mapping_summary, proposed_parser_change_type, proposed_mapping, validation_requirements, rollback_plan, and actor are required. phase4i_contract_required=true, awr_regression_required=true, and scoring_regression_required=true are mandatory. created_at defaults to None and is not generated from current time.

## ParserBacklogItem Object Shape

ParserBacklogItem contains backlog_id, source_evolution_id, parser_section, signal_name, proposed_parser_change_type, title, description, acceptance_criteria, validation_requirements, rollback_plan, runtime_active, runtime_influence_granted, status, actor, source_materialization_id, and source_candidate_id.

runtime_active=false and runtime_influence_granted=false are enforced. Parser backlog items are inactive. A ParserBacklogItem may be serialized, deserialized, validated, and compared as a work item, but it is never applied to runtime parser behavior in Phase 7Q.

## Supported Evolution Types

Supported evolution types are new_section_mapping, section_mapping_refinement, unknown_signal_mapping, regex_pattern_review, normalization_rule_review, field_extraction_review, unit_conversion_review, parser_confidence_metadata_review, section_registry_review, and parser_regression_test_addition. These cover proposed changes to section detection, existing section mapping, unknown signal mapping, regex patterns, normalization rules, field extraction, unit conversion, confidence metadata, section registry compatibility, and regression test coverage.

## Supported Parser Change Types

Supported parser change types are parser_code_change, parser_config_change, regex_mapping_change, section_registry_change, normalization_rule_change, field_extraction_change, unit_conversion_change, test_only_change, and documentation_change. These are proposal categories only. They do not modify runtime code or configuration.

## Statuses

Supported statuses are PROPOSED, UNDER_REVIEW, APPROVED_FOR_IMPLEMENTATION, BACKLOG_CREATED, IMPLEMENTED, VALIDATED, REJECTED, ROLLED_BACK, and CLOSED. No status means runtime active. BACKLOG_CREATED is not runtime active. IMPLEMENTED does not mean runtime active. VALIDATED does not mean runtime active by itself. runtime_influence_granted=false remains enforced for every status.

## Source Artifact Requirements

ParserMappingEvolution creation requires a Phase 7N parser_mapping_artifact source. The source must come from a parser_mapping_candidate, must be runtime-sensitive, must have runtime_influence_granted=false, must be MATERIALIZED or VALIDATED, must include parser validation requirements, and must not be REJECTED, ROLLED_BACK, or CLOSED. Scoring review artifacts and recommendation rule artifacts cannot create parser mapping evolutions.

## Validation Requirements

Every parser mapping evolution must include validation requirements covering parser tests, AWR regression validation, Phase 4I contract validation, unknown signal safety, scoring regression check, rollback plan, and deterministic runtime remains authoritative. Missing required concepts fail validation. Deserialization also validates these concepts so invalid records cannot bypass construction. Phase 4I contract must be preserved, and scoring regression validation is required.

## Evolution-Type-Specific Validation

new_section_mapping requires section detection validation. section_mapping_refinement requires old/new section comparison. unknown_signal_mapping requires unknown signal safety validation. regex_pattern_review requires regex regression validation. normalization_rule_review requires normalization regression validation. field_extraction_review requires field extraction validation. unit_conversion_review requires unit conversion validation. parser_confidence_metadata_review requires parser confidence metadata validation. section_registry_review requires registry compatibility validation. parser_regression_test_addition requires test coverage validation.

## Runtime Influence Fields

runtime_influence_requested is request-only and may be true as future review context. It does not activate runtime. runtime_influence_granted=false is mandatory and validation rejects any record that attempts to grant runtime influence. ParserBacklogItem also requires runtime_active=false and runtime_influence_granted=false.

## Deterministic ID Rules

ParserMappingEvolution IDs use PARSER-EVO, evolution type, source materialization id, parser section, and signal name after identifier normalization. ParserBacklogItem IDs use PARSER-BACKLOG and source evolution id after identifier normalization. IDs do not use random UUIDs, timestamps, database sequences, DB writes, network calls, or external services.

## Serialization Rules

ParserMappingEvolution and ParserBacklogItem serialize to deterministic dictionaries with fixed field order. Deserialization validates supported evolution types, supported parser change types, supported statuses, required strings, proposed mapping shape, validation requirements, rollback requirements, runtime_active=false, runtime_influence_granted=false, source evidence shape, and semantic context shape. Serialization does not import runtime parser modules and does not mutate source artifacts.

## Backlog Rules

Parser backlog items are inactive controlled work items. They describe review, implementation planning, validation, and rollback requirements. They cannot activate runtime behavior, cannot rewrite parser modules, cannot update parser regexes, cannot update the section registry, cannot classify unknown signals, and cannot change Phase 4I output.

## Rollback Rules

Every parser mapping evolution and parser backlog item requires rollback_plan. Rollback references describe how a proposed parser mapping would be discarded or reversed by a later certified process. Rollback is not runtime activation and does not modify parser behavior in Phase 7Q.

## Non-Goals

The model does not apply parser mappings, activate parser mappings, mutate parser modules, update runtime parser behavior, update parser regexes, update parser section registry behavior, classify unknown signals, change loader behavior, change parser output, change scoring behavior, change decision behavior, change recommendation behavior, change trend or anomaly behavior, change dashboard behavior, change CLI behavior, write to a database, call OCI, call Oracle Agent Memory, call a semantic recall service, call an LLM, make network calls, implement Phase 7R, implement ML, implement learned_model(x), or implement Phase 8 sizing/TCO. No automatic parser mutation is added. Existing parser remains authoritative. Semantic context is not parser truth. Dashboard and CLI are not parser mutation paths.

## Acceptance Criteria

The model is accepted when it creates proposal-only parser mapping evolutions from valid parser_mapping_artifact sources, rejects scoring and recommendation artifacts, rejects inactive source status misuse, rejects runtime influence grants, requires actor, proposed_mapping_summary, proposed_mapping, validation_requirements, and rollback_plan, enforces base and evolution-type-specific validation requirements, creates inactive parser backlog items, preserves runtime_active=false, preserves runtime_influence_granted=false, serializes deterministically, keeps parser backlog items inactive, applies no parser mapping to runtime, modifies no parser module, changes no Phase 4I contract, keeps no runtime parser changes are applied, keeps existing parser remains authoritative, and keeps deterministic runtime authoritative.
