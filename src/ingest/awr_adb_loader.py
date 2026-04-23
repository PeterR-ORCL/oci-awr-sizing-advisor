"""Batch loader for parsed Oracle AWR reports into ADB core tables."""

from __future__ import annotations

import hashlib
import importlib
import json
import logging
import os
import socket
import sys
import tempfile
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Protocol
from urllib.parse import urlparse

from dotenv import load_dotenv

from src.analysis.derived_metric_extractor import (
    extract_derived_pressure_metrics,
)
from src.analysis.trend_engine import persist_db_metric_trends
from src.models.parse_diagnostics import UnknownParserElement
from src.models.parse_result import ParseResult
from src.models.run_metadata import RunMetadata
from src.parser.awr_parser import parse_awr_file as parse_awr_report
from src.parser.section_registry import get_section_registry

LOGGER = logging.getLogger(__name__)


def _resolve_log_level() -> int:
    raw_level = str(os.getenv("AWR_LOG_LEVEL", "INFO")).strip().upper()
    resolved_level = getattr(logging, raw_level, logging.INFO)
    return resolved_level if isinstance(resolved_level, int) else logging.INFO


PIPELINE_NAME = "oci-awr-agentic-ai-sizing-advisor"
PIPELINE_VERSION = "1.0.0"
SNAPSHOT_TIME_FORMATS = (
    "%d-%b-%y %H:%M:%S",
    "%d-%b-%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)
SNAP_ID_BEGIN_PATTERNS = (
    re.compile(r"begin snap:\s*(\d+)", re.IGNORECASE),
    re.compile(r"begin snap id\s*[:=]?\s*(\d+)", re.IGNORECASE),
)
SNAP_ID_END_PATTERNS = (
    re.compile(r"end snap:\s*(\d+)", re.IGNORECASE),
    re.compile(r"end snap id\s*[:=]?\s*(\d+)", re.IGNORECASE),
)
DB_VERSION_PATTERNS = (
    re.compile(r"version\s*[:=]\s*([0-9][0-9A-Za-z\.\-_]+)", re.IGNORECASE),
    re.compile(r"release\s+([0-9][0-9A-Za-z\.\-_]+)", re.IGNORECASE),
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOTENV_PATH = PROJECT_ROOT / ".env"
FEATURE_SET_NAME = "awr_core_metrics"
FEATURE_SET_VERSION = "3.0.0"
SCORING_VECTOR_VERSION = "3.0.0"
SCORING_MODEL_CODE = "AWR_WEIGHTED_CORE"
SCORING_MODEL_DOMAIN = "SIZING"
FEATURE_REBUILD_MODE = "REBUILD_FEATURE_VECTORS"
REFRESH_PARSER_OUTPUT_JSON_MODE = "REFRESH_PARSER_OUTPUT_JSON"
DB_TREND_ANALYSIS_MODE = "DB_TREND_ANALYSIS"
SOURCE_MODE_LOCAL = "LOCAL"
SOURCE_MODE_OBJECT_STORAGE = "OBJECT_STORAGE"
_UNSET = object()
LOW_MATERIALITY_READ_LATENCY_MS = 1.5
LOW_MATERIALITY_USER_IO_PCT = 12.0
LOW_MATERIALITY_LOG_FILE_SYNC_MS = 3.0
LOW_MATERIALITY_COMMIT_PCT = 6.0
NATIVE_RAC_TEXT_PATTERNS = (
    "global cache",
    "cache fusion",
    " gc cr",
    " gc current",
    "gc buffer busy",
    " gcs ",
    " ges ",
    "interconnect",
)
PROMOTED_ENGINEERED_FEATURE_KEYS = (
    "WRITE_LATENCY_MS",
    "TEMP_WRITE_LATENCY_MS",
    "LOG_WRITE_LATENCY_MS",
    "NETWORK_WAIT_PCT_DB_TIME",
    "HARD_PARSE_PCT",
    "PGA_CACHE_HIT_PCT",
    "TEMP_SPILL_PCT",
    "SORTS_DISK_PCT",
    "WORKAREA_ONEPASS_PCT",
    "WORKAREA_MULTIPASS_PCT",
    "CURSOR_MUTEX_WAIT_PCT_DB_TIME",
    "CELL_SINGLE_BLOCK_LATENCY_MS",
    "CELL_MULTIBLOCK_LATENCY_MS",
    "STORAGE_INDEX_SAVINGS_PCT",
    "DB_CPU_PCT_DB_TIME",
    "REDO_GENERATION_PER_SEC",
)
SCORING_NORMALIZATION_DEFAULTS: dict[str, dict[str, float]] = {
    "CPU_UTIL_P95": {"min": 0.0, "max": 100.0},
    "DB_TIME_PER_TXN": {"median": 0.1, "iqr": 0.5},
    "READ_LATENCY_MS": {"min": 0.0, "max": 40.0},
    "LOG_FILE_SYNC_MS": {"min": 0.0, "max": 20.0},
    "TOP_SQL_LOAD_CONCENTRATION": {"min": 0.0, "max": 100.0},
    "AAS_PER_CPU": {"min": 0.0, "max": 4.0},
    "USER_IO_PRESSURE": {"min": 0.0, "max": 100.0},
    "COMMIT_PRESSURE": {"min": 0.0, "max": 100.0},
    "CONCURRENCY_PRESSURE": {"min": 0.0, "max": 100.0},
    "HARD_PARSES_PER_SEC": {"min": 0.0, "max": 100.0},
    "PGA_SPILL_PRESSURE": {"min": 0.0, "max": 1.0},
    "TEMP_IO_PRESSURE": {"min": 0.0, "max": 500.0},
    "THROUGHPUT_EXECUTIONS_PER_SEC": {"min": 0.0, "max": 20000.0},
    "THROUGHPUT_USER_CALLS_PER_SEC": {"min": 0.0, "max": 20000.0},
    "READ_MB_PER_SEC": {"min": 0.0, "max": 2048.0},
    "WRITE_MB_PER_SEC": {"min": 0.0, "max": 2048.0},
    "CLUSTER_WAIT_PCT_DB_TIME": {"min": 0.0, "max": 50.0},
    "GC_CR_WAIT_PCT_DB_TIME": {"min": 0.0, "max": 50.0},
    "GC_CURRENT_WAIT_PCT_DB_TIME": {"min": 0.0, "max": 50.0},
    "GC_BUFFER_BUSY_PCT_DB_TIME": {"min": 0.0, "max": 20.0},
    "TRANSPORT_LAG_SEC": {"min": 0.0, "max": 3600.0},
    "APPLY_LAG_SEC": {"min": 0.0, "max": 3600.0},
    "FAILOVER_EVENT_FLAG": {"min": 0.0, "max": 1.0},
    "ROLE_TRANSITION_FLAG": {"min": 0.0, "max": 1.0},
    "POST_FAILOVER_RECOVERY_FLAG": {"min": 0.0, "max": 1.0},
    "EXA_CELL_IO_PCT_DB_TIME": {"min": 0.0, "max": 50.0},
    "EXA_OFFLOAD_EFFICIENCY": {"min": 0.0, "max": 1.0},
    "EXA_STORAGE_INDEX_SAVINGS": {"min": 0.0, "max": 1.0},
    "SMART_SCAN_FLAG": {"min": 0.0, "max": 1.0},
    "INTERCONNECT_STRESS_FLAG": {"min": 0.0, "max": 1.0},
    "RAC_CONTENTION_FLAG": {"min": 0.0, "max": 1.0},
    "REDO_TRANSPORT_ISSUE_FLAG": {"min": 0.0, "max": 1.0},
}
TOPOLOGY_SCORING_FALLBACK_WEIGHTS: list[dict[str, Any]] = [
    {
        "feature_code": "CLUSTER_WAIT_PCT_DB_TIME",
        "feature_name": "Cluster Wait Pressure",
        "feature_domain": "CLUSTER",
        "feature_path": "$.CLUSTER_WAIT_PCT_DB_TIME",
        "weight_value": 0.14,
        "normalization_method": "MINMAX",
        "transform_method": "NONE",
        "polarity": "HIGH_BAD",
        "notes": "Fallback deterministic weight for RAC cluster waits",
    },
    {
        "feature_code": "GC_CURRENT_WAIT_PCT_DB_TIME",
        "feature_name": "GC Current Wait Pressure",
        "feature_domain": "CLUSTER",
        "feature_path": "$.GC_CURRENT_WAIT_PCT_DB_TIME",
        "weight_value": 0.10,
        "normalization_method": "MINMAX",
        "transform_method": "NONE",
        "polarity": "HIGH_BAD",
        "notes": "Fallback deterministic weight for RAC current block waits",
    },
    {
        "feature_code": "TRANSPORT_LAG_SEC",
        "feature_name": "Transport Lag",
        "feature_domain": "DG",
        "feature_path": "$.TRANSPORT_LAG_SEC",
        "weight_value": 0.12,
        "normalization_method": "MINMAX",
        "transform_method": "LOG1P",
        "polarity": "HIGH_BAD",
        "notes": "Fallback deterministic weight for DG transport lag",
    },
    {
        "feature_code": "APPLY_LAG_SEC",
        "feature_name": "Apply Lag",
        "feature_domain": "DG",
        "feature_path": "$.APPLY_LAG_SEC",
        "weight_value": 0.12,
        "normalization_method": "MINMAX",
        "transform_method": "LOG1P",
        "polarity": "HIGH_BAD",
        "notes": "Fallback deterministic weight for DG apply lag",
    },
    {
        "feature_code": "FAILOVER_EVENT_FLAG",
        "feature_name": "Failover Event",
        "feature_domain": "TOPOLOGY_EVENT",
        "feature_path": "$.FAILOVER_EVENT_FLAG",
        "weight_value": 0.18,
        "normalization_method": "MINMAX",
        "transform_method": "NONE",
        "polarity": "HIGH_BAD",
        "notes": "Fallback deterministic weight for failover events",
    },
    {
        "feature_code": "ROLE_TRANSITION_FLAG",
        "feature_name": "Role Transition Event",
        "feature_domain": "TOPOLOGY_EVENT",
        "feature_path": "$.ROLE_TRANSITION_FLAG",
        "weight_value": 0.12,
        "normalization_method": "MINMAX",
        "transform_method": "NONE",
        "polarity": "HIGH_BAD",
        "notes": "Fallback deterministic weight for role transitions",
    },
    {
        "feature_code": "POST_FAILOVER_RECOVERY_FLAG",
        "feature_name": "Post-Failover Recovery",
        "feature_domain": "TOPOLOGY_EVENT",
        "feature_path": "$.POST_FAILOVER_RECOVERY_FLAG",
        "weight_value": 0.12,
        "normalization_method": "MINMAX",
        "transform_method": "NONE",
        "polarity": "HIGH_BAD",
        "notes": "Fallback deterministic weight for post-failover recovery",
    },
    {
        "feature_code": "EXA_CELL_IO_PCT_DB_TIME",
        "feature_name": "Exadata Cell Wait Pressure",
        "feature_domain": "EXADATA",
        "feature_path": "$.EXA_CELL_IO_PCT_DB_TIME",
        "weight_value": 0.10,
        "normalization_method": "MINMAX",
        "transform_method": "NONE",
        "polarity": "HIGH_BAD",
        "notes": "Fallback deterministic weight for Exadata cell waits",
    },
    {
        "feature_code": "EXA_OFFLOAD_EFFICIENCY",
        "feature_name": "Exadata Offload Efficiency",
        "feature_domain": "EXADATA",
        "feature_path": "$.EXA_OFFLOAD_EFFICIENCY",
        "weight_value": 0.08,
        "normalization_method": "MINMAX",
        "transform_method": "NONE",
        "polarity": "HIGH_GOOD",
        "notes": "Fallback deterministic weight for beneficial Exadata offload",
    },
    {
        "feature_code": "SMART_SCAN_FLAG",
        "feature_name": "Smart Scan Active",
        "feature_domain": "EXADATA",
        "feature_path": "$.SMART_SCAN_FLAG",
        "weight_value": 0.06,
        "normalization_method": "MINMAX",
        "transform_method": "NONE",
        "polarity": "HIGH_GOOD",
        "notes": "Fallback deterministic weight for smart scan benefit",
    },
]


def _load_project_env() -> None:
    """Load the project .env file from a stable repo-root location."""

    load_dotenv(dotenv_path=DOTENV_PATH, override=False)


def _load_oci_config() -> dict[str, Any]:
    """Load OCI config for offline Object Storage and embedding helpers."""

    _load_project_env()
    try:
        import oci
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "oci is required for Object Storage and embedding hook integration. "
            "Install it with `pip install oci`."
        ) from exc

    config_profile = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")
    config_path = os.getenv("OCI_CONFIG_FILE", "~/.oci/config")
    return oci.config.from_file(os.path.expanduser(config_path), config_profile)


def _resolve_source_mode() -> str:
    raw_value = str(os.getenv("AWR_SOURCE_MODE", SOURCE_MODE_LOCAL)).strip().upper()
    if raw_value in {SOURCE_MODE_LOCAL, SOURCE_MODE_OBJECT_STORAGE}:
        return raw_value
    raise ValueError("AWR_SOURCE_MODE must be LOCAL or OBJECT_STORAGE.")


def _get_object_storage_namespace_from_env() -> str | None:
    for env_name in ("OCI_NAMESPACE", "OCI_OBJECT_STORAGE_NAMESPACE"):
        value = str(os.getenv(env_name, "")).strip()
        if value:
            return value
    return None


def _get_object_storage_bucket_name() -> str | None:
    for env_name in ("OCI_BUCKET_NAME", "OCI_OBJECT_STORAGE_BUCKET"):
        value = str(os.getenv(env_name, "")).strip()
        if value:
            return value
    return None


def _get_object_storage_prefix() -> str:
    for env_name in ("OCI_OBJECT_PREFIX", "OCI_OBJECT_STORAGE_PREFIX"):
        value = str(os.getenv(env_name, "")).strip().strip("/")
        if value:
            return value
    return "awr/raw"


def _has_any_object_storage_env() -> bool:
    return any(
        str(os.getenv(env_name, "")).strip()
        for env_name in (
            "OCI_NAMESPACE",
            "OCI_BUCKET_NAME",
            "OCI_OBJECT_PREFIX",
            "OCI_OBJECT_STORAGE_NAMESPACE",
            "OCI_OBJECT_STORAGE_BUCKET",
            "OCI_OBJECT_STORAGE_PREFIX",
        )
    )


def _resolve_object_storage_namespace_name(object_storage_client: Any) -> str:
    namespace_name = _get_object_storage_namespace_from_env()
    if namespace_name:
        return namespace_name
    namespace_response = object_storage_client.get_namespace()
    resolved_namespace = str(getattr(namespace_response, "data", "")).strip()
    if not resolved_namespace:
        raise ValueError("Unable to resolve OCI namespace for Object Storage.")
    return resolved_namespace


def _validate_optional_object_storage_upload_configuration() -> bool:
    bucket_name = _get_object_storage_bucket_name()
    if bucket_name:
        return True
    if _has_any_object_storage_env():
        LOGGER.warning(
            "Object Storage upload disabled: bucket name is not configured. "
            "Set OCI_BUCKET_NAME or OCI_OBJECT_STORAGE_BUCKET to enable uploads."
        )
    return False


def _validate_required_object_storage_configuration() -> tuple[str, str]:
    bucket_name = _get_object_storage_bucket_name()
    if not bucket_name:
        raise ValueError(
            "OBJECT_STORAGE mode requires OCI_BUCKET_NAME or OCI_OBJECT_STORAGE_BUCKET."
        )
    return bucket_name, _get_object_storage_prefix()


def _object_storage_is_configured() -> bool:
    return _validate_optional_object_storage_upload_configuration()


def _get_object_storage_client() -> Any:
    config = _load_oci_config()
    import oci

    return oci.object_storage.ObjectStorageClient(config)


def _build_object_storage_object_name(
    source_system_id: int,
    file_hash: str,
    source_file_name: str,
) -> str:
    prefix = _get_object_storage_prefix()
    safe_file_name = re.sub(r"[^A-Za-z0-9._-]+", "_", source_file_name)
    return f"{prefix}/source_system_{source_system_id}/{file_hash}/{safe_file_name}"


def _build_object_store_uri(
    namespace_name: str,
    bucket_name: str,
    object_name: str,
) -> str:
    return f"oci://{namespace_name}/{bucket_name}/{object_name}"


def _parse_object_store_uri(object_store_uri: str) -> tuple[str, str, str]:
    parsed = urlparse(object_store_uri)
    if parsed.scheme != "oci":
        raise ValueError(f"Unsupported object URI scheme: {object_store_uri}")
    namespace_name = parsed.netloc
    object_path = parsed.path.lstrip("/")
    path_parts = object_path.split("/", 1)
    if not namespace_name or len(path_parts) != 2:
        raise ValueError(f"Invalid OCI object URI: {object_store_uri}")
    bucket_name, object_name = path_parts
    if not bucket_name or not object_name:
        raise ValueError(f"Invalid OCI object URI: {object_store_uri}")
    return namespace_name, bucket_name, object_name


def upload_raw_awr_to_object_storage(
    file_path: str | Path,
    source_system_id: int,
    file_hash: str,
    object_storage_client: Any | None = None,
    namespace_name: str | None = None,
    bucket_name: str | None = None,
) -> str | None:
    """Upload one raw AWR file to Object Storage when configured."""

    if not _object_storage_is_configured():
        return None

    file_path_obj = Path(file_path)
    client = object_storage_client or _get_object_storage_client()
    resolved_namespace_name = namespace_name or _resolve_object_storage_namespace_name(
        client
    )
    resolved_bucket_name = bucket_name or _get_object_storage_bucket_name()
    if not resolved_bucket_name:
        raise ValueError(
            "Object Storage upload requires OCI_BUCKET_NAME or OCI_OBJECT_STORAGE_BUCKET."
        )
    object_name = _build_object_storage_object_name(
        source_system_id=source_system_id,
        file_hash=file_hash,
        source_file_name=file_path_obj.name,
    )
    with file_path_obj.open("rb") as source_handle:
        client.put_object(
            namespace_name=resolved_namespace_name,
            bucket_name=resolved_bucket_name,
            object_name=object_name,
            put_object_body=source_handle,
        )
    object_store_uri = _build_object_store_uri(
        resolved_namespace_name,
        resolved_bucket_name,
        object_name,
    )
    LOGGER.info("Raw AWR uploaded to Object Storage: %s", object_store_uri)
    return object_store_uri


def list_awr_objects(
    object_storage_client: Any,
    namespace_name: str,
    bucket_name: str,
    prefix: str,
) -> list[str]:
    """List candidate AWR objects under one Object Storage prefix."""

    response = object_storage_client.list_objects(
        namespace_name=namespace_name,
        bucket_name=bucket_name,
        prefix=prefix,
        fields="name,size,timeCreated",
        limit=1000,
    )
    data = getattr(response, "data", None)
    object_summaries = list(getattr(data, "objects", []) or [])
    object_names: list[str] = []
    for object_summary in object_summaries:
        object_name = str(getattr(object_summary, "name", "")).strip()
        if (
            not object_name
            or object_name.endswith("/")
            or not object_name.lower().endswith(".out")
        ):
            continue
        object_names.append(object_name)
    return sorted(object_names)


def download_object_to_temp(
    object_storage_client: Any,
    namespace_name: str,
    bucket_name: str,
    object_name: str,
) -> Path:
    """Download one Object Storage AWR object to a temp file for parsing."""

    response = object_storage_client.get_object(
        namespace_name=namespace_name,
        bucket_name=bucket_name,
        object_name=object_name,
    )
    suffix = Path(object_name).suffix or ".out"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_handle:
        temp_handle.write(response.data.content)
        return Path(temp_handle.name)


def _download_object_to_temp_file(object_store_uri: str) -> Path:
    """Download one Object Storage AWR object to a temp file for parsing."""

    namespace_name, bucket_name, object_name = _parse_object_store_uri(object_store_uri)
    client = _get_object_storage_client()
    return download_object_to_temp(
        object_storage_client=client,
        namespace_name=namespace_name,
        bucket_name=bucket_name,
        object_name=object_name,
    )


def _load_embedding_hook() -> Any:
    hook_path = str(os.getenv("AWR_EMBEDDING_HOOK", "")).strip()
    if not hook_path:
        return None
    module_name, separator, function_name = hook_path.partition(":")
    if not separator or not module_name or not function_name:
        raise ValueError(
            "AWR_EMBEDDING_HOOK must use the format 'module.path:function_name'."
        )
    module = importlib.import_module(module_name)
    hook = getattr(module, function_name, None)
    if hook is None or not callable(hook):
        raise ValueError(f"Configured embedding hook is not callable: {hook_path}")
    return hook


def _embedding_to_vector_literal(embedding: Any) -> str | None:
    if embedding is None:
        return None
    if isinstance(embedding, str):
        normalized = embedding.strip()
        return normalized or None
    if isinstance(embedding, (list, tuple)):
        numeric_values: list[str] = []
        for value in embedding:
            numeric_value = _safe_float(value)
            if numeric_value is None:
                return None
            numeric_values.append(str(numeric_value))
        return "[" + ",".join(numeric_values) + "]"
    return None


def generate_text_embedding(text: str) -> str | None:
    """Return a VECTOR literal string when an external embedding hook is configured."""

    normalized_text = text.strip()
    if not normalized_text:
        return None
    hook = _load_embedding_hook()
    if hook is None:
        return None
    return _embedding_to_vector_literal(hook(normalized_text))


class DbCursor(Protocol):
    def __enter__(self) -> "DbCursor": ...
    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None: ...
    def execute(self, statement: str, parameters: Any = ...) -> Any: ...
    def executemany(self, statement: str, parameters: Any) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchall(self) -> Any: ...


class DbConnection(Protocol):
    def cursor(self, *args: Any, **kwargs: Any) -> DbCursor: ...
    def commit(self) -> Any: ...
    def rollback(self) -> Any: ...
    def close(self) -> Any: ...


def get_db_connection() -> DbConnection:
    """Create a real python-oracledb connection to Autonomous Database."""

    _load_project_env()

    try:
        import oracledb
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "python-oracledb is required for ADB persistence. "
            "Install it with `pip install oracledb`."
        ) from exc

    user = os.getenv("ADB_USER")
    password = os.getenv("ADB_PASSWORD")
    dsn = os.getenv("ADB_DSN")
    config_dir = os.getenv("TNS_ADMIN")
    wallet_location = os.getenv("TNS_ADMIN")
    wallet_password = os.getenv("ADB_WALLET_PASSWORD")

    required_env = {
        "ADB_USER": user,
        "ADB_PASSWORD": password,
        "ADB_DSN": dsn,
        "TNS_ADMIN": config_dir,
        "ADB_WALLET_PASSWORD": wallet_password,
    }
    missing_env = [name for name, value in required_env.items() if not value]
    if missing_env:
        raise ValueError(
            "Missing required ADB environment variables: "
            + ", ".join(sorted(missing_env))
        )

    LOGGER.debug("ADB connect config: user=%s dsn=%s", user, dsn)
    LOGGER.debug(
        "ADB connect wallet: tns_admin=%s wallet_password_present=%s",
        config_dir,
        bool(wallet_password),
    )

    connect_kwargs: dict[str, Any] = {
        "user": user,
        "password": password,
        "dsn": dsn,
        "config_dir": config_dir,
        "wallet_location": wallet_location,
        "wallet_password": wallet_password,
    }

    conn = oracledb.connect(**connect_kwargs)
    LOGGER.info("ADB connection established")
    return conn


def load_awr_files(input_dir: str | Path) -> list[Path]:
    """Return all candidate AWR .out files in sorted order."""

    directory = Path(input_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Input directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {directory}")

    files: list[Path] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() != ".out":
            LOGGER.info("Skipping non-AWR file: %s", path)
            continue
        files.append(path)

    return files


def start_ingest_run(
    conn: Any,
    pipeline_name: str,
    pipeline_version: str,
    trigger_type: str,
) -> int:
    """Create one ingest-run audit record and return its identity."""

    run_guid = uuid.uuid4().hex
    params_json = _json_dumps(
        {
            "cwd": str(Path.cwd()),
            "execution_host": socket.gethostname(),
            "trigger_type": trigger_type,
        }
    )
    record = {
        "run_guid": run_guid,
        "pipeline_name": pipeline_name,
        "pipeline_version": pipeline_version,
        "trigger_type": trigger_type,
        "status": "STARTED",
        "requested_by": os.getenv("USER") or os.getenv("USERNAME"),
        "execution_host": socket.gethostname(),
        "notes": "AWR batch ingest started.",
        "parameters_json": params_json,
    }
    with conn.cursor() as cursor:
        cursor.execute(
            """
            insert into AWR_INGEST_RUN (
                RUN_GUID,
                PIPELINE_NAME,
                PIPELINE_VERSION,
                TRIGGER_TYPE,
                STATUS,
                REQUESTED_BY,
                EXECUTION_HOST,
                NOTES,
                PARAMETERS_JSON
            ) values (
                :run_guid,
                :pipeline_name,
                :pipeline_version,
                :trigger_type,
                :status,
                :requested_by,
                :execution_host,
                :notes,
                :parameters_json
            )
            """,
            record,
        )
    conn.commit()

    with conn.cursor() as cursor:
        cursor.execute(
            """
            select INGEST_RUN_ID
            from AWR_INGEST_RUN
            where RUN_GUID = :run_guid
            """,
            {"run_guid": run_guid},
        )
        row = cursor.fetchone()
    if not row:
        raise RuntimeError("Failed to create AWR_INGEST_RUN record.")
    ingest_run_id = int(row[0])
    LOGGER.info("Ingest run inserted: INGEST_RUN_ID=%s", ingest_run_id)
    return ingest_run_id


def finalize_ingest_run(
    conn: Any,
    ingest_run_id: int,
    status: str,
    file_count: int,
    success_count: int,
    error_count: int,
    notes: str | None = None,
    error_json: list[dict[str, Any]] | dict[str, Any] | None = None,
) -> None:
    """Finalize the ingest-run record with counts and optional errors."""

    with conn.cursor() as cursor:
        cursor.execute(
            """
            update AWR_INGEST_RUN
               set STATUS = :status,
                   ENDED_AT = SYSTIMESTAMP,
                   FILE_COUNT = :file_count,
                   SUCCESS_COUNT = :success_count,
                   ERROR_COUNT = :error_count,
                   NOTES = :notes,
                   ERROR_JSON = :error_json
             where INGEST_RUN_ID = :ingest_run_id
            """,
            {
                "status": status,
                "file_count": file_count,
                "success_count": success_count,
                "error_count": error_count,
                "notes": notes,
                "error_json": _json_dumps(error_json),
                "ingest_run_id": ingest_run_id,
            },
        )
    conn.commit()
    LOGGER.info(
        (
            "Ingest run finalized: INGEST_RUN_ID=%s STATUS=%s "
            "FILES=%s SUCCESS=%s ERRORS=%s"
        ),
        ingest_run_id,
        status,
        file_count,
        success_count,
        error_count,
    )


def _derive_operation_status(
    processed_count: int,
    error_count: int,
    downstream_error_count: int = 0,
) -> str:
    if error_count and processed_count == 0:
        return "FAILED"
    if error_count or downstream_error_count:
        return "COMPLETED_WITH_ERRORS"
    return "COMPLETED"


def parse_awr_file(file_path: str | Path) -> ParseResult:
    """Parse one AWR file through the existing parser stack."""

    return parse_awr_report(file_path)


def compute_file_hash(file_path: str | Path) -> str:
    """Return the SHA256 digest for one source file."""

    digest = hashlib.sha256()
    with Path(file_path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_source_system_record(parse_result: ParseResult) -> dict[str, Any]:
    """Map parsed metadata to one AWR_SOURCE_SYSTEM row."""

    metadata = parse_result.run_metadata
    topology = _ensure_native_feature_inputs(parse_result)
    db_name = metadata.database_name
    dbid = _to_int(metadata.db_id)
    instance_name = metadata.instance_name
    source_system_code = _build_source_system_code(
        dbid=dbid,
        db_name=db_name,
        instance_name=instance_name,
    )
    return {
        "source_system_code": source_system_code,
        "tenancy_name": None,
        "compartment_name": None,
        "environment_name": None,
        "customer_name": None,
        "application_name": _derive_application_name(parse_result),
        "db_name": db_name,
        "db_unique_name": db_name,
        "dbid": dbid,
        "platform_name": metadata.platform,
        "db_version": metadata.db_version
        or _extract_report_header_fields(metadata.source_file_path).get("db_version"),
        "rac_flag": "Y" if topology.get("is_rac") else "N",
        "adg_flag": "Y" if topology.get("is_dataguard") else "N",
        "cdb_flag": "N",
        "exadata_flag": "Y" if topology.get("is_exadata") else "N",
        "database_role": topology.get("database_role"),
        "instance_count": _to_int(topology.get("instance_count")),
        "primary_host_name": metadata.host_name,
        "region_name": None,
        "availability_domain": None,
        "tags_json": _json_dumps(
            {
                "source": "awr_text",
                "instance_name": instance_name,
                "database_role": topology.get("database_role"),
                "topology_class": topology.get("topology_class"),
                "platform_class": topology.get("platform_class"),
                "operational_event_class": topology.get(
                    "operational_event_class"
                ),
                "cpu_count": metadata.cpu_count,
                "core_count": metadata.core_count,
                "socket_count": metadata.socket_count,
                "memory_gb": metadata.memory_gb,
            }
        ),
    }


def upsert_source_system(
    conn: Any,
    source_system_record: dict[str, Any],
) -> int:
    """Insert or update one source-system record and return its identity."""

    clean_source_system_record = {
        key.lstrip(":"): value for key, value in source_system_record.items()
    }
    source_code_lookup = {
        "source_system_code": clean_source_system_record["source_system_code"]
    }
    db_identity_lookup = {
        "dbid": clean_source_system_record["dbid"],
        "db_unique_name": clean_source_system_record["db_unique_name"],
    }
    update_binds = _source_system_update_binds(clean_source_system_record)
    insert_binds = _source_system_insert_binds(clean_source_system_record)

    with conn.cursor() as cursor:
        cursor.execute(
            """
            select SOURCE_SYSTEM_ID
              from AWR_SOURCE_SYSTEM
             where SOURCE_SYSTEM_CODE = :source_system_code
            """,
            source_code_lookup,
        )
        row = cursor.fetchone()
        lookup_path = "source_system_code"

        if not row and db_identity_lookup["dbid"] is not None:
            cursor.execute(
                """
                select SOURCE_SYSTEM_ID
                  from AWR_SOURCE_SYSTEM
                 where DBID = :dbid
                   and DB_UNIQUE_NAME = :db_unique_name
                """,
                db_identity_lookup,
            )
            row = cursor.fetchone()
            lookup_path = "dbid/db_unique_name"

        if row:
            source_system_id = int(row[0])
            update_payload = dict(update_binds)
            update_payload["source_system_id"] = source_system_id
            cursor.execute(
                """
                update AWR_SOURCE_SYSTEM
                   set SOURCE_SYSTEM_CODE = :source_system_code,
                       TENANCY_NAME = :tenancy_name,
                       COMPARTMENT_NAME = :compartment_name,
                       ENVIRONMENT_NAME = :environment_name,
                       CUSTOMER_NAME = :customer_name,
                       APPLICATION_NAME = :application_name,
                       DB_NAME = :db_name,
                       DB_UNIQUE_NAME = :db_unique_name,
                       DBID = :dbid,
                       PLATFORM_NAME = :platform_name,
                       DB_VERSION = :db_version,
                       RAC_FLAG = :rac_flag,
                       ADG_FLAG = :adg_flag,
                       CDB_FLAG = :cdb_flag,
                       EXADATA_FLAG = :exadata_flag,
                       DATABASE_ROLE = :database_role,
                       INSTANCE_COUNT = :instance_count,
                       PRIMARY_HOST_NAME = :primary_host_name,
                       REGION_NAME = :region_name,
                       AVAILABILITY_DOMAIN = :availability_domain,
                       TAGS_JSON = :tags_json,
                       UPDATED_AT = SYSTIMESTAMP
                 where SOURCE_SYSTEM_ID = :source_system_id
                """,
                update_payload,
            )
            LOGGER.info(
                "Source system matched by %s: SOURCE_SYSTEM_ID=%s CODE=%s database_role=%s instance_count=%s",
                lookup_path,
                source_system_id,
                clean_source_system_record["source_system_code"],
                clean_source_system_record.get("database_role"),
                clean_source_system_record.get("instance_count"),
            )
            return source_system_id

        cursor.execute(
            """
            insert into AWR_SOURCE_SYSTEM (
                SOURCE_SYSTEM_CODE,
                TENANCY_NAME,
                COMPARTMENT_NAME,
                ENVIRONMENT_NAME,
                CUSTOMER_NAME,
                APPLICATION_NAME,
                DB_NAME,
                DB_UNIQUE_NAME,
                DBID,
                PLATFORM_NAME,
                DB_VERSION,
                RAC_FLAG,
                ADG_FLAG,
                CDB_FLAG,
                EXADATA_FLAG,
                DATABASE_ROLE,
                INSTANCE_COUNT,
                PRIMARY_HOST_NAME,
                REGION_NAME,
                AVAILABILITY_DOMAIN,
                TAGS_JSON
            ) values (
                :source_system_code,
                :tenancy_name,
                :compartment_name,
                :environment_name,
                :customer_name,
                :application_name,
                :db_name,
                :db_unique_name,
                :dbid,
                :platform_name,
                :db_version,
                :rac_flag,
                :adg_flag,
                :cdb_flag,
                :exadata_flag,
                :database_role,
                :instance_count,
                :primary_host_name,
                :region_name,
                :availability_domain,
                :tags_json
            )
            """,
            insert_binds,
        )

    with conn.cursor() as cursor:
        cursor.execute(
            """
            select SOURCE_SYSTEM_ID
              from AWR_SOURCE_SYSTEM
             where SOURCE_SYSTEM_CODE = :source_system_code
            """,
            source_code_lookup,
        )
        row = cursor.fetchone()
    if not row:
        raise RuntimeError("Failed to upsert AWR_SOURCE_SYSTEM record.")
    source_system_id = int(row[0])
    LOGGER.info(
        "Source system inserted: SOURCE_SYSTEM_ID=%s CODE=%s database_role=%s instance_count=%s",
        source_system_id,
        clean_source_system_record["source_system_code"],
        clean_source_system_record.get("database_role"),
        clean_source_system_record.get("instance_count"),
    )
    return source_system_id


def _source_system_update_binds(
    source_system_record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_system_code": source_system_record["source_system_code"],
        "tenancy_name": source_system_record["tenancy_name"],
        "compartment_name": source_system_record["compartment_name"],
        "environment_name": source_system_record["environment_name"],
        "customer_name": source_system_record["customer_name"],
        "application_name": source_system_record["application_name"],
        "db_name": source_system_record["db_name"],
        "db_unique_name": source_system_record["db_unique_name"],
        "dbid": source_system_record["dbid"],
        "platform_name": source_system_record["platform_name"],
        "db_version": source_system_record["db_version"],
        "rac_flag": source_system_record["rac_flag"],
        "adg_flag": source_system_record["adg_flag"],
        "cdb_flag": source_system_record["cdb_flag"],
        "exadata_flag": source_system_record["exadata_flag"],
        "database_role": source_system_record["database_role"],
        "instance_count": source_system_record["instance_count"],
        "primary_host_name": source_system_record["primary_host_name"],
        "region_name": source_system_record["region_name"],
        "availability_domain": source_system_record["availability_domain"],
        "tags_json": source_system_record["tags_json"],
    }


def _source_system_insert_binds(
    source_system_record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_system_code": source_system_record["source_system_code"],
        "tenancy_name": source_system_record["tenancy_name"],
        "compartment_name": source_system_record["compartment_name"],
        "environment_name": source_system_record["environment_name"],
        "customer_name": source_system_record["customer_name"],
        "application_name": source_system_record["application_name"],
        "db_name": source_system_record["db_name"],
        "db_unique_name": source_system_record["db_unique_name"],
        "dbid": source_system_record["dbid"],
        "platform_name": source_system_record["platform_name"],
        "db_version": source_system_record["db_version"],
        "rac_flag": source_system_record["rac_flag"],
        "adg_flag": source_system_record["adg_flag"],
        "cdb_flag": source_system_record["cdb_flag"],
        "exadata_flag": source_system_record["exadata_flag"],
        "database_role": source_system_record["database_role"],
        "instance_count": source_system_record["instance_count"],
        "primary_host_name": source_system_record["primary_host_name"],
        "region_name": source_system_record["region_name"],
        "availability_domain": source_system_record["availability_domain"],
        "tags_json": source_system_record["tags_json"],
    }


def build_report_record(
    parse_result: ParseResult,
    file_path: str | Path,
    file_hash: str,
    source_system_id: int,
    ingest_run_id: int,
    object_store_uri: str | None = None,
    source_file_name_override: str | None = None,
    source_file_path_override: Any = _UNSET,
) -> dict[str, Any]:
    """Map one parsed AWR file into an AWR_REPORT row."""

    metadata = parse_result.run_metadata
    file_path_obj = Path(file_path)
    source_file_name = source_file_name_override or file_path_obj.name
    if source_file_path_override is _UNSET:
        source_file_path = str(file_path_obj.resolve())
    elif source_file_path_override is None:
        source_file_path = None
    else:
        source_file_path = str(Path(source_file_path_override).expanduser())
    header_fields = _extract_report_header_fields(file_path_obj)
    snap_begin = normalize_timestamp(metadata.begin_snapshot_time)
    snap_end = normalize_timestamp(metadata.end_snapshot_time)
    if snap_begin is None and metadata.begin_snapshot_time:
        LOGGER.warning(
            "Could not normalize SNAP_TIME_BEGIN for %s: %r",
            file_path_obj.name,
            metadata.begin_snapshot_time,
        )
    if snap_end is None and metadata.end_snapshot_time:
        LOGGER.warning(
            "Could not normalize SNAP_TIME_END for %s: %r",
            file_path_obj.name,
            metadata.end_snapshot_time,
        )
    elapsed_minutes = None
    if snap_begin and snap_end:
        elapsed_minutes = round(
            (snap_end - snap_begin).total_seconds() / 60.0,
            2,
        )

    parse_status = "PARTIAL" if parse_result.parse_warnings else "PARSED"
    report_record = {
        "source_system_id": source_system_id,
        "ingest_run_id": ingest_run_id,
        "replay_of_awr_id": None,
        "source_file_name": source_file_name,
        "source_file_path": source_file_path,
        "object_store_uri": object_store_uri,
        "file_hash_sha256": file_hash,
        "file_size_bytes": file_path_obj.stat().st_size,
        "report_format": "AWR_OUT",
        "ingest_mode": os.getenv("AWR_INGEST_MODE", "NORMAL").upper(),
        "db_name": metadata.database_name,
        "dbid": _to_int(metadata.db_id),
        "instance_name": metadata.instance_name,
        "instance_number": _to_int(metadata.instance_number),
        "host_name": metadata.host_name,
        "platform_name": metadata.platform,
        "db_version": metadata.db_version or header_fields.get("db_version"),
        "snap_id_begin": header_fields.get("snap_id_begin"),
        "snap_id_end": header_fields.get("snap_id_end"),
        "snap_time_begin": snap_begin,
        "snap_time_end": snap_end,
        "snap_elapsed_minutes": elapsed_minutes,
        "parse_status": parse_status,
        "report_class": None,
        "workload_class": _derive_workload_class(parse_result),
        "anomaly_flag": "N",
        "raw_metadata_json": _json_dumps(asdict(parse_result.run_metadata)),
        "raw_header_json": _json_dumps(header_fields),
        "parser_output_json": _json_dumps(parse_result.to_dict()),
        "parser_warnings_json": _json_dumps(parse_result.parse_warnings),
    }
    LOGGER.debug(
        "Prepared report timestamps: snap_time_begin=%r (%s), snap_time_end=%r (%s)",
        report_record["snap_time_begin"],
        type(report_record["snap_time_begin"]).__name__,
        report_record["snap_time_end"],
        type(report_record["snap_time_end"]).__name__,
    )
    return report_record


def _allow_duplicate_report_ingest(report_record: dict[str, Any]) -> bool:
    """Return True when duplicate logical reports are explicitly allowed."""

    ingest_mode = str(report_record.get("ingest_mode") or "").upper()
    override_flag = str(
        os.getenv("AWR_ALLOW_DUPLICATE_REPORTS", "N")
    ).strip().upper()
    return ingest_mode == "REPLAY" or override_flag in {
        "1",
        "Y",
        "YES",
        "TRUE",
    }


def find_duplicate_report(
    conn: Any,
    report_record: dict[str, Any],
) -> tuple[int, str] | None:
    """Return an existing AWR_ID when the logical report already exists."""

    exact_hash_binds = {
        "source_system_id": report_record["source_system_id"],
        "file_hash_sha256": report_record["file_hash_sha256"],
    }
    with conn.cursor() as cursor:
        cursor.execute(
            """
            select AWR_ID
              from AWR_REPORT
             where SOURCE_SYSTEM_ID = :source_system_id
               and FILE_HASH_SHA256 = :file_hash_sha256
             order by AWR_ID desc
             fetch first 1 rows only
            """,
            exact_hash_binds,
        )
        row = cursor.fetchone()
    if row:
        return int(row[0]), "source_system_id + file_hash_sha256"

    logical_key_fields = (
        report_record.get("dbid"),
        report_record.get("instance_number"),
        report_record.get("snap_id_begin"),
        report_record.get("snap_id_end"),
        report_record.get("snap_time_begin"),
        report_record.get("snap_time_end"),
    )
    if not all(value is not None for value in logical_key_fields):
        return None

    logical_binds = {
        "source_system_id": report_record["source_system_id"],
        "dbid": report_record["dbid"],
        "instance_number": report_record["instance_number"],
        "snap_id_begin": report_record["snap_id_begin"],
        "snap_id_end": report_record["snap_id_end"],
        "snap_time_begin": report_record["snap_time_begin"],
        "snap_time_end": report_record["snap_time_end"],
    }
    with conn.cursor() as cursor:
        cursor.execute(
            """
            select AWR_ID
              from AWR_REPORT
             where SOURCE_SYSTEM_ID = :source_system_id
               and DBID = :dbid
               and INSTANCE_NUMBER = :instance_number
               and SNAP_ID_BEGIN = :snap_id_begin
               and SNAP_ID_END = :snap_id_end
               and SNAP_TIME_BEGIN = :snap_time_begin
               and SNAP_TIME_END = :snap_time_end
             order by AWR_ID desc
             fetch first 1 rows only
            """,
            logical_binds,
        )
        row = cursor.fetchone()
    if row:
        return (
            int(row[0]),
            "source_system_id + dbid + instance_number + snapshot window",
        )
    return None


def insert_report(conn: Any, report_record: dict[str, Any]) -> int:
    """Insert one AWR_REPORT row and return its identity."""

    timestamp_fields = (
        "snap_time_begin",
        "snap_time_end",
    )
    for field_name in timestamp_fields:
        field_value = report_record.get(field_name)
        LOGGER.debug(
            "Report timestamp bind %s=%r type=%s",
            field_name,
            field_value,
            type(field_value).__name__,
        )

    with conn.cursor() as cursor:
        LOGGER.debug(
            "Executing AWR_REPORT insert with timestamps: snap_time_begin=%r (%s), "
            "snap_time_end=%r (%s)",
            report_record.get("snap_time_begin"),
            type(report_record.get("snap_time_begin")).__name__,
            report_record.get("snap_time_end"),
            type(report_record.get("snap_time_end")).__name__,
        )
        cursor.execute(
            """
            insert into AWR_REPORT (
                SOURCE_SYSTEM_ID,
                INGEST_RUN_ID,
                REPLAY_OF_AWR_ID,
                SOURCE_FILE_NAME,
                SOURCE_FILE_PATH,
                OBJECT_STORE_URI,
                FILE_HASH_SHA256,
                FILE_SIZE_BYTES,
                REPORT_FORMAT,
                INGEST_MODE,
                DB_NAME,
                DBID,
                INSTANCE_NAME,
                INSTANCE_NUMBER,
                HOST_NAME,
                PLATFORM_NAME,
                DB_VERSION,
                SNAP_ID_BEGIN,
                SNAP_ID_END,
                SNAP_TIME_BEGIN,
                SNAP_TIME_END,
                SNAP_ELAPSED_MINUTES,
                PARSE_STATUS,
                REPORT_CLASS,
                WORKLOAD_CLASS,
                ANOMALY_FLAG,
                RAW_METADATA_JSON,
                RAW_HEADER_JSON,
                PARSER_OUTPUT_JSON,
                PARSER_WARNINGS_JSON
            ) values (
                :source_system_id,
                :ingest_run_id,
                :replay_of_awr_id,
                :source_file_name,
                :source_file_path,
                :object_store_uri,
                :file_hash_sha256,
                :file_size_bytes,
                :report_format,
                :ingest_mode,
                :db_name,
                :dbid,
                :instance_name,
                :instance_number,
                :host_name,
                :platform_name,
                :db_version,
                :snap_id_begin,
                :snap_id_end,
                :snap_time_begin,
                :snap_time_end,
                :snap_elapsed_minutes,
                :parse_status,
                :report_class,
                :workload_class,
                :anomaly_flag,
                :raw_metadata_json,
                :raw_header_json,
                :parser_output_json,
                :parser_warnings_json
            )
            """,
            report_record,
        )

    lookup_record = {
        "ingest_run_id": report_record["ingest_run_id"],
        "source_file_path": report_record["source_file_path"],
        "file_hash_sha256": report_record["file_hash_sha256"],
    }
    with conn.cursor() as cursor:
        cursor.execute(
            """
            select AWR_ID
              from AWR_REPORT
             where INGEST_RUN_ID = :ingest_run_id
               and SOURCE_FILE_PATH = :source_file_path
               and FILE_HASH_SHA256 = :file_hash_sha256
             order by AWR_ID desc
             fetch first 1 rows only
            """,
            lookup_record,
        )
        row = cursor.fetchone()
    if not row:
        raise RuntimeError("Failed to insert AWR_REPORT row.")
    awr_id = int(row[0])
    LOGGER.info(
        "Report inserted: AWR_ID=%s FILE=%s",
        awr_id,
        report_record["source_file_name"],
    )
    return awr_id


def build_metric_fact_rows(
    parse_result: ParseResult,
    awr_id: int,
    source_system_id: int,
) -> list[dict[str, Any]]:
    """Build useful normalized metric facts from the parsed report."""

    snap_begin, snap_end = _require_snapshot_window(parse_result)
    derived = extract_derived_pressure_metrics(parse_result)
    rows: list[dict[str, Any]] = []

    for metric in parse_result.cpu_metrics:
        metric_group = str(metric.get("metric_group") or "")
        metric_name = str(metric.get("metric_name") or "")
        if metric_group == "load_profile":
            rows.append(
                _metric_fact_row(
                    awr_id=awr_id,
                    source_system_id=source_system_id,
                    snap_begin=snap_begin,
                    snap_end=snap_end,
                    domain="load_profile",
                    name=metric_name,
                    value=metric.get("per_second"),
                    unit="per_second",
                    subtype="per_second",
                    metric_json=metric,
                )
            )
            if metric.get("per_transaction") is not None:
                rows.append(
                    _metric_fact_row(
                        awr_id=awr_id,
                        source_system_id=source_system_id,
                        snap_begin=snap_begin,
                        snap_end=snap_end,
                        domain="load_profile",
                        name=metric_name,
                        value=metric.get("per_transaction"),
                        unit="per_transaction",
                        subtype="per_transaction",
                        metric_json=metric,
                    )
                )
        elif metric_group in {"instance_efficiency", "host_cpu"}:
            rows.append(
                _metric_fact_row(
                    awr_id=awr_id,
                    source_system_id=source_system_id,
                    snap_begin=snap_begin,
                    snap_end=snap_end,
                    domain=metric_group,
                    name=metric_name,
                    value=metric.get("metric_value"),
                    unit=metric.get("metric_unit"),
                    metric_json=metric,
                )
            )

    for name, value, unit in (
        ("pga_spill_pressure", derived.get("pga_spill_pressure"), "ratio"),
        ("temp_io_pressure", derived.get("temp_io_pressure"), "per_second"),
        (
            "hard_parses_per_sec",
            derived.get("hard_parses_per_sec"),
            "per_second",
        ),
    ):
        if value is None:
            continue
        rows.append(
            _metric_fact_row(
                awr_id=awr_id,
                source_system_id=source_system_id,
                snap_begin=snap_begin,
                snap_end=snap_end,
                domain="derived",
                name=name,
                value=value,
                unit=unit,
                metric_json={
                    "raw": derived.get("raw"),
                    "availability": derived.get("availability"),
                },
            )
        )

    return [row for row in rows if row["metric_value_num"] is not None]


def insert_metric_facts(conn: Any, metric_rows: list[dict[str, Any]]) -> None:
    """Insert metric fact rows in bulk."""

    if not metric_rows:
        return
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            insert into AWR_METRIC_FACT (
                AWR_ID,
                SOURCE_SYSTEM_ID,
                SNAP_TIME_BEGIN,
                SNAP_TIME_END,
                METRIC_DOMAIN,
                METRIC_NAME,
                METRIC_SUBTYPE,
                DIMENSION_1,
                DIMENSION_2,
                DIMENSION_3,
                METRIC_VALUE_NUM,
                METRIC_VALUE_TXT,
                UNIT_OF_MEASURE,
                VALUE_DIRECTION,
                BASELINE_VALUE_NUM,
                DELTA_VALUE_NUM,
                ZSCORE_VALUE,
                PERCENTILE_VALUE,
                METRIC_JSON
            ) values (
                :awr_id,
                :source_system_id,
                :snap_time_begin,
                :snap_time_end,
                :metric_domain,
                :metric_name,
                :metric_subtype,
                :dimension_1,
                :dimension_2,
                :dimension_3,
                :metric_value_num,
                :metric_value_txt,
                :unit_of_measure,
                :value_direction,
                :baseline_value_num,
                :delta_value_num,
                :zscore_value,
                :percentile_value,
                :metric_json
            )
            """,
            metric_rows,
        )
    LOGGER.info("Metric facts inserted: %s", len(metric_rows))


def build_top_sql_fact_rows(
    parse_result: ParseResult,
    awr_id: int,
    source_system_id: int,
) -> list[dict[str, Any]]:
    """Build top-SQL fact rows from parsed top SQL output."""

    if not parse_result.top_sql:
        return []

    snap_begin, snap_end = _require_snapshot_window(parse_result)
    rows: list[dict[str, Any]] = []
    for rank, sql_row in enumerate(parse_result.top_sql, start=1):
        sql_id = str(sql_row.get("sql_id") or "").strip()
        if not sql_id:
            continue
        elapsed_seconds = _safe_float(sql_row.get("elapsed_time_seconds"))
        executions = _safe_float(sql_row.get("executions"))
        cpu_per_exec = None
        if elapsed_seconds is not None and executions and executions > 0:
            cpu_per_exec = None
        rows.append(
            {
                "awr_id": awr_id,
                "source_system_id": source_system_id,
                "snap_time_begin": snap_begin,
                "snap_time_end": snap_end,
                "sql_id": sql_id,
                "plan_hash_value": _to_int(sql_row.get("plan_hash_value")),
                "module_name": sql_row.get("module"),
                "parsing_schema_name": sql_row.get("parsing_schema_name"),
                "rank_by_elapsed": rank,
                "rank_by_cpu": None,
                "rank_by_gets": None,
                "rank_by_reads": None,
                "rank_by_executions": None,
                "elapsed_time_sec": elapsed_seconds,
                "cpu_time_sec": _safe_float(sql_row.get("cpu_time_seconds")),
                "io_time_sec": _safe_float(sql_row.get("io_time_seconds")),
                "buffer_gets": _safe_float(sql_row.get("buffer_gets")),
                "disk_reads": _safe_float(sql_row.get("disk_reads")),
                "executions": executions,
                "rows_processed": _safe_float(sql_row.get("rows_processed")),
                "elapsed_per_exec_sec": _milliseconds_to_seconds(
                    sql_row.get("elapsed_per_exec_ms")
                ),
                "cpu_per_exec_sec": cpu_per_exec,
                "gets_per_exec": _per_exec(
                    sql_row.get("buffer_gets"),
                    sql_row.get("executions"),
                ),
                "reads_per_exec": _per_exec(
                    sql_row.get("disk_reads"),
                    sql_row.get("executions"),
                ),
                "sql_text_short": _truncate(
                    str(sql_row.get("sql_text_snippet") or ""),
                    4000,
                ),
                "sql_text_clob": (str(sql_row.get("sql_text_snippet") or "") or None),
                "sql_metrics_json": _json_dumps(sql_row),
            }
        )

    return rows


def insert_top_sql_facts(conn: Any, sql_rows: list[dict[str, Any]]) -> None:
    """Insert top-SQL fact rows in bulk."""

    if not sql_rows:
        return
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            insert into AWR_TOP_SQL_FACT (
                AWR_ID,
                SOURCE_SYSTEM_ID,
                SNAP_TIME_BEGIN,
                SNAP_TIME_END,
                SQL_ID,
                PLAN_HASH_VALUE,
                MODULE_NAME,
                PARSING_SCHEMA_NAME,
                RANK_BY_ELAPSED,
                RANK_BY_CPU,
                RANK_BY_GETS,
                RANK_BY_READS,
                RANK_BY_EXECUTIONS,
                ELAPSED_TIME_SEC,
                CPU_TIME_SEC,
                IO_TIME_SEC,
                BUFFER_GETS,
                DISK_READS,
                EXECUTIONS,
                ROWS_PROCESSED,
                ELAPSED_PER_EXEC_SEC,
                CPU_PER_EXEC_SEC,
                GETS_PER_EXEC,
                READS_PER_EXEC,
                SQL_TEXT_SHORT,
                SQL_TEXT_CLOB,
                SQL_METRICS_JSON
            ) values (
                :awr_id,
                :source_system_id,
                :snap_time_begin,
                :snap_time_end,
                :sql_id,
                :plan_hash_value,
                :module_name,
                :parsing_schema_name,
                :rank_by_elapsed,
                :rank_by_cpu,
                :rank_by_gets,
                :rank_by_reads,
                :rank_by_executions,
                :elapsed_time_sec,
                :cpu_time_sec,
                :io_time_sec,
                :buffer_gets,
                :disk_reads,
                :executions,
                :rows_processed,
                :elapsed_per_exec_sec,
                :cpu_per_exec_sec,
                :gets_per_exec,
                :reads_per_exec,
                :sql_text_short,
                :sql_text_clob,
                :sql_metrics_json
            )
            """,
            sql_rows,
        )
    LOGGER.info("Top SQL facts inserted: %s", len(sql_rows))


def build_wait_event_fact_rows(
    parse_result: ParseResult,
    awr_id: int,
    source_system_id: int,
) -> list[dict[str, Any]]:
    """Build wait-event fact rows from parsed foreground waits."""

    if not parse_result.wait_events:
        return []

    snap_begin, snap_end = _require_snapshot_window(parse_result)
    ranked_events = sorted(
        parse_result.wait_events,
        key=lambda row: _safe_float(row.get("pct_db_time")) or 0.0,
        reverse=True,
    )
    rows: list[dict[str, Any]] = []
    for rank, wait_row in enumerate(ranked_events, start=1):
        event_name = str(wait_row.get("event_name") or "").strip()
        wait_class = str(wait_row.get("wait_class") or "").strip()
        if not event_name or not wait_class:
            continue
        rows.append(
            {
                "awr_id": awr_id,
                "source_system_id": source_system_id,
                "snap_time_begin": snap_begin,
                "snap_time_end": snap_end,
                "wait_class": wait_class,
                "event_name": event_name,
                "total_waits": _safe_float(wait_row.get("waits")),
                "total_timeouts": _safe_float(wait_row.get("timeouts")),
                "time_waited_sec": _safe_float(wait_row.get("time_seconds")),
                "avg_wait_ms": _safe_float(wait_row.get("avg_wait_ms")),
                "pct_db_time": _safe_float(wait_row.get("pct_db_time")),
                "rank_in_awr": rank,
                "foreground_flag": "Y",
                "wait_metrics_json": _json_dumps(wait_row),
            }
        )
    return rows


def insert_wait_event_facts(
    conn: Any,
    wait_rows: list[dict[str, Any]],
) -> None:
    """Insert wait-event fact rows in bulk."""

    if not wait_rows:
        return
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            insert into AWR_WAIT_EVENT_FACT (
                AWR_ID,
                SOURCE_SYSTEM_ID,
                SNAP_TIME_BEGIN,
                SNAP_TIME_END,
                WAIT_CLASS,
                EVENT_NAME,
                TOTAL_WAITS,
                TOTAL_TIMEOUTS,
                TIME_WAITED_SEC,
                AVG_WAIT_MS,
                PCT_DB_TIME,
                RANK_IN_AWR,
                FOREGROUND_FLAG,
                WAIT_METRICS_JSON
            ) values (
                :awr_id,
                :source_system_id,
                :snap_time_begin,
                :snap_time_end,
                :wait_class,
                :event_name,
                :total_waits,
                :total_timeouts,
                :time_waited_sec,
                :avg_wait_ms,
                :pct_db_time,
                :rank_in_awr,
                :foreground_flag,
                :wait_metrics_json
            )
            """,
            wait_rows,
        )
    LOGGER.info("Wait event facts inserted: %s", len(wait_rows))


def build_feature_vector_record(
    parse_result: ParseResult,
    awr_id: int,
    source_system_id: int,
) -> dict[str, Any]:
    """Build one feature-vector record with FEATURE_JSON populated."""

    _, snap_end = _require_snapshot_window(parse_result)
    feature_payload = _build_feature_payload(parse_result)
    feature_json = feature_payload["feature_json"]
    feature_record = {
        "awr_id": awr_id,
        "source_system_id": source_system_id,
        "observed_at": snap_end,
        "vector_version": SCORING_VECTOR_VERSION,
        "feature_set_name": FEATURE_SET_NAME,
        "feature_set_version": FEATURE_SET_VERSION,
        "workload_class": _derive_workload_class(parse_result),
        "topology_class": feature_json.get("topology_class"),
        "platform_class": feature_json.get("platform_class"),
        "event_class": feature_json.get("operational_event_class"),
        "vector_status": "ACTIVE",
        "feature_vector": None,
        "narrative_embedding": None,
        "feature_json": _json_dumps(feature_json),
        "normalization_json": _json_dumps(feature_payload["normalization_json"]),
        "explanation_json": _json_dumps(feature_payload["explanation_json"]),
        "source_lineage_json": _json_dumps(
            {
                "source_file_name": parse_result.run_metadata.source_file_name,
                "source_file_path": parse_result.run_metadata.source_file_path,
                "parser_sections": sorted(parse_result.sections_found),
            }
        ),
    }
    LOGGER.info(
        "Feature classifications derived: AWR_ID=%s workload_class=%s "
        "topology_class=%s platform_class=%s event_class=%s",
        awr_id,
        feature_record["workload_class"],
        feature_record["topology_class"],
        feature_record["platform_class"],
        feature_record["event_class"],
    )
    return feature_record


def insert_feature_vector(
    conn: Any,
    feature_vector_record: dict[str, Any],
) -> int:
    """Insert one feature vector row and return its identity."""

    with conn.cursor() as cursor:
        cursor.execute(
            """
            insert into AWR_FEATURE_VECTOR (
                AWR_ID,
                SOURCE_SYSTEM_ID,
                OBSERVED_AT,
                VECTOR_VERSION,
                FEATURE_SET_NAME,
                FEATURE_SET_VERSION,
                WORKLOAD_CLASS,
                TOPOLOGY_CLASS,
                PLATFORM_CLASS,
                EVENT_CLASS,
                VECTOR_STATUS,
                FEATURE_VECTOR,
                NARRATIVE_EMBEDDING,
                FEATURE_JSON,
                NORMALIZATION_JSON,
                EXPLANATION_JSON,
                SOURCE_LINEAGE_JSON
            ) values (
                :awr_id,
                :source_system_id,
                :observed_at,
                :vector_version,
                :feature_set_name,
                :feature_set_version,
                :workload_class,
                :topology_class,
                :platform_class,
                :event_class,
                :vector_status,
                :feature_vector,
                :narrative_embedding,
                :feature_json,
                :normalization_json,
                :explanation_json,
                :source_lineage_json
            )
            """,
            feature_vector_record,
        )
    with conn.cursor() as cursor:
        cursor.execute(
            """
            select FEATURE_VECTOR_ID
              from AWR_FEATURE_VECTOR
             where AWR_ID = :awr_id
               and FEATURE_SET_NAME = :feature_set_name
               and FEATURE_SET_VERSION = :feature_set_version
            """,
            {
                "awr_id": feature_vector_record["awr_id"],
                "feature_set_name": feature_vector_record["feature_set_name"],
                "feature_set_version": feature_vector_record["feature_set_version"],
            },
        )
        row = cursor.fetchone()
    if not row:
        raise RuntimeError("Failed to insert AWR_FEATURE_VECTOR row.")
    feature_vector_id = int(row[0])
    LOGGER.info(
        "Feature vector inserted: FEATURE_VECTOR_ID=%s AWR_ID=%s "
        "SOURCE_SYSTEM_ID=%s topology_class=%s platform_class=%s "
        "event_class=%s",
        feature_vector_id,
        feature_vector_record["awr_id"],
        feature_vector_record["source_system_id"],
        feature_vector_record.get("topology_class"),
        feature_vector_record.get("platform_class"),
        feature_vector_record.get("event_class"),
    )
    return feature_vector_id


def upsert_feature_vector(
    conn: Any,
    feature_vector_record: dict[str, Any],
) -> tuple[int, str]:
    """Update an existing feature vector in place or insert a new one."""

    with conn.cursor() as cursor:
        cursor.execute(
            """
            select FEATURE_VECTOR_ID
              from AWR_FEATURE_VECTOR
             where AWR_ID = :awr_id
               and FEATURE_SET_NAME = :feature_set_name
               and FEATURE_SET_VERSION = :feature_set_version
             fetch first 1 rows only
            """,
            {
                "awr_id": feature_vector_record["awr_id"],
                "feature_set_name": feature_vector_record["feature_set_name"],
                "feature_set_version": feature_vector_record["feature_set_version"],
            },
        )
        row = cursor.fetchone()

    if not row:
        feature_vector_id = insert_feature_vector(conn, feature_vector_record)
        return feature_vector_id, "inserted"

    feature_vector_id = int(row[0])
    update_record = {
        "observed_at": feature_vector_record["observed_at"],
        "vector_version": feature_vector_record["vector_version"],
        "workload_class": feature_vector_record["workload_class"],
        "topology_class": feature_vector_record.get("topology_class"),
        "platform_class": feature_vector_record.get("platform_class"),
        "event_class": feature_vector_record.get("event_class"),
        "vector_status": feature_vector_record["vector_status"],
        "feature_vector": feature_vector_record["feature_vector"],
        "narrative_embedding": feature_vector_record.get("narrative_embedding"),
        "feature_json": feature_vector_record["feature_json"],
        "normalization_json": feature_vector_record["normalization_json"],
        "explanation_json": feature_vector_record["explanation_json"],
        "source_lineage_json": feature_vector_record["source_lineage_json"],
        "feature_vector_id": feature_vector_id,
    }
    with conn.cursor() as cursor:
        cursor.execute(
            """
            update AWR_FEATURE_VECTOR
               set OBSERVED_AT = :observed_at,
                   VECTOR_VERSION = :vector_version,
                   WORKLOAD_CLASS = :workload_class,
                   TOPOLOGY_CLASS = :topology_class,
                   PLATFORM_CLASS = :platform_class,
                   EVENT_CLASS = :event_class,
                   VECTOR_STATUS = :vector_status,
                   FEATURE_VECTOR = :feature_vector,
                   NARRATIVE_EMBEDDING = :narrative_embedding,
                   FEATURE_JSON = :feature_json,
                   NORMALIZATION_JSON = :normalization_json,
                   EXPLANATION_JSON = :explanation_json,
                   SOURCE_LINEAGE_JSON = :source_lineage_json
             where FEATURE_VECTOR_ID = :feature_vector_id
            """,
            update_record,
        )
    LOGGER.info(
        "Feature vector updated in place: FEATURE_VECTOR_ID=%s AWR_ID=%s",
        feature_vector_id,
        feature_vector_record["awr_id"],
    )
    return feature_vector_id, "updated"


def load_active_scoring_model(
    conn: Any,
    decision_domain: str = SCORING_MODEL_DOMAIN,
) -> dict[str, Any] | None:
    """Load the active deterministic scoring model, if one exists."""

    with conn.cursor() as cursor:
        cursor.execute(
            """
            select SCORING_MODEL_ID,
                   MODEL_CODE,
                   MODEL_NAME,
                   MODEL_VERSION,
                   MODEL_TYPE,
                   TARGET_DECISION_DOMAIN,
                   STATUS,
                   SCORE_MIN,
                   SCORE_MAX,
                   THRESHOLD_JSON,
                   MODEL_CONFIG_JSON
              from AWR_SCORING_MODEL
             where STATUS = 'ACTIVE'
               and TARGET_DECISION_DOMAIN = :decision_domain
             order by
                   case when MODEL_CODE = :model_code then 0 else 1 end,
                   SCORING_MODEL_ID desc
             fetch first 1 rows only
            """,
            {
                "decision_domain": decision_domain,
                "model_code": SCORING_MODEL_CODE,
            },
        )
        row = cursor.fetchone()
    if not row:
        LOGGER.info(
            "Scoring skipped: no active scoring model found for domain=%s",
            decision_domain,
        )
        return None
    model = {
        "scoring_model_id": int(row[0]),
        "model_code": row[1],
        "model_name": row[2],
        "model_version": row[3],
        "model_type": row[4],
        "target_decision_domain": row[5],
        "status": row[6],
        "score_min": _safe_float(row[7]) or 0.0,
        "score_max": _safe_float(row[8]) or 100.0,
        "threshold_json": _json_loads(row[9]) or {},
        "model_config_json": _json_loads(row[10]) or {},
    }
    LOGGER.info(
        "Active scoring model loaded: id=%s code=%s version=%s",
        model["scoring_model_id"],
        model["model_code"],
        model["model_version"],
    )
    return model


def load_scoring_weights(conn: Any, scoring_model_id: int) -> list[dict[str, Any]]:
    """Load enabled weights for one scoring model."""

    with conn.cursor() as cursor:
        cursor.execute(
            """
            select FEATURE_CODE,
                   FEATURE_NAME,
                   FEATURE_DOMAIN,
                   FEATURE_PATH,
                   WEIGHT_VALUE,
                   NORMALIZATION_METHOD,
                   TRANSFORM_METHOD,
                   POLARITY,
                   NOTES
              from AWR_SCORING_WEIGHT
             where SCORING_MODEL_ID = :scoring_model_id
               and nvl(ENABLED_FLAG, 'Y') = 'Y'
             order by SCORING_WEIGHT_ID
            """,
            {"scoring_model_id": scoring_model_id},
        )
        rows = cursor.fetchall()
    weights = [
        {
            "feature_code": row[0],
            "feature_name": row[1],
            "feature_domain": row[2],
            "feature_path": row[3],
            "weight_value": _safe_float(row[4]) or 0.0,
            "normalization_method": row[5] or "MINMAX",
            "transform_method": row[6] or "NONE",
            "polarity": row[7] or "HIGH_BAD",
            "notes": row[8],
        }
        for row in rows
    ]
    LOGGER.info(
        "Scoring weights loaded: model_id=%s count=%s",
        scoring_model_id,
        len(weights),
    )
    return _augment_scoring_weights(weights)


def insert_score_result(conn: Any, score_result_record: dict[str, Any]) -> None:
    """Insert one deterministic score result row."""

    with conn.cursor() as cursor:
        cursor.execute(
            """
            insert into AWR_SCORE_RESULT (
                AWR_ID,
                SOURCE_SYSTEM_ID,
                FEATURE_VECTOR_ID,
                SCORING_MODEL_ID,
                SCORED_AT,
                DECISION_DOMAIN,
                RISK_LEVEL,
                TOTAL_SCORE,
                CONFIDENCE_SCORE,
                SEVERITY_SCORE,
                URGENCY_SCORE,
                BUSINESS_IMPACT_SCORE,
                WORKLOAD_CLASS,
                TOPOLOGY_CLASS,
                PLATFORM_CLASS,
                EVENT_CLASS,
                PRIMARY_SIGNAL_DOMAIN,
                EXPLANATION_JSON,
                CONTRIBUTION_JSON,
                SCORECARD_JSON
            ) values (
                :awr_id,
                :source_system_id,
                :feature_vector_id,
                :scoring_model_id,
                :scored_at,
                :decision_domain,
                :risk_level,
                :total_score,
                :confidence_score,
                :severity_score,
                :urgency_score,
                :business_impact_score,
                :workload_class,
                :topology_class,
                :platform_class,
                :event_class,
                :primary_signal_domain,
                :explanation_json,
                :contribution_json,
                :scorecard_json
            )
            """,
            score_result_record,
        )
    LOGGER.info(
        "Score result inserted: AWR_ID=%s MODEL_ID=%s TOTAL_SCORE=%s "
        "RISK=%s workload_class=%s topology_class=%s platform_class=%s "
        "event_class=%s primary_signal_domain=%s",
        score_result_record["awr_id"],
        score_result_record["scoring_model_id"],
        score_result_record["total_score"],
        score_result_record["risk_level"],
        score_result_record.get("workload_class"),
        score_result_record.get("topology_class"),
        score_result_record.get("platform_class"),
        score_result_record.get("event_class"),
        score_result_record.get("primary_signal_domain"),
    )


def process_awr_batch(
    input_dir: str | Path,
    conn: DbConnection | None = None,
) -> dict[str, Any]:
    """Process and load all AWR .out files from one directory."""

    managed_connection = conn is None
    db_conn: DbConnection | None = conn
    ingest_run_id: int | None = None
    try:
        if db_conn is None:
            db_conn = get_db_connection()

        LOGGER.info("Entering DB ingest flow")
        source_mode = _resolve_source_mode()
        object_storage_client: Any | None = None
        object_storage_namespace: str | None = None
        object_storage_bucket: str | None = None
        upload_to_object_storage = False
        if source_mode == SOURCE_MODE_OBJECT_STORAGE:
            object_storage_bucket, object_storage_prefix = (
                _validate_required_object_storage_configuration()
            )
            object_storage_client = _get_object_storage_client()
            object_storage_namespace = _resolve_object_storage_namespace_name(
                object_storage_client
            )
            LOGGER.info(
                "Listing AWR objects from Object Storage: namespace=%s bucket=%s prefix=%s",
                object_storage_namespace,
                object_storage_bucket,
                object_storage_prefix,
            )
            awr_sources: list[dict[str, Any]] = [
                {
                    "source_mode": SOURCE_MODE_OBJECT_STORAGE,
                    "object_name": object_name,
                    "display_name": object_name,
                    "source_file_name": Path(object_name).name,
                    "object_store_uri": _build_object_store_uri(
                        object_storage_namespace,
                        object_storage_bucket,
                        object_name,
                    ),
                }
                for object_name in list_awr_objects(
                    object_storage_client=object_storage_client,
                    namespace_name=object_storage_namespace,
                    bucket_name=object_storage_bucket,
                    prefix=object_storage_prefix,
                )
            ]
        else:
            awr_files = load_awr_files(input_dir)
            awr_sources = [
                {
                    "source_mode": SOURCE_MODE_LOCAL,
                    "file_path": file_path,
                    "display_name": str(file_path),
                    "source_file_name": Path(file_path).name,
                    "object_store_uri": None,
                }
                for file_path in awr_files
            ]
            upload_to_object_storage = _validate_optional_object_storage_upload_configuration()

        ingest_run_id = start_ingest_run(
            conn=db_conn,
            pipeline_name=PIPELINE_NAME,
            pipeline_version=PIPELINE_VERSION,
            trigger_type=os.getenv("AWR_TRIGGER_TYPE", "MANUAL"),
        )
        upsert_parser_knowledge_registry(db_conn)
        db_conn.commit()
        scoring_model: dict[str, Any] | None = None
        scoring_weights: list[dict[str, Any]] = []
        try:
            scoring_model = load_active_scoring_model(db_conn)
            if scoring_model is not None:
                scoring_weights = load_scoring_weights(
                    db_conn,
                    scoring_model["scoring_model_id"],
                )
        except Exception:  # noqa: BLE001
            LOGGER.exception(
                "Scoring model initialization failed; ingest will continue without scoring"
            )
            downstream_error_count = 1
            downstream_errors = [
                {
                    "stage": "scoring_model_initialization",
                    "error_type": "ScoringInitializationError",
                    "error_message": "Scoring model initialization failed during ingest.",
                }
            ]
            scoring_model = None
            scoring_weights = []
        else:
            downstream_error_count = 0
            downstream_errors: list[dict[str, Any]] = []

        file_count = len(awr_sources)
        success_count = 0
        skipped_count = 0
        error_count = 0
        errors: list[dict[str, Any]] = []
        affected_databases: set[tuple[str, int | None]] = set()

        for source_entry in awr_sources:
            temp_file_path: Path | None = None
            file_path: Path | None = None
            source_display_name = str(source_entry["display_name"])
            source_file_name = str(source_entry["source_file_name"])
            source_reference = str(
                source_entry.get("object_store_uri") or source_entry.get("file_path") or source_display_name
            )
            LOGGER.info("Processing AWR file: %s", source_display_name)
            try:
                if source_entry["source_mode"] == SOURCE_MODE_OBJECT_STORAGE:
                    if (
                        object_storage_client is None
                        or object_storage_namespace is None
                        or object_storage_bucket is None
                    ):
                        raise RuntimeError(
                            "Object Storage client is not initialized for OBJECT_STORAGE mode."
                        )
                    object_name = str(source_entry["object_name"])
                    LOGGER.info("Downloading object: %s", object_name)
                    temp_file_path = download_object_to_temp(
                        object_storage_client=object_storage_client,
                        namespace_name=object_storage_namespace,
                        bucket_name=object_storage_bucket,
                        object_name=object_name,
                    )
                    file_path = temp_file_path
                    LOGGER.info("Processing object: %s", object_name)
                else:
                    file_path = Path(source_entry["file_path"])

                if file_path is None:
                    raise RuntimeError("AWR source file path could not be resolved.")

                parse_result = parse_awr_file(file_path)
                file_hash = compute_file_hash(file_path)
                source_system_record = build_source_system_record(parse_result)
                source_system_id = upsert_source_system(
                    db_conn,
                    source_system_record,
                )
                if source_entry["source_mode"] == SOURCE_MODE_OBJECT_STORAGE:
                    object_store_uri = source_entry["object_store_uri"]
                elif upload_to_object_storage:
                    object_store_uri = upload_raw_awr_to_object_storage(
                        file_path=file_path,
                        source_system_id=source_system_id,
                        file_hash=file_hash,
                    )
                else:
                    object_store_uri = None

                report_record = build_report_record(
                    parse_result=parse_result,
                    file_path=file_path,
                    file_hash=file_hash,
                    source_system_id=source_system_id,
                    ingest_run_id=ingest_run_id,
                    object_store_uri=object_store_uri,
                    source_file_name_override=source_file_name,
                    source_file_path_override=(
                        None
                        if source_entry["source_mode"] == SOURCE_MODE_OBJECT_STORAGE
                        else _UNSET
                    ),
                )
                duplicate_match = None
                if not _allow_duplicate_report_ingest(report_record):
                    duplicate_match = find_duplicate_report(db_conn, report_record)
                if duplicate_match is not None:
                    db_conn.rollback()
                    LOGGER.info(
                        "Duplicate AWR report skipped: file=%s existing_awr_id=%s reason=%s ingest_mode=%s",
                        source_file_name,
                        duplicate_match[0],
                        duplicate_match[1],
                        report_record["ingest_mode"],
                    )
                    skipped_count += 1
                    continue
                awr_id = insert_report(db_conn, report_record)
                replace_parser_unknowns(
                    db_conn,
                    awr_id=awr_id,
                    parse_result=parse_result,
                )

                metric_rows = build_metric_fact_rows(
                    parse_result=parse_result,
                    awr_id=awr_id,
                    source_system_id=source_system_id,
                )
                insert_metric_facts(db_conn, metric_rows)

                sql_rows = build_top_sql_fact_rows(
                    parse_result=parse_result,
                    awr_id=awr_id,
                    source_system_id=source_system_id,
                )
                insert_top_sql_facts(db_conn, sql_rows)

                wait_rows = build_wait_event_fact_rows(
                    parse_result=parse_result,
                    awr_id=awr_id,
                    source_system_id=source_system_id,
                )
                insert_wait_event_facts(db_conn, wait_rows)

                feature_vector_record = build_feature_vector_record(
                    parse_result=parse_result,
                    awr_id=awr_id,
                    source_system_id=source_system_id,
                )
                feature_vector_id = insert_feature_vector(
                    db_conn,
                    feature_vector_record,
                )

                if scoring_model and scoring_weights:
                    try:
                        persist_deterministic_score(
                            conn=db_conn,
                            parse_result=parse_result,
                            awr_id=awr_id,
                            source_system_id=source_system_id,
                            feature_vector_id=feature_vector_id,
                            feature_vector_record=feature_vector_record,
                            scoring_model=scoring_model,
                            scoring_weights=scoring_weights,
                        )
                    except Exception:  # noqa: BLE001
                        LOGGER.exception(
                            "Scoring failed for AWR_ID=%s; ingest will continue without persisted score",
                            awr_id,
                        )
                        downstream_error_count += 1
                        downstream_errors.append(
                            {
                                "stage": "scoring",
                                "awr_id": awr_id,
                                "file_name": source_file_name,
                                "error_type": "ScorePersistenceError",
                                "error_message": (
                                    "Deterministic scoring failed after raw ingest commit boundary."
                                ),
                            }
                        )
                elif scoring_model and not scoring_weights:
                    LOGGER.info(
                        "Scoring skipped: AWR_ID=%s model_id=%s has no enabled weights",
                        awr_id,
                        scoring_model["scoring_model_id"],
                    )
                else:
                    LOGGER.info(
                        "Scoring skipped: AWR_ID=%s no active scoring model available",
                        awr_id,
                    )

                db_conn.commit()
                LOGGER.info(
                    "Commit complete: file=%s awr_id=%s",
                    source_file_name,
                    awr_id,
                )
                db_name = str(report_record["db_name"] or "").strip()
                dbid = _to_int(report_record["dbid"])
                if db_name:
                    affected_databases.add((db_name, dbid))
                success_count += 1
            except Exception as exc:  # noqa: BLE001
                db_conn.rollback()
                LOGGER.exception(
                    "Per-file ingest failure; rollback complete for %s",
                    source_display_name,
                )
                error_count += 1
                error_entry = {
                    "file_name": source_file_name,
                    "file_path": source_reference,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
                errors.append(error_entry)
            finally:
                if temp_file_path is not None:
                    try:
                        temp_file_path.unlink(missing_ok=True)
                        LOGGER.info("Temporary file removed: %s", temp_file_path)
                    except OSError:
                        LOGGER.warning(
                            "Failed to remove temporary Object Storage download: %s",
                            temp_file_path,
                        )

        final_status = _derive_operation_status(
            processed_count=success_count,
            error_count=error_count,
            downstream_error_count=downstream_error_count,
        )

        trend_analysis_results: list[dict[str, Any]] = []
        if affected_databases:
            try:
                trend_analysis_results = run_db_trend_analysis(
                    conn=db_conn,
                    affected_databases=affected_databases,
                )
                db_conn.commit()
            except Exception:  # noqa: BLE001
                db_conn.rollback()
                LOGGER.exception("DB trend analysis failed after ingest batch")
                downstream_error_count += 1
                downstream_errors.append(
                    {
                        "stage": "db_trend_analysis",
                        "error_type": "TrendAnalysisError",
                        "error_message": "DB trend analysis failed after ingest batch.",
                        "affected_database_count": len(affected_databases),
                    }
                )
                final_status = _derive_operation_status(
                    processed_count=success_count,
                    error_count=error_count,
                    downstream_error_count=downstream_error_count,
                )

        summary_notes = (
            f"Processed {file_count} file(s) from {source_mode}; "
            f"{success_count} succeeded, {skipped_count} skipped as duplicates, "
            f"{error_count} failed."
        )
        if downstream_error_count:
            summary_notes += (
                f" {downstream_error_count} downstream derived step(s) failed after raw ingest commits."
            )

        finalize_ingest_run(
            conn=db_conn,
            ingest_run_id=ingest_run_id,
            status=final_status,
            file_count=file_count,
            success_count=success_count,
            error_count=error_count,
            notes=summary_notes,
            error_json=(errors + downstream_errors) or None,
        )
        LOGGER.info(
            "ADB persistence complete: status=%s success=%s skipped=%s errors=%s downstream_errors=%s",
            final_status,
            success_count,
            skipped_count,
            error_count,
            downstream_error_count,
        )
        return {
            "ingest_run_id": ingest_run_id,
            "source_mode": source_mode,
            "status": final_status,
            "file_count": file_count,
            "success_count": success_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
            "downstream_error_count": downstream_error_count,
            "errors": errors,
            "downstream_errors": downstream_errors,
            "trend_analysis_results": trend_analysis_results,
        }
    except Exception:  # noqa: BLE001
        if db_conn is not None:
            db_conn.rollback()
            LOGGER.exception("Batch-level ingest failure; rollback complete")
            if ingest_run_id is not None:
                try:
                    finalize_ingest_run(
                        conn=db_conn,
                        ingest_run_id=ingest_run_id,
                        status="FAILED",
                        file_count=0,
                        success_count=0,
                        error_count=1,
                        notes="Batch failed before completion.",
                        error_json={"ingest_run_id": ingest_run_id},
                    )
                except Exception:  # noqa: BLE001
                    LOGGER.exception(
                        "Failed to finalize ingest run after batch failure"
                    )
        raise
    finally:
        if managed_connection and db_conn is not None:
            db_conn.close()


def _parse_result_from_persisted_json(
    parser_output_json: Any,
) -> ParseResult | None:
    payload = _json_loads(parser_output_json)
    if not isinstance(payload, dict):
        return None

    run_metadata_payload = payload.get("run_metadata") or {}
    if not isinstance(run_metadata_payload, dict):
        return None

    try:
        run_metadata = RunMetadata(**run_metadata_payload)
    except TypeError:
        LOGGER.exception("Persisted run metadata could not be reconstructed")
        return None

    return ParseResult(
        run_metadata=run_metadata,
        sections_found=_extract_payload_dict(
            payload,
            "sections_found",
            aliases=("sections",),
        ),
        cpu_metrics=_extract_payload_list(
            payload,
            "cpu_metrics",
            aliases=("metrics", "load_profile_metrics"),
        ),
        io_metrics=_extract_payload_list(payload, "io_metrics"),
        wait_events=_extract_payload_list(
            payload,
            "wait_events",
            aliases=("foreground_wait_events", "wait_event_rows"),
        ),
        top_sql=_extract_payload_list(payload, "top_sql", aliases=("top_sql_rows",)),
        instance_activity_stats=_extract_payload_list(
            payload,
            "instance_activity_stats",
            aliases=("instance_activity",),
        ),
        datafile_io_stats=_extract_payload_list(
            payload,
            "datafile_io_stats",
            aliases=("datafile_io",),
        ),
        tablespace_io_stats=_extract_payload_list(
            payload,
            "tablespace_io_stats",
            aliases=("tablespace_io",),
        ),
        pga_advisory=_normalize_pga_advisory_payload(
            _extract_payload_value(
                payload,
                "pga_advisory",
                aliases=("pga_target_advisory",),
            )
        ),
        workarea_histogram=_normalize_workarea_histogram_payload(
            _extract_payload_value(
                payload,
                "workarea_histogram",
                aliases=("workarea_executions",),
            )
        ),
        event_histograms=_extract_payload_dict(payload, "event_histograms"),
        ash_samples=_extract_payload_list(payload, "ash_samples"),
        session_metrics=_extract_payload_list(payload, "session_metrics"),
        topology_signals=_extract_payload_dict(payload, "topology_signals"),
        parse_warnings=_extract_payload_list(payload, "parse_warnings"),
        parse_errors=_extract_payload_list(payload, "parse_errors"),
    )


def _extract_payload_value(
    payload: dict[str, Any],
    key: str,
    aliases: tuple[str, ...] = (),
) -> Any:
    if key in payload and payload[key] is not None:
        return payload[key]
    for alias in aliases:
        if alias in payload and payload[alias] is not None:
            return payload[alias]
    return None


def _extract_payload_list(
    payload: dict[str, Any],
    key: str,
    aliases: tuple[str, ...] = (),
) -> list[Any]:
    value = _extract_payload_value(payload, key, aliases)
    if isinstance(value, list):
        return value
    return []


def _extract_payload_dict(
    payload: dict[str, Any],
    key: str,
    aliases: tuple[str, ...] = (),
) -> dict[str, Any]:
    value = _extract_payload_value(payload, key, aliases)
    if isinstance(value, dict):
        return value
    return {}


def _normalize_pga_advisory_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        rows = value.get("rows")
        if isinstance(rows, list):
            return value
        if isinstance(value.get("advisory_rows"), list):
            return {
                "current_target_mb": value.get("current_target_mb"),
                "rows": value.get("advisory_rows"),
            }
        return value
    if isinstance(value, list):
        return {
            "current_target_mb": None,
            "rows": value,
        }
    return {}


def _normalize_workarea_histogram_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        if {"optimal_executions", "onepass_executions", "multipass_executions"} <= set(
            value
        ):
            return value
        rows = value.get("rows")
        if isinstance(rows, list):
            optimal = sum(
                _safe_float(row.get("optimal_executions")) or 0.0 for row in rows
            )
            onepass = sum(
                _safe_float(row.get("onepass_executions")) or 0.0 for row in rows
            )
            multipass = sum(
                _safe_float(row.get("multipass_executions")) or 0.0 for row in rows
            )
            return {
                **value,
                "optimal_executions": optimal,
                "onepass_executions": onepass,
                "multipass_executions": multipass,
            }
    return {}


def _load_metric_facts(
    conn: Any,
    awr_id: int,
    source_system_id: int,
) -> list[dict[str, Any]]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            select METRIC_DOMAIN,
                   METRIC_NAME,
                   METRIC_SUBTYPE,
                   METRIC_VALUE_NUM,
                   UNIT_OF_MEASURE
              from AWR_METRIC_FACT
             where AWR_ID = :awr_id
               and SOURCE_SYSTEM_ID = :source_system_id
               and METRIC_DOMAIN in ('load_profile', 'instance_efficiency', 'host_cpu')
            """,
            {
                "awr_id": awr_id,
                "source_system_id": source_system_id,
            },
        )
        rows = cursor.fetchall()

    load_profile_map: dict[str, dict[str, Any]] = {}
    metrics: list[dict[str, Any]] = []
    for row in rows:
        domain = str(row[0] or "")
        metric_name = str(row[1] or "")
        subtype = str(row[2] or "") if row[2] is not None else None
        value = _safe_float(row[3])
        unit = str(row[4] or "") if row[4] is not None else None
        if domain == "load_profile":
            metric_row = load_profile_map.setdefault(
                metric_name,
                {
                    "metric_name": metric_name,
                    "per_second": None,
                    "per_transaction": None,
                    "metric_source_section": "metric_fact",
                    "metric_group": "load_profile",
                },
            )
            if subtype == "per_transaction":
                metric_row["per_transaction"] = value
            else:
                metric_row["per_second"] = value
            continue

        metrics.append(
            {
                "metric_name": metric_name,
                "metric_value": value,
                "metric_unit": unit,
                "metric_source_section": "metric_fact",
                "metric_group": domain,
            }
        )

    metrics.extend(load_profile_map.values())
    return metrics


def _load_wait_event_facts(
    conn: Any,
    awr_id: int,
    source_system_id: int,
) -> list[dict[str, Any]]:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            select EVENT_NAME,
                   TOTAL_WAITS,
                   TIME_WAITED_SEC,
                   AVG_WAIT_MS,
                   PCT_DB_TIME,
                   WAIT_CLASS
              from AWR_WAIT_EVENT_FACT
             where AWR_ID = :awr_id
               and SOURCE_SYSTEM_ID = :source_system_id
               and FOREGROUND_FLAG = 'Y'
            """,
            {
                "awr_id": awr_id,
                "source_system_id": source_system_id,
            },
        )
        rows = cursor.fetchall()

    return [
        {
            "event_name": str(row[0] or ""),
            "waits": _safe_float(row[1]),
            "time_seconds": _safe_float(row[2]),
            "avg_wait_ms": _safe_float(row[3]),
            "pct_db_time": _safe_float(row[4]),
            "wait_class": str(row[5] or ""),
            "source_section": "wait_event_fact",
        }
        for row in rows
        if row[0] is not None and row[5] is not None
    ]


def _merge_cpu_metrics(
    primary_metrics: list[dict[str, Any]],
    supplemental_metrics: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for metric in supplemental_metrics:
        key = (
            str(metric.get("metric_group") or ""),
            str(metric.get("metric_name") or ""),
        )
        merged[key] = dict(metric)
    for metric in primary_metrics:
        key = (
            str(metric.get("metric_group") or ""),
            str(metric.get("metric_name") or ""),
        )
        if key not in merged:
            merged[key] = dict(metric)
            continue
        merged[key] = _merge_missing_fields(
            primary=dict(metric),
            fallback=merged[key],
        )
    return list(merged.values())


def _merge_wait_events(
    primary_events: list[dict[str, Any]],
    supplemental_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for event in supplemental_events:
        key = str(event.get("event_name") or "").strip()
        if key:
            merged[key] = dict(event)
    for event in primary_events:
        key = str(event.get("event_name") or "").strip()
        if key:
            if key not in merged:
                merged[key] = dict(event)
                continue
            merged[key] = _merge_missing_fields(
                primary=dict(event),
                fallback=merged[key],
            )
    return list(merged.values())


def _merge_missing_fields(
    primary: dict[str, Any],
    fallback: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(primary)
    for key, value in fallback.items():
        if key not in merged or merged[key] is None:
            merged[key] = value
    return merged


def _merge_parse_result_sources(
    parse_result: ParseResult,
    metric_facts: list[dict[str, Any]],
    wait_facts: list[dict[str, Any]],
) -> ParseResult:
    cpu_metrics = _merge_cpu_metrics(parse_result.cpu_metrics, metric_facts)
    wait_events = _merge_wait_events(parse_result.wait_events, wait_facts)
    parse_result.cpu_metrics = cpu_metrics
    parse_result.wait_events = wait_events
    return parse_result


def _hydrate_parse_result_for_rebuild(
    conn: Any,
    parse_result: ParseResult,
    awr_id: int,
    source_system_id: int,
) -> ParseResult:
    metric_facts = _load_metric_facts(conn, awr_id, source_system_id)
    wait_facts = _load_wait_event_facts(conn, awr_id, source_system_id)
    return _merge_parse_result_sources(parse_result, metric_facts, wait_facts)


def _missing_promoted_feature_keys(feature_json: dict[str, Any]) -> list[str]:
    missing = []
    for key in PROMOTED_ENGINEERED_FEATURE_KEYS:
        if feature_json.get(key) is None:
            missing.append(key)
    return missing


def _parse_comma_separated_ids(value: str | None) -> set[int]:
    if not value:
        return set()
    ids: set[int] = set()
    for token in value.split(","):
        normalized = token.strip()
        if not normalized:
            continue
        try:
            ids.add(int(normalized))
        except ValueError:
            LOGGER.warning("Ignoring non-numeric AWR_ID filter token: %s", normalized)
    return ids


def load_reports_for_feature_rebuild(
    conn: Any,
    source_system_id: int | None = None,
    awr_ids: set[int] | None = None,
    only_missing_promoted_keys: bool = True,
) -> list[dict[str, Any]]:
    """Load canonical AWR reports plus current feature vectors for rebuild."""

    binds: dict[str, Any] = {}
    where_clauses = [
        "r.PARSER_OUTPUT_JSON is not null",
        "r.REPLAY_OF_AWR_ID is null",
        "r.PARSE_STATUS in ('PARSED', 'PARTIAL')",
    ]
    if source_system_id is not None:
        where_clauses.append("r.SOURCE_SYSTEM_ID = :source_system_id")
        binds["source_system_id"] = source_system_id

    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            select
                r.AWR_ID,
                r.SOURCE_SYSTEM_ID,
                r.SOURCE_FILE_NAME,
                r.SOURCE_FILE_PATH,
                r.DB_NAME,
                r.DBID,
                r.INSTANCE_NAME,
                r.INSTANCE_NUMBER,
                r.SNAP_TIME_BEGIN,
                r.SNAP_TIME_END,
                r.PARSER_OUTPUT_JSON,
                fv.FEATURE_VECTOR_ID,
                fv.FEATURE_JSON,
                fv.OBSERVED_AT
            from AWR_REPORT r
            left join AWR_FEATURE_VECTOR fv
              on fv.AWR_ID = r.AWR_ID
             and fv.SOURCE_SYSTEM_ID = r.SOURCE_SYSTEM_ID
             and fv.FEATURE_SET_NAME = :feature_set_name
             and fv.FEATURE_SET_VERSION = :feature_set_version
            where {' and '.join(where_clauses)}
            order by r.SNAP_TIME_BEGIN, r.AWR_ID
            """,
            {
                **binds,
                "feature_set_name": FEATURE_SET_NAME,
                "feature_set_version": FEATURE_SET_VERSION,
            },
        )
        rows = cursor.fetchall()

    selected_awr_ids = awr_ids or set()
    results: list[dict[str, Any]] = []
    for row in rows:
        row_dict = {
            "awr_id": int(row[0]),
            "source_system_id": int(row[1]),
            "source_file_name": row[2],
            "source_file_path": row[3],
            "db_name": row[4],
            "dbid": row[5],
            "instance_name": row[6],
            "instance_number": row[7],
            "snap_time_begin": row[8],
            "snap_time_end": row[9],
            "parser_output_json": row[10],
            "feature_vector_id": row[11],
            "feature_json": _json_loads(row[12]) or {},
            "observed_at": row[13],
        }
        if selected_awr_ids and row_dict["awr_id"] not in selected_awr_ids:
            continue
        if only_missing_promoted_keys:
            feature_json = row_dict["feature_json"]
            if feature_json and not _missing_promoted_feature_keys(feature_json):
                continue
        results.append(row_dict)
    return results


def load_reports_for_parser_refresh(
    conn: Any,
    source_system_id: int | None = None,
    awr_ids: set[int] | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Load canonical AWR reports eligible for parser-output refresh."""

    binds: dict[str, Any] = {}
    where_clauses = [
        "r.REPLAY_OF_AWR_ID is null",
    ]
    if source_system_id is not None:
        where_clauses.append("r.SOURCE_SYSTEM_ID = :source_system_id")
        binds["source_system_id"] = source_system_id

    with conn.cursor() as cursor:
        cursor.execute(
            f"""
            select
                r.AWR_ID,
                r.SOURCE_SYSTEM_ID,
                r.SOURCE_FILE_NAME,
                r.SOURCE_FILE_PATH,
                r.OBJECT_STORE_URI,
                r.DB_NAME,
                r.DBID
              from AWR_REPORT r
             where {' and '.join(where_clauses)}
             order by r.AWR_ID
            """,
            binds,
        )
        rows = cursor.fetchall()

    selected_awr_ids = awr_ids or set()
    results: list[dict[str, Any]] = []
    found_awr_ids: set[int] = set()
    for row in rows:
        awr_id = int(row[0])
        if selected_awr_ids and awr_id not in selected_awr_ids:
            continue
        found_awr_ids.add(awr_id)
        results.append(
            {
                "awr_id": awr_id,
                "source_system_id": int(row[1]),
                "source_file_name": row[2],
                "source_file_path": row[3],
                "source_object_uri": row[4],
                "object_store_uri": row[4],
                "db_name": row[5],
                "dbid": row[6],
            }
        )

    skipped_count = (
        len(selected_awr_ids - found_awr_ids)
        if selected_awr_ids
        else 0
    )
    return results, skipped_count


def _resolve_report_source_to_local_path(
    report_row: dict[str, Any],
) -> tuple[Path | None, Path | None]:
    """Resolve raw AWR content to a local file path, downloading from Object Storage if needed."""

    direct_path_value = str(report_row.get("source_file_path") or "").strip()
    if direct_path_value:
        direct_path = Path(direct_path_value)
        if direct_path.exists() and direct_path.is_file():
            return direct_path.resolve(), None

    object_store_uri = str(
        report_row.get("source_object_uri")
        or report_row.get("object_store_uri")
        or ""
    ).strip()
    if object_store_uri:
        temp_path = _download_object_to_temp_file(object_store_uri)
        return temp_path, temp_path

    source_file_name = str(report_row.get("source_file_name") or "").strip()
    if not source_file_name:
        return None, None

    fallback_directories = [
        Path(os.getenv("AWR_INPUT_DIR", "")).expanduser(),
        PROJECT_ROOT / "data" / "input",
    ]
    for directory in fallback_directories:
        if not str(directory):
            continue
        candidate_path = directory / source_file_name
        if candidate_path.exists() and candidate_path.is_file():
            return candidate_path.resolve(), None

    return None, None


def update_report_parser_output_json(
    conn: Any,
    awr_id: int,
    parse_result: ParseResult,
) -> None:
    """Refresh persisted parser payload fields in place for one AWR report."""

    parse_warnings = list(parse_result.parse_warnings)
    parse_status = "PARTIAL" if parse_warnings else "PARSED"
    with conn.cursor() as cursor:
        cursor.execute(
            """
            update AWR_REPORT
               set RAW_METADATA_JSON = :raw_metadata_json,
                   PARSER_OUTPUT_JSON = :parser_output_json,
                   PARSER_WARNINGS_JSON = :parser_warnings_json,
                   PARSE_STATUS = :parse_status
             where AWR_ID = :awr_id
            """,
            {
                "awr_id": awr_id,
                "raw_metadata_json": _json_dumps(asdict(parse_result.run_metadata)),
                "parser_output_json": _json_dumps(parse_result.to_dict()),
                "parser_warnings_json": _json_dumps(parse_warnings),
                "parse_status": parse_status,
            },
        )


def upsert_parser_knowledge_registry(conn: Any) -> None:
    """Persist canonical parser section knowledge for offline evolution workflows."""

    for definition in get_section_registry():
        description = (
            f"Deterministic parser registry entry for {definition.canonical_name} "
            f"({definition.section_kind} section, extractor={definition.extractor_id})."
        )
        embedding = generate_text_embedding(
            f"{definition.canonical_name}. {description}"
        )
        aliases_json = _json_dumps(list(definition.aliases))
        with conn.cursor() as cursor:
            cursor.execute(
                """
                select KNOWLEDGE_ID
                  from AWR_PARSER_KNOWLEDGE
                 where CONCEPT_TYPE = :concept_type
                   and CANONICAL_NAME = :canonical_name
                 fetch first 1 rows only
                """,
                {
                    "concept_type": "SECTION",
                    "canonical_name": definition.canonical_name,
                },
            )
            row = cursor.fetchone()
        if row:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    update AWR_PARSER_KNOWLEDGE
                       set ALIASES_JSON = :aliases_json,
                           DESCRIPTION = :description,
                           EMBEDDING = :embedding,
                           UPDATED_AT = SYSTIMESTAMP
                     where KNOWLEDGE_ID = :knowledge_id
                    """,
                    {
                        "knowledge_id": int(row[0]),
                        "aliases_json": aliases_json,
                        "description": description,
                        "embedding": embedding,
                    },
                )
        else:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    insert into AWR_PARSER_KNOWLEDGE (
                        CONCEPT_TYPE,
                        CANONICAL_NAME,
                        ALIASES_JSON,
                        DESCRIPTION,
                        EMBEDDING
                    ) values (
                        :concept_type,
                        :canonical_name,
                        :aliases_json,
                        :description,
                        :embedding
                    )
                    """,
                    {
                        "concept_type": "SECTION",
                        "canonical_name": definition.canonical_name,
                        "aliases_json": aliases_json,
                        "description": description,
                        "embedding": embedding,
                    },
                )


def replace_parser_unknowns(
    conn: Any,
    awr_id: int,
    parse_result: ParseResult,
) -> int:
    """Replace persisted parser unknown rows for one AWR report."""

    diagnostics = parse_result.parse_diagnostics
    unknown_sections = diagnostics.unknown_sections if diagnostics else []
    with conn.cursor() as cursor:
        cursor.execute(
            "delete from AWR_PARSER_UNKNOWN where AWR_ID = :awr_id",
            {"awr_id": awr_id},
        )

    rows = [
        _parser_unknown_row(awr_id, unknown_section)
        for unknown_section in unknown_sections
    ]
    if rows:
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                insert into AWR_PARSER_UNKNOWN (
                    AWR_ID,
                    PARSER_STAGE,
                    RAW_TEXT,
                    CONTEXT_BEFORE,
                    CONTEXT_AFTER,
                    STATUS,
                    EMBEDDING
                ) values (
                    :awr_id,
                    :parser_stage,
                    :raw_text,
                    :context_before,
                    :context_after,
                    :status,
                    :embedding
                )
                """,
                rows,
            )
    return len(rows)


def _parser_unknown_row(
    awr_id: int,
    unknown_section: UnknownParserElement,
) -> dict[str, Any]:
    return {
        "awr_id": awr_id,
        "parser_stage": unknown_section.parser_stage,
        "raw_text": unknown_section.raw_text,
        "context_before": _json_dumps(unknown_section.context_before),
        "context_after": _json_dumps(unknown_section.context_after),
        "status": "NEW",
        "embedding": generate_text_embedding(unknown_section.raw_text),
    }


def find_similar_parser_knowledge(
    conn: Any,
    query_vector: str,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Return the nearest parser knowledge rows for one query vector."""

    with conn.cursor() as cursor:
        cursor.execute(
            """
            select
                KNOWLEDGE_ID,
                CONCEPT_TYPE,
                CANONICAL_NAME,
                DESCRIPTION,
                VECTOR_DISTANCE(EMBEDDING, :query_vector, COSINE) as distance
              from AWR_PARSER_KNOWLEDGE
             where EMBEDDING is not null
             order by VECTOR_DISTANCE(EMBEDDING, :query_vector, COSINE)
             fetch first :top_n rows only
            """,
            {
                "query_vector": query_vector,
                "top_n": top_n,
            },
        )
        rows = cursor.fetchall()
    return [
        {
            "knowledge_id": int(row[0]),
            "concept_type": row[1],
            "canonical_name": row[2],
            "description": row[3],
            "distance": _safe_float(row[4]),
        }
        for row in rows
    ]


def find_similar_knowledge_for_unknown(
    conn: Any,
    unknown_id: int,
    top_n: int = 5,
) -> list[dict[str, Any]]:
    """Return the nearest parser knowledge rows for one persisted unknown."""

    with conn.cursor() as cursor:
        cursor.execute(
            """
            select EMBEDDING
              from AWR_PARSER_UNKNOWN
             where UNKNOWN_ID = :unknown_id
            """,
            {"unknown_id": unknown_id},
        )
        row = cursor.fetchone()
    if not row or row[0] is None:
        return []
    query_vector = str(row[0])
    return find_similar_parser_knowledge(
        conn=conn,
        query_vector=query_vector,
        top_n=top_n,
    )


def run_db_trend_analysis(
    conn: DbConnection,
    affected_databases: set[tuple[str, int | None]],
) -> list[dict[str, Any]]:
    """Recompute DB-scoped trend rows for affected DB identities only."""

    results: list[dict[str, Any]] = []
    for db_name, dbid in sorted(affected_databases, key=lambda item: (item[0], item[1] or -1)):
        if not db_name:
            continue
        trend_result = persist_db_metric_trends(
            conn=conn,
            db_name=db_name,
            dbid=dbid,
        )
        LOGGER.info(
            "DB trend analysis complete: db_name=%s dbid=%s metric_count=%s row_count=%s",
            db_name,
            dbid,
            trend_result["metric_count"],
            trend_result["row_count"],
        )
        results.append(trend_result)
    return results


def refresh_parser_output_json(
    conn: DbConnection | None = None,
    source_system_id: int | None = None,
    awr_ids: set[int] | None = None,
    refresh_rebuild_derived: bool = False,
) -> dict[str, Any]:
    """Refresh persisted parser output using the current parser and raw source files."""

    managed_connection = conn is None
    db_conn: DbConnection | None = conn
    try:
        if db_conn is None:
            db_conn = get_db_connection()

        upsert_parser_knowledge_registry(db_conn)
        db_conn.commit()

        candidate_reports, skipped_count = load_reports_for_parser_refresh(
            conn=db_conn,
            source_system_id=source_system_id,
            awr_ids=awr_ids,
        )
        candidate_count = len(candidate_reports)
        processed_count = 0
        updated_count = 0
        missing_file_count = 0
        parse_error_count = 0
        refresh_error_count = 0
        downstream_error_count = 0
        errors: list[dict[str, Any]] = []
        refreshed_awr_ids: set[int] = set()

        for report_row in candidate_reports:
            awr_id = int(report_row["awr_id"])
            processed_count += 1
            temp_file_path: Path | None = None
            try:
                source_file_path, temp_file_path = _resolve_report_source_to_local_path(
                    report_row
                )
                if source_file_path is None:
                    missing_file_count += 1
                    errors.append(
                        {
                            "awr_id": awr_id,
                            "stage": "source_file_resolution",
                            "error_type": "MissingSourceFile",
                            "error_message": "Raw source file could not be resolved for parser refresh.",
                            "source_file_name": report_row["source_file_name"],
                            "source_file_path": report_row["source_file_path"],
                        }
                    )
                    db_conn.rollback()
                    continue

                try:
                    parse_result = parse_awr_file(source_file_path)
                except Exception as exc:  # noqa: BLE001
                    parse_error_count += 1
                    errors.append(
                        {
                            "awr_id": awr_id,
                            "stage": "parse",
                            "error_type": type(exc).__name__,
                            "error_message": str(exc),
                            "source_file_path": str(source_file_path),
                        }
                    )
                    db_conn.rollback()
                    continue

                update_report_parser_output_json(
                    db_conn,
                    awr_id=awr_id,
                    parse_result=parse_result,
                )
                replace_parser_unknowns(
                    db_conn,
                    awr_id=awr_id,
                    parse_result=parse_result,
                )
                db_conn.commit()
                updated_count += 1
                refreshed_awr_ids.add(awr_id)
                LOGGER.info(
                    "Parser output refresh complete: awr_id=%s source_file=%s",
                    awr_id,
                    source_file_path.name,
                )
            except Exception as exc:  # noqa: BLE001
                db_conn.rollback()
                refresh_error_count += 1
                LOGGER.exception("Parser output refresh failed for AWR_ID=%s", awr_id)
                errors.append(
                    {
                        "awr_id": awr_id,
                        "stage": "refresh_update",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                        "source_file_name": report_row["source_file_name"],
                    }
                )
            finally:
                if temp_file_path is not None:
                    try:
                        temp_file_path.unlink(missing_ok=True)
                    except OSError:
                        LOGGER.warning(
                            "Failed to remove temporary Object Storage download: %s",
                            temp_file_path,
                        )

        derived_refresh_result: dict[str, Any] | None = None
        if refresh_rebuild_derived and refreshed_awr_ids:
            try:
                derived_refresh_result = rebuild_feature_vectors(
                    conn=db_conn,
                    awr_ids=refreshed_awr_ids,
                    only_missing_promoted_keys=False,
                )
                downstream_error_count = int(
                    derived_refresh_result.get("error_count", 0)
                ) + int(
                    derived_refresh_result.get("downstream_error_count", 0)
                )
            except Exception as exc:  # noqa: BLE001
                downstream_error_count += 1
                LOGGER.exception("Optional downstream rebuild failed after parser refresh")
                errors.append(
                    {
                        "stage": "downstream_rebuild",
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                )

        status = _derive_operation_status(
            processed_count=updated_count,
            error_count=skipped_count + missing_file_count + parse_error_count + refresh_error_count,
            downstream_error_count=downstream_error_count,
        )
        notes = (
            f"Processed {processed_count} parser refresh candidate(s); "
            f"{updated_count} updated, {skipped_count} skipped, "
            f"{missing_file_count} missing files, {parse_error_count} parse failures."
        )
        if refresh_error_count:
            notes += f" {refresh_error_count} refresh update failure(s)."
        if refresh_rebuild_derived:
            if refreshed_awr_ids:
                notes += " Optional downstream rebuild was requested."
            else:
                notes += " Optional downstream rebuild was requested but no parser refreshes succeeded."
        if candidate_count == 0:
            notes = "No canonical AWR reports matched parser refresh selection."

        return {
            "mode": REFRESH_PARSER_OUTPUT_JSON_MODE,
            "candidate_count": candidate_count,
            "processed_count": processed_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "missing_file_count": missing_file_count,
            "parse_error_count": parse_error_count,
            "downstream_error_count": downstream_error_count,
            "status": status,
            "errors": errors,
            "notes": notes,
            "derived_refresh_result": derived_refresh_result,
        }
    finally:
        if managed_connection and db_conn is not None:
            db_conn.close()


def load_db_trend_targets(
    conn: DbConnection,
    db_name: str | None = None,
    dbid: int | None = None,
) -> set[tuple[str, int | None]]:
    """Load DB identities that currently have DB-scoped engineered metrics."""

    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT DB_NAME, DBID
              FROM VW_AWR_FEATURE_METRIC_DB_SCOPE
             WHERE (:db_name IS NULL OR DB_NAME = :db_name)
               AND (:dbid IS NULL OR DBID = :dbid)
            """,
            {
                "db_name": db_name,
                "dbid": dbid,
            },
        )
        rows = cursor.fetchall()

    return {
        (str(row[0] or "").strip(), _to_int(row[1]))
        for row in rows
        if str(row[0] or "").strip()
    }


def rebuild_feature_vectors(
    conn: DbConnection | None = None,
    source_system_id: int | None = None,
    awr_ids: set[int] | None = None,
    only_missing_promoted_keys: bool = True,
) -> dict[str, Any]:
    """Rebuild feature vectors for existing canonical AWR reports only."""

    managed_connection = conn is None
    db_conn: DbConnection | None = conn
    try:
        if db_conn is None:
            db_conn = get_db_connection()

        scoring_model: dict[str, Any] | None = None
        scoring_weights: list[dict[str, Any]] = []
        try:
            scoring_model = load_active_scoring_model(db_conn)
            if scoring_model is not None:
                scoring_weights = load_scoring_weights(
                    db_conn,
                    scoring_model["scoring_model_id"],
                )
        except Exception:  # noqa: BLE001
            LOGGER.exception(
                "Scoring model initialization failed for feature rebuild"
            )
            downstream_error_count = 1
            downstream_errors = [
                {
                    "stage": "scoring_model_initialization",
                    "error_type": "ScoringInitializationError",
                    "error_message": "Scoring model initialization failed for feature rebuild.",
                }
            ]
            scoring_model = None
            scoring_weights = []
        else:
            downstream_error_count = 0
            downstream_errors: list[dict[str, Any]] = []

        candidate_reports = load_reports_for_feature_rebuild(
            conn=db_conn,
            source_system_id=source_system_id,
            awr_ids=awr_ids,
            only_missing_promoted_keys=only_missing_promoted_keys,
        )
        updated_count = 0
        inserted_count = 0
        skipped_count = 0
        score_regenerated_count = 0
        error_count = 0
        errors: list[dict[str, Any]] = []
        affected_databases: set[tuple[str, int | None]] = set()

        for report_row in candidate_reports:
            awr_id = report_row["awr_id"]
            try:
                parse_result = _parse_result_from_persisted_json(
                    report_row["parser_output_json"]
                )
                if parse_result is None:
                    raise ValueError(
                        "Persisted PARSER_OUTPUT_JSON could not be reconstructed."
                    )
                parse_result = _hydrate_parse_result_for_rebuild(
                    db_conn,
                    parse_result,
                    awr_id,
                    report_row["source_system_id"],
                )

                feature_vector_record = build_feature_vector_record(
                    parse_result=parse_result,
                    awr_id=awr_id,
                    source_system_id=report_row["source_system_id"],
                )
                source_lineage = _json_loads(
                    feature_vector_record.get("source_lineage_json")
                ) or {}
                source_lineage["rebuild_mode"] = FEATURE_REBUILD_MODE
                source_lineage["rebuilt_from"] = "AWR_REPORT.PARSER_OUTPUT_JSON"
                source_lineage["rebuilt_at"] = datetime.utcnow().isoformat()
                feature_vector_record["source_lineage_json"] = _json_dumps(
                    source_lineage
                )

                feature_vector_id, action = upsert_feature_vector(
                    db_conn,
                    feature_vector_record,
                )

                if action == "inserted":
                    inserted_count += 1
                else:
                    updated_count += 1

                db_name = str(report_row["db_name"] or "").strip()
                dbid = _to_int(report_row["dbid"])
                if db_name:
                    affected_databases.add((db_name, dbid))

                if scoring_model and scoring_weights:
                    persist_deterministic_score(
                        conn=db_conn,
                        parse_result=parse_result,
                        awr_id=awr_id,
                        source_system_id=report_row["source_system_id"],
                        feature_vector_id=feature_vector_id,
                        feature_vector_record=feature_vector_record,
                        scoring_model=scoring_model,
                        scoring_weights=scoring_weights,
                    )
                    score_regenerated_count += 1

                db_conn.commit()
                LOGGER.info(
                    "Feature rebuild complete: awr_id=%s action=%s file=%s",
                    awr_id,
                    action,
                    report_row["source_file_name"],
                )
            except Exception as exc:  # noqa: BLE001
                db_conn.rollback()
                LOGGER.exception("Feature rebuild failed for AWR_ID=%s", awr_id)
                error_count += 1
                errors.append(
                    {
                        "awr_id": awr_id,
                        "source_file_name": report_row["source_file_name"],
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                )

        if not candidate_reports:
            skipped_count = 0

        trend_analysis_results: list[dict[str, Any]] = []
        if affected_databases:
            try:
                trend_analysis_results = run_db_trend_analysis(
                    conn=db_conn,
                    affected_databases=affected_databases,
                )
                db_conn.commit()
            except Exception:  # noqa: BLE001
                db_conn.rollback()
                LOGGER.exception("DB trend analysis failed after feature rebuild")
                downstream_error_count += 1
                downstream_errors.append(
                    {
                        "stage": "db_trend_analysis",
                        "error_type": "TrendAnalysisError",
                        "error_message": "DB trend analysis failed after feature rebuild.",
                        "affected_database_count": len(affected_databases),
                    }
                )

        candidate_count = len(candidate_reports)
        processed_count = updated_count + inserted_count
        no_candidates = candidate_count == 0
        status = _derive_operation_status(
            processed_count=processed_count,
            error_count=error_count,
            downstream_error_count=downstream_error_count,
        )
        if no_candidates:
            notes = "No candidate reports matched rebuild selection."
        else:
            notes = (
                f"Processed {processed_count} feature vector rebuild candidate(s); "
                f"{error_count} failed."
            )
        if downstream_error_count:
            notes += (
                f" {downstream_error_count} downstream derived step(s) failed after feature rebuild commits."
            )

        return {
            "mode": FEATURE_REBUILD_MODE,
            "status": status,
            "candidate_count": candidate_count,
            "processed_count": processed_count,
            "updated_count": updated_count,
            "inserted_count": inserted_count,
            "skipped_count": skipped_count,
            "no_candidates": no_candidates,
            "score_regenerated_count": score_regenerated_count,
            "error_count": error_count,
            "downstream_error_count": downstream_error_count,
            "errors": errors,
            "downstream_errors": downstream_errors,
            "notes": notes,
            "promoted_metric_keys": list(PROMOTED_ENGINEERED_FEATURE_KEYS),
            "trend_analysis_results": trend_analysis_results,
        }
    finally:
        if managed_connection and db_conn is not None:
            db_conn.close()


def _build_source_system_code(
    dbid: int | None,
    db_name: str | None,
    instance_name: str | None,
) -> str:
    parts = [
        str(dbid) if dbid is not None else "unknown_dbid",
        (db_name or "unknown_db").strip().lower(),
        (instance_name or "unknown_instance").strip().lower(),
    ]
    return ":".join(parts)


def _derive_application_name(parse_result: ParseResult) -> str | None:
    if not parse_result.top_sql:
        return None
    for sql_row in parse_result.top_sql:
        module = str(sql_row.get("module") or "").strip()
        if module:
            return module
    return None


def _derive_workload_class(parse_result: ParseResult) -> str | None:
    cpu_pct = _compute_cpu_pct(parse_result)
    user_io_pct = _sum_wait_class_pct(parse_result, "User I/O")
    if cpu_pct is not None and cpu_pct >= 50:
        return "CPU_BOUND"
    if user_io_pct is not None and user_io_pct >= 30:
        return "IO_BOUND"
    if parse_result.top_sql:
        return "MIXED"
    return None


def _metric_fact_row(
    awr_id: int,
    source_system_id: int,
    snap_begin: datetime,
    snap_end: datetime,
    domain: str,
    name: str,
    value: Any,
    unit: str | None,
    subtype: str | None = None,
    metric_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "awr_id": awr_id,
        "source_system_id": source_system_id,
        "snap_time_begin": snap_begin,
        "snap_time_end": snap_end,
        "metric_domain": domain,
        "metric_name": name,
        "metric_subtype": subtype,
        "dimension_1": None,
        "dimension_2": None,
        "dimension_3": None,
        "metric_value_num": _safe_float(value),
        "metric_value_txt": None,
        "unit_of_measure": unit,
        "value_direction": None,
        "baseline_value_num": None,
        "delta_value_num": None,
        "zscore_value": None,
        "percentile_value": None,
        "metric_json": _json_dumps(metric_json),
    }


def _require_snapshot_window(
    parse_result: ParseResult,
) -> tuple[datetime, datetime]:
    snap_begin = normalize_timestamp(parse_result.run_metadata.begin_snapshot_time)
    snap_end = normalize_timestamp(parse_result.run_metadata.end_snapshot_time)
    if snap_begin is None or snap_end is None:
        raise ValueError(
            "Parsed AWR report does not include usable snapshot timestamps."
        )
    return snap_begin, snap_end


def normalize_timestamp(value: Any) -> datetime | None:
    """Normalize parsed timestamp values for Oracle TIMESTAMP binds."""

    if isinstance(value, datetime):
        return value if 1 <= value.year <= 9999 else None
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not candidate:
        return None
    cleaned_candidate = re.sub(r"^\d+\s+", "", candidate)
    if cleaned_candidate != candidate:
        LOGGER.info(
            "Cleaned snapshot timestamp raw=%r cleaned=%r",
            candidate,
            cleaned_candidate,
        )
    for fmt in SNAPSHOT_TIME_FORMATS:
        try:
            parsed = datetime.strptime(cleaned_candidate, fmt)
        except ValueError:
            continue
        if 1 <= parsed.year <= 9999:
            LOGGER.info(
                "Parsed snapshot timestamp cleaned=%r parsed=%r",
                cleaned_candidate,
                parsed,
            )
            return parsed
    LOGGER.warning(
        "Could not parse snapshot timestamp raw=%r cleaned=%r",
        candidate,
        cleaned_candidate,
    )
    return None


def _extract_report_header_fields(file_path: str | Path) -> dict[str, Any]:
    text = Path(file_path).read_text(encoding="utf-8", errors="replace")
    return {
        "snap_id_begin": _first_int_match(text, SNAP_ID_BEGIN_PATTERNS),
        "snap_id_end": _first_int_match(text, SNAP_ID_END_PATTERNS),
        "db_version": _first_str_match(text, DB_VERSION_PATTERNS),
    }


def _first_int_match(
    text: str,
    patterns: tuple[re.Pattern[str], ...],
) -> int | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return _to_int(match.group(1))
    return None


def _first_str_match(
    text: str,
    patterns: tuple[re.Pattern[str], ...],
) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


def _extract_load_profile_metric(
    parse_result: ParseResult,
    metric_name: str,
) -> float | None:
    normalized_metric_name = _normalize_load_profile_metric_name(metric_name)
    for metric in parse_result.cpu_metrics:
        if metric.get("metric_group") != "load_profile":
            continue
        metric_name_value = _normalize_load_profile_metric_name(
            str(metric.get("metric_name") or "").strip()
        )
        if metric_name_value != normalized_metric_name:
            continue
        return _safe_float(metric.get("per_second"))
    return None


def _compute_cpu_pct(parse_result: ParseResult) -> float | None:
    db_cpu = _extract_load_profile_metric(parse_result, "DB CPU(s)")
    db_time = _extract_load_profile_metric(parse_result, "DB Time(s)")
    if db_cpu is None or db_time is None or db_time <= 0:
        return None
    return round((db_cpu / db_time) * 100.0, 4)


def _sum_wait_class_pct(
    parse_result: ParseResult,
    wait_class: str,
) -> float | None:
    values: list[float | None] = [
        _safe_float(row.get("pct_db_time"))
        for row in parse_result.wait_events
        if str(row.get("wait_class") or "") == wait_class
    ]
    numeric_values = _compact_floats(values)
    if not numeric_values:
        return None
    return round(sum(numeric_values), 4)


def _extract_log_file_sync_ms(parse_result: ParseResult) -> float | None:
    for row in parse_result.wait_events:
        if str(row.get("event_name") or "") != "log file sync":
            continue
        return _safe_float(row.get("avg_wait_ms"))
    return None


def _top_sql_concentration(parse_result: ParseResult) -> float | None:
    pct_values = _compact_floats(
        [
            _safe_float(row.get("pct_total"))
            for row in parse_result.top_sql[:2]
            if _safe_float(row.get("pct_total")) is not None
        ]
    )
    if not pct_values:
        return None
    return round(sum(pct_values), 4)


def _aggregate_datafile_metric(
    parse_result: ParseResult,
    key: str,
) -> float | None:
    values = _compact_floats(
        [
            _safe_float(row.get(key))
            for row in parse_result.datafile_io_stats
            if _safe_float(row.get(key)) is not None
        ]
    )
    if not values:
        return None
    return round(sum(values), 4)


def _build_feature_payload(parse_result: ParseResult) -> dict[str, Any]:
    derived = extract_derived_pressure_metrics(parse_result)
    topology = _ensure_native_feature_inputs(parse_result)
    storage_index_savings = _safe_float(topology.get("exa_storage_index_savings"))
    base_features = {
        "cpu_pct": _compute_cpu_pct(parse_result),
        "db_cpu_pct_db_time": _compute_cpu_pct(parse_result),
        "user_io_pct": _sum_wait_class_pct(parse_result, "User I/O"),
        "commit_pct": _sum_wait_class_pct(parse_result, "Commit"),
        "concurrency_pct": _sum_wait_class_pct(parse_result, "Concurrency"),
        "network_wait_pct_db_time": _sum_wait_class_pct(parse_result, "Network"),
        "read_iops": _extract_load_profile_metric(parse_result, "Physical reads"),
        "write_iops": _extract_load_profile_metric(parse_result, "Physical writes"),
        "read_mb_per_sec": _aggregate_datafile_metric(parse_result, "read_mb"),
        "write_mb_per_sec": _aggregate_datafile_metric(parse_result, "write_mb"),
        "write_latency_ms": _aggregate_datafile_latency(
            parse_result,
            "avg_write_ms",
            "writes",
        ),
        "temp_write_latency_ms": _extract_temp_tablespace_metric(
            parse_result,
            "avg_write_ms",
        ),
        "hard_parses_per_sec": derived.get("hard_parses_per_sec"),
        "hard_parse_pct": _compute_hard_parse_pct(parse_result),
        "soft_parse_pct": _extract_instance_efficiency_metric(
            parse_result,
            "Soft Parse %",
        ),
        "temp_io_pressure": derived.get("temp_io_pressure"),
        "pga_spill_pressure": derived.get("pga_spill_pressure"),
        "temp_spill_pct": _compute_temp_spill_pct(derived),
        "sorts_disk_pct": _compute_sorts_disk_pct(parse_result),
        "workarea_onepass_pct": _compute_workarea_execution_pct(
            parse_result,
            "onepass_executions",
        ),
        "workarea_multipass_pct": _compute_workarea_execution_pct(
            parse_result,
            "multipass_executions",
        ),
        "log_file_sync_ms": _extract_log_file_sync_ms(parse_result),
        "log_write_latency_ms": _extract_exact_wait_event_avg_wait_ms(
            parse_result,
            ("log file parallel write",),
        ),
        "top_sql_concentration": _top_sql_concentration(parse_result),
        "db_time_per_txn": _extract_load_profile_transaction_metric(
            parse_result,
            "DB Time(s)",
        ),
        "read_latency_ms": _extract_wait_class_avg_wait_ms(parse_result, "User I/O"),
        "buffer_cache_hit_ratio_pct": _extract_instance_efficiency_metric(
            parse_result,
            "Buffer Hit %",
        ),
        "library_cache_hit_ratio_pct": _extract_instance_efficiency_metric(
            parse_result,
            "Library Hit %",
        ),
        "parse_cpu_to_parse_elapsed_pct": _extract_instance_efficiency_metric(
            parse_result,
            "Parse CPU to Parse Elapsd %",
        ),
        "pga_cache_hit_pct": _extract_pga_cache_hit_pct(parse_result),
        "cursor_mutex_wait_pct_db_time": _sum_exact_event_pct(
            parse_result,
            ("cursor: mutex S", "cursor: mutex X"),
        ),
        "db_time_per_sec": _extract_load_profile_metric(parse_result, "DB Time(s)"),
        "db_cpu_per_sec": _extract_load_profile_metric(parse_result, "DB CPU(s)"),
        "executions_per_sec": _extract_load_profile_metric(parse_result, "Executions"),
        "user_calls_per_sec": _extract_load_profile_metric(parse_result, "User calls"),
        "transactions_per_sec": _extract_load_profile_metric(
            parse_result,
            "Transactions",
        ),
        "redo_size_per_sec": _extract_load_profile_metric(parse_result, "Redo size"),
        "redo_generation_per_sec": _extract_load_profile_metric(
            parse_result,
            "Redo size",
        ),
        "host_cpu_busy_pct": _extract_host_cpu_metric(parse_result, "busy"),
        "is_rac": _flag_to_float(topology.get("is_rac")),
        "instance_count": _safe_float(topology.get("instance_count")),
        "cluster_wait_pct_db_time": _safe_float(
            topology.get("cluster_wait_pct_db_time")
        ),
        "gc_cr_wait_pct_db_time": _safe_float(
            topology.get("gc_cr_wait_pct_db_time")
        ),
        "gc_current_wait_pct_db_time": _safe_float(
            topology.get("gc_current_wait_pct_db_time")
        ),
        "gc_buffer_busy_pct_db_time": _safe_float(
            topology.get("gc_buffer_busy_pct_db_time")
        ),
        "interconnect_stress_flag": _flag_to_float(
            topology.get("interconnect_stress_flag")
        ),
        "rac_contention_flag": _flag_to_float(topology.get("rac_contention_flag")),
        "is_dataguard": _flag_to_float(topology.get("is_dataguard")),
        "database_role": topology.get("database_role"),
        "is_primary": _flag_to_float(topology.get("is_primary")),
        "is_standby": _flag_to_float(topology.get("is_standby")),
        "transport_lag_sec": _safe_float(topology.get("transport_lag_sec")),
        "apply_lag_sec": _safe_float(topology.get("apply_lag_sec")),
        "redo_transport_issue_flag": _flag_to_float(
            topology.get("redo_transport_issue_flag")
        ),
        "failover_event_flag": _flag_to_float(topology.get("failover_event_flag")),
        "role_transition_flag": _flag_to_float(
            topology.get("role_transition_flag")
        ),
        "post_failover_recovery_flag": _flag_to_float(
            topology.get("post_failover_recovery_flag")
        ),
        "is_exadata": _flag_to_float(topology.get("is_exadata")),
        "smart_scan_flag": _flag_to_float(topology.get("smart_scan_flag")),
        "exa_cell_io_pct_db_time": _safe_float(topology.get("exa_cell_io_pct_db_time")),
        "exa_offload_efficiency": _safe_float(topology.get("exa_offload_efficiency")),
        "exa_storage_index_savings": storage_index_savings,
        "storage_index_savings_pct": (
            round(storage_index_savings * 100.0, 4)
            if storage_index_savings is not None
            else None
        ),
        "cell_single_block_latency_ms": _extract_exact_wait_event_avg_wait_ms(
            parse_result,
            ("cell single block physical read",),
        ),
        "cell_multiblock_latency_ms": _extract_exact_wait_event_avg_wait_ms(
            parse_result,
            ("cell multiblock physical read",),
        ),
        "flash_cache_hit_flag": _flag_to_float(topology.get("flash_cache_hit_flag")),
        "exadata_io_benefit_flag": _flag_to_float(
            topology.get("exadata_io_benefit_flag")
        ),
        "topology_class": topology.get("topology_class"),
        "platform_class": topology.get("platform_class"),
        "operational_event_class": topology.get("operational_event_class"),
    }
    _apply_low_signal_feature_suppression(base_features)
    scoring_features = {
        "CPU_UTIL_P95": base_features["cpu_pct"],
        "DB_CPU_PCT_DB_TIME": base_features["db_cpu_pct_db_time"],
        "DB_TIME_PER_TXN": base_features["db_time_per_txn"],
        "READ_LATENCY_MS": base_features["read_latency_ms"],
        "WRITE_LATENCY_MS": base_features["write_latency_ms"],
        "TEMP_WRITE_LATENCY_MS": base_features["temp_write_latency_ms"],
        "LOG_FILE_SYNC_MS": base_features["log_file_sync_ms"],
        "LOG_WRITE_LATENCY_MS": base_features["log_write_latency_ms"],
        "REDO_GENERATION_PER_SEC": base_features["redo_generation_per_sec"],
        "TOP_SQL_LOAD_CONCENTRATION": base_features["top_sql_concentration"],
        "AAS_PER_CPU": _derive_aas_per_cpu(parse_result),
        "USER_IO_PRESSURE": base_features["user_io_pct"],
        "COMMIT_PRESSURE": base_features["commit_pct"],
        "CONCURRENCY_PRESSURE": base_features["concurrency_pct"],
        "NETWORK_WAIT_PCT_DB_TIME": base_features["network_wait_pct_db_time"],
        "HARD_PARSES_PER_SEC": base_features["hard_parses_per_sec"],
        "HARD_PARSE_PCT": base_features["hard_parse_pct"],
        "SOFT_PARSE_PCT": base_features["soft_parse_pct"],
        "PGA_SPILL_PRESSURE": base_features["pga_spill_pressure"],
        "PGA_CACHE_HIT_PCT": base_features["pga_cache_hit_pct"],
        "TEMP_IO_PRESSURE": base_features["temp_io_pressure"],
        "TEMP_SPILL_PCT": base_features["temp_spill_pct"],
        "SORTS_DISK_PCT": base_features["sorts_disk_pct"],
        "WORKAREA_ONEPASS_PCT": base_features["workarea_onepass_pct"],
        "WORKAREA_MULTIPASS_PCT": base_features["workarea_multipass_pct"],
        "THROUGHPUT_EXECUTIONS_PER_SEC": base_features["executions_per_sec"],
        "THROUGHPUT_USER_CALLS_PER_SEC": base_features["user_calls_per_sec"],
        "READ_MB_PER_SEC": base_features["read_mb_per_sec"],
        "WRITE_MB_PER_SEC": base_features["write_mb_per_sec"],
        "BUFFER_CACHE_HIT_RATIO_PCT": base_features["buffer_cache_hit_ratio_pct"],
        "LIBRARY_CACHE_HIT_RATIO_PCT": base_features[
            "library_cache_hit_ratio_pct"
        ],
        "PARSE_CPU_TO_PARSE_ELAPSED_PCT": base_features[
            "parse_cpu_to_parse_elapsed_pct"
        ],
        "CURSOR_MUTEX_WAIT_PCT_DB_TIME": base_features[
            "cursor_mutex_wait_pct_db_time"
        ],
        "CLUSTER_WAIT_PCT_DB_TIME": base_features["cluster_wait_pct_db_time"],
        "GC_CR_WAIT_PCT_DB_TIME": base_features["gc_cr_wait_pct_db_time"],
        "GC_CURRENT_WAIT_PCT_DB_TIME": base_features["gc_current_wait_pct_db_time"],
        "GC_BUFFER_BUSY_PCT_DB_TIME": base_features["gc_buffer_busy_pct_db_time"],
        "INTERCONNECT_STRESS_FLAG": base_features["interconnect_stress_flag"],
        "RAC_CONTENTION_FLAG": base_features["rac_contention_flag"],
        "TRANSPORT_LAG_SEC": base_features["transport_lag_sec"],
        "APPLY_LAG_SEC": base_features["apply_lag_sec"],
        "REDO_TRANSPORT_ISSUE_FLAG": base_features["redo_transport_issue_flag"],
        "FAILOVER_EVENT_FLAG": base_features["failover_event_flag"],
        "ROLE_TRANSITION_FLAG": base_features["role_transition_flag"],
        "POST_FAILOVER_RECOVERY_FLAG": base_features[
            "post_failover_recovery_flag"
        ],
        "EXA_CELL_IO_PCT_DB_TIME": base_features["exa_cell_io_pct_db_time"],
        "EXA_OFFLOAD_EFFICIENCY": base_features["exa_offload_efficiency"],
        "STORAGE_INDEX_SAVINGS_PCT": base_features["storage_index_savings_pct"],
        "CELL_SINGLE_BLOCK_LATENCY_MS": base_features["cell_single_block_latency_ms"],
        "CELL_MULTIBLOCK_LATENCY_MS": base_features["cell_multiblock_latency_ms"],
        "EXA_STORAGE_INDEX_SAVINGS": base_features["exa_storage_index_savings"],
        "SMART_SCAN_FLAG": base_features["smart_scan_flag"],
    }
    feature_json = {
        **base_features,
        **scoring_features,
        "feature_vector_version": SCORING_VECTOR_VERSION,
        "feature_set_name": FEATURE_SET_NAME,
        "feature_set_version": FEATURE_SET_VERSION,
        "scoring_features": scoring_features,
    }
    normalization_json = {
        "vector_version": SCORING_VECTOR_VERSION,
        "normalization_defaults": SCORING_NORMALIZATION_DEFAULTS,
        "scoring_weight_feature_codes": sorted(scoring_features),
    }
    explanation_json = {
        "derived_metrics": derived,
        "feature_keys": sorted(feature_json),
        "scoring_feature_keys": sorted(scoring_features),
        "feature_sources": {
            "CPU_UTIL_P95": "cpu_pct proxy from DB CPU(s) / DB Time(s)",
            "DB_CPU_PCT_DB_TIME": "cpu_pct proxy from DB CPU(s) / DB Time(s)",
            "DB_TIME_PER_TXN": "load_profile.DB Time(s).per_transaction",
            "READ_LATENCY_MS": "User I/O wait-class average wait",
            "WRITE_LATENCY_MS": "weighted Datafile IO Stats avg_write_ms",
            "TEMP_WRITE_LATENCY_MS": "Tablespace IO Stats TEMP avg_write_ms",
            "LOG_FILE_SYNC_MS": "wait event log file sync avg_wait_ms",
            "LOG_WRITE_LATENCY_MS": "wait event log file parallel write avg_wait_ms",
            "REDO_GENERATION_PER_SEC": "load_profile.Redo size.per_second",
            "TOP_SQL_LOAD_CONCENTRATION": "sum of top SQL pct_total values",
            "AAS_PER_CPU": "derived only when host CPU count evidence exists",
            "HARD_PARSE_PCT": "Hard parses / Parses from load profile",
            "PGA_CACHE_HIT_PCT": "PGA advisory nearest current target cache hit percentage",
            "NETWORK_WAIT_PCT_DB_TIME": "wait-class Network pct_db_time",
            "CLUSTER_WAIT_PCT_DB_TIME": "topology_signals.cluster_wait_pct_db_time",
            "TRANSPORT_LAG_SEC": "topology_signals.transport_lag_sec",
            "EXA_OFFLOAD_EFFICIENCY": "topology_signals.exa_offload_efficiency",
        },
        "topology_signals": topology,
    }
    LOGGER.info(
        "Feature vector created: source_file=%s feature_count=%s scoring_feature_count=%s",
        parse_result.run_metadata.source_file_name,
        len(feature_json),
        len(scoring_features),
    )
    return {
        "feature_json": feature_json,
        "normalization_json": normalization_json,
        "explanation_json": explanation_json,
    }


def persist_deterministic_score(
    conn: Any,
    parse_result: ParseResult,
    awr_id: int,
    source_system_id: int,
    feature_vector_id: int,
    feature_vector_record: dict[str, Any],
    scoring_model: dict[str, Any],
    scoring_weights: list[dict[str, Any]],
) -> None:
    """Compute and persist one explainable deterministic score result."""

    LOGGER.info(
        "Score calculation started: AWR_ID=%s MODEL_ID=%s",
        awr_id,
        scoring_model["scoring_model_id"],
    )
    feature_json = _json_loads(feature_vector_record["feature_json"]) or {}
    score_result_record = _build_score_result_record(
        parse_result=parse_result,
        awr_id=awr_id,
        source_system_id=source_system_id,
        feature_vector_id=feature_vector_id,
        feature_json=feature_json,
        scoring_model=scoring_model,
        scoring_weights=scoring_weights,
    )
    if score_result_record is None:
        LOGGER.info(
            "Scoring skipped due to insufficient evidence: AWR_ID=%s",
            awr_id,
        )
        return
    insert_score_result(conn, score_result_record)
    LOGGER.info(
        "Score calculation completed: AWR_ID=%s total_score=%s confidence=%s "
        "workload_class=%s topology_class=%s platform_class=%s "
        "event_class=%s primary_signal_domain=%s",
        awr_id,
        score_result_record["total_score"],
        score_result_record["confidence_score"],
        score_result_record.get("workload_class"),
        score_result_record.get("topology_class"),
        score_result_record.get("platform_class"),
        score_result_record.get("event_class"),
        score_result_record.get("primary_signal_domain"),
    )


def _build_score_result_record(
    parse_result: ParseResult,
    awr_id: int,
    source_system_id: int,
    feature_vector_id: int,
    feature_json: dict[str, Any],
    scoring_model: dict[str, Any],
    scoring_weights: list[dict[str, Any]],
) -> dict[str, Any] | None:
    component_rows = _score_weighted_components(feature_json, scoring_weights)
    usable_components = [row for row in component_rows if row["raw_value"] is not None]
    if not usable_components:
        return None

    total_weight = sum(row["weight_value"] for row in usable_components)
    if total_weight <= 0:
        return None

    weighted_score = (
        sum(row["weighted_points"] for row in usable_components) / total_weight
    )
    total_score = _round_score(weighted_score)
    confidence_score = _compute_confidence_score(feature_json, usable_components)
    risk_level = _classify_risk_level(
        total_score,
        scoring_model.get("threshold_json") or {},
    )
    workload_class = _derive_workload_class(parse_result)
    topology_class = feature_json.get("topology_class")
    platform_class = feature_json.get("platform_class")
    event_class = feature_json.get("operational_event_class")

    domain_totals = _aggregate_domain_scores(usable_components)
    primary_signal_domain = _derive_primary_signal_domain(domain_totals)
    severity_score = total_score
    urgency_score = _round_score(
        (0.65 * total_score)
        + (
            0.35
            * max(
                (row["weighted_points"] for row in usable_components),
                default=0.0,
            )
        )
    )
    impact_numerator = (
        domain_totals.get("CAPACITY", 0.0)
        + domain_totals.get("CPU", 0.0)
        + domain_totals.get("SQL", 0.0)
    )
    business_impact_score = _round_score(
        (impact_numerator / max(total_weight, 1.0)) * 100.0
    )

    explanation_json = {
        "summary": _build_score_summary(
            scoring_model=scoring_model,
            usable_components=usable_components,
            total_score=total_score,
            risk_level=risk_level,
            confidence_score=confidence_score,
        ),
        "evidence": {
            "feature_coverage": len(usable_components),
            "feature_codes_used": [row["feature_code"] for row in usable_components],
            "top_domains": sorted(
                [
                    {"domain": domain, "score": _round_score(score)}
                    for domain, score in domain_totals.items()
                ],
                key=lambda row: row["score"],
                reverse=True,
            ),
        },
    }
    contribution_json = {
        "components": [
            {
                "feature_code": row["feature_code"],
                "feature_name": row["feature_name"],
                "feature_domain": row["feature_domain"],
                "raw_value": row["raw_value"],
                "transformed_value": row["transformed_value"],
                "normalized_value": row["normalized_value"],
                "weight_value": row["weight_value"],
                "weighted_points": row["weighted_points"],
                "feature_path": row["feature_path"],
                "normalization_method": row["normalization_method"],
                "transform_method": row["transform_method"],
                "polarity": row["polarity"],
            }
            for row in usable_components
        ]
    }
    scorecard_json = {
        "model_code": scoring_model["model_code"],
        "model_version": scoring_model["model_version"],
        "decision_domain": scoring_model["target_decision_domain"],
        "domain_totals": {
            domain: _round_score(score) for domain, score in domain_totals.items()
        },
        "feature_vector_version": feature_json.get("feature_vector_version"),
        "workload_class": workload_class,
        "topology_class": topology_class,
        "platform_class": platform_class,
        "event_class": event_class,
        "primary_signal_domain": primary_signal_domain,
        "coverage_ratio": round(
            len(usable_components) / max(len(scoring_weights), 1),
            4,
        ),
    }
    _, snap_end = _require_snapshot_window(parse_result)
    LOGGER.info(
        "Score classifications derived: AWR_ID=%s workload_class=%s "
        "topology_class=%s platform_class=%s event_class=%s "
        "primary_signal_domain=%s",
        awr_id,
        workload_class,
        topology_class,
        platform_class,
        event_class,
        primary_signal_domain,
    )
    return {
        "awr_id": awr_id,
        "source_system_id": source_system_id,
        "feature_vector_id": feature_vector_id,
        "scoring_model_id": scoring_model["scoring_model_id"],
        "scored_at": snap_end,
        "decision_domain": scoring_model["target_decision_domain"],
        "risk_level": risk_level,
        "total_score": total_score,
        "confidence_score": confidence_score,
        "severity_score": severity_score,
        "urgency_score": urgency_score,
        "business_impact_score": business_impact_score,
        "workload_class": workload_class,
        "topology_class": topology_class,
        "platform_class": platform_class,
        "event_class": event_class,
        "primary_signal_domain": primary_signal_domain,
        "explanation_json": _json_dumps(explanation_json),
        "contribution_json": _json_dumps(contribution_json),
        "scorecard_json": _json_dumps(scorecard_json),
    }


def _score_weighted_components(
    feature_json: dict[str, Any],
    scoring_weights: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for weight in scoring_weights:
        raw_value = _extract_feature_value_by_path(
            feature_json,
            weight["feature_path"],
        )
        transformed_value = _apply_transform(
            raw_value,
            weight["transform_method"],
        )
        normalized_value = _normalize_weight_feature(
            feature_code=weight["feature_code"],
            value=transformed_value,
            method=weight["normalization_method"],
            polarity=weight["polarity"],
        )
        weighted_points = (
            round(normalized_value * 100.0 * weight["weight_value"], 6)
            if normalized_value is not None
            else 0.0
        )
        components.append(
            {
                "feature_code": weight["feature_code"],
                "feature_name": weight["feature_name"],
                "feature_domain": weight["feature_domain"] or "GENERAL",
                "feature_path": weight["feature_path"],
                "raw_value": raw_value,
                "transformed_value": transformed_value,
                "normalized_value": normalized_value,
                "weight_value": weight["weight_value"],
                "weighted_points": weighted_points,
                "normalization_method": weight["normalization_method"],
                "transform_method": weight["transform_method"],
                "polarity": weight["polarity"],
            }
        )
    return components


def _augment_scoring_weights(
    scoring_weights: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    present_codes = {
        str(weight.get("feature_code") or "").strip()
        for weight in scoring_weights
    }
    augmented_weights = list(scoring_weights)
    added_count = 0
    for fallback_weight in TOPOLOGY_SCORING_FALLBACK_WEIGHTS:
        feature_code = fallback_weight["feature_code"]
        if feature_code in present_codes:
            continue
        augmented_weights.append(dict(fallback_weight))
        added_count += 1
    if added_count:
        LOGGER.info(
            "Scoring weights augmented with deterministic topology/platform fallbacks: added=%s",
            added_count,
        )
    return augmented_weights


def _aggregate_domain_scores(components: list[dict[str, Any]]) -> dict[str, float]:
    domain_totals: dict[str, float] = {}
    for component in components:
        domain = component["feature_domain"] or "GENERAL"
        domain_totals[domain] = domain_totals.get(domain, 0.0) + component[
            "weighted_points"
        ]
    return domain_totals


def _derive_primary_signal_domain(domain_totals: dict[str, float]) -> str | None:
    ranked_domains = [
        (str(domain), float(score))
        for domain, score in domain_totals.items()
        if _safe_float(score) is not None and float(score) > 0.0
    ]
    if not ranked_domains:
        return None
    ranked_domains.sort(key=lambda item: item[1], reverse=True)
    return ranked_domains[0][0]


def _compute_confidence_score(
    feature_json: dict[str, Any],
    components: list[dict[str, Any]],
) -> float:
    coverage_ratio = len(components) / 6.0
    coverage_score = min(max(coverage_ratio, 0.0), 1.0)
    domain_values = {
        "cpu": _safe_float(feature_json.get("CPU_UTIL_P95")),
        "io": _safe_float(feature_json.get("USER_IO_PRESSURE")),
        "commit": _safe_float(feature_json.get("COMMIT_PRESSURE")),
        "concurrency": _safe_float(feature_json.get("CONCURRENCY_PRESSURE")),
        "sql": _safe_float(feature_json.get("TOP_SQL_LOAD_CONCENTRATION")),
    }
    present_values = [value for value in domain_values.values() if value is not None]
    conflict_penalty = 0.0
    if len(present_values) >= 3:
        dominant = max(present_values)
        secondary = sorted(present_values, reverse=True)[1]
        if dominant - secondary < 7.5:
            conflict_penalty = 0.12

    richness_score = 0.0
    for feature_code in (
        "HARD_PARSES_PER_SEC",
        "PGA_SPILL_PRESSURE",
        "TEMP_IO_PRESSURE",
        "CLUSTER_WAIT_PCT_DB_TIME",
        "TRANSPORT_LAG_SEC",
        "EXA_OFFLOAD_EFFICIENCY",
    ):
        if _safe_float(feature_json.get(feature_code)) is not None:
            richness_score += 0.08
    consistency_score = (
        0.22
        if (domain_values["cpu"] or 0.0) >= (domain_values["io"] or 0.0)
        else 0.16
    )
    total = (0.5 * coverage_score) + consistency_score + richness_score - conflict_penalty
    return _round_score(min(max(total, 0.05), 0.99) * 100.0)


def _classify_risk_level(total_score: float, thresholds: dict[str, Any]) -> str:
    critical = _safe_float(thresholds.get("critical")) or 90.0
    high = _safe_float(thresholds.get("high")) or 75.0
    medium = _safe_float(thresholds.get("medium")) or 50.0
    low = _safe_float(thresholds.get("low")) or 25.0
    if total_score >= critical:
        return "CRITICAL"
    if total_score >= high:
        return "HIGH"
    if total_score >= medium:
        return "MEDIUM"
    if total_score >= low:
        return "LOW"
    return "LOW"


def _build_score_summary(
    scoring_model: dict[str, Any],
    usable_components: list[dict[str, Any]],
    total_score: float,
    risk_level: str,
    confidence_score: float,
) -> str:
    top_components = sorted(
        usable_components,
        key=lambda row: row["weighted_points"],
        reverse=True,
    )[:3]
    driver_text = ", ".join(
        f"{row['feature_code']}={_display_score_value(row['raw_value'])}"
        for row in top_components
    )
    return (
        f"Deterministic model {scoring_model['model_code']} produced a total score of {total_score:.2f} "
        f"with risk level {risk_level} and confidence {confidence_score:.2f}. "
        f"The strongest weighted drivers were {driver_text}."
    )


def _extract_feature_value_by_path(
    feature_json: dict[str, Any],
    feature_path: str | None,
) -> float | None:
    if not feature_path:
        return None
    normalized_path = feature_path.strip()
    if normalized_path.startswith("$."):
        normalized_path = normalized_path[2:]
    value: Any = feature_json
    for key in normalized_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return _safe_float(value)


def _apply_transform(value: float | None, transform_method: str | None) -> float | None:
    if value is None:
        return None
    method = (transform_method or "NONE").upper()
    if method == "NONE":
        return value
    if method == "LOG1P":
        if value < 0:
            return None
        import math

        return round(math.log1p(value), 6)
    return value


def _normalize_weight_feature(
    feature_code: str,
    value: float | None,
    method: str | None,
    polarity: str | None,
) -> float | None:
    if value is None:
        return None
    normalization = (method or "MINMAX").upper()
    defaults = SCORING_NORMALIZATION_DEFAULTS.get(
        feature_code,
        {"min": 0.0, "max": 100.0},
    )
    if normalization == "ROBUST":
        median = defaults.get("median", 0.0)
        iqr = defaults.get("iqr", 1.0) or 1.0
        normalized = (value - median) / iqr
        normalized = normalized / 4.0
        normalized = max(0.0, min(1.0, normalized))
    else:
        min_value = defaults.get("min", 0.0)
        max_value = defaults.get("max", 100.0)
        if max_value <= min_value:
            return None
        normalized = (value - min_value) / (max_value - min_value)
        normalized = max(0.0, min(1.0, normalized))

    normalized_polarity = (polarity or "HIGH_BAD").upper()
    if normalized_polarity in {"LOW_BAD", "HIGH_GOOD"}:
        normalized = 1.0 - normalized
    return round(normalized, 6)


def _extract_load_profile_transaction_metric(
    parse_result: ParseResult,
    metric_name: str,
) -> float | None:
    normalized_metric_name = _normalize_load_profile_metric_name(metric_name)
    for metric in parse_result.cpu_metrics:
        if metric.get("metric_group") != "load_profile":
            continue
        metric_name_value = _normalize_load_profile_metric_name(
            str(metric.get("metric_name") or "").strip()
        )
        if metric_name_value != normalized_metric_name:
            continue
        return _safe_float(metric.get("per_transaction"))
    return None


LOAD_PROFILE_METRIC_ALIASES = {
    "DB Time (s)": "DB Time(s)",
    "DB CPU (s)": "DB CPU(s)",
    "Redo size (bytes)": "Redo size",
    "Physical read (blocks)": "Physical reads",
    "Physical write (blocks)": "Physical writes",
    "Parses (SQL)": "Parses",
    "Hard parses (SQL)": "Hard parses",
    "Executes (SQL)": "Executions",
}


def _normalize_load_profile_metric_name(metric_name: str) -> str:
    """Normalize native load-profile labels to canonical feature names."""

    normalized_name = " ".join(metric_name.strip().split())
    return LOAD_PROFILE_METRIC_ALIASES.get(normalized_name, normalized_name)


def _ensure_native_feature_inputs(parse_result: ParseResult) -> dict[str, Any]:
    """Supplement native parser output with deterministic fallback feature inputs."""

    source_lines = _load_native_source_lines(parse_result)
    if source_lines:
        _ensure_native_cpu_metrics(parse_result, source_lines)
    return _ensure_topology_lag_signals(parse_result, source_lines)


def _load_native_source_lines(parse_result: ParseResult) -> list[str]:
    """Read native AWR source lines when the original report path is available."""

    source_file_path = str(parse_result.run_metadata.source_file_path or "").strip()
    if not source_file_path:
        return []

    source_path = Path(source_file_path)
    if not source_path.exists() or not source_path.is_file():
        return []

    try:
        return source_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []


def _ensure_native_cpu_metrics(
    parse_result: ParseResult,
    source_lines: list[str],
) -> None:
    """Backfill core CPU load-profile metrics from native AWR text when missing."""

    for metric_label in ("DB Time (s)", "DB CPU (s)"):
        metric_name = _normalize_load_profile_metric_name(metric_label)
        if _extract_load_profile_metric(parse_result, metric_name) is not None:
            continue
        metric_row = _extract_native_load_profile_row(source_lines, metric_label)
        if metric_row is None:
            continue
        parse_result.cpu_metrics.append(metric_row)


def _extract_native_load_profile_row(
    source_lines: list[str],
    metric_label: str,
) -> dict[str, Any] | None:
    """Extract one native load-profile row directly from raw report text."""

    pattern = re.compile(
        rf"^\s*{re.escape(metric_label)}\s*:\s*"
        r"([0-9,]+(?:\.\d+)?)"
        r"(?:\s+([0-9,]+(?:\.\d+)?))?",
    )
    for line in source_lines:
        match = pattern.match(line)
        if match is None:
            continue
        per_second = _safe_float(match.group(1))
        per_transaction = _safe_float(match.group(2)) if match.group(2) else None
        if per_second is None:
            return None
        return {
            "metric_name": _normalize_load_profile_metric_name(metric_label),
            "per_second": per_second,
            "per_transaction": per_transaction,
            "metric_source_section": "native_fallback",
            "metric_group": "load_profile",
        }
    return None


def _ensure_topology_lag_signals(
    parse_result: ParseResult,
    source_lines: list[str] | None = None,
) -> dict[str, Any]:
    """Supplement topology signals with deterministic native RAC and Data Guard values."""

    from src.parser.metadata_parser import extract_dataguard_lag_metrics

    topology = dict(parse_result.topology_signals or {})
    if (
        topology.get("transport_lag_sec") is not None
        and topology.get("apply_lag_sec") is not None
        and topology.get("is_rac") is not None
        and topology.get("interconnect_stress_flag") is not None
        and topology.get("rac_contention_flag") is not None
    ):
        parse_result.topology_signals = topology
        return topology

    resolved_source_lines = source_lines or _load_native_source_lines(parse_result)
    if not resolved_source_lines:
        parse_result.topology_signals = topology
        return topology

    lag_metrics = extract_dataguard_lag_metrics(resolved_source_lines)
    transport_lag_sec = _safe_float(lag_metrics.get("transport_lag_sec"))
    apply_lag_sec = _safe_float(lag_metrics.get("apply_lag_sec"))

    if topology.get("transport_lag_sec") is None and transport_lag_sec is not None:
        topology["transport_lag_sec"] = transport_lag_sec
    if topology.get("apply_lag_sec") is None and apply_lag_sec is not None:
        topology["apply_lag_sec"] = apply_lag_sec
    if transport_lag_sec is not None or apply_lag_sec is not None:
        topology.setdefault("is_dataguard", True)
        topology.setdefault(
            "redo_transport_issue_flag",
            bool((transport_lag_sec or 0.0) > 0.0 or (apply_lag_sec or 0.0) > 0.0),
        )

    cluster_wait_pct = _sum_wait_class_pct(parse_result, "Cluster")
    gc_cr_wait_pct = _sum_event_pct(parse_result, ("gc cr",))
    gc_current_wait_pct = _sum_event_pct(parse_result, ("gc current",))
    gc_buffer_busy_pct = _sum_event_pct(parse_result, ("gc buffer busy",))
    if topology.get("cluster_wait_pct_db_time") is None and cluster_wait_pct is not None:
        topology["cluster_wait_pct_db_time"] = round(cluster_wait_pct, 4)
    if topology.get("gc_cr_wait_pct_db_time") is None and gc_cr_wait_pct is not None:
        topology["gc_cr_wait_pct_db_time"] = round(gc_cr_wait_pct, 4)
    if (
        topology.get("gc_current_wait_pct_db_time") is None
        and gc_current_wait_pct is not None
    ):
        topology["gc_current_wait_pct_db_time"] = round(gc_current_wait_pct, 4)
    if (
        topology.get("gc_buffer_busy_pct_db_time") is None
        and gc_buffer_busy_pct is not None
    ):
        topology["gc_buffer_busy_pct_db_time"] = round(gc_buffer_busy_pct, 4)
    normalized_text = f" {' '.join(' '.join(resolved_source_lines).lower().split())} "
    native_rac_detected = any(
        pattern in normalized_text for pattern in NATIVE_RAC_TEXT_PATTERNS
    )
    derived_is_rac = bool(
        native_rac_detected
        or (cluster_wait_pct or 0.0) > 0.0
        or (gc_cr_wait_pct or 0.0) > 0.0
        or (gc_current_wait_pct or 0.0) > 0.0
        or (gc_buffer_busy_pct or 0.0) > 0.0
    )
    if derived_is_rac:
        topology["is_rac"] = bool(topology.get("is_rac") or derived_is_rac)
        topology["interconnect_stress_flag"] = bool(
            topology.get("interconnect_stress_flag")
            or (cluster_wait_pct or 0.0) >= 8.0
            or (gc_cr_wait_pct or 0.0) + (gc_current_wait_pct or 0.0) >= 8.0
            or "interconnect" in normalized_text
        )
        topology["rac_contention_flag"] = bool(
            topology.get("rac_contention_flag")
            or (gc_buffer_busy_pct or 0.0) >= 2.0
            or (cluster_wait_pct or 0.0) >= 10.0
        )

    parse_result.topology_signals = topology
    return topology


def _apply_low_signal_feature_suppression(base_features: dict[str, Any]) -> None:
    """Suppress low-materiality IO and COMMIT signals that create native false positives."""

    read_latency_ms = _safe_float(base_features.get("read_latency_ms"))
    user_io_pct = _safe_float(base_features.get("user_io_pct"))
    temp_spill_pct = _safe_float(base_features.get("temp_spill_pct"))
    sorts_disk_pct = _safe_float(base_features.get("sorts_disk_pct"))
    log_file_sync_ms = _safe_float(base_features.get("log_file_sync_ms"))
    commit_pct = _safe_float(base_features.get("commit_pct"))

    if (
        read_latency_ms is not None
        and read_latency_ms < LOW_MATERIALITY_READ_LATENCY_MS
        and (user_io_pct is None or user_io_pct < LOW_MATERIALITY_USER_IO_PCT)
    ):
        base_features["read_latency_ms"] = None
        base_features["user_io_pct"] = None

    if (
        (temp_spill_pct or 0.0) >= 25.0
        or (sorts_disk_pct or 0.0) >= 20.0
    ) and (
        read_latency_ms is None
        or read_latency_ms < 20.0
    ) and (
        user_io_pct is None
        or user_io_pct < 50.0
    ):
        base_features["read_latency_ms"] = None
        base_features["user_io_pct"] = None

    if (
        log_file_sync_ms is not None
        and log_file_sync_ms < LOW_MATERIALITY_LOG_FILE_SYNC_MS
        and (commit_pct is None or commit_pct < LOW_MATERIALITY_COMMIT_PCT)
    ):
        base_features["log_file_sync_ms"] = None
        base_features["log_write_latency_ms"] = None
        base_features["commit_pct"] = None


def _extract_wait_class_avg_wait_ms(
    parse_result: ParseResult,
    wait_class: str,
) -> float | None:
    weighted_pairs: list[tuple[float, float]] = []
    for row in parse_result.wait_events:
        if str(row.get("wait_class") or "") != wait_class:
            continue
        avg_wait_ms = _safe_float(row.get("avg_wait_ms"))
        pct_db_time = _safe_float(row.get("pct_db_time"))
        if avg_wait_ms is None or pct_db_time is None:
            continue
        weighted_pairs.append((avg_wait_ms, pct_db_time))
    if not weighted_pairs:
        return None
    numerator = sum(value * weight for value, weight in weighted_pairs)
    denominator = sum(weight for _, weight in weighted_pairs)
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _extract_wait_event_avg_wait_ms(
    parse_result: ParseResult,
    event_fragments: tuple[str, ...],
) -> float | None:
    weighted_pairs: list[tuple[float, float]] = []
    normalized_fragments = tuple(fragment.lower() for fragment in event_fragments)
    for row in parse_result.wait_events:
        event_name = str(row.get("event_name") or "").strip().lower()
        if not any(fragment in event_name for fragment in normalized_fragments):
            continue
        avg_wait_ms = _safe_float(row.get("avg_wait_ms"))
        pct_db_time = _safe_float(row.get("pct_db_time")) or 1.0
        if avg_wait_ms is None:
            continue
        weighted_pairs.append((avg_wait_ms, pct_db_time))
    if not weighted_pairs:
        return None
    numerator = sum(value * weight for value, weight in weighted_pairs)
    denominator = sum(weight for _, weight in weighted_pairs)
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _extract_exact_wait_event_avg_wait_ms(
    parse_result: ParseResult,
    event_names: tuple[str, ...],
) -> float | None:
    weighted_pairs: list[tuple[float, float]] = []
    valid_names = set(event_names)
    for row in parse_result.wait_events:
        event_name = str(row.get("event_name") or "").strip()
        if event_name not in valid_names:
            continue
        avg_wait_ms = _safe_float(row.get("avg_wait_ms"))
        pct_db_time = _safe_float(row.get("pct_db_time")) or 1.0
        if avg_wait_ms is None:
            continue
        weighted_pairs.append((avg_wait_ms, pct_db_time))
    if not weighted_pairs:
        return None
    numerator = sum(value * weight for value, weight in weighted_pairs)
    denominator = sum(weight for _, weight in weighted_pairs)
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _sum_event_pct(
    parse_result: ParseResult,
    event_fragments: tuple[str, ...],
) -> float | None:
    normalized_fragments = tuple(fragment.lower() for fragment in event_fragments)
    values = _compact_floats(
        [
            _safe_float(row.get("pct_db_time"))
            for row in parse_result.wait_events
            if any(
                fragment in str(row.get("event_name") or "").strip().lower()
                for fragment in normalized_fragments
            )
        ]
    )
    if not values:
        return None
    return round(sum(values), 4)


def _sum_exact_event_pct(
    parse_result: ParseResult,
    event_names: tuple[str, ...],
) -> float | None:
    valid_names = set(event_names)
    values = _compact_floats(
        [
            _safe_float(row.get("pct_db_time"))
            for row in parse_result.wait_events
            if str(row.get("event_name") or "").strip() in valid_names
        ]
    )
    if not values:
        return None
    return round(sum(values), 4)


def _aggregate_datafile_latency(
    parse_result: ParseResult,
    latency_key: str,
    weight_key: str,
) -> float | None:
    weighted_pairs: list[tuple[float, float]] = []
    for row in parse_result.datafile_io_stats:
        latency_value = _safe_float(row.get(latency_key))
        weight_value = _safe_float(row.get(weight_key))
        if latency_value is None or weight_value is None or weight_value < 0:
            continue
        weighted_pairs.append((latency_value, weight_value))
    if not weighted_pairs:
        return None
    numerator = sum(value * weight for value, weight in weighted_pairs)
    denominator = sum(weight for _, weight in weighted_pairs)
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _extract_temp_tablespace_metric(
    parse_result: ParseResult,
    metric_key: str,
) -> float | None:
    for row in parse_result.tablespace_io_stats:
        if str(row.get("tablespace") or "").strip().upper() != "TEMP":
            continue
        return _safe_float(row.get(metric_key))
    return None


def _extract_instance_efficiency_metric(
    parse_result: ParseResult,
    metric_name: str,
) -> float | None:
    for metric in parse_result.cpu_metrics:
        if metric.get("metric_group") != "instance_efficiency":
            continue
        if str(metric.get("metric_name") or "").strip() != metric_name:
            continue
        return _safe_float(metric.get("metric_value"))
    return None


def _compute_hard_parse_pct(parse_result: ParseResult) -> float | None:
    hard_parses = _extract_load_profile_metric(parse_result, "Hard parses")
    parses = _extract_load_profile_metric(parse_result, "Parses")
    if hard_parses is None or parses is None or parses <= 0:
        return None
    return round((hard_parses / parses) * 100.0, 4)


def _extract_pga_cache_hit_pct(parse_result: ParseResult) -> float | None:
    advisory_rows = list(parse_result.pga_advisory.get("rows") or [])
    if not advisory_rows:
        return None

    current_target_mb = _safe_float(parse_result.pga_advisory.get("current_target_mb"))
    if current_target_mb is not None:
        nearest_row = min(
            advisory_rows,
            key=lambda row: abs(
                (_safe_float(row.get("target_mb")) or current_target_mb)
                - current_target_mb
            ),
        )
        return _safe_float(nearest_row.get("cache_hit_pct"))

    return _safe_float(advisory_rows[0].get("cache_hit_pct"))


def _compute_temp_spill_pct(derived: dict[str, Any]) -> float | None:
    spill_ratio = _safe_float(derived.get("pga_spill_pressure"))
    if spill_ratio is None:
        return None
    return round(spill_ratio * 100.0, 4)


def _compute_sorts_disk_pct(parse_result: ParseResult) -> float | None:
    in_memory_sort_pct = _extract_instance_efficiency_metric(
        parse_result,
        "In-memory Sort %",
    )
    if in_memory_sort_pct is None:
        return None
    return round(max(0.0, 100.0 - in_memory_sort_pct), 4)


def _compute_workarea_execution_pct(
    parse_result: ParseResult,
    numerator_key: str,
) -> float | None:
    workarea_histogram = parse_result.workarea_histogram or {}
    optimal = _safe_float(workarea_histogram.get("optimal_executions"))
    onepass = _safe_float(workarea_histogram.get("onepass_executions"))
    multipass = _safe_float(workarea_histogram.get("multipass_executions"))
    numerator = _safe_float(workarea_histogram.get(numerator_key))
    if (
        optimal is None
        or onepass is None
        or multipass is None
        or numerator is None
    ):
        return None
    total = optimal + onepass + multipass
    if total <= 0:
        return None
    return round((numerator / total) * 100.0, 4)


def _extract_host_cpu_metric(
    parse_result: ParseResult,
    metric_name: str,
) -> float | None:
    for metric in parse_result.cpu_metrics:
        if metric.get("metric_group") != "host_cpu":
            continue
        if str(metric.get("metric_name") or "").strip() != metric_name:
            continue
        return _safe_float(metric.get("metric_value"))
    return None


def _derive_aas_per_cpu(parse_result: ParseResult) -> float | None:
    # Keep this analytically honest: the current parser does not expose CPU-count
    # evidence, so AAS/CPU remains null rather than being backfilled with a proxy.
    return None


def _flag_to_float(value: Any) -> float | None:
    if value is None:
        return None
    return 1.0 if bool(value) else 0.0


def _display_score_value(value: Any) -> str:
    numeric_value = _safe_float(value)
    if numeric_value is None:
        return "null"
    return f"{numeric_value:.4f}"


def _round_score(value: float | None) -> float:
    if value is None:
        return 0.0
    return round(max(0.0, min(value, 100.0)), 4)


def _compact_floats(values: list[float | None]) -> list[float]:
    return [value for value in values if value is not None]


def _milliseconds_to_seconds(value: Any) -> float | None:
    numeric_value = _safe_float(value)
    if numeric_value is None:
        return None
    return round(numeric_value / 1000.0, 6)


def _per_exec(numerator: Any, executions: Any) -> float | None:
    numeric_numerator = _safe_float(numerator)
    numeric_executions = _safe_float(executions)
    if numeric_numerator is None or numeric_executions is None:
        return None
    if numeric_executions <= 0:
        return None
    return round(numeric_numerator / numeric_executions, 6)


def _truncate(value: str, max_length: int) -> str | None:
    normalized = value.strip()
    if not normalized:
        return None
    return normalized[:max_length]


def _safe_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", ""))
        except ValueError:
            return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        normalized = value.replace(",", "").strip()
        if not normalized:
            return None
        try:
            return int(float(normalized))
        except ValueError:
            return None
    return None


def _json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, default=str, sort_keys=True)


def _json_loads(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None
    try:
        return json.loads(value.read())
    except Exception:  # noqa: BLE001
        return None


def _configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=_resolve_log_level(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    args = argv if argv is not None else sys.argv[1:]
    maintenance_mode = str(os.getenv("AWR_MAINTENANCE_MODE", "")).strip().upper()
    if args and args[0].strip().upper() == FEATURE_REBUILD_MODE:
        maintenance_mode = FEATURE_REBUILD_MODE
        args = args[1:]
    elif args and args[0].strip().upper() == REFRESH_PARSER_OUTPUT_JSON_MODE:
        maintenance_mode = REFRESH_PARSER_OUTPUT_JSON_MODE
        args = args[1:]
    elif args and args[0].strip().upper() == DB_TREND_ANALYSIS_MODE:
        maintenance_mode = DB_TREND_ANALYSIS_MODE
        args = args[1:]

    if maintenance_mode == FEATURE_REBUILD_MODE:
        source_system_id = _to_int(os.getenv("AWR_BACKFILL_SOURCE_SYSTEM_ID"))
        awr_ids = _parse_comma_separated_ids(os.getenv("AWR_BACKFILL_AWR_IDS"))
        only_missing_promoted_keys = (
            str(os.getenv("AWR_BACKFILL_MISSING_ONLY", "Y")).strip().upper()
            not in {"N", "NO", "FALSE", "0"}
        )
        result = rebuild_feature_vectors(
            source_system_id=source_system_id,
            awr_ids=awr_ids,
            only_missing_promoted_keys=only_missing_promoted_keys,
        )
    elif maintenance_mode == REFRESH_PARSER_OUTPUT_JSON_MODE:
        source_system_id = _to_int(os.getenv("AWR_BACKFILL_SOURCE_SYSTEM_ID"))
        awr_ids = _parse_comma_separated_ids(os.getenv("AWR_BACKFILL_AWR_IDS"))
        refresh_rebuild_derived = (
            str(os.getenv("AWR_REFRESH_REBUILD_DERIVED", "FALSE")).strip().upper()
            in {"1", "Y", "YES", "TRUE"}
        )
        result = refresh_parser_output_json(
            source_system_id=source_system_id,
            awr_ids=awr_ids,
            refresh_rebuild_derived=refresh_rebuild_derived,
        )
    elif maintenance_mode == DB_TREND_ANALYSIS_MODE:
        db_conn = get_db_connection()
        try:
            db_name = str(os.getenv("AWR_TREND_DB_NAME", "")).strip() or None
            dbid = _to_int(os.getenv("AWR_TREND_DBID"))
            targets = load_db_trend_targets(
                conn=db_conn,
                db_name=db_name,
                dbid=dbid,
            )
            trend_analysis_results = run_db_trend_analysis(
                conn=db_conn,
                affected_databases=targets,
            )
            db_conn.commit()
            result = {
                "mode": DB_TREND_ANALYSIS_MODE,
                "target_count": len(targets),
                "trend_analysis_results": trend_analysis_results,
            }
        finally:
            db_conn.close()
    else:
        input_dir = (
            Path(args[0]) if args else Path(os.getenv("AWR_INPUT_DIR", "data/input"))
        )
        result = process_awr_batch(input_dir=input_dir)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
