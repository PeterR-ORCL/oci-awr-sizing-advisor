# Phase 7H.3 Screen 2 Diagnostic Exploration

## 1. Purpose

Phase 7H.3 makes Screen 2 diagnostic content explorable through read-only browser-side selectors. The selectors help a user highlight deterministic evidence already rendered on Screen 2 without changing any runtime truth.

Screen 2 is read-only. Selections are exploratory only. They do not change diagnostic truth, primary issue, secondary issues, severity, confidence, recommendation truth, parser output, scoring, trend/anomaly behavior, decisions, recommendations, Phase 4I output, semantic context, or learning candidate state. Screen 2 selection does not change diagnostic truth, does not change primary issue, does not change severity, does not change confidence, and does not change recommendation truth.

## 2. Scope

The scope is Screen 2 diagnostic exploration only. Screen 2 may render read-only selectors for diagnostic domains, evidence groups, metric/score groups, wait event groups, SQL signal groups, deterministic diagnostic sections, and current AWR/run context when deterministic dashboard data is available.

Selections may update browser-side selected state, selected styling, selected diagnostic summary text, URL hash state, and optional local storage state through the Phase 7H.1 foundation.

## 3. Non-Goals

Phase 7H.3 does not implement Screen 4 historical exploration, Screen 5 recommendation/action exploration, Screen 1 governance/parser exploration, Screen 6 fleet/governance/semantic/learning exploration, full cross-screen propagation, or Phase 7I CLI learning commands.

It adds no backend writes, no approval controls, no write controls, no runtime activation, no parser changes, no scoring changes, no trend/anomaly changes, no decision changes, no recommendation changes, no Phase 4I contract changes, no API calls, no database calls, no network calls, no external frontend dependencies, no OCI dependency, no ADB dependency, no Oracle Agent Memory live dependency, no semantic recall service dependency, and no LLM calls.

## 4. Screen 2 Selector Categories

Screen 2 selector categories are diagnostic domain, evidence group, metric/score group, wait event group, SQL signal group, deterministic diagnostic section, and current AWR/run context.

If deterministic metadata is unavailable, Screen 2 shows a safe empty state. It does not invent wait events, SQL signals, metric values, evidence groups, or scores.

## 5. Diagnostic Domain Selector

The Diagnostic Domain Selector includes CPU, IO, MEMORY, COMMIT, RAC, and ADG. It stores read-only browser-side state in `selectedDomain`.

Domain selection does not change diagnostic truth, primary issue, secondary issues, severity, confidence, evidence values, scoring, or recommendations.

## 6. Evidence Group Selector

The Evidence Group Selector uses deterministic diagnostic driver rows already available on Screen 2. It stores browser-side state in `selectedEvidenceGroup`.

Evidence selection only highlights deterministic evidence. It does not create new evidence and does not change existing evidence values.

## 7. Metric / Score Group Selector

The Metric / Score Group Selector uses deterministic score or visual-summary metric groups already rendered or available to Screen 2. It stores browser-side state in `selectedMetricGroup`.

Metric selection is read-only. It performs no recalculation and does not change scoring.

## 8. Wait Event Selector

The Wait Event Selector uses deterministic wait event data if present in the static export, plus already-rendered deterministic commit/RAC wait signals when present. It stores browser-side state in `selectedWaitEventGroup`.

Wait event selection is read-only and does not reclassify waits.

## 9. SQL Signal Selector

The SQL Signal Selector uses deterministic SQL signal data when present in the static export. It stores browser-side state in `selectedSqlSignal`.

SQL signal selection is read-only. It does not change SQL ranking, SQL evidence, recommendations, or diagnostic truth.

## 10. Selected Diagnostic Summary

Screen 2 includes a visible selected diagnostic summary labeled Read-only diagnostic exploration. The summary is exploratory only and may be updated by browser-side JavaScript.

The summary states that selections do not change diagnostic truth, primary issue, severity, confidence, or recommendation truth. It also states that semantic/learning context is not diagnostic evidence and that there are no backend writes.

## 11. Safe Empty State Behavior

When a selector category has no deterministic data, Screen 2 renders safe wording such as no additional evidence groups available in this static export, selection is local and read-only, and diagnostic output remains unchanged.

Safe empty states do not imply missing data is evidence. They do not fabricate metrics, wait events, SQL signals, or diagnostic groups.

## 12. URL Hash / Local State Behavior

Screen 2 uses Phase 7H.1 metadata hooks such as `data-dashboard-selectable`, `data-dashboard-select-type`, `data-dashboard-select-key`, `data-dashboard-select-id`, `data-dashboard-select-domain`, `data-dashboard-filter-key`, and `data-dashboard-filter-value`.

The foundation supports `selectedDomain`, `selectedEvidenceGroup`, `selectedMetricGroup`, `selectedWaitEventGroup`, `selectedSqlSignal`, `selectedDiagnosticSection`, `selectedAwr`, and `selectedSeverity` for Screen 2 exploration. URL hash and local storage state are browser-local only.

## 13. Runtime Truth Boundary

Screen 2 selections do not change runtime truth. Parser output, feature vectors, scoring, trends, anomalies, decisions, recommendations, Phase 4I output, and deterministic dashboard truth remain authoritative and unchanged.

No runtime learning is implemented.

## 14. Diagnostic Evidence Boundary

Selections do not change diagnostic truth. Selections do not create, remove, relabel, rank, or modify diagnostic evidence.

Screen 2 diagnostic evidence remains deterministic Phase 4I-derived evidence only.

## 15. Primary Issue Boundary

Selections do not change primary issue. Domain, evidence, metric, wait, SQL, and diagnostic-section selectors are exploration controls only and cannot alter the primary issue or secondary issues.

## 16. Severity / Confidence Boundary

Selections do not change severity and do not change confidence. They do not modify severity score, display severity, risk label, confidence score, confidence label, or confidence explanation.

## 17. Recommendation Truth Boundary

Selections do not change recommendation truth. Screen 2 exploration state is not recommendation evidence and does not alter Screen 5 recommendation objects, action guidance, or recommendation labels.

## 18. Learning / Semantic Boundary

Semantic/learning context is not diagnostic evidence. Semantic recall, semantic candidate context, learning candidates, governance records, and feedback records are not used as Screen 2 diagnostic evidence.

Learning candidates remain proposal/review context only. Semantic context remains reviewer-assist only.

## 19. Approval / Write-Control Boundary

Phase 7H.3 adds no approval controls and no write controls. It adds no approval buttons, reject buttons, implement buttons, validate buttons, close buttons, activate buttons, apply buttons, form posts, API write endpoints, database writes, network writes, CLI learning commands, OCI writes, ADB writes, or Oracle Agent Memory writes.

No backend writes are added.

## 20. Cross-Screen Propagation Deferral

Full cross-screen propagation remains future 7H.8. Screen 2 may update browser-side URL hash/local state now, but other screens do not react to Screen 2 selections in Phase 7H.3.

## 21. Relationship to Phase 7H.1 Foundation

Phase 7H.1 provided the read-only dashboard interactivity foundation. Phase 7H.3 extends the foundation state model with Screen 2 diagnostic exploration keys and uses the same safe metadata hooks.

The foundation remains browser-side only and read-only.

## 22. Relationship to Phase 7H.2 Screen 3 Control Center

Phase 7H.2 made Screen 3 a read-only control center. Phase 7H.3 applies the same safety model to Screen 2 diagnostic evidence exploration.

Neither Screen 3 nor Screen 2 selection state changes deterministic runtime truth.

## 23. Relationship to Future 7H.4-7H.8 Work

Future Phase 7H.4 through Phase 7H.7 may add screen-specific read-only exploration to other screens. Full cross-screen propagation remains future 7H.8.

Phase 7H.3 does not implement 7H.4+ behavior.

## 24. Validation Requirements

Validation must prove import and compile safety, Screen 2 Diagnostic Exploration markers, selected diagnostic summary markers, selector metadata hooks, authoritative domain choices, safety labels, absence of unsafe controls, absence of semantic/learning diagnostic evidence, absence of Screen 5 recommendation truth drift, absence of 7H.4+ implementation, and documentation boundary phrases.

Tests must be deterministic and local only. They must not require a database, OCI, ADB wallet, Oracle Agent Memory, environment variables, network, current date/time, or writes outside temporary directories.

## 25. Acceptance Criteria

Phase 7H.3 is accepted when Screen 2 includes read-only diagnostic selector controls, uses Phase 7H.1 foundation metadata hooks, includes a selected diagnostic summary, includes CPU, IO, MEMORY, COMMIT, RAC, and ADG domain selectors, includes deterministic evidence/metric/wait/SQL selectors where safe data exists or safe empty states where data is unavailable, and preserves all runtime truth boundaries.

It is accepted only if selections are exploratory only, no backend writes are added, no approval controls are added, no write controls are added, no runtime activation is added, diagnostic truth is unchanged, primary issue is unchanged, secondary issues are unchanged, severity is unchanged, confidence is unchanged, recommendation truth is unchanged, semantic/learning context is not diagnostic evidence, learning candidates remain proposal/review context only, semantic context remains reviewer-assist only, full cross-screen propagation remains future 7H.8, no 7H.4+ screen behavior is implemented, deterministic runtime remains authoritative, and parser/scoring/decision/recommendation behavior is unchanged.
