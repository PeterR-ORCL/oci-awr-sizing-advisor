from __future__ import annotations

import ast
import importlib
import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
CONTROLLER_DOC = DOCS / "phase7am_reanalysis_execution_controller.md"
COMPARISON_DOC = DOCS / "phase7am_awr_report_comparison_engine.md"
README = DOCS / "README.md"
MODULE_PATH = ROOT / "src" / "learning" / "screen3_reanalysis_controller.py"

RUNTIME_IMPORT_PATHS = (
    "scripts/run_analysis.py",
    "src/parser",
    "src/parsing",
    "src/scoring",
    "src/decision",
    "src/recommendation",
    "src/recommendations",
    "src/analysis/decision_engine.py",
    "src/analysis/recommendation_engine.py",
    "src/analysis/scoring_adapter.py",
)

FORBIDDEN_BEHAVIOR_FILES = (
    "src/reporting/html_dashboard.py",
    "src/reporting/ai_display_metadata.py",
    "scripts/awr_memory_cli.py",
    "scripts/run_analysis.py",
)

FORBIDDEN_IMPORT_PREFIXES = (
    "subprocess",
    "oracledb",
    "cx_Oracle",
    "sqlite3",
    "oci",
    "requests",
    "socket",
    "urllib",
    "http.client",
    "httpx",
    "boto3",
    "botocore",
    "src.reporting",
    "src.parser",
    "src.parsing",
    "src.scoring",
    "src.decision",
    "src.recommendation",
    "src.recommendations",
    "src.analysis",
    "src.memory",
    "scripts.awr_memory_cli",
    "scripts.run_analysis",
    "oracle_agent_memory",
)

FORBIDDEN_FUNCTION_NAMES = (
    "execute_analysis",
    "run_analysis",
    "call_object_storage",
    "read_file",
    "open_file",
    "query_database",
    "subprocess",
    "requests",
    "regenerate_dashboard",
    "mutate_phase4i",
    "auto_execute",
    "autonomous_execute",
)

FORBIDDEN_SOURCE_SNIPPETS = (
    "execute_analysis",
    "call_object_storage",
    "read_file",
    "open_file",
    "query_database",
    "subprocess",
    "requests",
    "regenerate_dashboard(",
    "mutate_phase4i",
    "auto_execute",
    "autonomous_execute",
    "run_analysis(",
    "run_analysis.py",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def lower_text(path: Path) -> str:
    return read_text(path).lower()


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def function_names(path: Path) -> set[str]:
    tree = ast.parse(read_text(path), filename=str(path))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def python_files(paths: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for relative_path in paths:
        path = ROOT / relative_path
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(child for child in path.rglob("*.py") if child.is_file()))
    return files


class Phase7AMReanalysisExecutionControllerTests(unittest.TestCase):
    @staticmethod
    def module():
        return importlib.import_module("src.learning.screen3_reanalysis_controller")

    @staticmethod
    def request_module():
        return importlib.import_module("src.learning.screen3_reanalysis_request")

    @staticmethod
    def source_module():
        return importlib.import_module("src.learning.screen3_source_selection")

    def make_source_selection_dict(self, source_mode: str = "local_file"):
        source_module = self.source_module()
        if source_mode == "object_storage":
            source_ref = source_module.ObjectStorageSourceReference(
                object_source_id=source_module.create_object_source_id(
                    namespace="namespace",
                    bucket="bucket",
                    object_name="awr.html",
                    region="us-ashburn-1",
                ),
                namespace="namespace",
                bucket="bucket",
                object_name="awr.html",
                region="us-ashburn-1",
                configured_hint=True,
            )
            selection = source_module.SourceSelection(
                source_selection_id=source_module.create_source_selection_id(
                    "object_storage",
                    "unit-test",
                ),
                source_mode="object_storage",
                object_storage_source=source_ref,
                validation_status="VALID_METADATA_ONLY",
            )
        else:
            source_ref = source_module.LocalSourceReference(
                local_source_id=source_module.create_local_source_id(
                    file_name="awr-1.html",
                ),
                file_name="awr-1.html",
                expected_file_type="html",
            )
            selection = source_module.SourceSelection(
                source_selection_id=source_module.create_source_selection_id(
                    source_mode,
                    "unit-test",
                ),
                source_mode=source_mode,
                local_source=source_ref,
                validation_status="VALID_METADATA_ONLY",
            )
        return source_module.source_selection_to_dict(selection)

    def make_request(
        self,
        requested_action: str = "analyze_selection",
        source_mode: str = "local_file",
        execution_mode: str = "local_backend_execution",
        **overrides,
    ):
        request_module = self.request_module()
        state = request_module.Screen3SelectedState(
            selected_state_id=request_module.create_selected_state_id(
                selected_run="RUN-1",
                selected_snapshot="SNAP-1",
            ),
            selected_run="RUN-1",
            selected_snapshot="SNAP-1",
            selected_source_mode=source_mode,
            selected_execution_mode=execution_mode,
            selected_local_source_reference=(
                "LOCAL-SOURCE-AWR-1" if source_mode != "object_storage" else None
            ),
            selected_object_storage_reference=(
                "OBJECT-SOURCE-AWR-1" if source_mode == "object_storage" else None
            ),
            selected_issue_domain="CPU",
        )
        values = {
            "request_id": request_module.create_reanalysis_request_id(
                requested_action,
                state.selected_state_id,
                execution_mode,
            ),
            "requested_action": requested_action,
            "selected_state": state,
            "source_selection": self.make_source_selection_dict(source_mode),
            "backend_execution_request": {"validation_status": "VALID_METADATA_ONLY"},
            "actor_audit_context": {"actor_id": "ACTOR-LOCAL-JANE-REVIEWER"},
            "execution_mode": execution_mode,
            "notes": "unit test",
        }
        values.update(overrides)
        return request_module.BackendReAnalysisRequest(**values)

    def comparison_inputs(self):
        return [
            {
                "run_id": "RUN-BASE",
                "awr_id": "AWR-BASE",
                "database_name": "PROD",
                "snapshot_label": "before",
                "platform_target": {"platform": "Exadata", "target": "DB1"},
                "source_options": {"rac": True},
                "scores": {"overall": 70, "io": 40},
                "domain_scores": {"CPU": 55},
                "waits": {"db_file_sequential_read": 120},
                "wait_events": {"log_file_sync": 30},
                "sql_concentration": {"top_sql_pct": 35},
                "top_sql_concentration": {"SQL1": 20},
                "trends": {"io_trend": "rising", "cpu_delta": 2},
                "anomalies": {"io_anomaly": False},
                "topology": {"instances": 2},
                "data_availability": {"ash": True},
                "missing_metrics": [],
            },
            {
                "run_id": "RUN-TARGET",
                "awr_id": "AWR-TARGET",
                "database_name": "PROD",
                "snapshot_label": "after",
                "platform_target": {"platform": "Exadata", "target": "DB2"},
                "source_options": {"rac": False},
                "scores": {"overall": 82},
                "domain_scores": {"CPU": 45},
                "waits": {"db_file_sequential_read": 150},
                "wait_events": {"log_file_sync": 15},
                "sql_concentration": {"top_sql_pct": 55},
                "top_sql_concentration": {"SQL1": 25},
                "trends": {"io_trend": "falling", "cpu_delta": 5},
                "anomalies": {"io_anomaly": True},
                "topology": {"instances": 1},
                "data_availability": {"ash": False},
                "missing_metrics": ["scores.io"],
            },
        ]

    def test_module_import_safety(self) -> None:
        before_environment = dict(os.environ)
        module = self.module()
        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(module, "ReAnalysisExecutionPlan"))
        self.assertTrue(hasattr(module, "ReAnalysisExecutionResult"))
        self.assertTrue(hasattr(module, "AWRReportComparisonArtifact"))

        imports = imported_modules(MODULE_PATH)
        for forbidden in FORBIDDEN_IMPORT_PREFIXES:
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        imported == forbidden or imported.startswith(f"{forbidden}.")
                        for imported in imports
                    )
                )

    def test_docs_exist(self) -> None:
        self.assertTrue(CONTROLLER_DOC.is_file(), CONTROLLER_DOC)
        self.assertTrue(COMPARISON_DOC.is_file(), COMPARISON_DOC)

    def test_docs_contain_required_boundary_phrases(self) -> None:
        text = lower_text(CONTROLLER_DOC) + "\n" + lower_text(COMPARISON_DOC)
        for phrase in (
            "controller does not execute analysis",
            "controller does not call run_analysis.py",
            "controller does not read files",
            "controller does not call object storage",
            "controller does not query db",
            "controller does not regenerate dashboards",
            "controller does not mutate phase 4i",
            "comparison is based only on supplied in-memory payloads",
            "missing metric handling remains future 7ao.1 / 7aq.1",
            "sizing/tco comparison belongs to phase 8",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_execution_plan_metadata_flags(self) -> None:
        module = self.module()
        request = self.make_request()
        plan = module.build_reanalysis_execution_plan(request)
        self.assertEqual(
            module.create_reanalysis_execution_plan_id(
                request.request_id,
                request.requested_action,
            ),
            plan.execution_plan_id,
        )
        self.assertFalse(plan.execution_performed)
        self.assertFalse(plan.run_analysis_called)
        self.assertFalse(plan.object_storage_called)
        self.assertFalse(plan.local_file_read_performed)
        self.assertFalse(plan.db_lookup_performed)
        self.assertFalse(plan.dashboard_regenerated)
        self.assertFalse(plan.output_written)
        self.assertTrue(plan.deterministic_default)
        self.assertTrue(plan.phase4i_contract_required)

    def test_execution_result_action_behaviors(self) -> None:
        module = self.module()
        analyze_result = module.evaluate_reanalysis_execution(
            self.make_request("analyze_selection")
        )
        self.assertEqual("PLANNED", analyze_result.execution_status)

        rerun_result = module.evaluate_reanalysis_execution(
            self.make_request("rerun_analysis")
        )
        self.assertEqual("PLANNED", rerun_result.execution_status)

        object_result = module.evaluate_reanalysis_execution(
            self.make_request(
                "load_from_object_storage",
                source_mode="object_storage",
            )
        )
        self.assertEqual("BLOCKED", object_result.execution_status)

        comparison_missing = module.evaluate_reanalysis_execution(
            self.make_request("build_comparison"),
            comparison_inputs=None,
        )
        self.assertEqual("BLOCKED", comparison_missing.execution_status)

        comparison_result = module.evaluate_reanalysis_execution(
            self.make_request("build_comparison"),
            comparison_inputs=self.comparison_inputs(),
            created_by="ACTOR-LOCAL-JANE-REVIEWER",
        )
        self.assertEqual(
            "COMPARISON_BUILT_IN_MEMORY",
            comparison_result.execution_status,
        )
        self.assertIsNotNone(comparison_result.comparison_artifact)

        for result in (
            analyze_result,
            rerun_result,
            object_result,
            comparison_missing,
            comparison_result,
        ):
            with self.subTest(status=result.execution_status):
                self.assertFalse(result.runtime_execution_performed)
                self.assertFalse(result.phase4i_mutated)
                self.assertFalse(result.dashboard_regenerated)
                self.assertFalse(result.output_written)
                self.assertTrue(result.deterministic_runtime_authoritative)

    def test_comparison_engine_dimensions(self) -> None:
        module = self.module()
        artifact = module.build_awr_report_comparison(
            self.comparison_inputs(),
            comparison_name="before-after",
            created_by="ACTOR-LOCAL-JANE-REVIEWER",
        )
        self.assertEqual(2, artifact.compared_report_count)
        self.assertEqual(["RUN-BASE", "RUN-TARGET"], artifact.compared_run_ids)
        self.assertEqual(["AWR-BASE", "AWR-TARGET"], artifact.compared_awr_ids)
        self.assertEqual("RUN-BASE", artifact.baseline_reference)
        self.assertEqual(["RUN-TARGET"], artifact.target_references)
        self.assertIn("scores.overall", artifact.score_differences)
        self.assertIn("waits.db_file_sequential_read", artifact.wait_event_differences)
        self.assertIn("sql_concentration.top_sql_pct", artifact.sql_concentration_differences)
        self.assertIn("trends.io_trend", artifact.trend_differences)
        self.assertIn("anomalies.io_anomaly", artifact.anomaly_differences)
        self.assertIn("topology.instances", artifact.topology_differences)
        self.assertIn("platform_target.target", artifact.platform_target_differences)
        self.assertIn("platform/target/source option differences", artifact.likely_difference_drivers)
        self.assertFalse(artifact.artifact_written)
        self.assertFalse(artifact.dashboard_generated)
        self.assertFalse(artifact.phase4i_mutated)

        with self.assertRaises(module.Screen3ReAnalysisControllerError):
            module.build_awr_report_comparison([self.comparison_inputs()[0]])

    def test_difference_classification_and_limitations(self) -> None:
        module = self.module()
        artifact = module.build_awr_report_comparison(self.comparison_inputs())
        missing_values = artifact.data_availability_differences["missing_values"]
        self.assertTrue(
            any(item["field"] == "scores.io" for item in missing_values),
            missing_values,
        )
        self.assertIn(
            "data availability differences",
            artifact.likely_difference_drivers,
        )
        self.assertTrue(
            any("missing comparison fields" in item for item in artifact.comparison_limitations),
            artifact.comparison_limitations,
        )
        self.assertIn("Compared 2 supplied report summaries", artifact.difference_summary)

    def test_safety_flag_validation_rejects_mutation(self) -> None:
        module = self.module()
        request = self.make_request()
        plan_values = module.reanalysis_execution_plan_to_dict(
            module.build_reanalysis_execution_plan(request)
        )
        for field_name in (
            "execution_performed",
            "run_analysis_called",
            "object_storage_called",
            "local_file_read_performed",
            "db_lookup_performed",
            "dashboard_regenerated",
            "output_written",
        ):
            values = dict(plan_values)
            values[field_name] = True
            with self.subTest(plan_field=field_name):
                with self.assertRaises(module.Screen3ReAnalysisControllerError):
                    module.reanalysis_execution_plan_from_dict(values)

        result_values = module.reanalysis_execution_result_to_dict(
            module.evaluate_reanalysis_execution(request)
        )
        for field_name in (
            "runtime_execution_performed",
            "phase4i_mutated",
            "dashboard_regenerated",
            "output_written",
        ):
            values = dict(result_values)
            values[field_name] = True
            with self.subTest(result_field=field_name):
                with self.assertRaises(module.Screen3ReAnalysisControllerError):
                    module.reanalysis_execution_result_from_dict(values)

        artifact_values = module.awr_report_comparison_artifact_to_dict(
            module.build_awr_report_comparison(self.comparison_inputs())
        )
        for field_name in ("artifact_written", "dashboard_generated", "phase4i_mutated"):
            values = dict(artifact_values)
            values[field_name] = True
            with self.subTest(artifact_field=field_name):
                with self.assertRaises(module.Screen3ReAnalysisControllerError):
                    module.awr_report_comparison_artifact_from_dict(values)

    def test_serialization_round_trips(self) -> None:
        module = self.module()
        request = self.make_request("build_comparison")
        plan = module.build_reanalysis_execution_plan(request)
        self.assertEqual(
            plan,
            module.reanalysis_execution_plan_from_dict(
                module.reanalysis_execution_plan_to_dict(plan)
            ),
        )

        artifact = module.build_awr_report_comparison(self.comparison_inputs())
        self.assertEqual(
            artifact,
            module.awr_report_comparison_artifact_from_dict(
                module.awr_report_comparison_artifact_to_dict(artifact)
            ),
        )

        result = module.evaluate_reanalysis_execution(
            request,
            comparison_inputs=self.comparison_inputs(),
        )
        self.assertEqual(
            result,
            module.reanalysis_execution_result_from_dict(
                module.reanalysis_execution_result_to_dict(result)
            ),
        )

    def test_deterministic_ids(self) -> None:
        module = self.module()
        request_id = "REQ-1"
        self.assertEqual(
            module.create_reanalysis_execution_plan_id(request_id, "analyze_selection"),
            module.create_reanalysis_execution_plan_id(request_id, "analyze_selection"),
        )
        self.assertEqual(
            module.create_reanalysis_execution_result_id(request_id, "rerun_analysis"),
            module.create_reanalysis_execution_result_id(request_id, "rerun_analysis"),
        )
        self.assertEqual(
            module.create_awr_report_comparison_id("Compare", ["A", "B"]),
            module.create_awr_report_comparison_id("Compare", ["A", "B"]),
        )

    def test_no_execution_functions(self) -> None:
        source = lower_text(MODULE_PATH)
        functions = function_names(MODULE_PATH)
        for term in FORBIDDEN_FUNCTION_NAMES:
            with self.subTest(term=term):
                self.assertNotIn(term, functions)
        for snippet in FORBIDDEN_SOURCE_SNIPPETS:
            with self.subTest(snippet=snippet):
                self.assertNotIn(snippet, source)

    def test_runtime_import_isolation(self) -> None:
        run_analysis_imports = imported_modules(ROOT / "scripts" / "run_analysis.py")
        for module_name in (
            "src.learning.screen3_reanalysis_controller",
            "learning.screen3_reanalysis_controller",
            "screen3_reanalysis_controller",
        ):
            with self.subTest(module_name=module_name):
                self.assertNotIn(module_name, run_analysis_imports)

        for path in python_files(RUNTIME_IMPORT_PATHS):
            imports = imported_modules(path)
            source = read_text(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.screen3_reanalysis_controller", imports)
                self.assertNotIn("learning.screen3_reanalysis_controller", imports)
                self.assertNotIn("screen3_reanalysis_controller", imports)
                self.assertNotIn("screen3_reanalysis_controller", source)

    def test_behavior_files_are_not_modified_by_phase7am(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not available")
        if not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")

        completed = subprocess.run(
            ("git", "diff", "--name-only", "--", *FORBIDDEN_BEHAVIOR_FILES),
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            self.skipTest(completed.stderr.strip() or "git diff unavailable")

        changed = {
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        }
        self.assertFalse(changed, f"behavior files modified: {sorted(changed)}")

    def test_readme_links_new_docs(self) -> None:
        text = read_text(README)
        for title, filename in (
            (
                "Phase 7AM Backend Re-Analysis Execution Controller",
                "phase7am_reanalysis_execution_controller.md",
            ),
            (
                "Phase 7AM.1 AWR / Report Comparison Engine",
                "phase7am_awr_report_comparison_engine.md",
            ),
        ):
            with self.subTest(title=title):
                self.assertIn(title, text)
                self.assertIn(filename, text)


if __name__ == "__main__":
    unittest.main()
