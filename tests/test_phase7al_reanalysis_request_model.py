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
MODEL_DOC = DOCS / "phase7al_reanalysis_request_model.md"
VALIDATION_DOC = DOCS / "phase7al_reanalysis_request_validation.md"
README = DOCS / "README.md"
MODULE_PATH = ROOT / "src" / "learning" / "screen3_reanalysis_request.py"

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
    "pathlib",
    "os",
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
    "execute_reanalysis",
    "run_analysis",
    "call_object_storage",
    "read_local_file",
    "query_database",
    "call_backend",
    "auto_execute",
    "autonomous_execute",
)

FORBIDDEN_SOURCE_SNIPPETS = (
    "execute_reanalysis",
    "call_object_storage",
    "read_local_file",
    "query_database",
    "call_backend",
    "subprocess",
    "requests",
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


class Phase7ALReanalysisRequestModelTests(unittest.TestCase):
    @staticmethod
    def module():
        return importlib.import_module("src.learning.screen3_reanalysis_request")

    @staticmethod
    def source_module():
        return importlib.import_module("src.learning.screen3_source_selection")

    def make_selected_state(self, **overrides):
        module = self.module()
        values = {
            "selected_state_id": module.create_selected_state_id(
                selected_run="RUN-1",
                selected_snapshot="SNAP-1",
            ),
            "selected_run": "RUN-1",
            "selected_snapshot": "SNAP-1",
            "selected_issue_domain": "CPU",
            "selected_source_mode": "local_file",
            "selected_execution_mode": "local_backend_execution",
            "selected_local_source_reference": "LOCAL-SOURCE-AWR-1",
            "notes": "unit test",
        }
        values.update(overrides)
        return module.Screen3SelectedState(**values)

    def make_source_selection_dict(self, validation_status: str = "VALID_METADATA_ONLY"):
        source_module = self.source_module()
        local_ref = source_module.LocalSourceReference(
            local_source_id=source_module.create_local_source_id(file_name="awr-1.html"),
            file_name="awr-1.html",
            expected_file_type="html",
            exists_hint=False,
        )
        selection = source_module.SourceSelection(
            source_selection_id=source_module.create_source_selection_id(
                "local_file",
                "unit-test",
            ),
            source_mode="local_file",
            source_label="unit-test",
            local_source=local_ref,
            validation_status=validation_status,
        )
        return source_module.source_selection_to_dict(selection)

    def make_request(self, **overrides):
        module = self.module()
        selected_state = overrides.pop("selected_state", self.make_selected_state())
        values = {
            "request_id": module.create_reanalysis_request_id(
                "analyze_selection",
                selected_state.selected_state_id,
                "local_backend_execution",
            ),
            "requested_action": "analyze_selection",
            "selected_state": selected_state,
            "source_selection": self.make_source_selection_dict(),
            "backend_execution_request": {"validation_status": "VALID_METADATA_ONLY"},
            "actor_audit_context": {"actor_id": "ACTOR-LOCAL-JANE-REVIEWER"},
            "execution_mode": "local_backend_execution",
            "adaptive_runtime_requested": False,
            "deterministic_default": True,
            "requires_validation": True,
            "requires_actor": True,
            "requires_source_validation": True,
            "requires_backend_execution_validation": True,
            "phase4i_contract_required": True,
            "created_at": None,
            "notes": "unit test",
        }
        values.update(overrides)
        return module.BackendReAnalysisRequest(**values)

    def test_module_import_safety(self) -> None:
        before_environment = dict(os.environ)
        module = self.module()
        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(module, "Screen3SelectedState"))
        self.assertTrue(hasattr(module, "BackendReAnalysisRequest"))
        self.assertTrue(hasattr(module, "BackendReAnalysisRequestValidation"))

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
        self.assertTrue(MODEL_DOC.is_file(), MODEL_DOC)
        self.assertTrue(VALIDATION_DOC.is_file(), VALIDATION_DOC)

    def test_docs_contain_required_boundary_phrases(self) -> None:
        text = lower_text(MODEL_DOC) + "\n" + lower_text(VALIDATION_DOC)
        for phrase in (
            "request model is not execution",
            "can_execute=false in phase 7al",
            "execution_blocked=true in phase 7al",
            "run_analysis.py is not called",
            "object storage is not called",
            "local files are not read",
            "db lookup is not performed",
            "awr/report comparison is future 7am.1",
            "missing metric handling is future 7ao.1 / 7aq.1",
            "phase 8 sizing/tco is not implemented",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_selected_state_validation(self) -> None:
        module = self.module()
        state = module.default_screen3_selected_state(notes="placeholder")
        self.assertEqual("none", state.selected_source_mode)
        self.assertEqual("static_read_only", state.selected_execution_mode)
        self.assertEqual(
            module.create_selected_state_id(),
            module.create_selected_state_id(),
        )

        for source_mode in module.SCREEN3_REANALYSIS_SOURCE_MODES:
            with self.subTest(source_mode=source_mode):
                source_state = self.make_selected_state(selected_source_mode=source_mode)
                self.assertEqual(source_mode, source_state.selected_source_mode)

        for execution_mode in module.SCREEN3_REANALYSIS_EXECUTION_MODES:
            with self.subTest(execution_mode=execution_mode):
                execution_state = self.make_selected_state(
                    selected_execution_mode=execution_mode,
                )
                self.assertEqual(execution_mode, execution_state.selected_execution_mode)

        with self.assertRaises(module.Screen3ReAnalysisRequestError):
            self.make_selected_state(selected_source_mode="remote_bucket")
        with self.assertRaises(module.Screen3ReAnalysisRequestError):
            self.make_selected_state(selected_execution_mode="shell")

        for domain in ("CPU", "IO", "MEMORY", "COMMIT", "RAC", "ADG", "cpu"):
            with self.subTest(domain=domain):
                self.assertEqual(
                    domain,
                    self.make_selected_state(selected_issue_domain=domain).selected_issue_domain,
                )
        with self.assertRaises(module.Screen3ReAnalysisRequestError):
            self.make_selected_state(selected_issue_domain="NETWORK")

    def test_request_validation_rules(self) -> None:
        module = self.module()
        request = self.make_request()
        self.assertIs(module.validate_backend_reanalysis_request(request), request)

        with self.assertRaises(module.Screen3ReAnalysisRequestError):
            self.make_request(requested_action="unsupported_action")
        with self.assertRaises(module.Screen3ReAnalysisRequestError):
            self.make_request(deterministic_default=False)
        with self.assertRaises(module.Screen3ReAnalysisRequestError):
            self.make_request(requires_validation=False)
        with self.assertRaises(module.Screen3ReAnalysisRequestError):
            self.make_request(phase4i_contract_required=False)

    def test_evaluate_backend_reanalysis_request(self) -> None:
        module = self.module()

        missing_actor = module.evaluate_backend_reanalysis_request(
            self.make_request(actor_audit_context=None)
        )
        self.assertEqual("NEEDS_ACTOR", missing_actor.validation_status)

        missing_source = module.evaluate_backend_reanalysis_request(
            self.make_request(source_selection=None)
        )
        self.assertEqual("NEEDS_SOURCE_SELECTION", missing_source.validation_status)

        missing_source_validation = module.evaluate_backend_reanalysis_request(
            self.make_request(source_selection={"source_mode": "local_file"})
        )
        self.assertEqual(
            "NEEDS_SOURCE_VALIDATION",
            missing_source_validation.validation_status,
        )

        missing_backend_validation = module.evaluate_backend_reanalysis_request(
            self.make_request(backend_execution_request=None)
        )
        self.assertEqual(
            "NEEDS_BACKEND_EXECUTION_VALIDATION",
            missing_backend_validation.validation_status,
        )

        otherwise_valid = module.evaluate_backend_reanalysis_request(self.make_request())
        self.assertEqual(
            "EXECUTION_NOT_ALLOWED_IN_THIS_PHASE",
            otherwise_valid.validation_status,
        )
        self.assertTrue(otherwise_valid.valid)

        for result in (
            missing_actor,
            missing_source,
            missing_source_validation,
            missing_backend_validation,
            otherwise_valid,
        ):
            with self.subTest(status=result.validation_status):
                self.assertFalse(result.can_execute)
                self.assertTrue(result.execution_blocked)
                self.assertFalse(result.runtime_execution_performed)
                self.assertFalse(result.run_analysis_called)
                self.assertFalse(result.object_storage_called)
                self.assertFalse(result.local_file_read_performed)
                self.assertFalse(result.db_lookup_performed)

    def test_validation_result_safety_flags(self) -> None:
        module = self.module()
        base = {
            "validation_id": "SCREEN3-REANALYSIS-VALIDATION-1",
            "request_id": "SCREEN3-REANALYSIS-REQUEST-1",
            "valid": True,
            "validation_status": "EXECUTION_NOT_ALLOWED_IN_THIS_PHASE",
            "requested_action": "analyze_selection",
            "source_mode": "local_file",
            "execution_mode": "local_backend_execution",
            "actor_present": True,
            "source_validation_present": True,
            "backend_execution_validation_present": True,
            "can_execute": False,
            "execution_blocked": True,
            "denied_reasons": ["execution is not allowed in Phase 7AL"],
            "warnings": [],
            "required_next_steps": [],
            "phase4i_contract_required": True,
            "deterministic_default": True,
            "adaptive_runtime_requested": False,
            "runtime_execution_performed": False,
            "run_analysis_called": False,
            "object_storage_called": False,
            "local_file_read_performed": False,
            "db_lookup_performed": False,
        }
        for field_name, bad_value in (
            ("can_execute", True),
            ("execution_blocked", False),
            ("runtime_execution_performed", True),
            ("run_analysis_called", True),
            ("object_storage_called", True),
            ("local_file_read_performed", True),
            ("db_lookup_performed", True),
            ("phase4i_contract_required", False),
            ("deterministic_default", False),
        ):
            values = dict(base)
            values[field_name] = bad_value
            with self.subTest(field_name=field_name):
                with self.assertRaises(module.Screen3ReAnalysisRequestError):
                    module.BackendReAnalysisRequestValidation(**values)

    def test_serialization_round_trips(self) -> None:
        module = self.module()
        state = self.make_selected_state()
        state_round_trip = module.screen3_selected_state_from_dict(
            module.screen3_selected_state_to_dict(state)
        )
        self.assertEqual(state, state_round_trip)

        request = self.make_request(selected_state=state)
        request_round_trip = module.backend_reanalysis_request_from_dict(
            module.backend_reanalysis_request_to_dict(request)
        )
        self.assertEqual(request, request_round_trip)

        validation = module.evaluate_backend_reanalysis_request(request)
        validation_round_trip = module.backend_reanalysis_request_validation_from_dict(
            module.backend_reanalysis_request_validation_to_dict(validation)
        )
        self.assertEqual(validation, validation_round_trip)

    def test_deterministic_ids(self) -> None:
        module = self.module()
        first_state_id = module.create_selected_state_id(
            selected_run="RUN-1",
            selected_snapshot="SNAP-1",
        )
        second_state_id = module.create_selected_state_id(
            selected_run="RUN-1",
            selected_snapshot="SNAP-1",
        )
        self.assertEqual(first_state_id, second_state_id)
        self.assertEqual("SCREEN3-SELECTED-STATE-RUN-1-SNAP-1", first_state_id)

        first_request_id = module.create_reanalysis_request_id(
            "analyze_selection",
            first_state_id,
            "local_backend_execution",
        )
        second_request_id = module.create_reanalysis_request_id(
            "analyze_selection",
            first_state_id,
            "local_backend_execution",
        )
        self.assertEqual(first_request_id, second_request_id)
        self.assertTrue(
            first_request_id.startswith(
                "SCREEN3-REANALYSIS-REQUEST-ANALYZE-SELECTION-"
            )
        )

        self.assertEqual(
            module.create_reanalysis_validation_id(first_request_id),
            module.create_reanalysis_validation_id(first_request_id),
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
            "src.learning.screen3_reanalysis_request",
            "learning.screen3_reanalysis_request",
            "screen3_reanalysis_request",
        ):
            with self.subTest(module_name=module_name):
                self.assertNotIn(module_name, run_analysis_imports)

        for path in python_files(RUNTIME_IMPORT_PATHS):
            imports = imported_modules(path)
            source = read_text(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.screen3_reanalysis_request", imports)
                self.assertNotIn("learning.screen3_reanalysis_request", imports)
                self.assertNotIn("screen3_reanalysis_request", imports)
                self.assertNotIn("screen3_reanalysis_request", source)

    def test_behavior_files_are_not_modified_by_phase7al(self) -> None:
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
                "Phase 7AL Backend Re-Analysis Request Model",
                "phase7al_reanalysis_request_model.md",
            ),
            (
                "Phase 7AL Re-Analysis Request Validation",
                "phase7al_reanalysis_request_validation.md",
            ),
        ):
            with self.subTest(title=title):
                self.assertIn(title, text)
                self.assertIn(filename, text)


if __name__ == "__main__":
    unittest.main()
