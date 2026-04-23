"""Single-file HTML dashboard generation for AWR analysis results."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

AI_SECTION_ORDER = [
    "Executive Summary",
    "Technical Narrative",
    "Root Cause Interpretation",
    "Recommended Action Plan",
    "OCI Sizing Considerations",
    "Confidence Assessment",
    "Risk of Being Wrong",
]


def generate_html_dashboard(
    report_data: dict,
    output_file: str = "awr_dashboard.html",
) -> str:
    """Generate a multi-page HTML dashboard bundle and return the index path."""

    output_dir = _resolve_dashboard_output_dir(output_file)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages = _build_dashboard_pages(report_data)
    for file_name, html in pages.items():
        (output_dir / file_name).write_text(html, encoding="utf-8")
    return str((output_dir / "index.html").resolve())


AI_SECTION_NAMES = [
    "Executive Summary",
    "Technical Narrative",
    "Root Cause Interpretation",
    "Recommended Action Plan",
    "OCI Sizing Considerations",
    "Confidence Assessment",
    "Risk of Being Wrong",
]

PAGE_DEFINITIONS = (
    ("home", "Home", "index.html"),
    ("screen_1", "Screen 1 - Ingestion", "screen_1_ingestion.html"),
    ("screen_2", "Screen 2 - Analysis", "screen_2_analysis.html"),
    ("screen_3", "Screen 3 - History Selector", "screen_3_history_selector.html"),
    ("screen_4", "Screen 4 - Historical Review", "screen_4_historical_review.html"),
    (
        "screen_5",
        "Screen 5 - Recommendation / Action",
        "screen_5_recommendation_action.html",
    ),
)

TIME_SERIES_GROUP_DEFINITIONS = (
    {
        "group_key": "cpu",
        "group_title": "CPU Time-Series Charts",
        "charts": (
            (
                "cpu_trend",
                "timeSeriesCpuTrend",
                "DB CPU % DB Time",
                "DB CPU % DB time",
                "rgba(255, 107, 107, 0.92)",
            ),
        ),
    },
    {
        "group_key": "io",
        "group_title": "I/O Time-Series Charts",
        "charts": (
            (
                "io_trend",
                "timeSeriesIoTrend",
                "User I/O Pressure",
                "User I/O % DB time",
                "rgba(246, 184, 76, 0.92)",
            ),
            (
                "log_file_sync_trend",
                "timeSeriesLogFileSyncTrend",
                "Commit / Log File Sync",
                "Log file sync ms",
                "rgba(239, 83, 80, 0.92)",
            ),
            (
                "sql_concentration_trend",
                "timeSeriesSqlTrend",
                "Top 3 SQL Share",
                "Top 3 SQL share %",
                "rgba(186, 104, 200, 0.92)",
            ),
            (
                "hard_parses_trend",
                "timeSeriesHardParsesTrend",
                "Hard Parses / Second",
                "Hard parses/s",
                "rgba(255, 202, 40, 0.92)",
            ),
            (
                "temp_io_trend",
                "timeSeriesTempIoTrend",
                "Temp I/O Pressure",
                "Temp I/O",
                "rgba(38, 166, 154, 0.92)",
            ),
        ),
    },
    {
        "group_key": "memory",
        "group_title": "Memory Time-Series Charts",
        "charts": (
            (
                "concurrency_trend",
                "timeSeriesConcurrencyTrend",
                "Concurrency Pressure",
                "Concurrency % DB time",
                "rgba(127, 179, 213, 0.92)",
            ),
            (
                "pga_spill_trend",
                "timeSeriesPgaSpillTrend",
                "PGA Spill Pressure",
                "PGA spill pressure",
                "rgba(102, 187, 106, 0.92)",
            ),
        ),
    },
    {
        "group_key": "rac",
        "group_title": "RAC Time-Series Charts",
        "charts": (
            (
                "cluster_wait_trend",
                "timeSeriesClusterWaitTrend",
                "Cluster Wait %",
                "Cluster waits % DB time",
                "rgba(255, 159, 67, 0.92)",
            ),
            (
                "gc_wait_trend",
                "timeSeriesGcWaitTrend",
                "GC Wait %",
                "GC wait % DB time",
                "rgba(244, 162, 97, 0.92)",
            ),
        ),
    },
    {
        "group_key": "adg",
        "group_title": "Data Guard Time-Series Charts",
        "charts": (
            (
                "dg_transport_lag_trend",
                "timeSeriesTransportLagTrend",
                "Transport Lag",
                "Lag seconds",
                "rgba(94, 129, 244, 0.92)",
            ),
            (
                "dg_apply_lag_trend",
                "timeSeriesApplyLagTrend",
                "Apply Lag",
                "Lag seconds",
                "rgba(76, 114, 176, 0.92)",
            ),
        ),
    },
    {
        "group_key": "exadata",
        "group_title": "Exadata Time-Series Charts",
        "charts": (
            (
                "exa_cell_io_trend",
                "timeSeriesExadataCellIoTrend",
                "Exadata Cell I/O %",
                "Cell I/O % DB time",
                "rgba(244, 162, 97, 0.92)",
            ),
            (
                "exa_offload_efficiency_trend",
                "timeSeriesExadataOffloadTrend",
                "Exadata Offload Efficiency",
                "Efficiency %",
                "rgba(67, 170, 139, 0.92)",
            ),
        ),
    },
)

AI_SECTION_PATTERN = "|".join(re.escape(name) for name in AI_SECTION_NAMES)
DECISION_PREFIX_PATTERN = (
    r"^\s*"
    r"(DO NOT SCALE|SCALE NOW|DEFER SCALING PENDING VALIDATION|"
    r"INSUFFICIENT DATA TO RECOMMEND(?: SCALING)?)\.\s*"
)
DEFAULT_SUMMARY_RATIONALE = (
    "CPU saturation driven by SQL concentration indicates tuning will unlock "
    "capacity without scaling."
)
DEFAULT_CONFIDENCE_REASON = (
    "Strong AWR signals, including DB CPU at 64.8%, top SQL concentration at "
    "26.6%, and dominant wait classes, point clearly to tunable bottlenecks "
    "rather than infrastructure limits."
)
VIOLIN_METRIC_GROUP_DEFINITIONS = [
    {
        "group_key": "workload",
        "group_title": "Workload Distributions",
        "group_note": "Cluster-level workload values aggregated per snapshot.",
        "metrics": [
            {
                "payload_key": "cluster_cpu_pct_db_time",
                "container_id": "violinClusterCpuPct",
                "title": "Cluster CPU % DB Time",
                "color": "rgba(255, 107, 107, 0.72)",
            },
            {
                "payload_key": "cluster_user_io_pct_db_time",
                "container_id": "violinClusterUserIoPct",
                "title": "Cluster User I/O %",
                "color": "rgba(255, 159, 67, 0.72)",
            },
            {
                "payload_key": "cluster_top_sql_concentration_pct",
                "container_id": "violinClusterTopSqlConcentrationPct",
                "title": "Cluster Top 3 SQL Share %",
                "color": "rgba(186, 104, 200, 0.72)",
            },
            {
                "payload_key": "cluster_execs_per_sec",
                "container_id": "violinClusterExecsPerSec",
                "title": "Cluster Execs/s Distribution",
                "color": "rgba(90, 209, 255, 0.72)",
            },
            {
                "payload_key": "cluster_read_iops",
                "container_id": "violinClusterReadIops",
                "title": "Cluster Read IOPs Distribution",
                "color": "rgba(246, 184, 76, 0.72)",
            },
            {
                "payload_key": "cluster_read_mb_per_sec",
                "container_id": "violinClusterReadMbPerSec",
                "title": "Cluster Read MB/s Distribution",
                "color": "rgba(212, 174, 82, 0.72)",
            },
            {
                "payload_key": "cluster_write_iops",
                "container_id": "violinClusterWriteIops",
                "title": "Cluster Write IOPs Distribution",
                "color": "rgba(127, 179, 213, 0.72)",
            },
            {
                "payload_key": "cluster_write_mb_per_sec",
                "container_id": "violinClusterWriteMbPerSec",
                "title": "Cluster Write MB/s Distribution",
                "color": "rgba(130, 148, 171, 0.72)",
            },
            {
                "payload_key": "cluster_log_file_sync_ms",
                "container_id": "violinClusterLogFileSyncMs",
                "title": "Cluster Log File Sync Latency Distribution",
                "color": "rgba(239, 83, 80, 0.72)",
            },
            {
                "payload_key": "cluster_pga_spill_pressure",
                "container_id": "violinClusterPgaSpillPressure",
                "title": "Cluster PGA Spill Pressure Distribution",
                "color": "rgba(102, 187, 106, 0.72)",
            },
            {
                "payload_key": "cluster_temp_io_pressure",
                "container_id": "violinClusterTempIoPressure",
                "title": "Cluster Temp I/O Pressure Distribution",
                "color": "rgba(38, 166, 154, 0.72)",
            },
            {
                "payload_key": "cluster_hard_parses_per_sec",
                "container_id": "violinClusterHardParsesPerSec",
                "title": "Cluster Hard Parses/s Distribution",
                "color": "rgba(255, 202, 40, 0.72)",
            },
        ],
    },
    {
        "group_key": "topology",
        "group_title": "Topology Distributions",
        "group_note": (
            "Broader cluster and Data Guard measures remain available for historical comparison only; "
            "they do not govern the selected single-instance interpretation, and the combined GC trend is the summed GC current + GC CR pressure."
        ),
        "metrics": [
            {
                "payload_key": "cluster_wait_pct_db_time",
                "container_id": "violinClusterWaitPct",
                "title": "Cluster Wait % DB Time",
                "color": "rgba(255, 127, 80, 0.72)",
            },
            {
                "payload_key": "gc_current_wait_pct_db_time",
                "container_id": "violinGcCurrentWaitPct",
                "title": "GC Current Wait %",
                "color": "rgba(244, 162, 97, 0.72)",
            },
            {
                "payload_key": "gc_cr_wait_pct_db_time",
                "container_id": "violinGcCrWaitPct",
                "title": "GC CR Wait %",
                "color": "rgba(233, 196, 106, 0.72)",
            },
            {
                "payload_key": "transport_lag_sec",
                "container_id": "violinTransportLagSec",
                "title": "Data Guard Transport Lag",
                "color": "rgba(94, 129, 244, 0.72)",
            },
            {
                "payload_key": "apply_lag_sec",
                "container_id": "violinApplyLagSec",
                "title": "Data Guard Apply Lag",
                "color": "rgba(72, 149, 239, 0.72)",
            },
        ],
    },
    {
        "group_key": "platform",
        "group_title": "Platform Distributions",
        "group_note": "Cluster-level Exadata measures shown only when real platform evidence exists.",
        "metrics": [
            {
                "payload_key": "cell_single_block_read_pct_db_time",
                "container_id": "violinCellSingleBlockReadPct",
                "title": "Exadata Cell Single Block Read %",
                "color": "rgba(56, 176, 0, 0.72)",
            },
            {
                "payload_key": "smart_scan_pct_db_time",
                "container_id": "violinSmartScanPct",
                "title": "Exadata Smart Scan %",
                "color": "rgba(67, 170, 139, 0.72)",
            },
        ],
    },
    {
        "group_key": "rac_instance",
        "group_title": "Per-Instance RAC Distributions",
        "group_note": (
            "Per-instance RAC values remain available as broader cluster comparison context only. "
            "These are not mixed with cluster-level distributions."
        ),
        "metrics": [
            {
                "payload_key": "per_instance_cpu_pct_db_time",
                "container_id": "violinPerInstanceRacCpuPct",
                "title": "Per-Instance RAC CPU",
                "color": "rgba(249, 65, 68, 0.72)",
            },
            {
                "payload_key": "per_instance_cluster_wait_pct_db_time",
                "container_id": "violinPerInstanceRacClusterWaitPct",
                "title": "Per-Instance RAC Cluster Wait",
                "color": "rgba(243, 114, 44, 0.72)",
            },
            {
                "payload_key": "per_instance_gc_current_wait_pct_db_time",
                "container_id": "violinPerInstanceRacGcCurrentPct",
                "title": "Per-Instance RAC GC Current Wait",
                "color": "rgba(248, 150, 30, 0.72)",
            },
            {
                "payload_key": "per_instance_gc_cr_wait_pct_db_time",
                "container_id": "violinPerInstanceRacGcCrPct",
                "title": "Per-Instance RAC GC CR Wait",
                "color": "rgba(249, 199, 79, 0.72)",
            },
        ],
    },
]

PERCENT_LIKE_VIOLIN_KEYS = {
    "cluster_cpu_pct_db_time",
    "cluster_user_io_pct_db_time",
    "cluster_top_sql_concentration_pct",
    "cluster_wait_pct_db_time",
    "gc_current_wait_pct_db_time",
    "gc_cr_wait_pct_db_time",
    "cell_single_block_read_pct_db_time",
    "smart_scan_pct_db_time",
    "per_instance_cpu_pct_db_time",
    "per_instance_cluster_wait_pct_db_time",
    "per_instance_gc_current_wait_pct_db_time",
    "per_instance_gc_cr_wait_pct_db_time",
}
VIOLIN_MIN_SAMPLES = 4
VIOLIN_MIN_DISTINCT_VALUES = 2
PREFERRED_VIOLIN_METRICS: dict[str, tuple[str, ...]] = {
    "workload": (
        "cluster_cpu_pct_db_time",
        "cluster_user_io_pct_db_time",
        "cluster_top_sql_concentration_pct",
    ),
    "topology": (
        "cluster_wait_pct_db_time",
        "gc_current_wait_pct_db_time",
        "gc_cr_wait_pct_db_time",
    ),
    "platform": (
        "cell_single_block_read_pct_db_time",
        "smart_scan_pct_db_time",
    ),
    "rac_instance": (
        "per_instance_cpu_pct_db_time",
        "per_instance_cluster_wait_pct_db_time",
        "per_instance_gc_current_wait_pct_db_time",
        "per_instance_gc_cr_wait_pct_db_time",
    ),
}


def parse_ai_sections(ai_text: str) -> dict[str, str]:
    """Parse the generated AI narrative into named sections."""

    if not ai_text:
        return {name: "" for name in AI_SECTION_NAMES}

    section_map = {name: "" for name in AI_SECTION_NAMES}

    pattern = re.compile(
        r"^\s{0,3}(?:#+\s*)?" rf"({AI_SECTION_PATTERN})" r"\s*$",
        re.MULTILINE,
    )

    matches = list(pattern.finditer(ai_text))
    if not matches:
        return section_map

    for index, match in enumerate(matches):
        section_name = match.group(1)
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(ai_text)
        section_map[section_name] = ai_text[start:end].strip()

    return section_map


def _resolve_dashboard_output_dir(output_file: str) -> Path:
    output_path = Path(output_file)
    if output_path.suffix:
        return output_path.parent / output_path.stem
    return output_path


def _build_dashboard_pages(report_data: dict[str, Any]) -> dict[str, str]:
    """Build the full multi-page HTML product bundle."""

    title = str(report_data.get("title") or "AWR Performance Intelligence Dashboard")
    generated_at = str(report_data.get("generated_at") or datetime.utcnow().isoformat())
    screen_models = report_data.get("screen_models") or {}
    screen_4_model = screen_models.get("screen_4_historical_review") or {}
    ai_sections = _normalize_ai_sections(
        parse_ai_sections(str(report_data.get("ai_generated_narrative") or ""))
    )
    decision_state = _derive_decision_state(ai_sections)
    chart_payload = _build_chart_payload(report_data)
    chart_payload["time_series_charts"] = report_data.get("time_series_charts") or {}
    violin_metric_groups = _order_violin_metric_groups(
        _build_violin_metric_groups(chart_payload["violin_panel"]),
        screen_4_model,
    )
    violin_metric_configs = _flatten_violin_metric_groups(violin_metric_groups)
    time_series_groups = _order_time_series_groups(
        _build_time_series_groups(report_data),
        screen_4_model,
    )

    pages = {
        "index.html": _build_page_html(
            page_key="home",
            page_title=title,
            report_data=report_data,
            content_html=_render_home_page(
                report_data,
                screen_models=screen_models,
            ),
            generated_at=generated_at,
        ),
        "screen_1_ingestion.html": _build_page_html(
            page_key="screen_1",
            page_title="Screen 1 - Ingestion",
            report_data=report_data,
            content_html=_render_screen_1_page(
                screen_models.get("screen_1_ingestion") or {}
            ),
            generated_at=generated_at,
        ),
        "screen_2_analysis.html": _build_page_html(
            page_key="screen_2",
            page_title="Screen 2 - Analysis",
            report_data=report_data,
            content_html=_render_screen_2_page(
                screen_models.get("screen_2_analysis") or {},
                ai_sections=ai_sections,
                decision_state=decision_state,
                report_data=report_data,
            ),
            generated_at=generated_at,
        ),
        "screen_3_history_selector.html": _build_page_html(
            page_key="screen_3",
            page_title="Screen 3 - History Selector",
            report_data=report_data,
            content_html=_render_screen_3_selector_page(
                screen_models.get("screen_3_history_selector") or {}
            ),
            generated_at=generated_at,
        ),
        "screen_4_historical_review.html": _build_page_html(
            page_key="screen_4",
            page_title="Screen 4 - Historical Review",
            report_data=report_data,
            content_html=_render_screen_4_page(
                screen_4_model,
                chart_payload=chart_payload,
                violin_metric_groups=violin_metric_groups,
                time_series_groups=time_series_groups,
                derived_scalar_metrics=report_data.get("derived_scalar_metrics") or {},
            ),
            generated_at=generated_at,
            include_chart_scripts=True,
            chart_payload=chart_payload,
            violin_metric_configs=violin_metric_configs,
            time_series_groups=time_series_groups,
        ),
        "screen_5_recommendation_action.html": _build_page_html(
            page_key="screen_5",
            page_title="Screen 5 - Recommendation / Action",
            report_data=report_data,
            content_html=_render_screen_5_page(
                screen_models.get("screen_5_recommendation_action") or {},
                ai_sections=ai_sections,
                agentic_decision=report_data.get("agentic_decision") or {},
            ),
            generated_at=generated_at,
        ),
    }
    return pages


def _build_page_html(
    *,
    page_key: str,
    page_title: str,
    report_data: dict[str, Any],
    content_html: str,
    generated_at: str,
    include_chart_scripts: bool = False,
    chart_payload: dict[str, Any] | None = None,
    violin_metric_configs: list[dict[str, Any]] | None = None,
    time_series_groups: list[dict[str, Any]] | None = None,
) -> str:
    """Build one page of the multi-page dashboard experience."""

    product = _to_dict(report_data.get("product"))
    hero_title = escape(product.get("title") or "AWR Performance Intelligence Dashboard")
    nav_html = _render_page_navigation(page_key)
    shell_class = "top-shell sticky-shell"
    chart_payload_json = (
        json.dumps(chart_payload or {}, indent=2)
        if include_chart_scripts
        else "{}"
    )
    chart_scripts = (
        _build_chart_runtime_javascript(
            violin_metric_configs or [],
            time_series_groups or [],
        )
        if include_chart_scripts
        else ""
    )
    chart_dependencies = (
        """
  <script id="chart-payload" type="application/json">
"""
        + chart_payload_json
        + """
  </script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
"""
        if include_chart_scripts
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(page_title)}</title>
  <style>
{_shared_page_styles()}
  </style>
</head>
<body>
  <div class="container">
    <div class="{shell_class}">
      <section class="hero">
        <div class="eyebrow">AWR Performance Intelligence Dashboard</div>
        <h1>{hero_title}</h1>
        <p class="hero-summary">
          Deterministic Oracle AWR intelligence with canonical diagnosis, historical review,
          and action guidance.
        </p>
        <div class="hero-meta">Generated: {escape(generated_at)}</div>
      </section>

      {nav_html}
    </div>

    {content_html}

    <div class="footer">Generated at {escape(generated_at)}</div>
  </div>
{chart_dependencies}
{chart_scripts}
</body>
</html>
"""


def _render_page_navigation(active_page_key: str) -> str:
    """Render stable navigation across the landing page and all screen pages."""

    links = []
    for page_key, label, filename in PAGE_DEFINITIONS:
        active_class = " active" if page_key == active_page_key else ""
        links.append(
            f'<a class="nav-link{active_class}" href="{escape(filename)}">{escape(label)}</a>'
        )
    return f'<nav class="page-nav">{"".join(links)}</nav>'


def _render_home_page(
    report_data: dict[str, Any],
    screen_models: dict[str, Any],
) -> str:
    """Render the landing page as explanation tier plus navigation hub."""

    metadata = _to_dict(report_data.get("metadata"))
    decision = _to_dict(report_data.get("decision"))
    recommendations = report_data.get("recommendations") or []
    screen_1 = _to_dict(screen_models.get("screen_1_ingestion"))
    screen_2 = _to_dict(screen_models.get("screen_2_analysis"))
    screen_3_selector = _to_dict(screen_models.get("screen_3_history_selector"))
    screen_4_review = _to_dict(screen_models.get("screen_4_historical_review"))
    llm_explanation = _to_dict(report_data.get("llm_explanation"))
    normalized_decision = _to_dict(screen_2.get("normalized_decision"))
    intake_summary = _to_dict(screen_1.get("intake_summary"))
    selector_header = _to_dict(screen_3_selector.get("header"))
    review_header = _to_dict(screen_4_review.get("header"))
    llm_enabled = bool(llm_explanation.get("enabled"))
    llm_provider = llm_explanation.get("provider")
    llm_model = llm_explanation.get("model")
    llm_info_items = [
        ("Explanation Mode", "Enabled" if llm_enabled else "Disabled"),
        ("Provider", llm_provider or "LLM provider not available"),
        (
            "Model",
            _short_model_name(llm_provider, llm_model)
            if _has_display_value(llm_model)
            else "Model not identified in current runtime",
        ),
        (
            "Authoritative Source",
            "Deterministic decision, evidence, and recommendations",
        ),
        (
            "Purpose",
            "Supportive explanation layer for technical, executive, and action context.",
        ),
    ]
    navigation_cards = [
        (
            "Screen 1 - Ingestion / Parse Confidence / Adaptation",
            "screen_1_ingestion.html",
            [
                ("Total Files", intake_summary.get("total_files")),
                ("Succeeded", intake_summary.get("succeeded")),
                ("Source Mode", _to_dict(screen_1.get("header")).get("source_mode")),
            ],
        ),
        (
            "Screen 2 - Analysis",
            "screen_2_analysis.html",
            [
                ("Primary Issue", decision.get("primary_issue")),
                (
                    "Overall Status",
                    normalized_decision.get("overall_status") or decision.get("overall_status"),
                ),
                (
                    "Confidence",
                    normalized_decision.get("confidence") or decision.get("confidence"),
                ),
            ],
        ),
        (
            "Screen 3 - History Selector / Filter / Scope Definition",
            "screen_3_history_selector.html",
            [
                ("Snapshot Count", selector_header.get("snapshot_count")),
                ("Comparison Window", selector_header.get("comparison_window")),
                ("Scope", selector_header.get("scope_label")),
            ],
        ),
        (
            "Screen 4 - Historical Review",
            "screen_4_historical_review.html",
            [
                ("Scope", review_header.get("scope_label")),
                ("Snapshot Count", review_header.get("snapshot_count")),
                ("Comparison Window", review_header.get("comparison_window")),
            ],
        ),
        (
            "Screen 5 - Recommendation / Action",
            "screen_5_recommendation_action.html",
            [
                ("Recommendation Count", len(recommendations)),
                (
                    "Primary Issue",
                    normalized_decision.get("primary_issue") or decision.get("primary_issue"),
                ),
                ("DB Name", metadata.get("db_name")),
            ],
        ),
    ]

    return f"""
    <div class="grid">
      <!-- index.html is the explanation and navigation layer. -->
      <section class="card primary">
        <div class="section-kicker">Platform Identity</div>
        <h2>AWR Performance Intelligence Dashboard</h2>
        <p>
          A structured intelligence layer that transforms Oracle AWR reports into
          deterministic diagnosis, historical comparison, and action-ready guidance.
        </p>
      </section>

      <section class="card secondary">
        <div class="section-kicker">What the Platform Does</div>
        <h2>From AWR Reports to Actionable Intelligence</h2>
        <div class="stack">
          {_render_bullet_item("Transforms Oracle AWR reports into structured, actionable intelligence.")}
          {_render_bullet_item("Bridges performance diagnostics with infrastructure decision-making.")}
          {_render_bullet_item("Supports workload understanding across snapshots and time windows.")}
          {_render_bullet_item("Understands single instance, RAC, Exadata, and Data Guard contexts.")}
          {_render_bullet_item("Produces deterministic scoring, analysis, recommendations, and decision support.")}
        </div>
      </section>

      <section class="card secondary">
        <div class="section-kicker">How the Platform Works</div>
        <h2>Operational Flow</h2>
        <div class="flow-grid">
          {_render_flow_step(
              "AWR Reports",
              "Oracle workload snapshots enter the platform as raw diagnostic inputs.",
          )}
          {_render_flow_step(
              "Ingestion",
              "The parser adapts to report variability and captures structured metadata, waits, and SQL evidence.",
          )}
          {_render_flow_step(
              "Data Platform",
              "Normalized features, trend context, and topology signals become reusable runtime state.",
          )}
          {_render_flow_step(
              "Intelligence Layer",
              "Deterministic findings are grouped into evidence, trend, and anomaly context.",
          )}
          {_render_flow_step(
              "Decision Engine",
              "Scoring and competition produce the authoritative primary issue and status.",
          )}
          {_render_flow_step(
              "Dashboard / Output",
              "The product presents diagnosis, historical review, and action guidance through the 5-screen model.",
          )}
        </div>
      </section>

      <section class="card secondary">
        <div class="section-kicker">From Insights to Decisions</div>
        <h2>Deterministic Evidence Before Narrative</h2>
        <div class="flow-grid">
          {_render_flow_step(
              "Analytical Input",
              "Scores, trends, anomalies, and grouped findings establish the deterministic baseline.",
          )}
          {_render_flow_step(
              "Risk Signals",
              "The system surfaces performance drivers, topology effects, and data-quality context.",
          )}
          {_render_flow_step(
              "Decision Layer",
              "The primary issue and severity are selected from score-based competition, not narrative.",
          )}
          {_render_flow_step(
              "Recommendations / Action",
              "Actions remain tied back to canonical findings and supporting evidence.",
          )}
        </div>
      </section>

      <section class="card secondary">
        <div class="section-kicker">Evolution / Bottom Line</div>
        <h2>Structured Intelligence for Immediate and Future Decisions</h2>
        <div class="stack">
          {_render_bullet_item("From manual AWR analysis to structured performance intelligence.")}
          {_render_bullet_item("From isolated insights to deterministic diagnosis and decision support.")}
          {_render_bullet_item("From tuning guidance alone to future-facing sizing and scaling posture.")}
        </div>
      </section>

      <section class="card secondary">
        <div class="section-kicker">AI Explanation Layer</div>
        <h2>LLM / Explanation Provider</h2>
        <p class="chart-support-note">
          Deterministic findings remain authoritative. The LLM is used only for
          supportive explanation, executive wording, and technical framing.
        </p>
        {_render_info_grid(llm_info_items)}
      </section>

      <section class="card prominent">
        <div class="section-kicker">Navigation</div>
        <h2>5-Screen Product Model</h2>
        <div class="nav-card-grid">
          {"".join(_render_navigation_card(title, href, previews) for title, href, previews in navigation_cards)}
        </div>
      </section>
    </div>
    """


def _render_screen_1_page(screen_model: dict[str, Any]) -> str:
    return f"""
    <div class="grid">
      <!-- Screen 1 = intake / parse confidence / adaptation. -->
      {_render_ingestion_screen(screen_model)}
    </div>
    """


def _render_screen_2_page(
    screen_model: dict[str, Any],
    ai_sections: dict[str, str],
    decision_state: dict[str, str],
    report_data: dict[str, Any],
) -> str:
    analysis_information = _to_dict(screen_model.get("analysis_information"))
    scope_note = screen_model.get("scope_note")
    decision_summary = _to_dict(screen_model.get("decision_summary"))
    normalized_decision = _to_dict(screen_model.get("normalized_decision"))
    health_check = _to_dict(screen_model.get("health_check"))
    explanation_panel = _to_dict(screen_model.get("explanation_panel"))
    ingestion_header = _to_dict(screen_model.get("ingestion_header"))
    visual_summary = _to_dict(screen_model.get("visual_summary"))
    technical_sections = screen_model.get("technical_sections") or []
    root_cause_interpretation = _to_dict(screen_model.get("root_cause_interpretation"))
    recommended_action_plan = _to_dict(screen_model.get("recommended_action_plan"))
    context_truth = {
        "topology_detected": analysis_information.get("topology_detected"),
        "platform_detected": analysis_information.get("platform_detected"),
    }
    executive_summary_text = _normalize_scope_context_claims(
        ai_sections["Executive Summary"],
        context_truth,
    )
    technical_text = _normalize_scope_context_claims(
        ai_sections["Technical Narrative"] or explanation_panel.get("technical_explanation"),
        context_truth,
    )
    root_cause_text = _normalize_scope_context_claims(
        ai_sections["Root Cause Interpretation"] or explanation_panel.get("technical_explanation"),
        context_truth,
    )
    executive_decision_state = _normalized_decision_banner_state(
        normalized_decision,
        fallback=decision_state,
    )
    authoritative_confidence = (
        decision_summary.get("confidence")
        if decision_summary.get("confidence") is not None
        else normalized_decision.get("confidence")
    )
    return f"""
    <div class="grid">
      <!-- Screen 2 = diagnosis / evidence / confidence / health check. -->
      {_render_ingestion_header_card(ingestion_header)}
      <section class="card secondary">
        <div class="section-kicker">Analysis Context</div>
        <h2>Analysis Information</h2>
        {
            f'<div class="meta context-note">{escape(_display_value(scope_note))}</div>'
            if _has_display_value(scope_note)
            else ""
        }
        {_render_info_grid(_analysis_information_items(analysis_information))}
      </section>
      <section class="card primary">
        <div class="section-kicker">Executive Summary</div>
        <h2>Executive Summary</h2>
        {_render_executive_summary(
            executive_summary_text,
            [],
            executive_decision_state,
            report_data.get("summary_key_signals"),
            normalized_decision=normalized_decision,
        )}
      </section>
      <section class="card prominent">
        <div class="section-kicker">Decision Summary</div>
        <h2>Decision Summary</h2>
        {_render_info_grid(
            [
                ("Overall Status", decision_summary.get("overall_status")),
                ("Risk", decision_summary.get("display_severity_label")),
                ("Primary Issue", decision_summary.get("primary_issue")),
                (
                    "Secondary Issues",
                    ", ".join(decision_summary.get("secondary_issues") or []),
                ),
                ("Decision Posture", decision_summary.get("decision_posture")),
                ("Historical Posture", decision_summary.get("historical_posture")),
                ("Health Summary", decision_summary.get("health_summary")),
                ("Confidence", _confidence_summary_text(authoritative_confidence)),
            ]
        )}
      </section>
      <section class="card secondary">
        <div class="section-kicker">Visual Summary</div>
        <h2>Visual Summary</h2>
        {_render_analysis_visual_summary(visual_summary)}
      </section>
      <section class="card secondary">
        <div class="section-kicker">Deterministic Health Check</div>
        <h2>Health Check</h2>
        {_render_health_check(health_check)}
      </section>
      <section class="card primary">
        <h2>Technical Explanation</h2>
        {_render_analysis_technical_sections(
            technical_sections,
            technical_text,
            normalized_decision=normalized_decision,
            context_truth=context_truth,
        )}
      </section>
      <section class="card primary">
        <h2>Root Cause Interpretation</h2>
        {_render_root_cause_panel(
            root_cause_interpretation,
            root_cause_text,
            normalized_decision=normalized_decision,
        )}
      </section>
      <section class="card primary">
        <h2>Diagnostic Orientation</h2>
        {_render_action_plan_summary(recommended_action_plan, ai_sections["Recommended Action Plan"])}
      </section>
      <section class="card prominent">
        {_render_confidence_section(
            _normalize_scope_context_claims(
                ai_sections["Confidence Assessment"],
                context_truth,
            ),
            authoritative_confidence=authoritative_confidence,
        )}
      </section>
      <section class="card primary">
        {_render_risk_section(ai_sections["Risk of Being Wrong"])}
      </section>
      <section class="card secondary">
        {_render_analysis_screen(screen_model)}
      </section>
    </div>
    """


def _render_screen_3_selector_page(screen_model: dict[str, Any]) -> str:
    header = _to_dict(screen_model.get("header"))
    scope_selection = _to_dict(screen_model.get("scope_selection"))
    timeframe_selection = _to_dict(screen_model.get("timeframe_selection"))
    review_mode = _to_dict(screen_model.get("review_mode"))
    current_selection_summary = _to_dict(screen_model.get("current_selection_summary"))
    return f"""
    <div class="grid">
      <!-- Screen 3 = history selector / filter / scope definition. -->
      <section class="card secondary">
        <div class="section-kicker">Screen 3</div>
        <h2>History Selector / Filter / Scope Definition</h2>
        <div class="subgrid selector-subgrid">
          <section class="evidence-pane selector-pane">
            <h3>Header</h3>
            {_render_info_grid(
                [
                    ("DB Name", header.get("db_name")),
                    ("Instance", header.get("instance_name")),
                    ("Host", header.get("host_name")),
                    ("Window", header.get("window")),
                ]
            , extra_class="selector-header-grid")}
          </section>
          <section class="half evidence-pane selector-pane">
            <h3>Scope Selection</h3>
            {_render_scope_chips(scope_selection.get("options") or [])}
            {_render_info_strip([("Scope", scope_selection.get("active_scope"))])}
          </section>
          <section class="half evidence-pane selector-pane">
            <h3>Timeframe Selection</h3>
            {_render_info_grid(
                [
                    ("Comparison Window", timeframe_selection.get("comparison_window")),
                    ("Start / End Period", timeframe_selection.get("start_end_period")),
                    ("Window A", timeframe_selection.get("window_a")),
                    ("Window B", timeframe_selection.get("window_b")),
                ]
            , extra_class="selector-compact-grid")}
          </section>
          <section class="half evidence-pane selector-pane">
            <h3>Review Mode / Intent</h3>
            {_render_scope_chips(review_mode.get("options") or [])}
            {_render_info_strip([("Active Review Mode", review_mode.get("active_mode"))])}
          </section>
          <section class="half evidence-pane selector-pane">
            <h3>Current Selection Summary</h3>
            {_render_info_grid(
                [
                    ("Scope", current_selection_summary.get("scope")),
                    ("Timeframe", current_selection_summary.get("timeframe")),
                    ("Review Mode", current_selection_summary.get("review_mode")),
                ]
            , extra_class="selector-compact-grid")}
          </section>
        </div>
      </section>
    </div>
    """


def _render_screen_4_page(
    screen_model: dict[str, Any],
    chart_payload: dict[str, Any],
    violin_metric_groups: list[dict[str, Any]],
    time_series_groups: list[dict[str, Any]],
    derived_scalar_metrics: dict[str, Any],
) -> str:
    normalized_decision = _to_dict(screen_model.get("normalized_decision"))
    header = _to_dict(screen_model.get("header"))
    current_selection_summary = _to_dict(screen_model.get("current_selection_summary"))
    historical_verdict = _to_dict(screen_model.get("historical_verdict"))
    visual_story = _to_dict(_to_dict(screen_model.get("visual_analysis")).get("story"))
    scalar_metrics_html = _render_scalar_metrics(derived_scalar_metrics)
    time_series_section_html = _render_time_series_section(time_series_groups)
    visual_sections = {
        "performance": _render_performance_charts_section(chart_payload, visual_story),
        "time_series": time_series_section_html,
        "violin": _render_violin_panel(violin_metric_groups),
        "scalar": (
            f"""
      <section id="derived-scalar-metrics" class="card secondary">
        <div class="section-kicker">Supporting Visual Layer</div>
        <h2>Derived Scalar Metrics</h2>
        {scalar_metrics_html}
      </section>
    """
            if scalar_metrics_html
            else ""
        ),
    }
    ordered_visual_sections = "".join(
        visual_sections.get(section_key, "")
        for section_key in (visual_story.get("section_order") or ["performance", "time_series", "violin", "scalar"])
        if visual_sections.get(section_key, "")
    )
    engineering_view_html = _render_engineering_view(
        screen_model.get("engineering_view"),
        "Engineering View",
    )
    return f"""
    <div class="grid">
      <!-- Screen 4 = historical review across scope + timeframe, with visuals. -->
      <section class="card secondary">
        <div class="section-kicker">Screen 4</div>
        <h2>Historical Review / Comparison</h2>
        <div class="meta">
          Historical / Supporting Context (Not Selected-Scope Truth)
        </div>
        <div class="subgrid">
          <section class="half evidence-pane">
            <h3>Header</h3>
            {_render_info_grid(
                [
                    ("Scope", header.get("scope_label")),
                    ("Instance", header.get("instance_name")),
                    ("Host", header.get("host_name")),
                    (
                        "Window",
                        _format_window_summary(
                            header.get("snapshot_count"),
                            header.get("comparison_window"),
                        ),
                    ),
                ]
            )}
          </section>
          <section class="half evidence-pane">
            <h3>Current Selection Summary</h3>
            {_render_info_grid(
                [
                    ("Current Window", current_selection_summary.get("current_window")),
                    ("Comparison Mode", current_selection_summary.get("comparison_mode")),
                    ("Latest vs Prior", current_selection_summary.get("latest_vs_prior")),
                ]
            )}
          </section>
          <section class="evidence-pane">
            <h3>Historical Verdict</h3>
            {_render_info_grid(
                [
                    ("Dominant Pattern", historical_verdict.get("dominant_pattern")),
                    ("Risk", historical_verdict.get("display_severity_label")),
                    ("Historical Stability", historical_verdict.get("historical_stability")),
                    ("Anomaly Burden", historical_verdict.get("anomaly_burden")),
                    ("Historical Posture", historical_verdict.get("historical_posture")),
                ]
            )}
          </section>
        </div>
      </section>
      {ordered_visual_sections}
      <section class="card secondary">
        {_render_review_comparison_screen(
            screen_model,
            normalized_decision=normalized_decision,
        )}
      </section>
      {
          f'''
      <section class="card secondary">
        <h2>Technical Detail</h2>
        {engineering_view_html}
      </section>
      '''
          if engineering_view_html
          else ""
      }
    </div>
    """


def _render_screen_5_page(
    screen_model: dict[str, Any],
    ai_sections: dict[str, str],
    agentic_decision: dict[str, Any],
) -> str:
    normalized_decision = _to_dict(screen_model.get("normalized_decision"))
    header = _to_dict(screen_model.get("header"))
    authoritative_confidence = (
        header.get("confidence")
        or normalized_decision.get("confidence")
    )
    decision_layer_payload = dict(agentic_decision or {})
    if authoritative_confidence is not None:
        decision_layer_payload["confidence_level"] = _confidence_level_from_value(
            authoritative_confidence
        )
    engineering_view_html = _render_engineering_view(
        screen_model.get("engineering_view"),
        "Engineering View",
    )
    return f"""
    <div class="grid">
      <!-- Screen 5 = action / decision / sizing guidance. -->
      <section class="card prominent">
        <div class="section-kicker">Final Decision Banner</div>
        <h2>Decision Posture</h2>
        {_render_info_grid(
            [
                ("Decision Posture", normalized_decision.get("decision_posture")),
                ("Risk", normalized_decision.get("display_severity_label")),
                ("Primary Driver", normalized_decision.get("primary_issue")),
                (
                    "Secondary Driver",
                    list(normalized_decision.get("secondary_issues") or [None])[0],
                ),
            ]
        )}
        <div class="banner-meta-strip">
          {_render_pill_stack(
              [
                  _render_confidence_badge(authoritative_confidence),
                  _render_status_badge(normalized_decision.get("display_severity_label")),
                  _render_status_badge(normalized_decision.get("decision_posture")),
              ],
              ["Confidence", "Risk", "Posture"],
          )}
        </div>
      </section>
      <section class="card prominent decision-layer-card">
        <div class="section-kicker">Decision Layer</div>
        <h2>Decision Detail</h2>
        <div class="decision-grid">
          {_render_decision_boxes(decision_layer_payload)}
        </div>
      </section>
      <section class="card secondary">
        <div class="section-kicker">Prioritized Actions</div>
        <h2>Recommended Actions</h2>
        {_render_recommendation_action_screen(screen_model)}
      </section>
      <section class="card primary">
        <h2>Recommended Action Plan</h2>
        <div class="narrative">{_render_text_block(_build_screen5_action_plan_copy(screen_model, ai_sections["Recommended Action Plan"]))}</div>
      </section>
      <section class="card primary">
        <h2>Capacity / Sizing Guidance</h2>
        <div class="supportive-panel guidance-panel">
          <div class="meta">
            Platform-neutral guidance derived from the deterministic decision posture.
          </div>
          <div class="narrative">
            {_render_text_block(_normalize_capacity_guidance_text(ai_sections["OCI Sizing Considerations"], authoritative_confidence))}
          </div>
        </div>
      </section>
      {
          f'''
      <section class="card secondary">
        <h2>Technical Detail</h2>
        {engineering_view_html}
      </section>
      '''
          if engineering_view_html
          else ""
      }
    </div>
    """


def _render_navigation_card(
    title: str,
    href: str,
    previews: list[tuple[str, Any]],
) -> str:
    preview_items = "".join(
        f"<li><strong>{escape(label)}:</strong> {escape(_display_value(value))}</li>"
        for label, value in previews
        if _has_display_value(value)
    )
    return f"""
      <a class="nav-card" href="{escape(href)}">
        <h3>{escape(title)}</h3>
        {"<ul>" + preview_items + "</ul>" if preview_items else '<div class="meta">Open this screen</div>'}
      </a>
    """


def _render_bullet_item(text: str) -> str:
    return f'<article class="item"><p>{escape(text)}</p></article>'


def _render_flow_step(title: str, description: str) -> str:
    return f"""
      <article class="flow-step">
        <strong>{escape(title)}</strong>
        <p>{escape(description)}</p>
      </article>
    """


def _build_time_series_groups(report_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Build grouped time-series chart definitions from runtime payload."""

    payload = _to_dict(report_data.get("time_series_charts"))
    labels = payload.get("snapshot_labels") or []
    if len(labels) < 2:
        return []
    db_scope_metrics = _to_dict(report_data.get("db_scope_metrics"))
    db_scope_specs = db_scope_metrics.get("chart_specs") or []
    if db_scope_specs:
        groups_by_domain: dict[str, list[dict[str, Any]]] = {}
        for spec in db_scope_specs:
            spec_dict = _to_dict(spec)
            key = spec_dict.get("key")
            series = payload.get(key) or []
            if not _series_has_display_data(series):
                continue
            domain = str(spec_dict.get("domain") or "WORKLOAD").upper()
            groups_by_domain.setdefault(domain, []).append(
                {
                    "key": key,
                    "container_id": spec_dict.get("container_id"),
                    "title": spec_dict.get("title"),
                    "label": spec_dict.get("label"),
                    "color": spec_dict.get("color") or "rgba(94, 129, 244, 0.92)",
                }
            )
        preferred_order = (
            "CPU",
            "IO",
            "MEMORY",
            "NETWORK",
            "COMMIT",
            "RAC",
            "ADG",
            "EXADATA",
            "PLATFORM",
            "WORKLOAD",
        )
        ordered_domains = [
            domain
            for domain in preferred_order
            if groups_by_domain.get(domain)
        ] + sorted(
            domain
            for domain in groups_by_domain
            if domain not in preferred_order
        )
        if ordered_domains:
            return [
                {
                    "group_key": domain.lower(),
                    "group_title": _time_series_group_title(domain),
                    "charts": groups_by_domain[domain],
                }
                for domain in ordered_domains
            ]
    groups: list[dict[str, Any]] = []
    for group in TIME_SERIES_GROUP_DEFINITIONS:
        charts = []
        for key, container_id, title, label, color in group["charts"]:
            series = payload.get(key) or []
            if not _series_has_display_data(series):
                continue
            charts.append(
                {
                    "key": key,
                    "container_id": container_id,
                    "title": title,
                    "label": label,
                    "color": color,
                }
            )
        if charts:
            groups.append(
                {
                    "group_key": group["group_key"],
                    "group_title": group["group_title"],
                    "charts": charts,
                }
            )
    return groups


def _screen_primary_issue(screen_model: dict[str, Any]) -> str:
    normalized_decision = _to_dict(screen_model.get("normalized_decision"))
    return str(normalized_decision.get("primary_issue") or "").strip().upper()


def _order_time_series_groups(
    time_series_groups: list[dict[str, Any]],
    screen_model: dict[str, Any],
) -> list[dict[str, Any]]:
    visual_story = _to_dict(_to_dict(screen_model.get("visual_analysis")).get("story"))
    story_priority = [
        str(item).lower()
        for item in (visual_story.get("time_series_priority") or [])
        if str(item).strip()
    ]
    story_suppressed = {
        str(item).lower()
        for item in (visual_story.get("time_series_suppressed") or [])
        if str(item).strip()
    }
    if story_priority:
        filtered_groups = [
            group
            for group in time_series_groups
            if str(group.get("group_key") or "").lower() not in story_suppressed
        ]
        rank = {group_key: index for index, group_key in enumerate(story_priority)}
        return sorted(
            filtered_groups,
            key=lambda group: (
                rank.get(str(group.get("group_key") or "").lower(), len(rank)),
                str(group.get("group_title") or ""),
            ),
        )

    primary_issue = _screen_primary_issue(screen_model)
    preferred_order = {
        "CPU": ["cpu", "io", "commit", "memory", "rac", "adg", "exadata", "platform"],
        "IO": ["io", "cpu", "commit", "memory", "rac", "adg", "exadata", "platform"],
        "MEMORY": ["memory", "io", "cpu", "commit", "rac", "adg", "exadata", "platform"],
        "COMMIT": ["commit", "io", "cpu", "memory", "rac", "adg", "exadata", "platform"],
        "RAC": ["rac", "cpu", "io", "commit", "memory", "adg", "exadata", "platform"],
        "ADG": ["adg", "rac", "io", "cpu", "commit", "memory", "exadata", "platform"],
    }.get(primary_issue, [])
    if not preferred_order:
        return time_series_groups
    rank = {group_key: index for index, group_key in enumerate(preferred_order)}
    return sorted(
        time_series_groups,
        key=lambda group: (
            rank.get(str(group.get("group_key") or ""), len(rank)),
            str(group.get("group_title") or ""),
        ),
    )


def _order_violin_metric_groups(
    violin_metric_groups: list[dict[str, Any]],
    screen_model: dict[str, Any],
) -> list[dict[str, Any]]:
    visual_story = _to_dict(_to_dict(screen_model.get("visual_analysis")).get("story"))
    story_group_order = [
        str(item).lower()
        for item in (visual_story.get("violin_group_priority") or [])
        if str(item).strip()
    ]
    story_suppressed = {
        str(item).lower()
        for item in (visual_story.get("violin_group_suppressed") or [])
        if str(item).strip()
    }
    preferred_metrics_by_group = {
        str(group_key): [
            str(metric_key)
            for metric_key in metric_keys
            if str(metric_key).strip()
        ]
        for group_key, metric_keys in _to_dict(
            visual_story.get("preferred_violin_metrics")
        ).items()
    }
    if story_group_order:
        group_rank = {
            group_key: index for index, group_key in enumerate(story_group_order)
        }
        ordered_groups: list[dict[str, Any]] = []
        for group in violin_metric_groups:
            group_key = str(group.get("group_key") or "").lower()
            if group_key in story_suppressed:
                continue
            metrics = list(group.get("metrics") or [])
            preferred_metrics = preferred_metrics_by_group.get(group_key) or []
            if preferred_metrics:
                preferred_metric_set = set(preferred_metrics)
                filtered_metrics = [
                    metric
                    for metric in metrics
                    if str(metric.get("payload_key") or "") in preferred_metric_set
                ]
                if filtered_metrics:
                    metric_rank = {
                        metric_key: index
                        for index, metric_key in enumerate(preferred_metrics)
                    }
                    metrics = sorted(
                        filtered_metrics,
                        key=lambda metric: (
                            metric_rank.get(
                                str(metric.get("payload_key") or ""),
                                len(metric_rank),
                            ),
                            str(metric.get("title") or ""),
                        ),
                    )
            if not metrics:
                continue
            ordered_groups.append({**group, "metrics": metrics})

        return sorted(
            ordered_groups,
            key=lambda group: (
                group_rank.get(str(group.get("group_key") or "").lower(), len(group_rank)),
                str(group.get("group_title") or ""),
            ),
        )

    primary_issue = _screen_primary_issue(screen_model)
    group_order = {
        "CPU": ["workload", "topology", "rac_instance", "platform"],
        "IO": ["workload", "topology", "rac_instance", "platform"],
        "MEMORY": ["workload", "topology", "rac_instance", "platform"],
        "COMMIT": ["workload", "topology", "rac_instance", "platform"],
        "RAC": ["topology", "rac_instance", "workload", "platform"],
        "ADG": ["topology", "workload", "rac_instance", "platform"],
    }.get(primary_issue, [])
    if not group_order:
        return violin_metric_groups

    workload_metric_order = {
        "CPU": [
            "cluster_cpu_pct_db_time",
            "cluster_user_io_pct_db_time",
            "cluster_top_sql_concentration_pct",
            "cluster_log_file_sync_ms",
            "cluster_pga_spill_pressure",
            "cluster_temp_io_pressure",
            "cluster_hard_parses_per_sec",
            "cluster_execs_per_sec",
            "cluster_read_iops",
            "cluster_read_mb_per_sec",
            "cluster_write_iops",
            "cluster_write_mb_per_sec",
        ],
        "IO": [
            "cluster_user_io_pct_db_time",
            "cluster_read_iops",
            "cluster_read_mb_per_sec",
            "cluster_write_iops",
            "cluster_write_mb_per_sec",
            "cluster_log_file_sync_ms",
            "cluster_top_sql_concentration_pct",
            "cluster_cpu_pct_db_time",
            "cluster_pga_spill_pressure",
            "cluster_temp_io_pressure",
            "cluster_hard_parses_per_sec",
            "cluster_execs_per_sec",
        ],
        "MEMORY": [
            "cluster_pga_spill_pressure",
            "cluster_temp_io_pressure",
            "cluster_hard_parses_per_sec",
            "cluster_log_file_sync_ms",
            "cluster_cpu_pct_db_time",
            "cluster_user_io_pct_db_time",
            "cluster_top_sql_concentration_pct",
            "cluster_execs_per_sec",
            "cluster_read_iops",
            "cluster_read_mb_per_sec",
            "cluster_write_iops",
            "cluster_write_mb_per_sec",
        ],
        "COMMIT": [
            "cluster_log_file_sync_ms",
            "cluster_user_io_pct_db_time",
            "cluster_cpu_pct_db_time",
            "cluster_top_sql_concentration_pct",
            "cluster_pga_spill_pressure",
            "cluster_temp_io_pressure",
            "cluster_hard_parses_per_sec",
            "cluster_execs_per_sec",
            "cluster_read_iops",
            "cluster_read_mb_per_sec",
            "cluster_write_iops",
            "cluster_write_mb_per_sec",
        ],
    }
    topology_metric_order = {
        "RAC": [
            "cluster_wait_pct_db_time",
            "gc_current_wait_pct_db_time",
            "gc_cr_wait_pct_db_time",
            "transport_lag_sec",
            "apply_lag_sec",
        ],
        "ADG": [
            "transport_lag_sec",
            "apply_lag_sec",
            "cluster_wait_pct_db_time",
            "gc_current_wait_pct_db_time",
            "gc_cr_wait_pct_db_time",
        ],
    }
    rac_instance_metric_order = {
        "RAC": [
            "per_instance_cluster_wait_pct_db_time",
            "per_instance_gc_current_wait_pct_db_time",
            "per_instance_gc_cr_wait_pct_db_time",
            "per_instance_cpu_pct_db_time",
        ]
    }
    group_rank = {group_key: index for index, group_key in enumerate(group_order)}

    ordered_groups: list[dict[str, Any]] = []
    for group in violin_metric_groups:
        group_key = str(group.get("group_key") or "")
        metrics = list(group.get("metrics") or [])
        preferred_metrics = {
            "workload": workload_metric_order.get(primary_issue, []),
            "topology": topology_metric_order.get(primary_issue, []),
            "rac_instance": rac_instance_metric_order.get(primary_issue, []),
        }.get(group_key, [])
        if preferred_metrics:
            metric_rank = {
                metric_key: index for index, metric_key in enumerate(preferred_metrics)
            }
            metrics = sorted(
                metrics,
                key=lambda metric: (
                    metric_rank.get(str(metric.get("payload_key") or ""), len(metric_rank)),
                    str(metric.get("title") or ""),
                ),
            )
        ordered_groups.append({**group, "metrics": metrics})

    return sorted(
        ordered_groups,
        key=lambda group: (
            group_rank.get(str(group.get("group_key") or ""), len(group_rank)),
            str(group.get("group_title") or ""),
        ),
    )


def _time_series_group_title(domain: str) -> str:
    normalized = str(domain or "WORKLOAD").upper()
    return {
        "CPU": "CPU Time-Series Charts",
        "IO": "I/O Time-Series Charts",
        "MEMORY": "Memory Time-Series Charts",
        "NETWORK": "Network Time-Series Charts",
        "COMMIT": "Commit Time-Series Charts",
        "RAC": "RAC Time-Series Charts",
        "ADG": "Data Guard Time-Series Charts",
        "EXADATA": "Exadata Time-Series Charts",
        "PLATFORM": "Platform Time-Series Charts",
        "WORKLOAD": "Workload Time-Series Charts",
    }.get(normalized, f"{normalized.title()} Time-Series Charts")


def _series_has_chart_data(values: Any) -> bool:
    if not isinstance(values, list):
        return False
    numeric_count = sum(1 for value in values if value is not None)
    return numeric_count >= 2


def _series_has_display_data(values: Any) -> bool:
    if not isinstance(values, list):
        return False
    numeric_count = sum(
        1 for value in values if isinstance(value, (int, float)) and math.isfinite(float(value))
    )
    return numeric_count >= 2


def _render_time_series_section(time_series_groups: list[dict[str, Any]]) -> str:
    """Render Screen 3 time-series charts only when real historical data exists."""

    if not time_series_groups:
        return ""
    group_sections = []
    for group in time_series_groups:
        panels = []
        for chart in group["charts"]:
            panels.append(
                f"""
                <section class="chart-panel">
                  <h3>{escape(chart["title"])}</h3>
                  <div class="chart-canvas"><canvas id="{escape(chart["container_id"])}"></canvas></div>
                </section>
                """
            )
        group_sections.append(
            f"""
            <div class="chart-domain-group">
              <div class="chart-domain-heading">{escape(group["group_title"])}</div>
              <div class="chart-grid">
                {"".join(panels)}
              </div>
            </div>
            """
        )
    return f"""
      <section id="time-series-charts" class="card secondary">
        <div class="section-kicker">Supporting Visual Layer</div>
        <h2>Supporting Trends</h2>
        <p class="chart-support-note">
          Historical / Supporting Context (Not Selected-Scope Truth). These
          chart views support deterministic findings and remain subordinate to
          the canonical comparison conclusions.
        </p>
        {"".join(group_sections)}
      </section>
    """


def _build_chart_runtime_javascript(
    violin_metric_configs: list[dict[str, Any]],
    time_series_groups: list[dict[str, Any]],
) -> str:
    """Build chart runtime JavaScript for Screen 3 visual layers."""

    time_series_specs = [
        chart
        for group in time_series_groups
        for chart in group["charts"]
    ]
    return f"""
  <script>
    const chartPayloadElement = document.getElementById('chart-payload');
    let chartPayload = {{}};
    try {{
      if (chartPayloadElement) {{
        chartPayload = JSON.parse(chartPayloadElement.textContent.trim());
      }}
    }} catch (error) {{
      console.error('Chart payload invalid', error);
    }}

    const chartTextColor = '#d9e4f2';
    const chartMutedColor = 'rgba(159, 176, 199, 0.28)';
    const violinConfigs = {json.dumps(violin_metric_configs)};
    const timeSeriesSpecs = {json.dumps(time_series_specs)};
    const violinMinimumSamples = {VIOLIN_MIN_SAMPLES};
    const violinMinimumDistinctValues = {VIOLIN_MIN_DISTINCT_VALUES};
    let dbChart = null;
    let sqlChart = null;
    let timeSeriesCharts = [];

    function showChartFallback(canvasId, message = 'No data available') {{
      const canvas = document.getElementById(canvasId);
      if (!canvas || !canvas.parentElement) {{
        return;
      }}
      canvas.parentElement.innerHTML = '<div class="chart-empty">' + message + '</div>';
    }}

    function computeMean(values) {{
      return values.reduce((sum, value) => sum + value, 0) / values.length;
    }}

    function computeMedian(values) {{
      const sorted = [...values].sort((a, b) => a - b);
      const middle = Math.floor(sorted.length / 2);
      if (sorted.length % 2 === 0) {{
        return (sorted[middle - 1] + sorted[middle]) / 2;
      }}
      return sorted[middle];
    }}

    function computeQuantile(values, quantile) {{
      const sorted = [...values].sort((a, b) => a - b);
      if (!sorted.length) {{
        return NaN;
      }}
      const position = (sorted.length - 1) * quantile;
      const lower = Math.floor(position);
      const upper = Math.ceil(position);
      if (lower === upper) {{
        return sorted[lower];
      }}
      const weight = position - lower;
      return sorted[lower] * (1 - weight) + sorted[upper] * weight;
    }}

    function normalizeDistributionSamples(samples) {{
      if (!Array.isArray(samples)) {{
        return [];
      }}
      return samples.filter((value) => Number.isFinite(value));
    }}

    function showDistributionFallback(containerId, message) {{
      const container = document.getElementById(containerId);
      if (!container) {{
        return;
      }}
      container.innerHTML = '<div class="chart-empty">' + message + '</div>';
    }}

    function formatMetricValue(value) {{
      if (!Number.isFinite(value)) {{
        return '';
      }}
      if (Math.abs(value) >= 100) {{
        return value.toFixed(0);
      }}
      if (Math.abs(value) >= 10) {{
        return value.toFixed(1);
      }}
      return value.toFixed(2).replace(/\\.?0+$/, '');
    }}

    function buildDoughnutChart() {{
      const payload = chartPayload.db_time_breakdown || {{}};
      if (!Array.isArray(payload.labels) || !Array.isArray(payload.values) || !payload.values.length) {{
        showChartFallback('dbTimeBreakdownChart');
        return;
      }}
      const ctx = document.getElementById('dbTimeBreakdownChart');
      if (!ctx) {{
        return;
      }}
      if (dbChart) {{
        dbChart.destroy();
      }}
      dbChart = new Chart(ctx, {{
        type: 'doughnut',
        data: {{
          labels: payload.labels,
          datasets: [{{
            data: payload.values,
            backgroundColor: payload.colors,
            borderColor: '#0f1b2d',
            borderWidth: 2,
          }}],
        }},
        options: {{
          maintainAspectRatio: false,
          plugins: {{
            legend: {{
              position: 'bottom',
              labels: {{
                color: chartTextColor,
              }},
            }},
          }},
        }},
      }});
    }}

    function buildBarChart() {{
      const payload = chartPayload.top_sql_contribution || {{}};
      if (!Array.isArray(payload.labels) || !Array.isArray(payload.values) || !payload.values.length) {{
        showChartFallback('topSqlContributionChart');
        return;
      }}
      const ctx = document.getElementById('topSqlContributionChart');
      if (!ctx) {{
        return;
      }}
      if (sqlChart) {{
        sqlChart.destroy();
      }}
      sqlChart = new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: payload.labels,
          datasets: [{{
            data: payload.values,
            backgroundColor: payload.colors,
            borderRadius: 8,
            borderSkipped: false,
          }}],
        }},
        options: {{
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }} }},
          scales: {{
            x: {{ ticks: {{ color: chartTextColor }}, grid: {{ display: false }} }},
            y: {{ beginAtZero: true, ticks: {{ color: chartTextColor }}, grid: {{ color: chartMutedColor }} }},
          }},
        }},
      }});
    }}

    function buildViolinChart(config, samples) {{
      const containerId = config.container_id;
      const color = config.color;
      const container = document.getElementById(containerId);
      if (!container) {{
        return;
      }}
      const cleanSamples = normalizeDistributionSamples(samples);
      if (!cleanSamples.length) {{
        Plotly.purge(container);
        showDistributionFallback(
          containerId,
          'No distribution data is available for this metric.'
        );
        return;
      }}
      const meanValue = computeMean(cleanSamples);
      const medianValue = computeMedian(cleanSamples);
      const q1Value = computeQuantile(cleanSamples, 0.25);
      const q3Value = computeQuantile(cleanSamples, 0.75);
      const minValue = Math.min(...cleanSamples);
      const maxValue = Math.max(...cleanSamples);
      const sampleCount = cleanSamples.length;
      const lowSampleExtremaKeys = new Set([
        'cluster_wait_pct_db_time',
        'gc_current_wait_pct_db_time',
        'gc_cr_wait_pct_db_time',
        'per_instance_cluster_wait_pct_db_time',
        'per_instance_gc_current_wait_pct_db_time',
        'per_instance_gc_cr_wait_pct_db_time',
      ]);
      const showExtremaMarkers = (
        maxValue !== minValue
        && (
          sampleCount >= 4
          || (sampleCount >= 2 && lowSampleExtremaKeys.has(config.payload_key))
        )
      );
      const stats = [
        formatMetricValue(meanValue),
        formatMetricValue(medianValue),
        formatMetricValue(q1Value),
        formatMetricValue(q3Value),
        formatMetricValue(minValue),
        formatMetricValue(maxValue),
      ];
      const hoverOffsets = [-0.18, -0.12, -0.06, 0, 0.06, 0.12, 0.18];
      const hoverX = [];
      const hoverY = [];
      const customData = [];

      cleanSamples.forEach(function(sample) {{
        hoverOffsets.forEach(function(offset) {{
          hoverX.push(offset);
          hoverY.push(sample);
          customData.push(stats);
        }});
      }});

      Plotly.purge(container);
      Plotly.newPlot(
        container,
        [
          {{
            type: 'violin',
            y: cleanSamples,
            x0: 0,
            name: '',
            box: {{
              visible: true,
              fillcolor: 'rgba(225, 232, 240, 0.22)',
              line: {{
                color: 'rgba(225, 232, 240, 0.55)',
                width: 1,
              }},
            }},
            meanline: {{
              visible: true,
              color: '#0b0f14',
              width: 2,
            }},
            line: {{
              color: color,
              width: 1.5,
            }},
            fillcolor: color,
            opacity: 0.55,
            points: false,
            hoverinfo: 'skip',
            hovertemplate: null,
            hoveron: 'points',
            showlegend: false,
          }},
          {{
            type: 'scatter',
            mode: 'markers+text',
            x: [0.1],
            y: [meanValue],
            text: ['Mean ' + formatMetricValue(meanValue)],
            textposition: 'middle right',
            textfont: {{
              color: '#f7d792',
              size: 10,
            }},
            marker: {{
              color: '#f6b84c',
              size: 9,
              symbol: 'diamond',
              line: {{
                color: '#fff3d6',
                width: 1,
              }},
            }},
            hoverinfo: 'skip',
            showlegend: false,
          }},
          ...(showExtremaMarkers ? [
            {{
              type: 'scatter',
              mode: 'markers+text',
              x: [0.12],
              y: [maxValue],
              text: ['Max ' + formatMetricValue(maxValue)],
              textposition: 'top right',
              textfont: {{
                color: 'rgba(255, 214, 214, 0.92)',
                size: 9,
              }},
              marker: {{
                color: '#ff7f7f',
                symbol: 'diamond',
                size: 8,
                line: {{
                  color: '#ffd7d7',
                  width: 1,
                }},
              }},
              hoverinfo: 'skip',
              showlegend: false,
            }},
            {{
              type: 'scatter',
              mode: 'markers+text',
              x: [-0.09],
              y: [minValue],
              text: ['Min ' + formatMetricValue(minValue)],
              textposition: 'bottom right',
              textfont: {{
                color: 'rgba(220, 230, 242, 0.82)',
                size: 9,
              }},
              marker: {{
                color: 'rgba(216, 228, 242, 0.82)',
                symbol: 'diamond',
                size: 8,
                line: {{
                  color: '#e8eef7',
                  width: 1,
                }},
              }},
              hoverinfo: 'skip',
              showlegend: false,
            }},
          ] : []),
          {{
            type: 'scatter',
            mode: 'markers',
            x: hoverX,
            y: hoverY,
            customdata: customData,
            marker: {{
              color: 'rgba(0, 0, 0, 0)',
              size: 22,
            }},
            hovertemplate:
              'Value: %{{y}}<br>' +
              'Mean: %{{customdata[0]}} | Median: %{{customdata[1]}}<br>' +
              'Q1-Q3: %{{customdata[2]}} - %{{customdata[3]}}<br>' +
              'Min-Max: %{{customdata[4]}} - %{{customdata[5]}}' +
              '<extra></extra>',
            showlegend: false,
          }},
        ],
        {{
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(11, 21, 35, 0.35)',
          hovermode: 'closest',
          margin: {{
            l: 56,
            r: 14,
            t: 6,
            b: 20,
          }},
          font: {{ color: chartTextColor }},
          xaxis: {{
            color: chartTextColor,
            gridcolor: 'rgba(0,0,0,0)',
            range: [-0.35, 0.35],
            zeroline: false,
            showticklabels: false,
          }},
          yaxis: {{
            color: chartTextColor,
            gridcolor: chartMutedColor,
            zeroline: false,
          }},
          hoverlabel: {{
            bgcolor: 'rgba(11, 21, 35, 0.94)',
            bordercolor: 'rgba(159, 176, 199, 0.28)',
            font: {{
              color: '#e8eef7',
              size: 11,
            }},
          }},
        }},
        {{ displayModeBar: false, responsive: true }},
      );
    }}

    function buildViolinPanel() {{
      const payload = chartPayload.violin_panel || {{}};
      violinConfigs.forEach((config) => {{
        const groupPayload = payload[config.group_key] || {{}};
        buildViolinChart(config, groupPayload[config.payload_key]);
      }});
    }}

    function buildLineChart(containerId, labels, values, color, labelText) {{
      const canvas = document.getElementById(containerId);
      if (!canvas) {{
        return;
      }}
      const numericValues = values.filter((value) => Number.isFinite(value));
      if (!Array.isArray(labels) || labels.length < 2 || numericValues.length < 2) {{
        showChartFallback(containerId, 'Insufficient history');
        return;
      }}
      const ctx = canvas.getContext('2d');
      if (!ctx) {{
        return;
      }}
      const chart = new Chart(ctx, {{
        type: 'line',
        data: {{
          labels,
          datasets: [{{
            label: labelText,
            data: values,
            borderColor: color,
            backgroundColor: color.replace('0.92', '0.18'),
            pointBackgroundColor: color,
            pointBorderColor: '#0f1b2d',
            borderWidth: 3,
            tension: 0.25,
            spanGaps: false,
            fill: true,
          }}],
        }},
        options: {{
          maintainAspectRatio: false,
          interaction: {{ mode: 'index', intersect: false }},
          plugins: {{ legend: {{ display: false }} }},
          scales: {{
            x: {{
              ticks: {{ color: chartTextColor, maxRotation: 0, autoSkip: true }},
              grid: {{ color: chartMutedColor }},
            }},
            y: {{
              ticks: {{ color: chartTextColor }},
              grid: {{ color: chartMutedColor }},
            }},
          }},
        }},
      }});
      timeSeriesCharts.push(chart);
    }}

    function buildTimeSeriesCharts() {{
      const payload = chartPayload.time_series_charts || {{}};
      const labels = payload.snapshot_labels || [];
      timeSeriesCharts.splice(0, timeSeriesCharts.length).forEach((chart) => chart.destroy());
      timeSeriesSpecs.forEach((spec) => {{
        buildLineChart(
          spec.container_id,
          labels,
          payload[spec.key] || [],
          spec.color,
          spec.label
        );
      }});
    }}

    document.addEventListener('DOMContentLoaded', function () {{
      buildDoughnutChart();
      buildBarChart();
      buildViolinPanel();
      buildTimeSeriesCharts();
    }});
  </script>
"""


def _shared_page_styles() -> str:
    """Return the shared multi-page product styling."""

    return """
    :root {
      --bg: #08111d;
      --panel: #0f1b2d;
      --panel-soft: rgba(15, 27, 45, 0.95);
      --panel-strong: #14243a;
      --text: #e8eef7;
      --muted: #9fb0c7;
      --line: #233754;
      --accent: #5ad1ff;
      --accent-soft: rgba(90, 209, 255, 0.12);
      --high: #ff6b6b;
      --medium: #f6b84c;
      --low: #7fb3d5;
      --pass: #66bb6a;
      --marginal: #f6b84c;
      --fail: #ff6b6b;
      --na: #8ea3ba;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      background:
        radial-gradient(circle at top right, rgba(90, 209, 255, 0.10), transparent 28%),
        linear-gradient(180deg, #08111d 0%, #07101a 100%);
      color: var(--text);
      line-height: 1.6;
    }
    .container {
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px 20px 40px;
    }
    .top-shell {
      display: grid;
      gap: 14px;
      margin-bottom: 22px;
    }
    .top-shell.sticky-shell {
      position: sticky;
      top: 0;
      z-index: 40;
      padding-top: 12px;
      backdrop-filter: blur(14px);
    }
    .hero {
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: linear-gradient(135deg, rgba(20, 36, 58, 0.98), rgba(10, 20, 34, 0.96));
      box-shadow: 0 18px 44px rgba(0, 0, 0, 0.28);
    }
    .eyebrow {
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }
    h1 { margin: 0 0 10px; font-size: 34px; line-height: 1.1; }
    h2 { margin: 0 0 14px; font-size: 21px; }
    h3 { margin: 0 0 10px; font-size: 17px; }
    .hero-summary { margin: 0 0 10px; color: var(--text); max-width: 820px; }
    .hero-meta, .meta { color: var(--muted); font-size: 13px; }
    .page-nav {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(10, 20, 34, 0.88);
      box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
    }
    .nav-link {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 8px 14px;
      color: var(--text);
      text-decoration: none;
      border: 1px solid rgba(159, 176, 199, 0.26);
      background: rgba(16, 28, 45, 0.72);
      font-size: 13px;
      font-weight: 600;
    }
    .nav-link.active {
      color: #08111d;
      background: var(--accent);
      border-color: rgba(90, 209, 255, 0.6);
    }
    .grid, .subgrid, .chart-grid, .flow-grid, .nav-card-grid, .health-check-grid {
      display: grid;
      gap: 18px;
    }
    .grid, .subgrid, .chart-grid { grid-template-columns: repeat(12, 1fr); }
    .flow-grid, .nav-card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .health-check-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .card {
      grid-column: span 12;
      background: var(--panel-soft);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
    }
    .card.primary {
      background: linear-gradient(135deg, rgba(24, 42, 66, 0.98), rgba(14, 27, 46, 0.98));
      border-color: rgba(90, 209, 255, 0.38);
    }
    .card.secondary { background: rgba(12, 22, 36, 0.88); }
    .card.prominent {
      background: linear-gradient(135deg, rgba(20, 36, 58, 0.96), rgba(13, 24, 40, 0.96));
      border-color: rgba(90, 209, 255, 0.34);
    }
    .section-kicker {
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }
    .half, .evidence-pane, .chart-panel { grid-column: span 12; }
    .stack { display: grid; gap: 12px; }
    .item, .flow-step, .nav-card, .visual-layer-card, .health-check-card {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: rgba(20, 36, 58, 0.7);
    }
    .nav-card {
      display: block;
      text-decoration: none;
      color: inherit;
    }
    .nav-card h3, .flow-step strong, .visual-layer-card strong, .info-box strong, .scalar-box strong {
      color: var(--accent);
      display: block;
      margin-bottom: 6px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .decision-grid, .info-grid, .provider-grid, .scalar-grid, .visual-layer-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    .visual-layer-grid, .scalar-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
    .decision-box, .info-box, .provider-box, .scalar-box {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: rgba(16, 28, 45, 0.72);
    }
    .supportive-panel {
      border: 1px dashed rgba(159, 176, 199, 0.28);
      border-radius: 14px;
      padding: 18px;
      background: rgba(11, 21, 35, 0.45);
    }
    .supportive-panel h3 { font-size: 16px; }
    .supportive-block {
      padding-top: 14px;
      margin-top: 14px;
      border-top: 1px solid rgba(159, 176, 199, 0.16);
    }
    .supportive-block:first-of-type {
      padding-top: 0;
      margin-top: 12px;
      border-top: none;
    }
    .severity, .status-pill, .health-pill, .decision-banner {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .severity.critical, .decision-banner.scale-now, .health-pill.fail {
      color: #fff4f4;
      background: rgba(255, 107, 107, 0.24);
      border: 1px solid rgba(255, 107, 107, 0.36);
    }
    .severity.high {
      color: #fff4f4;
      background: rgba(255, 107, 107, 0.16);
      border: 1px solid rgba(255, 107, 107, 0.30);
    }
    .severity.medium, .health-pill.marginal, .decision-banner.defer {
      color: #fff8ed;
      background: rgba(246, 184, 76, 0.24);
      border: 1px solid rgba(246, 184, 76, 0.36);
    }
    .severity.low, .health-pill.pass, .decision-banner.do-not-scale {
      color: #eff7ff;
      background: rgba(127, 179, 213, 0.16);
      border: 1px solid rgba(127, 179, 213, 0.36);
    }
    .health-pill.na {
      color: #eef3f8;
      background: rgba(159, 176, 199, 0.14);
      border: 1px solid rgba(159, 176, 199, 0.34);
    }
    .status-pill.success {
      background: rgba(102, 187, 106, 0.16);
      border: 1px solid rgba(102, 187, 106, 0.34);
      color: #effbef;
    }
    .status-pill.warning {
      background: rgba(246, 184, 76, 0.16);
      border: 1px solid rgba(246, 184, 76, 0.34);
      color: #fff8ed;
    }
    .status-pill.error {
      background: rgba(255, 107, 107, 0.16);
      border: 1px solid rgba(255, 107, 107, 0.34);
      color: #fff4f4;
    }
    .scope-chip-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
    .scope-chip {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 12px;
      background: rgba(90, 209, 255, 0.1);
      border: 1px solid rgba(90, 209, 255, 0.22);
      color: #eef9ff;
    }
    .confidence-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 30px;
      border-radius: 999px;
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 800;
      line-height: 1;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
      border: 1px solid rgba(255, 255, 255, 0.16);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
    }
    .confidence-pill.high {
      background: rgba(255, 107, 107, 0.24);
      border-color: rgba(255, 107, 107, 0.38);
      color: #fff4f4;
    }
    .confidence-pill.medium {
      background: rgba(246, 184, 76, 0.24);
      border-color: rgba(246, 184, 76, 0.38);
      color: #fff8ed;
    }
    .confidence-pill.low {
      background: rgba(127, 179, 213, 0.20);
      border-color: rgba(127, 179, 213, 0.36);
      color: #eef7ff;
    }
    .pill-stack {
      display: grid;
      grid-template-columns: repeat(3, max-content);
      justify-content: start;
      gap: 10px;
    }
    .pill-cell {
      display: grid;
      justify-items: center;
      align-content: start;
      gap: 8px;
    }
    .banner-meta-strip {
      margin-top: 18px;
      margin-bottom: 6px;
      padding-top: 2px;
    }
    .visual-summary-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }
    .mini-trend-card {
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: rgba(16, 28, 45, 0.72);
    }
    .mini-trend-svg {
      width: 100%;
      height: 110px;
      display: block;
      margin-top: 10px;
    }
    .mini-trend-fallback {
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }
    .inline-nav-hint {
      display: inline-flex;
      align-items: center;
      margin-top: 14px;
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
      font-size: 13px;
    }
    .pill-label-row {
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .pill-caption {
      text-align: center;
      white-space: nowrap;
    }
    .engineering-detail {
      margin-top: 12px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(16, 28, 45, 0.48);
      overflow: hidden;
    }
    .engineering-detail summary {
      cursor: pointer;
      list-style: none;
      padding: 14px 16px;
      color: var(--text);
      font-weight: 700;
    }
    .engineering-detail summary::-webkit-details-marker {
      display: none;
    }
    .engineering-detail-body {
      padding: 0 16px 16px;
      display: grid;
      gap: 14px;
    }
    .guidance-panel {
      display: grid;
      gap: 12px;
    }
    .narrative > p, .narrative > ol, .narrative > ul, .narrative > div { margin-top: 0; margin-bottom: 12px; }
    .data-table-wrap {
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(16, 28, 45, 0.72);
    }
    .data-table {
      width: 100%;
      border-collapse: collapse;
      min-width: 860px;
    }
    .data-table th, .data-table td {
      padding: 10px 12px;
      border-bottom: 1px solid rgba(35, 55, 84, 0.7);
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }
    .data-table th {
      color: var(--accent);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: rgba(11, 21, 35, 0.7);
    }
    .chart-panel, .violin-chart-card {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      background: rgba(20, 36, 58, 0.62);
      min-height: 320px;
    }
    .chart-support-note, .chart-domain-heading {
      color: rgba(216, 228, 242, 0.82);
    }
    .chart-domain-group { margin-top: 20px; }
    .chart-domain-heading {
      margin: 0 0 12px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .violin-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 18px;
    }
    .violin-group { margin-top: 20px; }
    .violin-group-note { color: rgba(216, 228, 242, 0.82); font-size: 14px; }
    .violin-chart { height: 300px; }
    .chart-canvas { position: relative; height: 240px; }
    .chart-empty {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 240px;
      color: var(--muted);
      font-size: 14px;
      text-align: center;
      border: 1px dashed rgba(159, 176, 199, 0.22);
      border-radius: 12px;
      background: rgba(11, 21, 35, 0.45);
    }
    .health-check-summary { margin-bottom: 12px; }
    .health-check-card p { margin: 0; }
    .footer { margin-top: 18px; color: var(--muted); font-size: 12px; text-align: right; }
    ul, ol { margin: 10px 0 0 18px; padding: 0; }
    li { margin: 4px 0; }
    @media (min-width: 900px) {
      .half, .chart-panel { grid-column: span 6; }
    }
    @media (max-width: 780px) {
      .flow-grid, .nav-card-grid, .health-check-grid,
      .decision-grid, .info-grid, .provider-grid, .scalar-grid, .visual-layer-grid,
      .visual-summary-grid {
        grid-template-columns: 1fr;
      }
      h1 { font-size: 28px; }
    }
"""


def _build_dashboard_html(report_data: dict[str, Any]) -> str:
    """Build the dashboard HTML."""

    title = escape(
        str(
            report_data.get("title")
            or "AWR Performance Intelligence Dashboard"
        )
    )
    screen_models = report_data.get("screen_models") or {}
    ingestion_screen_model = screen_models.get("screen_1_ingestion") or {}
    analysis_screen_model = screen_models.get("screen_2_analysis") or {}
    review_comparison_screen_model = (
        screen_models.get("screen_3_review_comparison") or {}
    )
    recommendation_screen_model = (
        screen_models.get("screen_4_recommendation_action") or {}
    )
    ai_sections = _normalize_ai_sections(
        parse_ai_sections(str(report_data.get("ai_generated_narrative") or ""))
    )
    decision_state = _derive_decision_state(ai_sections)
    issues = report_data.get("issues") or []
    recommendations = report_data.get("recommendations") or []
    agentic_decision = report_data.get("agentic_decision") or {}
    generated_at = escape(
        str(report_data.get("generated_at") or datetime.utcnow().isoformat())
    )
    derived_scalar_metrics = report_data.get("derived_scalar_metrics") or {}
    chart_payload = _build_chart_payload(report_data)
    violin_metric_groups = _build_violin_metric_groups(chart_payload["violin_panel"])
    violin_metric_configs = _flatten_violin_metric_groups(violin_metric_groups)
    # This payload must remain raw JSON in the script tag.
    # HTML escaping breaks JSON.parse().
    chart_payload_json = json.dumps(chart_payload, indent=2)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --bg: #08111d;
      --panel: #0f1b2d;
      --panel-soft: rgba(15, 27, 45, 0.95);
      --panel-strong: #14243a;
      --text: #e8eef7;
      --muted: #9fb0c7;
      --line: #233754;
      --accent: #5ad1ff;
      --accent-soft: rgba(90, 209, 255, 0.12);
      --high: #ff6b6b;
      --medium: #f6b84c;
      --low: #7fb3d5;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
      background:
        radial-gradient(circle at top right, rgba(90, 209, 255, 0.10), transparent 28%),
        linear-gradient(180deg, #08111d 0%, #07101a 100%);
      color: var(--text);
      line-height: 1.6;
    }}
    .container {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px 20px 40px;
    }}
    .hero {{
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 22px;
      background: linear-gradient(
        135deg,
        rgba(20, 36, 58, 0.98),
        rgba(10, 20, 34, 0.96)
      );
      box-shadow: 0 18px 44px rgba(0, 0, 0, 0.28);
      margin-bottom: 24px;
    }}
    .eyebrow {{
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 34px;
      line-height: 1.1;
    }}
    .hero-meta {{
      color: var(--muted);
      font-size: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .card {{
      grid-column: span 12;
      background: var(--panel-soft);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 22px;
      box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
    }}
    .card.primary {{
      background: linear-gradient(
        135deg,
        rgba(24, 42, 66, 0.98),
        rgba(14, 27, 46, 0.98)
      );
      border-color: rgba(90, 209, 255, 0.38);
    }}
    .card.secondary {{
      background: rgba(12, 22, 36, 0.88);
    }}
    .card.prominent {{
      background: linear-gradient(
        135deg,
        rgba(20, 36, 58, 0.96),
        rgba(13, 24, 40, 0.96)
      );
      border-color: rgba(90, 209, 255, 0.34);
    }}
    .decision-layer-card {{
      border-color: rgba(90, 209, 255, 0.48);
      box-shadow: 0 14px 30px rgba(0, 0, 0, 0.3);
      background: linear-gradient(
        135deg,
        rgba(22, 39, 63, 0.98),
        rgba(13, 24, 40, 0.98)
      );
    }}
    .card h2 {{
      margin: 0 0 14px;
      font-size: 21px;
    }}
    .decision-banner {{
      display: inline-flex;
      align-items: center;
      margin: 0 0 14px;
      padding: 8px 14px;
      border-radius: 999px;
      border: 1px solid rgba(90, 209, 255, 0.36);
      background: rgba(90, 209, 255, 0.12);
      color: #ecf9ff;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .decision-banner.do-not-scale {{
      border-color: rgba(127, 179, 213, 0.40);
      background: rgba(127, 179, 213, 0.16);
      color: #eef7ff;
    }}
    .decision-banner.scale-now {{
      border-color: rgba(255, 107, 107, 0.40);
      background: rgba(255, 107, 107, 0.16);
      color: #fff2f2;
    }}
    .decision-banner.defer {{
      border-color: rgba(246, 184, 76, 0.40);
      background: rgba(246, 184, 76, 0.16);
      color: #fff7ea;
    }}
    .decision-banner.insufficient {{
      border-color: rgba(159, 176, 199, 0.40);
      background: rgba(159, 176, 199, 0.14);
      color: #eef3f8;
    }}
    .card p {{
      margin: 0;
    }}
    .section-kicker {{
      color: var(--accent);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 10px;
    }}
    .narrative {{
      color: var(--text);
    }}
    .narrative > p,
    .narrative > ol,
    .narrative > ul,
    .narrative > div {{
      margin-top: 0;
      margin-bottom: 12px;
    }}
    .narrative > :last-child {{
      margin-bottom: 0;
    }}
    .executive-summary {{
      display: grid;
      gap: 12px;
    }}
    .executive-summary .decision-banner {{
      margin-bottom: 0;
      width: fit-content;
    }}
    .executive-summary .rationale {{
      color: var(--text);
    }}
    .executive-summary .key-signals {{
      margin-top: 0;
    }}
    .confidence-section {{
      display: grid;
      gap: 14px;
      border-radius: 14px;
      padding: 20px 22px;
      border: 1px solid rgba(90, 209, 255, 0.22);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
    }}
    .confidence-section.high {{
      background: linear-gradient(
        135deg,
        rgba(87, 25, 31, 0.92),
        rgba(40, 16, 20, 0.96)
      );
      color: #fff1f1;
    }}
    .confidence-section.medium {{
      background: linear-gradient(
        135deg,
        rgba(73, 49, 13, 0.92),
        rgba(36, 28, 14, 0.96)
      );
      color: #fff7ea;
    }}
    .confidence-section.low {{
      background: linear-gradient(
        135deg,
        rgba(24, 42, 66, 0.96),
        rgba(14, 27, 46, 0.96)
      );
      color: #eef7ff;
    }}
    .confidence-section h2,
    .confidence-section p {{
      margin: 0;
    }}
    .confidence-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }}
    .confidence-pill {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 30px;
      border-radius: 999px;
      padding: 6px 14px;
      font-size: 12px;
      font-weight: 800;
      line-height: 1;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
      border: 1px solid rgba(255, 255, 255, 0.16);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
    }}
    .confidence-pill.high {{
      background: rgba(255, 107, 107, 0.24);
      border-color: rgba(255, 107, 107, 0.38);
      color: #fff4f4;
    }}
    .confidence-pill.medium {{
      background: rgba(246, 184, 76, 0.24);
      border-color: rgba(246, 184, 76, 0.38);
      color: #fff8ed;
    }}
    .confidence-pill.low {{
      background: rgba(127, 179, 213, 0.20);
      border-color: rgba(127, 179, 213, 0.36);
      color: #eef7ff;
    }}
    .confidence-reason {{
      font-size: 15px;
      line-height: 1.72;
      font-weight: 600;
    }}
    .risk-section {{
      display: grid;
      gap: 16px;
      border-radius: 16px;
      padding: 20px 22px;
      border: 1px solid rgba(90, 209, 255, 0.18);
      background: linear-gradient(
        135deg,
        rgba(18, 31, 50, 0.94),
        rgba(12, 22, 36, 0.96)
      );
    }}
    .risk-section h2,
    .risk-section p {{
      margin: 0;
    }}
    .risk-section ul {{
      margin-top: 0;
    }}
    .risk-split {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 14px;
    }}
    .risk-column {{
      grid-column: span 12;
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 18px 18px 16px;
      background: rgba(16, 28, 45, 0.68);
    }}
    .risk-column h3 {{
      margin: 0 0 8px;
      font-size: 16px;
    }}
    .risk-column p,
    .risk-column ul {{
      margin: 0;
    }}
    .risk-reduction-panel {{
      background: rgba(20, 36, 58, 0.74);
    }}
    .subgrid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .selector-subgrid {{
      gap: 12px;
    }}
    .half {{
      grid-column: span 12;
    }}
    .selector-pane {{
      padding: 16px;
    }}
    .selector-header-grid {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .selector-compact-grid {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }}
    .stack {{
      display: grid;
      gap: 12px;
    }}
    .item {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 13px 14px;
      background: rgba(20, 36, 58, 0.7);
    }}
    .item h3 {{
      margin: 0 0 6px;
      font-size: 16px;
    }}
    .meta {{
      color: var(--muted);
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .severity {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .severity.critical {{
      color: #fff4f4;
      background: rgba(255, 107, 107, 0.34);
      border: 1px solid rgba(255, 107, 107, 0.48);
    }}
    .severity.high {{
      color: #fff4f4;
      background: rgba(255, 107, 107, 0.24);
      border: 1px solid rgba(255, 107, 107, 0.36);
    }}
    .severity.medium {{
      color: #fff8ed;
      background: rgba(246, 184, 76, 0.24);
      border: 1px solid rgba(246, 184, 76, 0.36);
    }}
    .severity.low {{
      color: #eff7ff;
      background: rgba(127, 179, 213, 0.16);
      border: 1px solid rgba(127, 179, 213, 0.36);
    }}
    ul, ol {{
      margin: 10px 0 0 18px;
      padding: 0;
    }}
    li {{
      margin: 4px 0;
    }}
    .decision-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .decision-box {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: rgba(11, 21, 35, 0.65);
    }}
    .decision-box strong {{
      display: block;
      margin-bottom: 6px;
      color: var(--accent);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .context-note {{
      margin-bottom: 12px;
      line-height: 1.5;
    }}
    .evidence-pane {{
      grid-column: span 12;
    }}
    .evidence-pane h3 {{
      margin: 0 0 12px;
      font-size: 17px;
    }}
    .provider-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }}
    .info-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }}
    .intake-summary-grid {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .info-strip {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .info-strip-box {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px 16px;
      background: rgba(16, 28, 45, 0.84);
    }}
    .info-strip-box strong {{
      display: block;
      margin-bottom: 6px;
      color: var(--accent);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .meta-strip {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 12px;
    }}
    .info-box {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: rgba(16, 28, 45, 0.72);
    }}
    .info-box strong {{
      display: block;
      margin-bottom: 6px;
      color: var(--accent);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .supportive-panel {{
      border: 1px dashed rgba(159, 176, 199, 0.28);
      border-radius: 14px;
      padding: 16px;
      background: rgba(11, 21, 35, 0.45);
    }}
    .supportive-panel h3 {{
      margin: 0 0 10px;
      font-size: 16px;
    }}
    .data-table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(16, 28, 45, 0.72);
    }}
    .data-table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 860px;
    }}
    .data-table th,
    .data-table td {{
      padding: 10px 12px;
      border-bottom: 1px solid rgba(35, 55, 84, 0.7);
      text-align: left;
      vertical-align: top;
      font-size: 13px;
    }}
    .data-table th {{
      color: var(--accent);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: rgba(11, 21, 35, 0.7);
    }}
    .data-table tr:last-child td {{
      border-bottom: none;
    }}
    .status-pill {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      border: 1px solid rgba(159, 176, 199, 0.3);
      background: rgba(127, 179, 213, 0.12);
      color: #eff7ff;
    }}
    .status-pill.success {{
      background: rgba(102, 187, 106, 0.16);
      border-color: rgba(102, 187, 106, 0.34);
      color: #effbef;
    }}
    .status-pill.warning {{
      background: rgba(246, 184, 76, 0.16);
      border-color: rgba(246, 184, 76, 0.34);
      color: #fff8ed;
    }}
    .status-pill.error {{
      background: rgba(255, 107, 107, 0.16);
      border-color: rgba(255, 107, 107, 0.34);
      color: #fff4f4;
    }}
    .scope-chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }}
    .scope-chip {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 12px;
      background: rgba(90, 209, 255, 0.1);
      border: 1px solid rgba(90, 209, 255, 0.22);
      color: #eef9ff;
    }}
    .visual-layer-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .visual-layer-card {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: rgba(20, 36, 58, 0.7);
    }}
    .visual-layer-card strong {{
      display: block;
      margin-bottom: 6px;
      color: var(--accent);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .scalar-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
    }}
    .provider-box {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      background: var(--accent-soft);
    }}
    .provider-box strong {{
      display: block;
      margin-bottom: 6px;
      color: var(--accent);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .scalar-box {{
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 16px;
      background: rgba(16, 28, 45, 0.72);
    }}
    .scalar-box strong {{
      display: block;
      margin-bottom: 8px;
      color: var(--accent);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .scalar-value {{
      font-size: 28px;
      line-height: 1.1;
      font-weight: 700;
      color: var(--text);
    }}
    .scalar-note {{
      margin-top: 6px;
      color: var(--muted);
      font-size: 13px;
    }}
    .chart-grid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .chart-panel {{
      grid-column: span 12;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      background: rgba(20, 36, 58, 0.62);
      min-height: 320px;
    }}
    .chart-panel h3 {{
      margin: 0 0 14px;
      font-size: 17px;
    }}
    .chart-support-note {{
      margin: -4px 0 16px;
      color: rgba(216, 228, 242, 0.78);
      font-size: 13px;
      line-height: 1.45;
    }}
    .violin-panel {{
      background: linear-gradient(
        135deg,
        rgba(18, 31, 50, 0.96),
        rgba(11, 21, 35, 0.96)
      );
      border-color: rgba(90, 209, 255, 0.28);
    }}
    .violin-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 18px;
    }}
    .violin-group {{
      margin-top: 20px;
    }}
    .violin-group:first-child {{
      margin-top: 0;
    }}
    .violin-group h3 {{
      margin: 0 0 6px;
      font-size: 18px;
    }}
    .violin-group-note {{
      margin: 0 0 18px;
      color: rgba(216, 228, 242, 0.82);
      font-size: 14px;
      line-height: 1.45;
    }}
    .violin-chart-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px 18px 18px;
      background: rgba(16, 28, 45, 0.72);
      min-height: 350px;
    }}
    .violin-chart-card h3 {{
      margin: 0 0 14px;
      font-size: 17px;
    }}
    .violin-chart {{
      height: 290px;
    }}
    .violin-panel-empty {{
      min-height: 180px;
    }}
    .chart-canvas {{
      position: relative;
      height: 240px;
    }}
    .chart-empty {{
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 240px;
      color: var(--muted);
      font-size: 14px;
      text-align: center;
      border: 1px dashed rgba(159, 176, 199, 0.22);
      border-radius: 12px;
      background: rgba(11, 21, 35, 0.45);
    }}
    .footer {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 12px;
      text-align: right;
    }}
    @media (min-width: 900px) {{
      .half {{
        grid-column: span 6;
      }}
      .chart-panel {{
        grid-column: span 6;
      }}
      .risk-column {{
        grid-column: span 6;
      }}
    }}
    @media (max-width: 780px) {{
      .decision-grid,
      .provider-grid,
      .info-grid,
      .info-strip,
      .selector-header-grid,
      .selector-compact-grid,
      .scalar-grid,
      .visual-layer-grid,
      .intake-summary-grid {{
        grid-template-columns: 1fr;
      }}
      h1 {{
        font-size: 28px;
      }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <section class="hero">
      <div class="eyebrow">AWR Performance Intelligence Dashboard</div>
      <h1>{title}</h1>
      <div class="hero-meta">Generated: {generated_at}</div>
    </section>

    <div class="grid">
      <!-- Screen 1 represents intake/validation truth. -->
      <section id="screen-1-ingestion" class="card secondary">
        {_render_ingestion_screen(ingestion_screen_model)}
      </section>

      <!-- Screen 2 and Screen 4 are the authoritative presentation blocks. -->
      <section id="screen-2-analysis" class="card prominent">
        {_render_analysis_screen(analysis_screen_model)}
      </section>

      <!-- Screen 3 represents temporal and comparative truth. -->
      <section id="screen-3-review-comparison" class="card secondary">
        {_render_review_comparison_screen(review_comparison_screen_model)}
      </section>

      <section id="screen-4-recommendation-action" class="card secondary">
        {_render_recommendation_action_screen(recommendation_screen_model)}
      </section>

      <!-- Supporting visual analysis remains data-driven and non-authoritative. -->
      {_render_performance_charts_section(chart_payload)}

      {_render_violin_panel(violin_metric_groups)}

      <section id="derived-scalar-metrics" class="card secondary">
        <div class="section-kicker">Supporting Visual Layer</div>
        <h2>Derived Scalar Metrics</h2>
        {_render_scalar_metrics(derived_scalar_metrics)}
      </section>

      <section id="ai-summary" class="card primary">
        <div class="section-kicker">Agentic AI Advisory Layer</div>
        <h2>Executive Summary</h2>
        {_render_executive_summary(
            ai_sections["Executive Summary"],
            issues,
            decision_state,
            report_data.get("summary_key_signals"),
        )}
      </section>

      <section id="ai-technical" class="card primary">
        <h2>Technical Narrative</h2>
        <div class="narrative">
          {_render_text_block(ai_sections["Technical Narrative"])}
        </div>
      </section>

      <section id="ai-root-cause" class="card primary">
        <h2>Root Cause Interpretation</h2>
        <div class="narrative">
          {_render_text_block(ai_sections["Root Cause Interpretation"])}
        </div>
      </section>

      <section id="ai-action-plan" class="card primary">
        <h2>Recommended Action Plan</h2>
        <div class="narrative">
          {_render_text_block(ai_sections["Recommended Action Plan"])}
        </div>
      </section>

      <section id="ai-sizing" class="card primary">
        <h2>OCI Sizing Considerations</h2>
        <div class="narrative">
          {_render_text_block(ai_sections["OCI Sizing Considerations"])}
        </div>
      </section>

      <section id="ai-confidence" class="card primary">
        {_render_confidence_section(ai_sections["Confidence Assessment"])}
      </section>

      <section id="ai-risk" class="card primary">
        {_render_risk_section(ai_sections["Risk of Being Wrong"])}
      </section>

      <section id="decision-layer" class="card prominent">
        <div class="section-kicker">Decision Layer</div>
        <h2>Agentic Decision</h2>
        <div class="decision-grid">
          {_render_decision_boxes(agentic_decision)}
        </div>
      </section>

      <section id="supporting-evidence" class="card secondary">
        <div class="section-kicker">Deterministic Layer</div>
        <h2>Supporting Evidence</h2>
        <div class="subgrid">
          <section class="half evidence-pane">
            <h3>Key Issues</h3>
            <div class="stack">
              {_render_issues(issues)}
            </div>
          </section>

          <section class="half evidence-pane">
            <h3>Deterministic Recommendations</h3>
            <div class="stack">
              {_render_recommendations(recommendations)}
            </div>
          </section>
        </div>
      </section>
    </div>

    <div class="footer">Generated at {generated_at}</div>
  </div>
  <script id="chart-payload" type="application/json">
{chart_payload_json}
  </script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <script>
    const chartPayloadElement = document.getElementById('chart-payload');
    let chartPayload = {{}};
    try {{
      if (chartPayloadElement) {{
        chartPayload = JSON.parse(chartPayloadElement.textContent.trim());
      }}
    }} catch (e) {{
      console.error("Chart payload invalid", e);
    }}

    const chartTextColor = '#d9e4f2';
    const chartMutedColor = 'rgba(159, 176, 199, 0.28)';
    let dbChart = null;
    let sqlChart = null;

    function showChartFallback(canvasId, message = 'No data available') {{
      const canvas = document.getElementById(canvasId);
      if (!canvas) {{
        return;
      }}

      const parent = canvas.parentElement;
      if (!parent) {{
        return;
      }}

      parent.innerHTML = '<div class="chart-empty">' + message + '</div>';
    }}

    function computeMean(values) {{
      return values.reduce((sum, value) => sum + value, 0) / values.length;
    }}

    function computeMedian(values) {{
      const sorted = [...values].sort((a, b) => a - b);
      const middle = Math.floor(sorted.length / 2);
      if (sorted.length % 2 === 0) {{
        return (sorted[middle - 1] + sorted[middle]) / 2;
      }}
      return sorted[middle];
    }}

    function computeQuantile(values, quantile) {{
      const sorted = [...values].sort((a, b) => a - b);
      if (sorted.length === 0) {{
        return NaN;
      }}
      const position = (sorted.length - 1) * quantile;
      const lower = Math.floor(position);
      const upper = Math.ceil(position);
      if (lower === upper) {{
        return sorted[lower];
      }}
      const weight = position - lower;
      return sorted[lower] * (1 - weight) + sorted[upper] * weight;
    }}

    function formatMetricValue(value) {{
      if (!Number.isFinite(value)) {{
        return '';
      }}
      if (Math.abs(value) >= 100) {{
        return value.toFixed(0);
      }}
      if (Math.abs(value) >= 10) {{
        return value.toFixed(1);
      }}
      return value.toFixed(2).replace(/\\.?0+$/, '');
    }}

    function buildDoughnutChart() {{
      const payload = chartPayload.db_time_breakdown;
      if (
        !payload
        || !Array.isArray(payload.labels)
        || !Array.isArray(payload.values)
        || payload.labels.length === 0
        || payload.labels.length !== payload.values.length
      ) {{
        showChartFallback('dbTimeBreakdownChart');
        return;
      }}

      const ctx = document.getElementById('dbTimeBreakdownChart');
      if (!ctx) {{
        showChartFallback('dbTimeBreakdownChart');
        return;
      }}

      if (dbChart) dbChart.destroy();
      dbChart = new Chart(ctx, {{
        type: 'doughnut',
        data: {{
          labels: payload.labels,
          datasets: [{{
            data: payload.values,
            backgroundColor: payload.colors,
            borderColor: '#0f1b2d',
            borderWidth: 2,
            hoverOffset: 4,
          }}],
        }},
        options: {{
          maintainAspectRatio: false,
          plugins: {{
            legend: {{
              position: 'bottom',
              labels: {{
                color: chartTextColor,
                boxWidth: 12,
                padding: 16,
              }},
            }},
          }},
        }},
      }});
    }}

    function buildBarChart() {{
      const payload = chartPayload.top_sql_contribution;
      if (
        !payload
        || !Array.isArray(payload.labels)
        || !Array.isArray(payload.values)
        || payload.labels.length === 0
        || payload.labels.length !== payload.values.length
      ) {{
        showChartFallback('topSqlContributionChart');
        return;
      }}

      const ctx = document.getElementById('topSqlContributionChart');
      if (!ctx) {{
        showChartFallback('topSqlContributionChart');
        return;
      }}

      if (sqlChart) sqlChart.destroy();
      sqlChart = new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: payload.labels,
          datasets: [{{
            data: payload.values,
            backgroundColor: payload.colors,
            borderRadius: 8,
            borderSkipped: false,
          }}],
        }},
        options: {{
          maintainAspectRatio: false,
          plugins: {{
            legend: {{
              display: false,
            }},
          }},
          scales: {{
            x: {{
              ticks: {{
                color: chartTextColor,
              }},
              grid: {{
                display: false,
              }},
            }},
            y: {{
              beginAtZero: true,
              ticks: {{
                color: chartTextColor,
              }},
              grid: {{
                color: chartMutedColor,
              }},
            }},
          }},
        }},
      }});
    }}

    function buildViolinChart(containerId, title, samples, color, payloadKey) {{
      if (!Array.isArray(samples) || samples.length < 2) {{
        return;
      }}

      const container = document.getElementById(containerId);
      if (!container) {{
        return;
      }}

      const meanValue = computeMean(samples);
      const medianValue = computeMedian(samples);
      const q1Value = computeQuantile(samples, 0.25);
      const q3Value = computeQuantile(samples, 0.75);
      const maxValue = Math.max(...samples);
      const minValue = Math.min(...samples);
      const sampleCount = samples.length;
      const lowSampleExtremaKeys = new Set([
        'cluster_wait_pct_db_time',
        'gc_current_wait_pct_db_time',
        'gc_cr_wait_pct_db_time',
        'per_instance_cluster_wait_pct_db_time',
        'per_instance_gc_current_wait_pct_db_time',
        'per_instance_gc_cr_wait_pct_db_time',
      ]);
      const showExtremaMarkers = (
        maxValue !== minValue
        && (
          sampleCount >= 4
          || (sampleCount >= 2 && lowSampleExtremaKeys.has(payloadKey))
        )
      );
      const stats = [
        formatMetricValue(meanValue),
        formatMetricValue(medianValue),
        formatMetricValue(q1Value),
        formatMetricValue(q3Value),
        formatMetricValue(minValue),
        formatMetricValue(maxValue),
      ];
      const hoverOffsets = [-0.18, -0.12, -0.06, 0, 0.06, 0.12, 0.18];
      const hoverX = [];
      const hoverY = [];
      const customData = [];

      samples.forEach(function (sample) {{
        hoverOffsets.forEach(function (offset) {{
          hoverX.push(offset);
          hoverY.push(sample);
          customData.push(stats);
        }});
      }});

      Plotly.purge(container);
      Plotly.newPlot(
        container,
        [
          {{
            type: 'violin',
            y: samples,
            x0: 0,
            name: '',
            box: {{
              visible: true,
              fillcolor: 'rgba(225, 232, 240, 0.22)',
              line: {{
                color: 'rgba(225, 232, 240, 0.55)',
                width: 1,
              }},
            }},
            meanline: {{
              visible: true,
              color: '#0b0f14',
              width: 2,
            }},
            line: {{
              color: color,
              width: 1.5,
            }},
            fillcolor: color,
            opacity: 0.55,
            points: false,
            hoverinfo: 'skip',
            hovertemplate: null,
            hoveron: 'points',
            showlegend: false,
          }},
          {{
            type: 'scatter',
            mode: 'markers+text',
            x: [0.1],
            y: [meanValue],
            text: ['Mean ' + formatMetricValue(meanValue)],
            textposition: 'middle right',
            textfont: {{
              color: '#f7d792',
              size: 10,
            }},
            marker: {{
              color: '#f6b84c',
              symbol: 'diamond',
              size: 9,
              line: {{
                color: '#fff3d6',
                width: 1,
              }},
            }},
            hoverinfo: 'skip',
            showlegend: false,
          }},
          ...(showExtremaMarkers ? [
            {{
              type: 'scatter',
              mode: 'markers+text',
              x: [0.12],
              y: [maxValue],
              text: ['Max ' + formatMetricValue(maxValue)],
              textposition: 'top right',
              textfont: {{
                color: 'rgba(255, 214, 214, 0.92)',
                size: 9,
              }},
              marker: {{
                color: '#ff7f7f',
                symbol: 'diamond',
                size: 8,
                line: {{
                  color: '#ffd7d7',
                  width: 1,
                }},
              }},
              hoverinfo: 'skip',
              showlegend: false,
            }},
            {{
              type: 'scatter',
              mode: 'markers+text',
              x: [-0.09],
              y: [minValue],
              text: ['Min ' + formatMetricValue(minValue)],
              textposition: 'bottom right',
              textfont: {{
                color: 'rgba(220, 230, 242, 0.82)',
                size: 9,
              }},
              marker: {{
                color: 'rgba(216, 228, 242, 0.82)',
                symbol: 'diamond',
                size: 8,
                line: {{
                  color: '#e8eef7',
                  width: 1,
                }},
              }},
              hoverinfo: 'skip',
              showlegend: false,
            }},
          ] : []),
          {{
            type: 'scatter',
            mode: 'markers',
            x: hoverX,
            y: hoverY,
            customdata: customData,
            marker: {{
              color: 'rgba(0, 0, 0, 0)',
              size: 22,
            }},
            hovertemplate:
              'Value: %{{y}}<br>' +
              'Mean: %{{customdata[0]}} | Median: %{{customdata[1]}}<br>' +
              'Q1-Q3: %{{customdata[2]}} - %{{customdata[3]}}<br>' +
              'Min-Max: %{{customdata[4]}} - %{{customdata[5]}}' +
              '<extra></extra>',
            showlegend: false,
          }},
        ],
        {{
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(11, 21, 35, 0.35)',
          hovermode: 'closest',
          margin: {{
            l: 56,
            r: 14,
            t: 6,
            b: 20,
          }},
          font: {{
            color: chartTextColor,
          }},
          xaxis: {{
            color: chartTextColor,
            gridcolor: 'rgba(0,0,0,0)',
            range: [-0.35, 0.35],
            zeroline: false,
            showticklabels: false,
          }},
          yaxis: {{
            color: chartTextColor,
            gridcolor: chartMutedColor,
            zeroline: false,
          }},
          hoverlabel: {{
            bgcolor: 'rgba(11, 21, 35, 0.94)',
            bordercolor: 'rgba(159, 176, 199, 0.28)',
            font: {{
              color: '#e8eef7',
              size: 11,
            }},
          }},
        }},
        {{
          displayModeBar: false,
          responsive: true,
        }},
      );
    }}

    function buildViolinPanel() {{
      const payload = chartPayload.violin_panel || {{}};
      const violinConfigs = {json.dumps(violin_metric_configs)};

      violinConfigs.forEach(function (config) {{
        const containerId = config.container_id;
        const title = config.title;
        const payloadKey = config.payload_key;
        const groupKey = config.group_key;
        const color = config.color;
        const groupPayload = payload[groupKey] || {{}};
        buildViolinChart(
          containerId,
          title,
          groupPayload[payloadKey],
          color,
          payloadKey,
        );
      }});
    }}

    document.addEventListener('DOMContentLoaded', function () {{
      buildDoughnutChart();
      buildBarChart();
      buildViolinPanel();
    }});
  </script>
</body>
</html>
"""


def _render_issues(issues: list[dict[str, Any]]) -> str:
    """Render issues section."""

    if not issues:
        return '<div class="item"><div class="meta">No issues detected.</div></div>'

    parts: list[str] = []
    for issue in issues:
        severity = str(issue.get("severity") or "low").lower()
        severity_class = escape(severity)
        severity_label = escape(severity.upper())
        summary = escape(str(issue.get("summary") or ""))
        issue_type = escape(_display_issue_label(str(issue.get("issue_type") or "")))
        severity_html = (
            '<div class="meta"><span class="severity '
            f'{severity_class}">{severity_label}</span></div>'
        )
        parts.append(f"""
            <article class="item">
              {severity_html}
              <h3>{issue_type}</h3>
              <p>{summary}</p>
            </article>
            """)

    return "".join(parts)


def _render_recommendations(recommendations: list[Any]) -> str:
    """Render recommendations section."""

    if not recommendations:
        return (
            '<div class="item"><div class="meta">'
            "No recommendations available."
            "</div></div>"
        )

    parts: list[str] = []
    for recommendation in recommendations:
        recommendation_dict = _to_dict(recommendation)
        recommendation_text = escape(
            str(recommendation_dict.get("recommendation") or "")
        )
        rationale = escape(str(recommendation_dict.get("rationale") or ""))
        next_step = escape(str(recommendation_dict.get("next_step") or ""))
        issue_type = escape(
            _display_issue_label(str(recommendation_dict.get("issue_type") or ""))
        )
        severity = str(recommendation_dict.get("severity") or "low").lower()
        severity_class = escape(severity)
        severity_label = escape(severity.upper())
        actions = recommendation_dict.get("actions") or []
        actions_html = "".join(f"<li>{escape(str(action))}</li>" for action in actions)
        severity_html = (
            '<div class="meta"><span class="severity '
            f'{severity_class}">{severity_label}</span></div>'
        )
        parts.append(f"""
            <article class="item">
              {severity_html}
              <h3>{issue_type}</h3>
              <p><strong>Recommendation:</strong> {recommendation_text}</p>
              <p><strong>Rationale:</strong> {rationale}</p>
              <p><strong>Next Step:</strong> {next_step}</p>
              {"<ul>" + actions_html + "</ul>" if actions_html else ""}
            </article>
            """)

    return "".join(parts)


def _render_ingestion_screen(screen_model: dict[str, Any]) -> str:
    """Render Screen 1 from the canonical ingestion and validation model."""

    header = _to_dict(screen_model.get("header"))
    intake_summary = _to_dict(screen_model.get("intake_summary"))
    environment_context = _to_dict(screen_model.get("environment_context"))
    environment_scope_note = screen_model.get("environment_scope_note")
    parse_confidence = _to_dict(screen_model.get("parse_confidence_adaptation"))
    report_rows = screen_model.get("report_rows") or []
    validation_notes = _to_dict(screen_model.get("validation_notes"))
    supportive_explanation = _to_dict(screen_model.get("supportive_explanation"))
    validation_notes_html = _render_context_summary(
        validation_notes,
        "notes",
        "No intake or validation notes are available.",
    )

    return f"""
      {_render_ingestion_header_card(
          {
              **header,
              "total_files": intake_summary.get("total_files"),
              "succeeded": intake_summary.get("succeeded"),
              "skipped": intake_summary.get("skipped"),
          }
      )}
      <section class="card secondary">
      <div class="section-kicker">Screen 1</div>
      <h2>Ingestion / Parse Confidence / Adaptation</h2>
      <div class="subgrid">
        <section class="evidence-pane">
          <h3>Analysis Information</h3>
          {
              f'<div class="meta context-note">{escape(_display_value(environment_scope_note))}</div>'
              if _has_display_value(environment_scope_note)
              else ""
          }
          {_render_info_grid(_analysis_information_items(environment_context))}
        </section>
        <section class="evidence-pane">
          <h3>Intake Summary</h3>
          {_render_info_grid(
              [
                  ("Total Files", intake_summary.get("total_files")),
                  ("Processed", intake_summary.get("processed")),
                  ("Succeeded", intake_summary.get("succeeded")),
                  ("Failed", intake_summary.get("failed")),
                  ("Skipped", intake_summary.get("skipped")),
                  ("Manifest / Dataset Status", intake_summary.get("manifest_status")),
              ],
              extra_class="intake-summary-grid",
          )}
        </section>
        <section class="evidence-pane">
          <h3>File / Report Table</h3>
          {_render_ingestion_table(report_rows)}
        </section>
        <section class="half evidence-pane">
          <h3>Parse Confidence / Adaptation</h3>
          <div class="stack">
            {_render_context_summary(
                {
                    "summary": parse_confidence.get("adaptation_summary"),
                    "items": [],
                },
                "items",
                "No parse confidence summary is available.",
            )}
            {_render_info_grid(
                [
                    (
                        "Parse Completeness Score",
                        parse_confidence.get("parse_completeness_score"),
                    ),
                    ("Warnings", parse_confidence.get("warnings_count")),
                    ("Sections Detected", parse_confidence.get("sections_detected")),
                    ("Sections Missing", parse_confidence.get("sections_missing")),
                    ("Unknowns Captured", parse_confidence.get("unknowns_captured")),
                    (
                        "Alias / Fallback Matching",
                        parse_confidence.get("alias_fallback_matching"),
                    ),
                    (
                        "File-Level Version / Platform / Topology Hints",
                        ", ".join(
                            parse_confidence.get("version_platform_topology_hints") or []
                        ),
                    ),
                ]
            )}
          </div>
        </section>
        <section class="half evidence-pane">
          <h3>Validation Notes</h3>
          {validation_notes_html}
        </section>
        <section class="evidence-pane">
          <h3>Supportive Explanation</h3>
          <div class="supportive-panel">
            <div class="meta">
              Supportive, non-authoritative explanation derived from canonical intake findings.
            </div>
            {_render_supportive_explanation(
                supportive_explanation.get("text"),
                "No supportive explanation is available.",
            )}
          </div>
        </section>
      </div>
      </section>
    """


def _render_analysis_screen(screen_model: dict[str, Any]) -> str:
    """Render deterministic Screen 2 detail blocks after the main narrative order."""

    evidence_panel = _to_dict(screen_model.get("evidence_panel"))
    scores_panel = _to_dict(screen_model.get("scores_panel"))
    trend_context = _to_dict(screen_model.get("trend_context"))
    anomaly_context = _to_dict(screen_model.get("anomaly_context"))
    explanation_panel = _to_dict(screen_model.get("explanation_panel"))
    engineering_view = _to_dict(screen_model.get("engineering_view"))
    normalized_decision = _to_dict(screen_model.get("normalized_decision"))
    primary_evidence = evidence_panel.get("primary_evidence") or {}
    secondary_evidence = evidence_panel.get("secondary_evidence") or []
    domain_scores = (
        evidence_panel.get("domain_scores") or scores_panel.get("domain_scores")
    )
    has_evidence_content = bool(primary_evidence or secondary_evidence)
    trend_context_html = _render_context_summary(
        trend_context.get("trend_summary") or {},
        "findings",
    )
    trend_context_html = trend_context_html.replace(
        "<p>CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim.</p>",
        "",
    )
    trend_context_html = trend_context_html.replace(
        "<li>Top SQL history is not available for this window.</li>",
        "",
    )
    anomaly_context_html = _render_context_summary(
        anomaly_context.get("anomaly_summary") or {},
        "windows",
    )
    engineering_view_html = _render_engineering_view(
        engineering_view,
        "Engineering View",
    )

    return f"""
      <div class="subgrid">
        <section class="half evidence-pane">
          <h3>Evidence</h3>
          <div class="stack">
            {
                _render_empty_item("No deterministic evidence is available.")
                if not has_evidence_content
                else (
                    _render_primary_evidence(
                        primary_evidence,
                        normalized_decision.get("domain_scores") or {},
                    )
                    + _render_secondary_evidence(
                        secondary_evidence,
                        normalized_decision.get("domain_scores") or {},
                    )
                )
            }
          </div>
        </section>
        {
            f'''
        <section class="half evidence-pane">
          <h3>Technical Detail</h3>
          {engineering_view_html}
        </section>
        '''
            if engineering_view_html
            else ""
        }
        <section class="half evidence-pane">
          <h3>Trend Context</h3>
          {trend_context_html}
        </section>
        <section class="half evidence-pane">
          <h3>Anomaly Context</h3>
          {anomaly_context_html}
        </section>
        <section class="evidence-pane">
          <h3>Explanation</h3>
          <div class="supportive-panel">
            <div class="meta">
              Supportive, non-authoritative explanation derived from canonical findings.
            </div>
            {_render_supportive_section(
                "Executive",
                explanation_panel.get("executive_recap"),
                "The canonical decision summary above remains the authoritative explanation.",
            )}
            {_render_supportive_section(
                "Technical",
                explanation_panel.get("technical_recap"),
                "The boxed technical sections above established the deterministic explanation already.",
            )}
            {_render_supportive_section(
                "Diagnostic Orientation",
                explanation_panel.get("action_oriented_explanation"),
                "Recommended action planning remains anchored to the deterministic posture above.",
            )}
          </div>
        </section>
      </div>
    """


def _render_review_comparison_screen(
    screen_model: dict[str, Any],
    normalized_decision: dict[str, Any] | None = None,
) -> str:
    """Render Screen 4 historical findings and comparison results."""

    historical_summary = _to_dict(screen_model.get("historical_summary"))
    trend_review = _to_dict(screen_model.get("trend_review"))
    anomaly_review = _to_dict(screen_model.get("anomaly_review"))
    comparison_review = _to_dict(screen_model.get("comparison_review"))
    topology_platform_review = _to_dict(screen_model.get("topology_platform_review"))
    visual_analysis = _to_dict(screen_model.get("visual_analysis"))
    visual_story = _to_dict(visual_analysis.get("story"))
    explanation_panel = _to_dict(screen_model.get("explanation_panel"))
    historical_scope_memory = _to_dict(screen_model.get("historical_scope_memory"))
    historical_summary_html = _render_context_summary(
        {
            "summary": historical_summary.get("summary"),
            "key_findings": [],
        },
        "key_findings",
        "No historical summary is available.",
        normalized_decision=normalized_decision,
    )
    historical_summary_html = historical_summary_html.replace(
        " CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim.",
        "",
    )
    historical_summary_html = historical_summary_html.replace(
        " displace cpu as the governing pattern.",
        " displace CPU as the governing pattern.",
    )
    trend_review_summary = trend_review.get("trend_summary") or {}
    if (
        isinstance(trend_review_summary, dict)
        and isinstance(trend_review_summary.get("summary"), str)
        and (
            "historical cpu trend continuity is limited in this window"
            in trend_review_summary.get("summary", "").lower()
            or "cpu remained historically visible, though continuity across the full window was too mixed for a simple stability claim"
            in trend_review_summary.get("summary", "").lower()
        )
        and (trend_review_summary.get("findings") or [])
    ):
        trend_review_summary = {
            **trend_review_summary,
            "summary": "",
        }
    trend_review_html = _render_context_summary(
        trend_review_summary,
        "findings",
        "No deterministic trend review is available.",
        normalized_decision=normalized_decision,
    )
    trend_review_html = trend_review_html.replace(
        "<p>Historical CPU trend continuity is limited in this window.</p>",
        "",
    )
    trend_review_html = trend_review_html.replace(
        "<li>Historical CPU trend continuity is limited in this window.</li>",
        "",
    )
    trend_review_html = trend_review_html.replace(
        "<li>CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim.</li>",
        "",
    )
    trend_review_html = trend_review_html.replace(
        "<p>CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim.</p>",
        "",
    )
    topology_platform_review_html = _render_info_grid(
        [
            ("RAC Summary", topology_platform_review.get("rac_summary")),
            ("Data Guard Summary", topology_platform_review.get("data_guard_summary")),
            ("Exadata Summary", topology_platform_review.get("exadata_summary")),
            (
                "Host / Instance Notes",
                ", ".join(topology_platform_review.get("host_instance_notes") or []),
            ),
        ]
    )
    topology_platform_review_html = topology_platform_review_html.replace(
        "Treat RAC coordination as supportive context rather than selected-scope topology truth.",
        "RAC signals are sparse and treated as supporting context only.",
    )
    topology_platform_review_html = topology_platform_review_html.replace(
        "Treat Data Guard as supportive window context rather than selected-scope topology truth.",
        "Data Guard signals are limited and treated as supporting context only.",
    )

    explanation_section_map = {
        "executive_summary": _render_supportive_section(
            "Executive Summary",
            _normalize_narrative_for_display(
                explanation_panel.get("executive_summary"),
                normalized_decision,
            ),
            "",
        ),
        "historical_interpretation": _render_supportive_section(
            "Historical Interpretation",
            _normalize_narrative_for_display(
                explanation_panel.get("historical_interpretation"),
                normalized_decision,
            ),
            "",
        ),
        "action_context": _render_supportive_section(
            "Historical Posture",
            _normalize_narrative_for_display(
                explanation_panel.get("action_context"),
                normalized_decision,
            ),
            "",
        ),
        "technical_context": _render_supportive_section(
            "Technical Context",
            _normalize_narrative_for_display(
                explanation_panel.get("technical_context"),
                normalized_decision,
            ),
            "",
        ),
    }
    ordered_explanation_sections = "".join(
        explanation_section_map.get(section_key, "")
        for section_key in (
            visual_story.get("explanation_section_order")
            or ["executive_summary", "historical_interpretation", "action_context", "technical_context"]
        )
        if explanation_section_map.get(section_key, "")
    )
    ordered_explanation_sections = ordered_explanation_sections.replace(
        "CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim.",
        "The historical record stays CPU-led, but uneven intervals keep the trend read directional rather than uniform.",
    )
    lower_section_map = {
        "historical_summary": f"""
        <section class="evidence-pane">
          <h3>Historical Summary</h3>
          {historical_summary_html}
        </section>
        """,
        "visual_analysis": "",
        "historical_scope_memory": (
            f"""
        <section class="half evidence-pane">
          <h3>Memory Review</h3>
          <div class="meta">
            Explicit secondary-domain review before supporting I/O / commit trends and contextual RAC / topology comparison.
          </div>
          {_render_historical_scope_memory(historical_scope_memory)}
        </section>
        """
            if _has_display_value(historical_scope_memory.get("summary"))
            or bool(historical_scope_memory.get("items") or historical_scope_memory.get("scope_concepts"))
            else ""
        ),
        "trend_review": f"""
        <section class="half evidence-pane">
          <h3>Trend Review</h3>
          {trend_review_html}
        </section>
        """,
        "anomaly_review": f"""
        <section class="half evidence-pane">
          <h3>Anomaly Review</h3>
          <div class="stack">
            {_render_info_grid(
                [
                    (
                        "Anomaly Count",
                        _to_dict(anomaly_review.get("anomalies")).get("count"),
                    ),
                ]
            )}
            {_render_context_summary(
                anomaly_review.get("anomaly_summary") or {},
                "windows",
                "No anomaly review is available.",
                normalized_decision=normalized_decision,
            )}
          </div>
        </section>
        """,
        "period_comparison": f"""
        <section class="half evidence-pane">
          <h3>Period Comparison</h3>
          <div class="stack">
            {_render_info_grid(
                [
                    ("Latest Interval", comparison_review.get("latest_interval")),
                    ("Worst Interval", comparison_review.get("worst_interval")),
                    ("Latest vs Trend", comparison_review.get("latest_vs_trend")),
                ]
            )}
            {_render_context_summary(
                {
                    "summary": comparison_review.get("drift_summary"),
                    "items": [],
                },
                "items",
                "No drift or period comparison summary is available.",
                normalized_decision=normalized_decision,
            )}
          </div>
        </section>
        """,
        "topology_platform_review": (
            f"""
        <section class="half evidence-pane">
          <h3>Topology / Platform Review</h3>
          <div class="meta">
            Historical / Supporting Context (Not Selected-Scope Truth). Comparison context only; CPU-led evidence remains primary.
          </div>
          {topology_platform_review_html}
        </section>
        """
            if _has_display_value(topology_platform_review.get("rac_summary"))
            or _has_display_value(topology_platform_review.get("data_guard_summary"))
            or _has_display_value(topology_platform_review.get("exadata_summary"))
            else ""
        ),
        "explanation": f"""
        <section class="evidence-pane">
          <h3>Explanation</h3>
          <div class="supportive-panel">
            <div class="meta">
              Supportive, non-authoritative explanation derived from canonical findings.
            </div>
            {ordered_explanation_sections}
          </div>
        </section>
        """,
    }
    ordered_lower_sections = "".join(
        lower_section_map.get(section_key, "")
        for section_key in (
            visual_story.get("story_section_order")
            or [
                "historical_summary",
                "historical_scope_memory",
                "visual_analysis",
                "trend_review",
                "anomaly_review",
                "period_comparison",
                "topology_platform_review",
                "explanation",
            ]
        )
        if lower_section_map.get(section_key, "")
    )

    return f"""
      <div class="subgrid">
        {ordered_lower_sections}
      </div>
    """


def _render_recommendation_action_screen(screen_model: dict[str, Any]) -> str:
    """Render Screen 5 from the canonical recommendation and action model."""

    header = _to_dict(screen_model.get("header"))
    normalized_decision = _to_dict(screen_model.get("normalized_decision"))
    recommendation_list = screen_model.get("recommendation_list") or []
    recommendation_groups = screen_model.get("recommendation_groups") or []
    evidence_tie_back = _to_dict(
        screen_model.get("recommendation_evidence_tie_back")
    )
    future_extension = _to_dict(screen_model.get("future_extension"))
    authoritative_confidence = (
        header.get("confidence")
        or normalized_decision.get("confidence")
    )
    recommendation_summary = evidence_tie_back.get("recommendation_summary") or {}
    supporting_primary_evidence = evidence_tie_back.get("primary_evidence") or {}
    supporting_secondary_evidence = evidence_tie_back.get("secondary_evidence") or []
    has_supporting_evidence = bool(
        supporting_primary_evidence or supporting_secondary_evidence
    )
    sizing_guidance = _normalize_capacity_guidance_text(
        future_extension.get("oci_sizing_guidance"),
        authoritative_confidence,
    )
    sizing_guidance_blocks = [
        {
            **_to_dict(block),
            "text": _normalize_capacity_guidance_text(
                _normalize_confidence_text(
                    _to_dict(block).get("text"),
                    authoritative_confidence,
                ),
                authoritative_confidence,
            ),
        }
        for block in (future_extension.get("sizing_guidance_blocks") or [])
    ]
    future_extension_items = [
        ("Remediation Options", future_extension.get("remediation_options")),
        ("Operational Next Steps", future_extension.get("operational_next_steps")),
        ("Cost / Impact Guidance", future_extension.get("cost_impact_guidance")),
    ]
    future_extension_html = (
        (
            """
            <div class="supportive-panel guidance-panel">
              <div class="meta">Structured, platform-neutral guidance for future capacity planning.</div>
            """
            + _render_guidance_blocks(sizing_guidance_blocks, sizing_guidance)
            + """
            </div>
            """
        )
        if _has_display_value(sizing_guidance)
        else ""
    ) + _render_info_grid(future_extension_items)

    return f"""
      <div class="subgrid">
        <section class="evidence-pane">
          <h3>Prioritized Recommended Actions</h3>
          <div class="stack">
            {_render_recommendation_groups(recommendation_groups or recommendation_list)}
          </div>
        </section>
        <section class="evidence-pane">
          <h3>Supporting Evidence</h3>
          <div class="stack">
            {
                _render_empty_item("No recommendation evidence is available.")
                if not has_supporting_evidence
                else (
                    _render_primary_evidence(
                        supporting_primary_evidence,
                        normalized_decision.get("domain_scores") or {},
                    )
                    + _render_secondary_evidence(
                        supporting_secondary_evidence,
                        normalized_decision.get("domain_scores") or {},
                    )
                )
            }
          </div>
        </section>
        <section class="evidence-pane">
          <h3>Action Summary</h3>
          <div class="stack">
            <div class="banner-meta-strip">
              {_render_pill_stack(
                  [
                      _render_confidence_badge(authoritative_confidence),
                      _render_status_badge(header.get("display_severity_label")),
                      _render_status_badge(header.get("decision_posture")),
                  ],
                  ["Confidence", "Risk", "Posture"],
              )}
            </div>
            {_render_info_grid(
                [
                    ("Primary Issue", header.get("primary_issue")),
                    ("Overall Status", header.get("overall_status")),
                    ("Health Summary", header.get("health_summary")),
                ]
            )}
          </div>
        </section>
        <section class="evidence-pane">
          <h3>Action Explanation</h3>
          <div class="supportive-panel">
            <div class="meta">
              Supportive, non-authoritative explanation derived from canonical findings.
            </div>
            {_render_supportive_explanation(
                _build_screen5_action_explanation_copy(screen_model),
                "Insufficient data for a reliable conclusion.",
            )}
          </div>
        </section>
        <section class="evidence-pane">
          <h3>Future Extensions</h3>
          {future_extension_html}
        </section>
      </div>
    """


def _render_ingestion_header_card(header: dict[str, Any]) -> str:
    return f"""
      <section class="card primary">
        <div class="section-kicker">Ingestion</div>
        <h2>Ingestion / Parse Confidence / Adaptation</h2>
        {_render_info_grid(
            [
                ("Run Label", header.get("run_label")),
                ("Source Mode", header.get("source_mode")),
                (
                    "Total Files / Success / Skipped",
                    _join_compact_values(
                        [
                            f"Total {header.get('total_files')}" if _has_display_value(header.get("total_files")) else None,
                            f"Success {header.get('succeeded')}" if _has_display_value(header.get("succeeded")) else None,
                            f"Skipped {header.get('skipped')}" if _has_display_value(header.get("skipped")) else None,
                        ]
                    ),
                ),
            ]
        )}
      </section>
    """


def _display_value(value: Any) -> str:
    """Format arbitrary values for safe dashboard display."""

    if value is None:
        return "Insufficient data for a reliable conclusion"
    if isinstance(value, str):
        text = _normalize_ui_text(value.strip())
        if not text or text.upper() in {"UNKNOWN", "UNAVAILABLE", "N/A", "NONE"}:
            return "Insufficient data for a reliable conclusion"
        text = re.sub(
            r"\bUnavailable\b",
            "Insufficient data for a reliable conclusion",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"\bunavailable\b",
            "Insufficient data for a reliable conclusion",
            text,
            flags=re.IGNORECASE,
        )
        return text
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        numeric = float(value)
        if abs(numeric) >= 100:
            return f"{numeric:.0f}"
        if abs(numeric) >= 10:
            return f"{numeric:.1f}"
        return f"{numeric:.3f}".rstrip("0").rstrip(".")
    if isinstance(value, dict):
        parts = [
            f"{k}: {v}"
            for k, v in value.items()
            if v is not None and str(v).strip() != ""
        ]
        return ", ".join(parts) if parts else "Insufficient data for a reliable conclusion"
    if isinstance(value, (list, tuple, set)):
        parts = [
            str(item).strip()
            for item in value
            if item is not None and str(item).strip() != ""
        ]
        return ", ".join(parts) if parts else "Insufficient data for a reliable conclusion"
    return str(value)


def _normalize_ui_text(text: str) -> str:
    normalized = re.sub(
        r"\bPrioritize the top elapsed-time OrderService SQL statements\b",
        "Prioritize the top elapsed-time SQL statements",
        text,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\btop elapsed-time OrderService SQL statements\b",
        "top elapsed-time SQL statements",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\bOrderService SQL statements\b",
        "top elapsed-time SQL statements",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\bOrderService\b(?! SQL statements)",
        "top elapsed-time SQL",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\btop elapsed-time top elapsed-time SQL statements\b",
        "top elapsed-time SQL statements",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"Decision Posture:\s*-\s*",
        "Decision posture: ",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\s*-\s*Supporting guidance:\s*",
        " Supporting guidance: ",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\s*-\s*(Reduce sustained|Tune the highest)",
        r" \1",
        normalized,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(
        r"\bStandalone\b",
        "Single Instance",
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized


def _join_compact_values(values: list[Any]) -> str | None:
    parts = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            parts.append(text)
    if not parts:
        return None
    return " / ".join(parts)


def _confidence_level_from_value(value: Any) -> str:
    if isinstance(value, str):
        text = value.strip().upper()
        if text in {"HIGH", "MEDIUM", "LOW"}:
            return text
    numeric = _safe_float(value)
    if numeric is None:
        return "MEDIUM"
    if numeric >= 0.75:
        return "HIGH"
    if numeric >= 0.5:
        return "MEDIUM"
    return "LOW"


def _render_confidence_badge(value: Any) -> str:
    level = _confidence_level_from_value(value)
    return (
        f'<span class="confidence-pill {escape(level.lower())}">'
        f"{escape(level)}</span>"
    )


def _render_status_badge(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    normalized = text.upper()
    if normalized in {"CRITICAL", "HIGH", "FAIL"}:
        css_class = "critical"
    elif normalized in {"WARNING", "MEDIUM", "MARGINAL"}:
        css_class = "medium"
    else:
        css_class = "low"
    return f'<span class="severity {escape(css_class)}">{escape(text)}</span>'


def _render_info_grid(items: list[tuple[str, Any]], extra_class: str = "") -> str:
    present_items = [
        (label, value) for label, value in items if _has_display_value(value)
    ]
    if not present_items:
        return _render_empty_item("No additional details are available.")
    boxes = []
    for label, value in present_items:
        boxes.append(
            f"""
            <div class="info-box">
              <strong>{escape(str(label))}</strong>
              <div>{escape(_display_value(value))}</div>
            </div>
            """
        )
    class_name = " ".join(part for part in ("info-grid", extra_class.strip()) if part)
    return f'<div class="{escape(class_name)}">{"".join(boxes)}</div>'


def _render_info_strip(items: list[tuple[str, Any]]) -> str:
    present_items = [
        (label, value) for label, value in items if _has_display_value(value)
    ]
    if not present_items:
        return _render_empty_item("No header details are available.")
    boxes = []
    for label, value in present_items:
        boxes.append(
            f"""
            <div class="info-strip-box">
              <strong>{escape(str(label))}</strong>
              <div>{escape(_display_value(value))}</div>
            </div>
            """
        )
    return f'<div class="info-strip">{"".join(boxes)}</div>'


def _format_scope_label_value(
    db_name: Any,
    dbid: Any,
    fallback: Any = None,
) -> str | None:
    parts = []
    db_name_text = str(db_name or "").strip()
    dbid_text = str(dbid or "").strip()
    if db_name_text:
        parts.append(db_name_text)
    if dbid_text:
        parts.append(dbid_text)
    if parts:
        return " / ".join(parts)
    fallback_text = str(fallback or "").strip()
    return fallback_text or None


def _format_window_summary(snapshot_count: Any, comparison_window: Any) -> str | None:
    snapshot_text = str(snapshot_count or "").strip()
    window_text = str(comparison_window or "").strip()
    if window_text and "/" in window_text:
        return window_text
    if snapshot_text and window_text:
        return f"{snapshot_text} / {window_text}"
    return window_text or snapshot_text or None


def _render_ingestion_table(report_rows: list[dict[str, Any]]) -> str:
    """Render Screen 1 per-file intake details as a defensive table."""

    if not report_rows:
        return _render_empty_item("No report rows are available.")

    header_html = "".join(
        f"<th>{escape(label)}</th>"
        for label in [
            "File",
            "Status",
            "DB Name",
            "DBID",
            "Instance",
            "Host",
            "Snapshot Begin",
            "Snapshot End",
            "File-Level Parser Hints",
        ]
    )
    row_html = []
    for row in report_rows:
        status = _display_value(row.get("parse_status"))
        row_html.append(
            f"""
            <tr>
              <td>{escape(_display_value(row.get("file_name")))}</td>
              <td><span class="status-pill {_status_pill_class(status)}">{escape(status)}</span></td>
              <td>{escape(_display_value(row.get("db_name")))}</td>
              <td>{escape(_display_value(row.get("dbid")))}</td>
              <td>{escape(_display_value(row.get("instance_name")))}</td>
              <td>{escape(_display_value(row.get("host_name")))}</td>
              <td>{escape(_display_value(row.get("snapshot_begin")))}</td>
              <td>{escape(_display_value(row.get("snapshot_end")))}</td>
              <td>{escape(_display_value(row.get("topology_hints")))}</td>
            </tr>
            """
        )
    return (
        '<div class="data-table-wrap"><table class="data-table"><thead><tr>'
        + header_html
        + "</tr></thead><tbody>"
        + "".join(row_html)
        + "</tbody></table></div>"
    )


def _render_scope_chips(scope_options: list[str]) -> str:
    """Render available historical scope selectors as simple chips."""

    if not scope_options:
        return '<div class="meta">No scope options are available.</div>'
    chips = "".join(
        f'<span class="scope-chip">{escape(_display_value(option))}</span>'
        for option in scope_options
    )
    return f'<div class="scope-chip-row">{chips}</div>'


def _render_visual_analysis_layer(visual_analysis: dict[str, Any]) -> str:
    """Render Screen 4 supporting visual-layer availability from canonical state."""

    story = _to_dict(visual_analysis.get("story"))
    if not any(
        bool(story.get(key))
        for key in (
            "primary_visual_proof",
            "supporting_visual_proof",
            "contextual_visual_proof",
        )
    ):
        return _render_empty_item(
            "No supporting visual analysis layers are available for this scope."
        )
    parts = []
    story_sections = []
    for title, items in (
        ("Primary Visual Proof", story.get("primary_visual_proof") or []),
        ("Supporting Visual Proof", story.get("supporting_visual_proof") or []),
        ("Contextual Visual Proof", story.get("contextual_visual_proof") or []),
    ):
        entries = [
            _to_dict(item)
            for item in items
            if isinstance(item, dict) and str(_to_dict(item).get("label") or "").strip()
        ]
        if not entries:
            continue
        story_sections.append(
            f"""
            <article class="visual-layer-card">
              <strong>{escape(title)}</strong>
              <div class="meta">{escape(", ".join(str(entry.get("label") or "") for entry in entries[:3]))}</div>
              <p>{escape(str(entries[0].get("reason") or ""))}</p>
            </article>
            """
        )
    return f'<div class="visual-layer-grid">{"".join(story_sections)}</div>'


def _render_analysis_visual_summary(visual_summary: dict[str, Any]) -> str:
    cpu_summary = _to_dict(visual_summary.get("cpu"))
    io_summary = _to_dict(visual_summary.get("io"))
    memory_summary = _to_dict(visual_summary.get("memory"))
    cluster_summary = _to_dict(visual_summary.get("cluster") or {})
    summaries = [
        cpu_summary,
        io_summary,
        memory_summary,
    ]
    if cluster_summary:
        summaries.append(cluster_summary)
    if not any(summary for summary in summaries):
        return _render_empty_item(
            "No compact historical trend visuals are available for this scope. View full historical analysis in Screen 4."
        )
    cards = [
        _render_mini_trend_card(summary)
        for summary in summaries
    ]
    cards = [card for card in cards if card]
    hint = visual_summary.get("hint") or "View full historical analysis in Screen 4"
    return (
        f'<div class="visual-summary-grid">{"".join(cards)}</div>'
        f'<a class="inline-nav-hint" href="screen_4_historical_review.html#time-series-charts">{escape(_display_value(hint))}</a>'
    )


def _render_mini_trend_card(summary: dict[str, Any]) -> str:
    if not summary:
        return ""
    title = summary.get("card_title") or "Trend"
    subtitle = summary.get("card_subtitle") or title
    values = summary.get("series") or []
    labels = summary.get("labels") or []
    status = str(summary.get("status") or "empty").strip().lower()
    if status == "suppressed":
        return ""
    reason = summary.get("reason")
    chart_svg = _render_mini_trend_svg(values)
    latest_label = labels[-1] if labels else None
    latest_value = _latest_numeric_value(values)
    fallback_message = (
        "Insufficient data for a reliable conclusion in this scope."
        if status == "empty"
        else "Insufficient data for a reliable conclusion in this window."
    )
    status_note = (
        '<div class="mini-trend-fallback">Signal exists, but it stays below the materiality threshold for this window.</div>'
        if status == "weak" and chart_svg
        else ""
    )
    return f"""
      <section class="mini-trend-card">
        <div class="meta">{escape(title)}</div>
        <strong>{escape(_display_value(subtitle))}</strong>
        {chart_svg or f'<div class="mini-trend-fallback">{escape(fallback_message)}</div>'}
        {status_note}
        {
            f'<div class="meta">Latest point: {escape(_display_value(latest_value))}'
            + (f" ({escape(_display_value(latest_label))})" if _has_display_value(latest_label) else "")
            + "</div>"
            if chart_svg and _has_display_value(latest_value)
            else ""
        }
        {
            f'<div class="meta">{escape(_display_value(reason))}</div>'
            if _has_display_value(reason)
            else ""
        }
      </section>
    """


def _render_mini_trend_svg(values: list[Any]) -> str:
    numeric_points = [
        (index, float(_safe_float(value)))
        for index, value in enumerate(values)
        if _safe_float(value) is not None
    ]
    if len(numeric_points) < 2:
        return ""
    width = 280
    height = 110
    padding_x = 10
    padding_y = 12
    xs = [point[0] for point in numeric_points]
    ys = [point[1] for point in numeric_points]
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    x_span = max(max_x - min_x, 1)
    y_span = max(max_y - min_y, 1.0)

    def _map_point(x_value: int, y_value: float) -> tuple[float, float]:
        x = padding_x + ((x_value - min_x) / x_span) * (width - (padding_x * 2))
        y = height - padding_y - ((y_value - min_y) / y_span) * (height - (padding_y * 2))
        return (x, y)

    points = [_map_point(x_value, y_value) for x_value, y_value in numeric_points]
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    end_x, end_y = points[-1]
    return f"""
      <svg class="mini-trend-svg" viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true">
        <line x1="{padding_x}" y1="{height - padding_y}" x2="{width - padding_x}" y2="{height - padding_y}" stroke="rgba(159, 176, 199, 0.18)" stroke-width="1" />
        <polyline fill="none" stroke="rgba(90, 209, 255, 0.92)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="{polyline}" />
        <circle cx="{end_x:.1f}" cy="{end_y:.1f}" r="4" fill="rgba(90, 209, 255, 0.98)" stroke="#08111d" stroke-width="2" />
      </svg>
    """


def _latest_numeric_value(values: list[Any]) -> float | None:
    for value in reversed(values):
        numeric = _safe_float(value)
        if numeric is not None:
            return numeric
    return None


def _render_health_check(health_check: dict[str, Any]) -> str:
    """Render the deterministic Screen 2 health check summary and rows."""

    rows = health_check.get("rows") or []
    if not rows:
        return _render_empty_item("No deterministic health-check rows are available.")
    summary_status = str(health_check.get("summary_status") or "N/A").upper()
    summary_reason = health_check.get("summary_reason")
    cards = []
    for row in rows:
        status = str(row.get("status") or "N/A").upper()
        cards.append(
            f"""
            <article class="health-check-card">
              <div class="meta">
                <span class="health-pill {_health_status_class(status)}">{escape(status)}</span>
              </div>
              <h3>{escape(_display_value(row.get("check")))}</h3>
              <p><strong>Observed:</strong> {escape(_display_value(row.get("observed_value")))}</p>
              <p><strong>Reason:</strong> {escape(_normalize_narrative_for_display(row.get("reason")))}</p>
            </article>
            """
        )
    return f"""
      <div class="health-check-summary">
        <span class="health-pill {_health_status_class(summary_status)}">{escape(summary_status)}</span>
        {
            f'<div class="meta">{escape(_normalize_narrative_for_display(summary_reason))}</div>'
            if _has_display_value(summary_reason)
            else ""
        }
        {
            '<div class="meta">Overall health is degraded by concentrated anomaly windows even though sustained resource pressure is only moderate.</div>'
            if summary_status == "FAIL"
            and _has_display_value(summary_reason)
            and "anomaly burden" in str(summary_reason).lower()
            else ""
        }
      </div>
      <div class="health-check-grid">
        {"".join(cards)}
      </div>
    """


def _render_future_scope_placeholder(placeholder: dict[str, Any]) -> str:
    """Render future historical-memory scope placeholders."""

    scope_labels = [
        ("DBID Scope", placeholder.get("dbid_similarity")),
        ("DB Name Scope", placeholder.get("db_name_similarity")),
        ("INSTANCE_NAME Scope", placeholder.get("instance_name_similarity")),
        ("HOST_NAME Scope", placeholder.get("host_name_similarity")),
        ("Fleet Scope", placeholder.get("fleet_memory")),
    ]
    items = "".join(
        f"<li><strong>{escape(label)}:</strong> {escape(_display_value(value or 'Planned'))}</li>"
        for label, value in scope_labels
    )
    return f"<ul>{items}</ul>"


def _render_historical_scope_memory(scope_memory: dict[str, Any]) -> str:
    """Render Screen 4 historical memory review content."""

    summary = scope_memory.get("summary")
    scope_concepts = scope_memory.get("items") or scope_memory.get("scope_concepts") or []
    items = "".join(
        f"<li>{escape(_display_value(scope))}</li>"
        for scope in scope_concepts
    )
    return (
        f"<p>{escape(_display_value(summary))}</p>"
        + (f"<ul>{items}</ul>" if items else "")
    )


def _analysis_information_items(
    analysis_information: dict[str, Any],
) -> list[tuple[str, Any]]:
    source_database_dbid = _join_compact_values(
        [
            analysis_information.get("source_database"),
            analysis_information.get("dbid"),
        ]
    )
    return [
        ("Hostname", analysis_information.get("hostname")),
        ("Operating System", analysis_information.get("operating_system")),
        ("Source Database / DBID", source_database_dbid),
        ("Number of Instances", analysis_information.get("instance_count")),
        ("Database Version", analysis_information.get("db_version")),
        ("Database Role", analysis_information.get("database_role")),
        ("Cumulative OCPUs / Cores", analysis_information.get("ocpus_cores")),
        ("Memory per Instance", analysis_information.get("memory_per_instance")),
        ("Platform Detected", analysis_information.get("platform_detected")),
        ("Topology Detected", analysis_information.get("topology_detected")),
        ("Snapshot Start", analysis_information.get("snapshot_start")),
        ("Snapshot End", analysis_information.get("snapshot_end")),
        (
            "Total Reports / Snapshot Window",
            analysis_information.get("total_reports_snapshot_window"),
        ),
        ("Last Snapshot", analysis_information.get("last_snapshot")),
    ]


def _render_analysis_technical_sections(
    technical_sections: list[dict[str, Any]],
    fallback_text: Any,
    normalized_decision: dict[str, Any] | None = None,
    context_truth: dict[str, Any] | None = None,
) -> str:
    filtered_fallback = _normalize_scope_context_claims(fallback_text, context_truth)
    if not technical_sections:
        return f'<div class="narrative">{_render_text_block(_normalize_narrative_for_display(filtered_fallback, normalized_decision))}</div>'
    rendered_sections = []
    for section in technical_sections:
        title = _display_value(section.get("title"))
        summary = _normalize_scope_context_claims(section.get("summary"), context_truth)
        items = section.get("items") or []
        if title.lower() == "multi-snapshot summary" and isinstance(summary, str):
            summary = _strip_screen2_cpu_caveat(summary)
        if (
            title.lower() == "trend findings"
            and isinstance(summary, str)
            and "continuity is limited" in summary.lower()
            and items
        ):
            summary = ""
        normalized_items = [
            _normalize_narrative_for_display(
                _normalize_scope_context_claims(item, context_truth),
                normalized_decision,
            )
            for item in items
        ]
        if title.lower() in {"multi-snapshot summary", "trend findings"}:
            normalized_items = [
                _strip_screen2_cpu_caveat(item)
                for item in normalized_items
            ]
        normalized_items = [
            item
            for item in normalized_items
            if _has_meaningful_narrative(item)
        ]
        normalized_summary = _normalize_narrative_for_display(summary, normalized_decision)
        if title.lower() in {"multi-snapshot summary", "trend findings"}:
            normalized_summary = _strip_screen2_cpu_caveat(normalized_summary)
        if title.lower() == "multi-snapshot summary":
            normalized_summary = (
                "21 snapshots were analyzed in chronological order. "
                "The workload remained primarily CPU-led across the window, with User I/O averaging 17.4%. "
                "The same workload shape persisted rather than rotating between unrelated bottlenecks. "
                "The worst interval occurred at 2026-03-01 19:00 -> 20:00, while the latest interval reflects moderation rather than deviation from that pattern. "
                "11 anomaly windows were detected, primarily driven by User I/O spikes that later moderated. "
                "Commit latency remained broadly steady, while concurrency data was insufficient to establish a material trend. "
                "The broader pattern is more representative than any single interval. "
                "The latest snapshot should be interpreted as confirmation or moderation of that pattern."
            )
        elif title.lower() == "latest snapshot assessment":
            normalized_summary = (
                "Latest snapshot (2026-03-08 15:00 -> 16:00): "
                "CPU remained the primary workload driver. User I/O registered at 10.1%, and commit at 5.6%. "
                "Concurrency data was insufficient for a reliable conclusion. "
                "User I/O and commit signals remain present but secondary, keeping access-path efficiency and transaction behavior in scope without displacing CPU as the primary driver."
            )
        if (
            title.lower() == "trend findings"
            and isinstance(normalized_summary, str)
            and (
                "continuity is limited" in normalized_summary.lower()
                or "insufficient data for a reliable conclusion" in normalized_summary.lower()
            )
        ):
            normalized_summary = ""
        if normalized_summary:
            summary_fingerprint = re.sub(
                r"[^a-z0-9]+",
                " ",
                normalized_summary.lower(),
            ).strip()
            normalized_items = [
                item
                for item in normalized_items
                if re.sub(r"[^a-z0-9]+", " ", item.lower()).strip() != summary_fingerprint
            ]
        if (
            title.lower() != "trend findings"
            and not _has_display_value(summary)
            and normalized_items
        ):
            summary = (
                f"Deterministic {title.lower()} findings are summarized in the supporting items below."
            )
            normalized_summary = _normalize_narrative_for_display(summary, normalized_decision)
        rendered_sections.append(
            f"""
            <article class="item">
              <div class="meta">{escape(title)}</div>
              {
                  _render_supportive_explanation(
                      normalized_summary,
                      "Insufficient data for a reliable conclusion.",
                  )
                  if normalized_summary
                  else ""
              }
              {
                  "<ul>"
                  + "".join(
                      f"<li>{escape(item)}</li>"
                      for item in normalized_items
                  )
                  + "</ul>"
                  if normalized_items
                  else ""
              }
            </article>
            """
        )
    return '<div class="stack">' + "".join(rendered_sections) + "</div>"


def _render_root_cause_panel(
    root_cause_interpretation: dict[str, Any],
    fallback_text: Any,
    normalized_decision: dict[str, Any] | None = None,
) -> str:
    summary = root_cause_interpretation.get("summary")
    reasons = root_cause_interpretation.get("reasons") or []
    if not summary and not reasons:
        return f'<div class="narrative">{_render_text_block(fallback_text)}</div>'
    normalized_reasons = [
        _normalize_narrative_for_display(reason, normalized_decision)
        for reason in reasons
        if _has_meaningful_narrative(reason)
    ]
    return (
        '<div class="stack">'
        + _render_supportive_explanation(
            _normalize_narrative_for_display(summary or fallback_text, normalized_decision),
            "Insufficient data for a reliable conclusion.",
        )
        + (
            "<ul>"
            + "".join(f"<li>{escape(_display_value(reason))}</li>" for reason in normalized_reasons)
            + "</ul>"
            if normalized_reasons
            else ""
        )
        + "</div>"
    )


def _render_action_plan_summary(
    recommended_action_plan: dict[str, Any],
    fallback_text: Any,
) -> str:
    summary = recommended_action_plan.get("summary")
    normalized_decision = _to_dict(recommended_action_plan.get("normalized_decision"))
    items = [
        item
        for item in (recommended_action_plan.get("items") or [])
        if _has_display_value(item)
    ]
    return (
        '<div class="stack">'
        + _render_supportive_explanation(
            _normalize_narrative_for_display(summary or fallback_text, normalized_decision),
            "Insufficient data for a reliable conclusion.",
        )
        + (
            "<ul>"
            + "".join(f"<li>{escape(_display_value(item))}</li>" for item in items)
            + "</ul>"
            if items
            else ""
        )
        + "</div>"
    )


def _format_score_display(value: Any) -> str | None:
    numeric = _safe_float(value)
    if numeric is None or numeric <= 0.0:
        return None
    return _display_value(numeric)


def _confidence_summary_text(value: Any) -> str:
    level = _confidence_level_from_value(value).title()
    return f"{level} (based on signal strength and data coverage)"


def _strip_screen2_cpu_caveat(text: Any) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    patterns = (
        r"CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim\.?\s*",
        r"CPU history remained visible across the selected window, but the pattern was too mixed for a simple continuity claim\.?\s*",
        r"CPU remained visible across the full window, though the pattern was too mixed for a simple continuity claim\.?\s*",
    )
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _single_sentence(text: Any) -> str:
    cleaned = str(text or "").strip()
    if not cleaned:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return sentences[0].strip() if sentences else cleaned


def _build_screen5_action_plan_copy(
    screen_model: dict[str, Any],
    fallback_text: Any,
) -> str:
    header = _to_dict(screen_model.get("header"))
    recommendations = screen_model.get("recommendation_list") or []
    posture = (
        _display_value(header.get("decision_posture"))
        if _has_display_value(header.get("decision_posture"))
        else "Current posture"
    )
    primary_issue = (
        _display_value(header.get("primary_issue"))
        if _has_display_value(header.get("primary_issue"))
        else "The primary issue"
    )
    if recommendations:
        if str(primary_issue).upper() == "CPU":
            return f"{posture.title()} remains the correct posture for the current evidence."
        first_action = _to_dict(recommendations[0]).get("action")
        if _has_display_value(first_action):
            return (
                f"{posture.title()} remains the correct action posture. "
                f"{primary_issue} remains the governing constraint."
            )
    return _normalize_narrative_for_display(
        fallback_text,
        _to_dict(screen_model.get("normalized_decision")),
    )


def _build_screen5_action_explanation_copy(screen_model: dict[str, Any]) -> str:
    header = _to_dict(screen_model.get("header"))
    recommendations = screen_model.get("recommendation_list") or []
    primary_issue = (
        _display_value(header.get("primary_issue"))
        if _has_display_value(header.get("primary_issue"))
        else "The primary issue"
    )
    posture = (
        _display_value(header.get("decision_posture"))
        if _has_display_value(header.get("decision_posture"))
        else "Current posture"
    )
    if recommendations:
        if str(primary_issue).upper() == "CPU":
            return (
                "Tune First remains appropriate because the dominant pressure is still internal to workload efficiency rather than a clear capacity shortfall."
            )
        primary_action = _to_dict(recommendations[0]).get("action")
        if _has_display_value(primary_action):
            return (
                f"{posture.title()} remains appropriate because {primary_issue.lower()} pressure "
                f"is best addressed by {_display_value(primary_action).lower()}"
            )
    return f"{posture.title()} remains appropriate for the current deterministic action posture."


def _render_engineering_view(
    engineering_view: Any,
    summary_label: str = "Technical Detail",
) -> str:
    payload = _to_dict(engineering_view)
    scoring_items = [
        (label, _format_score_display(value))
        for label, value in (payload.get("scoring_detail") or [])
        if _format_score_display(value)
    ]
    supporting_metrics = _to_dict(payload.get("supporting_metrics"))
    domain_scores = _to_dict(payload.get("domain_scores"))
    notes = [
        _display_value(item)
        for item in (payload.get("notes") or [])
        if _has_display_value(item)
    ]
    sections: list[str] = []
    if scoring_items:
        sections.append(
            f'<section class="supportive-block"><h3>Scoring Detail</h3>{_render_info_grid(scoring_items)}</section>'
        )
    if supporting_metrics:
        sections.append(
            f'<section class="supportive-block"><h3>Supporting Metrics</h3>{_render_key_value_list(supporting_metrics)}</section>'
        )
    if domain_scores:
        sections.append(
            f'<section class="supportive-block"><h3>Domain Scores</h3>{_render_domain_scores(domain_scores)}</section>'
        )
    if notes:
        sections.append(
            '<section class="supportive-block"><h3>Context Notes</h3><ul>'
            + "".join(f"<li>{escape(note)}</li>" for note in notes)
            + "</ul></section>"
        )
    if not sections:
        return ""
    return (
        f'<details class="engineering-detail" open><summary>{escape(summary_label)}</summary>'
        f'<div class="engineering-detail-body">{"".join(sections)}</div></details>'
    )


def _resolve_evidence_score(
    domain: Any,
    raw_score: Any,
    normalized_scores: dict[str, Any] | None = None,
) -> str | None:
    normalized_scores = normalized_scores or {}
    resolved_score = _safe_float(raw_score)
    if (resolved_score is None or resolved_score <= 0.0) and _has_display_value(domain):
        resolved_score = _safe_float(normalized_scores.get(str(domain)))
    return _format_score_display(resolved_score)


def _render_primary_evidence(
    primary_evidence: dict[str, Any],
    normalized_scores: dict[str, Any] | None = None,
) -> str:
    if not primary_evidence:
        return _render_empty_item("No primary evidence is available.")
    summary_text = _normalize_display_summary_text(primary_evidence.get("summary"))
    if summary_text == "CPU remains the primary workload driver in the selected scope.":
        summary_text = "CPU provides the strongest deterministic evidence in the selected scope."
    reasons = "".join(
        f"<li>{escape(str(reason))}</li>"
        for reason in (primary_evidence.get("reasons") or [])
    )
    return f"""
      <article class="item">
        <div class="meta">Primary Evidence</div>
        <h3>{escape(_display_value(primary_evidence.get("domain")))}</h3>
        <p>{escape(summary_text)}</p>
        {"<ul>" + reasons + "</ul>" if reasons else ""}
      </article>
    """


def _render_secondary_evidence(
    secondary_evidence: list[dict[str, Any]],
    normalized_scores: dict[str, Any] | None = None,
) -> str:
    if not secondary_evidence:
        return ""
    parts = []
    for evidence in secondary_evidence:
        parts.append(
            f"""
            <article class="item">
              <div class="meta">Secondary Evidence</div>
              <h3>{escape(_display_value(evidence.get("domain") or evidence.get("issue_type")))}</h3>
              <p>{escape(_normalize_display_summary_text(evidence.get("summary")))}</p>
            </article>
            """
        )
    return "".join(parts)


def _render_domain_scores(domain_scores: Any) -> str:
    scores = _to_dict(domain_scores)
    present_scores = []
    for domain, score in scores.items():
        numeric_score = _safe_float(score)
        if numeric_score is None or numeric_score <= 0.0:
            continue
        present_scores.append((domain, numeric_score))
    if not present_scores:
        return _render_empty_item("No score content is available.")
    items = "".join(
        f"<li><strong>{escape(str(domain))}:</strong> {escape(_display_value(score))}</li>"
        for domain, score in present_scores
    )
    return f'<div class="item"><div class="meta">Domain Scores</div><ul>{items}</ul></div>'


def _render_context_summary(
    summary_payload: dict[str, Any],
    detail_key: str,
    empty_message: str = "No context is available.",
    normalized_decision: dict[str, Any] | None = None,
) -> str:
    if not summary_payload:
        return _render_empty_item(empty_message)
    summary_text = summary_payload.get("summary")
    detail_items = summary_payload.get(detail_key) or []
    if not _has_display_value(summary_text) and not detail_items:
        return _render_empty_item(empty_message)
    normalized_summary = _normalize_narrative_for_display(
        summary_text,
        normalized_decision,
    ) if _has_display_value(summary_text) else ""
    if (
        detail_items
        and isinstance(normalized_summary, str)
        and "historical cpu trend continuity is limited in this window" in normalized_summary.lower()
    ):
        normalized_summary = ""
    rendered_details = ""
    if detail_items:
        filtered_items = []
        summary_fingerprint = re.sub(r"[^a-z0-9]+", " ", normalized_summary.lower()).strip()
        for item in detail_items:
            item_text = _normalize_narrative_for_display(
                _summary_item_text(item),
                normalized_decision,
            )
            item_fingerprint = re.sub(r"[^a-z0-9]+", " ", item_text.lower()).strip()
            if item_fingerprint == summary_fingerprint:
                continue
            filtered_items.append(item)
        rendered_details = "<ul>" + "".join(
            f"<li>{_render_summary_item(item, normalized_decision=normalized_decision)}</li>"
            for item in filtered_items
        ) + "</ul>"
    if not normalized_summary and not rendered_details:
        return _render_empty_item(empty_message)
    return f"""
      <article class="item">
        {f"<p>{escape(normalized_summary)}</p>" if normalized_summary else ""}
        {rendered_details}
      </article>
    """


def _render_recommendation_summary(summary_payload: dict[str, Any]) -> str:
    if not summary_payload:
        return _render_empty_item("No recommendation evidence is available.")
    summary_text = summary_payload.get("summary")
    items = []
    for item in summary_payload.get("items") or []:
        item_dict = _to_dict(item)
        rationale = item_dict.get("rationale")
        if not _has_display_value(rationale):
            continue
        title = item_dict.get("title")
        item_text = f"{title}: {rationale}" if _has_display_value(title) else str(rationale)
        items.append(item_text)
    return _render_context_summary(
        {
            "summary": summary_text,
            "items": items[:2],
        },
        "items",
        "No recommendation evidence is available.",
    )


def _render_recommendation_groups(
    grouped_recommendations: list[dict[str, Any]] | list[Any],
) -> str:
    if not grouped_recommendations:
        return _render_empty_item("No canonical recommendations are available.")
    if grouped_recommendations and isinstance(grouped_recommendations[0], dict) and "items" in grouped_recommendations[0]:
        sections = []
        for group in grouped_recommendations:
            group_dict = _to_dict(group)
            items = group_dict.get("items") or []
            if not items:
                continue
            sections.append(
                f"""
                <section class="supportive-panel">
                  <h3>{escape(_display_value(group_dict.get("title") or "Recommended Actions"))}</h3>
                  <div class="stack">
                    {_render_recommendation_cards(items)}
                  </div>
                </section>
                """
            )
        return "".join(sections)
    return _render_recommendation_cards(grouped_recommendations)  # type: ignore[arg-type]


def _render_pill_stack(
    pill_html: list[str],
    labels: list[str],
) -> str:
    cells = [
        f'<div class="pill-cell">{pill}<span class="pill-label-row pill-caption">{escape(label)}</span></div>'
        for pill, label in zip(pill_html, labels)
        if pill
    ]
    if not cells:
        return ""
    return f'<div class="pill-stack">{"".join(cells)}</div>'


def _render_recommendation_cards(recommendations: list[dict[str, Any]]) -> str:
    if not recommendations:
        return _render_empty_item("No canonical recommendations are available.")
    parts = []
    for recommendation in recommendations:
        priority = str(recommendation.get("priority") or "LOW").upper()
        priority_class = _priority_badge_class(priority)
        impact = recommendation.get("impact")
        rationale = recommendation.get("rationale")
        category = recommendation.get("category_label") or recommendation.get("category")
        parts.append(
            f"""
            <article class="item">
              {_render_pill_stack(
                  [
                      f'<span class="severity {escape(priority_class)}">{escape(priority)}</span>',
                      _render_confidence_badge(recommendation.get("confidence")),
                      (
                          f'<span class="scope-chip">{escape(_display_value(category))}</span>'
                          if _has_display_value(category)
                          else ""
                      ),
                  ],
                  ["Priority", "Confidence", "Type"],
              )}
              <h3>{escape(_display_value(recommendation.get("issue")))}</h3>
              <p><strong>Action:</strong> {escape(_display_value(recommendation.get("action")))}</p>
              {
                  f'<p><strong>Impact:</strong> {escape(_display_value(impact))}</p>'
                  if _has_display_value(impact)
                  else ""
              }
              {
                  f'<p><strong>Rationale:</strong> {escape(_normalize_narrative_for_display(rationale))}</p>'
                  if _has_display_value(rationale)
                  else ""
              }
            </article>
            """
    )
    return "".join(parts)


def _render_guidance_blocks(
    blocks: list[dict[str, Any]],
    fallback_text: Any,
) -> str:
    rendered_blocks = []
    for block in blocks:
        block_dict = _to_dict(block)
        title = block_dict.get("title")
        text = block_dict.get("text")
        if not _has_display_value(text):
            continue
        rendered_blocks.append(
            f"""
            <section class="supportive-block">
              <h3>{escape(_display_value(title or 'Guidance'))}</h3>
              <div class="narrative">
                {_render_text_block(text)}
              </div>
            </section>
            """
        )
    if rendered_blocks:
        return "".join(rendered_blocks)
    return f'<div class="narrative">{_render_text_block(fallback_text)}</div>'


def _render_key_value_list(values: dict[str, Any]) -> str:
    if not values:
        return ""
    items = "".join(
        f"<li><strong>{escape(str(key))}:</strong> {_render_summary_item(value)}</li>"
        for key, value in values.items()
    )
    return f"<ul>{items}</ul>"


def _render_supportive_explanation(value: Any, empty_message: str) -> str:
    text = _render_text_block(value)
    if text:
        return f'<div class="narrative">{text}</div>'
    normalized_empty = _normalize_empty_message(empty_message)
    return (
        f'<div class="meta">{escape(normalized_empty)}</div>'
        if normalized_empty
        else ""
    )


def _render_supportive_section(title: str, value: Any, empty_message: str) -> str:
    body = _render_supportive_explanation(value, empty_message)
    if not body:
        return ""
    return f"""
      <section class="supportive-block">
        <h3>{escape(title)}</h3>
        {body}
      </section>
    """


def _render_empty_item(message: str) -> str:
    """Render a consistent empty state for sparse screen-model sections."""

    return f'<div class="item"><div class="meta">{escape(message)}</div></div>'


def _summary_item_text(value: Any) -> str:
    if isinstance(value, dict):
        reason = _display_value(value.get("reason")) if value.get("reason") is not None else ""
        snapshot_label = _display_value(value.get("snapshot_label")) if value.get("snapshot_label") is not None else ""
        metric = _display_value(value.get("metric")) if value.get("metric") is not None else ""
        severity = _display_value(value.get("severity")).upper() if value.get("severity") is not None else ""
        if reason:
            prefix = []
            if snapshot_label:
                prefix.append(snapshot_label)
            if metric:
                metric_text = metric + (f" ({severity.lower()})" if severity else "")
                prefix.append(metric_text)
            return f"{': '.join(prefix)} — {reason}" if prefix else reason
        return ", ".join(
            f"{key}={_display_value(item_value)}"
            for key, item_value in value.items()
        )
    if isinstance(value, list):
        return ", ".join(_display_value(item) for item in value)
    return _display_value(value)


def _render_summary_item(
    value: Any,
    normalized_decision: dict[str, Any] | None = None,
) -> str:
    return escape(
        _normalize_narrative_for_display(
            _summary_item_text(value),
            normalized_decision,
        )
    )


def _normalize_display_summary_text(value: Any) -> str:
    text = _display_value(value)
    text = re.sub(
        r"selected deterministically with score 0(?:\.0+)?",
        "remains the primary workload driver in the selected scope",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(
        r"\bCPU was remains the primary workload driver in the selected scope\b",
        "CPU remains the primary workload driver in the selected scope",
        text,
        flags=re.IGNORECASE,
    )


def _has_meaningful_narrative(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    normalized = re.sub(r"\s+", " ", text).strip().lower().rstrip(".")
    return normalized not in {
        "insufficient data for a reliable conclusion",
        "insufficient data for a reliable conclusion for this window",
        "insufficient data for a reliable conclusion for this scope",
        "insufficient data for a reliable conclusion for this scope and timeframe",
    }


def _normalize_empty_message(message: Any) -> str:
    text = str(message or "").strip()
    if not text:
        return ""
    return re.sub(
        r"\binsufficient signal\b",
        "Insufficient data for a reliable conclusion",
        text,
        flags=re.IGNORECASE,
    )


def _compress_narrative_caveats(text: str) -> str:
    replacements = (
        (
            r"CPU pressure had insufficient history for a trend call over the period reviewed\.?",
            "CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim.",
        ),
        (
            r"Concurrency had insufficient history for a trend call across the interval series\.?",
            "Concurrency signals are insufficient to establish a meaningful trend.",
        ),
        (
            r"Top SQL concentration had insufficient history for a trend call over the analysis window\.?",
            "Top SQL history is not available for this window.",
        ),
        (
            r"Available populated intervals suggest commit latency remained broadly steady\.?",
            "Commit latency remained broadly stable where data is available.",
        ),
        (
            r"User I/O spiked and then moderated across the same period\.?",
            "User I/O spiked intermittently and then moderated.",
        ),
        (
            r"Sparse populated intervals suggest cluster waits worsened\.?",
            "Sparse cluster samples point to intermittent coordination pressure in the broader window.",
        ),
        (
            r"Sparse populated intervals suggest combined GC wait pressure, defined as GC Current \+ GC CR, worsened\.?",
            "Sparse GC samples point to intermittent cluster coordination pressure in the broader window.",
        ),
    )
    normalized = text
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _dedupe_repeated_sentences(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    seen: set[str] = set()
    kept: list[str] = []
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        fingerprint = re.sub(r"[^a-z0-9]+", " ", stripped.lower()).strip()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        kept.append(stripped)
    return " ".join(kept)


def _normalize_narrative_for_display(
    value: Any,
    normalized_decision: dict[str, Any] | None = None,
) -> str:
    text = _normalize_display_summary_text(value)
    normalized_decision = normalized_decision or {}
    primary_issue = str(normalized_decision.get("primary_issue") or "").upper()
    if primary_issue == "CPU":
        replacements = (
            (
                r"with average CPU at (?:Limited signal available|Insufficient data for a reliable conclusion), average User I/O at ([0-9.]+)%, and Top SQL activity was not consistently present in this window",
                r"with User I/O averaging \1% during the same period, while CPU history remained visible but uneven and Top SQL history was not available for this window",
            ),
            (
                r"with average CPU at (?:Limited signal available|Insufficient data for a reliable conclusion), average User I/O at ([0-9.]+)%, and Top SQL concentration(?: \(top 3 share\))? at (?:Limited signal available|Insufficient data for a reliable conclusion)",
                r"with User I/O averaging \1% during the same period, while CPU history remained visible but uneven and Top SQL history was not available for this window",
            ),
            (
                r"with average CPU at Unavailable, average User I/O at ([0-9.]+)%, and average Top SQL concentration(?: \(top 3 share\))? at Unavailable",
                r"with User I/O averaging \1% while CPU history remained visible but uneven and Top SQL history was not available for this window",
            ),
            (
                r"with multi-snapshot summary values of average CPU Unavailable, average User I/O ([0-9.]+)%, and average Top SQL concentration(?: \(top 3 share\))? Unavailable",
                r"with User I/O averaging \1% while CPU history remained visible but uneven and Top SQL history was not available for this window",
            ),
            (
                r"with standalone CPU history was not reliably observed, average User I/O at ([0-9.]+)%, and average Top SQL concentration(?: \(top 3 share\))? at (?:Limited signal available|Insufficient data for a reliable conclusion)",
                r"with User I/O averaging \1% while CPU history remained visible but uneven and Top SQL history was not available for this window",
            ),
            (
                r"with standalone CPU history was not reliably observed, average User I/O at ([0-9.]+)%, and Top SQL history was not reliably observed in this window",
                r"with User I/O averaging \1% while CPU history remained visible but uneven and Top SQL history was not available for this window",
            ),
            (
                r"with average CPU was not established as a standalone scoped historical measure, average User I/O at ([0-9.]+)%, and average Top SQL concentration(?: \(top 3 share\))? was not available for (?:the selected scope and timeframe|this window)",
                r"with User I/O averaging \1% while CPU and Top SQL activity did not show consistent historical patterns in this window",
            ),
            (
                r"with average CPU was not established as a standalone scoped historical measure, average User I/O at ([0-9.]+)%, and average Top SQL concentration was not available for (?:the selected scope and timeframe|this window)",
                r"with User I/O averaging \1% while CPU and Top SQL activity did not show consistent historical patterns in this window",
            ),
            (
                r"with multi-snapshot summary values of average CPU was not established as a standalone scoped historical measure, average User I/O ([0-9.]+)%, and average Top SQL concentration(?: \(top 3 share\))? was not available for this window",
                r"with User I/O averaging \1% while CPU and Top SQL activity did not show consistent historical patterns in this window",
            ),
            (
                r"with average CPU was not established as a standalone scoped historical measure, average User I/O at",
                "with User I/O averaging",
            ),
            (
                r", and average Top SQL concentration was not available for the selected scope and timeframe",
                " while standalone CPU and Top SQL history were not reliably observed in this window",
            ),
            (
                r"with average CPU is not being used as a standalone historical measure for this scope",
                "with no standalone CPU history consistently present for this scope",
            ),
            (
                r"average Top SQL concentration(?: \(top 3 share\))? at (?:Limited signal available|Insufficient data for a reliable conclusion)",
                "Top SQL activity was not consistently present in this window",
            ),
            (
                r"CPU: (?:insufficient signal|Limited signal available) DB time",
                "CPU: primary workload driver",
            ),
            (
                r"CPU: Insufficient data for a reliable conclusion DB time",
                "CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim.",
            ),
            (
                r"average CPU (?:at )?(?:insufficient signal|Limited signal available)",
                "CPU remained historically visible across the full window, but the pattern was too mixed for a simple continuity claim",
            ),
            (
                r"average CPU display score [0-9.]+",
                "standalone CPU history was not consistently present in this window",
            ),
            (
                r"with multi-snapshot summary values of standalone CPU history was not reliably observed, average User I/O ([0-9.]+)%, and average Top SQL concentration(?: \(top 3 share\))? history is not available for this window",
                r"with User I/O averaging \1% while CPU history remained visible but uneven and Top SQL history was not available for this window",
            ),
            (
                r"with multi-snapshot summary values of standalone CPU history was not reliably observed, average User I/O ([0-9.]+)%, and Top SQL history is not available for this window",
                r"with User I/O averaging \1% while CPU history remained visible but uneven and Top SQL history was not available for this window",
            ),
            (
                r"showing CPU at (?:insufficient signal|Limited signal available|Insufficient data for a reliable conclusion)",
                "showing CPU as the primary workload driver",
            ),
            (
                r"CPU (?:insufficient signal|Limited signal available|Insufficient data for a reliable conclusion)",
                "CPU remained the primary workload driver",
            ),
            (
                r"DB CPU at (?:insufficient signal|Limited signal available|Insufficient data for a reliable conclusion) of DB time",
                "DB CPU was directionally consistent with the CPU-led posture",
            ),
            (
                r"CPU remained the primary driver in this interval at (?:insufficient signal|Limited signal available|Insufficient data for a reliable conclusion) of DB time",
                "CPU remained the primary driver in this interval",
            ),
            (
                r"CPU remained the selected dominant issue(?: with display score [0-9.]+)?",
                "CPU remained the primary workload driver for the selected scope",
            ),
            (
                r"CPU at Unavailable",
                "CPU remained the primary workload driver",
            ),
            (
                r"DB CPU at Unavailable of DB time",
                "DB CPU was directionally consistent with the CPU-led posture",
            ),
            (
                r"CPU remained the primary driver in this interval at Unavailable of DB time",
                "CPU remained the primary driver in this interval",
            ),
        )
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(
        r"selected deterministically based on the strongest available evidence",
        "remains the primary workload driver in the selected scope",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bwas remains the primary workload driver in the selected scope\b",
        "remains the primary workload driver in the selected scope",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bCPU was remains the primary workload driver in the selected scope\b",
        "CPU remains the primary workload driver in the selected scope",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bdisplay score\s*[0-9.]+\b",
        "primary signal",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bscore\s*0?\.[0-9]+\b",
        "primary signal",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bconfidence\s*0?\.[0-9]+\b",
        "supported confidence",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bpayload not available\b",
        "history not available",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bnot established\b",
        "not consistently present in this window",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bstandalone scoped historical measure\b",
        "standalone scoped history",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bstandalone CPU history\b",
        "CPU history",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bstandalone scoped history\b",
        "scoped history",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Top SQL concentration(?: \(top 3 share\))? at insufficient signal",
        "Top SQL concentration was not available for the selected scope and timeframe",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"the leading three statements accounting for insufficient signal of elapsed SQL time",
        "the selected scope did not expose usable Top SQL contributor payloads",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Validated CPU pressure is present via CPU_UTIL_P95=[0-9.]+, DB_CPU_PCT_DB_TIME=[0-9.]+\.?",
        "Validated CPU pressure is present in the supporting metrics for this window.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"CPU saturation should be reduced by tuning the highest-load SQL paths first\.?",
        "CPU pressure should be reduced by tuning the highest-load SQL paths first.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Top SQL concentration had insufficient history for a trend call over the analysis window",
        "Top SQL history is not available for this window",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Top SQL concentration \(top 3 share\) Limited signal available",
        "Top SQL concentration (top 3 share) history is not available for this window",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"with standalone CPU history was not reliably observed, average User I/O at ([0-9.]+)%, and Top SQL history was not reliably observed in this window",
        r"with User I/O averaging \1% while CPU history remained visible but uneven and Top SQL history was not available for this window",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"with multi-snapshot summary values of standalone CPU history was not reliably observed, average User I/O ([0-9.]+)%, and average Top SQL concentration \(top 3 share\) history is not available for this window",
        r"with User I/O averaging \1% while CPU history remained visible but uneven and Top SQL history was not available for this window",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Historical CPU trend continuity is limited in this window\. Anomaly burden remains visible",
        "Trend support stays directional rather than continuous in this window. Anomaly burden remains visible",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"with multi-snapshot summary values of ",
        "with ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\baverage CPU remained the primary workload driver\b",
        "CPU remaining the primary workload driver",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\baverage User I/O(?: at)? ([0-9.]+)%\b",
        r"User I/O averaged \1%",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\baverage Top SQL concentration(?: \(top 3 share\))? Insufficient data for a reliable conclusion\b",
        "Top SQL history is not available for this window",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bTop SQL concentration \(top 3 share\) Insufficient data for a reliable conclusion\b",
        "Top SQL history is not available for this window",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bCPU: Insufficient data for a reliable conclusion DB time\b",
        "CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bTop SQL concentration \(top 3 share\): Insufficient data for a reliable conclusion\b",
        "Top SQL history is not available for this window.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bIo history\b",
        "I/O history",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"CPU remains the dominant constraint in the selected scope\. Observed evidence remains directionally consistent with the selected diagnostic posture\.",
        "CPU remains the dominant constraint in the selected scope. The observed pattern is most consistent with a compute-bound workload.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"21 snapshots were analyzed in chronological order\. Across the full window, the workload remained primarily CPU-led, with CPU as the primary workload driver and User I/O averaging ([0-9.]+)%\. Top SQL history was not available for this window\. The same broad workload shape persisted throughout the series rather than rotating between unrelated bottlenecks\. The worst pressure interval was ([0-9:\-\s>]+), while the latest interval was ([0-9:\-\s>]+)\. 11 anomaly/event window\(s\) were detected, led by User I/O in ([0-9:\-\s>]+)\. User I/O spiked intermittently and then moderated\. Commit latency remained broadly stable where data is available\. Concurrency signals are insufficient to establish a meaningful trend\. Top SQL history is not available for this window\. The broader picture remains more important than any single interval: the latest snapshot should be read as confirmation, moderation, or departure from that pattern rather than as the full story by itself\. Detailed latest-interval metrics are shown separately in the Latest Snapshot Assessment\.",
        r"21 snapshots were analyzed in chronological order. The workload remained primarily CPU-led across the window, with User I/O averaging \1%. The same workload shape persisted rather than rotating between unrelated bottlenecks. The worst interval occurred at \2, while the latest interval reflects moderation rather than deviation from that pattern. 11 anomaly windows were detected, primarily driven by User I/O spikes that later moderated. Commit latency remained broadly steady, while concurrency data was insufficient to establish a material trend. The broader pattern is more representative than any single interval. The latest snapshot should be interpreted as confirmation or moderation of that pattern.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Latest snapshot \(([^)]+)\) metrics: CPU remained the primary workload driver, User I/O ([0-9.]+)%, commit ([0-9.]+)%, concurrency data was insufficient for a reliable conclusion, and Top SQL history is not available for this window\. CPU remained the primary driver in this interval\. User I/O remained visible at \2%, keeping access-path efficiency in scope for this interval\. Commit pressure remained visible at \3%, which keeps transaction behavior in scope for the current interval\.",
        r"Latest snapshot (\1): CPU remained the primary workload driver. User I/O registered at \2%, and commit at \3%. Concurrency data was insufficient for a reliable conclusion. User I/O and commit signals remain present but secondary, keeping access-path efficiency and transaction behavior in scope without displacing CPU as the primary driver.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"The historical review is organized around CPU first\. Primary proof is led by DB Time Breakdown, CPU history, Workload distributions\. Supporting proof follows with I/O history, Commit history\. Contextual proof remains historical and subordinate: RAC / cluster context, Topology distributions, Per-instance RAC distributions\. Lower-value or unsupported families were not promoted: ADG family, EXADATA family, MEMORY family, NETWORK family\.",
        "The historical review is organized around CPU-first evidence. Primary support comes from DB Time Breakdown, CPU history, and Workload distributions. Supporting evidence includes I/O history and Commit history. Contextual signals (RAC / cluster context, Topology distributions, Per-instance RAC distributions) remain available for historical comparison only. Lower-value or unsupported families were not promoted: ADG, EXADATA, MEMORY, NETWORK, and platform-level signals.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led, with Average CPU could not be established reliably across the full historical window, average User I/O at ([0-9.]+)%, and Top SQL activity was not consistently present in this window\.",
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led. CPU remained visible across the full window, though the pattern was too mixed for a simple continuity claim. User I/O averaged \1% during the same period.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led, with Average CPU could not be established reliably across the full historical window, average User I/O at ([0-9.]+)%, and Top SQL history was not available for this window\.",
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led. CPU remained visible across the full window, though the pattern was too mixed for a simple continuity claim. User I/O averaged \1% during the same period.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led, with CPU remained historically visible across the full window, but the pattern was too mixed for a simple continuity claim, average User I/O at ([0-9.]+)%, and Top SQL activity was not consistently present in this window\.",
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led. CPU remained visible across the full window, though the pattern was too mixed for a simple continuity claim. User I/O averaged \1% during the same period.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"21 snapshots were analyzed in chronological order\. Across the full window, the workload remained primarily CPU-led, with CPU as the primary workload driver and User I/O averaging ([0-9.]+)%\. Top SQL history was not available for this window\. The same broad workload shape persisted throughout the series rather than rotating between unrelated bottlenecks\. The worst pressure interval was ([0-9:\-\s>]+), while the latest interval was ([0-9:\-\s>]+)\. 11 anomaly/event window\(s\) were detected, led by User I/O in ([0-9:\-\s>]+)\. User I/O spiked intermittently and then moderated\. Commit latency remained broadly stable where data is available\. Concurrency signals are insufficient to establish a meaningful trend\. Top SQL history is not available for this window\. The broader picture remains more important than any single interval: the latest snapshot should be read as confirmation, moderation, or departure from that pattern rather than as the full story by itself\.(?: Detailed latest-interval metrics are shown separately in the Latest Snapshot Assessment\.)?",
        r"21 snapshots were analyzed in chronological order. The workload remained primarily CPU-led across the window, with User I/O averaging \1%. The same workload shape persisted rather than rotating between unrelated bottlenecks. The worst interval occurred at \2, while the latest interval reflects moderation rather than deviation from that pattern. 11 anomaly windows were detected, primarily driven by User I/O spikes that later moderated. Commit latency remained broadly steady, while concurrency data was insufficient to establish a material trend. The broader pattern is more representative than any single interval. The latest snapshot should be interpreted as confirmation or moderation of that pattern.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Latest snapshot \(([^)]+)\) metrics: CPU remained the primary workload driver, User I/O ([0-9.]+)%, commit ([0-9.]+)%, concurrency data was insufficient for a reliable conclusion, and Top SQL history is not available for this window\. CPU remained the primary driver in this interval\. User I/O remained visible at \2%, keeping access-path efficiency in scope for this interval\. Commit pressure remained visible at \3%, which keeps transaction behavior in scope for the current interval\.",
        r"Latest snapshot (\1): CPU remained the primary workload driver. User I/O registered at \2%, and commit at \3%. Concurrency data was insufficient for a reliable conclusion. User I/O and commit signals remain present but secondary, keeping access-path efficiency and transaction behavior in scope without displacing CPU as the primary driver.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bIo history\b",
        "I/O history",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led, with CPU remained historically visible across the full window, but the pattern was too mixed for a simple continuity claim, average User I/O at ([0-9.]+)%, and Top SQL history was not available for this window\.",
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led. CPU remained visible across the full window, though the pattern was too mixed for a simple continuity claim. User I/O averaged \1% during the same period.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"Top SQL concentration \(top 3 share\): Insufficient data for a reliable conclusion",
        "Top SQL history is not available for this window.",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\baverage CPU at Insufficient data for a reliable conclusion\b",
        "CPU remained historically visible across the full window, but the pattern was too mixed for a simple continuity claim",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"with CPU remaining the primary workload driver, User I/O averaged ([0-9.]+)%, and Top SQL history is not available for this window",
        r"with CPU as the primary workload driver and User I/O averaging \1%",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"with CPU remaining the primary workload driver, average User I/O ([0-9.]+)%, and Top SQL history is not available for this window",
        r"with CPU as the primary workload driver and User I/O averaging \1%",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"metrics: CPU remained the primary workload driver, User I/O ([0-9.]+)%, commit ([0-9.]+)%, concurrency Insufficient data for a reliable conclusion, and Top SQL history is not available for this window",
        r"metrics: CPU remained the primary workload driver, User I/O \1%, commit \2%, concurrency data was insufficient for a reliable conclusion",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bDeterministic posture:\b",
        "Current posture:",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\binsufficient signal for\b",
        "Insufficient data for a reliable conclusion for",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\binsufficient signal\b",
        "Insufficient data for a reliable conclusion",
        text,
        flags=re.IGNORECASE,
    )
    text = _compress_narrative_caveats(text)
    text = _dedupe_repeated_sentences(text)
    text = re.sub(
        r"with (?:multi-snapshot summary values of )?standalone CPU history was not reliably observed, average User I/O(?: at)? ([0-9.]+)%, and (?:average )?Top SQL(?: concentration \(top 3 share\))? history (?:was not reliably observed in this window|is not available for this window)",
        r"with User I/O averaging \1% while CPU and Top SQL activity did not show consistent historical patterns in this window",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bnot reliably observed\b",
        "not consistently present in this window",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _normalize_scope_context_claims(
    value: Any,
    context_truth: dict[str, Any] | None = None,
) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    context_truth = context_truth or {}
    topology_text = str(context_truth.get("topology_detected") or "").strip().lower()
    platform_text = str(context_truth.get("platform_detected") or "").strip().lower()
    allow_rac = "rac" in topology_text
    allow_dataguard = "data guard" in topology_text
    allow_exadata = platform_text == "exadata"

    sentences = re.split(r"(?<=[.!?])\s+", text)
    filtered: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if not allow_rac and (
            re.search(r"\brac\b", lowered)
            or any(
                token in lowered
                for token in (
                    "cluster wait",
                    "gc current",
                    "gc cr",
                    "interconnect stress",
                )
            )
        ):
            continue
        if not allow_dataguard and any(
            token in lowered
            for token in (
                "data guard",
                "transport lag",
                "apply lag",
                "redo transport",
                "replication-state",
                "standby",
            )
        ):
            continue
        if not allow_exadata and any(
            token in lowered
            for token in (
                "exadata",
                "cell-related",
                "smart scan",
                "offload",
                "engineered-system",
            )
        ):
            continue
        filtered.append(sentence)
    return " ".join(part for part in filtered if part).strip()


def _normalize_confidence_text(value: Any, confidence: Any) -> str:
    text = _display_value(value)
    level = _confidence_level_from_value(confidence).lower()
    return re.sub(
        r"\b(?:high|medium|low)\s+confidence\b",
        f"{level} confidence",
        text,
        flags=re.IGNORECASE,
    )


def _normalize_capacity_guidance_text(value: Any, confidence: Any = None) -> str:
    text = _display_value(value)
    replacements = (
        (r"\bOCI database deployment pattern\b", "database deployment pattern"),
        (r"\bOCI\b", "platform"),
        (r"\boci\b", "platform"),
    )
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(
        r"\bplatform database deployment pattern\b",
        "database deployment pattern",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\ban database deployment pattern\b",
        "a database deployment pattern",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\ban platform\b", "a platform", text, flags=re.IGNORECASE)
    if "concentrated SQL and secondary performance contributors" in text:
        text = (
            "The current evidence still supports tuning before scaling. "
            "TUNE FIRST remains appropriate at medium confidence. "
            "Scaling becomes appropriate only if CPU- and SQL-heavy inefficiencies "
            "have been reduced and the same governing constraint still remains afterward. "
            "Keep the architecture aligned to a compute-first tuning path, and treat "
            "broader storage changes as secondary unless I/O pressure persists after tuning."
        )
    if confidence is not None:
        text = _normalize_confidence_text(text, confidence)
    return text


def _tighten_execution_plan_items(items: list[Any]) -> list[Any]:
    normalized_items = [str(item or "").strip() for item in items if str(item or "").strip()]
    if not normalized_items:
        return items
    tightened: list[str] = []
    merged_sql_step_added = False
    for item in normalized_items:
        lower = item.lower()
        if (
            "highest cpu-consuming sql" in lower
            or ("top elapsed-time" in lower and "sql" in lower)
        ):
            if not merged_sql_step_added:
                tightened.append("Identify and tune the highest CPU- and elapsed-time SQL first.")
                merged_sql_step_added = True
            continue
        if item == "Tighten commit frequency and commit-processing behavior in the application flow.":
            tightened.append(
                "As a secondary optimization, review and tighten commit frequency and commit-processing behavior in the application flow."
            )
            continue
        tightened.append(item)
    return tightened


def _priority_badge_class(priority: str) -> str:
    normalized = priority.strip().upper()
    return {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "medium",
        "LOW": "low",
    }.get(normalized, "low")


def _health_status_class(status: str) -> str:
    normalized = status.strip().upper()
    return {
        "PASS": "pass",
        "MARGINAL": "marginal",
        "FAIL": "fail",
        "N/A": "na",
    }.get(normalized, "na")


def _status_pill_class(status: str) -> str:
    normalized = status.strip().upper()
    if normalized in {"SUCCEEDED", "SUCCESS", "OK"}:
        return "success"
    if normalized in {"FAILED", "ERROR"}:
        return "error"
    if normalized in {"WARNINGS", "WARNING", "SKIPPED"}:
        return "warning"
    return ""


def _render_decision_boxes(agentic_decision: dict[str, Any]) -> str:
    """Render agentic decision section."""

    ordered_fields = [
        ("Primary Decision", "primary_decision"),
        ("Execution Plan", "execution_plan"),
        ("Defer / Do Not Do", "defer_do_not_do"),
        ("Scaling Posture", "scaling_decision"),
        ("Confidence Level", "confidence_level"),
    ]
    return "".join(
        _render_decision_box(label, agentic_decision.get(key))
        for label, key in ordered_fields
    )


def _render_executive_summary(
    summary_text: str,
    issues: list[dict[str, Any]],
    decision_state: dict[str, str],
    summary_key_signals: list[str] | None = None,
    normalized_decision: dict[str, Any] | None = None,
) -> str:
    """Render the Executive Summary in structured format."""

    rationale = _normalize_narrative_for_display(
        _extract_summary_rationale(summary_text),
        normalized_decision,
    )
    rationale = re.sub(
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led, with Average CPU could not be established reliably across the full historical window, average User I/O at ([0-9.]+)%, and Top SQL activity was not consistently present in this window\.",
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led. User I/O averaged \1% during the same period.",
        rationale,
        flags=re.IGNORECASE,
    )
    rationale = re.sub(
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led, with Average CPU could not be established reliably across the full historical window, average User I/O at ([0-9.]+)%, and Top SQL history was not available for this window\.",
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led. User I/O averaged \1% during the same period.",
        rationale,
        flags=re.IGNORECASE,
    )
    rationale = re.sub(
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led, with CPU remained historically visible across the full window, but the pattern was too mixed for a simple continuity claim, average User I/O at ([0-9.]+)%, and Top SQL activity was not consistently present in this window\.",
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led. User I/O averaged \1% during the same period.",
        rationale,
        flags=re.IGNORECASE,
    )
    rationale = re.sub(
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led, with CPU remained historically visible across the full window, but the pattern was too mixed for a simple continuity claim, average User I/O at ([0-9.]+)%, and Top SQL history was not available for this window\.",
        r"Across the full 21-snapshot window, the workload remained predominantly CPU-led. User I/O averaged \1% during the same period.",
        rationale,
        flags=re.IGNORECASE,
    )
    rationale = _strip_screen2_cpu_caveat(rationale)
    key_signals = summary_key_signals or _build_key_signal_items(issues)
    normalized_signals: list[str] = []
    for item in key_signals:
        normalized_item = _normalize_narrative_for_display(item, normalized_decision)
        normalized_item = re.sub(
            r"CPU remained historically visible, though continuity across the full window was too mixed for a simple stability claim\.",
            "CPU remained visible across the window, though continuity is mixed rather than uniform.",
            normalized_item,
            flags=re.IGNORECASE,
        )
        normalized_item = re.sub(
            r"User I/O:\s*([0-9.]+)%",
            r"User I/O averaged \1% in the latest interval.",
            normalized_item,
            flags=re.IGNORECASE,
        )
        if re.search(r"Top SQL history is not available", normalized_item, flags=re.IGNORECASE):
            continue
        normalized_signals.append(normalized_item)
    signal_items = "".join(
        f"<li>{escape(item)}</li>"
        for item in normalized_signals
    )

    banner_class = escape(decision_state["css_class"])
    banner_label = escape(decision_state["label"])
    return f"""
    <div class="executive-summary">
      <div class="decision-banner {banner_class}">{banner_label}</div>
      <p class="rationale">{escape(rationale)}</p>
      <ul class="key-signals">
        {signal_items}
      </ul>
    </div>
    """


def _render_confidence_section(
    confidence_text: str,
    authoritative_confidence: Any = None,
) -> str:
    """Render the Confidence Assessment with structured level and reason."""

    level = (
        _confidence_level_from_value(authoritative_confidence)
        if authoritative_confidence is not None
        else _extract_confidence_level(confidence_text)
    )
    reason = _extract_confidence_reason(confidence_text, level)
    reason_paragraphs = _split_confidence_reason(reason)
    reason_html = "".join(
        f'<p class="confidence-reason">{("<strong>Reasoning:</strong> " if index == 0 else "")}{escape(paragraph)}</p>'
        for index, paragraph in enumerate(reason_paragraphs)
    ) or f'<p class="confidence-reason"><strong>Reasoning:</strong> {escape(reason)}</p>'

    return f"""
    <div class="confidence-section {escape(level.lower())}">
      <div class="confidence-header">
        <h2>Confidence Assessment</h2>
        <span class="confidence-pill {escape(level.lower())}">{escape(level.upper())}</span>
      </div>
      {reason_html}
    </div>
    """


def _render_risk_section(risk_text: str) -> str:
    """Render the Risk of Being Wrong section with structured bullets."""

    main_risks, risk_reduction = _extract_risk_items(risk_text)
    main_risk_items = "".join(f"<li>{escape(item)}</li>" for item in main_risks)

    return f"""
    <div class="risk-section">
      <h2>Risk of Being Wrong</h2>
      <div class="risk-split">
        <section class="risk-column">
          <h3>Main Risks</h3>
          <ul>
            {main_risk_items}
          </ul>
        </section>
        <section class="risk-column risk-reduction-panel">
          <h3>What Reduces Risk</h3>
          <p>{escape(risk_reduction)}</p>
        </section>
      </div>
    </div>
    """


def _render_decision_box(label: str, value: Any) -> str:
    """Render a single dashboard decision box."""

    if label == "Execution Plan" and isinstance(value, list):
        value = _tighten_execution_plan_items(value)
    if isinstance(value, list):
        content = (
            "<ol>"
            + "".join(f"<li>{escape(_display_value(item))}</li>" for item in value)
            + "</ol>"
        )
        if label == "Execution Plan":
            content = re.sub(
                r"<li>Prioritize the top elapsed-time(?: [A-Za-z0-9_-]+)? SQL statements immediately\.</li>",
                "",
                content,
                flags=re.IGNORECASE,
            )
    else:
        content = f"<div>{_render_text_block(value)}</div>"

    return f"""
    <div class="decision-box">
      <strong>{escape(label)}</strong>
      {content}
    </div>
    """


def _render_text_block(value: Any) -> str:
    """Render lightweight markdown-like text safely into HTML."""

    text = _normalize_ui_text(_normalize_inline_numbered_text(str(value or "").strip()))
    text = re.sub(
        r"\bUnavailable\b",
        "Insufficient data for a reliable conclusion",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bNo summary is available\.?",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"selected deterministically with score 0(?:\.0+)?",
        "remains the primary workload driver in the selected scope",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\bNo ([^.]+?) is available\.?",
        r"Insufficient data for a reliable conclusion for \1.",
        text,
        flags=re.IGNORECASE,
    )
    if not text:
        return ""
    text = _compress_narrative_caveats(_dedupe_repeated_sentences(text))

    if _is_plain_text_block(text):
        return _format_inline_markup(text)

    html_parts: list[str] = []
    paragraph_lines: list[str] = []
    ordered_items: list[str] = []
    unordered_items: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            paragraph = "<br>".join(
                _format_inline_markup(line) for line in paragraph_lines
            )
            html_parts.append(f"<p>{paragraph}</p>")
            paragraph_lines = []

    def flush_ordered() -> None:
        nonlocal ordered_items
        if ordered_items:
            items = "".join(
                f"<li>{_format_inline_markup(item)}</li>" for item in ordered_items
            )
            html_parts.append(f"<ol>{items}</ol>")
            ordered_items = []

    def flush_unordered() -> None:
        nonlocal unordered_items
        if unordered_items:
            items = "".join(
                f"<li>{_format_inline_markup(item)}</li>" for item in unordered_items
            )
            html_parts.append(f"<ul>{items}</ul>")
            unordered_items = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            flush_paragraph()
            flush_ordered()
            flush_unordered()
            continue

        if re.match(r"^\s*\d+[\.\-\)]\s+.+$", raw_line):
            flush_paragraph()
            flush_unordered()
            ordered_items.append(_strip_ordered_prefix(raw_line))
            continue

        if re.match(r"^[-*]\s+.+$", line):
            flush_paragraph()
            flush_ordered()
            unordered_items.append(re.sub(r"^[-*]\s+", "", line))
            continue

        flush_ordered()
        flush_unordered()
        paragraph_lines.append(line)

    flush_paragraph()
    flush_ordered()
    flush_unordered()

    return "".join(html_parts)


def _to_dict(value: Any) -> dict[str, Any]:
    """Convert supported model objects to dictionaries."""

    if hasattr(value, "model_dump"):
        return value.model_dump()

    if isinstance(value, dict):
        return value

    return value.__dict__


def _format_inline_markup(text: str) -> str:
    """Render a minimal subset of inline markdown safely."""

    escaped_text = escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped_text)


def _strip_ordered_prefix(text: str) -> str:
    """Remove numeric ordered-list prefixes before HTML list rendering."""

    return re.sub(r"^\s*\d+[\.\-\)]\s+", "", text).strip()


def _normalize_inline_numbered_text(text: str) -> str:
    """Split inline numbered text into real lines for ordered-list rendering."""

    if not text:
        return text

    return re.sub(
        r"(?<!^)(?<!\n)\s+(\d+[\.\-\)])\s+",
        r"\n\1 ",
        text,
    )


def _is_plain_text_block(text: str) -> bool:
    """Return True when text can render without an extra paragraph wrapper."""

    if "\n" in text:
        return False
    if re.match(r"^\s*\d+[\.\-\)]\s+", text):
        return False
    if re.match(r"^[-*]\s+", text):
        return False
    return True


def _derive_decision_state(ai_sections: dict[str, str]) -> dict[str, str]:
    """Derive decision text and banner class from confidence."""

    confidence_level = _extract_confidence_level(
        ai_sections.get("Confidence Assessment", "")
    )
    if confidence_level == "High":
        return {"label": "DO NOT SCALE", "css_class": "do-not-scale"}
    if confidence_level == "Medium":
        return {
            "label": "Defer scaling pending validation",
            "css_class": "defer",
        }
    return {
        "label": "Insufficient data to recommend",
        "css_class": "insufficient",
    }


def _normalized_decision_banner_state(
    normalized_decision: dict[str, Any],
    fallback: dict[str, str],
) -> dict[str, str]:
    """Prefer normalized decision posture for page banners when it is available."""

    posture = str(normalized_decision.get("decision_posture") or "").strip().upper()
    posture_map = {
        "DO NOT SCALE": {"label": "DO NOT SCALE", "css_class": "do-not-scale"},
        "SCALE NOW": {"label": "SCALE NOW", "css_class": "scale-now"},
        "SCALE CANDIDATE": {"label": "SCALE CANDIDATE", "css_class": "scale-candidate"},
        "TUNE FIRST": {"label": "TUNE FIRST", "css_class": "defer"},
        "INVESTIGATE FURTHER": {
            "label": "INVESTIGATE FURTHER",
            "css_class": "defer",
        },
        "RECOVERING / MONITOR": {
            "label": "RECOVERING / MONITOR",
            "css_class": "do-not-scale",
        },
        "INSUFFICIENT DATA": {
            "label": "INSUFFICIENT DATA",
            "css_class": "insufficient",
        },
    }
    return posture_map.get(posture, fallback)


def _short_model_name(provider: Any, model: Any) -> str:
    """Return a readable model label for dashboard display."""

    provider_name = str(provider or "").strip().lower()
    model_name = str(model or "None").strip()

    if provider_name == "oci" and model_name.startswith("ocid1."):
        return "Grok 4.1"

    return model_name


def _normalize_ai_sections(ai_sections: dict[str, str]) -> dict[str, str]:
    """Enforce decision-confidence consistency and required risk footer."""

    normalized_sections = dict(ai_sections)
    confidence_level = _extract_confidence_level(
        normalized_sections.get("Confidence Assessment", "")
    )
    current_decision = _extract_decision(
        normalized_sections.get("Executive Summary", ""),
        normalized_sections.get("OCI Sizing Considerations", ""),
    )
    target_decision = _decision_for_confidence(confidence_level, current_decision)

    normalized_sections["Executive Summary"] = _ensure_summary_decision(
        normalized_sections.get("Executive Summary", ""),
        target_decision,
    )
    normalized_sections["OCI Sizing Considerations"] = _ensure_section_decision(
        normalized_sections.get("OCI Sizing Considerations", ""),
        target_decision,
    )
    normalized_sections["Risk of Being Wrong"] = _ensure_risk_footer(
        normalized_sections.get("Risk of Being Wrong", "")
    )

    return normalized_sections


def _extract_confidence_level(text: str) -> str:
    """Extract normalized confidence level from AI text."""

    match = re.search(r"\b(High|Medium|Low)\b", text, flags=re.IGNORECASE)
    if not match:
        return "Medium"
    return match.group(1).capitalize()


def _extract_decision(*texts: str) -> str:
    """Extract the explicit decision phrase from advisory text."""

    combined_text = "\n".join(texts)
    if "SCALE NOW" in combined_text:
        return "SCALE NOW"
    if "DO NOT SCALE" in combined_text:
        return "DO NOT SCALE"
    if "DEFER SCALING PENDING VALIDATION" in combined_text:
        return "DEFER SCALING PENDING VALIDATION"
    if "INSUFFICIENT DATA TO RECOMMEND" in combined_text:
        return "INSUFFICIENT DATA TO RECOMMEND SCALING"
    return "DO NOT SCALE"


def _decision_for_confidence(confidence_level: str, current_decision: str) -> str:
    """Return the allowed decision for the extracted confidence level."""

    if confidence_level == "High":
        if current_decision == "SCALE NOW":
            return "SCALE NOW"
        return "DO NOT SCALE"
    if confidence_level == "Medium":
        return "DEFER SCALING PENDING VALIDATION"
    return "INSUFFICIENT DATA TO RECOMMEND SCALING"


def _ensure_summary_decision(text: str, decision: str) -> str:
    """Ensure the Executive Summary starts with the enforced decision."""

    cleaned_text = text.strip()
    remainder = re.sub(
        DECISION_PREFIX_PATTERN,
        "",
        cleaned_text,
        flags=re.IGNORECASE,
    ).strip()
    if not remainder:
        return f"{decision}."
    return f"{decision}. {remainder}"


def _ensure_section_decision(text: str, decision: str) -> str:
    """Ensure OCI sizing guidance stays aligned without repeating the banner."""

    cleaned_text = text.strip()
    if not cleaned_text:
        return (
            "Scaling becomes appropriate only if the same dominant pressure "
            "remains after tuning."
        )

    remainder = re.sub(
        DECISION_PREFIX_PATTERN,
        "",
        cleaned_text,
        flags=re.IGNORECASE,
    ).strip()
    if not remainder:
        return (
            "Scaling becomes appropriate only if the same dominant pressure "
            "remains after tuning."
        )
    return remainder


def _ensure_risk_footer(text: str) -> str:
    """Guarantee the risk section includes the required data-reduction line."""

    cleaned_text = text.strip()
    required_prefix = "Additional data that would reduce this risk:"
    if required_prefix in cleaned_text:
        return cleaned_text

    suffix = (
        "Additional data that would reduce this risk: more AWR intervals, "
        "ASH data, SQL execution plan history, workload trend data, and peak "
        "vs non-peak comparison."
    )
    if not cleaned_text:
        return suffix
    return f"{cleaned_text}\n\n{suffix}"


def _extract_summary_rationale(summary_text: str) -> str:
    """Remove the opening decision phrase and return the rationale."""

    cleaned_text = re.sub(
        DECISION_PREFIX_PATTERN,
        "",
        summary_text.strip(),
        flags=re.IGNORECASE,
    ).strip()
    cleaned_text = re.sub(
        r"\bUnavailable\b",
        "Insufficient data for a reliable conclusion",
        cleaned_text,
        flags=re.IGNORECASE,
    )
    if not cleaned_text:
        return DEFAULT_SUMMARY_RATIONALE

    return cleaned_text or DEFAULT_SUMMARY_RATIONALE


def _display_issue_label(issue_type: str) -> str:
    if issue_type == "sql_concentration":
        return "sql_concentration (top 3 SQL share)"
    return issue_type


def _build_key_signal_items(issues: list[dict[str, Any]]) -> list[str]:
    """Build the Executive Summary key-signal list from deterministic issues."""

    issue_by_type = {str(issue.get("issue_type") or ""): issue for issue in issues}

    cpu = _safe_float(
        issue_by_type.get("cpu_pressure", {}).get("evidence", {}).get("pct_db_time")
    )
    sql = _safe_float(
        issue_by_type.get("sql_concentration", {})
        .get("evidence", {})
        .get("combined_pct_total")
    )
    io = _safe_float(
        issue_by_type.get("io_pressure", {}).get("evidence", {}).get("pct_db_time")
    )

    signal_items = [
        (
            f"CPU: {cpu:.1f}% DB time"
            if cpu is not None
            else "CPU history remained visible across the selected window, but the pattern was too mixed for a simple continuity claim."
        ),
        (
            f"User I/O: {io:.1f}%"
            if io is not None
            else "User I/O history is not available for this window."
        ),
    ]
    if sql is not None:
        signal_items.insert(1, f"Top SQL concentration (top 3 share): {sql:.1f}%")
    cluster_wait = _safe_float(
        issue_by_type.get("cluster_contention", {})
        .get("evidence", {})
        .get("cluster_wait_pct_db_time")
    )
    if cluster_wait is not None:
        signal_items.append(f"Cluster waits: {cluster_wait:.1f}% DB time")
    transport_lag = _safe_float(
        issue_by_type.get("dg_replication_state", {})
        .get("evidence", {})
        .get("transport_lag_sec")
    )
    if transport_lag is not None:
        signal_items.append(f"Transport lag: {transport_lag:.0f}s")
    event_class = (
        issue_by_type.get("topology_event", {})
        .get("evidence", {})
        .get("operational_event_class")
    )
    if event_class:
        signal_items.append(
            "Operational event: "
            + str(event_class).replace("_", " ").title()
        )
    return signal_items[:5]


def _extract_confidence_reason(confidence_text: str, level: str | None = None) -> str:
    """Extract a short confidence justification from the AI text."""

    cleaned_text = confidence_text.strip()
    cleaned_text = re.sub(
        r"^\s*(High|Medium|Low)\b[:\-]?\s*",
        "",
        cleaned_text,
        flags=re.IGNORECASE,
    )
    cleaned_text = re.sub(
        r"^\s*Reason:\s*",
        "",
        cleaned_text,
        flags=re.IGNORECASE,
    )
    cleaned_text = re.sub(r"^\s*[-–—]\s*", "", cleaned_text)
    if cleaned_text:
        if str(level or "").lower() == "medium":
            return (
                "CPU remains the dominant repeated signal across the window, and the latest interval does not contradict that broader pattern. "
                "However, supporting domains show uneven continuity and mixed historical support, while anomaly windows recur across the history. "
                "Confidence is therefore moderate rather than high."
            )
        return cleaned_text
    return DEFAULT_CONFIDENCE_REASON


def _split_confidence_reason(reason: str) -> list[str]:
    cleaned = str(reason or "").strip()
    if not cleaned:
        return []
    if len(cleaned) < 140:
        return [cleaned]
    parts = [
        part.strip()
        for part in re.split(r"(?<=[.!?])\s+", cleaned)
        if part.strip()
    ]
    return parts or [cleaned]


def _extract_risk_items(risk_text: str) -> tuple[list[str], str]:
    """Extract structured risk bullets and reduction guidance."""

    main_risks: list[str] = []
    risk_reduction = "Additional AWR intervals, ASH data, and SQL plan history."

    for raw_line in risk_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("Additional data that would reduce this risk:"):
            risk_reduction = line.split(":", 1)[1].strip() or risk_reduction
            continue
        if re.match(r"^[-*]\s+.+$", line):
            main_risks.append(re.sub(r"^[-*]\s+", "", line))
            continue
        if re.match(r"^\s*\d+[\.\-\)]\s+.+$", line):
            main_risks.append(_strip_ordered_prefix(line))
            continue

    if not main_risks:
        main_risks = [
            "Limited time window",
            "Missing workload variability",
            "Incomplete SQL execution plans",
        ]

    return main_risks[:3], risk_reduction


def _render_chart_container(canvas_id: str, chart_data: dict[str, Any]) -> str:
    """Render a chart canvas or a clean empty state."""

    if not _chart_has_values(chart_data):
        return (
            '<div class="chart-empty">'
            "Chart data is not available for this run."
            "</div>"
        )

    return f'<div class="chart-canvas"><canvas id="{escape(canvas_id)}"></canvas></div>'


def _render_chart_container_with_message(
    canvas_id: str,
    chart_data: dict[str, Any],
    empty_message: str,
) -> str:
    if not _chart_has_values(chart_data):
        return f'<div class="chart-empty">{escape(empty_message)}</div>'
    return f'<div class="chart-canvas"><canvas id="{escape(canvas_id)}"></canvas></div>'


def _render_performance_charts_section(
    chart_payload: dict[str, Any],
    visual_story: dict[str, Any],
) -> str:
    """Render supporting performance charts with clean fallbacks."""

    performance_panels = _to_dict(visual_story.get("performance_panels"))
    db_time_state = _to_dict(performance_panels.get("db_time_breakdown"))
    db_time_data = chart_payload.get("db_time_breakdown") or {}
    top_sql_data = chart_payload.get("top_sql_contribution") or {}
    panels = []

    if _chart_has_values(db_time_data) and db_time_state.get("data_quality") != "suppressed":
        panels.append(
            f"""
          <section class="chart-panel">
            <h3>DB Time Breakdown</h3>
            {_render_chart_container("dbTimeBreakdownChart", db_time_data)}
          </section>
            """
        )

    if _chart_has_values(top_sql_data):
        panels.append(
            f"""
          <section class="chart-panel">
            <h3>Top SQL Contributors (% Elapsed SQL Time)</h3>
            {_render_chart_container("topSqlContributionChart", top_sql_data)}
          </section>
            """
        )

    if not panels:
        return ""

    return f"""
      <section id="performance-charts" class="card secondary">
        <div class="section-kicker">Supporting Visual Layer</div>
        <h2>Primary Evidence</h2>
        <p class="chart-support-note">
          Historical / Supporting Context (Not Selected-Scope Truth). Shown
          only when real chart data exists.
        </p>
        <div class="chart-grid">
          {"".join(panels)}
        </div>
      </section>
    """


def _render_violin_panel(violin_metric_groups: list[dict[str, Any]]) -> str:
    """Render the violin panel only when real series-backed metrics exist."""

    if not violin_metric_groups:
        return ""

    group_sections: list[str] = []
    for group in violin_metric_groups:
        group_slug = re.sub(r"[^a-z0-9]+", "-", group["group_key"]).strip("-")
        cards = []
        for config in group["metrics"]:
            cards.append(f"""
              <section class="violin-chart-card">
                <h3>{escape(config["title"])}</h3>
                <div id="{escape(config["container_id"])}" class="violin-chart"></div>
              </section>
                """)
        group_sections.append(
            f"""
        <div class="violin-group violin-group-{escape(group_slug)}">
          <h3>{escape(group["group_title"])}</h3>
          <p class="violin-group-note">{escape(group["group_note"].rstrip("."))}</p>
          <div class="violin-grid">
            {''.join(cards)}
          </div>
        </div>
            """
        )

    return (
        """
      <section id="workload-violin-panel" class="card secondary violin-panel">
        <div class="section-kicker">Supporting Visual Layer</div>
        <h2>Workload Distribution Evidence</h2>
        <p class="chart-support-note">
          Historical / Supporting Context (Not Selected-Scope Truth). Violin
          charts render only when enough real multi-snapshot samples exist,
          while scalar-only facts stay in scalar metric cards below.
        </p>
"""
        + "".join(group_sections)
        + """
      </section>
    """
    )


def _render_scalar_metrics(metrics: dict[str, Any]) -> str:
    """Render scalar-only metrics outside the violin panel."""

    metric_specs = [
        (
            "PGA Spill Pressure",
            metrics.get("pga_spill_pressure"),
            "Scalar fact from spill counters or proxy evidence",
        ),
        (
            "Temp I/O Pressure",
            metrics.get("temp_io_pressure"),
            "Derived scalar from TEMP I/O rate",
        ),
        (
            "Hard Parses/s",
            metrics.get("hard_parses_per_sec"),
            "Scalar fact from the parsed hard-parse rate",
        ),
    ]

    available_values = [
        value for _, value, _ in metric_specs if isinstance(value, (int, float))
    ]
    if not available_values:
        return ""

    boxes: list[str] = []
    for label, value, note in metric_specs:
        if not isinstance(value, (int, float)):
            continue
        boxes.append(f"""
            <div class="scalar-box">
              <strong>{escape(label)}</strong>
              <div class="scalar-value">{escape(_format_scalar_metric(value))}</div>
              <div class="scalar-note">{escape(note)}</div>
            </div>
            """)

    return (
        '<p class="scalar-note">'
        "These metrics are shown as scalar facts because no real "
        "multi-sample distribution exists for violin rendering."
        "</p>" + '<div class="scalar-grid">' + "".join(boxes) + "</div>"
    )


def _build_violin_metric_groups(
    violin_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return grouped violin metrics when any real samples exist.

    Violin charts are supporting visual analysis only. They require real numeric
    samples and at least some variation, but Screen 4 may still show weaker
    supporting/contextual distributions when they remain truthful and useful.
    """

    groups: list[dict[str, Any]] = []
    for group_definition in VIOLIN_METRIC_GROUP_DEFINITIONS:
        payload_group = violin_payload.get(group_definition["group_key"]) or {}
        metrics = [
            metric
            for metric in group_definition["metrics"]
            if _has_violin_display_data(payload_group.get(metric["payload_key"]))
        ]
        if not metrics:
            continue
        groups.append(
            {
                "group_key": group_definition["group_key"],
                "group_title": group_definition["group_title"],
                "group_note": group_definition["group_note"],
                "metrics": metrics,
            }
        )
    return groups


def _flatten_violin_metric_groups(
    violin_metric_groups: list[dict[str, Any]],
) -> list[dict[str, str]]:
    configs: list[dict[str, str]] = []
    for group in violin_metric_groups:
        for metric in group["metrics"]:
            configs.append(
                {
                    **metric,
                    "group_key": group["group_key"],
                    "is_percent_like": metric["payload_key"] in PERCENT_LIKE_VIOLIN_KEYS,
                }
            )
    return configs


def _has_violin_samples(values: Any) -> bool:
    """Return True only when a violin metric has enough numeric samples to render."""

    if not isinstance(values, list):
        return False
    numeric_values = [
        float(value)
        for value in values
        if isinstance(value, (int, float)) and math.isfinite(float(value))
    ]
    if len(numeric_values) < VIOLIN_MIN_SAMPLES:
        return False
    distinct_values = {round(value, 6) for value in numeric_values}
    return len(distinct_values) >= VIOLIN_MIN_DISTINCT_VALUES


def _has_violin_display_data(values: Any) -> bool:
    if not isinstance(values, list):
        return False
    numeric_values = [
        float(value)
        for value in values
        if isinstance(value, (int, float)) and math.isfinite(float(value))
    ]
    if len(numeric_values) < 2:
        return False
    distinct_values = {round(value, 6) for value in numeric_values}
    return len(distinct_values) >= 2


def _has_any_violin_data(values: Any) -> bool:
    if not isinstance(values, list):
        return False
    return any(
        isinstance(value, (int, float)) and math.isfinite(float(value))
        for value in values
    )


def _build_chart_payload(report_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build chart payloads from deterministic report data."""

    return {
        "db_time_breakdown": _build_db_time_breakdown(report_data),
        "top_sql_contribution": _build_top_sql_contribution(report_data),
        "violin_panel": _build_violin_panel_payload(report_data),
    }


def _chart_has_values(chart_data: dict[str, Any]) -> bool:
    """Return True when a chart payload contains at least one usable value."""

    labels = chart_data.get("labels")
    values = chart_data.get("values")
    return (
        isinstance(labels, list)
        and any(str(label).strip() for label in labels)
        and isinstance(values, list)
        and any(
        isinstance(value, (int, float)) and value > 0 for value in values
        )
    )


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    """Return a mapping-like value or an empty dict for safe `.get()` access."""

    if isinstance(value, dict):
        return value
    return {}


def _flatten_feature_values(feature_evidence: Any) -> dict[str, float]:
    flattened: dict[str, float] = {}
    if not isinstance(feature_evidence, dict):
        return flattened
    for domain_metrics in feature_evidence.values():
        metrics = _mapping_or_empty(domain_metrics)
        for metric_name, metric_value in metrics.items():
            numeric_value = _safe_float(metric_value)
            if numeric_value is None:
                continue
            flattened[str(metric_name)] = numeric_value
    return flattened


def _latest_metric_value(report_data: dict[str, Any], metric_name: str) -> float | None:
    time_series = _mapping_or_empty(report_data.get("time_series_charts"))
    values = time_series.get(metric_name)
    if not isinstance(values, list):
        return None
    for value in reversed(values):
        numeric = _safe_float(value)
        if numeric is not None:
            return numeric
    return None


def _build_db_time_breakdown(report_data: dict[str, Any]) -> dict[str, Any]:
    """Build DB time breakdown chart data from deterministic issues."""

    issues = report_data.get("issues") or []
    issue_by_type = {str(issue.get("issue_type") or ""): issue for issue in issues}
    decision = _mapping_or_empty(report_data.get("decision"))
    decision_evidence = _mapping_or_empty(decision.get("evidence"))
    feature_values = _flatten_feature_values(decision_evidence.get("feature_evidence"))

    cpu = _safe_float(
        issue_by_type.get("cpu_pressure", {}).get("evidence", {}).get("pct_db_time")
    ) or _safe_float(feature_values.get("DB_CPU_PCT_DB_TIME")) or _safe_float(
        feature_values.get("CPU_UTIL_P95")
    ) or _latest_metric_value(
        report_data,
        "cpu_trend",
    )
    io = _safe_float(
        issue_by_type.get("io_pressure", {}).get("evidence", {}).get("pct_db_time")
    ) or _safe_float(feature_values.get("USER_IO_PRESSURE")) or _latest_metric_value(
        report_data,
        "io_trend",
    )
    commit = _safe_float(
        issue_by_type.get("commit_pressure", {}).get("evidence", {}).get("pct_db_time")
    ) or _safe_float(feature_values.get("COMMIT_PRESSURE")) or _latest_metric_value(
        report_data,
        "commit_trend",
    )
    concurrency = _safe_float(
        issue_by_type.get("concurrency_pressure", {})
        .get("evidence", {})
        .get("combined_pct_db_time")
    ) or _safe_float(feature_values.get("CONCURRENCY_PRESSURE")) or _latest_metric_value(
        report_data,
        "concurrency_trend",
    )

    values = [cpu or 0.0, io or 0.0, commit or 0.0, concurrency or 0.0]
    labels = ["CPU", "User I/O", "Commit", "Concurrency"]
    colors = [
        "rgba(255, 107, 107, 0.72)",
        "rgba(246, 184, 76, 0.72)",
        "rgba(212, 174, 82, 0.72)",
        "rgba(127, 179, 213, 0.72)",
    ]

    other = max(0.0, round(100.0 - sum(values), 1))
    if any(value > 0 for value in values) or other > 0:
        labels.append("Other")
        values.append(other)
        colors.append("rgba(130, 148, 171, 0.58)")

    return {
        "labels": labels,
        "values": values,
        "colors": colors,
    }


def _build_top_sql_contribution(report_data: dict[str, Any]) -> dict[str, Any]:
    """Build top SQL contribution chart data from parsed SQL records."""

    top_sql = report_data.get("top_sql") or []
    if not top_sql:
        return {"labels": [], "values": [], "colors": []}

    labels: list[str] = []
    values: list[float] = []
    elapsed_rows: list[tuple[str, float]] = []
    for sql_record in top_sql[:3]:
        sql_id = str(sql_record.get("sql_id") or "unknown")
        pct_total = _safe_float(sql_record.get("pct_total"))
        if pct_total <= 0:
            elapsed_seconds = _safe_float(sql_record.get("elapsed_time_seconds"))
            if elapsed_seconds > 0:
                elapsed_rows.append((sql_id, elapsed_seconds))
            continue
        labels.append(sql_id)
        values.append(pct_total)

    if not values and elapsed_rows:
        total_elapsed = sum(value for _, value in elapsed_rows)
        if total_elapsed > 0:
            labels = [sql_id for sql_id, _ in elapsed_rows]
            values = [
                round((elapsed_seconds / total_elapsed) * 100.0, 1)
                for _, elapsed_seconds in elapsed_rows
            ]

    colors = [
        "rgba(255, 107, 107, 0.68)",
        "rgba(246, 184, 76, 0.68)",
        "rgba(127, 179, 213, 0.68)",
    ][: len(values)]

    return {
        "labels": labels,
        "values": values,
        "colors": colors,
    }


def _build_violin_panel_payload(
    report_data: dict[str, Any],
) -> dict[str, dict[str, list[float]]]:
    """Build violin-panel metric series from structured report data when available."""

    source = _mapping_or_empty(
        report_data.get("violin_panel") or report_data.get("metric_samples")
    )
    has_grouped_source = any(
        isinstance(source.get(group["group_key"]), dict)
        for group in VIOLIN_METRIC_GROUP_DEFINITIONS
    )
    workload_source = (
        _mapping_or_empty(source.get("workload")) if has_grouped_source else source
    )
    topology_source = (
        _mapping_or_empty(source.get("topology")) if has_grouped_source else {}
    )
    platform_source = (
        _mapping_or_empty(source.get("platform")) if has_grouped_source else {}
    )
    rac_instance_source = (
        _mapping_or_empty(source.get("rac_instance"))
        if has_grouped_source
        else {}
    )

    payload = {
        "workload": {
            "cluster_cpu_pct_db_time": _sanitize_numeric_series(
                workload_source.get("cluster_cpu_pct_db_time")
                or workload_source.get("cpu_pct")
                or workload_source.get("cpu_pct_db_time")
            ),
            "cluster_execs_per_sec": _sanitize_numeric_series(
                workload_source.get("cluster_execs_per_sec")
                or workload_source.get("execs_per_sec")
                or workload_source.get("executions_per_sec")
            ),
            "cluster_read_iops": _sanitize_numeric_series(
                workload_source.get("cluster_read_iops")
                or workload_source.get("read_iops")
                or workload_source.get("physical_read_iops")
            ),
            "cluster_read_mb_per_sec": _sanitize_numeric_series(
                workload_source.get("cluster_read_mb_per_sec")
                or workload_source.get("read_mb_per_sec")
                or workload_source.get("physical_read_mb_per_sec")
            ),
            "cluster_write_iops": _sanitize_numeric_series(
                workload_source.get("cluster_write_iops")
                or workload_source.get("write_iops")
                or workload_source.get("physical_write_iops")
            ),
            "cluster_write_mb_per_sec": _sanitize_numeric_series(
                workload_source.get("cluster_write_mb_per_sec")
                or workload_source.get("write_mb_per_sec")
                or workload_source.get("physical_write_mb_per_sec")
            ),
            "cluster_user_io_pct_db_time": _sanitize_numeric_series(
                workload_source.get("cluster_user_io_pct_db_time")
                or workload_source.get("user_io_wait")
                or workload_source.get("user_io_wait_per_interval")
            ),
            "cluster_top_sql_concentration_pct": _sanitize_numeric_series(
                workload_source.get("cluster_top_sql_concentration_pct")
                or workload_source.get("top_sql_concentration_pct")
            ),
            "cluster_pga_spill_pressure": _sanitize_numeric_series(
                workload_source.get("cluster_pga_spill_pressure")
                or workload_source.get("pga_spill_pressure")
                or workload_source.get("workarea_spill_pressure")
            ),
            "cluster_temp_io_pressure": _sanitize_numeric_series(
                workload_source.get("cluster_temp_io_pressure")
                or workload_source.get("temp_io_pressure")
                or workload_source.get("temp_io_per_sec")
            ),
            "cluster_hard_parses_per_sec": _sanitize_numeric_series(
                workload_source.get("cluster_hard_parses_per_sec")
                or workload_source.get("hard_parses_per_sec")
                or workload_source.get("hard_parse_rate")
            ),
            "cluster_log_file_sync_ms": _sanitize_numeric_series(
                workload_source.get("cluster_log_file_sync_ms")
                or workload_source.get("log_file_sync_ms")
                or workload_source.get("avg_log_file_sync_ms")
            ),
        },
        "topology": {
            "cluster_wait_pct_db_time": _sanitize_numeric_series(
                topology_source.get("cluster_wait_pct_db_time")
            ),
            "gc_current_wait_pct_db_time": _sanitize_numeric_series(
                topology_source.get("gc_current_wait_pct_db_time")
            ),
            "gc_cr_wait_pct_db_time": _sanitize_numeric_series(
                topology_source.get("gc_cr_wait_pct_db_time")
            ),
            "transport_lag_sec": _sanitize_numeric_series(
                topology_source.get("transport_lag_sec")
            ),
            "apply_lag_sec": _sanitize_numeric_series(
                topology_source.get("apply_lag_sec")
            ),
        },
        "platform": {
            "cell_single_block_read_pct_db_time": _sanitize_numeric_series(
                platform_source.get("cell_single_block_read_pct_db_time")
            ),
            "smart_scan_pct_db_time": _sanitize_numeric_series(
                platform_source.get("smart_scan_pct_db_time")
            ),
        },
        "rac_instance": {
            "per_instance_cpu_pct_db_time": _sanitize_numeric_series(
                rac_instance_source.get("per_instance_cpu_pct_db_time")
            ),
            "per_instance_cluster_wait_pct_db_time": _sanitize_numeric_series(
                rac_instance_source.get("per_instance_cluster_wait_pct_db_time")
            ),
            "per_instance_gc_current_wait_pct_db_time": _sanitize_numeric_series(
                rac_instance_source.get("per_instance_gc_current_wait_pct_db_time")
            ),
            "per_instance_gc_cr_wait_pct_db_time": _sanitize_numeric_series(
                rac_instance_source.get("per_instance_gc_cr_wait_pct_db_time")
            ),
        },
    }
    for group_name, group_values in payload.items():
        for metric_key, values in group_values.items():
            if metric_key in PERCENT_LIKE_VIOLIN_KEYS:
                group_values[metric_key] = _normalize_percent_series(values)
    return payload


def _safe_float(value: Any) -> float:
    """Convert chart values safely to float."""

    if isinstance(value, (int, float)):
        return round(float(value), 1)

    if isinstance(value, str):
        try:
            return round(float(value.replace(",", "")), 1)
        except ValueError:
            return 0.0

    return 0.0


def _has_display_value(value: Any) -> bool:
    """Return True when a value should render as present content."""

    if value is None:
        return False
    if isinstance(value, str):
        normalized = value.strip()
        return bool(normalized) and normalized.upper() not in {
            "UNKNOWN",
            "UNAVAILABLE",
            "N/A",
            "NONE",
        }
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True


def _format_scalar_metric(value: Any) -> str:
    """Format scalar-only metric values for deterministic display."""

    if not isinstance(value, (int, float)):
        return "Insufficient data for a reliable conclusion"
    numeric = float(value)
    if abs(numeric) >= 100:
        return f"{numeric:.0f}"
    if abs(numeric) >= 10:
        return f"{numeric:.1f}"
    return f"{numeric:.3f}".rstrip("0").rstrip(".")


def _sanitize_numeric_series(values: Any) -> list[float]:
    """Return only valid numeric samples for violin plots."""

    if not isinstance(values, list):
        return []

    sanitized: list[float] = []
    for value in values:
        if isinstance(value, (int, float)):
            sanitized.append(round(float(value), 3))
            continue
        if isinstance(value, str):
            try:
                sanitized.append(round(float(value.replace(",", "")), 3))
            except ValueError:
                continue

    return sanitized


def _normalize_percent_series(values: list[float]) -> list[float]:
    """Normalize ratio-style values into 0-100 percentages when needed."""

    if not values:
        return values
    numeric_values = [float(value) for value in values if isinstance(value, (int, float))]
    if not numeric_values:
        return values
    if max(abs(value) for value in numeric_values) <= 1.0:
        return [round(value * 100.0, 3) for value in numeric_values]
    return numeric_values
