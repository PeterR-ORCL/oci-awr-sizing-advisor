# Phase 7H.4 Screen 4 Historical Review Exploration

## 1. Purpose

Phase 7H.4 makes Screen 4 historical review content explorable through read-only browser-side selectors. The selectors help a user highlight deterministic historical context already rendered on Screen 4 without changing any runtime truth.

Screen 4 is read-only. Selections are exploratory only. They do not change historical truth, trend values, anomaly classifications, baseline values, similarity results, diagnostic truth, recommendation truth, parser output, scoring, trend/anomaly behavior, decisions, recommendations, Phase 4I output, semantic context, or learning candidate state. Screen 4 selection does not change historical truth, does not recalculate trends, does not reclassify anomalies, does not change baseline, does not change similarity results, does not change diagnostic truth, and does not change recommendation truth.

## 2. Scope

The scope is Screen 4 historical review exploration only. Screen 4 may render read-only selectors for historical domains, time windows, trend/metric groups, anomaly groups, violin/distribution domains, comparison baselines, similar historical cases, and current AWR/run context when deterministic dashboard data is available.

Selections may update browser-side selected state, selected styling, selected historical summary text, URL hash state, and optional local storage state through the Phase 7H.1 foundation.

## 3. Non-Goals

Phase 7H.4 does not implement Screen 5 recommendation/action exploration, Screen 1 governance/parser exploration, Screen 6 fleet/governance/semantic/learning exploration, full cross-screen propagation, or Phase 7I CLI learning commands.

It adds no backend writes, no approval controls, no write controls, no runtime activation, no parser changes, no scoring changes, no trend/anomaly changes, no decision changes, no recommendation changes, no Phase 4I contract changes, no API calls, no database calls, no network calls, no external frontend dependencies, no OCI dependency, no ADB dependency, no Oracle Agent Memory live dependency, no semantic recall service dependency, and no LLM calls.

## 4. Screen 4 Selector Categories

Screen 4 selector categories are historical domain, time window, trend/metric, anomaly group, violin/distribution, comparison baseline, similar case, and current AWR/run context where safe deterministic metadata is available.

If deterministic metadata is unavailable, Screen 4 shows a safe empty state. It does not invent trend data, anomaly groups, baseline values, distribution samples, or similar cases.

## 5. Historical Domain Selector

The Historical Domain Selector includes CPU, IO, MEMORY, COMMIT, RAC, and ADG. It stores read-only browser-side state in `selectedDomain`.

Domain selection does not change historical truth, trend values, anomaly classifications, baseline values, primary issue, severity, confidence, diagnostic truth, or recommendation truth.

## 6. Time Window Selector

The Time Window Selector uses deterministic window metadata already rendered or available to Screen 4, such as comparison window, current window, latest interval, worst interval, or snapshot label range. It stores browser-side state in `selectedHistoricalWindow`.

Window selection is read-only. It does not recalculate trends and does not re-window deterministic analysis.

## 7. Trend / Metric Selector

The Trend / Metric Selector uses rendered time-series groups or scalar metric groups already available to Screen 4. It stores browser-side state in `selectedTrendMetric`.

Trend selection is read-only. It does not recalculate metrics, scores, trend values, or diagnostic evidence.

## 8. Anomaly Selector

The Anomaly Selector uses deterministic anomaly review data already present in Screen 4. It stores browser-side state in `selectedAnomalyGroup`.

Anomaly selection is read-only. It does not reclassify anomalies and does not change anomaly burden.

## 9. Violin / Distribution Selector

The Violin / Distribution Selector uses rendered violin or distribution groups that already passed deterministic display gates. It stores browser-side state in `selectedDistribution`.

Distribution selection is read-only. It does not recalculate distributions and does not fabricate samples.

## 10. Baseline / Similar Case Selector

The Baseline / Similar Case Selector uses deterministic comparison context and similar-case rows already included in Screen 4 output. It stores browser-side state in `selectedComparisonBaseline` or `selectedSimilarCase`.

Baseline selection does not change baseline. Similar-case selection does not change similarity results and does not recompute nearest neighbors.

## 11. Selected Historical Summary

Screen 4 includes a visible selected historical summary labeled Read-only historical exploration. The summary is exploratory only and may be updated by browser-side JavaScript.

The summary states that selections do not change historical truth, do not recalculate trends, do not reclassify anomalies, do not change baseline, do not change similarity results, do not change diagnostic truth, and do not change recommendation truth. It also states that semantic/learning context is not historical evidence and that there are no backend writes.

## 12. Safe Empty State Behavior

When a selector category has no deterministic data, Screen 4 renders safe wording such as no additional historical windows available in this static export, no anomaly groups available in this static export, no similar-case selector available in this static export, selection is local and read-only, and historical output remains unchanged.

Safe empty states do not imply missing data is evidence. They do not fabricate trend data, anomaly groups, baseline values, distribution samples, or similar cases.

## 13. URL Hash / Local State Behavior

Screen 4 uses Phase 7H.1 metadata hooks such as `data-dashboard-selectable`, `data-dashboard-select-type`, `data-dashboard-select-key`, `data-dashboard-select-id`, `data-dashboard-select-domain`, `data-dashboard-filter-key`, and `data-dashboard-filter-value`.

The foundation supports `selectedDomain`, `selectedHistoricalWindow`, `selectedTrendMetric`, `selectedAnomalyGroup`, `selectedDistribution`, `selectedComparisonBaseline`, and `selectedSimilarCase` for Screen 4 exploration. URL hash and local storage state are browser-local only.

## 14. Runtime Truth Boundary

Screen 4 selections do not change runtime truth. Parser output, feature vectors, scoring, trends, anomalies, decisions, recommendations, Phase 4I output, and deterministic dashboard truth remain authoritative and unchanged.

No runtime learning is implemented.

## 15. Historical Evidence Boundary

Screen 4 selections do not change historical truth. They only highlight deterministic historical context already rendered or available to Screen 4.

Selections do not create historical evidence, promote contextual data into historical proof, or alter historical review conclusions.

## 16. Trend / Anomaly Boundary

Screen 4 selections do not recalculate trends and do not reclassify anomalies. Trend values, anomaly windows, anomaly burden, and anomaly labels remain deterministic output.

Browser-local selected state is not trend logic and is not anomaly logic.

## 17. Baseline / Similarity Boundary

Screen 4 selections do not change baseline and do not change similarity results. They do not recompute nearest neighbors, validate clusters, alter distances, alter similarity scores, or change comparison conclusions.

Similar-case rows remain deterministic or structured output already present in the export.

## 18. Diagnostic Truth Boundary

Screen 4 selections do not change diagnostic truth. They do not change primary issue, secondary issues, severity, confidence, evidence values, scoring, or Screen 2 diagnosis.

Historical context remains supporting context and does not override selected-scope diagnostic truth.

## 19. Recommendation Truth Boundary

Screen 4 selections do not change recommendation truth. They do not create, remove, rank, approve, activate, or rewrite recommendations.

Screen 5 recommendation truth remains downstream of deterministic recommendations only.

## 20. Learning / Semantic Boundary

Semantic/learning context is not historical evidence. Semantic recall, semantic candidate context, learning candidates, governance records, feedback, and outcome pattern records are not used to support Screen 4 historical truth.

Learning candidates remain proposal/review context only. Semantic context remains reviewer-assist only and cannot change historical conclusions.

## 21. Approval / Write-Control Boundary

Phase 7H.4 adds no approval controls and no write controls. It adds no approval buttons, reject buttons, implement buttons, validate buttons, close buttons, activate buttons, apply buttons, form posts, database calls, network calls, API write endpoints, CLI learning commands, OCI writes, ADB writes, or Oracle Agent Memory writes.

No backend writes are added.

## 22. Cross-Screen Propagation Deferral

Full cross-screen propagation remains future 7H.8. Screen 4 may update URL hash and local browser state through the Phase 7H.1 foundation, but Screen 2, Screen 3, Screen 5, Screen 1, and Screen 6 do not react authoritatively to Screen 4 selections in Phase 7H.4.

## 23. Relationship to Phase 7H.1 Foundation

Phase 7H.4 uses the Phase 7H.1 read-only dashboard interactivity foundation. It uses browser-side state keys, selectable metadata hooks, selected styling, selected summary updates, URL hash state, and optional local storage state.

The foundation remains static-dashboard-compatible, dependency-free, read-only, and exploratory only.

## 24. Relationship to Phase 7H.2 Screen 3 Control Center

Phase 7H.2 Screen 3 Control Center remains read-only and exploratory. Phase 7H.4 does not make Screen 3 selections authoritative and does not implement cross-screen propagation from Screen 3 into Screen 4.

Both screens can store browser-local state through the same foundation, but deterministic runtime truth remains unchanged.

## 25. Relationship to Phase 7H.3 Screen 2 Diagnostic Exploration

Phase 7H.3 Screen 2 Diagnostic Exploration remains read-only and deterministic evidence-only. Phase 7H.4 does not alter Screen 2 diagnostic truth, primary issue, severity, confidence, or diagnostic evidence.

Historical exploration on Screen 4 remains supporting context and does not override Screen 2.

## 26. Relationship to Future 7H.5-7H.8 Work

Future Phase 7H.5 through Phase 7H.7 work may add additional read-only screen-specific selectors. Full cross-screen propagation remains future 7H.8.

Phase 7H.4 does not implement Screen 5 recommendation/action exploration, Screen 1 governance/parser exploration, Screen 6 fleet/governance/semantic/learning exploration, or full cross-screen propagation.

## 27. Validation Requirements

Validation must prove import and compile safety, Screen 4 historical exploration markers, selected historical summary markers, selector metadata for historical domains and historical categories, authoritative domain controls, required safety wording, absence of unsafe controls, absence of semantic/learning/governance historical evidence, absence of Screen 2 and Screen 5 truth drift, absence of 7H.5+ behavior, existing 7H.1 through 7H.3 preservation, documentation coverage, Phase 7A-G preservation, and Phase 6 validation preservation when available.

Tests must be deterministic and local only. They must not require a database, OCI, ADB wallet, Oracle Agent Memory, environment variables, network, current date/time, or write access outside temporary directories.

## 28. Acceptance Criteria

Phase 7H.4 is accepted when Screen 4 Historical Review Exploration exists, Screen 4 has read-only historical selector controls, Screen 4 uses Phase 7H.1 foundation metadata hooks, Screen 4 includes selected historical summary, domain selectors include CPU, IO, MEMORY, COMMIT, RAC, and ADG, and historical window/trend/anomaly/distribution/similar-case selectors exist where safe deterministic data is available or safe empty states are shown.

It is also accepted only if selections are browser-side and read-only, selections are exploratory only, no backend writes are added, no approval controls are added, no write controls are added, no runtime activation is added, historical truth is unchanged, trends are not recalculated, anomalies are not reclassified, baseline is unchanged, similarity results are unchanged, diagnostic truth is unchanged, recommendation truth is unchanged, semantic/learning context is not historical evidence, learning candidates remain proposal/review context only, semantic context remains reviewer-assist only, full cross-screen propagation remains future 7H.8, no 7H.5+ screen-specific behavior is implemented, no runtime learning is implemented, deterministic runtime remains authoritative, and parser/scoring/decision/recommendation behavior is unchanged.
