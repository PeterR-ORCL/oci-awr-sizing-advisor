from __future__ import annotations

import ast
import importlib
import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
CONTROL_DOC = DOCS / "phase7av_source_intake_control_model.md"
VALIDATION_DOC = DOCS / "phase7av_source_intake_validation.md"
MODULE_PATH = ROOT / "src" / "learning" / "screen1_source_intake.py"

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
    "read_file",
    "open_file",
    "call_object_storage",
    "list_bucket",
    "download_object",
    "query_database",
    "invoke_parser",
    "run_analysis",
    "execute_intake",
    "auto_execute",
    "autonomous_execute",
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def lower_text(path: Path) -> str:
    return read_text(path).lower()


def python_files(paths: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for relative_path in paths:
        path = ROOT / relative_path
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(child for child in path.rglob("*.py") if child.is_file()))
    return files


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


class Phase7AVSourceIntakeControlModelTests(unittest.TestCase):
    @staticmethod
    def module():
        return importlib.import_module("src.learning.screen1_source_intake")

    def make_request(self, **overrides):
        module = self.module()
        values = {
            "intake_request_id": module.create_source_intake_request_id(
                "local_file",
                "request_source_intake",
                "awr-one",
            ),
            "source_mode": "local_file",
            "source_reference": {"file_name": "awr.html", "available_hint": True},
            "requested_action": "request_source_intake",
            "actor_id": "ACTOR-LOCAL-REVIEWER",
            "backend_execution_request": {
                "request_id": "DASHBOARD-BACKEND-REQUEST-SCREEN1",
                "validation_status": "VALID",
            },
            "expected_file_type": "html",
            "target_screen": "screen1",
            "source_label": "awr-one",
            "notes": "metadata only",
        }
        values.update(overrides)
        return module.SourceIntakeRequest(**values)

    def test_module_import_safety(self) -> None:
        before_environment = dict(os.environ)
        module = self.module()
        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(module, "SourceIntakeRequest"))
        self.assertTrue(hasattr(module, "SourceIntakeValidation"))
        self.assertTrue(hasattr(module, "SourceIntakePreview"))

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
        self.assertTrue(CONTROL_DOC.is_file(), CONTROL_DOC)
        self.assertTrue(VALIDATION_DOC.is_file(), VALIDATION_DOC)

    def test_docs_contain_required_boundary_phrases(self) -> None:
        text = lower_text(CONTROL_DOC) + "\n" + lower_text(VALIDATION_DOC)
        for phrase in (
            "source intake is not execution",
            "no files are read",
            "no object storage calls are made",
            "no db lookup is made",
            "parser is not invoked",
            "run_analysis.py is not called",
            "can_intake=false in 7av",
            "intake_blocked=true in 7av",
            "future_em_extract is placeholder only",
            "em extract implementation belongs to phase 8",
            "phase 8 sizing/tco is not implemented",
            "validation is not intake",
            "no file read is made",
            "no object storage call is made",
            "no parser invocation occurs",
            "invalid requests fail safely",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_supported_source_modes(self) -> None:
        module = self.module()
        self.assertEqual(
            module.SCREEN1_SOURCE_MODES,
            (
                "none",
                "local_staged",
                "local_file",
                "existing_run",
                "object_storage",
                "future_upload",
                "future_em_extract",
            ),
        )
        for source_mode in module.SCREEN1_SOURCE_MODES:
            with self.subTest(source_mode=source_mode):
                source_id = module.create_source_intake_request_id(
                    source_mode,
                    "preview_source_intake",
                    "label",
                )
                self.assertTrue(
                    source_id.startswith("SCREEN1-SOURCE-INTAKE-REQUEST-")
                )
        with self.assertRaises(module.Screen1SourceIntakeError):
            module.create_source_intake_request_id(
                "unsupported",
                "preview_source_intake",
            )

    def test_supported_intake_actions(self) -> None:
        module = self.module()
        self.assertEqual(
            module.SOURCE_INTAKE_ACTIONS,
            (
                "validate_source",
                "request_source_intake",
                "preview_source_intake",
                "prepare_for_reanalysis",
                "prepare_for_parser_review",
                "prepare_for_existing_run_review",
                "prepare_for_object_storage_load",
                "prepare_for_future_em_extract",
            ),
        )
        for action in module.SOURCE_INTAKE_ACTIONS:
            with self.subTest(action=action):
                request_id = module.create_source_intake_request_id(
                    "none",
                    action,
                    "label",
                )
                self.assertIn(action.upper().replace("_", "-"), request_id)
        with self.assertRaises(module.Screen1SourceIntakeError):
            module.create_source_intake_request_id("none", "unsupported")

    def test_default_request_is_blocked_metadata_only(self) -> None:
        module = self.module()
        request = module.default_source_intake_request(notes="unit test")
        self.assertEqual(request.source_mode, "none")
        self.assertTrue(request.dry_run)
        self.assertFalse(request.intake_performed)

        validation = module.evaluate_source_intake_request(request)
        self.assertFalse(validation.can_intake)
        self.assertTrue(validation.intake_blocked)
        self.assertFalse(validation.file_read_performed)
        self.assertFalse(validation.object_storage_called)
        self.assertFalse(validation.db_lookup_performed)
        self.assertFalse(validation.parser_invoked)
        self.assertFalse(validation.run_analysis_called)

    def test_request_validation_rejects_unsafe_flags(self) -> None:
        module = self.module()
        unsafe_values = {
            "dry_run": False,
            "intake_performed": True,
            "file_read_performed": True,
            "object_storage_called": True,
            "db_lookup_performed": True,
            "parser_invoked": True,
            "run_analysis_called": True,
        }
        for field_name, unsafe_value in unsafe_values.items():
            with self.subTest(field_name=field_name):
                with self.assertRaises(module.Screen1SourceIntakeError):
                    self.make_request(**{field_name: unsafe_value})

    def test_evaluation_statuses(self) -> None:
        module = self.module()

        missing_actor = self.make_request(actor_id=None, actor_audit_context=None)
        self.assertEqual(
            module.evaluate_source_intake_request(missing_actor).validation_status,
            "NEEDS_ACTOR",
        )

        missing_source = self.make_request(source_reference=None)
        self.assertEqual(
            module.evaluate_source_intake_request(missing_source).validation_status,
            "NEEDS_SOURCE_REFERENCE",
        )

        missing_backend = self.make_request(backend_execution_request=None)
        self.assertEqual(
            module.evaluate_source_intake_request(missing_backend).validation_status,
            "NEEDS_BACKEND_VALIDATION",
        )

        object_storage_missing_config = self.make_request(
            source_mode="object_storage",
            source_reference={
                "namespace": "ns",
                "bucket": "bucket",
                "object_name": "awr.html",
                "region": "us-ashburn-1",
                "configured_hint": False,
            },
            requested_action="prepare_for_object_storage_load",
        )
        self.assertEqual(
            module.evaluate_source_intake_request(
                object_storage_missing_config
            ).validation_status,
            "NEEDS_OBJECT_STORAGE_CONFIG",
        )

        future_em = self.make_request(
            source_mode="future_em_extract",
            source_reference={"extract_id": "EM-1"},
            requested_action="prepare_for_future_em_extract",
        )
        self.assertEqual(
            module.evaluate_source_intake_request(future_em).validation_status,
            "FUTURE_SOURCE_NOT_IMPLEMENTED",
        )

        valid_request = self.make_request()
        validation = module.evaluate_source_intake_request(valid_request)
        self.assertTrue(validation.valid)
        self.assertEqual(
            validation.validation_status,
            "INTAKE_NOT_ALLOWED_IN_THIS_PHASE",
        )
        self.assertFalse(validation.can_intake)
        self.assertTrue(validation.intake_blocked)

    def test_preview_metadata(self) -> None:
        module = self.module()
        request = self.make_request()
        validation = module.evaluate_source_intake_request(request)
        preview = module.create_source_intake_preview(request, validation)

        self.assertEqual(preview.intake_request_id, request.intake_request_id)
        self.assertEqual(preview.source_mode, "local_file")
        self.assertFalse(preview.intake_performed)
        self.assertTrue(preview.source_validation_required)
        self.assertTrue(preview.backend_execution_required)
        self.assertTrue(preview.actor_required)
        self.assertTrue(preview.audit_required)
        self.assertTrue(preview.source_available_hint)
        self.assertIn("intake_performed=false", preview.preview_summary)

    def test_serialization_round_trip(self) -> None:
        module = self.module()
        request = self.make_request()
        validation = module.evaluate_source_intake_request(request)
        preview = module.create_source_intake_preview(request, validation)

        request_dict = module.source_intake_request_to_dict(request)
        validation_dict = module.source_intake_validation_to_dict(validation)
        preview_dict = module.source_intake_preview_to_dict(preview)

        self.assertEqual(
            request_dict,
            module.source_intake_request_to_dict(
                module.source_intake_request_from_dict(request_dict)
            ),
        )
        self.assertEqual(
            validation_dict,
            module.source_intake_validation_to_dict(
                module.source_intake_validation_from_dict(validation_dict)
            ),
        )
        self.assertEqual(
            preview_dict,
            module.source_intake_preview_to_dict(
                module.source_intake_preview_from_dict(preview_dict)
            ),
        )

    def test_deterministic_ids(self) -> None:
        module = self.module()
        first = module.create_source_intake_request_id(
            "local_file",
            "request_source_intake",
            "awr-one",
        )
        second = module.create_source_intake_request_id(
            "local_file",
            "request_source_intake",
            "awr-one",
        )
        self.assertEqual(first, second)
        self.assertEqual(
            module.create_source_intake_validation_id(first),
            module.create_source_intake_validation_id(second),
        )
        self.assertEqual(
            module.create_source_intake_preview_id(first),
            module.create_source_intake_preview_id(second),
        )
        self.assertNotIn("UUID", first.upper())

    def test_no_execution_functions(self) -> None:
        names = function_names(MODULE_PATH)
        for forbidden in FORBIDDEN_FUNCTION_NAMES:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, names)

        source = lower_text(MODULE_PATH)
        for forbidden in ("subprocess", "requests"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_runtime_import_isolation(self) -> None:
        run_analysis_imports = imported_modules(ROOT / "scripts" / "run_analysis.py")
        for module_name in (
            "src.learning.screen1_source_intake",
            "learning.screen1_source_intake",
            "screen1_source_intake",
        ):
            with self.subTest(module_name=module_name):
                self.assertNotIn(module_name, run_analysis_imports)

        for path in python_files(RUNTIME_IMPORT_PATHS):
            imports = imported_modules(path)
            source = read_text(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.screen1_source_intake", imports)
                self.assertNotIn("learning.screen1_source_intake", imports)
                self.assertNotIn("screen1_source_intake", imports)
                self.assertNotIn("screen1_source_intake", source)


if __name__ == "__main__":
    unittest.main()
