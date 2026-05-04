"""Deterministic Phase 6 memory persistence for AWR analysis runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ingest.awr_adb_loader import get_db_connection

SNAPSHOT_TIME_FORMATS = (
    "%d-%b-%y %H:%M:%S",
    "%d-%b-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)

MEMORY_TABLE_DDL: tuple[tuple[str, str], ...] = (
    (
        "AWR_RUN_HISTORY",
        """
        CREATE TABLE AWR_RUN_HISTORY (
            RUN_HISTORY_ID        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            ANALYSIS_RUN_ID       NUMBER,
            SOURCE_FILE_NAME      VARCHAR2(512) NOT NULL,
            SOURCE_FILE_HASH      VARCHAR2(128) NOT NULL,
            DB_NAME               VARCHAR2(128),
            DBID                  NUMBER,
            INSTANCE_NAME         VARCHAR2(128),
            INSTANCE_NUMBER       NUMBER,
            AWR_BEGIN_TIME        TIMESTAMP(6),
            AWR_END_TIME          TIMESTAMP(6),
            ANALYSIS_TIMESTAMP    TIMESTAMP(6),
            DECISION_POSTURE      VARCHAR2(64),
            RISK_LEVEL            VARCHAR2(64),
            CONFIDENCE_SCORE      NUMBER(8,4),
            PRIMARY_DOMAIN        VARCHAR2(64),
            SECONDARY_DOMAINS     JSON,
            WORKLOAD_CLASS        VARCHAR2(64),
            TOPOLOGY_CLASS        VARCHAR2(64),
            PLATFORM_CLASS        VARCHAR2(64),
            PARSE_SUCCESS_RATE    NUMBER(8,4),
            KNOWN_SECTION_COUNT   NUMBER,
            UNKNOWN_SECTION_COUNT NUMBER,
            UNKNOWN_SIGNAL_COUNT  NUMBER,
            PHASE4I_OUTPUT_JSON   JSON,
            CREATED_AT            TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL,
            CONSTRAINT UK_P6_RUN_HASH UNIQUE (SOURCE_FILE_HASH)
        )
        """,
    ),
    (
        "AWR_RECOMMENDATION_HISTORY",
        """
        CREATE TABLE AWR_RECOMMENDATION_HISTORY (
            RECOMMENDATION_HISTORY_ID NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            RUN_HISTORY_ID            NUMBER NOT NULL,
            RECOMMENDATION_ID         VARCHAR2(128) NOT NULL,
            DOMAIN                    VARCHAR2(64),
            SEVERITY                  VARCHAR2(64),
            RECOMMENDATION_TYPE       VARCHAR2(128),
            RECOMMENDATION_TEXT       CLOB,
            SUPPORTING_EVIDENCE_JSON  JSON,
            CONFIDENCE_SCORE          NUMBER(8,4),
            RANK_ORDER                NUMBER,
            CREATED_AT                TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL,
            CONSTRAINT FK_P6_REC_RUN
                FOREIGN KEY (RUN_HISTORY_ID)
                REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID),
            CONSTRAINT UK_P6_REC_RUN_REC
                UNIQUE (RUN_HISTORY_ID, RECOMMENDATION_ID)
        )
        """,
    ),
    (
        "AWR_ACTION_HISTORY",
        """
        CREATE TABLE AWR_ACTION_HISTORY (
            ACTION_HISTORY_ID          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            RUN_HISTORY_ID             NUMBER NOT NULL,
            RECOMMENDATION_HISTORY_ID  NUMBER,
            ACTION_STATUS              VARCHAR2(64),
            ACTION_TYPE                VARCHAR2(128),
            ACTION_DESCRIPTION         CLOB,
            ACTION_NOTES               CLOB,
            ACTION_OWNER               VARCHAR2(256),
            ACTION_TIMESTAMP           TIMESTAMP(6),
            CREATED_AT                 TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL,
            CONSTRAINT FK_P6_ACT_RUN
                FOREIGN KEY (RUN_HISTORY_ID)
                REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID),
            CONSTRAINT FK_P6_ACT_REC
                FOREIGN KEY (RECOMMENDATION_HISTORY_ID)
                REFERENCES AWR_RECOMMENDATION_HISTORY (RECOMMENDATION_HISTORY_ID)
        )
        """,
    ),
    (
        "AWR_OUTCOME_HISTORY",
        """
        CREATE TABLE AWR_OUTCOME_HISTORY (
            OUTCOME_HISTORY_ID       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            BEFORE_RUN_HISTORY_ID    NUMBER NOT NULL,
            AFTER_RUN_HISTORY_ID     NUMBER NOT NULL,
            ACTION_HISTORY_ID        NUMBER,
            OUTCOME_STATUS           VARCHAR2(64),
            BEFORE_POSTURE           VARCHAR2(64),
            AFTER_POSTURE            VARCHAR2(64),
            BEFORE_PRIMARY_DOMAIN    VARCHAR2(64),
            AFTER_PRIMARY_DOMAIN     VARCHAR2(64),
            BEFORE_CONFIDENCE_SCORE  NUMBER(8,4),
            AFTER_CONFIDENCE_SCORE   NUMBER(8,4),
            METRIC_DELTA_JSON        JSON,
            DOMAIN_DELTA_JSON        JSON,
            OUTCOME_SUMMARY          CLOB,
            REVIEWER_NOTES           CLOB,
            CREATED_AT               TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL,
            CONSTRAINT FK_P6_OUT_PRE_RUN
                FOREIGN KEY (BEFORE_RUN_HISTORY_ID)
                REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID),
            CONSTRAINT FK_P6_OUT_POST_RUN
                FOREIGN KEY (AFTER_RUN_HISTORY_ID)
                REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID),
            CONSTRAINT FK_P6_OUT_ACT
                FOREIGN KEY (ACTION_HISTORY_ID)
                REFERENCES AWR_ACTION_HISTORY (ACTION_HISTORY_ID)
        )
        """,
    ),
    (
        "AWR_FEEDBACK_HISTORY",
        """
        CREATE TABLE AWR_FEEDBACK_HISTORY (
            FEEDBACK_ID                NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            RUN_HISTORY_ID             NUMBER NOT NULL,
            RECOMMENDATION_HISTORY_ID  NUMBER,
            ACTION_HISTORY_ID          NUMBER,
            OUTCOME_HISTORY_ID         NUMBER,
            FEEDBACK_TYPE              VARCHAR2(64),
            FEEDBACK_TEXT              CLOB,
            FEEDBACK_RATING            NUMBER,
            SUBMITTED_BY               VARCHAR2(256),
            SUBMITTED_TIMESTAMP        TIMESTAMP(6),
            REVIEW_STATUS              VARCHAR2(64),
            REVIEW_NOTES               CLOB,
            CONSTRAINT FK_P6_FB_RUN
                FOREIGN KEY (RUN_HISTORY_ID)
                REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID),
            CONSTRAINT FK_P6_FB_REC
                FOREIGN KEY (RECOMMENDATION_HISTORY_ID)
                REFERENCES AWR_RECOMMENDATION_HISTORY (RECOMMENDATION_HISTORY_ID),
            CONSTRAINT FK_P6_FB_ACT
                FOREIGN KEY (ACTION_HISTORY_ID)
                REFERENCES AWR_ACTION_HISTORY (ACTION_HISTORY_ID),
            CONSTRAINT FK_P6_FB_OUT
                FOREIGN KEY (OUTCOME_HISTORY_ID)
                REFERENCES AWR_OUTCOME_HISTORY (OUTCOME_HISTORY_ID)
        )
        """,
    ),
    (
        "AWR_UNKNOWN_SIGNAL_HISTORY",
        """
        CREATE TABLE AWR_UNKNOWN_SIGNAL_HISTORY (
            UNKNOWN_SIGNAL_ID      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            RUN_HISTORY_ID         NUMBER NOT NULL,
            SOURCE_FILE_NAME       VARCHAR2(512),
            DB_NAME                VARCHAR2(128),
            DBID                   NUMBER,
            UNKNOWN_TYPE           VARCHAR2(64) NOT NULL,
            SECTION_NAME           VARCHAR2(256),
            RAW_HEADER_TEXT        CLOB,
            RAW_SAMPLE_TEXT        CLOB,
            PARSER_CONTEXT         JSON,
            DETECTION_REASON       VARCHAR2(1000),
            FREQUENCY_COUNT        NUMBER DEFAULT 1 NOT NULL,
            FIRST_SEEN_TIMESTAMP   TIMESTAMP(6),
            LAST_SEEN_TIMESTAMP    TIMESTAMP(6),
            REVIEW_STATUS          VARCHAR2(64),
            CONSTRAINT FK_P6_UNK_RUN
                FOREIGN KEY (RUN_HISTORY_ID)
                REFERENCES AWR_RUN_HISTORY (RUN_HISTORY_ID)
        )
        """,
    ),
    (
        "AWR_PARSER_MAPPING_CANDIDATE",
        """
        CREATE TABLE AWR_PARSER_MAPPING_CANDIDATE (
            MAPPING_CANDIDATE_ID    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            UNKNOWN_SIGNAL_ID       NUMBER NOT NULL,
            PROPOSED_SECTION_TYPE   VARCHAR2(128),
            PROPOSED_DOMAIN         VARCHAR2(128),
            PROPOSED_METRIC_NAME    VARCHAR2(256),
            PROPOSED_MAPPING_JSON   JSON,
            APPROVAL_STATUS         VARCHAR2(64),
            APPROVED_BY             VARCHAR2(256),
            APPROVED_TIMESTAMP      TIMESTAMP(6),
            REVIEWER_NOTES          CLOB,
            CONSTRAINT FK_P6_MAP_UNK
                FOREIGN KEY (UNKNOWN_SIGNAL_ID)
                REFERENCES AWR_UNKNOWN_SIGNAL_HISTORY (UNKNOWN_SIGNAL_ID)
        )
        """,
    ),
    (
        "AWR_KNOWLEDGE_UPDATE_REQUEST",
        """
        CREATE TABLE AWR_KNOWLEDGE_UPDATE_REQUEST (
            KNOWLEDGE_UPDATE_ID       NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            SOURCE_REFERENCE_ID       VARCHAR2(256),
            UPDATE_TYPE               VARCHAR2(128),
            PROPOSED_CHANGE_SUMMARY   CLOB,
            PROPOSED_CHANGE_JSON      JSON,
            APPROVAL_STATUS           VARCHAR2(64),
            IMPLEMENTATION_STATUS     VARCHAR2(64),
            CREATED_AT                TIMESTAMP(6) DEFAULT SYSTIMESTAMP NOT NULL
        )
        """,
    ),
)


def persist_analysis(
    phase4i_output: dict[str, Any],
    source_context: dict[str, Any] | None,
    parser_output: Any,
) -> int:
    """Persist deterministic analysis memory and return RUN_HISTORY_ID."""

    source_context = source_context or {}
    connection = source_context.get("connection")
    managed_connection = connection is None
    if connection is None:
        connection = get_db_connection()

    try:
        _ensure_schema(connection)
        run_row = _build_run_history_row(phase4i_output, source_context, parser_output)

        existing_run_history_id = _find_run_history_id(
            connection,
            run_row["source_file_hash"],
        )
        if existing_run_history_id is not None:
            connection.commit()
            return existing_run_history_id

        run_history_id = _insert_run_history(connection, run_row)
        _insert_recommendations(
            connection,
            run_history_id,
            phase4i_output.get("recommendations") or [],
        )
        _insert_unknown_signals(
            connection,
            run_history_id,
            _unknown_signal_rows(
                parser_output,
                source_context,
                run_row["analysis_timestamp"] or datetime.now(),
            ),
        )
        connection.commit()
        return run_history_id
    except Exception:
        connection.rollback()
        raise
    finally:
        if managed_connection:
            connection.close()


def insert_action_history(
    *,
    run_history_id: int,
    action_type: str,
    action_description: str,
    action_status: str = "RECORDED",
    recommendation_history_id: int | None = None,
    action_owner: str | None = None,
    action_notes: str | None = None,
    action_timestamp: datetime | None = None,
    connection: Any | None = None,
) -> int:
    """Insert an append-only action history row and return ACTION_HISTORY_ID."""

    managed_connection = connection is None
    if connection is None:
        connection = get_db_connection()
    row = {
        "run_history_id": run_history_id,
        "recommendation_history_id": recommendation_history_id,
        "action_status": action_status,
        "action_type": action_type,
        "action_description": action_description,
        "action_notes": action_notes,
        "action_owner": action_owner,
        "action_timestamp": action_timestamp or datetime.now(timezone.utc),
    }
    try:
        _ensure_schema(connection)
        action_history_id = _insert_action_history_row(connection, row)
        connection.commit()
        return action_history_id
    except Exception:
        connection.rollback()
        raise
    finally:
        if managed_connection:
            connection.close()


def _ensure_schema(connection: Any) -> None:
    with connection.cursor() as cursor:
        for table_name, ddl in MEMORY_TABLE_DDL:
            cursor.execute(
                "select count(*) from user_tables where table_name = :table_name",
                {"table_name": table_name},
            )
            row = cursor.fetchone()
            if row and int(row[0]) > 0:
                continue
            cursor.execute(ddl)


def _find_run_history_id(connection: Any, source_file_hash: str) -> int | None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            select RUN_HISTORY_ID
              from AWR_RUN_HISTORY
             where SOURCE_FILE_HASH = :source_file_hash
            """,
            {"source_file_hash": source_file_hash},
        )
        row = cursor.fetchone()
    return int(row[0]) if row else None


def _insert_run_history(connection: Any, row: dict[str, Any]) -> int:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into AWR_RUN_HISTORY (
                ANALYSIS_RUN_ID,
                SOURCE_FILE_NAME,
                SOURCE_FILE_HASH,
                DB_NAME,
                DBID,
                INSTANCE_NAME,
                INSTANCE_NUMBER,
                AWR_BEGIN_TIME,
                AWR_END_TIME,
                ANALYSIS_TIMESTAMP,
                DECISION_POSTURE,
                RISK_LEVEL,
                CONFIDENCE_SCORE,
                PRIMARY_DOMAIN,
                SECONDARY_DOMAINS,
                WORKLOAD_CLASS,
                TOPOLOGY_CLASS,
                PLATFORM_CLASS,
                PARSE_SUCCESS_RATE,
                KNOWN_SECTION_COUNT,
                UNKNOWN_SECTION_COUNT,
                UNKNOWN_SIGNAL_COUNT,
                PHASE4I_OUTPUT_JSON
            ) values (
                :analysis_run_id,
                :source_file_name,
                :source_file_hash,
                :db_name,
                :dbid,
                :instance_name,
                :instance_number,
                :awr_begin_time,
                :awr_end_time,
                :analysis_timestamp,
                :decision_posture,
                :risk_level,
                :confidence_score,
                :primary_domain,
                :secondary_domains,
                :workload_class,
                :topology_class,
                :platform_class,
                :parse_success_rate,
                :known_section_count,
                :unknown_section_count,
                :unknown_signal_count,
                :phase4i_output_json
            )
            """,
            row,
        )
    run_history_id = _find_run_history_id(connection, row["source_file_hash"])
    if run_history_id is None:
        raise RuntimeError("AWR_RUN_HISTORY insert did not return a persisted row.")
    return run_history_id


def _insert_recommendations(
    connection: Any,
    run_history_id: int,
    recommendations: list[Any],
) -> None:
    rows = [
        _recommendation_row(run_history_id, index, recommendation)
        for index, recommendation in enumerate(recommendations, start=1)
    ]
    if not rows:
        return
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into AWR_RECOMMENDATION_HISTORY (
                RUN_HISTORY_ID,
                RECOMMENDATION_ID,
                DOMAIN,
                SEVERITY,
                RECOMMENDATION_TYPE,
                RECOMMENDATION_TEXT,
                SUPPORTING_EVIDENCE_JSON,
                CONFIDENCE_SCORE,
                RANK_ORDER
            ) values (
                :run_history_id,
                :recommendation_id,
                :domain,
                :severity,
                :recommendation_type,
                :recommendation_text,
                :supporting_evidence_json,
                :confidence_score,
                :rank_order
            )
            """,
            rows,
        )


def _insert_unknown_signals(
    connection: Any,
    run_history_id: int,
    unknown_signals: list[dict[str, Any]],
) -> None:
    rows = [dict(row, run_history_id=run_history_id) for row in unknown_signals]
    if not rows:
        return
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into AWR_UNKNOWN_SIGNAL_HISTORY (
                RUN_HISTORY_ID,
                SOURCE_FILE_NAME,
                DB_NAME,
                DBID,
                UNKNOWN_TYPE,
                SECTION_NAME,
                RAW_HEADER_TEXT,
                RAW_SAMPLE_TEXT,
                PARSER_CONTEXT,
                DETECTION_REASON,
                FREQUENCY_COUNT,
                FIRST_SEEN_TIMESTAMP,
                LAST_SEEN_TIMESTAMP,
                REVIEW_STATUS
            ) values (
                :run_history_id,
                :source_file_name,
                :db_name,
                :dbid,
                :unknown_type,
                :section_name,
                :raw_header_text,
                :raw_sample_text,
                :parser_context,
                :detection_reason,
                :frequency_count,
                :first_seen_timestamp,
                :last_seen_timestamp,
                :review_status
            )
            """,
            rows,
        )


def _insert_action_history_row(connection: Any, row: dict[str, Any]) -> int:
    with connection.cursor() as cursor:
        action_history_id = cursor.var(int)
        cursor.execute(
            """
            insert into AWR_ACTION_HISTORY (
                RUN_HISTORY_ID,
                RECOMMENDATION_HISTORY_ID,
                ACTION_STATUS,
                ACTION_TYPE,
                ACTION_DESCRIPTION,
                ACTION_NOTES,
                ACTION_OWNER,
                ACTION_TIMESTAMP
            ) values (
                :run_history_id,
                :recommendation_history_id,
                :action_status,
                :action_type,
                :action_description,
                :action_notes,
                :action_owner,
                :action_timestamp
            )
            returning ACTION_HISTORY_ID into :action_history_id
            """,
            {**row, "action_history_id": action_history_id},
        )
        value = action_history_id.getvalue()
        if isinstance(value, list):
            value = value[0] if value else None
        if value is None:
            raise RuntimeError("AWR_ACTION_HISTORY insert did not return ACTION_HISTORY_ID.")
        return int(value)


def _build_run_history_row(
    phase4i_output: dict[str, Any],
    source_context: dict[str, Any],
    parser_output: Any,
) -> dict[str, Any]:
    latest_result = _latest_parse_result(parser_output, source_context)
    metadata = getattr(latest_result, "run_metadata", None)
    phase4_metadata = phase4i_output.get("metadata") or {}
    decision = phase4i_output.get("decision") or {}
    classification = decision.get("classification") or {}
    parser_stats = _parser_stats(parser_output)
    source_file_name = _source_file_name(source_context, phase4_metadata)
    source_file_hash = _source_file_hash(source_context, phase4i_output)
    analysis_timestamp = _parse_timestamp(
        source_context.get("analysis_timestamp")
        or phase4_metadata.get("generated_at")
        or datetime.now(timezone.utc)
    )
    decision_posture = source_context.get("decision_posture") or {}

    return {
        "analysis_run_id": _safe_int(
            source_context.get("analysis_run_id") or phase4_metadata.get("awr_id")
        ),
        "source_file_name": source_file_name,
        "source_file_hash": source_file_hash,
        "db_name": (
            _safe_str(getattr(metadata, "database_name", None))
            or _safe_str(phase4_metadata.get("db_name"))
        ),
        "dbid": _safe_int(getattr(metadata, "db_id", None)),
        "instance_name": _safe_str(getattr(metadata, "instance_name", None)),
        "instance_number": _safe_int(getattr(metadata, "instance_number", None)),
        "awr_begin_time": _parse_timestamp(
            getattr(metadata, "begin_snapshot_time", None)
            or phase4_metadata.get("snapshot_begin")
        ),
        "awr_end_time": _parse_timestamp(
            getattr(metadata, "end_snapshot_time", None)
            or phase4_metadata.get("snapshot_end")
        ),
        "analysis_timestamp": analysis_timestamp,
        "decision_posture": _safe_str(
            decision_posture.get("posture")
            if isinstance(decision_posture, dict)
            else decision_posture
        ),
        "risk_level": _safe_str(decision.get("risk_level")),
        "confidence_score": _safe_float(decision.get("confidence")),
        "primary_domain": _safe_str(decision.get("primary_domain")),
        "secondary_domains": _json_dumps(decision.get("secondary_domains") or []),
        "workload_class": _safe_str(classification.get("workload_class")),
        "topology_class": _safe_str(classification.get("topology_class")),
        "platform_class": _safe_str(classification.get("platform_class")),
        "parse_success_rate": parser_stats["parse_success_rate"],
        "known_section_count": parser_stats["known_section_count"],
        "unknown_section_count": parser_stats["unknown_section_count"],
        "unknown_signal_count": parser_stats["unknown_signal_count"],
        "phase4i_output_json": _json_dumps(phase4i_output),
    }


def _parser_stats(parser_output: Any) -> dict[str, Any]:
    parse_results = _parse_results(parser_output)
    known_section_count = 0
    unknown_section_count = 0
    unknown_signal_count = 0
    parse_rates: list[float] = []

    for parse_result in parse_results:
        diagnostics = getattr(parse_result, "parse_diagnostics", None)
        if diagnostics is None:
            known_section_count += len(getattr(parse_result, "sections_found", {}) or {})
            continue
        known_section_count += _safe_int(
            getattr(diagnostics, "observed_section_count", None)
        ) or len(getattr(diagnostics, "sections_found", []) or [])
        unknown_sections = getattr(diagnostics, "unknown_sections", []) or []
        unknown_section_count += len(unknown_sections)
        unknown_signal_count += len(unknown_sections)
        unknown_signal_count += len(_missing_expected_sections(diagnostics))
        unknown_signal_count += len(_unmapped_metric_warnings(parse_result))
        rate = _safe_float(
            getattr(diagnostics, "parse_completeness_ratio", None)
            or getattr(diagnostics, "observed_section_rate", None)
        )
        if rate is not None:
            parse_rates.append(rate)

    return {
        "parse_success_rate": (
            round(sum(parse_rates) / len(parse_rates), 4) if parse_rates else None
        ),
        "known_section_count": known_section_count,
        "unknown_section_count": unknown_section_count,
        "unknown_signal_count": unknown_signal_count,
    }


def _unknown_signal_rows(
    parser_output: Any,
    source_context: dict[str, Any],
    seen_timestamp: datetime,
) -> list[dict[str, Any]]:
    del source_context
    aggregated: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}

    for parse_result in _parse_results(parser_output):
        metadata = getattr(parse_result, "run_metadata", None)
        diagnostics = getattr(parse_result, "parse_diagnostics", None)
        if diagnostics is None:
            continue

        source_file_name = _safe_str(
            getattr(diagnostics, "source_file_name", None)
            or getattr(metadata, "source_file_name", None)
        )
        db_name = _safe_str(getattr(metadata, "database_name", None))
        dbid = _safe_int(getattr(metadata, "db_id", None))

        for unknown_section in getattr(diagnostics, "unknown_sections", []) or []:
            row = {
                "source_file_name": source_file_name,
                "db_name": db_name,
                "dbid": dbid,
                "unknown_type": "UNKNOWN_SECTION",
                "section_name": None,
                "raw_header_text": _safe_str(getattr(unknown_section, "raw_text", None)),
                "raw_sample_text": "\n".join(
                    getattr(unknown_section, "context_after", []) or []
                )
                or None,
                "parser_context": _json_dumps(_unknown_section_context(unknown_section)),
                "detection_reason": (
                    "Unknown section header detected by deterministic parser diagnostics."
                ),
                "frequency_count": 1,
                "first_seen_timestamp": seen_timestamp,
                "last_seen_timestamp": seen_timestamp,
                "review_status": "NEW",
            }
            _aggregate_unknown_row(aggregated, row)

        for section_name, reason in _missing_expected_sections(diagnostics):
            row = {
                "source_file_name": source_file_name,
                "db_name": db_name,
                "dbid": dbid,
                "unknown_type": "MISSING_EXPECTED_SECTION",
                "section_name": section_name,
                "raw_header_text": None,
                "raw_sample_text": None,
                "parser_context": _json_dumps(_diagnostics_context(diagnostics)),
                "detection_reason": reason,
                "frequency_count": 1,
                "first_seen_timestamp": seen_timestamp,
                "last_seen_timestamp": seen_timestamp,
                "review_status": "NEW",
            }
            _aggregate_unknown_row(aggregated, row)

        for warning_text in _unmapped_metric_warnings(parse_result):
            row = {
                "source_file_name": source_file_name,
                "db_name": db_name,
                "dbid": dbid,
                "unknown_type": "UNMAPPED_METRIC",
                "section_name": None,
                "raw_header_text": warning_text,
                "raw_sample_text": None,
                "parser_context": _json_dumps(_diagnostics_context(diagnostics)),
                "detection_reason": (
                    "Parser warning indicated an unmapped metric without changing parser logic."
                ),
                "frequency_count": 1,
                "first_seen_timestamp": seen_timestamp,
                "last_seen_timestamp": seen_timestamp,
                "review_status": "NEW",
            }
            _aggregate_unknown_row(aggregated, row)

    return list(aggregated.values())


def _aggregate_unknown_row(
    aggregated: dict[tuple[str, str, str, str, str], dict[str, Any]],
    row: dict[str, Any],
) -> None:
    key = (
        str(row.get("unknown_type") or ""),
        str(row.get("source_file_name") or ""),
        str(row.get("section_name") or ""),
        str(row.get("raw_header_text") or ""),
        str(row.get("detection_reason") or ""),
    )
    existing = aggregated.get(key)
    if existing is None:
        aggregated[key] = row
        return
    existing["frequency_count"] = int(existing["frequency_count"]) + int(
        row["frequency_count"]
    )
    existing["last_seen_timestamp"] = row["last_seen_timestamp"]


def _missing_expected_sections(diagnostics: Any) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    for section_name in getattr(diagnostics, "required_sections_missing", []) or []:
        sections.append((str(section_name), "Required parser section was missing."))
    for section_name in getattr(diagnostics, "optional_core_sections_missing", []) or []:
        sections.append((str(section_name), "Optional core parser section was missing."))
    for section_name in getattr(diagnostics, "contextual_sections_missing", []) or []:
        sections.append((str(section_name), "Contextual parser section was relevant but missing."))
    return list(dict.fromkeys(sections))


def _unmapped_metric_warnings(parse_result: Any) -> list[str]:
    warnings = list(getattr(parse_result, "parse_warnings", []) or [])
    warnings.extend(list(getattr(parse_result, "parse_errors", []) or []))
    return [
        str(warning)
        for warning in warnings
        if "unmapped" in str(warning).lower()
    ]


def _recommendation_row(
    run_history_id: int,
    rank_order: int,
    recommendation: Any,
) -> dict[str, Any]:
    recommendation_dict = _to_dict(recommendation)
    domain = _safe_str(
        recommendation_dict.get("domain") or recommendation_dict.get("issue")
    )
    recommendation_type = _safe_str(
        recommendation_dict.get("category")
        or recommendation_dict.get("issue_type")
        or recommendation_dict.get("title")
    )
    recommendation_text = _safe_str(
        recommendation_dict.get("action")
        or recommendation_dict.get("recommendation")
        or recommendation_dict.get("title")
    )
    evidence = (
        recommendation_dict.get("source_signals")
        or recommendation_dict.get("evidence")
        or {}
    )
    recommendation_id = _safe_str(
        recommendation_dict.get("recommendation_id")
        or _recommendation_digest(domain, recommendation_type, recommendation_text)
    )
    return {
        "run_history_id": run_history_id,
        "recommendation_id": recommendation_id,
        "domain": domain,
        "severity": _safe_str(
            recommendation_dict.get("priority") or recommendation_dict.get("severity")
        ),
        "recommendation_type": recommendation_type,
        "recommendation_text": recommendation_text,
        "supporting_evidence_json": _json_dumps(evidence),
        "confidence_score": _safe_float(recommendation_dict.get("confidence")),
        "rank_order": rank_order,
    }


def _recommendation_digest(*parts: Any) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part or "").encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:32]


def _source_file_name(
    source_context: dict[str, Any],
    phase4_metadata: dict[str, Any],
) -> str:
    if source_context.get("source_file_name"):
        return str(source_context["source_file_name"])

    latest_context = source_context.get("latest_context") or {}
    if latest_context.get("file_name"):
        return str(latest_context["file_name"])

    source_files = _source_files(source_context)
    if len(source_files) == 1:
        return source_files[0].name
    if source_files:
        return f"{source_files[0].parent} ({len(source_files)} files)"

    return str(phase4_metadata.get("file_name") or "unknown")


def _source_file_hash(
    source_context: dict[str, Any],
    phase4i_output: dict[str, Any],
) -> str:
    if source_context.get("source_file_hash"):
        return str(source_context["source_file_hash"])

    source_files = _source_files(source_context)
    if len(source_files) == 1:
        return _hash_file(source_files[0])
    if source_files:
        digest = hashlib.sha256()
        for file_path in source_files:
            digest.update(file_path.name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(_hash_file(file_path).encode("ascii"))
            digest.update(b"\0")
        return digest.hexdigest()

    return hashlib.sha256(_json_dumps(phase4i_output).encode("utf-8")).hexdigest()


def _source_files(source_context: dict[str, Any]) -> list[Path]:
    raw_files = source_context.get("source_files") or source_context.get("awr_files") or []
    return [Path(file_path) for file_path in raw_files if Path(file_path).exists()]


def _hash_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _latest_parse_result(parser_output: Any, source_context: dict[str, Any]) -> Any:
    latest_context = source_context.get("latest_context") or {}
    if latest_context.get("result") is not None:
        return latest_context["result"]
    parse_results = _parse_results(parser_output)
    return parse_results[-1] if parse_results else None


def _parse_results(parser_output: Any) -> list[Any]:
    if parser_output is None:
        return []
    if isinstance(parser_output, (list, tuple)):
        return list(parser_output)
    if isinstance(parser_output, dict) and isinstance(parser_output.get("results"), list):
        return list(parser_output["results"])
    return [parser_output]


def _unknown_section_context(unknown_section: Any) -> dict[str, Any]:
    return {
        "parser_stage": getattr(unknown_section, "parser_stage", None),
        "line_number": getattr(unknown_section, "line_number", None),
        "classification_hint": getattr(unknown_section, "classification_hint", None),
        "context_before": getattr(unknown_section, "context_before", []) or [],
        "context_after": getattr(unknown_section, "context_after", []) or [],
        "source_file_path": getattr(unknown_section, "source_file_path", None),
    }


def _diagnostics_context(diagnostics: Any) -> dict[str, Any]:
    return {
        "parse_quality": getattr(diagnostics, "parse_quality", None),
        "parse_completeness_ratio": getattr(
            diagnostics,
            "parse_completeness_ratio",
            None,
        ),
        "source_file_path": getattr(diagnostics, "source_file_path", None),
    }


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "model_dump"):
        return value.model_dump()
    try:
        return asdict(value)
    except TypeError:
        return dict(getattr(value, "__dict__", {}) or {})


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except ValueError:
        pass

    parts = text.split()
    if len(parts) >= 3 and parts[0].isdigit():
        text = " ".join(parts[1:])
    for fmt in SNAPSHOT_TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
