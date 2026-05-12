# Phase 7H.8 Cross-Screen Selection Propagation

## 1. Purpose

Phase 7H.8 connects the read-only selectors added in Phase 7H.1 through Phase 7H.7 so selected dashboard state can be restored, summarized, and visually reflected across static dashboard pages. Cross-screen propagation is browser-side only, read-only, and exploratory only.

## 2. Scope

The scope is static-dashboard-compatible selection propagation. The dashboard may parse URL hash state, store the same bounded selector values in optional local storage, restore state on page load, preserve state on dashboard navigation links, highlight matching selectable elements, and update selected summary panels.

## 3. Non-Goals

Phase 7H.8 does not add backend writes, API calls, database calls, server-side state, network services, external JavaScript dependencies, approval controls, write controls, runtime activation, or Phase 7I CLI learning commands. It does not change parser output, diagnostic truth, historical truth, recommendation truth, governance state, candidate status, or any parser/scoring/decision/recommendation behavior. It does not change governance state and does not change candidate status.

## 4. Browser-Side State Model

The state model remains browser-side only. Selector values are short string identifiers used by rendered HTML metadata such as `data-dashboard-selectable`, `data-dashboard-select-key`, and `data-dashboard-filter-value`. URL hash/localStorage state is not authoritative truth.

## 5. Supported State Keys

The supported keys are `selectedAwr`, `selectedRun`, `selectedDb`, `selectedSystem`, `selectedSnapshot`, `selectedDomain`, `selectedSeverity`, `selectedRecommendation`, `selectedRecommendationCategory`, `selectedRecommendationEvidence`, `selectedEvidenceGroup`, `selectedMetricGroup`, `selectedWaitEventGroup`, `selectedSqlSignal`, `selectedDiagnosticSection`, `selectedHistoricalWindow`, `selectedTrendMetric`, `selectedAnomalyGroup`, `selectedDistribution`, `selectedSimilarCase`, `selectedActionContext`, `selectedOutcomeContext`, `selectedFeedbackContext`, `selectedParserSection`, `selectedParserDiagnostic`, `selectedUnknownSignal`, `selectedGovernanceItem`, `selectedKnowledgeRequest`, `selectedArtifact`, `selectedSemanticItem`, `selectedLearningCandidate`, `selectedLearningCandidateStatus`, `selectedLearningCandidateType`, `selectedOutcomePattern`, `selectedActionEffectivenessPattern`, `selectedFleetGroup`, and `selectedComparisonBaseline`.

## 6. URL Hash State

URL hash state may look like `#selectedDomain=CPU&selectedRun=run-001`. The parser accepts only supported keys, strips unsafe angle brackets, bounds value length, ignores unknown keys, avoids dynamic execution, and uses safe URL encoding. Hash state is convenience state only and does not persist to a backend.

## 7. Local Storage State

Local storage remains optional and uses the namespaced key `agenticAiAwrAdvisor.dashboardInteractivityState.v1`. If local storage is unavailable, the dashboard fails safely and still renders normally. Local storage does not store raw report content and is not authoritative truth.

## 8. Navigation Persistence

Dashboard navigation links may carry the current selected state forward by appending the encoded URL hash to static dashboard page links. This preserves selected values across static page navigation without a server, router, session store, API call, or backend persistence.

## 9. Visual Selected State

Matching selectable elements may receive the `is-selected` class, `data-selected="true"`, and `aria-selected="true"` when appropriate. Non-matching deterministic content remains visible; Phase 7H.8 does not hide diagnostic truth, historical truth, recommendation truth, parser truth, governance truth, semantic context, or learning context by default.

## 10. Selected Summary Panels

Selected summary panels on Screens 1 through 6 consume the shared browser-side state and continue to state that selections are read-only, exploratory only, no backend writes are performed, no API calls are made, URL hash/localStorage state is not authoritative truth, and selections do not change truth.

## 11. Safe Unknown State Handling

Unknown state keys are ignored. Known state values that have no matching element on a page may still appear in a selected summary, but they do not invent page content, mutate DOM truth, hide existing output, or create backend actions.

## 12. Static Dashboard Compatibility

The dashboard remains plain static HTML. Phase 7H.8 adds no React, Vue, npm, bundler, server route, session state, network dependency, database dependency, OCI dependency, ADB dependency, Oracle Agent Memory live dependency, semantic recall service dependency, or LLM dependency.

## 13. Screen 1 Propagation Behavior

Screen 1 may reflect `selectedRun`, `selectedAwr`, `selectedParserSection`, `selectedParserDiagnostic`, `selectedUnknownSignal`, `selectedGovernanceItem`, `selectedKnowledgeRequest`, and `selectedArtifact`. This does not change loader behavior, parser output, parser diagnostics, unknown signal classification, governance state, knowledge requests, or artifact lifecycle state.

## 14. Screen 2 Propagation Behavior

Screen 2 may reflect `selectedDomain`, `selectedEvidenceGroup`, `selectedMetricGroup`, `selectedWaitEventGroup`, `selectedSqlSignal`, and `selectedDiagnosticSection`. This does not change diagnostic truth, primary issue, secondary issues, severity, confidence, or deterministic evidence values.

## 15. Screen 3 Propagation Behavior

Screen 3 remains the primary read-only control center and may reflect `selectedAwr`, `selectedRun`, `selectedDb`, `selectedSystem`, `selectedSnapshot`, `selectedDomain`, `selectedSeverity`, and `selectedComparisonBaseline`. It does not switch backend output or make selected state authoritative.

## 16. Screen 4 Propagation Behavior

Screen 4 may reflect `selectedDomain`, `selectedHistoricalWindow`, `selectedTrendMetric`, `selectedAnomalyGroup`, `selectedDistribution`, `selectedSimilarCase`, and `selectedComparisonBaseline`. This does not change historical truth, recalculate trends, reclassify anomalies, change baselines, or recompute similarity results.

## 17. Screen 5 Propagation Behavior

Screen 5 may reflect `selectedRecommendation`, `selectedRecommendationCategory`, `selectedRecommendationEvidence`, `selectedActionContext`, `selectedOutcomeContext`, `selectedFeedbackContext`, and `selectedLearningCandidate`. This does not change recommendation truth, priority, rank, rationale, supporting evidence, action records, outcome records, feedback records, or candidate status.

## 18. Screen 6 Propagation Behavior

Screen 6 may reflect `selectedFleetGroup`, `selectedSystem`, `selectedAwr`, `selectedRun`, `selectedDomain`, `selectedGovernanceItem`, `selectedSemanticItem`, `selectedLearningCandidate`, `selectedLearningCandidateStatus`, `selectedLearningCandidateType`, `selectedOutcomePattern`, and `selectedActionEffectivenessPattern`. Semantic context remains reviewer-assist only, and learning candidates remain proposal/review context only.

## 19. Runtime Truth Boundary

Selections do not change runtime truth. Parser output, feature vectors, scoring, trend/anomaly results, decision logic, recommendation generation, recommendation ranking, and the Phase 4I output contract remain unchanged.

## 20. Parser / Loader Boundary

Selections do not change loader behavior, parser behavior, parser output, parser diagnostics, parser mappings, or unknown signal classification. No parser update controls are added.

## 21. Diagnostic Truth Boundary

Selections do not change diagnostic truth. Semantic context, learning candidates, governance state, and browser-side selections are not diagnostic evidence.

## 22. Historical Truth Boundary

Selections do not change historical truth. They do not recalculate trends, reclassify anomalies, change baselines, recompute similarity results, or convert semantic/learning context into historical evidence.

## 23. Recommendation Truth Boundary

Selections do not change recommendation truth. They do not change recommendation priority, rank, rationale, text, supporting evidence, action status, outcome status, or feedback status.

## 24. Governance State Boundary

Selections do not change governance state. They do not approve, reject, revise, validate, close, implement, or mutate governance records.

## 25. Candidate Status Boundary

Selections do not change candidate status. Learning candidates are not approved, rejected, implemented, validated, closed, applied, activated, or promoted into runtime behavior.

## 26. Semantic Context Boundary

Semantic context remains reviewer-assist only, non-authoritative, not diagnostic evidence, and not recommendation truth. Phase 7H.8 makes no semantic recall service calls and performs no Oracle Agent Memory calls.

## 27. Learning Candidate Boundary

Learning candidates remain proposal/review context only. They are not diagnostic evidence, not recommendation truth, not automatically applied, and not runtime activated. Existing `runtime_influence=false` and `requires_human_review=true` labels remain the governing display boundary.

## 28. Approval / Write-Control Boundary

Phase 7H.8 adds no approval controls, no reject controls, no implement controls, no validate controls, no close controls, no materialize controls, no activate controls, no apply controls, no parser update controls, no knowledge update controls, no candidate status mutation controls, and no governance status mutation controls.

## 29. Backend Persistence Boundary

Phase 7H.8 adds no backend writes, no API calls, no database calls, no network calls, no server-side session state, no backend state persistence, and no dashboard write paths. State remains browser-side only.

## 30. Relationship to Phase 7H.1 Foundation

Phase 7H.8 extends the Phase 7H.1 foundation by finalizing safe cross-screen selection propagation through existing state helpers, selected summaries, navigation hash preservation, local storage fallback, and visual selected-state behavior.

## 31. Relationship to Phase 7H.2 Screen 3 Control Center

Screen 3 remains the read-only control center. Phase 7H.8 lets its selected values persist to other static pages through browser-side state only.

## 32. Relationship to Phase 7H.3 Screen 2 Diagnostic Exploration

Screen 2 remains read-only deterministic evidence exploration. Phase 7H.8 may highlight matching existing Screen 2 selectors but does not change diagnostic truth.

## 33. Relationship to Phase 7H.4 Screen 4 Historical Review Exploration

Screen 4 remains read-only historical context exploration. Phase 7H.8 may highlight matching existing historical selectors but does not change historical truth.

## 34. Relationship to Phase 7H.5 Screen 5 Recommendation / Action Exploration

Screen 5 remains read-only recommendation/action exploration. Phase 7H.8 may highlight matching existing recommendation/action selectors but does not change recommendation truth or mutate action, outcome, or feedback records.

## 35. Relationship to Phase 7H.6 Screen 1 Governance / Parser Exploration

Screen 1 remains read-only governance/parser exploration. Phase 7H.8 may highlight matching existing parser/governance selectors but does not change parser output, unknown signal status, governance state, knowledge requests, or artifacts.

## 36. Relationship to Phase 7H.7 Screen 6 Fleet / Governance / Semantic / Learning Exploration

Screen 6 remains read-only fleet/governance/semantic/learning exploration. Phase 7H.8 may highlight matching existing Screen 6 selectors but does not change fleet posture, governance state, semantic authority, candidate status, diagnostic truth, or recommendation truth.

## 37. Relationship to Future Phase 7H.9 Validation / Docs

Future Phase 7H.9 may package broader validation and readiness documentation. Phase 7H.8 only implements and documents browser-side, read-only, static-dashboard-compatible cross-screen selection propagation.

## 38. Validation Requirements

Validation must prove import/compile safety, source markers, supported state keys, safe URL hash behavior, optional local storage behavior, visual selected-state behavior, selected summary updates, static navigation persistence, no unsafe controls, no backend dependencies, no truth drift, semantic/learning boundaries, existing Phase 7H.1 through Phase 7H.7 compatibility, Phase 7A through Phase 7G compatibility, and Phase 6 validation when the environment supports it.

## 39. Acceptance Criteria

Phase 7H.8 is accepted only if propagation is browser-side only, selections are read-only, selections are exploratory only, URL hash/localStorage state is not authoritative truth, no backend writes are added, no API calls are added, no approval controls are added, no write controls are added, no runtime activation is added, selections do not change parser output, selections do not change diagnostic truth, selections do not change historical truth, selections do not change recommendation truth, selections do not change governance state, selections do not change candidate status, semantic context remains reviewer-assist only, learning candidates remain proposal/review context only, no Phase 7I CLI learning commands are implemented, no runtime learning is implemented, deterministic runtime remains authoritative, and parser/scoring/decision/recommendation behavior is unchanged.
