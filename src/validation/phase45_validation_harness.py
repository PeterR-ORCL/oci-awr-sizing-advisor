from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from inspect import signature
from pathlib import Path
from typing import Any, Callable
import sys
import types

from src.analysis.decision_engine import (
    DOMAIN_ORDER,
    QUALIFICATION_THRESHOLD,
    build_decision,
)
from src.analysis.output_layer import build_analysis_output
from src.analysis.recommendation_engine import generate_decision_recommendations
from src.analysis.trend_engine import compute_trend_features, detect_anomalies
from src.parser.awr_parser import parse_awr_file

MANIFEST_CSV_NAME = "manifest.csv"
MANIFEST_JSON_NAME = "manifest.json"
OUTPUT_VERSION = "phase4.5"
OUTPUT_SOURCE = "phase4.5-validation"


@dataclass(slots=True)
class ValidationManifestEntry:
    begin_time: datetime | None
    db_name: str
    dbid: int | None
    expected_primary_issue: str
    expected_secondary_issues: list[str]
    expected_status: str
    file: str
    notes: str
    scenario_name: str
    manifest_order: int = 0


@dataclass(slots=True)
class ValidationCaseResult:
    scenario_name: str
    file: str
    expected_primary_issue: str
    actual_primary_issue: str
    expected_secondary_issues: list[str]
    actual_secondary_issues: list[str]
    expected_status: str
    actual_status: str
    passed: bool
    validation_diagnostics: dict[str, Any] | None
    output: dict[str, Any]


@dataclass(slots=True)
class ValidationHarnessResult:
    manifest_source: str
    case_count: int
    passed_count: int
    failed_count: int
    cases: list[ValidationCaseResult]

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_source": self.manifest_source,
            "case_count": self.case_count,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "cases": [asdict(case) for case in self.cases],
        }


@dataclass(slots=True)
class _ScenarioArtifact:
    awr_id: int
    entry: ValidationManifestEntry
    parse_result: Any
    feature_json: dict[str, Any]
    trend_rows: list[dict[str, Any]]


def load_manifest_entries(
    input_dir: str | Path,
    manifest_path: str | Path | None = None,
) -> tuple[list[ValidationManifestEntry], str]:
    base_dir = Path(input_dir)
    if manifest_path is not None:
        resolved_manifest = Path(manifest_path)
        suffix = resolved_manifest.suffix.lower()
        if suffix == ".csv":
            return _load_manifest_csv(resolved_manifest), str(resolved_manifest)
        if suffix == ".json":
            return _load_manifest_json(resolved_manifest), str(resolved_manifest)
        raise ValueError(
            "Manifest path must point to a .csv or .json file."
        )

    csv_path = base_dir / MANIFEST_CSV_NAME
    json_path = base_dir / MANIFEST_JSON_NAME
    if csv_path.exists():
        return _load_manifest_csv(csv_path), str(csv_path)
    if json_path.exists():
        return _load_manifest_json(json_path), str(json_path)
    raise FileNotFoundError(
        f"No manifest found in {base_dir}; expected {MANIFEST_CSV_NAME} or {MANIFEST_JSON_NAME}."
    )


def run_validation_harness(
    input_dir: str | Path,
    manifest_path: str | Path | None = None,
    parser: Callable[[str | Path], Any] = parse_awr_file,
    feature_vector_builder: Callable[[Any, int, int], dict[str, Any]] | None = None,
    decision_builder: Callable[..., Any] = build_decision,
    recommendation_builder: Callable[[Any], list[Any]] = generate_decision_recommendations,
    output_builder: Callable[..., dict[str, Any]] = build_analysis_output,
    include_decision_diagnostics: bool = True,
) -> ValidationHarnessResult:
    entries, manifest_source = load_manifest_entries(
        input_dir,
        manifest_path=manifest_path,
    )
    builder = feature_vector_builder or _load_feature_vector_builder()
    artifacts = _build_scenario_artifacts(entries, Path(input_dir), parser, builder)
    _populate_local_trend_rows(artifacts)

    case_results: list[ValidationCaseResult] = []
    for artifact in artifacts:
        decision = _invoke_decision_builder(
            decision_builder=decision_builder,
            awr_id=artifact.awr_id,
            feature_json=artifact.feature_json,
            trend_rows=artifact.trend_rows,
            include_decision_diagnostics=include_decision_diagnostics,
        )
        recommendations = recommendation_builder(decision)
        output = output_builder(
            decision=decision,
            recommendations=recommendations,
            output_version=OUTPUT_VERSION,
            source=OUTPUT_SOURCE,
        )
        actual_primary_issue, actual_secondary_issues = (
            normalize_decision_for_validation(decision)
        )
        validation_diagnostics = None
        if include_decision_diagnostics:
            validation_diagnostics = _build_validation_diagnostics(
                decision=decision,
                actual_primary_issue=actual_primary_issue,
                actual_secondary_issues=actual_secondary_issues,
            )
            output["validation_diagnostics"] = validation_diagnostics
        expected_secondary_issues = artifact.entry.expected_secondary_issues
        passed = (
            actual_primary_issue == artifact.entry.expected_primary_issue
            and actual_secondary_issues == expected_secondary_issues
            and decision.overall_status == artifact.entry.expected_status
        )
        case_results.append(
            ValidationCaseResult(
                scenario_name=artifact.entry.scenario_name,
                file=artifact.entry.file,
                expected_primary_issue=artifact.entry.expected_primary_issue,
                actual_primary_issue=actual_primary_issue,
                expected_secondary_issues=expected_secondary_issues,
                actual_secondary_issues=actual_secondary_issues,
                expected_status=artifact.entry.expected_status,
                actual_status=decision.overall_status,
                passed=passed,
                validation_diagnostics=validation_diagnostics,
                output=output,
            )
        )

    passed_count = sum(1 for case in case_results if case.passed)
    failed_count = len(case_results) - passed_count
    return ValidationHarnessResult(
        manifest_source=manifest_source,
        case_count=len(case_results),
        passed_count=passed_count,
        failed_count=failed_count,
        cases=case_results,
    )


def normalize_decision_for_validation(decision: Any) -> tuple[str, list[str]]:
    evidence = getattr(decision, "evidence", {}) or {}
    domain_scores = evidence.get("domain_scores") or {}
    qualifying_domains = [
        domain
        for domain in DOMAIN_ORDER
        if _safe_float(domain_scores.get(domain)) is not None
        and float(domain_scores[domain]) >= QUALIFICATION_THRESHOLD
    ]
    if getattr(decision, "overall_status", "") == "OK" and not qualifying_domains:
        return "NONE", []
    return str(decision.primary_issue), list(decision.secondary_issues)


def _invoke_decision_builder(
    decision_builder: Callable[..., Any],
    awr_id: int,
    feature_json: dict[str, Any],
    trend_rows: list[dict[str, Any]],
    include_decision_diagnostics: bool,
) -> Any:
    kwargs = {
        "awr_id": awr_id,
        "feature_vector": {"feature_json": feature_json},
        "trend_rows": trend_rows,
        "score_result": None,
        "anomaly_signals": None,
    }
    if include_decision_diagnostics:
        parameters = signature(decision_builder).parameters
        accepts_var_kwargs = any(
            parameter.kind == parameter.VAR_KEYWORD
            for parameter in parameters.values()
        )
        if "include_diagnostics" in parameters or accepts_var_kwargs:
            kwargs["include_diagnostics"] = True
    return decision_builder(**kwargs)


def _build_validation_diagnostics(
    decision: Any,
    actual_primary_issue: str,
    actual_secondary_issues: list[str],
) -> dict[str, Any]:
    evidence = getattr(decision, "evidence", {}) or {}
    normalized_to_none = actual_primary_issue == "NONE"
    return {
        "decision_diagnostics": evidence.get("decision_diagnostics"),
        "normalized_to_none": normalized_to_none,
        "normalized_primary_issue": actual_primary_issue,
        "normalized_secondary_issues": list(actual_secondary_issues),
    }


def render_validation_cli_summary(result: ValidationHarnessResult) -> str:
    lines = [
        "=" * 56,
        "PHASE 4.5 VALIDATION SUMMARY",
        "=" * 56,
        f"Manifest Source: {result.manifest_source}",
        f"Cases: {result.case_count}",
        f"Passed: {result.passed_count}",
        f"Failed: {result.failed_count}",
    ]
    if result.failed_count:
        lines.append("")
        lines.append("MISMATCHED CASES:")
        for case in result.cases:
            if case.passed:
                continue
            lines.append(
                f"- {case.scenario_name}: expected "
                f"{case.expected_primary_issue}/{case.expected_status}, got "
                f"{case.actual_primary_issue}/{case.actual_status}"
            )
    lines.append("=" * 56)
    return "\n".join(lines)


def write_validation_json_summary(
    result: ValidationHarnessResult,
    output_path: str | Path,
) -> None:
    path = Path(output_path)
    path.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=False, default=str) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the Phase 4.5 validation harness against a local dataset."
    )
    parser.add_argument(
        "dataset_dir",
        nargs="?",
        default="data/input",
        help="Dataset directory containing AWR files and manifest files.",
    )
    parser.add_argument(
        "--manifest",
        dest="manifest_path",
        help="Optional explicit manifest path (.csv or .json).",
    )
    parser.add_argument(
        "--json-output",
        dest="json_output",
        help="Optional path to write the machine-readable validation summary.",
    )
    args = parser.parse_args(argv)

    try:
        result = run_validation_harness(
            input_dir=args.dataset_dir,
            manifest_path=args.manifest_path,
        )
    except Exception as exc:
        print(f"Validation harness failed: {exc}", file=sys.stderr)
        return 1

    print(render_validation_cli_summary(result))
    if args.json_output:
        write_validation_json_summary(result, args.json_output)
        print(f"JSON summary written to: {args.json_output}")
    return 0


def _build_scenario_artifacts(
    entries: list[ValidationManifestEntry],
    input_dir: Path,
    parser: Callable[[str | Path], Any],
    feature_vector_builder: Callable[[Any, int, int], dict[str, Any]],
) -> list[_ScenarioArtifact]:
    artifacts: list[_ScenarioArtifact] = []
    for awr_id, entry in enumerate(entries, start=1):
        file_path = input_dir / entry.file
        if not file_path.exists():
            raise FileNotFoundError(f"Manifest file does not exist: {file_path}")
        parse_result = parser(file_path)
        feature_vector = feature_vector_builder(parse_result, awr_id, awr_id)
        feature_json = _coerce_feature_json(feature_vector)
        artifacts.append(
            _ScenarioArtifact(
                awr_id=awr_id,
                entry=entry,
                parse_result=parse_result,
                feature_json=feature_json,
                trend_rows=[],
            )
        )
    return artifacts


def _populate_local_trend_rows(artifacts: list[_ScenarioArtifact]) -> None:
    history: dict[tuple[str, int | None, str], list[tuple[datetime, float]]] = {}
    for artifact in artifacts:
        current_trend_rows: list[dict[str, Any]] = []
        numeric_metrics = _numeric_feature_metrics(artifact.feature_json)
        for metric_name, metric_value in numeric_metrics.items():
            history_key = (
                artifact.entry.db_name,
                artifact.entry.dbid,
                metric_name,
            )
            metric_history = list(history.get(history_key, []))
            metric_history.append((artifact.entry.begin_time, metric_value))
            trend_features = compute_trend_features(metric_history)
            anomaly_rows = detect_anomalies(
                metric_history,
                trend_features,
                metric_name,
            )
            current_anomaly = anomaly_rows[-1]
            if current_anomaly.get("anomaly_flag") != "Y":
                history[history_key] = metric_history
                continue
            current_trend_rows.append(
                {
                    "metric_name": metric_name,
                    "metric_value_num": metric_value,
                    "anomaly_flag": current_anomaly.get("anomaly_flag"),
                    "anomaly_type": current_anomaly.get("anomaly_type"),
                    "anomaly_score": current_anomaly.get("anomaly_score"),
                }
            )
            history[history_key] = metric_history
        artifact.trend_rows = current_trend_rows


def _numeric_feature_metrics(feature_json: dict[str, Any]) -> dict[str, float]:
    numeric_metrics: dict[str, float] = {}
    for key, value in feature_json.items():
        numeric_value = _safe_float(value)
        if numeric_value is None:
            continue
        numeric_metrics[str(key)] = numeric_value
    return numeric_metrics


def _coerce_feature_json(feature_vector: dict[str, Any]) -> dict[str, Any]:
    feature_json = feature_vector.get("feature_json")
    if isinstance(feature_json, dict):
        return feature_json
    if isinstance(feature_json, str) and feature_json.strip():
        return json.loads(feature_json)
    raise ValueError("Feature vector builder did not return a usable feature_json payload.")


def _load_manifest_csv(path: Path) -> list[ValidationManifestEntry]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return _build_manifest_entries(rows)


def _load_manifest_json(path: Path) -> list[ValidationManifestEntry]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Manifest JSON must contain a list of scenario objects.")
    return _build_manifest_entries(payload)


def _build_manifest_entries(rows: list[dict[str, Any]]) -> list[ValidationManifestEntry]:
    entries = [
        ValidationManifestEntry(
            begin_time=_parse_manifest_begin_time(row.get("begin_time")),
            db_name=str(row.get("db_name") or "").strip(),
            dbid=_safe_int(row.get("dbid")),
            expected_primary_issue=_normalize_manifest_issue(
                row.get("expected_primary_issue")
            ),
            expected_secondary_issues=_split_expected_secondary_issues(
                row.get("expected_secondary_issues")
            ),
            expected_status=str(row.get("expected_status") or "").strip().upper(),
            file=str(row.get("file") or row.get("filename") or "").strip(),
            notes=str(row.get("notes") or "").strip(),
            scenario_name=str(row.get("scenario_name") or "").strip(),
            manifest_order=index,
        )
        for index, row in enumerate(rows)
    ]
    return sorted(
        entries,
        key=lambda entry: (
            entry.begin_time is None,
            entry.begin_time or datetime.max,
            entry.manifest_order,
            entry.scenario_name,
        ),
    )


def _parse_manifest_begin_time(value: Any) -> datetime | None:
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    return datetime.strptime(raw_value, "%Y-%m-%d %H:%M:%S")


def _split_expected_secondary_issues(value: Any) -> list[str]:
    raw_value = str(value or "").strip()
    if not raw_value:
        return []
    return [item.strip().upper() for item in raw_value.split(",") if item.strip()]


def _normalize_manifest_issue(value: Any) -> str:
    normalized = str(value or "").strip().upper()
    return normalized or "NONE"


def _load_feature_vector_builder() -> Callable[[Any, int, int], dict[str, Any]]:
    try:
        from src.ingest.awr_adb_loader import build_feature_vector_record
    except ModuleNotFoundError as exc:
        if exc.name != "dotenv":
            raise
        sys.modules.setdefault(
            "dotenv",
            types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None),
        )
        from src.ingest.awr_adb_loader import build_feature_vector_record
    return build_feature_vector_record


def _safe_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").strip())
        except ValueError:
            return None
    return None


def _safe_int(value: Any) -> int | None:
    numeric_value = _safe_float(value)
    if numeric_value is None:
        return None
    return int(numeric_value)


if __name__ == "__main__":
    raise SystemExit(main())
