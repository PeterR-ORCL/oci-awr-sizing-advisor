"""Registry-driven canonical AWR section definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AwrSectionDefinition:
    """Deterministic metadata for one canonical AWR section."""

    canonical_name: str
    aliases: tuple[str, ...]
    extractor_id: str
    required: bool = False
    section_kind: str = "functional"
    completeness_role: str = "optional_core"


SECTION_REGISTRY: tuple[AwrSectionDefinition, ...] = (
    AwrSectionDefinition(
        canonical_name="report_header",
        aliases=(
            "workload repository report",
            "awr report",
        ),
        extractor_id="parse_awr_metadata",
        required=True,
        section_kind="functional",
        completeness_role="required",
    ),
    AwrSectionDefinition(
        canonical_name="cpu",
        aliases=(
            "load profile",
            "host cpu",
            "cpu statistics",
            "foreground cpu usage summary",
        ),
        extractor_id="parse_cpu_section",
        required=True,
        section_kind="functional",
        completeness_role="required",
    ),
    AwrSectionDefinition(
        canonical_name="waits",
        aliases=(
            "top 10 foreground events by total wait time",
            "foreground wait events",
            "wait classes by total wait time",
        ),
        extractor_id="parse_waits_section",
        required=True,
        section_kind="functional",
        completeness_role="required",
    ),
    AwrSectionDefinition(
        canonical_name="top_sql",
        aliases=(
            "sql ordered by elapsed time",
            "sql ordered by cpu time",
            "sql ordered by gets",
            "sql ordered by reads",
            "sql ordered by executions",
        ),
        extractor_id="parse_sql_section",
        required=False,
        section_kind="functional",
        completeness_role="optional_core",
    ),
    AwrSectionDefinition(
        canonical_name="io",
        aliases=(
            "iostat by function",
            "iostat by filetype summary",
            "i o statistics",
            "io profile",
            "tablespace io stats",
            "file io stats",
            "segments by physical reads",
        ),
        extractor_id="parse_io_related_sections",
        required=False,
        section_kind="functional",
        completeness_role="optional_core",
    ),
    AwrSectionDefinition(
        canonical_name="sessions",
        aliases=(
            "session statistics",
            "instance activity statistics",
            "key instance activity stats",
            "instance activity stats",
            "sql ordered by version count",
            "logons cumulative",
            "activity during the snapshot period",
        ),
        extractor_id="parse_session_related_sections",
        required=False,
        section_kind="functional",
        completeness_role="optional_core",
    ),
    AwrSectionDefinition(
        canonical_name="cluster_summary",
        aliases=(
            "cluster summary",
        ),
        extractor_id="parse_topology_signals",
        required=False,
        section_kind="functional",
        completeness_role="neutral",
    ),
    AwrSectionDefinition(
        canonical_name="rac_statistics",
        aliases=(
            "rac statistics",
        ),
        extractor_id="parse_topology_signals",
        required=False,
        section_kind="functional",
        completeness_role="neutral",
    ),
    AwrSectionDefinition(
        canonical_name="transactions_redo",
        aliases=(
            "transactions and redo",
        ),
        extractor_id="parse_topology_signals",
        required=False,
        section_kind="functional",
        completeness_role="neutral",
    ),
    AwrSectionDefinition(
        canonical_name="cluster",
        aliases=(
            "global cache",
            "cluster wait",
            "cache fusion",
            "gc cr",
            "gc current",
        ),
        extractor_id="parse_topology_signals",
        required=False,
        section_kind="functional",
        completeness_role="optional_contextual",
    ),
    AwrSectionDefinition(
        canonical_name="dataguard",
        aliases=(
            "data guard statistics",
            "data guard",
            "replication statistics",
            "transport lag",
            "apply lag",
            "managed recovery",
            "database role",
        ),
        extractor_id="parse_topology_signals",
        required=False,
        section_kind="functional",
        completeness_role="optional_contextual",
    ),
    AwrSectionDefinition(
        canonical_name="exadata",
        aliases=(
            "exadata",
            "cell smart table scan",
            "cell physical io interconnect bytes",
            "bytes eligible for predicate offload",
            "storage index",
        ),
        extractor_id="parse_topology_signals",
        required=False,
        section_kind="functional",
        completeness_role="optional_contextual",
    ),
    AwrSectionDefinition(
        canonical_name="workload_note",
        aliases=(
            "workload note",
        ),
        extractor_id="parse_annotation_text_section",
        required=False,
        section_kind="annotation",
        completeness_role="neutral",
    ),
    AwrSectionDefinition(
        canonical_name="anomaly_flags",
        aliases=(
            "anomaly flags",
        ),
        extractor_id="parse_annotation_labels_section",
        required=False,
        section_kind="annotation",
        completeness_role="neutral",
    ),
)


def get_section_registry() -> tuple[AwrSectionDefinition, ...]:
    """Return the canonical immutable section registry."""

    return SECTION_REGISTRY
