# Phase 7 Final Operational Checklist

## Purpose

This checklist defines the final Phase 7 operator flow for readiness validation and release certification.

## Pre-Run Checklist

- Confirm the branch is `phase7-controlled-runtime-integration`.
- Confirm the working tree is clean.
- Confirm no runtime activation, rollback execution, parser mutation, scoring mutation, decision mutation, or recommendation mutation is in scope.
- Use `.venv/bin/python` if system Python lacks `dotenv` or other project dependencies.

## Final Validation Checklist

Run:

```bash
python3 scripts/run_phase7_final_readiness_check.py
python3 scripts/run_phase7_final_readiness_check.py --json
```

Do not certify if validation fails.

## Learning Foundation Checklist

Run:

```bash
python3 scripts/run_phase7_readiness_check.py
```

Learning candidates must remain governed proposal/review records.

## Materialization Checklist

Run:

```bash
python3 scripts/run_phase7_materialization_readiness_check.py
```

Materialization artifacts must remain governed records and must not activate runtime influence.

## ML / Adaptive Scoring Checklist

Run:

```bash
python3 scripts/run_phase7_ml_readiness_check.py
```

ML outputs must remain shadow/advisory, and deterministic runtime remains authoritative.

## Runtime Integration Checklist

Run:

```bash
python3 scripts/run_phase7aa_runtime_integration_readiness_check.py
```

Adaptive runtime must remain gated, opt-in, default-deny, and inactive unless a future phase explicitly certifies activation.

## Dashboard / CLI Visibility Checklist

Run the dashboard and CLI validation commands:

```bash
python3 scripts/run_phase7h_dashboard_validation.py
.venv/bin/python scripts/awr_memory_cli.py learning validate --json
```

Dashboard and CLI visibility must remain read-only.

## Runtime Isolation Checklist

Confirm:

- `run_analysis.py` is not wired to Phase 7AA runtime modules.
- Parser/scoring/decision/recommendation runtime paths do not import Phase 7AA runtime modules.
- Runtime paths do not import Phase 7 ML modules for runtime execution.
- No rollback execution functions exist.
- No adaptive apply functions exist.

## Documentation Checklist

Confirm these documents exist:

- `docs/architecture/phase7_final_readiness.md`
- `docs/architecture/phase7_final_release_certification.md`
- `docs/architecture/phase7_final_operational_checklist.md`
- `docs/architecture/phase7_final_validation_matrix.md`

## Failure Handling

If any readiness command fails:

- Do not certify if validation fails.
- Do not treat readiness as runtime activation.
- Do not bypass runtime isolation boundaries.
- Do not modify runtime parser/scoring/decision/recommendation behavior to force readiness.
- Re-run validation after any scoped fix.

## Acceptance Checklist

Acceptance requires:

- `phase7_final_ready=true`.
- Deterministic runtime remains authoritative.
- Adaptive runtime remains gated.
- Runtime mutation remains absent.
- Phase 4I contract remains protected.
- Phase 8 is not implemented.

For full release signoff, also run:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_phase6_validation.py
```
