"""Grounded AI narrative prompt preparation for AWR analysis outputs."""

from __future__ import annotations

import re
from typing import Any

from src.models.parse_result import ParseResult

ISSUE_ORDER = (
    "cpu_pressure",
    "sql_concentration",
    "io_pressure",
    "commit_pressure",
    "concurrency_pressure",
)


SYSTEM_ROLE = (
    "You are a senior Oracle performance architect. Use only the provided "
    "deterministic findings and evidence. Do not invent metrics, issues, "
    "recommendations, root causes, or sizing values. Do not contradict the "
    "provided evidence."
)

EXPECTED_SECTIONS = [
    "Executive Summary",
    "Technical Narrative",
    "Root Cause Interpretation",
    "Recommended Action Plan",
    "OCI Sizing Considerations",
    "Confidence Assessment",
    "Risk of Being Wrong",
]


def build_ai_prompt(
    parse_result: ParseResult,
    issues: list[dict[str, Any]],
    recommendations: list[Any],
) -> str:
    """Build a grounded provider-agnostic prompt from deterministic outputs."""

    sections: list[str] = [
        "Role and Constraints",
        SYSTEM_ROLE,
        _build_role_constraints(),
        "Response Objectives",
        _build_response_objectives(),
        "Required Output Sections",
        _format_required_output_sections(),
        "Deterministic Input Data",
        _format_deterministic_input_data(parse_result, issues, recommendations),
    ]

    return "\n\n".join(section for section in sections if section)


def generate_ai_narrative(
    parse_result: ParseResult,
    issues: list[dict[str, Any]],
    recommendations: list[Any],
) -> dict[str, Any]:
    """Return a deterministic AI narrative package without calling any API."""

    return {
        "system_role": SYSTEM_ROLE,
        "prompt": build_ai_prompt(parse_result, issues, recommendations),
        "expected_sections": EXPECTED_SECTIONS,
    }


def _build_role_constraints() -> str:
    """Return the grounded role and prohibition block."""

    return "\n".join(
        [
            "- Use only the provided deterministic findings, evidence, and recommendations.",
            "- Do not invent data.",
            "- Do not add unsupported root causes.",
            "- Do not recommend actions that contradict the deterministic recommendations.",
            "- Do not introduce technologies or architectural claims not present in the provided evidence.",
            "- Do not mention Oracle features, OCI services, or architectural components unless they are explicitly present in the deterministic inputs or required by the requested output section.",
            "- Do not use specific numeric sizing values unless those values are explicitly present in the deterministic inputs.",
            "- If evidence is limited, say so directly and remain within the provided facts.",
        ]
    )


def _build_response_objectives() -> str:
    """Return the response behavior instructions for the future model."""

    return "\n".join(
        [
            "- Be concise, professional, executive-friendly, and technically credible.",
            "- Sound like a senior Oracle performance architect, not a generic chatbot.",
            "- Keep the response concise enough for demo presentation while remaining useful to DBAs.",
            "- Prioritize the most material bottlenecks first.",
            "- Treat issues in descending order of impact and severity. Focus first on CPU and dominant SQL drivers, then secondary contributors such as User I/O and commit latency, and finally concurrency effects.",
            "- Preserve the prioritization implied by the deterministic recommendations and next steps.",
            "- Distinguish primary constraints from secondary contributing factors.",
            "- Explain why the deterministic recommendations matter to workload performance.",
            "- Reinforce tuning before scaling when supported by the evidence.",
            "- Include OCI sizing considerations only as directional guidance, not fixed sizing numbers.",
            "- In the Executive Summary, the first sentence must state the decision outcome using one of these exact phrases when appropriate: DO NOT SCALE, DEFER SCALING PENDING VALIDATION, INSUFFICIENT DATA TO RECOMMEND SCALING, SCALE NOW.",
            '- Format the first sentence like this: "DO NOT SCALE. <reason>" when that decision applies.',
            "- Keep the decision in the first 1–2 sentences only.",
            "- The Executive Summary must include the decision, 1–2 key metrics explaining why, and a clear next action.",
            "- Make decision strength consistent with confidence: High confidence supports decisive language such as DO NOT SCALE or SCALE NOW; Medium confidence supports DEFER SCALING PENDING VALIDATION; Low confidence supports INSUFFICIENT DATA TO RECOMMEND.",
            "- Keep the OCI Sizing Considerations section consistent with the confidence-adjusted decision.",
            "- Keep the Recommended Action Plan tone consistent with the confidence-adjusted decision.",
            "- Base Confidence Assessment only on deterministic evidence such as AWR metrics, SQL concentration, wait events, and observed signals. Do not use speculation.",
            "- Format Confidence Assessment as High, Medium, or Low followed by a short justification.",
            "- If the decision would otherwise be DO NOT SCALE but confidence is not High, use DEFER SCALING PENDING VALIDATION instead.",
            "- If confidence is Low, use INSUFFICIENT DATA TO RECOMMEND SCALING.",
            "- Also produce Confidence Assessment and Risk of Being Wrong sections grounded only in the deterministic evidence.",
        ]
    )


def _format_required_output_sections() -> str:
    """Return the explicit output contract for the future narrative model."""

    return "\n".join(
        [
            "Produce a response using exactly these section headings:",
            *(f"- {section}" for section in EXPECTED_SECTIONS),
            "",
            "Also produce these additional sections:",
            "Confidence Assessment:",
            "State how confident you are in the advisory conclusion based only on the deterministic evidence.",
            "Use clear levels such as High, Medium, or Low, and briefly justify the confidence.",
            "",
            "Risk of Being Wrong:",
            "State the main ways this recommendation could be wrong or incomplete if important evidence is missing.",
            "Be explicit about why the recommendation could be wrong, what assumptions were made, and what evidence is missing.",
            "End with a final sentence in this form: Additional data that would reduce this risk: ...",
            "",
            "Response formatting and content rules:",
            "- Avoid markdown tables.",
            "- Avoid excessive bullets.",
            "- Avoid unsupported root-cause claims.",
            "- Avoid specific numeric sizing values unless those values are explicitly present in the deterministic inputs.",
            "- Keep the response concise and suitable for both executives and DBAs.",
            "- Do not omit any required section; if evidence is limited, state that limitation explicitly.",
        ]
    )


def _format_deterministic_input_data(
    parse_result: ParseResult,
    issues: list[dict[str, Any]],
    recommendations: list[Any],
) -> str:
    """Return the compact deterministic data block for prompt grounding."""

    data_sections = [
        ("Run Metadata", _format_run_metadata(parse_result)),
        ("Issues", _format_issues(issues)),
        ("Recommendations", _format_recommendations(recommendations)),
        ("Key Metrics Summary", _format_key_metrics_summary(parse_result)),
        ("Top SQL Summary", _format_top_sql_summary(parse_result)),
    ]

    formatted_sections: list[str] = []
    for title, content in data_sections:
        if not content:
            continue
        formatted_sections.append(title)
        formatted_sections.append(content)

    return "\n\n".join(formatted_sections)


def _format_run_metadata(parse_result: ParseResult) -> str:
    """Format compact run metadata for prompt inclusion."""

    metadata = parse_result.run_metadata
    fields = [
        ("Source File", metadata.source_file_name),
        ("Database Name", metadata.database_name),
        ("DB ID", metadata.db_id),
        ("Instance Name", metadata.instance_name),
        ("Instance Number", metadata.instance_number),
        ("Host Name", metadata.host_name),
        ("Platform", metadata.platform),
        ("Begin Snapshot Time", metadata.begin_snapshot_time),
        ("End Snapshot Time", metadata.end_snapshot_time),
        ("Parse Timestamp", metadata.parse_timestamp),
    ]
    return "\n".join(f"- {label}: {_display_value(value)}" for label, value in fields)


def _format_issues(issues: list[dict[str, Any]]) -> str:
    """Format deterministic issues in compact narrative form."""

    if not issues:
        return "- None"

    ordered_issues = sorted(
        issues,
        key=lambda issue: _issue_sort_key(issue.get("issue_type")),
    )
    lines: list[str] = []
    for issue in ordered_issues:
        lines.append(
            "- "
            f"{_display_value(issue.get('issue_type'))} "
            f"({_display_value(issue.get('severity'))}): "
            f"{_display_value(issue.get('summary'))}"
        )

    return "\n".join(lines)


def _format_recommendations(recommendations: list[Any]) -> str:
    """Format deterministic recommendations in compact form."""

    if not recommendations:
        return "- None"

    ordered_recommendations = sorted(
        recommendations,
        key=lambda recommendation: _issue_sort_key(
            _recommendation_to_dict(recommendation).get("issue_type")
        ),
    )
    lines: list[str] = []
    for recommendation in ordered_recommendations:
        recommendation_dict = _recommendation_to_dict(recommendation)
        lines.append(
            "- "
            f"{_display_value(recommendation_dict.get('issue_type'))} "
            f"({_display_value(recommendation_dict.get('severity'))}): "
            f"{_display_value(recommendation_dict.get('recommendation'))}"
        )
        next_step = recommendation_dict.get("next_step")
        if next_step is not None:
            lines.append(f"  next_step: {_display_value(next_step)}")
        lines.append(
            f"  rationale: {_display_value(recommendation_dict.get('rationale'))}"
        )

    return "\n".join(lines)


def _format_key_metrics_summary(parse_result: ParseResult) -> str:
    """Format compact CPU and wait signal summaries for grounding."""

    summary_lines: list[str] = []

    cpu_priority_names = ("DB Time(s)", "DB CPU(s)")
    cpu_signals = [
        metric
        for metric in parse_result.cpu_metrics
        if metric.get("metric_group") == "load_profile"
        and metric.get("metric_name") in cpu_priority_names
    ]
    for metric in cpu_signals[:2]:
        summary_lines.append(
            "- CPU signal: "
            f"{_display_value(metric.get('metric_name'))}, "
            f"per_second={_display_value(metric.get('per_second'))}, "
            f"per_transaction={_display_value(metric.get('per_transaction'))}"
        )

    for wait_event in parse_result.wait_events[:3]:
        summary_lines.append(
            "- Wait signal: "
            f"{_display_value(wait_event.get('event_name'))}, "
            f"pct_db_time={_display_value(wait_event.get('pct_db_time'))}, "
            f"wait_class={_display_value(wait_event.get('wait_class'))}"
        )

    if not summary_lines:
        return "- None"

    return "\n".join(summary_lines)


def _format_top_sql_summary(parse_result: ParseResult) -> str:
    """Format compact top SQL signals for grounding."""

    if not parse_result.top_sql:
        return "- None"

    lines: list[str] = []
    for sql_record in parse_result.top_sql[:3]:
        lines.append(
            "- SQL signal: "
            f"sql_id={_display_value(sql_record.get('sql_id'))}, "
            f"pct_total={_display_value(sql_record.get('pct_total'))}, "
            f"module={_display_value(sql_record.get('module'))}, "
            f"sql_text_snippet={_truncate_text(sql_record.get('sql_text_snippet'))}"
        )

    return "\n".join(lines)


def _recommendation_to_dict(recommendation: Any) -> dict[str, Any]:
    """Convert a recommendation object into a plain dictionary."""

    if hasattr(recommendation, "model_dump"):
        return recommendation.model_dump()

    if isinstance(recommendation, dict):
        return recommendation

    return recommendation.__dict__


def _issue_sort_key(issue_type: Any) -> int:
    """Return a stable materiality-driven sort order for issues."""

    normalized_issue_type = str(issue_type or "")
    if normalized_issue_type in ISSUE_ORDER:
        return ISSUE_ORDER.index(normalized_issue_type)

    return len(ISSUE_ORDER)


def _truncate_text(value: Any, max_length: int = 140) -> str:
    """Return a compact SQL text snippet for prompt quality."""

    text = _display_value(value)
    if len(text) <= max_length:
        return text

    return text[: max_length - 3].rstrip() + "..."


def _display_value(value: Any) -> str:
    """Render a prompt-safe display value."""

    if value is None:
        return "None"

    return _normalize_terminology(str(value))


def _normalize_terminology(text: str) -> str:
    """Normalize terminology for prompt quality and consistency."""

    normalized_text = text
    normalized_text = normalized_text.replace("user i/o", "User I/O")
    normalized_text = normalized_text.replace("USER I/O", "User I/O")
    normalized_text = normalized_text.replace("User i/o", "User I/O")
    normalized_text = re.sub(
        r"\bdb cpu\b", "DB CPU", normalized_text, flags=re.IGNORECASE
    )
    normalized_text = re.sub(r"\boci\b", "OCI", normalized_text, flags=re.IGNORECASE)
    normalized_text = re.sub(r"\bsql\b", "SQL", normalized_text, flags=re.IGNORECASE)
    return normalized_text
