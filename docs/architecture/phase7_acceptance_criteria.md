# Phase 7 Acceptance Criteria

## 1. Purpose

This document defines the acceptance criteria for Phase 7 before Phase 7L readiness/certification work. It consolidates subphase completion, runtime isolation, learning safety, semantic boundaries, governance, dashboard behavior, CLI behavior, validation, documentation, and non-goals.

## 2. Acceptance Scope

Phase 7 acceptance covers Phase 7A through Phase 7K. It confirms that learning foundations, local operations, read-only dashboard exploration, CLI support, validation, and final documentation are complete while deterministic runtime truth remains unchanged.

Phase 7 acceptance is not Phase 7L production readiness/certification.

## 3. Required Completed Subphases

Phase 7 acceptance requires completion of:

- Phase 7A Learning Boundary Definition.
- Phase 7B Outcome Pattern Mining.
- Phase 7C Learning Candidate Model.
- Phase 7D Candidate Generation Engine.
- Phase 7E Semantic Candidate Context.
- Phase 7F Learning Governance Bridge.
- Phase 7G Dashboard Learning Visibility.
- Phase 7H Dashboard Interactivity.
- Phase 7H.x Dashboard Pylance / Static Typing Cleanup.
- Phase 7I CLI Learning Commands.
- Phase 7J Validation Harness.
- Phase 7K Documentation Finalization.

## 4. Runtime Isolation Criteria

Phase 7 is accepted only if deterministic runtime remains authoritative, no runtime activation exists, parser/scoring/decision/recommendation runtime paths remain isolated, `scripts/run_analysis.py` remains protected, and Phase 7 learning modules are not imported by runtime truth paths.

No parser behavior, parser output, loader behavior, scoring logic, scoring weights, trend/anomaly logic, decision logic, recommendation logic, recommendation ranking, or Phase 4I output contract changes may be introduced by Phase 7K.

## 5. Learning Safety Criteria

Learning must remain candidate-based and human-governed. Candidates must remain proposal/review context only until approved and implemented separately.

Candidate records must preserve `runtime_influence=false` and `requires_human_review=true`. Pattern records must not become candidates automatically. Candidate generation must not approve, implement, persist, materialize, activate, or apply candidates.

## 6. Semantic Boundary Criteria

Semantic context remains reviewer-assist only. Semantic context is non-authoritative, optional, not source evidence, not deterministic evidence, and not approval evidence.

Semantic context must not change candidate confidence, candidate status, candidate type, source evidence, structured sources, runtime influence, parser output, diagnostic truth, historical truth, recommendation truth, or governance state.

## 7. Governance Criteria

Governance remains human-governed and actor-gated. Candidate review transitions require explicit actor attribution where state changes are requested.

Approval means approved for implementation only. Approval is not runtime activation, runtime integration, automatic learning, or backend write permission.

## 8. Dashboard Criteria

Dashboard learning visibility must remain read-only. Dashboard interactivity remains read-only. Dashboard controls must not add approval controls, write controls, backend writes, API calls, candidate status mutation, governance mutation, diagnostic truth mutation, historical truth mutation, recommendation truth mutation, or parser output mutation.

Learning candidates must remain out of diagnostic evidence and recommendation truth.

## 9. CLI Criteria

CLI learning commands remain local and actor-gated. They operate on local JSON inputs and local deterministic module outputs.

The CLI must not write to Oracle DB, require OCI, require ADB, require Oracle Agent Memory, require a semantic recall service, call an LLM, call a network service, or activate runtime behavior.

## 10. Validation Criteria

Phase 7 is accepted only if:

- Phase 7 validation harness passes.
- Phase 7H dashboard validation passes.
- Phase 7I CLI validation passes.
- Phase 6 validation passes where environment supports it.
- Documentation finalization tests pass.

Required commands are listed below.

## 11. Documentation Criteria

Phase 7 final documentation must include:

- Phase 7 Learning Architecture.
- Phase 7 Operational Model.
- Phase 7 Component Inventory.
- Phase 7 Repository Map.
- Phase 7 Release Notes.
- Phase 7 Demo Walkthrough.
- Phase 7 Acceptance Criteria.

The architecture README must link the final Phase 7K documents.

## 12. Non-Goals Confirmation

Phase 7 acceptance confirms no autonomous learning, no uncontrolled autonomous learning, no automatic parser updates, no automatic scoring updates, no automatic recommendation updates, no runtime activation, no parser/scoring/decision/recommendation behavior changes, no generated dashboard HTML edits for Phase 7K, no backend writes added by Phase 7K, no API calls added by Phase 7K, and no Phase 7L readiness/certification implementation.

## 13. Required Commands Before Readiness

Run these commands before Phase 7L readiness/certification:

```bash
python3 -m py_compile tests/test_phase7_documentation_finalization.py
python3 -m unittest tests/test_phase7_documentation_finalization.py
python3 scripts/run_phase7_validation.py
python3 scripts/run_phase7_validation.py --json
python3 scripts/run_phase7h_dashboard_validation.py
python3 scripts/awr_memory_cli.py learning validate --json
python3 -m unittest tests/test_learning_cli_commands.py
```

Run Phase 6 validation where the environment supports it:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_phase6_validation.py
```

Also run:

```bash
git diff --check
```

## 14. Phase 7 Acceptance Statement

Phase 7 is accepted when the required subphases are complete, final documentation is linked, validation gates pass, Phase 6 validation passes where environment supports it, deterministic runtime remains authoritative, no runtime activation exists, no parser/scoring/decision/recommendation behavior changes are introduced, learning remains candidate-based and human-governed, semantic context remains reviewer-assist only, dashboard interactivity remains read-only, and CLI learning commands remain local and actor-gated.
