# Phase 7AB CLI ML Visibility

## 1. Purpose

Phase 7AB adds local, deterministic CLI visibility for ML/adaptive explainability, model registry posture, and controlled runtime integration posture.

## 2. Scope

The scope is read-only `learning` namespace commands in `scripts/awr_memory_cli.py`. Commands accept optional local JSON input and render status without database, OCI, Oracle Agent Memory, semantic recall service, network, or environment variable requirements.

## 3. Non-Goals

The CLI does not write files, does not activate runtime, does not change registry/governance state, does not call live services, does not approve models, does not deploy models, does not execute rollback, and does not implement Phase 8 sizing/TCO.

## 4. CLI Command Summary

- `learning ml-status`
- `learning ml-explain`
- `learning ml-models`
- `learning adaptive-runtime-status`

## 5. learning ml-status

`learning ml-status` shows whether local ML/adaptive modules are present, including the ML boundary, feature/label dataset, trend-aware scoring, shadow ML interface, training/backtesting, explainability, model registry, runtime integration gate, runtime context, scoring adapter, recommendation adapter, parser adapter, and fallback layer.

## 6. learning ml-explain

`learning ml-explain` renders local ML explanation records from optional JSON input. Empty input returns a safe empty read-only result. ML explanations are not diagnostic evidence and are not recommendation truth.

## 7. learning ml-models

`learning ml-models` renders local model registry entries from optional JSON input. It shows model id, model family, governance status, shadow eligibility, runtime eligibility requested, runtime eligibility granted, runtime active, and runtime influence granted. Model registry visibility does not deploy models.

## 8. learning adaptive-runtime-status

`learning adaptive-runtime-status` renders local adaptive runtime gate/context/adapter/fallback visibility from optional JSON input. Runtime gate visibility does not activate runtime. Fallback visibility does not execute rollback.

## 9. Local JSON Input

Input is local JSON only. Explanation input may be a single object, a list, `{ "explanations": [...] }`, or `{ "ml_explanations": [...] }`. Model input may be a single object, a list, `{ "models": [...] }`, or `{ "model_registry_entries": [...] }`. Adaptive runtime input may include runtime context, gate results, scoring result, recommendation result, parser result, fallback decision, and readiness summary.

## 10. JSON Output

Every command supports `--json`. JSON output includes read-only flags, runtime safety flags, deterministic runtime authority, and normalized visibility rows.

## 11. Read-Only Boundary

CLI visibility is read-only. Commands do not write. Commands do not change registry/governance state. Commands do not mutate governance, registry, runtime config, runtime eligibility, or adaptive artifacts.

## 12. Runtime Activation Boundary

Commands do not activate runtime. Commands do not call live services. They keep `runtime_active=false`, `runtime_influence=false`, `runtime_influence_granted=false`, and `runtime_eligibility_granted=false`.

## 13. Dashboard Boundary

CLI visibility mirrors dashboard visibility but does not generate dashboard HTML, change dashboard truth, or create dashboard controls.

## 14. Validation Requirements

Validation must prove command help includes the new commands, empty input is safe, local JSON input is accepted, JSON output is valid, input files are not mutated, no unsafe dependencies are required, and no write or mutation commands are added.

## 15. Acceptance Criteria

Acceptance requires local/deterministic CLI visibility, safe empty states, no writes, no live service calls, no runtime activation, no registry/governance mutation, no rollback execution, and deterministic runtime remains authoritative.
