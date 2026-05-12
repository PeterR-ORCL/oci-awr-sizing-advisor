# Phase 7 Operational Model

## 1. Purpose

This document defines how Phase 7 learning capabilities are operated locally and safely. It covers validation, CLI workflows, outcome pattern mining, candidate generation, semantic context, governance review, dashboard review, dashboard interactivity, actor requirements, local JSON input/output, and troubleshooting.

Phase 7 operations are local and deterministic. They do not add runtime behavior, learning activation, dashboard mutation, CLI behavior changes, backend writes, API calls, DB writes, OCI dependencies, Oracle Agent Memory dependencies, semantic recall service dependencies, or LLM calls.

## 2. Operating Modes

Phase 7 has four safe operating modes:

| Mode | Purpose | Runtime Influence | Inputs | Outputs |
| --- | --- | --- | --- | --- |
| Validation mode | Prove Phase 7 boundaries and local test coverage. | None. | Repository files. | Text or JSON validation summaries. |
| CLI inspection mode | Show learning status, patterns, candidates, semantic context, and candidate details. | None. | Local JSON or empty local defaults. | Text or JSON. |
| CLI review mode | Apply local actor-gated candidate lifecycle transitions. | None. | Local candidate JSON, action, actor. | Local JSON review result. |
| Dashboard review mode | Inspect read-only learning, governance, semantic, diagnostic, historical, recommendation, and fleet context. | None. | Existing dashboard payload/rendered output. | Browser-side read-only exploration. |

## 3. Local Validation Workflow

Run the consolidated Phase 7 validation harness:

```bash
python3 scripts/run_phase7_validation.py
```

Run the deterministic JSON form:

```bash
python3 scripts/run_phase7_validation.py --json
```

Run the Phase 7H dashboard validation:

```bash
python3 scripts/run_phase7h_dashboard_validation.py
```

Run Phase 7I CLI validation:

```bash
python3 scripts/awr_memory_cli.py learning validate --json
```

Run the focused CLI unittest:

```bash
python3 -m unittest tests/test_learning_cli_commands.py
```

## 4. Learning CLI Workflow

The learning CLI command group is:

```bash
python3 scripts/awr_memory_cli.py learning ...
```

Use `learning status` to confirm the modules are available and that deterministic runtime remains authoritative. Use `learning patterns` for observational local pattern mining. Use `learning candidates` for proposal-only candidate generation. Use `learning semantic-context` for local reviewer-assist context. Use `learning review` for actor-gated local lifecycle transitions. Use `learning validate --json` for the local CLI validation subset.

All commands are local. Candidate-producing commands preserve `runtime_influence=false` and `requires_human_review=true`.

## 5. Outcome Pattern Mining Workflow

Outcome pattern mining reads local memory-shaped JSON and emits observational pattern records. The records can describe repeated unknown signals, repeated recommendation/outcome relationships, feedback clusters, or governance signals, depending on local input content.

Pattern records are not candidates. They do not approve, implement, activate, or change runtime behavior.

## 6. Candidate Generation Workflow

Candidate generation reads local pattern JSON or mines local memory JSON with `--from-memory`. It emits deterministic proposal-only learning candidates with source evidence, structured sources, candidate type, affected component, confidence, rationale, and safety markers.

Generated candidates are review context only. They do not update parser logic, scoring logic, decision logic, recommendation logic, dashboard truth, or governed memory.

## 7. Semantic Context Workflow

Semantic context attachment reads local semantic JSON and a local candidate record. It attaches optional reviewer-assist context when the local semantic record is relevant.

Semantic context is reviewer-assist only and semantic context is non-authoritative. It is not source evidence, not deterministic evidence, not approval evidence, and not runtime evidence. It cannot change candidate confidence, status, candidate type, source evidence, structured sources, or runtime influence.

## 8. Governance Review Workflow

Governance review uses `learning review` with an explicit actor. Allowed review transitions are local lifecycle transitions. Approval means approved for implementation only.

The review workflow does not implement a candidate, activate runtime behavior, write to DB, write to dashboard artifacts, modify parser logic, change scoring, change recommendations, or create autonomous runtime learning.

## 9. Dashboard Review Workflow

Dashboard review is read-only. Reviewers can inspect learning visibility, candidate status, governance state, semantic context labels, deterministic diagnostic evidence, historical context, recommendation/action context, parser/governance context, and fleet context.

The dashboard is not an approval plane and not a write plane. Learning candidates remain proposal/review context only.

## 10. Dashboard Interactivity Workflow

Dashboard interactivity is read-only. It supports browser-side selection, focused detail panels, and cross-screen selection propagation. URL hash and localStorage state are non-authoritative convenience state.

Interactivity does not change backend state, generated data, candidate status, governance state, parser output, diagnostic truth, historical truth, recommendation truth, or runtime behavior.

## 11. Actor Requirements

Read-only commands do not require an actor. Review commands require `--actor` for every review action.

Actor attribution is required for under-review, reject, needs-revision, approve-for-implementation, attach-materialization, implemented, validated, and close transitions. Actor-gating supports auditability; it is not runtime activation.

## 12. Local JSON Input/Output

Phase 7 CLI commands accept local JSON files. Memory input can include `runs`, `recommendations`, `actions`, `outcomes`, `feedback`, `unknown_signals`, `knowledge_requests`, and `knowledge_artifacts`. Pattern input can be a list, one pattern, or an object with `patterns`. Candidate input can be a list, one candidate, an object with `candidates`, or an object with `candidate`.

Output is deterministic JSON when `--json` is used. Optional export output writes only to a user-specified local file and does not persist runtime state.

## 13. Validation Commands

Required local validation commands before readiness review are:

```bash
python3 scripts/run_phase7_validation.py
python3 scripts/run_phase7_validation.py --json
python3 scripts/run_phase7h_dashboard_validation.py
python3 scripts/awr_memory_cli.py learning validate --json
python3 -m unittest tests/test_learning_cli_commands.py
```

Where available, Phase 6 regression validation can also be run:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_phase6_validation.py
```

## 14. Runtime Isolation Rules

Phase 7 learning modules must not be imported by runtime truth paths. `scripts/run_analysis.py` remains protected. Parser/scoring/decision/recommendation runtime paths remain isolated.

No Phase 7 operation may set `runtime_influence=true`, activate a candidate, alter deterministic truth, call a live semantic service, call Oracle Agent Memory, call OCI, call ADB, call an LLM, or make network calls.

## 15. Operational Non-Goals

Phase 7 operations do not include production readiness certification, live deployment, Phase 7L readiness, automatic parser updates, automatic scoring updates, automatic recommendation updates, uncontrolled autonomous learning, runtime activation, dashboard write controls, CLI behavior changes beyond the existing Phase 7I command group, or DB-backed learning persistence.

## 16. Troubleshooting Notes

If validation fails, inspect the failing group or unittest module first. Missing local files, changed safety phrases, unsafe imports, or behavior changes in learning/dashboard/CLI boundaries should be treated as blockers.

If `.venv` is unavailable, run the standard `python3` validation commands and report Phase 6 validation as not run in that environment. Do not fabricate validation success.

If a local JSON command fails, verify that the input shape matches the documented local forms and that review actions include `--actor`.

## 17. Acceptance Summary

Phase 7 operations are accepted when the validation commands pass locally, CLI learning commands remain local and actor-gated, semantic context remains reviewer-assist only, dashboard interactivity remains read-only, deterministic runtime remains authoritative, no runtime activation exists, and no parser/scoring/decision/recommendation behavior changes are introduced.
