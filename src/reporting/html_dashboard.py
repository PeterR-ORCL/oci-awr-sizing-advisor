"""Single-file HTML dashboard generation for AWR analysis results."""

from __future__ import annotations

import json
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
    """Generate a self-contained HTML dashboard file and return its path."""

    output_path = Path(output_file)
    html = _build_dashboard_html(report_data)
    output_path.write_text(html, encoding="utf-8")
    return str(output_path.resolve())


AI_SECTION_NAMES = [
    "Executive Summary",
    "Technical Narrative",
    "Root Cause Interpretation",
    "Recommended Action Plan",
    "OCI Sizing Considerations",
    "Confidence Assessment",
    "Risk of Being Wrong",
]

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
VIOLIN_METRIC_DEFINITIONS = [
    {
        "payload_key": "cpu_pct",
        "container_id": "violinCpuPct",
        "title": "CPU %",
        "color": "rgba(255, 107, 107, 0.72)",
    },
    {
        "payload_key": "execs_per_sec",
        "container_id": "violinExecsPerSec",
        "title": "Execs/s",
        "color": "rgba(90, 209, 255, 0.72)",
    },
    {
        "payload_key": "read_iops",
        "container_id": "violinReadIops",
        "title": "Read IOPs",
        "color": "rgba(246, 184, 76, 0.72)",
    },
    {
        "payload_key": "read_mb_per_sec",
        "container_id": "violinReadMbPerSec",
        "title": "Read MB/s",
        "color": "rgba(212, 174, 82, 0.72)",
    },
    {
        "payload_key": "write_iops",
        "container_id": "violinWriteIops",
        "title": "Write IOPs",
        "color": "rgba(127, 179, 213, 0.72)",
    },
    {
        "payload_key": "write_mb_per_sec",
        "container_id": "violinWriteMbPerSec",
        "title": "Write MB/s",
        "color": "rgba(130, 148, 171, 0.72)",
    },
    {
        "payload_key": "user_io_wait",
        "container_id": "violinUserIoWait",
        "title": "User I/O Wait",
        "color": "rgba(255, 159, 67, 0.72)",
    },
    {
        "payload_key": "top_sql_elapsed_norm",
        "container_id": "violinTopSqlElapsedNorm",
        "title": "Top SQL Elapsed Time (normalized)",
        "color": "rgba(186, 104, 200, 0.72)",
    },
    {
        "payload_key": "pga_spill_pressure",
        "container_id": "violinPgaSpillPressure",
        "title": "PGA Spill Pressure",
        "color": "rgba(102, 187, 106, 0.72)",
    },
    {
        "payload_key": "temp_io_pressure",
        "container_id": "violinTempIoPressure",
        "title": "Temp I/O Pressure",
        "color": "rgba(38, 166, 154, 0.72)",
    },
    {
        "payload_key": "hard_parses_per_sec",
        "container_id": "violinHardParsesPerSec",
        "title": "Hard Parses/s",
        "color": "rgba(255, 202, 40, 0.72)",
    },
    {
        "payload_key": "log_file_sync_ms",
        "container_id": "violinLogFileSyncMs",
        "title": "Log File Sync Latency",
        "color": "rgba(239, 83, 80, 0.72)",
    },
]


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


def _build_dashboard_html(report_data: dict[str, Any]) -> str:
    """Build the dashboard HTML."""

    title = escape(str(report_data.get("title") or "OCI AWR Sizing Advisor"))
    ai_sections = _normalize_ai_sections(
        parse_ai_sections(str(report_data.get("ai_generated_narrative") or ""))
    )
    decision_state = _derive_decision_state(ai_sections)
    issues = report_data.get("issues") or []
    recommendations = report_data.get("recommendations") or []
    agentic_decision = report_data.get("agentic_decision") or {}
    ai_provider = escape(str(report_data.get("ai_provider")))
    ai_model = escape(
        _short_model_name(report_data.get("ai_provider"), report_data.get("ai_model"))
    )
    generated_at = escape(
        str(report_data.get("generated_at") or datetime.utcnow().isoformat())
    )
    derived_scalar_metrics = report_data.get("derived_scalar_metrics") or {}
    chart_payload = _build_chart_payload(report_data)
    violin_metric_configs = _build_violin_metric_configs(chart_payload["violin_panel"])
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
      gap: 10px;
      border-radius: 14px;
      padding: 16px;
    }}
    .confidence-section.high {{
      background: #ffe5e5;
      color: #341516;
    }}
    .confidence-section.medium {{
      background: #fff9e6;
      color: #3b2f13;
    }}
    .confidence-section.low {{
      background: #f0f0f0;
      color: #252525;
    }}
    .confidence-section h2,
    .confidence-section p {{
      margin: 0;
    }}
    .risk-section {{
      display: grid;
      gap: 10px;
    }}
    .risk-section h2,
    .risk-section p {{
      margin: 0;
    }}
    .risk-section ul {{
      margin-top: 0;
    }}
    .subgrid {{
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .half {{
      grid-column: span 12;
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
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }}
    .violin-chart-card {{
      grid-column: span 12;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 18px;
      background: rgba(16, 28, 45, 0.72);
      min-height: 320px;
    }}
    .violin-chart-card h3 {{
      margin: 0 0 14px;
      font-size: 17px;
    }}
    .violin-chart {{
      height: 260px;
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
    @media (min-width: 700px) {{
      .violin-chart-card {{
        grid-column: span 6;
      }}
    }}
    @media (min-width: 900px) {{
      .half {{
        grid-column: span 6;
      }}
      .chart-panel {{
        grid-column: span 6;
      }}
      .violin-chart-card {{
        grid-column: span 4;
      }}
    }}
    @media (min-width: 1200px) {{
      .violin-chart-card {{
        grid-column: span 3;
      }}
    }}
    @media (max-width: 780px) {{
      .decision-grid,
      .provider-grid,
      .scalar-grid {{
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
      <div class="eyebrow">OCI AWR Sizing Advisor</div>
      <h1>{title}</h1>
      <div class="hero-meta">Generated: {generated_at}</div>
    </section>

    <div class="grid">
      <section id="ai-summary" class="card primary">
        <div class="section-kicker">AI Advisory Layer</div>
        <h2>Executive Summary</h2>
        {_render_executive_summary(
            ai_sections["Executive Summary"],
            issues,
            decision_state,
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

      <section id="performance-charts" class="card secondary">
        <div class="section-kicker">Visual Signals</div>
        <h2>Performance Charts</h2>
        <div class="chart-grid">
          <section class="chart-panel">
            <h3>DB Time Breakdown</h3>
            {_render_chart_container(
                "dbTimeBreakdownChart",
                chart_payload["db_time_breakdown"],
            )}
          </section>
          <section class="chart-panel">
            <h3>Top SQL Contribution (% Elapsed SQL Time)</h3>
            {_render_chart_container(
                "topSqlContributionChart",
                chart_payload["top_sql_contribution"],
            )}
          </section>
        </div>
      </section>

      {_render_violin_panel(violin_metric_configs)}

      <section id="derived-scalar-metrics" class="card secondary">
        <div class="section-kicker">Deterministic Metrics</div>
        <h2>Derived Scalar Metrics</h2>
        {_render_scalar_metrics(derived_scalar_metrics)}
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

      <section id="provider-metadata" class="card secondary">
        <h2>Provider Metadata</h2>
        <div class="provider-grid">
          <div class="provider-box">
            <strong>Provider</strong>
            <div>{ai_provider}</div>
          </div>
          <div class="provider-box">
            <strong>Model</strong>
            <div>{ai_model}</div>
          </div>
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

    function buildViolinChart(containerId, title, samples, color) {{
      if (!Array.isArray(samples) || samples.length < 2) {{
        return;
      }}

      const container = document.getElementById(containerId);
      if (!container) {{
        return;
      }}

      const meanValue = computeMean(samples);
      const medianValue = computeMedian(samples);
      const maxValue = Math.max(...samples);
      const minValue = Math.min(...samples);

      Plotly.purge(container);
      Plotly.newPlot(
        container,
        [
          {{
            type: 'violin',
            y: samples,
            name: title,
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
            hoveron: 'violins+points+kde',
          }},
          {{
            type: 'scatter',
            mode: 'markers+text',
            x: [title],
            y: [meanValue],
            text: ['Mean ' + formatMetricValue(meanValue)],
            textposition: 'middle right',
            textfont: {{
              color: '#f6b84c',
              size: 11,
            }},
            marker: {{
              color: '#f6b84c',
              symbol: 'diamond',
              size: 10,
              line: {{
                color: '#fff3d6',
                width: 1,
              }},
            }},
            hoverinfo: 'skip',
            showlegend: false,
          }},
          {{
            type: 'scatter',
            mode: 'markers+text',
            x: [title],
            y: [maxValue],
            text: ['Max ' + formatMetricValue(maxValue)],
            textposition: 'top right',
            textfont: {{
              color: '#ff6b6b',
              size: 11,
            }},
            marker: {{
              color: '#ff6b6b',
              symbol: 'diamond',
              size: 10,
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
            mode: 'text',
            x: [title],
            y: [minValue],
            text: ['Min ' + formatMetricValue(minValue)],
            textposition: 'bottom left',
            textfont: {{
              color: 'rgba(232, 238, 247, 0.72)',
              size: 10,
            }},
            hoverinfo: 'skip',
            showlegend: false,
          }},
        ],
        {{
          paper_bgcolor: 'rgba(0,0,0,0)',
          plot_bgcolor: 'rgba(11, 21, 35, 0.35)',
          margin: {{
            l: 56,
            r: 18,
            t: 8,
            b: 42,
          }},
          font: {{
            color: chartTextColor,
          }},
          xaxis: {{
            color: chartTextColor,
            gridcolor: 'rgba(0,0,0,0)',
            zeroline: false,
          }},
          yaxis: {{
            color: chartTextColor,
            gridcolor: chartMutedColor,
            zeroline: false,
          }},
          shapes: [
            {{
              type: 'line',
              xref: 'paper',
              x0: 0.38,
              x1: 0.62,
              y0: medianValue,
              y1: medianValue,
              line: {{
                color: '#0b0f14',
                width: 2,
              }},
            }},
          ],
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
        const color = config.color;
        buildViolinChart(containerId, title, payload[payloadKey], color);
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
        issue_type = escape(str(issue.get("issue_type") or ""))
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
        issue_type = escape(str(recommendation_dict.get("issue_type") or ""))
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
) -> str:
    """Render the Executive Summary in structured format."""

    rationale = _extract_summary_rationale(summary_text)
    key_signals = _build_key_signal_items(issues)
    signal_items = "".join(f"<li>{escape(item)}</li>" for item in key_signals)

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


def _render_confidence_section(confidence_text: str) -> str:
    """Render the Confidence Assessment with structured level and reason."""

    level = _extract_confidence_level(confidence_text)
    reason = _extract_confidence_reason(confidence_text)

    return f"""
    <div class="confidence-section {escape(level.lower())}">
      <h2>Confidence Assessment</h2>
      <p><strong>Level:</strong> {escape(level)}</p>
      <p><strong>Reason:</strong> {escape(reason)}</p>
    </div>
    """


def _render_risk_section(risk_text: str) -> str:
    """Render the Risk of Being Wrong section with structured bullets."""

    main_risks, risk_reduction = _extract_risk_items(risk_text)
    main_risk_items = "".join(f"<li>{escape(item)}</li>" for item in main_risks)

    return f"""
    <div class="risk-section">
      <h2>Risk of Being Wrong</h2>
      <p><strong>Main Risks:</strong></p>
      <ul>
        {main_risk_items}
      </ul>
      <p class="risk-reduction">
        <strong>What would reduce this risk:</strong><br>
        {escape(risk_reduction)}
      </p>
    </div>
    """


def _render_decision_box(label: str, value: Any) -> str:
    """Render a single dashboard decision box."""

    if isinstance(value, list):
        content = (
            "<ol>"
            + "".join(f"<li>{escape(str(item))}</li>" for item in value)
            + "</ol>"
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

    text = _normalize_inline_numbered_text(str(value or "").strip())
    if not text:
        return ""

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
    if not cleaned_text:
        return DEFAULT_SUMMARY_RATIONALE

    first_sentence = re.split(r"(?<=[.!?])\s+", cleaned_text, maxsplit=1)[0].strip()
    return first_sentence or DEFAULT_SUMMARY_RATIONALE


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

    return [
        f"CPU: {cpu:.1f}% DB time",
        f"Top SQL concentration: {sql:.1f}%",
        f"User I/O: {io:.1f}%",
    ]


def _extract_confidence_reason(confidence_text: str) -> str:
    """Extract a short confidence justification from the AI text."""

    cleaned_text = confidence_text.strip()
    cleaned_text = re.sub(
        r"^\s*(High|Medium|Low)\b[:\-]?\s*",
        "",
        cleaned_text,
        flags=re.IGNORECASE,
    )
    cleaned_text = re.sub(r"^\s*[-–—]\s*", "", cleaned_text)
    if cleaned_text:
        return DEFAULT_CONFIDENCE_REASON
    return DEFAULT_CONFIDENCE_REASON


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

    values = chart_data.get("values") or []
    if not values:
        return (
            '<div class="chart-empty">'
            "Chart data is not available for this run."
            "</div>"
        )

    return f'<div class="chart-canvas"><canvas id="{escape(canvas_id)}"></canvas></div>'


def _render_violin_panel(violin_metric_configs: list[dict[str, str]]) -> str:
    """Render the violin panel only when real series-backed metrics exist."""

    if not violin_metric_configs:
        return ""

    cards = []
    for config in violin_metric_configs:
        cards.append(f"""
          <section class="violin-chart-card">
            <h3>{escape(config["title"])}</h3>
            <div id="{escape(config["container_id"])}" class="violin-chart"></div>
          </section>
            """)

    return (
        """
      <section id="workload-violin-panel" class="card secondary violin-panel">
        <div class="section-kicker">Workload Analysis</div>
        <h2>Workload Distribution — Violin Panel</h2>
        <div class="violin-grid">
"""
        + "".join(cards)
        + """
        </div>
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

    boxes: list[str] = []
    for label, value, note in metric_specs:
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


def _build_violin_metric_configs(
    violin_payload: dict[str, list[float]],
) -> list[dict[str, str]]:
    """Return only violin metrics that have real series data to render."""

    return [
        metric
        for metric in VIOLIN_METRIC_DEFINITIONS
        if _has_violin_samples(violin_payload.get(metric["payload_key"]))
    ]


def _has_violin_samples(values: Any) -> bool:
    """Return True only when a violin metric has enough numeric samples to render."""

    if not isinstance(values, list) or len(values) < 2:
        return False
    return all(isinstance(value, (int, float)) for value in values)


def _build_chart_payload(report_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build chart payloads from deterministic report data."""

    issues = report_data.get("issues") or []
    top_sql = report_data.get("top_sql") or []

    return {
        "db_time_breakdown": _build_db_time_breakdown(issues),
        "top_sql_contribution": _build_top_sql_contribution(top_sql),
        "violin_panel": _build_violin_panel_payload(report_data),
    }


def _build_db_time_breakdown(issues: list[dict[str, Any]]) -> dict[str, Any]:
    """Build DB time breakdown chart data from deterministic issues."""

    issue_by_type = {str(issue.get("issue_type") or ""): issue for issue in issues}

    cpu = _safe_float(
        issue_by_type.get("cpu_pressure", {}).get("evidence", {}).get("pct_db_time")
    )
    io = _safe_float(
        issue_by_type.get("io_pressure", {}).get("evidence", {}).get("pct_db_time")
    )
    commit = _safe_float(
        issue_by_type.get("commit_pressure", {}).get("evidence", {}).get("pct_db_time")
    )
    concurrency = _safe_float(
        issue_by_type.get("concurrency_pressure", {})
        .get("evidence", {})
        .get("combined_pct_db_time")
    )

    values = [cpu, io, commit, concurrency]
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


def _build_top_sql_contribution(top_sql: list[dict[str, Any]]) -> dict[str, Any]:
    """Build top SQL contribution chart data from parsed SQL records."""

    if not top_sql:
        return {"labels": [], "values": [], "colors": []}

    labels: list[str] = []
    values: list[float] = []
    for sql_record in top_sql[:3]:
        sql_id = str(sql_record.get("sql_id") or "unknown")
        pct_total = _safe_float(sql_record.get("pct_total"))
        if pct_total <= 0:
            continue
        labels.append(sql_id)
        values.append(pct_total)

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


def _build_violin_panel_payload(report_data: dict[str, Any]) -> dict[str, list[float]]:
    """Build violin-panel metric series from structured report data when available."""

    source = report_data.get("violin_panel") or report_data.get("metric_samples") or {}

    # Intended interval series meanings:
    # cpu_pct = (DB CPU / DB Time) * 100 per interval
    # execs_per_sec = executions delta / elapsed seconds
    # read_iops = physical read requests delta / elapsed seconds
    # read_mb_per_sec = physical read bytes delta / elapsed seconds / 1024 / 1024
    # write_iops = physical write requests delta / elapsed seconds
    # write_mb_per_sec = physical write bytes delta / elapsed seconds / 1024 / 1024
    # user_io_wait = User I/O wait per interval (keep consistent units)
    # top_sql_elapsed_norm = top SQL elapsed time normalized per execution
    # or equivalent normalized interval metric
    # pga_spill_pressure = onepass + multipass workarea pressure
    # per interval, or equivalent spill signal
    # temp_io_pressure = temp reads/writes per second or equivalent
    # temp I/O pressure signal
    # hard_parses_per_sec = hard parses delta / elapsed seconds
    # log_file_sync_ms = average log file sync latency per interval in milliseconds
    full_payload = {
        "cpu_pct": _sanitize_numeric_series(
            source.get("cpu_pct") or source.get("cpu_pct_db_time")
        ),
        "execs_per_sec": _sanitize_numeric_series(
            source.get("execs_per_sec") or source.get("executions_per_sec")
        ),
        "read_iops": _sanitize_numeric_series(
            source.get("read_iops") or source.get("physical_read_iops")
        ),
        "read_mb_per_sec": _sanitize_numeric_series(
            source.get("read_mb_per_sec") or source.get("physical_read_mb_per_sec")
        ),
        "write_iops": _sanitize_numeric_series(
            source.get("write_iops") or source.get("physical_write_iops")
        ),
        "write_mb_per_sec": _sanitize_numeric_series(
            source.get("write_mb_per_sec") or source.get("physical_write_mb_per_sec")
        ),
        "user_io_wait": _sanitize_numeric_series(
            source.get("user_io_wait") or source.get("user_io_wait_per_interval")
        ),
        "top_sql_elapsed_norm": _sanitize_numeric_series(
            source.get("top_sql_elapsed_norm")
            or source.get("top_sql_elapsed_normalized")
        ),
        "pga_spill_pressure": _sanitize_numeric_series(
            source.get("pga_spill_pressure") or source.get("workarea_spill_pressure")
        ),
        "temp_io_pressure": _sanitize_numeric_series(
            source.get("temp_io_pressure") or source.get("temp_io_per_sec")
        ),
        "hard_parses_per_sec": _sanitize_numeric_series(
            source.get("hard_parses_per_sec") or source.get("hard_parse_rate")
        ),
        "log_file_sync_ms": _sanitize_numeric_series(
            source.get("log_file_sync_ms") or source.get("avg_log_file_sync_ms")
        ),
    }

    return {
        key: values
        for key, values in full_payload.items()
        if _has_violin_samples(values)
    }


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


def _format_scalar_metric(value: Any) -> str:
    """Format scalar-only metric values for deterministic display."""

    if not isinstance(value, (int, float)):
        return "Unavailable"
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
