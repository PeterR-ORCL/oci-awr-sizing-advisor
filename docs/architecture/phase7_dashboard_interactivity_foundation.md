# Phase 7H.1 Dashboard Interactivity Foundation

## 1. Purpose

Phase 7H.1 establishes a lightweight browser-side foundation for future static dashboard interactivity. The foundation provides read-only selection state, safe selector metadata conventions, optional URL hash state, optional local storage state, and small rendering hooks that later Phase 7H subtasks can reuse.

Dashboard interactivity is read-only and exploratory only. It does not change backend truth, deterministic runtime truth, diagnostic truth, recommendation truth, governed memory state, semantic context, or learning candidate state. It does not change diagnostic truth and does not change recommendation truth.

## 2. Scope

The scope is the reusable foundation only. It may define state keys, parse and write URL hash state, persist browser-local selection state, mark selected DOM elements, update optional selected-state summary text, and mark read-only filter placeholders.

The dashboard remains static HTML. The foundation has no server requirement, no build step, no external JavaScript dependency, no database dependency, no API dependency, no network dependency, no OCI dependency, no ADB dependency, no Oracle Agent Memory live dependency, no semantic recall service dependency, and no LLM dependency.

## 3. Non-Goals

Phase 7H.1 does not implement Phase 7H.2 Screen 3 Control Center, Phase 7H.3 Screen 2 diagnostic exploration, Phase 7H.4 Screen 4 historical review exploration, Phase 7H.5 Screen 5 recommendation/action exploration, Phase 7H.6 Screen 1 governance/parser exploration, Phase 7H.7 Screen 6 fleet/governance/semantic/learning exploration, Phase 7H.8 cross-screen propagation, or Phase 7I CLI learning commands.

It does not add approval controls, reject controls, implement controls, validate controls, close controls, activate controls, apply controls, form posts, API write endpoints, database writes, backend mutation, runtime activation, autonomous learning, parser changes, scoring changes, trend/anomaly changes, decision changes, recommendation changes, or Phase 4I output contract changes.

## 4. Read-Only State Model

The state model is browser-side only. It may live in the URL hash and, when available, local storage under a dashboard-specific key. The state is limited to string identifiers for selected dashboard concepts.

Selections are exploratory only. They may affect browser-visible selection styling or optional read-only summaries, but they cannot mutate embedded source data, backend artifacts, parser output, feature vectors, scoring, trends, anomalies, decisions, recommendations, learning candidates, semantic context, governance records, or memory artifacts.

## 5. Supported State Keys

The Phase 7H.1 foundation supports these state keys for future use: `selectedAwr`, `selectedRun`, `selectedDb`, `selectedSystem`, `selectedSnapshot`, `selectedDomain`, `selectedSeverity`, `selectedRecommendation`, `selectedRecommendationCategory`, `selectedRecommendationEvidence`, `selectedEvidenceGroup`, `selectedMetricGroup`, `selectedWaitEventGroup`, `selectedSqlSignal`, `selectedDiagnosticSection`, `selectedHistoricalWindow`, `selectedTrendMetric`, `selectedAnomalyGroup`, `selectedDistribution`, `selectedSimilarCase`, `selectedActionContext`, `selectedOutcomeContext`, `selectedFeedbackContext`, `selectedParserSection`, `selectedParserDiagnostic`, `selectedUnknownSignal`, `selectedGovernanceItem`, `selectedKnowledgeRequest`, `selectedArtifact`, `selectedSemanticItem`, `selectedLearningCandidate`, `selectedLearningCandidateStatus`, `selectedLearningCandidateType`, `selectedOutcomePattern`, `selectedActionEffectivenessPattern`, `selectedFleetGroup`, and `selectedComparisonBaseline`.

For Phase 7H.1 these keys are defined and safely handled only. They do not drive full screen-specific behavior.

## 6. URL Hash State

URL hash state is optional and read-only from the backend perspective. A browser may represent state as hash parameters such as `#selectedDomain=CPU&selectedSeverity=HIGH`.

The hash parser accepts only supported state keys, trims values, bounds value length, strips angle brackets, ignores unsupported keys, and falls back safely on invalid input. Updating the hash does not write to the backend and does not change deterministic runtime truth.

## 7. Optional Local Storage State

The foundation may persist the same supported state keys to local storage under a dedicated dashboard key. This is browser-local convenience state only.

If local storage is unavailable, blocked, or invalid, the dashboard still renders normally. Local storage state does not approve, activate, validate, close, apply, implement, or reject anything.

## 8. Selectable Element Metadata

Future Phase 7H subtasks may opt into read-only selection behavior by adding metadata such as `data-dashboard-selectable`, `data-dashboard-select-type`, `data-dashboard-select-id`, `data-dashboard-select-domain`, `data-dashboard-target`, `data-dashboard-filter-key`, and `data-dashboard-filter-value`.

The foundation attaches click behavior only to elements marked as dashboard selectable. It does not introduce write controls. It may add `is-selected`, `data-selected`, `aria-selected`, or read-only filter activity markers to the DOM.

## 9. Progressive Enhancement Rules

The dashboard content must remain visible and usable if JavaScript fails. No core diagnostic truth, recommendation truth, parser finding, scoring result, historical conclusion, learning record, semantic context, or governance state depends on JavaScript.

If no selectable metadata exists, the foundation safely does nothing. Static pages remain valid plain HTML files.

## 10. Runtime Truth Boundary

Phase 7H.1 does not change runtime truth. Parser output, feature vectors, scoring, trends, anomalies, decisions, recommendations, Phase 4I output, and deterministic dashboard truth remain authoritative and unchanged.

No runtime learning was implemented. The deterministic runtime remains authoritative.

## 11. Diagnostic Evidence Boundary

Selections do not change diagnostic truth. They do not convert semantic context, learning candidates, historical neighbors, fleet groups, governance state, or browser-local state into diagnostic evidence.

Screen 2 diagnostic evidence remains downstream of deterministic runtime analysis only. Screen-specific diagnostic selection behavior is future work.

## 12. Recommendation Truth Boundary

Selections do not change recommendation truth. They do not convert learning candidates, semantic context, governance state, fleet similarity, or browser-local selections into recommendation evidence, recommendation objects, or action truth.

Screen 5 recommendation truth remains downstream of deterministic recommendations only.

## 13. Learning Candidate Boundary

Learning candidates remain review/proposal context only. The foundation does not approve, reject, implement, validate, close, activate, apply, rank for runtime use, or materialize learning candidates.

`runtime_influence=false` remains the required learning candidate display boundary. Phase 7H.1 does not set `runtime_influence=true`.

## 14. Semantic Context Boundary

Semantic context remains reviewer-assist only. The foundation does not turn semantic recall or semantic candidate context into source evidence, diagnostic evidence, recommendation truth, scoring input, or runtime truth.

Semantic context remains non-authoritative and cannot change confidence, status, diagnosis, recommendation, or governance state.

## 15. Approval / Write-Control Boundary

Phase 7H.1 adds no approval controls and no write controls. It adds no approval buttons, reject buttons, implement buttons, validate buttons, close buttons, activate buttons, apply buttons, form posts, database calls, network calls, API write endpoints, CLI learning commands, OCI writes, ADB writes, or Oracle Agent Memory writes.

No backend writes are added.

## 16. Screen-Specific Deferral Boundary

Screen-specific selection behavior is future work. Phase 7H.1 only creates the shared foundation so later subtasks can add controlled metadata and screen-specific read-only behavior.

It does not implement a full Screen 3 control center, diagnostic drilldown, historical comparison selector, recommendation/action selector, governance/parser selector, fleet selector, semantic selector, learning candidate selector experience, or full cross-screen propagation.

## 17. Relationship to Phase 7G Dashboard Learning Visibility

Phase 7G added read-only Screen 6 learning visibility. Phase 7H.1 preserves that boundary.

Learning candidates remain review/proposal context only. They are not diagnostic evidence, not recommendation truth, not automatically applied, and not runtime activated. Phase 7H.1 does not add approval controls or write controls to Phase 7G learning visibility.

## 18. Relationship to Future Phase 7H.2 Screen 3 Control Center

Phase 7H.2 may use the foundation to build the Screen 3 Control Center in a controlled later subtask. Phase 7H.1 does not implement that control center.

Any future Screen 3 behavior must remain read-only unless a later approved phase explicitly changes the boundary.

## 19. Relationship to Future Phase 7H.3-7H.8 Screen-Specific Work

Future Phase 7H.3 through Phase 7H.7 subtasks may add screen-specific exploratory behavior by applying the metadata hooks to selected dashboard elements. Full cross-screen propagation is future 7H.8 work.

Phase 7H.6 uses the foundation state keys for read-only Screen 1 governance/parser exploration, including `selectedParserSection`, `selectedParserDiagnostic`, `selectedUnknownSignal`, `selectedGovernanceItem`, `selectedKnowledgeRequest`, and `selectedArtifact`. These keys remain browser-side only and do not change parser output, classify unknown signals, approve mappings, materialize artifacts, create/update knowledge requests, or change governance state.

Phase 7H.7 uses the foundation state keys for read-only Screen 6 fleet/governance/semantic/learning exploration, including `selectedFleetGroup`, `selectedSemanticItem`, `selectedLearningCandidate`, `selectedLearningCandidateStatus`, `selectedLearningCandidateType`, `selectedOutcomePattern`, and `selectedActionEffectivenessPattern`. These keys remain browser-side only and do not change fleet posture, governance state, semantic authority, candidate status, diagnostic truth, recommendation truth, or runtime activation.

Phase 7H.1 only defines the reusable browser-side foundation and guardrails.

## 20. Validation Requirements

Validation must prove import and compile safety, foundation script presence, state key presence, selectable metadata hook presence, read-only safety wording, absence of unsafe write controls, absence of runtime import drift, Phase 7G learning visibility preservation, absence of Phase 7H.2+ screen-specific behavior, static dashboard compatibility, and documentation boundary coverage.

Tests must be deterministic and local only. They must not require a database, OCI, ADB wallet, Oracle Agent Memory, environment variables, network, current date/time, or write access outside temporary directories.

## 21. Acceptance Criteria

Phase 7H.1 is accepted when the dashboard includes the Dashboard Interactivity Foundation, read-only selection state, supported state keys, URL hash state handling, optional local storage state handling, selectable metadata hooks, safe empty behavior, progressive enhancement behavior, and boundary wording.

It is also accepted only if selections are exploratory only, no backend writes are added, no approval controls are added, no write controls are added, no runtime activation is added, diagnostic truth is unchanged, recommendation truth is unchanged, learning candidates remain review/proposal context only, semantic context remains reviewer-assist only, screen-specific selection behavior is future work, full cross-screen propagation is future 7H.8, no runtime learning is implemented, deterministic runtime remains authoritative, and parser/scoring/decision/recommendation behavior is unchanged.
