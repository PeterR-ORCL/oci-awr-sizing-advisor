# Phase 7 Demo Walkthrough

## 1. Purpose

This walkthrough provides a safe Phase 7 demo flow. It shows validation, local learning CLI status, local outcome pattern mining, proposal-only candidate generation, optional semantic reviewer-assist context, actor-gated local review, dashboard learning visibility, dashboard interactivity, cross-screen propagation, and safety talking points.

The demo uses local JSON placeholders only. It does not require live DB, OCI, ADB, Oracle Agent Memory, semantic recall service, LLM, or network access.

## 2. Demo Preconditions

Start from a clean working tree on the Phase 7 documentation branch. Use local JSON files for memory, patterns, candidates, and semantic context. If example files do not exist, replace the sample paths below with local JSON paths.

Do not demo runtime activation, automatic parser updates, automatic scoring updates, automatic recommendation updates, approval/write controls, DB writes, or live semantic recall.

## 3. Validate Phase 7

Run:

```bash
python3 scripts/run_phase7_validation.py
```

Expected talking point: Phase 7 validates locally and deterministically, with no runtime activation and no live service dependencies.

## 4. Show Learning CLI Status

Run:

```bash
python3 scripts/awr_memory_cli.py learning status
```

Expected talking point: the CLI reports module availability, `runtime_influence=false`, no runtime activation, and deterministic runtime authority.

## 5. Mine Outcome Patterns From Local JSON

Run:

```bash
python3 scripts/awr_memory_cli.py learning patterns --input examples/phase7_memory_sample.json --json
```

If `examples/phase7_memory_sample.json` does not exist, replace it with a local memory-shaped JSON path. The input is local JSON only.

Expected talking point: outcome patterns are observational and are not learning candidates.

## 6. Generate Learning Candidates

Run:

```bash
python3 scripts/awr_memory_cli.py learning candidates --input examples/phase7_patterns_sample.json --json
```

If `examples/phase7_patterns_sample.json` does not exist, replace it with a local patterns JSON path.

Expected talking point: candidates are proposal-only, candidate-based, human-governed, and preserve `runtime_influence=false` and `requires_human_review=true`.

## 7. Attach Semantic Candidate Context

Run with local candidate and semantic JSON paths:

```bash
python3 scripts/awr_memory_cli.py learning semantic-context \
  --candidate-input examples/phase7_candidate_sample.json \
  --semantic-input examples/phase7_semantic_context_sample.json \
  --json
```

If these example files do not exist, replace them with local JSON paths.

Expected talking point: semantic context is reviewer-assist only and semantic context is non-authoritative. It is not source evidence and cannot change candidate status, confidence, source evidence, structured sources, or runtime influence.

## 8. Review Candidate Locally With Actor

Run:

```bash
python3 scripts/awr_memory_cli.py learning review --input examples/phase7_candidates_sample.json --candidate-id ... --action approve-for-implementation --actor reviewer@example.com --json
```

If `examples/phase7_candidates_sample.json` does not exist, replace it with a local candidates JSON path. Replace `...` with a real candidate ID from the local candidate output.

Expected talking point: approval means approved for implementation only. It is not runtime activation, not runtime integration, and not automatic learning.

## 9. Show Dashboard Learning Visibility

Open the generated dashboard already produced by the project workflow, if available, and navigate to the learning/governance/fleet areas. The dashboard should show learning candidates as read-only proposal/review context with visible safety markers.

Expected talking point: dashboard learning visibility is read-only and does not add approval controls or write controls.

## 10. Show Dashboard Interactivity Screens

Walk through Screen 1 through Screen 6 interactions that already exist in Phase 7H:

- Screen 1 governance/parser exploration.
- Screen 2 diagnostic exploration.
- Screen 3 control center.
- Screen 4 historical review exploration.
- Screen 5 recommendation/action exploration.
- Screen 6 fleet/governance/semantic/learning exploration.

Expected talking point: dashboard interactivity is read-only and exploratory.

## 11. Show Cross-Screen Propagation

Select an item on one screen and show how browser-side selection context appears on related screens. URL hash and localStorage state are convenience state only.

Expected talking point: cross-screen propagation does not change backend truth, candidate status, governance state, diagnostic truth, historical truth, recommendation truth, or parser output.

## 12. Safety Talking Points

Use these safety talking points during the demo:

- Deterministic runtime remains authoritative.
- Learning is candidate-based and human-governed.
- Learning candidates remain proposal/review context only.
- Semantic context is reviewer-assist only.
- Semantic context is non-authoritative.
- Dashboard interactivity is read-only.
- CLI learning commands are local and actor-gated.
- No runtime activation exists.
- No parser/scoring/decision/recommendation behavior changed.
- No backend writes, API calls, DB writes, network calls, Oracle Agent Memory calls, semantic recall service calls, or LLM calls are part of Phase 7K.

## 13. What Not To Demonstrate

Do not demonstrate autonomous learning, uncontrolled autonomous learning, automatic parser updates, automatic scoring updates, automatic recommendation updates, runtime activation, runtime self-modification, live DB persistence, live semantic recall, Oracle Agent Memory, OCI calls, ADB calls, LLM calls, dashboard approval controls, dashboard write controls, parser changes, scoring changes, decision changes, recommendation changes, generated dashboard HTML edits, or Phase 7L readiness/certification.

## 14. Acceptance Summary

The demo is accepted when it shows local validation, local CLI status, local pattern mining, proposal-only candidate generation, optional reviewer-assist semantic context, actor-gated local review, read-only dashboard learning visibility, read-only dashboard interactivity, cross-screen propagation, and the safety boundaries without claiming or performing runtime activation.
