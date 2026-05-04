import os
import json
import re
import html
import hashlib
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

from src.analysis.ai_narrative_generator import generate_ai_narrative
from src.analysis.decision_engine import build_decision
from src.analysis.ai_provider import generate_ai_response
from src.analysis.derived_metric_extractor import (
    extract_derived_pressure_metrics,
)
from src.analysis.scoring_adapter import build_decision_input_from_score_result
from src.analysis.engineered_metric_catalog import (
    DOMAIN_DISPLAY_ORDER,
    get_implemented_metric_definitions,
)
from src.analysis.frontend_contract import build_phase5_screen_models
from src.analysis.issue_detector import detect_issues
from src.analysis.output_layer import build_analysis_output
from src.analysis.recommendation_engine import generate_decision_recommendations
from src.analysis.similarity_intelligence import (
    build_disabled_similarity_intelligence,
    build_failed_similarity_intelligence,
    build_similarity_intelligence,
    is_similarity_intelligence_disabled,
)
from src.analysis.violin_panel_builder import build_violin_panel_data
from src.ingest.awr_adb_loader import (
    build_feature_vector_record,
    get_db_connection,
    process_awr_batch,
    upsert_feature_vector,
)
from src.memory import memory_orchestrator
from src.parser.awr_parser import parse_awr_file
from src.reporting.html_dashboard import generate_html_dashboard

SNAPSHOT_TIME_FORMATS = (
    "%d-%b-%y %H:%M:%S",
    "%d-%b-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)


def _load_local_env_file() -> tuple[bool, Path]:
    """Load the repository-local .env file for consistent provider resolution."""

    env_path = Path(__file__).resolve().parents[1] / ".env"
    loaded = (
        load_dotenv(dotenv_path=env_path, override=False)
        if env_path.exists()
        else False
    )
    return loaded, env_path


def _resolve_ai_provider() -> str:
    """Resolve AI provider with OCI as the system default."""

    provider = str(os.getenv("AI_PROVIDER", "oci") or "oci").strip().lower()
    return provider or "oci"


def _resolve_ai_model_identifier(provider: str) -> str:
    """Resolve the configured model identifier for startup logging."""

    normalized_provider = str(provider or "").strip().lower()
    if normalized_provider == "oci":
        return str(os.getenv("OCI_MODEL_ID", "") or "").strip()
    if normalized_provider == "openai":
        return str(os.getenv("OPENAI_MODEL", "gpt-5.4-mini") or "").strip()
    return ""


def _runtime_config() -> dict[str, Any]:
    config: dict[str, Any] = {}
    if is_similarity_intelligence_disabled():
        config["disable_similarity_intelligence"] = True
    return config


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


def normalize_terms(text: str) -> str:
    return _normalize_terminology(text)


def _to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return value.__dict__


def _safe_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)

    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None

    return None


def _normalize_percentage_value(value: float | None) -> float | None:
    if value is None:
        return None
    if 0.0 <= value <= 1.0:
        return round(value * 100.0, 4)
    return round(value, 4)


def _format_pct(value: object) -> str:
    numeric_value = _safe_float(value)
    if numeric_value is None:
        return "0.0%"
    return f"{numeric_value:.1f}%"


def _format_metric(value: float | None, suffix: str = "") -> str:
    if value is None:
        return "Unavailable"
    if abs(value) >= 100:
        formatted = f"{value:.0f}"
    elif abs(value) >= 10:
        formatted = f"{value:.1f}"
    else:
        formatted = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{formatted}{suffix}"


def _format_generated_at_local() -> str:
    local_now = datetime.now().astimezone()
    month = local_now.strftime("%b")
    day = local_now.day
    year = local_now.year
    time_text = local_now.strftime("%I:%M %p").lstrip("0")
    return f"{month} {day}, {year}, {time_text}"


def _format_datetime_display(value: datetime | None) -> str:
    if value is None:
        return "Unavailable"
    return (
        value.strftime("%b ")
        + str(value.day)
        + value.strftime(", %Y, %I:%M %p").replace(" 0", " ")
    )


def _format_interval_display(
    start: datetime | None,
    end: datetime | None,
) -> str:
    if start is None or end is None:
        return "Unavailable"
    if start.date() == end.date():
        end_time = end.strftime("%I:%M %p").lstrip("0")
        return f"{_format_datetime_display(start)} to {end_time}"
    return f"{_format_datetime_display(start)} to {_format_datetime_display(end)}"


def _format_duration(start: datetime | None, end: datetime | None) -> str:
    if start is None or end is None or end < start:
        return "Unavailable"

    total_seconds = int((end - start).total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _json_for_html(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def _metric_series_key(metric_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", metric_name.strip().lower())
    return normalized.strip("_") + "_trend"


def _selected_snapshot_windows(
    snapshot_contexts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    windows_by_key: dict[tuple[datetime, datetime], dict[str, Any]] = {}
    for context in snapshot_contexts:
        begin_time = context.get("begin_time")
        end_time = context.get("end_time")
        if begin_time is None or end_time is None:
            continue
        window_key = (begin_time, end_time)
        windows_by_key.setdefault(
            window_key,
            {
                "key": window_key,
                "begin_time": begin_time,
                "end_time": end_time,
                "label": _snapshot_label(context),
            },
        )
    return sorted(windows_by_key.values(), key=lambda window: window["begin_time"])


def _resolve_scope_db_identity(
    snapshot_contexts: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    db_ids = list(
        dict.fromkeys(
            str(context["result"].run_metadata.db_id or "").strip()
            for context in snapshot_contexts
            if str(context["result"].run_metadata.db_id or "").strip()
        )
    )
    db_names = list(
        dict.fromkeys(
            str(context["result"].run_metadata.database_name or "").strip()
            for context in snapshot_contexts
            if str(context["result"].run_metadata.database_name or "").strip()
        )
    )
    db_id = db_ids[0] if len(db_ids) == 1 else None
    db_name = db_names[0] if len(db_names) == 1 else None
    return db_id, db_name


def _fetch_db_scope_metric_rows(
    snapshot_contexts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    debug_lines: list[str] = []
    selected_windows = _selected_snapshot_windows(snapshot_contexts)
    if not selected_windows:
        return [], ["DB-scope metric retrieval skipped: no canonical snapshot windows."]

    db_id, db_name = _resolve_scope_db_identity(snapshot_contexts)
    if db_id is None and db_name is None:
        return [], [
            "DB-scope metric retrieval skipped: current analysis scope did not resolve to a single DB identity."
        ]

    min_begin = selected_windows[0]["begin_time"]
    max_end = selected_windows[-1]["end_time"]
    selected_window_keys = {window["key"] for window in selected_windows}
    query = """
        SELECT
            DB_NAME,
            DBID,
            SNAP_BEGIN_TIME,
            SNAP_END_TIME,
            DB_VERSION,
            DATABASE_ROLE,
            INSTANCE_COUNT,
            PLATFORM,
            TOPOLOGY_CLASS,
            PLATFORM_CLASS,
            METRIC_NAME,
            METRIC_SCOPE,
            METRIC_CATEGORY,
            METRIC_VALUE_NUM,
            CONTRIBUTING_REPORT_COUNT,
            AWR_COUNT,
            SNAPSHOT_LABEL,
            DISTINCT_VALUE_COUNT,
            VALUE_COLLAPSE_RULE,
            DATA_QUALITY_FLAG
        FROM VW_AWR_FEATURE_METRIC_DB_SCOPE
        WHERE SNAP_BEGIN_TIME >= :min_begin
          AND SNAP_END_TIME <= :max_end
          AND (
                (:dbid IS NOT NULL AND DBID = :dbid)
             OR (:dbid IS NULL AND :db_name IS NOT NULL AND DB_NAME = :db_name)
          )
        ORDER BY SNAP_BEGIN_TIME, METRIC_NAME
    """
    bindings = {
        "min_begin": min_begin,
        "max_end": max_end,
        "dbid": int(db_id) if db_id and db_id.isdigit() else None,
        "db_name": db_name,
    }

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(query, bindings)
            rows = cursor.fetchall()
            cursor_description = getattr(cursor, "description", None)
            column_names = [column[0] for column in cursor_description or []]
    except Exception as exc:  # noqa: BLE001
        if connection is not None:
            connection.close()
            connection = None
        return [], [f"DB-scope metric retrieval unavailable: {exc}"]
    finally:
        if connection is not None:
            connection.close()

    scoped_rows = []
    for row in rows:
        row_dict = dict(zip(column_names, row, strict=True))
        window_key = (
            row_dict.get("SNAP_BEGIN_TIME"),
            row_dict.get("SNAP_END_TIME"),
        )
        if window_key in selected_window_keys:
            scoped_rows.append(row_dict)

    debug_lines.append(
        "DB-scope metric retrieval source: VW_AWR_FEATURE_METRIC_DB_SCOPE"
    )
    debug_lines.append(
        "DB-scope metric retrieval rows: "
        + str(len(scoped_rows))
        + f" for DBID={db_id or 'n/a'} DB_NAME={db_name or 'n/a'}"
    )
    return scoped_rows, debug_lines


def _series_note_from_rows(metric_rows: list[dict[str, Any]]) -> str | None:
    if not metric_rows:
        return None
    data_quality_flags = sorted(
        {
            str(row.get("DATA_QUALITY_FLAG") or "").strip()
            for row in metric_rows
            if str(row.get("DATA_QUALITY_FLAG") or "").strip()
        }
    )
    collapse_rules = sorted(
        {
            str(row.get("VALUE_COLLAPSE_RULE") or "").strip()
            for row in metric_rows
            if str(row.get("VALUE_COLLAPSE_RULE") or "").strip()
        }
    )
    if data_quality_flags == ["CONSISTENT"] and collapse_rules == ["IDENTICAL_VALUE"]:
        return None
    quality_text = ", ".join(data_quality_flags) if data_quality_flags else "Unknown"
    collapse_text = ", ".join(collapse_rules) if collapse_rules else "Unknown"
    return "Data quality: " + quality_text + "; collapse rule: " + collapse_text


def _build_db_scope_metric_history(
    snapshot_contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    selected_windows = _selected_snapshot_windows(snapshot_contexts)
    snapshot_labels = [window["label"] for window in selected_windows]
    metric_rows, debug_lines = _fetch_db_scope_metric_rows(snapshot_contexts)
    if not metric_rows:
        return {
            "available": False,
            "rows": [],
            "chart_specs": [],
            "chart_payload": {"snapshot_labels": snapshot_labels},
            "metrics_by_name": {},
            "metrics_by_domain": {},
            "snapshot_labels": snapshot_labels,
            "debug_lines": debug_lines,
        }

    rows_by_metric: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in metric_rows:
        rows_by_metric[str(row.get("METRIC_NAME") or "")].append(row)

    metrics_by_name: dict[str, dict[str, Any]] = {}
    metrics_by_domain: dict[str, list[dict[str, Any]]] = {
        domain: [] for domain in DOMAIN_DISPLAY_ORDER
    }
    chart_specs: list[dict[str, Any]] = []
    chart_payload: dict[str, Any] = {"snapshot_labels": snapshot_labels}

    for definition in get_implemented_metric_definitions():
        metric_name = definition.source_metric_name or definition.metric_name
        metric_scope_rows = rows_by_metric.get(metric_name, [])
        if not metric_scope_rows:
            continue

        row_by_window = {
            (row["SNAP_BEGIN_TIME"], row["SNAP_END_TIME"]): row
            for row in metric_scope_rows
        }
        values = [
            _safe_float(row_by_window.get(window["key"], {}).get("METRIC_VALUE_NUM"))
            for window in selected_windows
        ]
        if not any(value is not None for value in values):
            continue

        chart_key = _metric_series_key(definition.metric_name)
        chart_payload[chart_key] = values
        note = _series_note_from_rows(metric_scope_rows)
        spec = {
            "key": chart_key,
            "title": definition.chart_title,
            "label": definition.chart_label,
            "color": definition.color,
            "container_id": chart_key + "Chart",
            "domain": definition.domain,
        }
        if note:
            spec["note"] = note
        chart_specs.append(spec)

        sql_row_count = len(metric_scope_rows)
        point_count = sum(1 for value in values if value is not None)
        metrics_by_name[definition.metric_name] = {
            "definition": definition,
            "rows": metric_scope_rows,
            "values": values,
            "snapshot_labels": snapshot_labels,
            "chart_key": chart_key,
            "sql_row_count": sql_row_count,
            "point_count": point_count,
            "chronological": all(
                earlier["SNAP_BEGIN_TIME"] <= later["SNAP_BEGIN_TIME"]
                for earlier, later in zip(
                    metric_scope_rows, metric_scope_rows[1:], strict=False
                )
            ),
            "data_quality_flags": sorted(
                {
                    str(row.get("DATA_QUALITY_FLAG") or "").strip()
                    for row in metric_scope_rows
                    if str(row.get("DATA_QUALITY_FLAG") or "").strip()
                }
            ),
            "value_collapse_rules": sorted(
                {
                    str(row.get("VALUE_COLLAPSE_RULE") or "").strip()
                    for row in metric_scope_rows
                    if str(row.get("VALUE_COLLAPSE_RULE") or "").strip()
                }
            ),
        }
        metrics_by_domain[definition.domain].append(
            metrics_by_name[definition.metric_name]
        )
        debug_lines.append(
            "DB metric "
            + definition.metric_name
            + f": sql_rows={sql_row_count} points={point_count} "
            + f"chronological={metrics_by_name[definition.metric_name]['chronological']} "
            + f"domain={definition.domain} source=VW_AWR_FEATURE_METRIC_DB_SCOPE"
        )

    non_empty_domain_metrics = {
        domain: metrics for domain, metrics in metrics_by_domain.items() if metrics
    }
    rendered_domains = list(non_empty_domain_metrics)
    debug_lines.append(
        "Rendered domains from DB-scope metrics: "
        + (", ".join(rendered_domains) if rendered_domains else "None")
    )
    return {
        "available": bool(chart_specs),
        "rows": metric_rows,
        "chart_specs": chart_specs,
        "chart_payload": chart_payload,
        "metrics_by_name": metrics_by_name,
        "metrics_by_domain": non_empty_domain_metrics,
        "snapshot_labels": snapshot_labels,
        "debug_lines": debug_lines,
    }


def _history_values_for_metric(
    db_scope_metrics: dict[str, Any],
    *metric_names: str,
) -> list[float | None]:
    snapshot_labels = db_scope_metrics.get("snapshot_labels") or []
    for metric_name in metric_names:
        metric_history = (db_scope_metrics.get("metrics_by_name") or {}).get(
            metric_name
        )
        if metric_history:
            return list(metric_history["values"])
    return [None] * len(snapshot_labels)


def _join_factors(factors: list[str]) -> str:
    if not factors:
        return ""

    if len(factors) == 1:
        return factors[0].capitalize()

    if len(factors) == 2:
        return f"{factors[0].capitalize()}, and {factors[1]}"

    return f"{factors[0].capitalize()}, {factors[1]}, and {factors[2]}"


def _parse_snapshot_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate:
        return None

    parts = candidate.split()
    if len(parts) >= 3 and parts[0].isdigit():
        candidate = " ".join(parts[1:])

    for fmt in SNAPSHOT_TIME_FORMATS:
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def _snapshot_sort_key(context: dict[str, Any]) -> tuple[int, object]:
    begin_time = context.get("begin_time")
    if begin_time is not None:
        return (0, begin_time)
    return (1, context["file_name"])


def _snapshot_label(context: dict[str, Any]) -> str:
    begin_time = context.get("begin_time")
    end_time = context.get("end_time")
    if begin_time and end_time:
        return (
            f"{begin_time.strftime('%Y-%m-%d %H:%M')} -> "
            f"{end_time.strftime('%H:%M')}"
        )
    if begin_time:
        return begin_time.strftime("%Y-%m-%d %H:%M")
    return context["file_name"]


def _extract_load_profile_metric(result: Any, metric_name: str) -> float | None:
    for metric in result.cpu_metrics:
        if metric.get("metric_group") != "load_profile":
            continue
        if str(metric.get("metric_name") or "").strip() != metric_name:
            continue
        return _safe_float(metric.get("per_second"))
    return None


def _sum_wait_class_pct(result: Any, wait_class: str) -> float | None:
    values = [
        _safe_float(row.get("pct_db_time"))
        for row in result.wait_events
        if str(row.get("wait_class") or "").strip() == wait_class
    ]
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return round(sum(numeric_values), 4)


def _extract_log_file_sync_ms(result: Any) -> float | None:
    for row in result.wait_events:
        if str(row.get("event_name") or "").strip() != "log file sync":
            continue
        return _safe_float(row.get("avg_wait_ms"))
    return None


def _compute_cpu_pct(result: Any) -> float | None:
    db_cpu = _extract_load_profile_metric(result, "DB CPU(s)")
    db_time = _extract_load_profile_metric(result, "DB Time(s)")
    if db_cpu is None or db_time is None or db_time <= 0:
        return None
    return round((db_cpu / db_time) * 100.0, 4)


def _top_sql_concentration(result: Any) -> float | None:
    pct_values: list[float] = []
    for row in result.top_sql[:3]:
        pct_total = _safe_float(row.get("pct_total"))
        if pct_total is not None:
            pct_values.append(pct_total)
    if pct_values:
        return round(sum(pct_values), 4)

    elapsed_values: list[float] = []
    for row in result.top_sql:
        elapsed_value = _safe_float(row.get("elapsed_time_seconds"))
        if elapsed_value is not None:
            elapsed_values.append(elapsed_value)
    if not elapsed_values:
        return None

    top_elapsed = sum(elapsed_values[:3])
    total_elapsed = sum(elapsed_values)
    if total_elapsed <= 0:
        return None
    return round((top_elapsed / total_elapsed) * 100.0, 4)


def _top_sql_module_name(result: Any) -> str | None:
    modules: list[str] = []
    for sql_row in result.top_sql[:5]:
        module = str(sql_row.get("module") or "").strip()
        if module and module not in modules:
            modules.append(module)
    if not modules:
        return None
    return modules[0]


def _dominant_wait_event(result: Any, wait_class: str) -> str | None:
    candidates = [
        row
        for row in result.wait_events
        if str(row.get("wait_class") or "").strip() == wait_class
    ]
    if not candidates:
        return None
    ranked = sorted(
        candidates,
        key=lambda row: _safe_float(row.get("pct_db_time")) or 0.0,
        reverse=True,
    )
    event_name = str(ranked[0].get("event_name") or "").strip()
    return event_name or None


def _topology_signals(result: Any) -> dict[str, Any]:
    signals = getattr(result, "topology_signals", None)
    if isinstance(signals, dict):
        return signals
    return {}


def _topology_float(result: Any, key: str) -> float | None:
    return _safe_float(_topology_signals(result).get(key))


def _topology_pct(result: Any, key: str) -> float | None:
    return _normalize_percentage_value(_topology_float(result, key))


def _topology_text(result: Any, key: str) -> str | None:
    value = _topology_signals(result).get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _topology_flag(result: Any, key: str) -> bool:
    return bool(_topology_signals(result).get(key))


def _humanize_classification(value: str | None) -> str:
    text = str(value or "").strip()
    if not text:
        return "Unknown"
    return text.replace("_", " ").title()


def _collect_event_classes(
    snapshot_contexts: list[dict[str, Any]],
) -> list[str]:
    return list(
        dict.fromkeys(
            str(
                (context.get("topology") or {}).get("operational_event_class") or ""
            ).strip()
            for context in snapshot_contexts
            if str(
                (context.get("topology") or {}).get("operational_event_class") or ""
            ).strip()
            not in {"", "NONE"}
        )
    )


def _collect_topology_labels(
    snapshot_contexts: list[dict[str, Any]],
) -> list[str]:
    labels: list[str] = []
    if any(
        (context.get("topology") or {}).get("is_rac") for context in snapshot_contexts
    ):
        labels.append("RAC")
    if any(
        (context.get("topology") or {}).get("is_dataguard")
        for context in snapshot_contexts
    ):
        labels.append("Data Guard")
    if not labels:
        labels.append("Single Instance")
    return labels


def _collect_platform_labels(
    snapshot_contexts: list[dict[str, Any]],
) -> list[str]:
    if any(
        (context.get("topology") or {}).get("is_exadata")
        for context in snapshot_contexts
    ):
        return ["Exadata"]
    return ["Generic"]


def _summarize_database_role(
    snapshot_contexts: list[dict[str, Any]],
) -> str:
    roles = list(
        dict.fromkeys(
            str((context.get("topology") or {}).get("database_role") or "").strip()
            for context in snapshot_contexts
            if str((context.get("topology") or {}).get("database_role") or "").strip()
            not in {"", "UNKNOWN"}
        )
    )
    if not roles:
        return "Not explicitly identified in AWR"
    if len(roles) == 1:
        return roles[0]
    return "Multiple roles observed (" + ", ".join(roles) + ")"


def _join_readable_labels(labels: list[str]) -> str:
    cleaned = [str(label).strip() for label in labels if str(label).strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return cleaned[0] + " and " + cleaned[1]
    return ", ".join(cleaned[:-1]) + ", and " + cleaned[-1]


def _format_dataguard_evidence_phrase(
    transport_lag_sec: float | None,
    apply_lag_sec: float | None,
    database_role: str | None = None,
) -> str:
    role_text = str(database_role or "UNKNOWN").strip() or "UNKNOWN"
    lag_parts: list[str] = []
    if transport_lag_sec is not None:
        lag_parts.append(f"transport lag is {_format_metric(transport_lag_sec, 's')}")
    if apply_lag_sec is not None:
        lag_parts.append(f"apply lag is {_format_metric(apply_lag_sec, 's')}")
    if lag_parts:
        role_prefix = (
            f"Database role is {role_text}"
            if role_text != "UNKNOWN"
            else "Data Guard behavior is present, but the role is not explicit in the report"
        )
        return role_prefix + "; " + " and ".join(lag_parts) + "."
    if role_text != "UNKNOWN":
        return (
            f"Database role is {role_text}, but explicit transport/apply lag values "
            "are unavailable in this interval."
        )
    return (
        "Data Guard transition or replication-state evidence is present, but explicit "
        "transport/apply lag values are unavailable in this interval."
    )


def _dashboard_issue_dicts(
    issues: list[Any],
    metrics: dict[str, Any],
    topology: dict[str, Any],
) -> list[dict[str, Any]]:
    lag_available = (
        metrics.get("transport_lag_sec") is not None
        or metrics.get("apply_lag_sec") is not None
    )
    normalized: list[dict[str, Any]] = []
    for issue in issues:
        issue_dict = _to_dict(issue)
        if (
            str(issue_dict.get("issue_type") or "") == "dg_replication_state"
            and not lag_available
        ):
            issue_dict = dict(issue_dict)
            issue_dict["summary"] = (
                "Data Guard transition or replication-state evidence is present, "
                "but explicit transport/apply lag values are unavailable in this interval."
            )
            evidence = dict(issue_dict.get("evidence") or {})
            evidence["database_role"] = topology.get("database_role")
            issue_dict["evidence"] = evidence
        normalized.append(issue_dict)
    return normalized


def _dashboard_recommendation_dicts(
    recommendations: list[Any],
    metrics: dict[str, Any],
    topology: dict[str, Any],
) -> list[dict[str, Any]]:
    lag_available = (
        metrics.get("transport_lag_sec") is not None
        or metrics.get("apply_lag_sec") is not None
    )
    normalized: list[dict[str, Any]] = []
    for recommendation in recommendations:
        recommendation_dict = _to_dict(recommendation)
        if (
            str(recommendation_dict.get("issue_type") or "") == "dg_replication_state"
            and not lag_available
        ):
            recommendation_dict = dict(recommendation_dict)
            recommendation_dict["recommendation"] = (
                "Validate Data Guard role, transition state, and replication "
                "health before treating this interval as a pure sizing problem."
            )
            recommendation_dict["rationale"] = (
                "Deterministic topology evidence indicates Data Guard "
                "transition or replication-state activity, but explicit "
                "transport/apply lag values are unavailable."
            )
            recommendation_dict["next_step"] = (
                "Review broker status, alert history, and redo transport/apply state for the interval."
            )
        normalized.append(recommendation_dict)
    return normalized


def _get_compatibility_issues(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Return legacy issue data only for transitional compatibility helpers."""

    cached = context.get("compatibility_issues")
    if isinstance(cached, list):
        return cached

    issues = _dashboard_issue_dicts(
        detect_issues(context["result"]),
        context.get("metrics") or {},
        context.get("topology") or {},
    )
    context["compatibility_issues"] = issues
    return issues


def _dashboard_decision_recommendation_dicts(
    recommendations: list[Any],
) -> list[dict[str, Any]]:
    """Adapt decision-driven recommendations for the legacy dashboard renderer."""

    normalized: list[dict[str, Any]] = []
    for recommendation in recommendations:
        recommendation_dict = recommendation.to_dict()
        issue_type = (
            "cpu_pressure"
            if str(recommendation_dict.get("domain") or "").upper() == "CPU"
            else (
                f"{str(recommendation_dict.get('domain') or 'issue').lower()}_"
                f"{str(recommendation_dict.get('category') or 'action').lower()}"
            )
        )
        normalized.append(
            {
                "issue_type": issue_type,
                "severity": str(recommendation_dict.get("priority") or "low").lower(),
                "recommendation": recommendation_dict.get("action", ""),
                "rationale": recommendation_dict.get("rationale", ""),
                "next_step": recommendation_dict.get("title", ""),
                "actions": [recommendation_dict.get("action", "")],
                "evidence": recommendation_dict.get("source_signals", {}),
            }
        )
    return normalized


def _build_summary_key_signals(
    context: dict[str, Any],
) -> list[str]:
    metrics = context.get("metrics") or {}
    topology = context.get("topology") or {}
    signals: list[str] = []

    event_class = str(topology.get("operational_event_class") or "").strip()
    if event_class and event_class != "NONE":
        signals.append("Operational event: " + _humanize_classification(event_class))
    elif topology.get("interconnect_stress_flag"):
        signals.append("Operational state: Interconnect Stress")

    signals.append(f"CPU: {_format_metric(metrics.get('cpu_pct'), '%')} DB time")
    signals.append(
        "Top SQL concentration (top 3 share): "
        + _format_metric(metrics.get("top_sql_concentration"), "%")
    )
    signals.append(f"User I/O: {_format_metric(metrics.get('user_io_pct'), '%')}")

    if metrics.get("cluster_wait_pct_db_time") is not None:
        signals.append(
            "Cluster waits: "
            + _format_metric(metrics.get("cluster_wait_pct_db_time"), "%")
            + " DB time"
        )
    elif metrics.get("gc_total_wait_pct_db_time") is not None:
        signals.append(
            "Combined GC current + GC CR: "
            + _format_metric(metrics.get("gc_total_wait_pct_db_time"), "%")
            + " DB time"
        )

    if metrics.get("transport_lag_sec") is not None:
        signals.append(
            "Transport lag: " + _format_metric(metrics.get("transport_lag_sec"), "s")
        )
    elif metrics.get("apply_lag_sec") is not None:
        signals.append(
            "Apply lag: " + _format_metric(metrics.get("apply_lag_sec"), "s")
        )

    if metrics.get("exa_cell_io_pct_db_time") is not None:
        signals.append(
            "Exadata cell waits: "
            + _format_metric(metrics.get("exa_cell_io_pct_db_time"), "%")
            + " DB time"
        )
    return signals[:6]


def _trend_direction(values: list[float | None]) -> str:
    numeric_values = [value for value in values if value is not None]
    if len(numeric_values) < 2:
        return "insufficient history"

    first = numeric_values[0]
    last = numeric_values[-1]
    peak = max(numeric_values)
    trough = min(numeric_values)
    delta = last - first
    range_size = peak - trough
    tolerance = max(2.0, abs(first) * 0.1)

    if abs(delta) <= tolerance and range_size <= tolerance * 1.5:
        return "stable"
    if delta > tolerance:
        if last < peak and (peak - last) > tolerance:
            return "recovering"
        return "degrading"
    if delta < -tolerance:
        return "improving"
    return "stable"


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 0:
        return (ordered[middle - 1] + ordered[middle]) / 2
    return ordered[middle]


def _detect_metric_anomalies(
    snapshot_labels: list[str],
    values: list[float | None],
    metric_name: str,
    anomaly_type: str,
    floor: float,
    multiplier: float,
) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    history: list[float] = []

    for index, value in enumerate(values):
        if value is None:
            continue

        if len(history) >= 2:
            baseline = _median(history)
            threshold = max(floor, baseline * multiplier)
            if value >= threshold:
                severity = "high" if value >= threshold * 1.35 else "medium"
                anomalies.append(
                    {
                        "snapshot_label": snapshot_labels[index],
                        "metric": metric_name,
                        "anomaly_type": anomaly_type,
                        "severity": severity,
                        "value": round(value, 4),
                        "baseline": round(baseline, 4),
                        "reason": (
                            f"{metric_name} spiked from a baseline of "
                            f"{baseline:.2f} to {value:.2f}."
                        ),
                    }
                )

        history.append(value)

    return anomalies


def _canonical_anomaly_metric_label(metric: str) -> str:
    normalized = re.sub(r"[-_]+", " ", str(metric or "").strip().lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if normalized == "interconnect stress":
        return "Interconnect Stress"
    if normalized == "failover event":
        return "Failover Event"
    if normalized == "post failover recovery":
        return "Post-Failover Recovery"
    if normalized == "role transition":
        return "Role Transition"
    return str(metric or "").strip()


def _transition_metric_tokens(metric: str) -> list[str]:
    normalized = _canonical_anomaly_metric_label(metric)
    parts = [
        _canonical_anomaly_metric_label(part.strip())
        for part in re.split(r"\s*/\s*", normalized)
        if part.strip()
    ]
    return [
        part
        for part in parts
        if part
        in {
            "Failover Event",
            "Role Transition",
            "Post-Failover Recovery",
        }
    ]


def _dedupe_anomaly_windows(
    windows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for window in windows:
        normalized_metric = _canonical_anomaly_metric_label(
            str(window.get("metric") or "")
        )
        normalized_window = {**window, "metric": normalized_metric}
        key = (
            str(normalized_window.get("snapshot_label") or ""),
            normalized_metric.lower(),
        )
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = normalized_window
            continue
        if _severity_score(
            str(normalized_window.get("severity") or "")
        ) > _severity_score(str(existing.get("severity") or "")):
            deduped[key] = normalized_window
            continue
        if len(str(normalized_window.get("reason") or "")) > len(
            str(existing.get("reason") or "")
        ):
            deduped[key] = normalized_window
    return list(deduped.values())


def _collapse_transition_event_windows(
    windows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    transition_order = [
        "Failover Event",
        "Role Transition",
        "Post-Failover Recovery",
    ]
    grouped_windows: dict[str, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []

    for window in windows:
        metric = _canonical_anomaly_metric_label(str(window.get("metric") or ""))
        normalized_window = {**window, "metric": metric}
        transition_tokens = _transition_metric_tokens(metric)
        if (
            str(normalized_window.get("anomaly_type") or "") == "topology_event"
            and transition_tokens
        ):
            snapshot_label = str(normalized_window.get("snapshot_label") or "")
            grouped_windows.setdefault(snapshot_label, []).append(normalized_window)
            continue
        passthrough.append(normalized_window)

    for snapshot_label, interval_windows in grouped_windows.items():
        distinct_transition_tokens = [
            metric
            for metric in transition_order
            if any(
                metric in _transition_metric_tokens(window["metric"])
                for window in interval_windows
            )
        ]
        if len(distinct_transition_tokens) == 1:
            matching_window = next(
                (
                    window
                    for window in interval_windows
                    if distinct_transition_tokens[0]
                    in _transition_metric_tokens(window["metric"])
                ),
                interval_windows[0],
            )
            passthrough.append(
                {
                    **matching_window,
                    "metric": distinct_transition_tokens[0],
                }
            )
            continue
        severity = max(
            (str(window.get("severity") or "") for window in interval_windows),
            key=_severity_score,
        )
        passthrough.append(
            {
                "snapshot_label": snapshot_label,
                "metric": " / ".join(distinct_transition_tokens),
                "anomaly_type": "topology_event",
                "severity": severity,
                "value": None,
                "baseline": None,
                "reason": (
                    "Deterministic topology-event evidence places this interval "
                    "inside a transition/recovery phase."
                ),
            }
        )

    return passthrough


def _build_local_time_series(snapshot_contexts: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot_labels = [context["snapshot_label"] for context in snapshot_contexts]
    cpu_trend = [context["metrics"]["cpu_pct"] for context in snapshot_contexts]
    io_trend = [context["metrics"]["user_io_pct"] for context in snapshot_contexts]
    commit_trend = [
        context["metrics"]["commit_pressure"] for context in snapshot_contexts
    ]
    concurrency_trend = [
        context["metrics"]["concurrency_pct"] for context in snapshot_contexts
    ]
    sql_concentration_trend = [
        context["metrics"]["top_sql_concentration"] for context in snapshot_contexts
    ]
    hard_parses_trend = [
        context["metrics"]["hard_parses_per_sec"] for context in snapshot_contexts
    ]
    log_file_sync_trend = [
        context["metrics"]["log_file_sync_ms"] for context in snapshot_contexts
    ]
    temp_io_trend = [
        context["metrics"]["temp_io_pressure"] for context in snapshot_contexts
    ]
    pga_spill_trend = [
        context["metrics"]["pga_spill_pressure"] for context in snapshot_contexts
    ]
    cluster_wait_trend = [
        context["metrics"]["cluster_wait_pct_db_time"] for context in snapshot_contexts
    ]
    gc_wait_trend = [
        context["metrics"]["gc_total_wait_pct_db_time"] for context in snapshot_contexts
    ]
    dg_transport_lag_trend = [
        context["metrics"]["transport_lag_sec"] for context in snapshot_contexts
    ]
    dg_apply_lag_trend = [
        context["metrics"]["apply_lag_sec"] for context in snapshot_contexts
    ]
    exa_cell_io_trend = [
        context["metrics"]["exa_cell_io_pct_db_time"] for context in snapshot_contexts
    ]
    exa_offload_efficiency_trend = [
        context["metrics"]["exa_offload_efficiency"] for context in snapshot_contexts
    ]

    return {
        "snapshot_labels": snapshot_labels,
        "cpu_trend": cpu_trend,
        "io_trend": io_trend,
        "commit_trend": commit_trend,
        "concurrency_trend": concurrency_trend,
        "sql_concentration_trend": sql_concentration_trend,
        "hard_parses_trend": hard_parses_trend,
        "log_file_sync_trend": log_file_sync_trend,
        "temp_io_trend": temp_io_trend,
        "pga_spill_trend": pga_spill_trend,
        "cluster_wait_trend": cluster_wait_trend,
        "gc_wait_trend": gc_wait_trend,
        "dg_transport_lag_trend": dg_transport_lag_trend,
        "dg_apply_lag_trend": dg_apply_lag_trend,
        "exa_cell_io_trend": exa_cell_io_trend,
        "exa_offload_efficiency_trend": exa_offload_efficiency_trend,
        "trend_directions": {
            "cpu": _trend_direction(cpu_trend),
            "io": _trend_direction(io_trend),
            "commit": _trend_direction(commit_trend),
            "concurrency": _trend_direction(concurrency_trend),
            "sql_concentration": _trend_direction(sql_concentration_trend),
            "hard_parses": _trend_direction(hard_parses_trend),
            "cluster_wait": _trend_direction(cluster_wait_trend),
            "gc_wait": _trend_direction(gc_wait_trend),
            "dg_transport_lag": _trend_direction(dg_transport_lag_trend),
            "dg_apply_lag": _trend_direction(dg_apply_lag_trend),
            "exa_cell_io": _trend_direction(exa_cell_io_trend),
            "exa_offload_efficiency": _trend_direction(exa_offload_efficiency_trend),
        },
    }


def _build_time_series(
    snapshot_contexts: list[dict[str, Any]],
    db_scope_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not db_scope_metrics or not db_scope_metrics.get("available"):
        return _build_local_time_series(snapshot_contexts)

    snapshot_labels = db_scope_metrics.get("snapshot_labels") or []
    cpu_trend = _history_values_for_metric(
        db_scope_metrics,
        "DB_CPU_PCT_DB_TIME",
        "CPU_UTIL_P95",
    )
    io_trend = _history_values_for_metric(db_scope_metrics, "USER_IO_PRESSURE")
    commit_trend = _history_values_for_metric(db_scope_metrics, "LOG_FILE_SYNC_MS")
    concurrency_trend = _history_values_for_metric(
        db_scope_metrics,
        "CONCURRENCY_PRESSURE",
    )
    sql_concentration_trend = _history_values_for_metric(
        db_scope_metrics,
        "TOP_SQL_LOAD_CONCENTRATION",
    )
    hard_parses_trend = _history_values_for_metric(
        db_scope_metrics,
        "HARD_PARSES_PER_SEC",
    )
    log_file_sync_trend = _history_values_for_metric(
        db_scope_metrics,
        "LOG_FILE_SYNC_MS",
    )
    temp_io_trend = _history_values_for_metric(db_scope_metrics, "TEMP_IO_PRESSURE")
    pga_spill_trend = _history_values_for_metric(
        db_scope_metrics,
        "PGA_SPILL_PRESSURE",
    )
    cluster_wait_trend = _history_values_for_metric(
        db_scope_metrics,
        "CLUSTER_WAIT_PCT_DB_TIME",
    )
    gc_current_wait = _history_values_for_metric(
        db_scope_metrics,
        "GC_CURRENT_WAIT_PCT_DB_TIME",
    )
    gc_cr_wait = _history_values_for_metric(
        db_scope_metrics,
        "GC_CR_WAIT_PCT_DB_TIME",
    )
    gc_wait_trend = []
    for current_wait, cr_wait in zip(gc_current_wait, gc_cr_wait, strict=True):
        if current_wait is None and cr_wait is None:
            gc_wait_trend.append(None)
            continue
        gc_wait_trend.append(round((current_wait or 0.0) + (cr_wait or 0.0), 4))
    dg_transport_lag_trend = _history_values_for_metric(
        db_scope_metrics,
        "TRANSPORT_LAG_SEC",
    )
    dg_apply_lag_trend = _history_values_for_metric(
        db_scope_metrics,
        "APPLY_LAG_SEC",
    )
    exa_cell_io_trend = _history_values_for_metric(
        db_scope_metrics,
        "EXA_CELL_IO_PCT_DB_TIME",
    )
    exa_offload_efficiency_trend = _history_values_for_metric(
        db_scope_metrics,
        "EXA_OFFLOAD_EFFICIENCY",
    )

    return {
        "snapshot_labels": snapshot_labels,
        "cpu_trend": cpu_trend,
        "io_trend": io_trend,
        "commit_trend": commit_trend,
        "concurrency_trend": concurrency_trend,
        "sql_concentration_trend": sql_concentration_trend,
        "hard_parses_trend": hard_parses_trend,
        "log_file_sync_trend": log_file_sync_trend,
        "temp_io_trend": temp_io_trend,
        "pga_spill_trend": pga_spill_trend,
        "cluster_wait_trend": cluster_wait_trend,
        "gc_wait_trend": gc_wait_trend,
        "dg_transport_lag_trend": dg_transport_lag_trend,
        "dg_apply_lag_trend": dg_apply_lag_trend,
        "exa_cell_io_trend": exa_cell_io_trend,
        "exa_offload_efficiency_trend": exa_offload_efficiency_trend,
        "trend_directions": {
            "cpu": _trend_direction(cpu_trend),
            "io": _trend_direction(io_trend),
            "commit": _trend_direction(commit_trend),
            "concurrency": _trend_direction(concurrency_trend),
            "sql_concentration": _trend_direction(sql_concentration_trend),
            "hard_parses": _trend_direction(hard_parses_trend),
            "cluster_wait": _trend_direction(cluster_wait_trend),
            "gc_wait": _trend_direction(gc_wait_trend),
            "dg_transport_lag": _trend_direction(dg_transport_lag_trend),
            "dg_apply_lag": _trend_direction(dg_apply_lag_trend),
            "exa_cell_io": _trend_direction(exa_cell_io_trend),
            "exa_offload_efficiency": _trend_direction(exa_offload_efficiency_trend),
        },
    }


def _build_anomaly_windows(
    snapshot_contexts: list[dict[str, Any]],
    time_series: dict[str, Any],
) -> list[dict[str, Any]]:
    if len(snapshot_contexts) < 2:
        return []

    snapshot_labels = time_series["snapshot_labels"]
    anomalies: list[dict[str, Any]] = []
    anomalies.extend(
        _detect_metric_anomalies(
            snapshot_labels,
            time_series["commit_trend"],
            "Commit / log file sync",
            "commit_anomaly",
            floor=8.0,
            multiplier=1.6,
        )
    )
    anomalies.extend(
        _detect_metric_anomalies(
            snapshot_labels,
            time_series["concurrency_trend"],
            "Concurrency",
            "concurrency_anomaly",
            floor=8.0,
            multiplier=1.6,
        )
    )
    anomalies.extend(
        _detect_metric_anomalies(
            snapshot_labels,
            time_series["io_trend"],
            "User I/O",
            "io_anomaly",
            floor=18.0,
            multiplier=1.5,
        )
    )
    if any(value is not None for value in time_series["cluster_wait_trend"]):
        anomalies.extend(
            _detect_metric_anomalies(
                snapshot_labels,
                time_series["cluster_wait_trend"],
                "Cluster waits",
                "cluster_anomaly",
                floor=8.0,
                multiplier=1.5,
            )
        )
    if any(value is not None for value in time_series["dg_transport_lag_trend"]):
        anomalies.extend(
            _detect_metric_anomalies(
                snapshot_labels,
                time_series["dg_transport_lag_trend"],
                "Data Guard transport lag",
                "dg_transport_lag",
                floor=30.0,
                multiplier=1.5,
            )
        )
    anomalies.extend(_build_topology_event_windows(snapshot_contexts))
    anomalies = _dedupe_anomaly_windows(anomalies)
    anomalies = _collapse_transition_event_windows(anomalies)
    anomalies = _dedupe_anomaly_windows(anomalies)
    anomalies.sort(
        key=lambda window: (
            _severity_score(window["severity"]),
            window["snapshot_label"],
        ),
        reverse=True,
    )
    return anomalies


def _build_topology_event_windows(
    snapshot_contexts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    for context in snapshot_contexts:
        topology = context.get("topology") or {}
        snapshot_label = context["snapshot_label"]
        event_specs: list[tuple[str, str, str, float | None]] = []

        if topology.get("failover_event_flag"):
            event_specs.append(
                (
                    "Failover event",
                    "high",
                    "Deterministic topology/event evidence places this interval inside a failover phase.",
                    None,
                )
            )
        if topology.get("role_transition_flag"):
            event_specs.append(
                (
                    "Role transition",
                    "high",
                    "Deterministic topology/event evidence shows a role-transition phase in this interval.",
                    None,
                )
            )
        if topology.get("post_failover_recovery_flag"):
            event_specs.append(
                (
                    "Post-failover recovery",
                    "high",
                    "Deterministic topology/event evidence shows post-failover recovery behavior in this interval.",
                    None,
                )
            )

        event_class = str(topology.get("operational_event_class") or "NONE").strip()
        if event_class and event_class not in {"", "NONE"}:
            humanized = _humanize_classification(event_class)
            if all(spec[0].lower() != humanized.lower() for spec in event_specs):
                event_specs.append(
                    (
                        humanized,
                        (
                            "high"
                            if event_class
                            in {"FAILOVER_EVENT", "POST_FAILOVER_RECOVERY"}
                            else "medium"
                        ),
                        "Deterministic topology/event classification flagged "
                        f"{humanized.lower()} in this interval.",
                        None,
                    )
                )

        if topology.get("interconnect_stress_flag"):
            event_specs.append(
                (
                    "Interconnect Stress",
                    "medium",
                    "Deterministic RAC/interconnect evidence indicates cluster coordination stress in this interval.",
                    context["metrics"].get("cluster_wait_pct_db_time"),
                )
            )

        seen_metrics: set[str] = set()
        for metric, severity, reason, value in event_specs:
            if metric in seen_metrics:
                continue
            seen_metrics.add(metric)
            windows.append(
                {
                    "snapshot_label": snapshot_label,
                    "metric": metric,
                    "anomaly_type": "topology_event",
                    "severity": severity,
                    "value": value,
                    "baseline": None,
                    "reason": reason,
                }
            )
    return windows


def _build_trend_findings(time_series: dict[str, Any]) -> list[str]:
    trend_directions = time_series["trend_directions"]
    snapshot_count = max(len(time_series.get("snapshot_labels") or []), 1)

    def is_sparse_series(series_key: str) -> bool:
        series = time_series.get(series_key) or []
        populated = sum(1 for value in series if value is not None)
        return populated >= 2 and (populated < 3 or (populated / snapshot_count) < 0.6)

    def has_fragmented_history(series_key: str) -> bool:
        series = time_series.get(series_key) or []
        populated = sum(1 for value in series if value is not None)
        return populated >= 2 and populated < snapshot_count

    def describe_direction(direction: str) -> str:
        return {
            "degrading": "trended upward",
            "improving": "eased",
            "recovering": "spiked and then moderated",
            "stable": "held broadly steady",
            "insufficient history": "had insufficient history for a trend call",
        }.get(direction, direction)

    def describe_sparse_direction(direction: str) -> str:
        return {
            "degrading": "worsened",
            "improving": "eased",
            "recovering": "spiked and then moderated",
            "stable": "remained broadly steady",
            "insufficient history": "had insufficient populated history for a trend call",
        }.get(direction, direction)

    findings = [
        f"CPU pressure {describe_direction(trend_directions['cpu'])} over the period reviewed.",
        f"User I/O {describe_direction(trend_directions['io'])} across the same period.",
        (
            "Available populated intervals suggest commit latency "
            f"{describe_sparse_direction(trend_directions['commit'])}."
            if is_sparse_series("commit_trend")
            or has_fragmented_history("commit_trend")
            else f"Commit latency {describe_direction(trend_directions['commit'])} over the same period."
        ),
        (
            "Available populated intervals suggest concurrency "
            f"{describe_sparse_direction(trend_directions['concurrency'])}."
            if is_sparse_series("concurrency_trend")
            else f"Concurrency {describe_direction(trend_directions['concurrency'])} across the interval series."
        ),
        (
            "Top SQL concentration remained effectively unchanged across the "
            "analysis window, indicating a persistent concentrated SQL footprint rather than an episodic spike."
            if trend_directions["sql_concentration"] == "stable"
            else (
                "Top SQL concentration "
                f"{describe_direction(trend_directions['sql_concentration'])} over the analysis window."
            )
        ),
    ]

    if trend_directions["hard_parses"] != "insufficient history":
        findings.append(
            "Hard parses/s "
            f"{describe_direction(trend_directions['hard_parses'])} over the analysis window."
        )

    if any(value is not None for value in time_series["cluster_wait_trend"]):
        if is_sparse_series("cluster_wait_trend"):
            findings.append(
                "Sparse populated intervals suggest cluster waits "
                f"{describe_sparse_direction(trend_directions['cluster_wait'])}."
            )
        else:
            findings.append(
                "Cluster waits "
                f"{describe_direction(trend_directions['cluster_wait'])} over the analysis window."
            )
    if any(value is not None for value in time_series["gc_wait_trend"]):
        if is_sparse_series("gc_wait_trend"):
            findings.append(
                "Sparse populated intervals suggest combined GC wait pressure, defined as GC Current + GC CR, "
                f"{describe_sparse_direction(trend_directions['gc_wait'])}."
            )
        else:
            findings.append(
                "Combined GC wait pressure, defined as GC Current + GC CR, "
                f"{describe_direction(trend_directions['gc_wait'])} across the interval series."
            )
    if any(value is not None for value in time_series["dg_transport_lag_trend"]):
        findings.append(
            "Data Guard transport lag "
            f"{describe_direction(trend_directions['dg_transport_lag'])} across the analysis window."
        )
    if any(value is not None for value in time_series["dg_apply_lag_trend"]):
        findings.append(
            "Data Guard apply lag "
            f"{describe_direction(trend_directions['dg_apply_lag'])} over the same period."
        )
    if any(value is not None for value in time_series["exa_cell_io_trend"]):
        findings.append(
            "Exadata cell-wait pressure "
            f"{describe_direction(trend_directions['exa_cell_io'])} across the interval series."
        )
    if any(value is not None for value in time_series["exa_offload_efficiency_trend"]):
        offload_direction = trend_directions["exa_offload_efficiency"]
        if offload_direction == "stable":
            findings.append(
                "Exadata offload efficiency remained materially present across "
                "the analysis window, indicating that smart-scan benefits were "
                "persistent rather than episodic."
            )
        else:
            findings.append(
                "Exadata offload efficiency "
                f"{describe_direction(offload_direction)} over the analysis window."
            )

    return findings


def _average_metric(values: list[float | None]) -> float | None:
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return round(sum(numeric_values) / len(numeric_values), 4)


def _latest_non_null(values: list[float | None]) -> float | None:
    for value in reversed(values):
        if value is not None:
            return value
    return None


def _format_interval_evidence_label(snapshot_count: int) -> str:
    if snapshot_count > 1:
        return (
            "Latest interval deterministic evidence below shows how the most "
            "recent interval supports the broader multi-snapshot conclusion above."
        )
    return "Supporting evidence below reflects latest-interval deterministic metrics."


def _build_topology_assessment(context: dict[str, Any]) -> str | None:
    topology = context.get("topology") or {}
    statements: list[str] = []
    if topology.get("is_rac"):
        cluster_wait = _format_metric(
            context["metrics"].get("cluster_wait_pct_db_time"),
            "%",
        )
        gc_wait = _format_metric(
            context["metrics"].get("gc_total_wait_pct_db_time"),
            "%",
        )
        statements.append(
            "Topology assessment indicates RAC behavior is present"
            + (
                f", with cluster waits at {cluster_wait} and combined GC "
                f"current + GC CR wait pressure at {gc_wait} of DB time."
                if (
                    context["metrics"].get("cluster_wait_pct_db_time") is not None
                    or context["metrics"].get("gc_total_wait_pct_db_time") is not None
                )
                else "."
            )
        )
    if topology.get("is_dataguard"):
        role = str(topology.get("database_role") or "UNKNOWN")
        transport_lag = context["metrics"].get("transport_lag_sec")
        apply_lag = context["metrics"].get("apply_lag_sec")
        lag_parts: list[str] = []
        if transport_lag is not None:
            lag_parts.append(f"transport lag is {_format_metric(transport_lag, 's')}")
        if apply_lag is not None:
            lag_parts.append(f"apply lag is {_format_metric(apply_lag, 's')}")
        lag_text = (", with " + " and ".join(lag_parts) + ".") if lag_parts else "."
        if role == "UNKNOWN":
            statements.append(
                "Data Guard behavior is present, but the report does not state a definitive database role"
                + lag_text
            )
        else:
            statements.append(f"Data Guard role is {role}{lag_text}")
    if topology.get("is_exadata"):
        offload = context["metrics"].get("exa_offload_efficiency")
        cell_wait = context["metrics"].get("exa_cell_io_pct_db_time")
        statements.append(
            "Platform assessment indicates Exadata behavior is present"
            + (
                f", with cell-related waits at {_format_metric(cell_wait, '%')} and "
                f"offload efficiency at {_format_metric((offload or 0.0) * 100.0, '%')}."
                if offload is not None or cell_wait is not None
                else "."
            )
        )
    if topology.get("operational_event_class") not in {None, "NONE"}:
        statements.append(
            "Operational event classification is "
            f"{_humanize_classification(topology['operational_event_class'])}."
        )
    if not statements:
        return None
    return " ".join(statements)


def _build_topology_window_summary(
    multi_snapshot_analysis: dict[str, Any],
) -> str | None:
    snapshot_contexts = multi_snapshot_analysis["ordered_snapshots"]
    time_series = multi_snapshot_analysis["time_series"]

    has_rac = any(
        (context.get("topology") or {}).get("is_rac") for context in snapshot_contexts
    )
    has_dataguard = any(
        (context.get("topology") or {}).get("is_dataguard")
        for context in snapshot_contexts
    )
    has_exadata = any(
        (context.get("topology") or {}).get("is_exadata")
        for context in snapshot_contexts
    )
    unique_event_classes = _collect_event_classes(snapshot_contexts)
    parts: list[str] = []

    if unique_event_classes:
        parts.append(
            "The window includes operational-event phases such as "
            + ", ".join(
                _humanize_classification(event_class)
                for event_class in unique_event_classes
            )
            + "."
        )
    elif any(
        (context.get("topology") or {}).get("interconnect_stress_flag")
        for context in snapshot_contexts
    ):
        parts.append(
            "The window includes deterministic interconnect-stress phases even "
            "though no failover-style event classification was recorded."
        )
    if has_rac:
        cluster_avg = _average_metric(time_series.get("cluster_wait_trend", []))
        gc_avg = _average_metric(time_series.get("gc_wait_trend", []))
        parts.append(
            "RAC behavior is present across the window"
            + (
                f", with cluster waits averaging "
                f"{_format_metric(cluster_avg, '%')} and combined GC current "
                f"+ GC CR wait pressure averaging {_format_metric(gc_avg, '%')}."
                if cluster_avg is not None or gc_avg is not None
                else "."
            )
        )
    if has_dataguard:
        role = _summarize_database_role(snapshot_contexts)
        transport_avg = _average_metric(time_series.get("dg_transport_lag_trend", []))
        apply_avg = _average_metric(time_series.get("dg_apply_lag_trend", []))
        if transport_avg is None and apply_avg is None:
            if role == "Unknown":
                parts.append(
                    "Data Guard behavior is present, but the report does not "
                    "state a definitive role and no explicit transport/apply "
                    "lag values were available across the window."
                )
            else:
                parts.append(
                    f"Data Guard role is {role}, but explicit transport/apply "
                    "lag values were unavailable across the window."
                )
        elif role == "Unknown":
            parts.append(
                "Data Guard behavior is present, but the report does not state a definitive role"
                + (
                    f"; transport lag averages "
                    f"{_format_metric(transport_avg, 's')} and apply lag "
                    f"averages {_format_metric(apply_avg, 's')}."
                    if transport_avg is not None or apply_avg is not None
                    else "."
                )
            )
        else:
            parts.append(
                f"Data Guard role is {role}"
                + (
                    f", with transport lag averaging "
                    f"{_format_metric(transport_avg, 's')} and apply lag "
                    f"averaging {_format_metric(apply_avg, 's')}."
                    if transport_avg is not None or apply_avg is not None
                    else "."
                )
            )
    if has_exadata:
        cell_avg = _average_metric(time_series.get("exa_cell_io_trend", []))
        parts.append(
            "Exadata behavior is present across the window"
            + (
                f", with cell-related waits averaging {_format_metric(cell_avg, '%')} of DB time."
                if cell_avg is not None
                else "."
            )
        )
    if not parts:
        return None
    return " ".join(parts)


def _build_topology_narrative_sections(
    multi_snapshot_analysis: dict[str, Any],
) -> list[str]:
    latest_snapshot = multi_snapshot_analysis["latest_snapshot"]
    topology = latest_snapshot.get("topology") or {}
    metrics = latest_snapshot.get("metrics") or {}
    sections: list[str] = []
    summary = _build_topology_window_summary(multi_snapshot_analysis)
    if summary:
        sections.extend(["Topology Assessment", summary])
    if topology.get("is_rac"):
        sections.extend(
            [
                "RAC / Cluster Findings",
                (
                    "RAC evidence is explicitly present, with cluster waits at "
                    f"{_format_metric(metrics.get('cluster_wait_pct_db_time'), '%')} "
                    "and combined GC current + GC CR wait pressure at "
                    f"{_format_metric(metrics.get('gc_total_wait_pct_db_time'), '%')} "
                    "in the latest interval. Those signals should be "
                    "interpreted as cluster coordination behavior rather than "
                    "as a generic single-instance bottleneck."
                ),
            ]
        )
    if (
        topology.get("is_dataguard")
        or metrics.get("transport_lag_sec") is not None
        or metrics.get("apply_lag_sec") is not None
    ):
        sections.extend(
            [
                "Data Guard Findings",
                (
                    _format_dataguard_evidence_phrase(
                        metrics.get("transport_lag_sec"),
                        metrics.get("apply_lag_sec"),
                        topology.get("database_role"),
                    )
                    + " Those values should be interpreted as "
                    "replication-state evidence rather than generic CPU or I/O "
                    "pressure."
                ),
            ]
        )
    if topology.get("is_exadata"):
        sections.extend(
            [
                "Exadata Findings",
                (
                    "Exadata-specific behavior is present, with cell-related waits at "
                    f"{_format_metric(metrics.get('exa_cell_io_pct_db_time'), '%')} and "
                    f"offload efficiency at "
                    f"{_format_metric((metrics.get('exa_offload_efficiency') or 0.0) * 100.0, '%')}. "
                    "That means storage behavior should be interpreted through "
                    "smart-scan/offload effects rather than generic storage "
                    "assumptions."
                ),
            ]
        )
    if topology.get("operational_event_class") not in {None, "NONE"}:
        sections.extend(
            [
                "Operational Event Interpretation",
                (
                    "Operational event classification is "
                    f"{_humanize_classification(str(topology.get('operational_event_class')))}, "
                    "so the latest interval should be read in the context of "
                    "topology transition behavior as well as workload behavior."
                ),
            ]
        )
    elif topology.get("interconnect_stress_flag"):
        sections.extend(
            [
                "Operational Event Interpretation",
                (
                    "Deterministic topology evidence flags interconnect stress in the latest interval, "
                    "so cluster communication efficiency is part of the "
                    "interpretation even without a failover-style event "
                    "classification."
                ),
            ]
        )
    return sections


def _build_latest_interval_interpretation(context: dict[str, Any]) -> str:
    metrics = context["metrics"]
    topology = context.get("topology") or {}
    issue_types = {
        str(issue.get("issue_type") or "")
        for issue in _get_compatibility_issues(context)
    }
    statements = [
        (
            f"CPU remained the primary driver in this interval at "
            f"{_format_metric(metrics.get('cpu_pct'), '%')} of DB time."
        )
    ]
    if "sql_concentration" in issue_types:
        statements.append(
            (
                "SQL concentration remained material, indicating that a small "
                "set of statements still accounted for a disproportionate share "
                "of work in the current interval."
            )
        )
    if "io_pressure" in issue_types:
        statements.append(
            (
                f"User I/O remained visible at {_format_metric(metrics.get('user_io_pct'), '%')}, "
                "keeping access-path efficiency in scope for this interval."
            )
        )
    if "commit_pressure" in issue_types:
        statements.append(
            (
                f"Commit pressure remained visible at {_format_metric(metrics.get('commit_pct'), '%')}, "
                "which keeps transaction behavior in scope for the current interval."
            )
        )
    if "concurrency_pressure" in issue_types:
        statements.append(
            (
                f"Concurrency contributed {_format_metric(metrics.get('concurrency_pct'), '%')} "
                "of DB time in this interval, but it was not the leading driver."
            )
        )
    if topology.get("is_rac"):
        statements.append(
            (
                "RAC coordination is also part of the current-interval "
                "picture, with cluster waits at "
                f"{_format_metric(metrics.get('cluster_wait_pct_db_time'), '%')} "
                "and combined GC current + GC CR wait pressure at "
                f"{_format_metric(metrics.get('gc_total_wait_pct_db_time'), '%')}."
            )
        )
    if (
        topology.get("is_dataguard")
        or metrics.get("transport_lag_sec") is not None
        or metrics.get("apply_lag_sec") is not None
    ):
        statements.append(
            _format_dataguard_evidence_phrase(
                metrics.get("transport_lag_sec"),
                metrics.get("apply_lag_sec"),
                topology.get("database_role"),
            )
        )
    if topology.get("is_exadata"):
        statements.append(
            (
                "Exadata-specific execution paths are present in the current interval, with cell-related waits at "
                f"{_format_metric(metrics.get('exa_cell_io_pct_db_time'), '%')} and "
                f"offload efficiency at {_format_metric((metrics.get('exa_offload_efficiency') or 0.0) * 100.0, '%')}."
            )
        )
    if topology.get("operational_event_class") not in {None, "NONE"}:
        statements.append(
            "This interval also sits inside "
            + _humanize_classification(str(topology.get("operational_event_class")))
            + "."
        )
    elif topology.get("interconnect_stress_flag"):
        statements.append(
            "This interval also carries deterministic interconnect-stress evidence."
        )
    return " ".join(statements)


def _build_analysis_context(
    snapshot_contexts: list[dict[str, Any]],
) -> dict[str, str]:
    first_context = snapshot_contexts[0]
    latest_context = snapshot_contexts[-1]
    analysis_start = first_context.get("begin_time") or first_context.get("end_time")
    analysis_end = latest_context.get("end_time") or latest_context.get("begin_time")
    latest_label = _format_interval_display(
        latest_context.get("begin_time"),
        latest_context.get("end_time"),
    )
    metadata = latest_context["result"].run_metadata
    latest_topology = latest_context.get("topology") or {}
    topology_detected = ", ".join(_collect_topology_labels(snapshot_contexts))
    platform_detected = ", ".join(_collect_platform_labels(snapshot_contexts))
    database_role = _summarize_database_role(snapshot_contexts)

    observed_hostnames = list(
        dict.fromkeys(
            str((context["result"].run_metadata.host_name or "")).strip()
            for context in snapshot_contexts
            if str((context["result"].run_metadata.host_name or "")).strip()
        )
    )
    observed_platforms = list(
        dict.fromkeys(
            str((context["result"].run_metadata.platform or "")).strip()
            for context in snapshot_contexts
            if str((context["result"].run_metadata.platform or "")).strip()
        )
    )
    observed_versions = list(
        dict.fromkeys(
            str((context["result"].run_metadata.db_version or "")).strip()
            for context in snapshot_contexts
            if str((context["result"].run_metadata.db_version or "")).strip()
        )
    )
    db_name = str(metadata.database_name or "").strip()
    db_id = str(metadata.db_id or "").strip()
    db_identity_parts = []
    if db_name:
        db_identity_parts.append(db_name)
    if db_id:
        db_identity_parts.append(f"DBID {db_id}")
    db_identity = " | ".join(db_identity_parts) or "Unavailable"

    if not observed_hostnames:
        hostname = "Unknown"
    elif len(observed_hostnames) <= 2:
        hostname = " | ".join(observed_hostnames)
    else:
        hostname = " | ".join(
            observed_hostnames[:2] + [f"+{len(observed_hostnames) - 2} more"]
        )
    operating_system = (
        " | ".join(observed_platforms) if observed_platforms else "Unknown"
    )
    if not observed_versions:
        db_version = "Unknown"
    elif len(observed_versions) == 1:
        db_version = observed_versions[0]
    else:
        db_version = " | ".join(observed_versions)

    instance_count = latest_topology.get("instance_count")
    if not isinstance(instance_count, (int, float)):
        observed_instances = {
            str((context["result"].run_metadata.instance_name or "")).strip()
            for context in snapshot_contexts
            if str((context["result"].run_metadata.instance_name or "")).strip()
        }
        instance_count = len(observed_instances) if observed_instances else None
    normalized_instance_count = (
        int(instance_count) if isinstance(instance_count, (int, float)) else None
    )

    host_capacity_by_name: dict[str, dict[str, float | None]] = {}
    for context in snapshot_contexts:
        run_metadata = context["result"].run_metadata
        host_key = str(run_metadata.host_name or "").strip()
        if not host_key:
            continue
        host_capacity_by_name[host_key] = {
            "cpu_count": (
                float(run_metadata.cpu_count)
                if isinstance(run_metadata.cpu_count, (int, float))
                else None
            ),
            "core_count": (
                float(run_metadata.core_count)
                if isinstance(run_metadata.core_count, (int, float))
                else None
            ),
            "memory_gb": (
                float(run_metadata.memory_gb)
                if isinstance(run_metadata.memory_gb, (int, float))
                else None
            ),
        }

    observed_host_count = len(host_capacity_by_name)
    latest_cpu_count = (
        float(metadata.cpu_count)
        if isinstance(metadata.cpu_count, (int, float))
        else None
    )
    latest_core_count = (
        float(metadata.core_count)
        if isinstance(metadata.core_count, (int, float))
        else None
    )
    latest_memory_gb = (
        float(metadata.memory_gb)
        if isinstance(metadata.memory_gb, (int, float))
        else None
    )

    cumulative_core_total = None
    cumulative_cpu_total = None
    if host_capacity_by_name:
        core_values = [
            numeric_value
            for value in host_capacity_by_name.values()
            if (numeric_value := _safe_float(value.get("core_count"))) is not None
        ]
        cpu_values = [
            numeric_value
            for value in host_capacity_by_name.values()
            if (numeric_value := _safe_float(value.get("cpu_count"))) is not None
        ]
        if core_values and observed_host_count:
            cumulative_core_total = sum(core_values)
        if cpu_values and observed_host_count:
            cumulative_cpu_total = sum(cpu_values)
    if normalized_instance_count and normalized_instance_count > max(
        observed_host_count, 1
    ):
        if latest_core_count is not None:
            cumulative_core_total = latest_core_count * normalized_instance_count
        elif latest_cpu_count is not None:
            cumulative_cpu_total = latest_cpu_count * normalized_instance_count

    if cumulative_core_total is not None:
        ocpus_cores = (
            f"{int(cumulative_core_total)} cores"
            if float(cumulative_core_total).is_integer()
            else f"{cumulative_core_total:.1f} cores"
        )
    elif cumulative_cpu_total is not None:
        ocpus_cores = (
            f"{int(cumulative_cpu_total)} CPUs"
            if float(cumulative_cpu_total).is_integer()
            else f"{cumulative_cpu_total:.1f} CPUs"
        )
    else:
        ocpus_cores = "Unknown"

    memory_values = [
        numeric_value
        for value in host_capacity_by_name.values()
        if (numeric_value := _safe_float(value.get("memory_gb"))) is not None
    ]
    if not memory_values and latest_memory_gb is not None:
        memory_values = [latest_memory_gb]
    unique_memory_values = sorted({round(value, 2) for value in memory_values})
    if not unique_memory_values:
        memory_per_instance = "Unknown"
    elif len(unique_memory_values) == 1:
        memory_value = unique_memory_values[0]
        memory_per_instance = (
            f"{int(memory_value)} GB"
            if float(memory_value).is_integer()
            else f"{memory_value:.1f} GB"
        )
    else:
        low_memory = unique_memory_values[0]
        high_memory = unique_memory_values[-1]
        low_text = (
            str(int(low_memory))
            if float(low_memory).is_integer()
            else f"{low_memory:.1f}"
        )
        high_text = (
            str(int(high_memory))
            if float(high_memory).is_integer()
            else f"{high_memory:.1f}"
        )
        memory_per_instance = f"{low_text}-{high_text} GB"

    snapshot_count = _count_canonical_reports(snapshot_contexts)
    time_window = _format_duration(analysis_start, analysis_end)

    return {
        "snapshot_count": str(snapshot_count),
        "analysis_start": _format_datetime_display(analysis_start),
        "analysis_end": _format_datetime_display(analysis_end),
        "time_window": time_window,
        "awr_count_and_window": f"{snapshot_count} / {time_window}",
        "latest_snapshot_interval": latest_label,
        "topology_detected": topology_detected,
        "platform_detected": platform_detected,
        "database_role": database_role,
        "db_version": db_version,
        "ocpus_cores": ocpus_cores,
        "memory_per_instance": memory_per_instance,
        "operating_system": operating_system,
        "source_database": db_identity,
        "hostname": hostname,
        "instance_count": (
            str(normalized_instance_count) if normalized_instance_count else "Unknown"
        ),
    }


def _count_canonical_reports(
    snapshot_contexts: list[dict[str, Any]],
) -> int:
    """Count canonical logical AWR reports within the current dashboard scope."""

    canonical_keys: set[tuple[Any, ...]] = set()
    for context in snapshot_contexts:
        run_metadata = context["result"].run_metadata
        db_id = str(run_metadata.db_id or "").strip() or None
        instance_number = str(run_metadata.instance_number or "").strip() or None
        snap_id_begin = getattr(run_metadata, "snap_id_begin", None)
        snap_id_end = getattr(run_metadata, "snap_id_end", None)
        begin_time = context.get("begin_time")
        end_time = context.get("end_time")

        if (
            db_id is not None
            and instance_number is not None
            and snap_id_begin is not None
            and snap_id_end is not None
            and begin_time is not None
            and end_time is not None
        ):
            canonical_key = (
                "logical_snapshot",
                db_id,
                instance_number,
                int(snap_id_begin),
                int(snap_id_end),
                begin_time.isoformat(),
                end_time.isoformat(),
            )
        else:
            canonical_key = (
                "selected_file",
                str(context.get("file_path") or context.get("file_name") or ""),
            )

        canonical_keys.add(canonical_key)

    return len(canonical_keys)


def _severity_score(severity: str) -> int:
    return {"high": 3, "medium": 2, "low": 1}.get(severity.lower(), 0)


def _snapshot_score(context: dict[str, Any]) -> float:
    issues = _get_compatibility_issues(context)
    metrics = context["metrics"]
    severity_points = sum(
        _severity_score(str(issue.get("severity") or "")) for issue in issues
    )
    numeric_signals = [
        metrics.get("cpu_pct") or 0.0,
        metrics.get("user_io_pct") or 0.0,
        metrics.get("commit_pct") or 0.0,
        metrics.get("concurrency_pct") or 0.0,
        metrics.get("top_sql_concentration") or 0.0,
    ]
    return severity_points * 10.0 + sum(numeric_signals)


def _build_latest_snapshot_summary(context: dict[str, Any]) -> str:
    metrics = context["metrics"]
    latest_metrics_sentence = (
        f"Latest snapshot ({context['snapshot_label']}) metrics: "
        f"CPU {_format_metric(metrics.get('cpu_pct'), '%')}, "
        f"User I/O {_format_metric(metrics.get('user_io_pct'), '%')}, "
        f"commit {_format_metric(metrics.get('commit_pct'), '%')}, "
        f"concurrency {_format_metric(metrics.get('concurrency_pct'), '%')}, and "
        "Top SQL concentration (top 3 share) "
        f"{_format_metric(metrics.get('top_sql_concentration'), '%')}."
    )
    interpretation = _build_latest_interval_interpretation(context)
    return f"{latest_metrics_sentence} {interpretation}"


def _build_multi_snapshot_summary(
    snapshot_contexts: list[dict[str, Any]],
    time_series: dict[str, Any],
    anomaly_windows: list[dict[str, Any]],
    latest_snapshot_summary: str,
) -> str:
    if len(snapshot_contexts) < 2:
        return (
            "Only one snapshot is available, so the analysis remains specific "
            "to the current interval. Historical trend and anomaly detection "
            "are limited by single-interval history."
        )

    latest_context = snapshot_contexts[-1]
    worst_context = max(snapshot_contexts, key=_snapshot_score)
    trend_findings = _build_trend_findings(time_series)
    anomaly_text = (
        "No deterministic anomaly or event windows were detected."
        if not anomaly_windows
        else (
            f"{len(anomaly_windows)} anomaly/event window(s) were detected, led by "
            f"{anomaly_windows[0]['metric']} in "
            f"{anomaly_windows[0]['snapshot_label']}."
        )
    )

    paragraph_one = " ".join(
        [
            f"{len(snapshot_contexts)} snapshots were analyzed in chronological order.",
            (
                f"Across the full window, the workload remained primarily CPU-led, "
                "with multi-snapshot summary values of average CPU "
                f"{_format_metric(_average_metric(time_series['cpu_trend']), '%')}, "
                "average User I/O "
                f"{_format_metric(_average_metric(time_series['io_trend']), '%')}, "
                "and average Top SQL concentration (top 3 share) "
                f"{_format_metric(_average_metric(time_series['sql_concentration_trend']), '%')}. "
                "The same broad workload "
                "shape persisted throughout the series rather than rotating between unrelated bottlenecks."
            ),
        ]
    )
    paragraph_two = " ".join(
        [
            (
                f"The worst pressure interval was {worst_context['snapshot_label']}, "
                f"while the latest interval was {latest_context['snapshot_label']}."
            ),
            anomaly_text,
            " ".join(trend_findings),
        ]
    )
    paragraph_three = " ".join(
        [
            (
                "The broader picture remains more important than any single interval: "
                "the latest snapshot should be read as confirmation, moderation, or "
                "departure from that pattern rather than as the full story by itself."
            ),
            _build_topology_window_summary(
                {
                    "ordered_snapshots": snapshot_contexts,
                    "latest_snapshot": latest_context,
                    "time_series": time_series,
                }
            )
            or "",
            (
                "Detailed latest-interval metrics are shown separately in the "
                "Latest Snapshot Assessment."
            ),
        ]
    )
    return "\n\n".join([paragraph_one, paragraph_two, paragraph_three])


def _build_multi_snapshot_executive_summary(
    multi_snapshot_analysis: dict[str, Any],
) -> str:
    snapshot_count = len(multi_snapshot_analysis["ordered_snapshots"])
    posture = multi_snapshot_analysis["decision_posture"]
    time_series = multi_snapshot_analysis["time_series"]
    latest_cpu = _latest_non_null(time_series["cpu_trend"])
    latest_io = _latest_non_null(time_series["io_trend"])
    latest_sql = _latest_non_null(time_series["sql_concentration_trend"])
    if snapshot_count < 2:
        return " ".join(
            [
                f"{posture['posture']}: {posture['rationale']}",
                (
                    f"The single available interval shows latest-snapshot CPU at "
                    f"{_format_metric(latest_cpu, '%')}, User I/O at "
                    f"{_format_metric(latest_io, '%')}, and Top SQL concentration (top 3 share) "
                    f"at {_format_metric(latest_sql, '%')}."
                ),
                (
                    "With no broader history available, the posture is anchored to "
                    "that interval alone rather than to trend confirmation."
                ),
                "The latest-interval evidence below shows why that interval-level posture was chosen.",
            ]
        )
    return _build_executive_summary_rationale(multi_snapshot_analysis)


def _build_confidence(
    snapshot_contexts: list[dict[str, Any]],
    anomaly_windows: list[dict[str, Any]],
    time_series: dict[str, Any],
) -> dict[str, str]:
    snapshot_count = len(snapshot_contexts)
    non_insufficient = sum(
        1
        for direction in time_series["trend_directions"].values()
        if direction != "insufficient history"
    )
    latest_context = snapshot_contexts[-1]
    latest_issue_strength = sum(
        _severity_score(str(issue.get("severity") or ""))
        for issue in _get_compatibility_issues(latest_context)
    )
    io_direction = time_series["trend_directions"]["io"]
    commit_direction = time_series["trend_directions"]["commit"]
    latest_cpu = _latest_non_null(time_series["cpu_trend"])
    latest_sql = _latest_non_null(time_series["sql_concentration_trend"])
    latest_topology = snapshot_contexts[-1].get("topology") or {}
    pattern_phrase = (
        f"Across {snapshot_count} snapshots, CPU remained the dominant repeated signal"
        if snapshot_count > 1
        else "Only one snapshot is available"
    )
    if io_direction == commit_direction:
        trend_phrase = f"User I/O and commit pressure both followed a {io_direction} pattern over the same window"
    else:
        trend_phrase = (
            f"User I/O followed a {io_direction} pattern while commit "
            f"pressure followed a {commit_direction} pattern over the same "
            "window"
        )
    anomaly_phrase = (
        "The observed anomalies were isolated rather than persistent"
        if len(anomaly_windows) <= 1
        else "Multiple anomaly windows recur across the history"
    )
    latest_phrase = (
        "The latest interval stays aligned with that broader picture, with "
        f"CPU at {_format_metric(latest_cpu, '%')} and Top SQL concentration "
        f"(top 3 share) at {_format_metric(latest_sql, '%')}."
        if latest_cpu is not None or latest_sql is not None
        else "The latest interval does not contradict the broader pattern."
    )
    topology_phrase = ""
    if latest_topology.get("is_rac"):
        topology_phrase = (
            " RAC coordination signals, including combined GC current + GC CR "
            "waits, were interpreted as topology evidence rather than generic "
            "CPU pressure."
        )
    elif latest_topology.get("is_dataguard"):
        topology_phrase = (
            " Data Guard role and replication-state evidence are explicitly "
            "present and were interpreted separately from generic workload "
            "pressure."
        )
    elif latest_topology.get("is_exadata"):
        topology_phrase = (
            " Exadata-specific cell/offload evidence is explicitly present and "
            "was interpreted as platform behavior rather than generic storage "
            "pressure."
        )

    if (
        snapshot_count >= 4
        and non_insufficient >= 4
        and (anomaly_windows or latest_issue_strength >= 3)
    ):
        return {
            "level": "HIGH",
            "reason": (
                f"{pattern_phrase}. {trend_phrase}. {anomaly_phrase}. "
                f"{latest_phrase}{topology_phrase} Taken together, the "
                "repeated dominant pattern, the isolated anomaly behavior, "
                "and the latest interval all reinforce the same posture with "
                "very little contradiction."
            ),
        }
    if snapshot_count >= 2 and non_insufficient >= 2:
        return {
            "level": "MEDIUM",
            "reason": (
                f"{pattern_phrase}. {trend_phrase}. {anomaly_phrase}. "
                f"{latest_phrase}{topology_phrase} The posture is credible "
                "overall because the broader pattern and the latest interval "
                "still point in the same direction, even though some signals "
                "carry more weight than others."
            ),
        }
    return {
        "level": "LOW",
        "reason": (
            "Only one interval is available, so the posture rests on a clear "
            "latest-snapshot pattern rather than on repeated confirmation over time."
        ),
    }


def _build_root_cause_interpretation(
    latest_context: dict[str, Any],
    multi_snapshot_analysis: dict[str, Any],
) -> str:
    metrics = latest_context["metrics"]
    issues = _get_compatibility_issues(latest_context)
    topology = latest_context.get("topology") or {}
    issue_types = {str(issue.get("issue_type") or "") for issue in issues}
    dominant_user_io = (
        _dominant_wait_event(
            latest_context["result"],
            "User I/O",
        )
        or "single-block read activity"
    )
    module_text = (
        _top_sql_module_name(latest_context["result"])
        or "the dominant application module"
    )
    concurrency_text = (
        f"Concurrency is secondary at {_format_metric(metrics.get('concurrency_pct'), '%')} of DB time."
        if metrics.get("concurrency_pct") and metrics.get("concurrency_pct", 0) >= 5.0
        else "Concurrency is not currently a material driver."
    )
    posture = multi_snapshot_analysis["decision_posture"]["posture"]
    root_cause_sentences = [
        (
            "CPU pressure is the primary constraint, with the latest interval "
            f"still showing DB CPU at {_format_metric(metrics.get('cpu_pct'), '%')} "
            "of DB time."
        ),
        (
            f"SQL concentration remains material in {module_text}, with the leading "
            f"three statements accounting for {_format_metric(metrics.get('top_sql_concentration'), '%')} "
            "of elapsed SQL time in the latest snapshot."
        ),
        (
            f"User I/O is still present and is led by {dominant_user_io}, which is "
            "more consistent with access-path and single-block read pressure than "
            "with a broad platform-wide capacity ceiling."
        ),
    ]
    if "commit_pressure" in issue_types or (metrics.get("commit_pct") or 0) >= 5.0:
        root_cause_sentences.append(
            (
                "Commit pressure is also visible through log file sync behavior, "
                "keeping transaction design and commit frequency in scope."
            )
        )
    if topology.get("is_rac"):
        root_cause_sentences.append(
            (
                "RAC topology is part of the story, with cluster waits at "
                f"{_format_metric(metrics.get('cluster_wait_pct_db_time'), '%')} "
                "and combined GC current + GC CR wait pressure at "
                f"{_format_metric(metrics.get('gc_total_wait_pct_db_time'), '%')} "
                "of DB time, so cross-instance coordination should be interpreted "
                "separately from generic single-instance CPU pressure."
            )
        )
    if topology.get("is_dataguard"):
        root_cause_sentences.append(
            (
                _format_dataguard_evidence_phrase(
                    metrics.get("transport_lag_sec"),
                    metrics.get("apply_lag_sec"),
                    topology.get("database_role"),
                )
                + " That points to replication health or transition state "
                "rather than to a simple workload shortfall."
            )
        )
    if topology.get("is_exadata"):
        root_cause_sentences.append(
            (
                "Exadata behavior is also present, with cell-related waits at "
                f"{_format_metric(metrics.get('exa_cell_io_pct_db_time'), '%')} and "
                f"offload efficiency at "
                f"{_format_metric((metrics.get('exa_offload_efficiency') or 0.0) * 100.0, '%')}. "
                "Those signals should be interpreted as engineered-system "
                "behavior rather than generic storage pressure."
            )
        )
    root_cause_sentences.append(concurrency_text)
    root_cause_sentences.append(
        (
            f"Together these drivers support {posture} because they point first to "
            "tunable workload behavior, topology state, and platform-specific "
            "execution paths rather "
            "than to an immediate need for capacity expansion."
        )
    )
    return " ".join(root_cause_sentences)


def _build_executive_summary_rationale(
    multi_snapshot_analysis: dict[str, Any],
) -> str:
    snapshot_count = len(multi_snapshot_analysis["ordered_snapshots"])
    posture = multi_snapshot_analysis["decision_posture"]
    time_series = multi_snapshot_analysis["time_series"]
    latest_snapshot = multi_snapshot_analysis["latest_snapshot"]
    anomaly_windows = multi_snapshot_analysis["anomaly_windows"]
    avg_cpu = _average_metric(time_series["cpu_trend"])
    avg_io = _average_metric(time_series["io_trend"])
    avg_sql = _average_metric(time_series["sql_concentration_trend"])
    latest_cpu = _latest_non_null(time_series["cpu_trend"])
    latest_io = _latest_non_null(time_series["io_trend"])
    latest_sql = _latest_non_null(time_series["sql_concentration_trend"])
    snapshot_contexts = multi_snapshot_analysis["ordered_snapshots"]
    latest_topology = latest_snapshot.get("topology") or {}
    unique_event_classes = _collect_event_classes(snapshot_contexts)
    topology_labels = _collect_topology_labels(snapshot_contexts)
    platform_labels = _collect_platform_labels(snapshot_contexts)

    if snapshot_count < 2:
        return (
            f"{posture['posture']}: the current snapshot shows CPU at "
            f"{_format_metric(latest_cpu, '%')}, User I/O at "
            f"{_format_metric(latest_io, '%')}, and Top SQL concentration "
            f"(top 3 share) at {_format_metric(latest_sql, '%')}. "
            "No historical trend is available, so this posture is anchored to "
            "the current interval alone. "
            "The latest-interval evidence below explains why that single-snapshot conclusion was chosen."
        )

    first_sentence = (
        f"Across the full {snapshot_count}-snapshot window, the workload "
        "remained predominantly CPU-led, "
        f"with average CPU at {_format_metric(avg_cpu, '%')}, average User "
        f"I/O at {_format_metric(avg_io, '%')}, and average Top SQL "
        f"concentration (top 3 share) at {_format_metric(avg_sql, '%')}."
    )

    topology_text = _join_readable_labels(topology_labels)
    platform_text = _join_readable_labels(
        [label for label in platform_labels if label != "Generic"]
    )
    has_rac = "RAC" in topology_labels
    has_dataguard = "Data Guard" in topology_labels
    if has_rac and platform_text:
        second_sentence = f"The window spans RAC on {platform_text}"
        if has_dataguard:
            second_sentence += " and includes Data Guard behavior"
    elif topology_text and platform_text:
        second_sentence = f"The window spans {topology_text} on {platform_text}"
    elif topology_text:
        second_sentence = f"The window spans {topology_text}"
    elif platform_text:
        second_sentence = f"The window reflects {platform_text} platform behavior"
    else:
        second_sentence = (
            "Topology and platform state remain part of the interpretation"
        )

    if unique_event_classes:
        transition_events = [
            event_class
            for event_class in unique_event_classes
            if event_class
            in {
                "FAILOVER_EVENT",
                "ROLE_TRANSITION",
                "POST_FAILOVER_RECOVERY",
            }
        ]
        if transition_events:
            transition_phrase = (
                "Data Guard transition behavior"
                if has_dataguard
                else "topology transition behavior"
            )
            if has_dataguard and "Data Guard behavior" in second_sentence:
                second_sentence = second_sentence.replace(
                    "Data Guard behavior",
                    "Data Guard transition behavior",
                )
            else:
                second_sentence += f" and includes {transition_phrase}"
        else:
            second_sentence += (
                " and includes "
                + _join_readable_labels(
                    [
                        _humanize_classification(event_class)
                        for event_class in unique_event_classes
                    ]
                ).lower()
            )
    elif anomaly_windows:
        lead_window = anomaly_windows[0]
        lead_metric = str(lead_window.get("metric") or "deterministic event")
        if lead_window.get("anomaly_type") == "topology_event":
            second_sentence += (
                f", with the most material deterministic window occurring as "
                f"{lead_metric} in {lead_window['snapshot_label']}"
            )
        else:
            second_sentence += (
                f", with the most material deterministic window occurring as "
                f"the {lead_metric} spike in {lead_window['snapshot_label']}"
            )
    second_sentence += "."

    latest_state_parts: list[str] = []
    if latest_topology.get("is_exadata") and latest_topology.get("is_rac"):
        latest_state_parts.append("RAC on Exadata")
    else:
        if latest_topology.get("is_rac"):
            latest_state_parts.append("RAC")
        if latest_topology.get("is_exadata"):
            latest_state_parts.append("Exadata behavior")
    if latest_topology.get("is_dataguard"):
        latest_state_parts.append("Data Guard context")
    if latest_topology.get("interconnect_stress_flag"):
        latest_state_parts.append("interconnect stress explicitly detected")
    latest_state_text = (
        ", with " + _join_readable_labels(latest_state_parts)
        if latest_state_parts
        else ""
    )

    return " ".join(
        [
            first_sentence,
            second_sentence,
            (
                "The latest interval remains aligned with that broader "
                f"picture, showing CPU at {_format_metric(latest_cpu, '%')}, "
                f"User I/O at {_format_metric(latest_io, '%')}, and Top SQL "
                f"concentration (top 3 share) at "
                f"{_format_metric(latest_sql, '%')}{latest_state_text}, "
                f"so the posture remains {posture['posture']} before immediate scaling."
            ),
        ]
    )


def _build_technical_narrative_text(
    multi_snapshot_analysis: dict[str, Any],
    latest_summary: str,
    trend_lines: list[str],
    anomaly_lines: list[str],
    ai_addendum: str,
) -> str:
    snapshot_count = len(multi_snapshot_analysis["ordered_snapshots"])
    paragraphs = multi_snapshot_analysis["multi_snapshot_summary"].split("\n\n")
    paragraph_one = paragraphs[0] if len(paragraphs) > 0 else ""
    paragraph_two = paragraphs[1] if len(paragraphs) > 1 else ""
    paragraph_three = paragraphs[2] if len(paragraphs) > 2 else ""
    trend_block = "\n".join(trend_lines)
    anomaly_block = "\n".join(anomaly_lines)
    topology_sections = _build_topology_narrative_sections(multi_snapshot_analysis)
    topology_block = ""
    if topology_sections:
        topology_chunks = []
        for index in range(0, len(topology_sections), 2):
            topology_chunks.append(
                topology_sections[index] + "\n" + topology_sections[index + 1]
            )
        topology_block = "\n\n" + "\n\n".join(topology_chunks)
    summary_label = (
        "Multi-Snapshot Summary" if snapshot_count > 1 else "Snapshot Summary"
    )
    trend_label = "Trend Findings" if snapshot_count > 1 else "Trend View"
    anomaly_label = "Anomaly Windows" if snapshot_count > 1 else "Anomaly Detection"
    return (
        f"{summary_label}\n"
        f"{paragraph_one}\n\n{paragraph_two}\n\n{paragraph_three}\n\n"
        f"{trend_label}\n"
        f"{trend_block}\n\n"
        + f"{anomaly_label}\n"
        + f"{anomaly_block}\n\n"
        + topology_block
        + "\n\nLatest Snapshot Assessment\n"
        + latest_summary
        + ai_addendum
    )


def _series_has_chart_data(values: list[float | None]) -> bool:
    return sum(value is not None for value in values) >= 2


def _build_time_series_chart_specs(
    multi_snapshot_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    db_scope_metrics = multi_snapshot_analysis.get("db_scope_metrics") or {}
    db_scope_chart_specs = db_scope_metrics.get("chart_specs") or []
    if db_scope_chart_specs:
        return db_scope_chart_specs

    time_series = multi_snapshot_analysis["time_series"]
    chart_candidates = [
        {
            "key": "cpu_trend",
            "title": "CPU Trend",
            "label": "CPU % DB time",
            "color": "rgba(255, 107, 107, 0.92)",
            "container_id": "cpuTrendChart",
        },
        {
            "key": "io_trend",
            "title": "User I/O Trend",
            "label": "User I/O % DB time",
            "color": "rgba(255, 159, 67, 0.92)",
            "container_id": "userIoTrendChart",
        },
        {
            "key": "commit_trend",
            "title": "Commit / Log File Sync Trend",
            "label": "Log file sync ms",
            "color": "rgba(246, 184, 76, 0.92)",
            "container_id": "commitTrendChart",
        },
        {
            "key": "concurrency_trend",
            "title": "Concurrency Trend",
            "label": "Concurrency % DB time",
            "color": "rgba(90, 209, 255, 0.92)",
            "container_id": "concurrencyTrendChart",
        },
        {
            "key": "sql_concentration_trend",
            "title": "Top 3 SQL Share Trend",
            "label": "Top 3 SQL share %",
            "color": "rgba(186, 104, 200, 0.92)",
            "container_id": "topSqlTrendChart",
        },
        {
            "key": "cluster_wait_trend",
            "title": "Cluster Wait Trend",
            "label": "Cluster waits % DB time",
            "color": "rgba(129, 199, 132, 0.92)",
            "container_id": "clusterWaitTrendChart",
        },
        {
            "key": "gc_wait_trend",
            "title": "Combined GC Current + GC CR Trend",
            "label": "Combined GC current + GC CR % DB time",
            "note": "Trend = GC Current + GC CR; violin cards show each component separately",
            "color": "rgba(77, 182, 172, 0.92)",
            "container_id": "gcWaitTrendChart",
        },
        {
            "key": "dg_transport_lag_trend",
            "title": "Data Guard Transport Lag",
            "label": "Transport lag seconds",
            "color": "rgba(255, 213, 79, 0.92)",
            "container_id": "dgTransportLagTrendChart",
        },
        {
            "key": "exa_offload_efficiency_trend",
            "title": "Exadata Offload Trend",
            "label": "Offload efficiency ratio",
            "color": "rgba(171, 71, 188, 0.92)",
            "container_id": "exaOffloadTrendChart",
        },
    ]

    return [
        chart
        for chart in chart_candidates
        if _series_has_chart_data(time_series[chart["key"]])
    ]


def _build_time_series_section_html(
    chart_specs: list[dict[str, Any]],
    snapshot_count: int,
) -> str:
    kicker = "Multi-Snapshot Trends" if snapshot_count > 1 else "Trend View"
    if not chart_specs:
        return (
            '\n      <section id="time-series-charts" class="card secondary">'
            f'\n        <div class="section-kicker">{kicker}</div>'
            "\n        <h2>Time-Series Charts</h2>"
            '\n        <div class="chart-empty">'
            "Insufficient history for time-series chart rendering."
            "</div>\n      </section>\n"
        )

    grouped_specs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for spec in chart_specs:
        grouped_specs[str(spec.get("domain") or "General")].append(spec)

    ordered_domains = [
        domain for domain in DOMAIN_DISPLAY_ORDER if grouped_specs.get(domain)
    ]
    ordered_domains.extend(
        domain for domain in grouped_specs if domain not in ordered_domains
    )
    domain_sections = []
    for domain in ordered_domains:
        specs = grouped_specs[domain]
        chart_panels = "\n".join(
            (
                '            <section class="chart-panel">'
                + f"\n              <h3>{spec['title']}</h3>"
                + (
                    f'\n              <p class="chart-note">{spec["note"]}</p>'
                    if spec.get("note")
                    else ""
                )
                + '\n              <div class="chart-canvas">'
                + f'\n                <canvas id="{spec["container_id"]}"></canvas>'
                + "\n              </div>\n            </section>"
            )
            for spec in specs
        )
        domain_sections.append(
            '          <div class="chart-domain-group">'
            + f'\n            <div class="chart-domain-heading">{domain}</div>'
            + '\n            <div class="chart-grid">'
            + f"\n{chart_panels}"
            + "\n            </div>\n          </div>"
        )
    return (
        '\n      <section id="time-series-charts" class="card secondary">'
        f'\n        <div class="section-kicker">{kicker}</div>'
        "\n        <h2>Time-Series Charts</h2>"
        + ("\n" + "\n".join(domain_sections) if domain_sections else "")
        + "\n      </section>\n"
    )


def _build_time_series_js(chart_specs: list[dict[str, Any]]) -> str:
    spec_json = _json_for_html(chart_specs)
    return rf"""
    const timeSeriesChartSpecs = {spec_json};
    const timeSeriesCharts = [];

    function setSparseSeriesNote(containerId, message) {{
      const canvas = document.getElementById(containerId);
      if (!canvas) {{
        return;
      }}
      const chartPanel = canvas.closest('.chart-panel');
      if (!chartPanel) {{
        return;
      }}
      let note = chartPanel.querySelector('.chart-sparse-note');
      if (!message) {{
        if (note) {{
          note.remove();
        }}
        return;
      }}
      if (!note) {{
        note = document.createElement('p');
        note.className = 'chart-sparse-note';
        chartPanel.appendChild(note);
      }}
      note.textContent = message;
    }}

    function formatCompactIntervalLabel(label) {{
      const text = String(label || '').trim();
      const intervalMatch = text.match(/(\d{{2}}:\d{{2}})\s*->\s*(\d{{2}}:\d{{2}})/);
      if (intervalMatch) {{
        return `${{intervalMatch[1]}}-${{intervalMatch[2]}}`;
      }}
      return text;
    }}

    function buildLineChart(containerId, title, labels, values, color, labelText) {{
      const canvas = document.getElementById(containerId);
      if (!canvas) {{
        return;
      }}

      const numericValues = values.filter((value) => Number.isFinite(value));
      if (!Array.isArray(labels) || labels.length < 2 || numericValues.length < 2) {{
        setSparseSeriesNote(containerId, '');
        showChartFallback(containerId, 'Insufficient history');
        return;
      }}

      const coverageRatio = labels.length > 0
        ? (numericValues.length / labels.length)
        : 0;
      const isSparseSeries = numericValues.length < 3 || coverageRatio < 0.6;
      setSparseSeriesNote(
        containerId,
        isSparseSeries
          ? `Sparse series: ${{numericValues.length}} populated snapshots across ${{labels.length}} intervals`
          : '',
      );

      const ctx = canvas.getContext('2d');
      if (!ctx) {{
        return;
      }}

      const chart = new Chart(ctx, {{
        type: 'line',
        data: {{
          labels,
          datasets: [{{
            label: labelText || title,
            data: values,
            borderColor: color,
            backgroundColor: isSparseSeries
              ? color.replace('0.92', '0.08')
              : color.replace('0.92', '0.18'),
            pointBackgroundColor: color,
            pointBorderColor: '#0f1b2d',
            pointRadius: isSparseSeries ? 5 : 4,
            pointHoverRadius: isSparseSeries ? 6 : 5,
            borderWidth: isSparseSeries ? 2 : 3,
            tension: isSparseSeries ? 0 : 0.25,
            spanGaps: false,
            fill: isSparseSeries ? false : true,
          }}],
        }},
        options: {{
          maintainAspectRatio: false,
          interaction: {{
            mode: 'index',
            intersect: false,
          }},
          plugins: {{
            legend: {{
              display: false,
            }},
            tooltip: {{
              callbacks: {{
                title: function(items) {{
                  if (!items || !items.length) {{
                    return '';
                  }}
                  return labels[items[0].dataIndex] || '';
                }},
              }},
            }},
          }},
          scales: {{
            x: {{
              ticks: {{
                color: chartTextColor,
                maxRotation: 0,
                autoSkip: true,
                callback: function(value, index) {{
                  return formatCompactIntervalLabel(labels[index]);
                }},
              }},
              grid: {{
                color: chartMutedColor,
              }},
            }},
            y: {{
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

      timeSeriesCharts.push(chart);
    }}

    function buildTimeSeriesCharts() {{
      const payload = chartPayload.time_series_charts || {{}};
      const labels = payload.snapshot_labels || [];
      timeSeriesCharts.splice(0, timeSeriesCharts.length).forEach((chart) => chart.destroy());

      timeSeriesChartSpecs.forEach((spec) => {{
        buildLineChart(
          spec.container_id,
          spec.title,
          labels,
          payload[spec.key] || [],
          spec.color,
          spec.label
        );
      }});
    }}
"""


def _replace_chart_payload_json(
    html: str,
    chart_payload: dict[str, Any],
) -> str:
    payload_json = json.dumps(chart_payload, indent=2)
    pattern = re.compile(
        r'(<script id="chart-payload" type="application/json">\s*)(.*?)(\s*</script>)',
        re.DOTALL,
    )
    match = pattern.search(html)
    if not match:
        return html
    return (
        html[: match.start()]
        + match.group(1)
        + payload_json
        + match.group(3)
        + html[match.end() :]
    )


def _extract_existing_chart_payload(html: str) -> dict[str, Any]:
    pattern = re.compile(
        r'<script id="chart-payload" type="application/json">\s*(.*?)\s*</script>',
        re.DOTALL,
    )
    match = pattern.search(html)
    if match is None:
        return {}
    return json.loads(match.group(1))


def _replace_confidence_section_html(
    html: str,
    confidence: dict[str, str],
) -> str:
    level = confidence["level"].lower()
    reason = confidence["reason"]
    replacement = (
        '<section id="ai-confidence" class="card primary">\n'
        f'        <div class="confidence-section confidence-card {level}">\n'
        "          <h2>Confidence Assessment</h2>\n"
        f'          <p><span class="confidence-pill {level}">{confidence["level"]}</span></p>\n'
        f"          <p>Reason: {reason}</p>\n"
        "        </div>\n"
        "      </section>"
    )
    pattern = re.compile(
        r'<section id="ai-confidence" class="card primary">.*?</section>',
        re.DOTALL,
    )
    return pattern.sub(replacement, html, count=1)


def _replace_executive_summary_rationale(
    html_text: str,
    rationale: str,
) -> str:
    escaped_rationale = html.escape(rationale).replace("\n", " ")
    patterns = [
        re.compile(
            (
                r'(<section id="ai-summary" class="card primary">.*?<div '
                r'class="decision-banner[^"]*">.*?</div>\s*<p[^>]*>)'
                r"(.*?)(</p>)"
            ),
            re.DOTALL,
        ),
        re.compile(
            (
                r'(<section id="ai-summary" class="card primary">.*?<div '
                r'class="decision-banner[^"]*">.*?</div>\s*<div '
                r'class="summary-text">\s*<p[^>]*>)(.*?)(</p>)'
            ),
            re.DOTALL,
        ),
    ]
    for pattern in patterns:
        match = pattern.search(html_text)
        if match is None:
            continue
        return (
            html_text[: match.start()]
            + match.group(1)
            + escaped_rationale
            + match.group(3)
            + html_text[match.end() :]
        )
    return html_text


def _inject_executive_summary_scope_label(
    html: str,
    scope_label: str,
) -> str:
    pattern = re.compile(
        r'(<section id="ai-summary" class="card primary">.*?)(<ul[^>]*>)',
        re.DOTALL,
    )
    match = pattern.search(html)
    if match is None:
        return html
    label_html = '\n        <p class="section-kicker">' + scope_label + "</p>\n        "
    return (
        html[: match.start()]
        + match.group(1)
        + label_html
        + match.group(2)
        + html[match.end() :]
    )


def _posture_banner_class(posture: str) -> str:
    posture_map = {
        "TUNE FIRST": "tune-first",
        "DO NOT SCALE": "do-not-scale",
        "INVESTIGATE FURTHER": "investigate",
        "RECOVERING / MONITOR": "recovering-monitor",
        "SCALE CANDIDATE": "scale-candidate",
        "SCALE NOW": "scale-now",
        "INSUFFICIENT DATA": "insufficient",
    }
    return posture_map.get(posture, "insufficient")


def _inject_dashboard_style_overrides(html: str) -> str:
    css_block = """
    .decision-banner.tune-first {
      border-color: rgba(246, 184, 76, 0.40);
      background: rgba(246, 184, 76, 0.16);
      color: #fff7ea;
    }
    .decision-banner.investigate {
      border-color: rgba(255, 159, 67, 0.40);
      background: rgba(255, 159, 67, 0.16);
      color: #fff5ea;
    }
    .decision-banner.recovering-monitor {
      border-color: rgba(102, 187, 106, 0.40);
      background: rgba(102, 187, 106, 0.16);
      color: #effbef;
    }
    .decision-banner.scale-candidate {
      border-color: rgba(90, 209, 255, 0.40);
      background: rgba(90, 209, 255, 0.16);
      color: #eef9ff;
    }
    .confidence-card {
      background: rgba(16, 28, 45, 0.72);
      color: var(--text);
      border: 1px solid var(--line);
    }
    .confidence-pill {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border: 1px solid #000000;
    }
    .confidence-pill.high {
      color: #fff4f4;
      background: rgba(255, 107, 107, 0.24);
    }
    .confidence-pill.medium {
      color: #fff8ed;
      background: rgba(246, 184, 76, 0.24);
    }
    .confidence-pill.low {
      color: #eff7ff;
      background: rgba(127, 179, 213, 0.16);
    }
    .chart-note {
      margin: -4px 0 12px;
      color: rgba(216, 228, 242, 0.78);
      font-size: 13px;
      line-height: 1.4;
    }
    .chart-sparse-note {
      margin: 10px 0 0;
      color: rgba(216, 228, 242, 0.74);
      font-size: 12px;
      line-height: 1.35;
    }
    .chart-domain-group {
      margin-top: 20px;
    }
    .chart-domain-group:first-of-type {
      margin-top: 14px;
    }
    .chart-domain-heading {
      margin: 0 0 12px;
      color: rgba(216, 228, 242, 0.92);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
"""
    if css_block.strip() in html:
        return html
    return html.replace("</style>", css_block + "\n  </style>", 1)


def _build_analysis_context_html(analysis_context: dict[str, str]) -> str:
    hostname = analysis_context["hostname"].replace(" | ", "<br>")
    operating_system = analysis_context["operating_system"].replace(" | ", "<br>")
    return (
        '\n      <section id="analysis-context" class="card secondary">'
        '\n        <div class="section-kicker">Analysis Context</div>'
        "\n        <h2>Analysis Information</h2>"
        '\n        <div class="provider-grid">'
        '\n          <div class="provider-box"><strong>Hostname</strong><div>'
        + hostname
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Operating System</strong><div>'
        + operating_system
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Source Database</strong><div>'
        + analysis_context["source_database"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Number of Instances</strong><div>'
        + analysis_context["instance_count"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Database Version</strong><div>'
        + analysis_context["db_version"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Database Role</strong><div>'
        + analysis_context["database_role"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Cumulative OCPUs / Cores</strong><div>'
        + analysis_context["ocpus_cores"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Memory per Instance</strong><div>'
        + analysis_context["memory_per_instance"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Platform Detected</strong><div>'
        + analysis_context["platform_detected"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Topology Detected</strong><div>'
        + analysis_context["topology_detected"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Snapshot Start</strong><div>'
        + analysis_context["analysis_start"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Snapshot End</strong><div>'
        + analysis_context["analysis_end"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Total Number of Reports / Total Snapshot Window</strong><div>'
        + analysis_context["awr_count_and_window"]
        + "</div></div>"
        '\n          <div class="provider-box"><strong>Last Snapshot</strong><div>'
        + analysis_context["latest_snapshot_interval"]
        + "</div></div>"
        "\n        </div>\n      </section>\n"
    )


def _inject_time_series_section(
    html: str,
    chart_specs: list[dict[str, Any]],
    snapshot_count: int,
) -> str:
    section_html = _build_time_series_section_html(chart_specs, snapshot_count)
    anchor = '<section id="derived-scalar-metrics" class="card secondary">'
    if anchor in html:
        return html.replace(anchor, section_html + "      " + anchor, 1)
    return html


def _inject_analysis_context_section(
    html: str,
    analysis_context: dict[str, str],
) -> str:
    section_html = _build_analysis_context_html(analysis_context)
    anchor = '<section id="ai-summary" class="card primary">'
    if anchor in html:
        return html.replace(anchor, section_html + "      " + anchor, 1)
    return html


def _inject_time_series_javascript(
    html: str,
    chart_specs: list[dict[str, Any]],
) -> str:
    js_block = _build_time_series_js(chart_specs)
    if "function buildTimeSeriesCharts()" not in html:
        html = html.replace(
            "    function buildViolinPanel() {",
            js_block + "\n    function buildViolinPanel() {",
            1,
        )
    html = html.replace(
        "      buildViolinPanel();",
        "      buildViolinPanel();\n      buildTimeSeriesCharts();",
        1,
    )
    return html


def _replace_primary_posture_banner(
    html: str,
    posture: str,
) -> str:
    banner_class = _posture_banner_class(posture)
    banner_pattern = re.compile(
        r'<div class="decision-banner[^"]*">\s*.*?</div>',
        re.DOTALL,
    )
    match = banner_pattern.search(html)
    if match is None:
        return html
    replacement = f'<div class="decision-banner {banner_class}">{posture}</div>'
    return html[: match.start()] + replacement + html[match.end() :]


def _postprocess_dashboard_html(
    dashboard_file: str,
    report_data: dict[str, Any],
    multi_snapshot_analysis: dict[str, Any],
) -> str:
    chart_specs = _build_time_series_chart_specs(multi_snapshot_analysis)
    snapshot_count = len(multi_snapshot_analysis["ordered_snapshots"])
    output_path = Path(dashboard_file)
    html = output_path.read_text(encoding="utf-8")
    html = _inject_dashboard_style_overrides(html)

    chart_payload = {
        "snapshot_labels": multi_snapshot_analysis["snapshot_labels"],
        **report_data["time_series_charts"],
    }
    existing_chart_payload = _extract_existing_chart_payload(html)
    html = _replace_chart_payload_json(
        html,
        {
            **existing_chart_payload,
            "time_series_charts": chart_payload,
        },
    )
    html = _inject_analysis_context_section(
        html,
        report_data["analysis_context"],
    )
    html = _inject_time_series_section(html, chart_specs, snapshot_count)
    html = _inject_time_series_javascript(html, chart_specs)
    html = _replace_confidence_section_html(
        html,
        multi_snapshot_analysis["confidence"],
    )
    html = _replace_executive_summary_rationale(
        html,
        report_data["executive_summary"],
    )
    html = _inject_executive_summary_scope_label(
        html,
        "Latest interval deterministic evidence",
    )
    html = _replace_primary_posture_banner(
        html,
        multi_snapshot_analysis["decision_posture"]["posture"],
    )

    output_path.write_text(html, encoding="utf-8")
    return str(output_path.resolve())


def _build_decision_posture(
    snapshot_contexts: list[dict[str, Any]],
    anomaly_windows: list[dict[str, Any]],
    confidence: dict[str, str],
) -> dict[str, str]:
    latest_context = snapshot_contexts[-1]
    latest_metrics = latest_context["metrics"]
    latest_topology = latest_context.get("topology") or {}
    latest_issue_types = {
        str(issue.get("issue_type") or "")
        for issue in _get_compatibility_issues(latest_context)
    }
    latest_cpu = latest_metrics.get("cpu_pct") or 0.0
    latest_io = latest_metrics.get("user_io_pct") or 0.0
    latest_commit = latest_metrics.get("commit_pct") or 0.0
    latest_concurrency = latest_metrics.get("concurrency_pct") or 0.0
    latest_sql = latest_metrics.get("top_sql_concentration") or 0.0
    anomaly_count = len(anomaly_windows)
    has_tunable_signals = bool(
        {"cpu_pressure", "io_pressure", "commit_pressure", "sql_concentration"}
        & latest_issue_types
    )

    if latest_topology.get("failover_event_flag") or latest_topology.get(
        "role_transition_flag"
    ):
        posture = "INVESTIGATE FURTHER"
        rationale = (
            "The latest snapshot sits inside a failover or role-transition event, "
            "so topology state should be stabilized before generic scaling conclusions are drawn."
        )
    elif latest_topology.get("is_dataguard") and (
        (latest_metrics.get("transport_lag_sec") or 0.0) >= 30.0
        or (latest_metrics.get("apply_lag_sec") or 0.0) >= 30.0
    ):
        posture = "INVESTIGATE FURTHER"
        rationale = (
            "Replication lag is materially visible, so the dominant posture should "
            "focus on Data Guard health before treating the interval as a pure sizing problem."
        )
    elif (
        latest_topology.get("is_rac")
        and (latest_metrics.get("cluster_wait_pct_db_time") or 0.0) >= 8.0
    ):
        posture = "TUNE FIRST"
        rationale = (
            "The interval is materially influenced by RAC coordination pressure, "
            "so cluster access patterns and cross-instance behavior should be tuned before scaling."
        )
    elif confidence["level"] == "LOW" and len(snapshot_contexts) == 1:
        if _get_compatibility_issues(latest_context):
            posture = "TUNE FIRST"
            rationale = (
                "Only one snapshot is available, but that interval still shows "
                "clear tunable pressure that should be addressed before scaling."
            )
        else:
            posture = "INSUFFICIENT DATA"
            rationale = (
                "Only one low-signal snapshot is available, so there is not "
                "enough deterministic evidence to set a stronger posture."
            )
    elif latest_cpu >= 85.0 and latest_io >= 25.0 and latest_sql < 10.0:
        posture = "SCALE NOW"
        rationale = (
            "The latest snapshot shows broad-based pressure that is less "
            "likely to be solved by tuning alone."
        )
    elif latest_cpu >= 75.0 and latest_io < 15.0 and latest_sql < 10.0:
        posture = "SCALE CANDIDATE"
        rationale = (
            "Pressure remains high with limited evidence of concentrated "
            "tunable SQL, so compute scaling may become appropriate."
        )
    elif anomaly_count >= 2 and (
        latest_commit >= 10.0 or latest_concurrency >= 10.0 or latest_io >= 20.0
    ):
        posture = "INVESTIGATE FURTHER"
        rationale = (
            "Repeated anomaly windows indicate interval instability that "
            "should be explained before scaling."
        )
    elif (
        len(snapshot_contexts) >= 3
        and not _get_compatibility_issues(latest_context)
        and anomaly_count
    ):
        posture = "RECOVERING / MONITOR"
        rationale = (
            "Earlier anomalous intervals have moderated in the latest "
            "snapshot, so monitoring is appropriate."
        )
    elif latest_sql >= 25.0 or has_tunable_signals:
        posture = "TUNE FIRST"
        rationale = (
            "The strongest current evidence still points to tunable SQL, "
            "access-path, or transaction behavior before scaling."
        )
    else:
        posture = "DO NOT SCALE"
        rationale = (
            "The observed workload does not currently justify scaling based on "
            "the available deterministic evidence."
        )

    return {
        "posture": posture,
        "rationale": rationale,
        "confidence": confidence["level"],
        "supporting_guidance": (
            "Do not scale now until the current primary posture is resolved."
        ),
    }


def _build_agentic_decision(
    issues: list[dict],
    decision_posture: dict[str, str] | None = None,
) -> dict:
    issue_by_type = {str(issue.get("issue_type") or ""): issue for issue in issues}

    execution_plan = [
        "Tune the highest CPU-consuming SQL and execution paths first.",
        ("Prioritize the top elapsed-time OrderService SQL statements " "immediately."),
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

    if "topology_event" in issue_by_type or "dg_replication_state" in issue_by_type:
        primary_decision = (
            "Stabilize topology, failover, and Data Guard transition state "
            "first, then tune the highest-impact CPU-heavy SQL paths."
        )
    elif "cpu_pressure" in issue_by_type:
        primary_decision = (
            "Start with CPU-heavy SQL in OrderService. Tune the top "
            "CPU-consuming and top elapsed-time SQL paths first."
        )
    else:
        primary_decision = (
            "Start with the most material SQL and execution-path " "bottlenecks first."
        )

    scaling_decision = "INSUFFICIENT DATA"
    confidence_level = "High"
    if decision_posture is not None:
        scaling_decision = decision_posture["posture"]
        confidence_level = decision_posture["confidence"].title()
        primary_decision = (
            f"{primary_decision} Current decision posture: "
            f"{decision_posture['posture']}."
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
        "scaling_decision": scaling_decision,
        "confidence_level": confidence_level,
    }


def _build_oci_guidance(
    issues: list[dict],
    decision_posture: dict[str, str] | None = None,
) -> dict:
    issue_by_type = {str(issue.get("issue_type") or ""): issue for issue in issues}

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
    if decision_posture is not None:
        current_state += (
            f" Deterministic posture: {decision_posture['posture']} "
            f"({decision_posture['confidence']} confidence)."
        )

    return {
        "current_state_assessment": current_state,
        "scaling_trigger_conditions": (
            "Scaling becomes appropriate only after the CPU-heavy SQL paths, "
            "concentrated statements, physical read demand, and commit "
            "behavior have been tuned and the same dominant constraints "
            "still remain."
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
            "compute scaling ahead of storage scaling."
        ),
        "risk_considerations": (
            "Scaling too early will mask the real problem and carry "
            "inefficient SQL and transaction behavior into a larger "
            "footprint."
        ),
    }


def _build_executive_summary(issues: list[dict]) -> str:
    issue_by_type = {str(issue.get("issue_type") or ""): issue for issue in issues}

    summary_parts: list[str] = []

    cpu_issue = issue_by_type.get("cpu_pressure")
    if cpu_issue:
        pct_db_time = _format_pct(cpu_issue.get("evidence", {}).get("pct_db_time"))
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
        commit_pct = _format_pct(commit_issue.get("evidence", {}).get("pct_db_time"))
        secondary_factors.append(f"commit latency is also contributing at {commit_pct}")

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
        combined_pct_total = _format_pct(sql_evidence.get("combined_pct_total"))
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


def _build_snapshot_context(file_path: Path) -> dict[str, Any]:
    result = parse_awr_file(file_path)
    derived_pressure_metrics = extract_derived_pressure_metrics(result)
    topology = _topology_signals(result)
    begin_time = _parse_snapshot_time(result.run_metadata.begin_snapshot_time)
    end_time = _parse_snapshot_time(result.run_metadata.end_snapshot_time)

    metrics = {
        "cpu_pct": _compute_cpu_pct(result),
        "user_io_pct": _sum_wait_class_pct(result, "User I/O"),
        "commit_pct": _sum_wait_class_pct(result, "Commit"),
        "commit_pressure": _extract_log_file_sync_ms(result),
        "concurrency_pct": _sum_wait_class_pct(result, "Concurrency"),
        "top_sql_concentration": _top_sql_concentration(result),
        "hard_parses_per_sec": derived_pressure_metrics["hard_parses_per_sec"],
        "temp_io_pressure": derived_pressure_metrics["temp_io_pressure"],
        "pga_spill_pressure": derived_pressure_metrics["pga_spill_pressure"],
        "log_file_sync_ms": _extract_log_file_sync_ms(result),
        "cluster_wait_pct_db_time": _topology_pct(
            result,
            "cluster_wait_pct_db_time",
        ),
        "gc_current_wait_pct_db_time": _topology_pct(
            result,
            "gc_current_wait_pct_db_time",
        ),
        "gc_cr_wait_pct_db_time": _topology_pct(
            result,
            "gc_cr_wait_pct_db_time",
        ),
        "gc_total_wait_pct_db_time": (
            (
                (_topology_pct(result, "gc_cr_wait_pct_db_time") or 0.0)
                + (_topology_pct(result, "gc_current_wait_pct_db_time") or 0.0)
            )
            if (
                _topology_pct(result, "gc_cr_wait_pct_db_time") is not None
                or _topology_pct(result, "gc_current_wait_pct_db_time") is not None
            )
            else None
        ),
        "transport_lag_sec": _topology_float(result, "transport_lag_sec"),
        "apply_lag_sec": _topology_float(result, "apply_lag_sec"),
        "exa_cell_io_pct_db_time": _topology_pct(
            result,
            "exa_cell_io_pct_db_time",
        ),
        "exa_offload_efficiency": _topology_float(
            result,
            "exa_offload_efficiency",
        ),
    }

    context = {
        "file_path": file_path,
        "file_name": file_path.name,
        "result": result,
        "topology": topology,
        "derived_pressure_metrics": derived_pressure_metrics,
        "begin_time": begin_time,
        "end_time": end_time,
        "metrics": metrics,
    }
    context["snapshot_label"] = _snapshot_label(context)
    return context


def _topology_hint_labels(topology: dict[str, Any]) -> str:
    """Return a concise topology/platform label string for intake review."""

    labels: list[str] = []
    cluster_wait = _safe_float(topology.get("cluster_wait_pct_db_time"))
    gc_cr_wait = _safe_float(topology.get("gc_cr_wait_pct_db_time"))
    gc_current_wait = _safe_float(topology.get("gc_current_wait_pct_db_time"))
    transport_lag = _safe_float(topology.get("transport_lag_sec"))
    apply_lag = _safe_float(topology.get("apply_lag_sec"))
    exa_cell_io = _safe_float(topology.get("exa_cell_io_pct_db_time"))
    exa_offload = _safe_float(topology.get("exa_offload_efficiency"))
    database_role = str(topology.get("database_role") or "").strip()
    normalized_role = database_role.lower()
    if (
        (cluster_wait or 0.0) > 0.0
        or (gc_cr_wait or 0.0) > 0.0
        or (gc_current_wait or 0.0) > 0.0
    ):
        labels.append("RAC")
    if (
        (transport_lag or 0.0) > 0.0
        or (apply_lag or 0.0) > 0.0
        or any(
            token in normalized_role
            for token in ("standby", "far sync", "snapshot standby")
        )
    ):
        labels.append("Data Guard")
    if (exa_cell_io or 0.0) > 0.0 or (exa_offload or 0.0) > 0.0:
        labels.append("Exadata")
    if database_role and database_role.upper() not in {"UNKNOWN", "NONE"}:
        labels.append(database_role)
    return ", ".join(dict.fromkeys(labels)) or "Single Instance"


def _build_ingestion_runtime_context(
    snapshot_contexts: list[dict[str, Any]],
    awr_files: list[Path],
    generated_at_display: str,
    db_ingestion_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build plain runtime intake data for Screen 1 mapping."""

    db_ingestion_context = db_ingestion_context or {}
    db_report_rows = db_ingestion_context.get("report_rows") or {}
    report_rows: list[dict[str, Any]] = []
    validation_notes: list[str] = []
    succeeded = 0
    failed = 0

    for context in snapshot_contexts:
        result = context["result"]
        metadata = result.run_metadata
        parser_notes = [
            _normalize_parser_note(note)
            for note in list(
                dict.fromkeys(
                    (result.parse_warnings or []) + (result.parse_errors or [])
                )
            )
        ]
        warning_notes = [
            note for note in parser_notes if _is_warning_parser_note(note)
        ]
        if result.parse_errors:
            parse_status = "FAILED"
            failed += 1
        elif warning_notes:
            parse_status = "WARNINGS"
            succeeded += 1
        else:
            parse_status = "SUCCESS"
            succeeded += 1

        db_row = db_report_rows.get(context["file_name"]) or {}
        report_rows.append(
            {
                "file_name": context["file_name"],
                "parse_status": parse_status,
                "db_status": db_row.get("db_status"),
                "awr_id": db_row.get("awr_id"),
                "vector_status": db_row.get("vector_status"),
                "similarity_eligible": db_row.get("similarity_eligible"),
                "db_name": metadata.database_name,
                "dbid": metadata.db_id,
                "instance_name": metadata.instance_name,
                "host_name": metadata.host_name,
                "snapshot_begin": metadata.begin_snapshot_time,
                "snapshot_end": metadata.end_snapshot_time,
                "topology_hints": _topology_hint_labels(context.get("topology") or {}),
                "validation_notes": warning_notes,
                "parser_notes": parser_notes,
            }
        )
        validation_notes.extend(
            f"{context['file_name']}: {note}" for note in parser_notes
        )

    total_files = len(awr_files)
    processed = len(snapshot_contexts)
    skipped = max(0, total_files - processed)
    return {
        "run_label": generated_at_display,
        "source_mode": "LOCAL",
        "intake_summary": {
            "total_files": total_files,
            "processed": processed,
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "manifest_status": "Input directory scan complete.",
        },
        "report_rows": report_rows,
        "validation_notes": validation_notes,
        "db_ingestion": db_ingestion_context,
    }


def _normalize_parser_note(note: Any) -> str:
    text = str(note or "").strip()
    optional_match = re.match(
        r"Optional section not found:\s*(.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if optional_match:
        section_name = optional_match.group(1).strip()
        if section_name.lower() == "io":
            return "INFO: Optional IO section not present."
        return f"INFO: Optional section not present: {section_name}."
    return text


def _is_warning_parser_note(note: str) -> bool:
    normalized = str(note or "").strip().lower()
    if not normalized:
        return False
    if normalized.startswith("info:"):
        return False
    return (
        normalized.startswith("required section not found")
        or normalized.startswith("unknown section header")
        or "error" in normalized
        or "failed" in normalized
    )


def _build_comparison_runtime_context(
    multi_snapshot_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Build plain runtime comparison data for Screen 3 mapping."""

    latest_snapshot = multi_snapshot_analysis["latest_snapshot"]
    worst_snapshot = multi_snapshot_analysis["worst_snapshot"]
    latest_score = _snapshot_score(latest_snapshot)
    worst_score = max(_snapshot_score(worst_snapshot), 0.0001)
    if latest_snapshot["snapshot_label"] == worst_snapshot["snapshot_label"]:
        latest_vs_trend = "The latest interval confirms the strongest pressure seen in the broader window."
    elif latest_score >= worst_score * 0.85:
        latest_vs_trend = (
            "The latest interval broadly aligns with the broader multi-snapshot trend."
        )
    else:
        latest_vs_trend = "The latest interval departs from the worst interval and should be read in broader context."

    return {
        "snapshot_count": len(multi_snapshot_analysis["ordered_snapshots"]),
        "comparison_window": multi_snapshot_analysis["analysis_context"].get(
            "awr_count_and_window"
        ),
        "analysis_scope_label": multi_snapshot_analysis["analysis_context"].get(
            "source_database"
        ),
        "latest_snapshot_summary": multi_snapshot_analysis["latest_snapshot_summary"],
        "worst_snapshot_summary": _build_latest_snapshot_summary(
            worst_snapshot
        ).replace("Latest snapshot", "Worst interval", 1),
        "latest_vs_trend": latest_vs_trend,
        "drift_summary": multi_snapshot_analysis["multi_snapshot_summary"],
    }


def _runtime_awr_id(context: dict[str, Any]) -> int:
    """Build a deterministic runtime AWR identifier for non-ingest analysis."""

    result = context["result"]
    metadata = result.run_metadata
    seed = "|".join(
        [
            context["file_name"],
            str(metadata.db_id or "").strip(),
            str(metadata.begin_snapshot_time or "").strip(),
            str(metadata.end_snapshot_time or "").strip(),
        ]
    )
    return int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12], 16)


def _runtime_feature_vector(context: dict[str, Any]) -> dict[str, Any]:
    """Reuse the validated feature builder for the active runtime path."""

    feature_vector_record = build_feature_vector_record(
        parse_result=context["result"],
        awr_id=_runtime_awr_id(context),
        source_system_id=0,
    )
    feature_json = json.loads(feature_vector_record["feature_json"])
    return {
        "feature_json": feature_json,
        "feature_vector_record": feature_vector_record,
    }


def _lookup_loaded_awr_record(
    connection: Any,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    metadata = context["result"].run_metadata
    dbid = str(metadata.db_id or "").strip()
    binds = {
        "source_file_name": context["file_name"],
        "dbid": int(dbid) if dbid.isdigit() else None,
        "db_name": str(metadata.database_name or "").strip() or None,
        "instance_name": str(metadata.instance_name or "").strip() or None,
        "snap_begin": context.get("begin_time"),
        "snap_end": context.get("end_time"),
    }
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT r.AWR_ID,
                   r.SOURCE_SYSTEM_ID,
                   fv.FEATURE_VECTOR_ID
              FROM AWR_REPORT r
              LEFT JOIN AWR_FEATURE_VECTOR fv
                ON fv.AWR_ID = r.AWR_ID
               AND fv.FEATURE_VECTOR IS NOT NULL
             WHERE r.SOURCE_FILE_NAME = :source_file_name
               AND (:dbid IS NULL OR r.DBID = :dbid)
               AND (:db_name IS NULL OR UPPER(r.DB_NAME) = UPPER(:db_name))
               AND (:instance_name IS NULL OR UPPER(r.INSTANCE_NAME) = UPPER(:instance_name))
               AND (:snap_begin IS NULL OR r.SNAP_TIME_BEGIN = :snap_begin)
               AND (:snap_end IS NULL OR r.SNAP_TIME_END = :snap_end)
             ORDER BY CASE WHEN fv.FEATURE_VECTOR_ID IS NOT NULL THEN 0 ELSE 1 END,
                      r.AWR_ID DESC
             FETCH FIRST 1 ROWS ONLY
            """,
            binds,
        )
        row = cursor.fetchone()
    if not row:
        return None
    return {
        "awr_id": int(row[0]),
        "source_system_id": int(row[1]),
        "feature_vector_id": int(row[2]) if row[2] is not None else None,
    }


def _lookup_loaded_awr_id(
    connection: Any,
    context: dict[str, Any],
) -> int | None:
    record = _lookup_loaded_awr_record(connection, context)
    return int(record["awr_id"]) if record else None


def _ensure_loaded_feature_vector(
    connection: Any,
    context: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    if record.get("feature_vector_id") is not None:
        return {
            "feature_vector_id": int(record["feature_vector_id"]),
            "vector_status": "Existing",
            "vector_action": "existing",
        }

    feature_vector_record = build_feature_vector_record(
        parse_result=context["result"],
        awr_id=int(record["awr_id"]),
        source_system_id=int(record["source_system_id"]),
    )
    feature_vector_id, action = upsert_feature_vector(connection, feature_vector_record)
    connection.commit()
    print(
        "Similarity load/reuse: "
        f"{action} feature vector {feature_vector_id} for AWR_ID {record['awr_id']}"
    )
    action_text = str(action or "").strip().lower()
    if "update" in action_text:
        vector_status = "Updated"
    elif "create" in action_text or "insert" in action_text or "upsert" in action_text:
        vector_status = "Created"
    else:
        vector_status = "Created"
    return {
        "feature_vector_id": int(feature_vector_id),
        "vector_status": vector_status,
        "vector_action": action or vector_status,
    }


def _prepare_db_backed_similarity_runtime(
    connection: Any,
    snapshot_contexts: list[dict[str, Any]],
    latest_context: dict[str, Any],
) -> dict[str, Any]:
    loaded_records = {
        context["file_name"]: _lookup_loaded_awr_record(connection, context)
        for context in snapshot_contexts
    }
    initially_loaded = {
        file_name: record
        for file_name, record in loaded_records.items()
        if record is not None
    }
    if any(record is None for record in loaded_records.values()):
        missing = [
            file_name
            for file_name, record in loaded_records.items()
            if record is None
        ]
        print(
            "Similarity load/reuse: loading missing AWR history into ADB for "
            + ", ".join(missing[:5])
            + (" ..." if len(missing) > 5 else "")
        )
        process_awr_batch(Path("data/input"), conn=connection)
        loaded_records = {
            context["file_name"]: _lookup_loaded_awr_record(connection, context)
            for context in snapshot_contexts
        }

    file_rows: dict[str, dict[str, Any]] = {}
    vector_existing = 0
    vector_changed = 0
    for context in snapshot_contexts:
        file_name = context["file_name"]
        record = loaded_records.get(context["file_name"])
        if record is None:
            file_rows[file_name] = {
                "db_status": "Failed",
                "awr_id": None,
                "vector_status": "Missing",
                "similarity_eligible": False,
            }
            continue
        vector_result = _ensure_loaded_feature_vector(connection, context, record)
        vector_status = vector_result.get("vector_status")
        if vector_status == "Existing":
            vector_existing += 1
        elif vector_status in {"Created", "Updated"}:
            vector_changed += 1
        if file_name in initially_loaded:
            db_status = "Already Loaded"
        else:
            db_status = "Newly Loaded"
        file_rows[file_name] = {
            "db_status": db_status,
            "awr_id": int(record["awr_id"]),
            "source_system_id": int(record["source_system_id"]),
            "vector_status": vector_status,
            "feature_vector_id": vector_result.get("feature_vector_id"),
            "similarity_eligible": bool(vector_result.get("feature_vector_id")),
        }

    latest_record = loaded_records.get(latest_context["file_name"])
    analysis_awr_id = (
        int(latest_record["awr_id"])
        if latest_record
        else _runtime_awr_id(latest_context)
    )
    newly_loaded = sum(
        1 for file_name, row in file_rows.items()
        if row.get("db_status") == "Newly Loaded"
    )
    already_loaded = len(initially_loaded)
    return {
        "analysis_awr_id": analysis_awr_id,
        "db_ingestion": {
            "summary": {
                "db_connectivity": "Connected",
                "db_load_mode": "Insert missing" if newly_loaded else "Reuse existing",
                "already_loaded": already_loaded,
                "newly_loaded": newly_loaded,
                "reused_awr_ids": already_loaded,
                "feature_vectors_existing": vector_existing,
                "feature_vectors_created_updated": vector_changed,
                "db_similarity_ready": bool(
                    latest_record
                    and file_rows.get(latest_context["file_name"], {}).get(
                        "similarity_eligible"
                    )
                ),
            },
            "report_rows": file_rows,
        },
    }


def _db_ingestion_not_checked_context(reason: str, *, failed: bool = False) -> dict[str, Any]:
    return {
        "summary": {
            "db_connectivity": "Failed" if failed else "Not checked",
            "db_load_mode": "Local only",
            "db_similarity_ready": False,
            "status_message": reason,
        },
        "report_rows": {},
    }


def _build_feature_visual_series(
    snapshot_contexts: list[dict[str, Any]],
) -> dict[str, list[float | None]]:
    """Recover truthful visual series from per-snapshot feature vectors."""

    series: dict[str, list[float | None]] = {
        "cpu_pct": [],
        "user_io_pressure": [],
        "top_sql_concentration": [],
        "log_file_sync_ms": [],
        "cluster_wait_pct_db_time": [],
        "gc_current_wait_pct_db_time": [],
        "gc_cr_wait_pct_db_time": [],
        "gc_total_wait_pct_db_time": [],
        "interconnect_stress_flag": [],
        "transport_lag_sec": [],
        "apply_lag_sec": [],
        "cell_single_block_read_pct_db_time": [],
        "smart_scan_pct_db_time": [],
    }
    for context in snapshot_contexts:
        feature_json = _runtime_feature_vector(context)["feature_json"]
        series["cpu_pct"].append(
            _safe_float(feature_json.get("DB_CPU_PCT_DB_TIME"))
            or _safe_float(feature_json.get("CPU_UTIL_P95"))
        )
        series["user_io_pressure"].append(
            _safe_float(feature_json.get("USER_IO_PRESSURE"))
        )
        series["top_sql_concentration"].append(
            _safe_float(feature_json.get("TOP_SQL_LOAD_CONCENTRATION"))
        )
        series["log_file_sync_ms"].append(
            _safe_float(feature_json.get("LOG_FILE_SYNC_MS"))
        )
        series["cluster_wait_pct_db_time"].append(
            _safe_float(feature_json.get("CLUSTER_WAIT_PCT_DB_TIME"))
        )
        series["gc_current_wait_pct_db_time"].append(
            _safe_float(feature_json.get("GC_CURRENT_WAIT_PCT_DB_TIME"))
        )
        series["gc_cr_wait_pct_db_time"].append(
            _safe_float(feature_json.get("GC_CR_WAIT_PCT_DB_TIME"))
        )
        gc_current = _safe_float(feature_json.get("GC_CURRENT_WAIT_PCT_DB_TIME"))
        gc_cr = _safe_float(feature_json.get("GC_CR_WAIT_PCT_DB_TIME"))
        series["gc_total_wait_pct_db_time"].append(
            (gc_current or 0.0) + (gc_cr or 0.0)
            if gc_current is not None or gc_cr is not None
            else None
        )
        series["interconnect_stress_flag"].append(
            _safe_float(feature_json.get("INTERCONNECT_STRESS_FLAG"))
        )
        series["transport_lag_sec"].append(
            _safe_float(feature_json.get("TRANSPORT_LAG_SEC"))
        )
        series["apply_lag_sec"].append(_safe_float(feature_json.get("APPLY_LAG_SEC")))
        series["cell_single_block_read_pct_db_time"].append(
            _safe_float(feature_json.get("CELL_SINGLE_BLOCK_READ_PCT_DB_TIME"))
        )
        series["smart_scan_pct_db_time"].append(
            _safe_float(feature_json.get("SMART_SCAN_PCT_DB_TIME"))
        )
    return series


def _series_has_numeric_values(values: list[float | None]) -> bool:
    return any(value is not None for value in values)


def _coalesce_series(
    existing: list[float | None] | None,
    fallback: list[float | None],
) -> list[float | None]:
    if isinstance(existing, list) and _series_has_numeric_values(existing):
        return existing
    return fallback


def _absolute_delta_series(
    left_values: list[float | None],
    right_values: list[float | None],
) -> list[float | None]:
    deltas: list[float | None] = []
    for left_value, right_value in zip(left_values, right_values, strict=False):
        if left_value is None or right_value is None:
            deltas.append(None)
            continue
        deltas.append(round(abs(float(left_value) - float(right_value)), 4))
    return deltas


def _supplement_time_series_charts(
    time_series_charts: dict[str, Any],
    feature_visual_series: dict[str, list[float | None]],
) -> dict[str, Any]:
    supplemented = dict(time_series_charts)
    supplemented["cpu_trend"] = _coalesce_series(
        supplemented.get("cpu_trend"),
        feature_visual_series.get("cpu_pct") or [],
    )
    supplemented["io_trend"] = _coalesce_series(
        supplemented.get("io_trend"),
        feature_visual_series.get("user_io_pressure") or [],
    )
    supplemented["sql_concentration_trend"] = _coalesce_series(
        supplemented.get("sql_concentration_trend"),
        feature_visual_series.get("top_sql_concentration") or [],
    )
    supplemented["commit_trend"] = _coalesce_series(
        supplemented.get("commit_trend"),
        feature_visual_series.get("log_file_sync_ms") or [],
    )
    supplemented["cluster_wait_trend"] = _coalesce_series(
        supplemented.get("cluster_wait_trend"),
        feature_visual_series.get("cluster_wait_pct_db_time") or [],
    )
    return supplemented


def _supplement_violin_panel_payload(
    violin_panel: dict[str, Any],
    feature_visual_series: dict[str, list[float | None]],
) -> dict[str, Any]:
    supplemented = {
        group_name: dict(group_values)
        for group_name, group_values in (violin_panel or {}).items()
        if isinstance(group_values, dict)
    }
    workload = supplemented.setdefault("workload", {})
    topology = supplemented.setdefault("topology", {})
    platform = supplemented.setdefault("platform", {})
    workload["cluster_cpu_pct_db_time"] = _coalesce_series(
        workload.get("cluster_cpu_pct_db_time"),
        feature_visual_series.get("cpu_pct") or [],
    )
    workload["cluster_user_io_pct_db_time"] = _coalesce_series(
        workload.get("cluster_user_io_pct_db_time"),
        feature_visual_series.get("user_io_pressure") or [],
    )
    workload["cluster_top_sql_concentration_pct"] = _coalesce_series(
        workload.get("cluster_top_sql_concentration_pct"),
        feature_visual_series.get("top_sql_concentration") or [],
    )
    workload["cluster_log_file_sync_ms"] = _coalesce_series(
        workload.get("cluster_log_file_sync_ms"),
        feature_visual_series.get("log_file_sync_ms") or [],
    )
    topology["cluster_wait_pct_db_time"] = _coalesce_series(
        topology.get("cluster_wait_pct_db_time"),
        feature_visual_series.get("cluster_wait_pct_db_time") or [],
    )
    topology["gc_current_wait_pct_db_time"] = _coalesce_series(
        topology.get("gc_current_wait_pct_db_time"),
        feature_visual_series.get("gc_current_wait_pct_db_time") or [],
    )
    topology["gc_cr_wait_pct_db_time"] = _coalesce_series(
        topology.get("gc_cr_wait_pct_db_time"),
        feature_visual_series.get("gc_cr_wait_pct_db_time") or [],
    )
    topology["combined_gc_wait_pct_db_time"] = _coalesce_series(
        topology.get("combined_gc_wait_pct_db_time"),
        feature_visual_series.get("gc_total_wait_pct_db_time") or [],
    )
    topology["interconnect_stress_flag"] = _coalesce_series(
        topology.get("interconnect_stress_flag"),
        feature_visual_series.get("interconnect_stress_flag") or [],
    )
    topology["transport_lag_sec"] = _coalesce_series(
        topology.get("transport_lag_sec"),
        feature_visual_series.get("transport_lag_sec") or [],
    )
    topology["apply_lag_sec"] = _coalesce_series(
        topology.get("apply_lag_sec"),
        feature_visual_series.get("apply_lag_sec") or [],
    )
    topology["lag_stability_sec"] = _coalesce_series(
        topology.get("lag_stability_sec"),
        _absolute_delta_series(
            feature_visual_series.get("transport_lag_sec") or [],
            feature_visual_series.get("apply_lag_sec") or [],
        ),
    )
    platform["cell_single_block_read_pct_db_time"] = _coalesce_series(
        platform.get("cell_single_block_read_pct_db_time"),
        feature_visual_series.get("cell_single_block_read_pct_db_time") or [],
    )
    platform["smart_scan_pct_db_time"] = _coalesce_series(
        platform.get("smart_scan_pct_db_time"),
        feature_visual_series.get("smart_scan_pct_db_time") or [],
    )
    return supplemented


def _decision_anomaly_signals(
    latest_context: dict[str, Any],
    multi_snapshot_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    """Translate latest-window anomaly context into decision-engine inputs."""

    metric_map = {
        "Commit / log file sync": "LOG_FILE_SYNC_MS",
        "User I/O": "READ_LATENCY_MS",
        "Cluster waits": "CLUSTER_WAIT_PCT_DB_TIME",
        "Data Guard transport lag": "TRANSPORT_LAG_SEC",
    }
    latest_label = str(latest_context.get("snapshot_label") or "")
    signals: list[dict[str, Any]] = []
    for window in multi_snapshot_analysis.get("anomaly_windows") or []:
        if str(window.get("snapshot_label") or "") != latest_label:
            continue
        metric_name = metric_map.get(str(window.get("metric") or ""))
        if not metric_name:
            continue
        signals.append(
            {
                "metric_name": metric_name,
                "anomaly_type": "SPIKE",
                "severity": str(window.get("severity") or "").upper(),
                "reason": window.get("reason"),
            }
        )
    return signals


def _grouped_deterministic_findings(
    decision: Any,
    canonical_recommendations: list[Any],
    latest_context: dict[str, Any],
    multi_snapshot_analysis: dict[str, Any],
) -> dict[str, Any]:
    """Build grouped deterministic findings for explanation-layer synthesis."""

    issue_type_map = {
        "CPU": "cpu_pressure",
        "IO": "io_pressure",
        "COMMIT": "commit_pressure",
        "RAC": "cluster_contention",
        "ADG": "dg_replication_state",
        "MEMORY": "memory_pressure",
    }
    severity = (
        "high"
        if decision.overall_status == "CRITICAL"
        else "medium" if decision.overall_status == "WARNING" else "low"
    )
    domain_scores = (
        decision.evidence.get("domain_scores", {}) if decision.evidence else {}
    )
    feature_evidence = (
        decision.evidence.get("feature_evidence", {}) if decision.evidence else {}
    )
    findings: list[dict[str, Any]] = []
    ordered_domains = [decision.primary_issue, *list(decision.secondary_issues)]
    seen_domains: set[str] = set()

    for raw_domain in ordered_domains:
        if raw_domain is None:
            continue

        domain = str(raw_domain).upper()

        if domain in seen_domains:
            continue

        seen_domains.add(domain)

        reasons = (
            decision.evidence.get("primary_reasons", [])
            if domain == str(decision.primary_issue or "").upper() and decision.evidence
            else []
        )

        summary = (
            reasons[0]
            if reasons
            else (
                f"{domain} was selected deterministically with score "
                f"{_format_metric(_safe_float(domain_scores.get(domain)))}."
            )
        )

        findings.append(
            {
                "domain": domain,
                "issue_type": issue_type_map.get(domain, domain.lower()),
                "severity": severity,
                "summary": summary,
                "score": _safe_float(domain_scores.get(domain)),
                "evidence": feature_evidence.get(domain, {}),
            }
        )
    recommendation_items = [
        recommendation.to_dict() for recommendation in canonical_recommendations
    ]
    anomaly_windows = list((multi_snapshot_analysis.get("anomaly_windows") or [])[:5])
    trend_findings = list(multi_snapshot_analysis.get("trend_findings") or [])
    primary_finding = findings[0] if findings else None
    return {
        "decision_summary": {
            "primary_issue": decision.primary_issue,
            "secondary_issues": list(decision.secondary_issues),
            "overall_status": decision.overall_status,
            "severity_score": decision.severity_score,
            "confidence": decision.confidence,
            "summary": (
                f"{decision.primary_issue} is the authoritative deterministic conclusion "
                f"with status {decision.overall_status}."
            ),
        },
        "primary_evidence": {
            "domain": primary_finding.get("domain") if primary_finding else None,
            "summary": primary_finding.get("summary") if primary_finding else None,
            "score": primary_finding.get("score") if primary_finding else None,
            "feature_values": (
                primary_finding.get("evidence", {}) if primary_finding else {}
            ),
            "reasons": (
                list(decision.evidence.get("primary_reasons", []))
                if decision.evidence
                else []
            ),
        },
        "secondary_evidence": findings[1:],
        "trend_summary": {
            "summary": (
                trend_findings[0]
                if trend_findings
                else "No deterministic trend summary is available."
            ),
            "findings": trend_findings,
        },
        "anomaly_summary": {
            "summary": (
                str(anomaly_windows[0].get("reason") or "")
                if anomaly_windows
                else "No deterministic anomaly windows were detected."
            ),
            "count": len(multi_snapshot_analysis.get("anomaly_windows") or []),
            "windows": anomaly_windows,
        },
        "recommendation_summary": {
            "count": len(recommendation_items),
            "items": recommendation_items,
            "summary": (
                recommendation_items[0].get("action")
                if recommendation_items
                else "No deterministic recommendations were generated."
            ),
        },
        "key_evidence": {
            "summary_key_signals": _build_summary_key_signals(latest_context),
            "domain_scores": domain_scores,
            "primary_reasons": (
                list(decision.evidence.get("primary_reasons", []))
                if decision.evidence
                else []
            ),
        },
    }


def _narrative_findings_from_grouped(
    grouped_findings: dict[str, Any],
) -> list[dict[str, Any]]:
    """Adapt grouped deterministic findings into the existing explanation shape."""

    decision_summary = grouped_findings.get("decision_summary") or {}
    primary_evidence = grouped_findings.get("primary_evidence") or {}
    secondary_evidence = list(grouped_findings.get("secondary_evidence") or [])
    trend_summary = grouped_findings.get("trend_summary") or {}
    anomaly_summary = grouped_findings.get("anomaly_summary") or {}
    key_evidence = grouped_findings.get("key_evidence") or {}
    findings: list[dict[str, Any]] = []

    if decision_summary:
        findings.append(
            {
                "issue_type": "decision_summary",
                "severity": str(
                    decision_summary.get("overall_status") or "low"
                ).lower(),
                "summary": decision_summary.get("summary"),
                "evidence": {
                    "primary_issue": decision_summary.get("primary_issue"),
                    "secondary_issues": decision_summary.get("secondary_issues"),
                    "severity_score": decision_summary.get("severity_score"),
                    "confidence": decision_summary.get("confidence"),
                },
            }
        )
    if primary_evidence:
        findings.append(
            {
                "issue_type": "primary_evidence",
                "severity": "high",
                "summary": primary_evidence.get("summary"),
                "evidence": {
                    "domain": primary_evidence.get("domain"),
                    "score": primary_evidence.get("score"),
                    "feature_values": primary_evidence.get("feature_values"),
                    "reasons": primary_evidence.get("reasons"),
                },
            }
        )
    for evidence_item in secondary_evidence:
        findings.append(
            {
                "issue_type": str(
                    evidence_item.get("issue_type") or "secondary_evidence"
                ),
                "severity": str(evidence_item.get("severity") or "medium"),
                "summary": evidence_item.get("summary"),
                "evidence": evidence_item.get("evidence", {}),
            }
        )

    if trend_summary.get("findings"):
        findings.append(
            {
                "issue_type": "trend_context",
                "severity": "medium",
                "summary": trend_summary.get("summary"),
                "evidence": {
                    "trend_findings": list(trend_summary.get("findings") or [])[:3]
                },
            }
        )
    if anomaly_summary.get("windows"):
        lead_window = list(anomaly_summary.get("windows") or [])[0]
        findings.append(
            {
                "issue_type": "anomaly_context",
                "severity": str(lead_window.get("severity") or "medium").lower(),
                "summary": anomaly_summary.get("summary")
                or str(lead_window.get("reason") or ""),
                "evidence": {
                    "metric": lead_window.get("metric"),
                    "snapshot_label": lead_window.get("snapshot_label"),
                    "severity": lead_window.get("severity"),
                    "count": anomaly_summary.get("count"),
                },
            }
        )
    if key_evidence.get("summary_key_signals"):
        findings.append(
            {
                "issue_type": "deterministic_evidence",
                "severity": "low",
                "summary": "Key deterministic evidence was grouped for narrative synthesis.",
                "evidence": {
                    "summary_key_signals": key_evidence.get("summary_key_signals"),
                    "primary_reasons": key_evidence.get("primary_reasons"),
                },
            }
        )
    return findings


def _narrative_recommendations_from_grouped(
    grouped_findings: dict[str, Any],
) -> list[dict[str, Any]]:
    """Adapt grouped deterministic recommendations into the explanation prompt shape."""

    recommendations: list[dict[str, Any]] = []
    for recommendation in (
        grouped_findings.get("recommendation_summary", {}).get("items") or []
    ):
        recommendations.append(
            {
                "issue_type": (
                    "cpu_pressure"
                    if str(recommendation.get("domain") or "").upper() == "CPU"
                    else str(recommendation.get("domain") or "issue").lower()
                ),
                "severity": str(recommendation.get("priority") or "low").lower(),
                "recommendation": recommendation.get("action", ""),
                "rationale": recommendation.get("rationale", ""),
                "next_step": recommendation.get("title", ""),
            }
        )
    return recommendations


def _build_multi_snapshot_analysis(
    snapshot_contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    db_scope_metrics = _build_db_scope_metric_history(snapshot_contexts)
    time_series = _build_time_series(snapshot_contexts, db_scope_metrics)
    anomaly_windows = _build_anomaly_windows(snapshot_contexts, time_series)
    latest_snapshot = snapshot_contexts[-1]
    worst_snapshot = max(snapshot_contexts, key=_snapshot_score)
    latest_snapshot_summary = _build_latest_snapshot_summary(latest_snapshot)
    multi_snapshot_summary = _build_multi_snapshot_summary(
        snapshot_contexts,
        time_series,
        anomaly_windows,
        latest_snapshot_summary,
    )
    confidence = _build_confidence(
        snapshot_contexts,
        anomaly_windows,
        time_series,
    )
    decision_posture = _build_decision_posture(
        snapshot_contexts,
        anomaly_windows,
        confidence,
    )

    return {
        "ordered_snapshots": snapshot_contexts,
        "snapshot_labels": [context["snapshot_label"] for context in snapshot_contexts],
        "analysis_context": _build_analysis_context(snapshot_contexts),
        "db_scope_metrics": db_scope_metrics,
        "time_series": time_series,
        "latest_snapshot": latest_snapshot,
        "worst_snapshot": worst_snapshot,
        "anomaly_windows": anomaly_windows,
        "trend_findings": _build_trend_findings(time_series),
        "multi_snapshot_summary": multi_snapshot_summary,
        "latest_snapshot_summary": latest_snapshot_summary,
        "decision_posture": decision_posture,
        "confidence": confidence,
    }


def _compose_dashboard_narrative(
    ai_content: str,
    multi_snapshot_analysis: dict[str, Any],
    latest_context: dict[str, Any],
    oci_guidance: dict[str, Any],
) -> str:
    snapshot_count = len(multi_snapshot_analysis["ordered_snapshots"])
    trend_findings = multi_snapshot_analysis["trend_findings"]
    anomaly_windows = multi_snapshot_analysis["anomaly_windows"]
    anomaly_lines = (
        ["- Insufficient history for anomaly detection."]
        if snapshot_count < 2
        else (
            ["- No deterministic anomaly or event windows detected."]
            if not anomaly_windows
            else [
                (
                    f"- {window['snapshot_label']}: {window['metric']} "
                    f"({window['severity']}) — {window['reason']}"
                )
                for window in anomaly_windows
            ]
        )
    )
    trend_lines = (
        ["- Insufficient history for trend analysis."]
        if snapshot_count < 2
        else [f"- {finding}" for finding in trend_findings]
    )
    latest_summary = multi_snapshot_analysis["latest_snapshot_summary"]
    posture = multi_snapshot_analysis["decision_posture"]
    confidence = multi_snapshot_analysis["confidence"]

    recommended_actions = []
    for rec in latest_context["recommendations"][:5]:
        rec_dict = _to_dict(rec)
        recommended_actions.append(
            f"- {rec_dict.get('recommendation', '')} Next step: {rec_dict.get('next_step', '')}"
        )
    if not recommended_actions:
        recommended_actions = ["- No deterministic recommendations were generated."]

    risk_lines = [
        "- Single-interval signals can still dominate if history is sparse.",
        "- Missing metrics remain excluded rather than inferred.",
        "- Point-in-time improvements may hide recurring spikes outside the sampled intervals.",
    ]

    ai_addendum = ""
    if ai_content.strip():
        ai_addendum = (
            "\n\nDeterministic narrative retained the provider response as a "
            "secondary input for wording consistency."
        )
    technical_narrative = _build_technical_narrative_text(
        multi_snapshot_analysis,
        latest_summary,
        trend_lines,
        anomaly_lines,
        ai_addendum,
    )

    sections = [
        "Executive Summary",
        _build_multi_snapshot_executive_summary(multi_snapshot_analysis),
        "",
        "Technical Narrative",
        technical_narrative,
        "",
        "Root Cause Interpretation",
        _build_root_cause_interpretation(
            latest_context,
            multi_snapshot_analysis,
        ),
        "",
        "Recommended Action Plan",
        "\n".join(
            [
                "Decision Posture:",
                f"- {posture['posture']}: {posture['rationale']}",
                f"- Supporting guidance: {posture['supporting_guidance']}",
                "",
                *recommended_actions,
            ]
        ),
        "",
        "OCI Sizing Considerations",
        "\n".join(
            [
                oci_guidance["current_state_assessment"],
                "",
                oci_guidance["scaling_trigger_conditions"],
                "",
                oci_guidance["oci_architecture_guidance"],
            ]
        ),
        "",
        "Confidence Assessment",
        (f"{confidence['level']}\n\n" f"Reason: {confidence['reason']}"),
        "",
        "Risk of Being Wrong",
        "\n".join(risk_lines),
    ]
    return "\n".join(sections)


if __name__ == "__main__":
    env_loaded, env_path = _load_local_env_file()
    provider = _resolve_ai_provider()
    resolved_model = _resolve_ai_model_identifier(provider)
    runtime_config = _runtime_config()
    print("AI Provider Resolution:")
    print(f"  .env loaded: {'yes' if env_loaded else 'no'} ({env_path})")
    print(f"  provider: {provider}")
    print(f"  model: {resolved_model or '(not configured)'}")
    input_dir = Path("data/input")
    awr_files = sorted(input_dir.glob("*.out"))
    if not awr_files:
        raise FileNotFoundError("No AWR input files found in data/input")

    snapshot_contexts = [_build_snapshot_context(file_path) for file_path in awr_files]
    snapshot_contexts = sorted(snapshot_contexts, key=_snapshot_sort_key)
    snapshot_results = [context["result"] for context in snapshot_contexts]

    multi_snapshot_analysis = _build_multi_snapshot_analysis(snapshot_contexts)
    latest_context = multi_snapshot_analysis["latest_snapshot"]
    result = latest_context["result"]
    # The decision object is now the authoritative deterministic conclusion.
    runtime_feature_vector = _runtime_feature_vector(latest_context)
    decision_input = build_decision_input_from_score_result(
        awr_id=_runtime_awr_id(latest_context),
        score_result=None,
        anomaly_signals=_decision_anomaly_signals(
            latest_context,
            multi_snapshot_analysis,
        ),
        feature_evidence=runtime_feature_vector["feature_json"],
    )
    decision = build_decision(
        decision_input=decision_input,
    )
    # Recommendations are decision-driven; legacy issue-based recommendations
    # remain deprecated and are no longer the authoritative path.
    decision_recommendations = generate_decision_recommendations(decision)
    compatibility_recommendations = _dashboard_decision_recommendation_dicts(
        decision_recommendations
    )
    latest_context = {
        **latest_context,
        "recommendations": compatibility_recommendations,
        "decision": decision.to_dict(),
    }
    multi_snapshot_analysis["latest_snapshot"] = latest_context
    derived_pressure_metrics = latest_context["derived_pressure_metrics"]
    executive_summary = normalize_terms(
        _build_multi_snapshot_executive_summary(multi_snapshot_analysis)
    )
    feature_visual_series = _build_feature_visual_series(snapshot_contexts)
    generated_at_display = _format_generated_at_local()
    decision_posture = multi_snapshot_analysis["decision_posture"]
    db_ingestion_context = _db_ingestion_not_checked_context(
        "DB ingestion status not reported by current run."
    )
    if runtime_config.get("disable_similarity_intelligence"):
        analysis_awr_id = _runtime_awr_id(latest_context)
        db_ingestion_context = _db_ingestion_not_checked_context(
            "DB ingestion status not reported by current run."
        )
        similarity_intelligence = build_disabled_similarity_intelligence(
            "Disabled by DISABLE_SIMILARITY_INTELLIGENCE"
        )
    else:
        connection = None
        try:
            connection = get_db_connection()
            db_similarity_runtime = _prepare_db_backed_similarity_runtime(
                connection=connection,
                snapshot_contexts=snapshot_contexts,
                latest_context=latest_context,
            )
            analysis_awr_id = int(db_similarity_runtime["analysis_awr_id"])
            db_ingestion_context = db_similarity_runtime["db_ingestion"]
            similarity_intelligence = build_similarity_intelligence(
                connection=connection,
                awr_id=analysis_awr_id,
                feature_vector=runtime_feature_vector["feature_vector_record"][
                    "feature_vector"
                ],
                top_k=5,
            )
        except Exception as exc:
            analysis_awr_id = _runtime_awr_id(latest_context)
            print(f"Similarity intelligence failed: {type(exc).__name__}: {exc}")
            db_ingestion_context = _db_ingestion_not_checked_context(
                "DB ingestion status not reported by current run.",
                failed=True,
            )
            similarity_intelligence = build_failed_similarity_intelligence(str(exc))
        finally:
            if connection is not None:
                connection.close()
    decision_evidence = decision.evidence or {}
    domain_scores = decision_evidence.get("domain_scores", {})
    trends = {
        "findings": multi_snapshot_analysis["trend_findings"],
        "time_series": multi_snapshot_analysis["time_series"],
    }
    analysis_output = build_analysis_output(
        decision=decision,
        scores=domain_scores,
        trends=trends,
        similarity_intelligence=similarity_intelligence,
        recommendations=decision_recommendations,
        metadata={
            "awr_id": analysis_awr_id,
            "db_name": getattr(result.run_metadata, "db_name", None)
            or getattr(result.run_metadata, "database_name", None),
            "snapshot_begin": result.run_metadata.begin_snapshot_time,
            "snapshot_end": result.run_metadata.end_snapshot_time,
        },
    )
    memory_result = memory_orchestrator.persist_run_memory(
        phase4i_output=analysis_output,
        source_context={
            "analysis_run_id": analysis_awr_id,
            "source_files": awr_files,
            "latest_context": latest_context,
            "decision_posture": decision_posture,
            "analysis_timestamp": analysis_output["metadata"].get(
                "generated_at"
            ),
        },
        parser_output=snapshot_results,
    )
    memory_run_history_id = memory_result.get("run_history_id")
    dashboard_metadata = {
        **analysis_output["metadata"],
        "file_name": latest_context["file_name"],
        "snapshot_label": latest_context["snapshot_label"],
        "db_name": result.run_metadata.database_name,
        "dbid": result.run_metadata.db_id,
        "instance_name": result.run_metadata.instance_name,
        "host_name": result.run_metadata.host_name,
        "snapshot_begin": result.run_metadata.begin_snapshot_time,
        "snapshot_end": result.run_metadata.end_snapshot_time,
    }
    anomaly_windows = multi_snapshot_analysis["anomaly_windows"]
    grouped_findings = _grouped_deterministic_findings(
        decision=decision,
        canonical_recommendations=decision_recommendations,
        latest_context=latest_context,
        multi_snapshot_analysis=multi_snapshot_analysis,
    )
    # Legacy issue detection is transitional compatibility support only.
    # It is generated late near the reporting adapters that still need it.
    compatibility_issues = _get_compatibility_issues(latest_context)
    latest_context["compatibility_issues"] = compatibility_issues
    multi_snapshot_analysis["latest_snapshot"] = latest_context
    # Transitional compatibility helpers remain available for current dashboard
    # sections, but they do not drive the canonical result anymore.
    agentic_decision = _build_agentic_decision(compatibility_issues, decision_posture)
    oci_guidance = _build_oci_guidance(compatibility_issues, decision_posture)

    # LLM output is narrative-only. It operates on grouped deterministic
    # findings derived from the canonical decision and recommendations, and
    # it does not decide the primary issue, status, or recommendations.
    ai_narrative = generate_ai_narrative(
        result,
        _narrative_findings_from_grouped(grouped_findings),
        _narrative_recommendations_from_grouped(grouped_findings),
    )
    ai_response = generate_ai_response(
        provider=provider,
        system_role=ai_narrative["system_role"],
        prompt=ai_narrative["prompt"],
        expected_sections=ai_narrative["expected_sections"],
    )
    llm_explanation_text = _compose_dashboard_narrative(
        ai_response["content"],
        multi_snapshot_analysis,
        latest_context,
        oci_guidance,
    )
    llm_explanation = {
        "enabled": bool(ai_response["content"].strip()),
        "authoritative": False,
        "technical_explanation": llm_explanation_text,
        "executive_explanation": executive_summary,
        "action_explanation": grouped_findings["recommendation_summary"]["summary"],
        "provider": ai_response["provider"],
        "model": ai_response["model"],
        "prompt_context": {
            "system_role": ai_narrative["system_role"],
            "expected_sections": ai_narrative["expected_sections"],
            "prompt": ai_narrative["prompt"],
        },
    }
    compatibility_payload = {
        "issues": compatibility_issues,
        "recommendations": compatibility_recommendations,
        "agentic_decision": agentic_decision,
        "oci_guidance": oci_guidance,
        "ai_generated_narrative": llm_explanation_text,
        "ai_provider": ai_response["provider"],
        "ai_model": ai_response["model"],
    }
    ingestion_context = _build_ingestion_runtime_context(
        snapshot_contexts,
        awr_files,
        generated_at_display,
        db_ingestion_context,
    )
    comparison_context = _build_comparison_runtime_context(multi_snapshot_analysis)
    # Canonical payload is the authoritative backend contract.
    # Grouped deterministic findings are the structured input to the LLM explanation layer.
    # LLM explanation is non-authoritative, and compatibility fields exist only
    # to support the existing reporting/dashboard code paths.
    canonical_payload = {
        "product": {
            "title": "AWR Performance Intelligence Dashboard",
        },
        "metadata": dashboard_metadata,
        "scores": analysis_output["scores"],
        "trends": analysis_output["trends"],
        "anomalies": {
            "count": len(anomaly_windows),
            "windows": anomaly_windows,
        },
        "decision": analysis_output["decision"],
        "similarity_intelligence": analysis_output["similarity_intelligence"],
        "recommendations": analysis_output["recommendations"],
        "grouped_deterministic_findings": grouped_findings,
        "llm_explanation": llm_explanation,
        "compatibility": compatibility_payload,
    }
    base_time_series_charts = (
        multi_snapshot_analysis["db_scope_metrics"]["chart_payload"]
        if multi_snapshot_analysis["db_scope_metrics"].get("available")
        else {
            "snapshot_labels": multi_snapshot_analysis["snapshot_labels"],
            "cpu_trend": multi_snapshot_analysis["time_series"]["cpu_trend"],
            "io_trend": multi_snapshot_analysis["time_series"]["io_trend"],
            "commit_trend": multi_snapshot_analysis["time_series"]["commit_trend"],
            "concurrency_trend": multi_snapshot_analysis["time_series"][
                "concurrency_trend"
            ],
            "sql_concentration_trend": multi_snapshot_analysis["time_series"][
                "sql_concentration_trend"
            ],
            "hard_parses_trend": multi_snapshot_analysis["time_series"][
                "hard_parses_trend"
            ],
            "log_file_sync_trend": multi_snapshot_analysis["time_series"][
                "log_file_sync_trend"
            ],
            "temp_io_trend": multi_snapshot_analysis["time_series"]["temp_io_trend"],
            "pga_spill_trend": multi_snapshot_analysis["time_series"][
                "pga_spill_trend"
            ],
            "cluster_wait_trend": multi_snapshot_analysis["time_series"][
                "cluster_wait_trend"
            ],
            "gc_wait_trend": multi_snapshot_analysis["time_series"]["gc_wait_trend"],
            "dg_transport_lag_trend": multi_snapshot_analysis["time_series"][
                "dg_transport_lag_trend"
            ],
            "dg_apply_lag_trend": multi_snapshot_analysis["time_series"][
                "dg_apply_lag_trend"
            ],
            "exa_cell_io_trend": multi_snapshot_analysis["time_series"][
                "exa_cell_io_trend"
            ],
            "exa_offload_efficiency_trend": multi_snapshot_analysis["time_series"][
                "exa_offload_efficiency_trend"
            ],
        }
    )
    time_series_charts = _supplement_time_series_charts(
        base_time_series_charts,
        feature_visual_series,
    )
    violin_panel = _supplement_violin_panel_payload(
        build_violin_panel_data(snapshot_results),
        feature_visual_series,
    )
    report_data = {
        **canonical_payload,
        "title": canonical_payload["product"]["title"],
        "generated_at": generated_at_display,
        "executive_summary": executive_summary,
        "metadata": canonical_payload["metadata"],
        "scores": canonical_payload["scores"],
        "trends": canonical_payload["trends"],
        "anomalies": canonical_payload["anomalies"],
        "decision": canonical_payload["decision"],
        # Top-level recommendations are canonical deterministic output.
        # Compatibility recommendation shapes are adapter-only under compatibility.
        "recommendations": canonical_payload["recommendations"],
        "grouped_deterministic_findings": canonical_payload[
            "grouped_deterministic_findings"
        ],
        "llm_explanation": canonical_payload["llm_explanation"],
        "compatibility": canonical_payload["compatibility"],
        "analysis_output": canonical_payload,
        "issues": compatibility_payload["issues"],
        "top_sql": result.top_sql,
        "summary_key_signals": _build_summary_key_signals(latest_context),
        "violin_panel": violin_panel,
        "derived_pressure_metrics": derived_pressure_metrics,
        "derived_scalar_metrics": {
            "pga_spill_pressure": (derived_pressure_metrics["pga_spill_pressure"]),
            "temp_io_pressure": derived_pressure_metrics["temp_io_pressure"],
            "hard_parses_per_sec": (derived_pressure_metrics["hard_parses_per_sec"]),
        },
        "agentic_decision": compatibility_payload["agentic_decision"],
        "oci_guidance": compatibility_payload["oci_guidance"],
        "ai_generated_narrative": compatibility_payload["ai_generated_narrative"],
        "ai_provider": compatibility_payload["ai_provider"],
        "ai_model": compatibility_payload["ai_model"],
        "ingestion_context": ingestion_context,
        "comparison_context": comparison_context,
        "analysis_context": multi_snapshot_analysis["analysis_context"],
        "snapshot_labels": multi_snapshot_analysis["snapshot_labels"],
        "time_series": multi_snapshot_analysis["time_series"],
        "db_scope_metrics": multi_snapshot_analysis["db_scope_metrics"],
        "time_series_charts": time_series_charts,
        "anomaly_windows": multi_snapshot_analysis["anomaly_windows"],
        "multi_snapshot_summary": multi_snapshot_analysis["multi_snapshot_summary"],
        "latest_snapshot_summary": multi_snapshot_analysis["latest_snapshot_summary"],
        "decision_posture": multi_snapshot_analysis["decision_posture"],
        "confidence": multi_snapshot_analysis["confidence"],
        "memory_runtime": {
            "enabled": bool(memory_result.get("enabled")),
            "success": bool(memory_result.get("success")),
            "state": (
                "Off"
                if not memory_result.get("enabled")
                else "Active"
                if memory_result.get("success")
                else "Error"
            ),
        },
    }
    canonical_payload["screen_models"] = build_phase5_screen_models(
        canonical_payload,
        report_data=report_data,
    )
    report_data["screen_models"] = canonical_payload["screen_models"]
    dashboard_file = generate_html_dashboard(report_data)

    print("EXECUTIVE SUMMARY")
    print("-" * 80)
    print(executive_summary)

    print("\nTrend Findings:")
    for finding in multi_snapshot_analysis["trend_findings"]:
        print(f"  - {finding}")

    print("\nDB-Scope Engineered Metric Debug:")
    for line in multi_snapshot_analysis["db_scope_metrics"]["debug_lines"]:
        print(f"  - {line}")

    print("\nAnomaly Windows:")
    if not multi_snapshot_analysis["anomaly_windows"]:
        print("  Insufficient history or no anomalies detected.")
    else:
        for anomaly in multi_snapshot_analysis["anomaly_windows"]:
            print(
                "  - "
                f"{anomaly['snapshot_label']} | {anomaly['metric']} | "
                f"{anomaly['severity']} | {anomaly['reason']}"
            )

    print("\nLatest Snapshot Assessment:")
    print(f"  {multi_snapshot_analysis['latest_snapshot_summary']}")

    print("\nDecision Posture:")
    print(f"  {decision_posture['posture']}")
    print(f"  Rationale: {decision_posture['rationale']}")
    print(f"  Confidence: {decision_posture['confidence']}")

    print("\nDetected Issues:")
    if not compatibility_issues:
        print("  None")
    else:
        for issue in compatibility_issues:
            print(f"\n- issue_type: {issue['issue_type']}")
            print(f"  severity: {issue['severity']}")
            print(f"  summary: {issue['summary']}")
            print(f"  evidence: {issue['evidence']}")

    print("\nRecommendations:\n")
    for rec in compatibility_recommendations:
        rec_dict = _to_dict(rec)
        print(
            f"- {rec_dict.get('issue_type', 'unknown')} "
            f"({rec_dict.get('severity', 'unknown')})"
        )
        print(f"  Recommendation: {rec_dict.get('recommendation', '')}")
        print(f"  Rationale: {rec_dict.get('rationale', '')}")
        print(f"  Next Step: {rec_dict.get('next_step', '')}")
        print("  Actions:")
        for action in rec_dict.get("actions", []):
            print(f"    - {action}")
        print()

    print("Derived Metric Availability:\n")
    for line in derived_pressure_metrics["debug_summary"]:
        print(f"  {line}")
    print("\nDerived Metric Values:")
    print("  pga_spill_pressure: " f"{derived_pressure_metrics['pga_spill_pressure']}")
    print("  temp_io_pressure: " f"{derived_pressure_metrics['temp_io_pressure']}")
    print(
        "  hard_parses_per_sec: " f"{derived_pressure_metrics['hard_parses_per_sec']}"
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
    print(llm_explanation_text)
    print("\nHTML Dashboard:")
    print(f"  {dashboard_file}")
    print("\nMemory Persistence:")
    print(f"  enabled: {str(bool(memory_result.get('enabled'))).lower()}")
    if memory_result.get("enabled"):
        print(f"  success: {str(bool(memory_result.get('success'))).lower()}")
        print(f"  run_history_id: {memory_run_history_id}")
        if memory_result.get("errors"):
            print(f"  error: {memory_result['errors'][0]}")
    else:
        skipped = memory_result.get("skipped") or []
        print(f"  skipped: {', '.join(skipped) if skipped else 'none'}")
