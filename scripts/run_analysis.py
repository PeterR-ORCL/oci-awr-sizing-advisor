import os

from src.analysis.ai_narrative_generator import generate_ai_narrative
from src.analysis.issue_detector import detect_issues
from src.analysis.ai_provider import generate_ai_response
from src.analysis.recommendation_engine import generate_recommendations
from src.parser.awr_parser import parse_awr_file

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
        str(issue.get("issue_type") or ""): issue
        for issue in issues
    }

    summary_parts: list[str] = []

    cpu_issue = issue_by_type.get("cpu_pressure")
    if cpu_issue:
        pct_db_time = _format_pct(cpu_issue.get("evidence", {}).get("pct_db_time"))
        summary_parts.append(
            f"The workload is primarily CPU-bound, with DB CPU consuming {pct_db_time} of total database time."
        )
    else:
        summary_parts.append(
            "The workload does not show a single dominant CPU bottleneck from the current extracted metrics."
        )

    secondary_factors: list[str] = []
    io_issue = issue_by_type.get("io_pressure")
    if io_issue:
        io_event = _normalize_terminology(
            str(io_issue.get("evidence", {}).get("event_name") or "the dominant User I/O event")
        )
        io_pct = _format_pct(io_issue.get("evidence", {}).get("pct_db_time"))
        secondary_factors.append(f"User I/O remains material, led by '{io_event}' at {io_pct}")

    commit_issue = issue_by_type.get("commit_pressure")
    if commit_issue:
        commit_pct = _format_pct(commit_issue.get("evidence", {}).get("pct_db_time"))
        secondary_factors.append(f"commit latency is also contributing at {commit_pct}")

    concurrency_issue = issue_by_type.get("concurrency_pressure")
    if concurrency_issue and str(concurrency_issue.get("severity") or "") in {"medium", "high"}:
        concurrency_pct = _format_pct(
            concurrency_issue.get("evidence", {}).get("combined_pct_db_time")
        )
        secondary_factors.append(f"concurrency pressure is present at {concurrency_pct}")

    if secondary_factors:
        summary_parts.append(_join_factors(secondary_factors) + ".")

    sql_issue = issue_by_type.get("sql_concentration")
    if sql_issue:
        sql_evidence = sql_issue.get("evidence", {})
        modules = sql_evidence.get("modules") or []
        combined_pct_total = _format_pct(sql_evidence.get("combined_pct_total"))
        if len(modules) == 1:
            summary_parts.append(
                f"SQL activity is concentrated in module '{modules[0]}', where the top statements account for {combined_pct_total} of elapsed SQL time."
            )
        else:
            summary_parts.append(
                f"SQL activity is concentrated, with the top statements accounting for {combined_pct_total} of elapsed SQL time."
            )

    summary_parts.append(
        "The correct direction is to tune SQL, access paths, and transaction behavior before considering additional capacity."
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


if __name__ == "__main__":
    provider = os.getenv("AI_PROVIDER", "openai")
    result = parse_awr_file("data/input/sample_awr_01.out")

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

    print("EXECUTIVE SUMMARY")
    print("--------------------------------------------------------------------------------")
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
