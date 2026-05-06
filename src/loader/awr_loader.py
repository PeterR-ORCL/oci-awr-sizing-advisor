"""Loader-facing AWR source discovery.

The loader layer owns source and file inventory only. It deliberately does
not inspect AWR contents, classify sections, extract metrics, or produce
parser diagnostics. Parser-facing code receives explicit files from this
contract and remains responsible for AWR interpretation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict


class LoaderFile(TypedDict):
    """One discovered AWR source file and file-level staging metadata."""

    file_name: str
    file_path: str
    file_size_bytes: int
    read_status: str
    loader_notes: list[str]


class LoaderResult(TypedDict):
    """Loader boundary result consumed by parser orchestration."""

    source_type: str
    source_path: str
    files_discovered: int
    files: list[LoaderFile]
    loader_status: str
    loader_notes: list[str]


def load_awr_sources(
    source_path: str | Path,
    *,
    source_type: str = "LOCAL",
) -> LoaderResult:
    """Discover AWR source files without interpreting report contents.

    This preserves the current local ``*.out`` discovery behavior used by
    ``scripts/run_analysis.py`` while making the loader/parser handoff
    explicit. Object Storage discovery is intentionally not implemented in
    this phase.
    """

    normalized_source_type = str(source_type or "LOCAL").strip().upper()
    if normalized_source_type != "LOCAL":
        raise NotImplementedError(
            "Only LOCAL AWR source discovery is implemented in this phase."
        )

    directory = Path(source_path)
    if not directory.exists():
        raise FileNotFoundError(f"Input directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {directory}")

    files: list[LoaderFile] = []
    loader_notes: list[str] = []
    for path in sorted(directory.glob("*.out")):
        if not path.is_file():
            continue
        files.append(_build_loader_file(path))

    loader_status = "READY" if files else "EMPTY"
    if not files:
        loader_notes.append("No local AWR .out files discovered.")

    return {
        "source_type": normalized_source_type,
        "source_path": str(directory),
        "files_discovered": len(files),
        "files": files,
        "loader_status": loader_status,
        "loader_notes": loader_notes,
    }


def loader_file_paths(loader_result: LoaderResult) -> list[Path]:
    """Return ready local paths from a loader result for parser handoff."""

    return [
        Path(file_record["file_path"])
        for file_record in loader_result.get("files", [])
        if file_record.get("read_status") == "READY"
    ]


def _build_loader_file(path: Path) -> LoaderFile:
    notes: list[str] = []
    read_status = "READY"
    try:
        size_bytes = path.stat().st_size
    except OSError as exc:
        size_bytes = 0
        read_status = "ERROR"
        notes.append(f"File metadata unavailable: {type(exc).__name__}: {exc}")

    return {
        "file_name": path.name,
        "file_path": str(path),
        "file_size_bytes": size_bytes,
        "read_status": read_status,
        "loader_notes": notes,
    }


def loader_result_to_jsonable(loader_result: LoaderResult) -> dict[str, Any]:
    """Return a plain dict copy for logging or future presentation adapters."""

    return {
        "source_type": loader_result.get("source_type"),
        "source_path": loader_result.get("source_path"),
        "files_discovered": loader_result.get("files_discovered", 0),
        "files": [dict(file_record) for file_record in loader_result.get("files", [])],
        "loader_status": loader_result.get("loader_status"),
        "loader_notes": list(loader_result.get("loader_notes", [])),
    }
