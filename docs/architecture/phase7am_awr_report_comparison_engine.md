# Phase 7AM.1 AWR / Report Comparison Engine

## 1. Purpose

Phase 7AM.1 defines a local deterministic AWR / Report Comparison Engine for supplied in-memory report/run summary payloads.

The comparison engine creates a comparison artifact from already-provided dictionaries only.

## 2. Scope

The scope is in-memory comparison of two or more supplied report/run summary payloads.

The comparison artifact can describe compared report count, run ids, AWR ids, baseline/target references, score differences, wait/event differences, SQL concentration differences, trend differences, anomaly differences, topology differences, platform/target/source-option differences, data availability differences, likely drivers, limitations, and safety flags.

## 3. Non-Goals

No AWR files are read.

No parser is called.

No DB is queried.

No object storage is called.

No LLM is used.

The comparison engine does not parse reports, call `run_analysis.py`, call network services, generate dashboards, write artifacts, mutate Phase 4I, change scoring, change recommendations, implement missing metric handling, or implement Phase 8 sizing/TCO.

## 4. In-Memory Comparison Only

Comparison is based only on supplied in-memory payloads.

The engine accepts dictionaries already provided by caller/test code. It does not fetch, read, infer, enrich, parse, or validate external report content.

## 5. Comparison Input Shape

Each supplied report/run summary may include:

- `run_id`
- `awr_id`
- `dbid`
- `database_name`
- `snapshot_label`
- `platform_target`
- `target_platform`
- `source_options`
- `scores`
- `domain_scores`
- `waits`
- `wait_events`
- `sql_concentration`
- `top_sql_concentration`
- `trends`
- `anomalies`
- `topology`
- `metrics`
- `data_availability`
- `missing_metrics`

Flexible keys are allowed, but unsupported facts are not fabricated.

## 6. Compared Dimensions

The comparison engine compares supplied values across:

- score posture
- wait/event posture
- SQL concentration
- trends
- anomalies
- topology
- platform/target/source options
- data availability

Comparison requires at least two supplied payloads.

## 7. Score Differences

Score differences are computed deterministically where numeric score fields are present.

The baseline value is compared to each target value. Missing values are recorded as data availability differences, not fabricated as zero.

## 8. Wait/Event Differences

Wait/event differences are computed from supplied `waits` and `wait_events` maps.

Only provided numeric or comparable values are compared. Missing values are recorded as data availability differences.

## 9. SQL Concentration Differences

SQL concentration differences are computed from supplied `sql_concentration` and `top_sql_concentration` maps.

The engine preserves supplied values and reports deterministic changes without interpreting SQL text or querying workload repositories.

## 10. Trend Differences

Trend differences are computed from supplied `trends` metadata.

Numeric trend values may produce numeric differences. Non-numeric values are reported as changed values when they differ.

## 11. Anomaly Differences

Anomaly differences are computed from supplied `anomalies` metadata.

The engine does not classify new anomalies. It only compares supplied anomaly indicators.

## 12. Topology / Platform / Target Differences

Topology, platform, target, and source option differences are recorded separately from metric/value differences.

This keeps data differences distinct from option, target, topology, or platform differences.

## 13. Data Availability Differences

Data availability differences record missing fields and supplied `data_availability` or `missing_metrics` changes.

Missing values produce limitations, not fabricated results. Full missing metric handling remains future work.

## 14. Difference Drivers

Likely difference drivers are derived only from supplied differences.

Driver labels may include score changes, wait/event posture changes, SQL concentration changes, trend changes, anomaly changes, topology differences, platform/target/source option differences, and data availability differences.

## 15. Comparison Limitations

Comparison limitations are recorded when report identity is missing, data availability metadata is absent, or fields are missing across compared payloads.

Limitations explain evidence gaps without implementing the future missing metric review model.

## 16. Comparison Artifact Shape

`AWRReportComparisonArtifact` includes:

- `comparison_id`
- `comparison_name`
- `compared_report_count`
- `compared_run_ids`
- `compared_awr_ids`
- `baseline_reference`
- `target_references`
- `score_differences`
- `wait_event_differences`
- `sql_concentration_differences`
- `trend_differences`
- `anomaly_differences`
- `topology_differences`
- `platform_target_differences`
- `data_availability_differences`
- `difference_summary`
- `likely_difference_drivers`
- `comparison_limitations`
- `artifact_written`
- `dashboard_generated`
- `phase4i_mutated`
- `created_by`
- `notes`

`artifact_written=false`, `dashboard_generated=false`, and `phase4i_mutated=false`.

## 17. Relationship to Missing Metric Handling Future 7AO.1 / 7AQ.1

Missing metric handling remains future 7AO.1 / 7AQ.1.

Phase 7AM.1 may note missing or unavailable values in the comparison artifact, but it does not implement missing metric confidence adjustment, parser/source review candidates, evidence availability review, or missing metric workflow behavior.

## 18. Relationship to Phase 8 Sizing / TCO Comparison

Sizing/TCO comparison belongs to Phase 8.

Phase 7AM.1 does not compare costs, capacity plans, sizing options, licensing, cloud shapes, TCO, what-if scenarios, or EM Extract-based sizing data.

## 19. Acceptance Criteria

Phase 7AM.1 is accepted when:

- Comparison is based only on supplied in-memory payloads.
- At least two payloads are required.
- Score differences are compared.
- Wait/event differences are compared.
- SQL concentration differences are compared.
- Trend differences are compared.
- Anomaly differences are compared.
- Topology/platform/target differences are compared.
- Data availability differences are recorded.
- Missing values produce limitations, not fabricated results.
- No AWR files are read.
- No parser is called.
- No DB is queried.
- No object storage is called.
- No LLM is used.
- Missing metric handling remains future 7AO.1 / 7AQ.1.
- Sizing/TCO comparison belongs to Phase 8.
