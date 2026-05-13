# Phase 7Q Parser Mapping Evolution

## Purpose

Phase 7Q adds parser mapping evolution as a controlled, local, deterministic proposal model for parser changes derived from approved parser materialization artifacts. Parser mapping evolution is proposal-only. It describes proposed parser section mappings, unknown signal mappings, regex reviews, normalization reviews, field extraction reviews, unit conversion reviews, parser confidence metadata reviews, section registry reviews, and parser regression test additions for human review without changing runtime parser behavior.

## Scope

Phase 7Q may create and validate ParserMappingEvolution records, serialize and deserialize those records, create inactive ParserBacklogItem records, preserve source evidence and semantic reviewer-assist context, and enforce deterministic validation requirements. It supports proposed work for new section mapping, existing section mapping refinement, unknown signal mapping proposal, regex pattern review, parser normalization rule review, parser field extraction review, unit conversion or normalization review, parser confidence or diagnostic metadata review, parser section registry review, and parser regression test addition.

## Non-Goals

Phase 7Q does not modify runtime parser behavior, parser code paths, parser regexes used by runtime, parser section registry behavior used by runtime, loader behavior, unknown signal classification behavior, scoring logic, decision logic, recommendation logic, trend or anomaly logic, Phase 4I output contracts, dashboard behavior, CLI behavior, database state, OCI state, Oracle Agent Memory, semantic recall services, LLM services, or network resources. No runtime parser changes are applied. Phase 7Q does not apply parser mappings automatically, does not create dashboard parser approval controls, does not add CLI parser mutation commands, does not implement Phase 7R certification, does not implement ML, does not implement learned_model(x), and does not implement Phase 8 sizing/TCO.

## Source Materialization Artifact Requirement

A parser mapping evolution must originate from a parser_mapping_artifact created from a parser_mapping_candidate. The source artifact must be runtime-sensitive, must have runtime_influence_granted=false, must be MATERIALIZED or VALIDATED, must include parser validation requirements, and must not be REJECTED, ROLLED_BACK, or CLOSED. The source artifact is never mutated by parser evolution creation.

## Parser Evolution Types

Supported parser evolution types are new_section_mapping, section_mapping_refinement, unknown_signal_mapping, regex_pattern_review, normalization_rule_review, field_extraction_review, unit_conversion_review, parser_confidence_metadata_review, section_registry_review, and parser_regression_test_addition. Unsupported parser evolution types fail validation.

## Parser Change Types

Supported parser change types are parser_code_change, parser_config_change, regex_mapping_change, section_registry_change, normalization_rule_change, field_extraction_change, unit_conversion_change, test_only_change, and documentation_change. These are proposed change categories only. They do not modify runtime parser code, parser regexes, parser configuration, parser registry behavior, or parser output.

## Parser Mapping Evolution Flow

The flow is parser_mapping_candidate approval, Phase 7N parser_mapping_artifact materialization, Phase 7Q ParserMappingEvolution creation, deterministic proposal validation, and optional later human review. This flow produces proposal records only. It does not activate parser mappings, call runtime parser modules, rewrite parser registries, update parser regexes, classify unknown signals, or write runtime configuration.

## Parser Backlog Flow

A ParserBacklogItem may be created from a validated ParserMappingEvolution. The backlog item receives a deterministic backlog_id, source_evolution_id, parser_section, signal_name, proposed_parser_change_type, title, description, acceptance criteria, validation requirements, rollback plan, source references, runtime_active=false, and runtime_influence_granted=false. Parser backlog items are inactive. IMPLEMENTED does not mean runtime active. VALIDATED does not mean runtime active by itself. A backlog item is controlled work context, not parser runtime truth.

## Runtime Influence Boundary

runtime_influence_requested may document a request for future approval, but it is not runtime activation. runtime_influence_granted=false is enforced for every ParserMappingEvolution and ParserBacklogItem in Phase 7Q. No Phase 7Q status grants runtime influence. BACKLOG_CREATED is not runtime active, IMPLEMENTED is not runtime active by itself, and VALIDATED is not runtime active by itself.

## Phase 4I Contract Boundary

Phase 4I contract preservation is mandatory. Phase 4I contract must be preserved for every parser evolution proposal. A Phase 7Q record may require Phase 4I contract validation, but Phase 7Q itself does not change parser output shape, diagnostic payloads, score payloads, recommendation payloads, dashboard truth, or any validated Phase 4I output contract.

## AWR Regression Boundary

AWR regression validation is required for every parser evolution proposal. Parser changes can alter parsed sections, extracted fields, normalization, diagnostics, scores, trends, decisions, recommendations, and later sizing assumptions. Phase 7Q only records the requirement for AWR regression validation; it does not execute or apply parser changes.

## Unknown Signal Boundary

Unknown signal review may inform a proposal, but unknown signals are not auto-classified. Phase 7Q can represent an unknown_signal_mapping proposal, but it cannot directly change parser output, convert unknown signals into known signals, or modify section detection. Unknown signal safety validation is mandatory.

## Scoring Regression Boundary

Scoring regression validation is required. Parser changes can corrupt downstream scoring and recommendation behavior. Every parser evolution proposal must require a scoring regression check before any later certified implementation path can be considered. Phase 7Q itself does not change scoring logic or scoring inputs.

## Semantic Context Boundary

Semantic context may support reviewer-assist context only. Semantic context is not parser truth, not source evidence, not deterministic parser evidence, and not a source of automatic parser changes. Semantic context cannot activate a parser mapping evolution or parser backlog item.

## Dashboard / CLI Boundary

Dashboard and CLI are not parser mutation paths. Dashboard and CLI surfaces may not rewrite parser logic, approve parser mappings into runtime, update parser regexes, change parser registry entries, classify unknown signals, or mark parser backlog items active. Phase 7Q adds no dashboard controls, no CLI controls, no approval buttons, no write controls, and no commands that mutate parser behavior.

## Parser Runtime Boundary

Existing runtime parser behavior remains deterministic and authoritative. Existing parser remains authoritative. Phase 7Q does not import runtime parser modules, does not change parser regexes, does not change section registry behavior, does not change parser normalization, does not change field extraction, and does not change parser confidence or diagnostic metadata produced by runtime.

## Validation Requirements

Every parser mapping evolution must include parser tests, AWR regression validation, Phase 4I contract validation, unknown signal safety, scoring regression check, rollback plan, and deterministic runtime remains authoritative. Evolution-type-specific validation also applies: new section mapping requires section detection validation, section mapping refinement requires old/new section comparison, unknown signal mapping requires unknown signal safety validation, regex pattern review requires regex regression validation, normalization rule review requires normalization regression validation, field extraction review requires field extraction validation, unit conversion review requires unit conversion validation, parser confidence metadata review requires parser confidence metadata validation, section registry review requires registry compatibility validation, and parser regression test addition requires test coverage validation.

## Rollback Requirements

Every parser mapping evolution must include rollback_plan. Rollback planning must identify how the proposed parser mapping or backlog item would be discarded or reversed by a later certified implementation process. Rollback is audit and validation context only in Phase 7Q. It does not activate, update, or revert runtime parser behavior by itself.

## Relationship to Phase 7M

Phase 7M defined the learning materialization boundary and established that parser evolution is first-class and protected. Phase 7Q follows that boundary by keeping parser evolution local, deterministic, proposal-only, and separated from runtime activation.

## Relationship to Phase 7N

Phase 7N introduced parser_mapping_artifact records from approved parser_mapping_candidate records. Phase 7Q uses only MATERIALIZED or VALIDATED parser_mapping_artifact sources and converts them into proposal-only parser evolution records and inactive parser backlog items. Phase 7N artifacts remain source materialization records and are not mutated.

## Relationship to Phase 7O

Phase 7O added proposal-only scoring review artifacts and inactive proposed scoring configs. Phase 7Q preserves Phase 7O behavior and adds no scoring mutation. Parser evolution must require scoring regression validation because parser changes can corrupt scores.

## Relationship to Phase 7P

Phase 7P added proposal-only recommendation rule evolution artifacts and inactive proposed recommendation rules. Phase 7Q preserves Phase 7P behavior and adds no recommendation mutation. Parser evolution must protect recommendation behavior by requiring AWR, Phase 4I, and scoring regression checks before any later certified implementation.

## Relationship to Future Phase 7R

Future Phase 7R may define certification or approval mechanics for controlled materialization, but Phase 7Q does not implement Phase 7R. Phase 7Q does not certify parser mappings, does not grant runtime influence, and does not apply parser backlog items.

## Relationship to ML Phases

Future ML phases may define certified adaptive intelligence, but Phase 7Q is not ML. It does not implement learned_model(x), does not train a model, does not infer parser mappings at runtime, and does not create autonomous runtime parser changes.

## Acceptance Criteria

Phase 7Q is accepted when parser mapping evolution records can be created only from valid parser_mapping_artifact sources, unsupported source artifact types fail, unsupported evolution types fail, unsupported parser change types fail, required validation requirements are enforced, evolution-type-specific validation is enforced, rollback plans are required, deterministic evolution and backlog IDs are generated, serialization is deterministic, parser backlog items are inactive, runtime_active=false, runtime_influence_granted=false, IMPLEMENTED does not mean runtime active, VALIDATED does not mean runtime active by itself, no runtime parser changes are applied, no parser module is modified, no parser output changes, no scoring/decision/recommendation behavior changes, no dashboard behavior changes, no CLI behavior changes, no automatic parser mutation is added, semantic context is not parser truth, existing parser remains authoritative, and deterministic runtime remains authoritative.
