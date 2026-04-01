import os
from datetime import datetime, timezone
from pathlib import Path

from src.analysis.ai_narrative_generator import generate_ai_narrative
from src.analysis.issue_detector import detect_issues
from src.analysis.ai_provider import generate_ai_response
from src.analysis.derived_metric_extractor import (
    extract_derived_pressure_metrics,
)
from src.analysis.recommendation_engine import generate_recommendations
from src.analysis.violin_panel_builder import build_violin_panel_data
from src.parser.awr_parser import parse_awr_file
from src.reporting.html_dashboard import generate_html_dashboard


def _normalize_terminology(text: str) -> str:
    replacements = {
        "user i/o": "User I/O",
        "User i/o": "User I/O",
        "user I/O": "User I/O",
        "USER I/O": "User I/O",
        "db cpu": "DB CPU",
        "Db Cpu": "DB CPU",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def _build_executive_summary(issues: list[dict]) -> str:
    issue_by_type = {
        str(issue.get("issue_type") or ""): issue for issue in issues
    }

    summary_parts: list[str] = []

    cpu_issue = issue_by_type.get("cpu_pressure")
    if cpu_issue:
        pct_db_time = _format_pct(
            cpu_issue.get("evidence", {}).get("pct_db_time")
        )
        summary_parts.append(
            "The workload is primarily CPU-bound, with DB CPU consuming "
            f"{pct_db_time} of total database time."
        )
    else:
        summary_parts.append(
            "The workload does not show a single dominant CPU bottleneck "
            "from the current extracted metrics."
        )

    secondary_factors: list[str] = []
    io_issue = issue_by_type.get("io_pressure")
    if io_issue:
        io_event = _normalize_terminology(
            str(
                io_issue.get("evidence", {}).get("event_name")
                or "the dominant User I/O event"
            )
        )
        io_pct = _format_pct(io_issue.get("evidence", {}).get("pct_db_time"))
        secondary_factors.append(
            f"User I/O remains material, led by '{io_event}' at {io_pct}"
        )

    commit_issue = issue_by_type.get("commit_pressure")
    if commit_issue:
        commit_pct = _format_pct(
            commit_issue.get("evidence", {}).get("pct_db_time")
        )
        secondary_factors.append(
            f"commit latency is also contributing at {commit_pct}"
        )

    concurrency_issue = issue_by_type.get("concurrency_pressure")
    if concurrency_issue and str(concurrency_issue.get("severity") or "") in {
        "medium",
        "high",
    }:
        concurrency_pct = _format_pct(
            concurrency_issue.get("evidence", {}).get("combined_pct_db_time")
        )
        secondary_factors.append(
            f"concurrency pressure is present at {concurrency_pct}"
        )

    if secondary_factors:
        summary_parts.append(_join_factors(secondary_factors) + ".")

    sql_issue = issue_by_type.get("sql_concentration")
    if sql_issue:
        sql_evidence = sql_issue.get("evidence", {})
        modules = sql_evidence.get("modules") or []
        combined_pct_total = _format_pct(
            sql_evidence.get("combined_pct_total")
        )
        if len(modules) == 1:
            summary_parts.append(
                "SQL activity is concentrated in module "
                f"'{modules[0]}', where the top statements account for "
                f"{combined_pct_total} of elapsed SQL time."
            )
        else:
            summary_parts.append(
                "SQL activity is concentrated, with the top statements "
                f"accounting for {combined_pct_total} of elapsed SQL time."
            )

    summary_parts.append(
        "The correct direction is to tune SQL, access paths, and "
        "transaction behavior before considering additional capacity."
    )

    return " ".join(summary_parts)


def _join_factors(factors: list[str]) -> str:
    if not factors:
        return ""

    if len(factors) == 1:
        return factors[0].capitalize()

    if len(factors) == 2:
        return f"{factors[0].capitalize()}, and {factors[1]}"

    return f"{factors[0].capitalize()}, {factors[1]}, and {factors[2]}"


def _format_pct(value: object) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.1f}%"

    if isinstance(value, str):
        try:
            return f"{float(value.replace(',', '')):.1f}%"
        except ValueError:
            return "0.0%"

    return "0.0%"


def normalize_terms(text: str) -> str:
    replacements = {
        "user i/o": "User I/O",
        "User i/o": "User I/O",
        "user I/O": "User I/O",
        "USER I/O": "User I/O",
        "db cpu": "DB CPU",
        "Db Cpu": "DB CPU",
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text


def _build_agentic_decision(issues: list[dict]) -> dict:
    issue_by_type = {
        str(issue.get("issue_type") or ""): issue for issue in issues
    }

    execution_plan = [
        "Tune the highest CPU-consuming SQL and execution paths first.",
        (
            "Prioritize the top elapsed-time OrderService SQL statements "
            "immediately."
        ),
        (
            "Reduce physical reads by correcting SQL and access paths "
            "behind the dominant User I/O waits."
        ),
        (
            "Tighten commit frequency and commit-processing behavior in the "
            "application flow."
        ),
        (
            "Address concurrency after the primary CPU, SQL, I/O, and "
            "commit fixes are underway."
        ),
    ]

    if "cpu_pressure" in issue_by_type:
        primary_decision = (
            "Start with CPU-heavy SQL in OrderService. Tune the top "
            "CPU-consuming and top elapsed-time SQL paths first."
        )
    else:
        primary_decision = (
            "Start with the most material SQL and execution-path "
            "bottlenecks first."
        )

    return {
        "primary_decision": primary_decision,
        "execution_plan": execution_plan,
        "defer_do_not_do": [
            "Do not scale now.",
            "Do not treat storage as the first remedy.",
            (
                "Do not prioritize concurrency ahead of CPU, SQL "
                "concentration, User I/O, or commit latency."
            ),
        ],
        "scaling_decision": "DO NOT SCALE",
        "confidence_level": "High",
    }


def _build_oci_guidance(issues: list[dict]) -> dict:
    issue_by_type = {
        str(issue.get("issue_type") or ""): issue for issue in issues
    }

    current_state = (
        "The workload is CPU-bound and driven by a small number of "
        "high-impact SQL paths in OrderService. User I/O and commit latency "
        "are secondary contributors. The current state supports tuning "
        "first, not immediate scaling."
    )
    if "cpu_pressure" not in issue_by_type:
        current_state = (
            "The workload shows concentrated SQL and secondary performance "
            "contributors, but the current state still supports tuning "
            "before scaling."
        )

    return {
        "current_state_assessment": current_state,
        "scaling_trigger_conditions": (
            "Scaling becomes appropriate only after the CPU-heavy SQL paths, "
            "concentrated OrderService statements, physical read demand, and "
            "commit behavior have been tuned and the same dominant "
            "constraints still remain."
        ),
        "oci_architecture_guidance": (
            "Keep the architecture aligned to a compute-first tuning path. "
            "Use an OCI database deployment pattern that can scale CPU "
            "cleanly if residual pressure remains after SQL and transaction "
            "tuning. Treat storage and broader architectural changes as "
            "secondary unless the post-tuning workload still shows "
            "persistent I/O pressure."
        ),
        "resource_direction": (
            "Increase CPU capacity before expanding for other dimensions if "
            "tuning does not remove the dominant pressure. Prioritize "
            "compute scaling ahead of storage scaling. Address storage "
            "latency directionally only after SQL and access-path "
            "corrections confirm that physical read demand remains material."
        ),
        "risk_considerations": (
            "Scaling too early will mask the real problem and carry "
            "inefficient SQL and transaction behavior into a larger "
            "footprint. Skipping tuning will preserve the current CPU, SQL "
            "concentration, physical read, and commit inefficiencies. "
            "Scaling the wrong resource, especially storage before compute "
            "and SQL correction, will add cost without resolving the "
            "primary bottleneck."
        ),
    }


if __name__ == "__main__":
    provider = os.getenv("AI_PROVIDER", "openai")
    input_dir = Path("data/input")
    awr_files = sorted(input_dir.glob("*.out"))
    if not awr_files:
        raise FileNotFoundError("No AWR input files found in data/input")

    snapshot_results = [parse_awr_file(file_path) for file_path in awr_files]
    result = snapshot_results[-1]

    issues = detect_issues(result)
    recommendations = generate_recommendations(issues)
    ai_narrative = generate_ai_narrative(result, issues, recommendations)
    ai_response = generate_ai_response(
        provider=provider,
        system_role=ai_narrative["system_role"],
        prompt=ai_narrative["prompt"],
        expected_sections=ai_narrative["expected_sections"],
    )
    executive_summary = _build_executive_summary(issues)
    executive_summary = normalize_terms(executive_summary)
    agentic_decision = _build_agentic_decision(issues)
    oci_guidance = _build_oci_guidance(issues)
    derived_pressure_metrics = extract_derived_pressure_metrics(result)
    report_data = {
        "title": "OCI AWR Sizing Advisor Dashboard",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": executive_summary,
        "issues": issues,
        "recommendations": recommendations,
        "top_sql": result.top_sql,
        "violin_panel": build_violin_panel_data(snapshot_results),
        "derived_pressure_metrics": derived_pressure_metrics,
        "derived_scalar_metrics": {
            "pga_spill_pressure": (
                derived_pressure_metrics["pga_spill_pressure"]
            ),
            "temp_io_pressure": derived_pressure_metrics["temp_io_pressure"],
            "hard_parses_per_sec": (
                derived_pressure_metrics["hard_parses_per_sec"]
            ),
        },
        "agentic_decision": agentic_decision,
        "oci_guidance": oci_guidance,
        "ai_generated_narrative": ai_response["content"],
        "ai_provider": ai_response["provider"],
        "ai_model": ai_response["model"],
    }
    dashboard_file = generate_html_dashboard(report_data)

    print("EXECUTIVE SUMMARY")
    print("-" * 80)
    print(executive_summary)

    print("\nDetected Issues:")
    if not issues:
        print("  None")
    else:
        for issue in issues:
            print(f"\n- issue_type: {issue['issue_type']}")
            print(f"  severity: {issue['severity']}")
            print(f"  summary: {issue['summary']}")
            print(f"  evidence: {issue['evidence']}")

    print("\nRecommendations:\n")

    for rec in recommendations:
        print(f"- {rec.issue_type} ({rec.severity})")
        print(f"  Recommendation: {rec.recommendation}")
        print(f"  Rationale: {rec.rationale}")
        print(f"  Next Step: {rec.next_step}")
        print("  Actions:")
        for action in rec.actions:
            print(f"    - {action}")
        print()

    print("Derived Metric Availability:\n")
    for line in derived_pressure_metrics["debug_summary"]:
        print(f"  {line}")
    print("\nDerived Metric Values:")
    print(
        "  pga_spill_pressure: "
        f"{derived_pressure_metrics['pga_spill_pressure']}"
    )
    print(
        "  temp_io_pressure: "
        f"{derived_pressure_metrics['temp_io_pressure']}"
    )
    print(
        "  hard_parses_per_sec: "
        f"{derived_pressure_metrics['hard_parses_per_sec']}"
    )
    print(f"  availability: {derived_pressure_metrics['availability']}")

    print("AI Narrative Layer:\n")
    print("System Role:")
    print(f"  {ai_narrative['system_role']}\n")

    print("Expected Sections:")
    for section in ai_narrative["expected_sections"]:
        print(f"  - {section}")

    print("\nPrompt:")
    print(ai_narrative["prompt"])

    print("\nAI Generated Narrative:\n")
    print("Provider:")
    print(f"  {ai_response['provider']}\n")
    print("Model:")
    print(f"  {ai_response['model']}\n")
    print("Content:")
    print(ai_response["content"])
    print("\nHTML Dashboard:")
    print(f"  {dashboard_file}")
