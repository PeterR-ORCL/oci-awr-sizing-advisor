# Phase 7H.7 Screen 6 Fleet / Governance / Semantic / Learning Exploration

## 1. Purpose

Phase 7H.7 makes Screen 6 explorable through read-only selector metadata. It helps reviewers inspect fleet, governance, semantic reviewer-assist, and learning visibility context already shown on the static dashboard.

Screen 6 is read-only. Selections are exploratory only. They do not change fleet posture, governance state, parser output, unknown-signal classification, semantic authority, learning candidate truth, diagnostic truth, historical truth, recommendation truth, or runtime behavior.

The boundary wording is explicit: Screen 6 does not change fleet posture, does not change governance state, does not classify unknown signals, does not materialize artifacts, does not change diagnostic truth, and does not change recommendation truth.

## 2. Scope

The scope is a browser-side Screen 6 exploration surface. It may render selectable cards, update URL hash or local browser state through the Phase 7H.1 foundation, visually mark selected items, and update a selected Screen 6 summary.

No backend writes are added. No approval controls are added. No write controls are added. No runtime activation is added.

## 3. Non-Goals

Phase 7H.7 does not implement full cross-screen propagation, Phase 7I CLI learning commands, parser mapping updates, governance transitions, knowledge request creation, artifact materialization, semantic recall service calls, candidate generation, candidate status mutation, runtime learning, or parser/scoring/decision/recommendation behavior changes.

It does not approve, reject, revise, implement, validate, close, materialize, activate, apply, or persist anything.

## 4. Screen 6 Selector Categories

Screen 6 selector categories are fleet group, database/system, AWR/run, issue domain, governance item, parser unknown group, knowledge request, knowledge artifact, semantic reviewer-assist, learning candidate, learning candidate status/type, outcome pattern, and action effectiveness pattern selectors.

Each category appears only when deterministic, governed, or reviewer-assist display data is safely available. Empty categories show safe empty states.

## 5. Fleet Group Selector

The fleet group selector highlights fleet summary, cluster, similarity, rarity, repeated issue, backlog, and anomaly support context where rendered. It stores `selectedFleetGroup`.

Selections do not change fleet posture or scoring.

## 6. Database / System Selector

The database/system selector highlights current DB, DBID, instance, host, or similar-case system context where rendered. It stores `selectedDb` or `selectedSystem`.

Selections do not change fleet grouping or posture.

## 7. AWR / Run Selector

The AWR/run selector highlights current or similar-case AWR/run context where rendered. It stores `selectedAwr` or `selectedRun`.

Selections do not switch backend output and do not rerun analysis.

## 8. Issue Domain Selector

The issue domain selector exposes fixed authoritative domains: CPU, IO, MEMORY, COMMIT, RAC, and ADG. It stores `selectedDomain`.

Selections do not change primary issue, severity, score, or fleet posture.

## 9. Governance Item Selector

The governance item selector highlights existing governance summary or linkage context. It stores `selectedGovernanceItem`.

Selections do not change governance state, approval status, review status, or linkage records.

## 10. Parser Unknown Group Selector

The parser unknown group selector highlights existing unknown-signal summary context. It stores `selectedUnknownSignal`.

Selections do not classify unknown signals, map unknown signals, approve mappings, or reject mappings.

## 11. Knowledge Request Selector

The knowledge request selector highlights existing governed request context. It stores `selectedKnowledgeRequest`.

Selections do not create/update knowledge requests, submit requests, approve requests, reject requests, revise requests, validate requests, close requests, or activate requests.

## 12. Knowledge Artifact Selector

The knowledge artifact selector highlights existing artifact summary or linkage context. It stores `selectedArtifact`.

Selections do not materialize artifacts, activate artifacts, update artifacts, validate artifacts, or convert artifacts into runtime behavior.

## 13. Semantic Reviewer-Assist Selector

The semantic reviewer-assist selector highlights semantic recall status, assist scope, or latest semantic context summaries where rendered. It stores `selectedSemanticItem`.

Semantic context is reviewer-assist only. Semantic context is non-authoritative. Semantic context is not diagnostic evidence. Semantic context is not recommendation truth. The selector performs no semantic service calls and no Oracle Agent Memory calls.

## 14. Learning Candidate Selector

The learning candidate selector highlights learning candidates already visible on Screen 6. It stores `selectedLearningCandidate`.

Learning candidates are proposal/review context only. Learning candidates are not diagnostic evidence. Learning candidates are not recommendation truth. Candidate display keeps `runtime_influence=false` and `requires_human_review=true`.

## 15. Learning Candidate Status / Type Selector

The learning candidate status/type selector highlights status and type group counts. It stores `selectedLearningCandidateStatus` or `selectedLearningCandidateType`.

Selections do not mutate candidate status, candidate type, governance status, or runtime behavior.

## 16. Outcome Pattern Selector

The outcome pattern selector highlights outcome pattern groups when those records are already included in Screen 6 display data. It stores `selectedOutcomePattern`.

Pattern records are not candidates. Selections do not trigger candidate generation.

## 17. Action Effectiveness Pattern Selector

The action effectiveness pattern selector highlights action-effectiveness groups when already available. It stores `selectedActionEffectivenessPattern`.

Selections do not write action records, outcome records, feedback records, or recommendation truth.

## 18. Selected Screen 6 Summary

Screen 6 includes a selected Screen 6 summary labeled "Read-only fleet/governance/semantic/learning exploration." The summary is exploratory only and browser-local.

It states that there are no backend writes, no approval controls, no runtime activation, no fleet posture changes, no governance state changes, no unknown signal classification, no artifact materialization, no diagnostic truth changes, no recommendation truth changes, semantic context is reviewer-assist only, learning candidates are proposal/review context only, `runtime_influence=false`, and `requires_human_review=true`.

## 19. Safe Empty State Behavior

If selector metadata is unavailable, Screen 6 renders empty states rather than inventing fleet groups, semantic summaries, learning candidates, outcome patterns, systems, runs, governance rows, requests, or artifacts.

Safe empty states include "No fleet group selector available in this static export," "No semantic reviewer-assist groups available in this static export," "No learning candidates available in this static export," "No outcome pattern groups available in this static export," "Selection is local and read-only," and "Fleet, governance, semantic, and learning output remains unchanged."

## 20. URL Hash / Local State Behavior

Screen 6 uses the Phase 7H.1 foundation for URL hash and optional local storage state. Supported keys include `selectedFleetGroup`, `selectedDb`, `selectedSystem`, `selectedAwr`, `selectedRun`, `selectedDomain`, `selectedGovernanceItem`, `selectedUnknownSignal`, `selectedKnowledgeRequest`, `selectedArtifact`, `selectedSemanticItem`, `selectedLearningCandidate`, `selectedLearningCandidateStatus`, `selectedLearningCandidateType`, `selectedOutcomePattern`, and `selectedActionEffectivenessPattern`.

Hash and local storage changes are browser-side only. They do not write to a backend, database, API, memory store, governance store, semantic service, candidate store, or artifact store.

## 21. Runtime Truth Boundary

Selections do not change runtime truth. Deterministic runtime remains authoritative.

No runtime learning was implemented. Phase 7H.7 does not alter parser/scoring/decision/recommendation behavior.

## 22. Fleet Posture Boundary

Selections do not change fleet posture. They do not recalculate similarity, rewrite clusters, recalculate rarity, alter outliers, alter repeated issue grouping, alter anomaly support, or alter fleet scoring.

## 23. Governance State Boundary

Selections do not change governance state. They do not approve, reject, revise, implement, validate, close, or update governance records.

## 24. Parser Unknown Signal Boundary

Selections do not classify unknown signals. They do not map unknown signals, approve parser mappings, reject parser mappings, or update unknown-signal review state.

## 25. Knowledge Request Boundary

Selections do not create/update knowledge requests. They do not submit, approve, reject, revise, validate, close, or activate requests.

## 26. Artifact Materialization Boundary

Selections do not materialize artifacts. They do not activate artifacts, update lifecycle state, or use artifacts as runtime truth.

## 27. Semantic Context Boundary

Semantic context is reviewer-assist only. Semantic context is non-authoritative. Semantic context is not diagnostic evidence. Semantic context is not recommendation truth.

Selections do not turn semantic recall, semantic candidate context, or semantic summaries into parser truth, diagnostic truth, recommendation truth, scoring input, decision input, governance approval, or runtime activation.

## 28. Learning Candidate Boundary

Learning candidates are proposal/review context only. Learning candidates are not diagnostic evidence. Learning candidates are not recommendation truth.

Selections do not approve, reject, revise, implement, validate, close, activate, apply, rank for runtime use, or mutate learning candidates. `runtime_influence=false` and `requires_human_review=true` remain required display boundaries.

## 29. Outcome Pattern Boundary

Pattern records are not candidates. Outcome pattern selectors do not create learning candidates, trigger candidate generation, alter candidate status, alter action effectiveness records, or write action/outcome/feedback records.

## 30. Diagnostic Truth Boundary

Selections do not change diagnostic truth. Screen 6 fleet, governance, semantic, and learning exploration does not become Screen 2 diagnostic evidence and does not alter primary issue, severity, confidence, scoring, trend, anomaly, or evidence values.

## 31. Recommendation Truth Boundary

Selections do not change recommendation truth. Screen 6 exploration does not become Screen 5 recommendation evidence and does not alter recommendation text, priority, rank, rationale, action posture, or supporting evidence.

## 32. Approval / Write-Control Boundary

Phase 7H.7 adds no approval controls and no write controls. It adds no approval buttons, reject buttons, implement buttons, validate buttons, close buttons, materialize buttons, activate buttons, apply controls, parser update controls, knowledge update controls, candidate status mutation controls, governance status mutation controls, form posts, database calls, API write endpoints, network calls, OCI dependencies, ADB dependencies, Oracle Agent Memory live dependencies, semantic recall service dependencies, LLM calls, or CLI learning commands.

## 33. Cross-Screen Propagation Deferral

Full cross-screen propagation remains future 7H.8. Screen 6 may update browser-side selection state now, but other screens do not react authoritatively to Screen 6 selections in Phase 7H.7.

## 34. Relationship to Phase 7H.1 Foundation

Phase 7H.7 uses the Phase 7H.1 read-only foundation, including supported state keys, selector metadata hooks, URL hash state, optional local storage state, selected styling, and selected summary updates.

## 35. Relationship to Phase 7H.2 Screen 3 Control Center

Screen 3 remains a read-only control center. Phase 7H.7 does not make Screen 3 authoritative over Screen 6 and does not implement cross-screen propagation.

## 36. Relationship to Phase 7H.3 Screen 2 Diagnostic Exploration

Screen 2 remains deterministic diagnostic exploration only. Screen 6 selections do not become diagnostic evidence and do not change diagnostic truth.

## 37. Relationship to Phase 7H.4 Screen 4 Historical Review Exploration

Screen 4 remains deterministic historical context exploration only. Screen 6 selections do not change historical truth, trends, anomalies, baselines, or similarity results.

## 38. Relationship to Phase 7H.5 Screen 5 Recommendation / Action Exploration

Screen 5 remains deterministic/governed recommendation/action context exploration only. Screen 6 selections do not change recommendation truth or action/outcome/feedback records.

## 39. Relationship to Phase 7H.6 Screen 1 Governance / Parser Exploration

Screen 1 remains read-only governance/parser exploration only. Screen 6 selections do not change parser output, parser diagnostics, unknown signal classification, governance state, knowledge requests, or artifacts.

## 40. Relationship to Future 7H.8 Cross-Screen Selection Propagation

Full cross-screen propagation remains future 7H.8. Phase 7H.7 does not implement an active cross-screen selector synchronization layer, backend state persistence, dashboard write paths, or CLI learning commands.

## 41. Validation Requirements

Validation must prove import and compile safety, Screen 6 fleet/governance/semantic/learning exploration markers, selected Screen 6 summary markers, selector metadata for fleet/governance/semantic/learning categories, authoritative domain controls, required safety wording, absence of unsafe controls, absence of governance/candidate/artifact mutation, absence of semantic/learning evidence drift, absence of Screen 1, Screen 2, Screen 4, and Screen 5 truth drift, absence of 7H.8 behavior, existing 7H.1 through 7H.6 preservation, documentation coverage, Phase 7A-G preservation, and Phase 6 validation preservation when available.

Tests must be deterministic and local only. They must not require a database, OCI, ADB wallet, Oracle Agent Memory, environment variables, network, current date/time, or write access outside temporary directories.

## 42. Acceptance Criteria

Phase 7H.7 is accepted when Screen 6 Fleet / Governance / Semantic / Learning Exploration exists, Screen 6 has read-only fleet/governance/semantic/learning selector controls, Screen 6 uses Phase 7H.1 metadata hooks, Screen 6 includes selected Screen 6 summary, fleet/system/run/domain/governance/unknown/knowledge/artifact/semantic/learning/outcome-pattern selectors exist where safe deterministic, governed, or reviewer-assist data is available, safe empty states appear when metadata is unavailable, and selections remain browser-side and read-only.

It is also accepted only if selections are exploratory only, no backend writes are added, no approval controls are added, no write controls are added, no runtime activation is added, fleet posture is unchanged, governance state is unchanged, candidate status is unchanged, unknown signals are not classified, knowledge requests are not created/updated, artifacts are not materialized, diagnostic truth is unchanged, historical truth is unchanged, recommendation truth is unchanged, semantic context remains reviewer-assist only, semantic context is not diagnostic evidence, semantic context is not recommendation truth, learning candidates remain proposal/review context only, learning candidates are not diagnostic evidence, learning candidates are not recommendation truth, pattern records are not candidates, full cross-screen propagation remains future 7H.8, no 7H.8 cross-screen propagation is implemented, no runtime learning is implemented, deterministic runtime remains authoritative, and parser/scoring/decision/recommendation behavior is unchanged.
