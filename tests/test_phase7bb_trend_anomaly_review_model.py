from __future__ import annotations

import ast
import importlib
import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "architecture"
MODEL_DOC = DOCS / "phase7bb_trend_anomaly_review_model.md"
LIFECYCLE_DOC = DOCS / "phase7bb_trend_anomaly_review_lifecycle.md"
README = DOCS / "README.md"
MODULE_PATH = ROOT / "src" / "learning" / "screen4_trend_anomaly_review.py"

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
    "src.trend",
    "src.anomaly",
    "src.decision",
    "src.recommendation",
    "src.recommendations",
    "src.analysis",
    "src.memory",
    "scripts.awr_memory_cli",
    "scripts.run_analysis",
    "oracle_agent_memory",
)

FORBIDDEN_SOURCE_TERMS = (
    "persist_trend_review",
    "persist_anomaly_review",
    "update_trend",
    "update_anomaly",
    "update_score",
    "create_learning_candidate",
    "mutate_phase4i",
    "write_database",
    "run_analysis",
    "auto_apply",
    "autonomous_apply",
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
            files.extend(
                sorted(child for child in path.rglob("*.py") if child.is_file())
            )
    return files


def git_changed_paths(pathspecs: tuple[str, ...] = ()) -> set[str]:
    changed: set[str] = set()
    git_commands = (
        ("git", "diff", "--name-only"),
        ("git", "diff", "--cached", "--name-only"),
        ("git", "ls-files", "--others", "--exclude-standard"),
    )
    for base_command in git_commands:
        command = base_command + (("--",) + pathspecs if pathspecs else ())
        completed = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "git change scan unavailable")
        changed.update(
            line.strip()
            for line in completed.stdout.splitlines()
            if line.strip()
        )
    return changed


class Phase7BBTrendAnomalyReviewModelTests(unittest.TestCase):
    @staticmethod
    def module():
        return importlib.import_module("src.learning.screen4_trend_anomaly_review")

    def make_trend_record(self, **overrides):
        module = self.module()
        run_id = overrides.get("run_id", "RUN-1")
        awr_id = overrides.get("awr_id", "AWR-1")
        trend_id = overrides.get("trend_id", "TREND-CPU-1")
        values = {
            "trend_review_id": module.create_trend_review_id(
                run_id,
                awr_id,
                trend_id,
            ),
            "run_id": run_id,
            "awr_id": awr_id,
            "baseline_candidate_id": "HIST-BASELINE-CANDIDATE-RUN-BASE-SNAP-10",
            "comparison_context_id": "HIST-COMPARISON-CONTEXT-BASE-TARGET",
            "trend_id": trend_id,
            "trend_name": "CPU rose over baseline",
            "domain": "CPU",
            "trend_direction": "increasing",
            "trend_strength": 0.82,
            "review_decision": "approve_trend",
            "review_status": "approved",
            "reviewer_actor_id": "ACTOR-LOCAL-JANE-REVIEWER",
            "actor_audit_context": {"actor_id": "ACTOR-LOCAL-JANE-REVIEWER"},
            "review_notes": "metadata only",
            "linked_scoring_review_id": None,
            "linked_candidate_intent_id": None,
            "write_performed": False,
            "trend_truth_changed": False,
            "scoring_mutation_requested": False,
            "runtime_influence": False,
            "phase4i_mutation_requested": False,
            "created_at": "2026-05-15T12:00:00",
            "notes": "metadata only",
        }
        values.update(overrides)
        return module.HistoricalTrendReviewRecord(**values)

    def make_anomaly_record(self, **overrides):
        module = self.module()
        run_id = overrides.get("run_id", "RUN-1")
        awr_id = overrides.get("awr_id", "AWR-1")
        anomaly_id = overrides.get("anomaly_id", "ANOM-CPU-1")
        values = {
            "anomaly_review_id": module.create_anomaly_review_id(
                run_id,
                awr_id,
                anomaly_id,
            ),
            "run_id": run_id,
            "awr_id": awr_id,
            "baseline_candidate_id": "HIST-BASELINE-CANDIDATE-RUN-BASE-SNAP-10",
            "comparison_context_id": "HIST-COMPARISON-CONTEXT-BASE-TARGET",
            "anomaly_id": anomaly_id,
            "anomaly_name": "CPU anomaly spike",
            "domain": "CPU",
            "anomaly_pattern": "single_snapshot_spike",
            "anomaly_severity": 0.74,
            "review_decision": "approve_anomaly",
            "review_status": "approved",
            "reviewer_actor_id": "ACTOR-LOCAL-JANE-REVIEWER",
            "actor_audit_context": {"actor_id": "ACTOR-LOCAL-JANE-REVIEWER"},
            "review_notes": "metadata only",
            "linked_scoring_review_id": None,
            "linked_candidate_intent_id": None,
            "write_performed": False,
            "anomaly_truth_changed": False,
            "scoring_mutation_requested": False,
            "runtime_influence": False,
            "phase4i_mutation_requested": False,
            "created_at": "2026-05-15T12:00:00",
            "notes": "metadata only",
        }
        values.update(overrides)
        return module.HistoricalAnomalyReviewRecord(**values)

    def make_request(self, **overrides):
        module = self.module()
        target_type = overrides.get("review_target_type", "trend_metric")
        target_id = overrides.get("review_target_id", "TREND-CPU-1")
        decision = overrides.get("requested_decision", "approve_trend")
        request_id = overrides.get(
            "request_id",
            (
                module.create_historical_review_request_id(
                    target_type,
                    target_id,
                    decision,
                )
                if target_id
                else "SCREEN4-HIST-REQUEST-MISSING-TARGET"
            ),
        )
        values = {
            "request_id": request_id,
            "review_target_type": target_type,
            "review_target_id": target_id,
            "requested_decision": decision,
            "actor_id": "ACTOR-LOCAL-JANE-REVIEWER",
            "actor_audit_context": {"actor_id": "ACTOR-LOCAL-JANE-REVIEWER"},
            "baseline_candidate_id": "HIST-BASELINE-CANDIDATE-RUN-BASE-SNAP-10",
            "comparison_context_id": "HIST-COMPARISON-CONTEXT-BASE-TARGET",
            "payload": {"domain": "CPU"},
            "validation_status": "valid",
            "can_route_to_governance": True,
            "write_performed": False,
            "truth_mutation_requested": False,
            "scoring_mutation_requested": False,
            "runtime_influence": False,
            "phase4i_mutation_requested": False,
            "notes": "metadata only",
        }
        values.update(overrides)
        return module.HistoricalReviewRequest(**values)

    def make_validation(self, **overrides):
        module = self.module()
        request = overrides.pop("request", self.make_request())
        values = {
            "validation_id": module.create_historical_review_validation_id(
                request.request_id,
            ),
            "request_id": request.request_id,
            "valid": True,
            "validation_status": "valid",
            "requested_decision": request.requested_decision,
            "actor_present": True,
            "target_present": True,
            "baseline_context_present": True,
            "can_route_to_governance": True,
            "write_performed": False,
            "truth_mutation_requested": False,
            "scoring_mutation_requested": False,
            "denied_reasons": [],
            "warnings": ["metadata only"],
            "required_next_steps": ["future governed write path"],
            "runtime_influence": False,
            "phase4i_mutation_requested": False,
            "notes": "metadata only",
        }
        values.update(overrides)
        return module.HistoricalReviewValidation(**values)

    def test_module_import_safety(self) -> None:
        before_environment = dict(os.environ)
        module = self.module()
        self.assertEqual(before_environment, dict(os.environ))
        self.assertTrue(hasattr(module, "HistoricalTrendReviewRecord"))
        self.assertTrue(hasattr(module, "HistoricalAnomalyReviewRecord"))
        self.assertTrue(hasattr(module, "HistoricalReviewRequest"))
        self.assertTrue(hasattr(module, "HistoricalReviewValidation"))

        imports = imported_modules(MODULE_PATH)
        for forbidden in FORBIDDEN_IMPORT_PREFIXES:
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        imported == forbidden or imported.startswith(f"{forbidden}.")
                        for imported in imports
                    )
                )

    def test_docs_exist_and_contain_required_boundary_phrases(self) -> None:
        self.assertTrue(MODEL_DOC.is_file(), MODEL_DOC)
        self.assertTrue(LIFECYCLE_DOC.is_file(), LIFECYCLE_DOC)
        text = lower_text(MODEL_DOC) + "\n" + lower_text(LIFECYCLE_DOC)
        for phrase in (
            "review records do not mutate trend truth",
            "review records do not mutate anomaly truth",
            "review records do not change scoring",
            "review records do not create learning candidates",
            "write_performed=false in 7bb",
            "runtime_influence=false",
            "phase 4i mutation is forbidden",
            "deterministic runtime remains authoritative",
            "no lifecycle stage writes records in 7bb",
            "review validation is not persistence",
            "routing intent is metadata only",
            "future workflows cannot skip actor",
            "future workflows cannot skip governed write path",
            "trend/anomaly review cannot mutate historical truth",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_supported_values_and_unsupported_values(self) -> None:
        module = self.module()
        self.assertEqual(
            module.HISTORICAL_REVIEW_TARGET_TYPES,
            (
                "trend_summary",
                "trend_metric",
                "anomaly_group",
                "anomaly_event",
                "historical_baseline",
                "comparison_baseline",
                "recurrence_pattern",
                "historical_confidence",
                "missing_historical_evidence",
                "trend_aware_scoring_reference",
                "learning_candidate_intent",
            ),
        )
        self.assertEqual(
            module.HISTORICAL_REVIEW_DECISIONS,
            (
                "approve_trend",
                "dispute_trend",
                "mark_trend_insufficient",
                "approve_anomaly",
                "mark_anomaly_false_positive",
                "mark_anomaly_insufficient",
                "request_trend_aware_scoring_review",
                "request_anomaly_sensitivity_review",
                "request_scoring_threshold_review",
                "request_learning_candidate",
                "add_historical_review_note",
            ),
        )
        self.assertEqual(
            module.HISTORICAL_REVIEW_STATUSES,
            (
                "proposed",
                "under_review",
                "approved",
                "disputed",
                "insufficient_evidence",
                "false_positive",
                "routed_to_governance",
                "linked_to_candidate",
                "closed",
            ),
        )
        self.assertIn("write_not_allowed_in_this_phase", module.HISTORICAL_REVIEW_VALIDATION_STATUSES)

        with self.assertRaises(module.Screen4TrendAnomalyReviewError):
            self.make_trend_record(review_decision="approve_runtime")
        with self.assertRaises(module.Screen4TrendAnomalyReviewError):
            self.make_trend_record(review_status="runtime_applied")
        with self.assertRaises(module.Screen4TrendAnomalyReviewError):
            self.make_request(review_target_type="runtime_target")
        with self.assertRaises(module.Screen4TrendAnomalyReviewError):
            self.make_validation(validation_status="runtime_applied")

    def test_trend_review_record_validation(self) -> None:
        module = self.module()
        record = self.make_trend_record()
        self.assertIs(module.validate_historical_trend_review_record(record), record)

        for overrides in (
            {"write_performed": True},
            {"trend_truth_changed": True},
            {"scoring_mutation_requested": True},
            {"runtime_influence": True},
            {"phase4i_mutation_requested": True},
            {"review_decision": "unsupported"},
            {"review_status": "unsupported"},
            {"trend_strength": -0.1},
            {"trend_strength": 1.1},
            {"reviewer_actor_id": None},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(module.Screen4TrendAnomalyReviewError):
                    self.make_trend_record(**overrides)

    def test_anomaly_review_record_validation(self) -> None:
        module = self.module()
        record = self.make_anomaly_record()
        self.assertIs(module.validate_historical_anomaly_review_record(record), record)

        for overrides in (
            {"write_performed": True},
            {"anomaly_truth_changed": True},
            {"scoring_mutation_requested": True},
            {"runtime_influence": True},
            {"phase4i_mutation_requested": True},
            {"review_decision": "unsupported"},
            {"review_status": "unsupported"},
            {"anomaly_severity": -0.1},
            {"anomaly_severity": 1.1},
            {"reviewer_actor_id": None},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(module.Screen4TrendAnomalyReviewError):
                    self.make_anomaly_record(**overrides)

    def test_review_request_validation(self) -> None:
        module = self.module()
        request = self.make_request()
        self.assertIs(module.validate_historical_review_request(request), request)

        missing_actor = self.make_request(actor_id=None)
        with self.assertRaises(module.Screen4TrendAnomalyReviewError):
            module.validate_historical_review_request(missing_actor)

        for overrides in (
            {"truth_mutation_requested": True},
            {"scoring_mutation_requested": True},
            {"write_performed": True},
            {"runtime_influence": True},
            {"phase4i_mutation_requested": True},
            {"payload": []},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(module.Screen4TrendAnomalyReviewError):
                    self.make_request(**overrides)

    def test_review_validation_validation(self) -> None:
        module = self.module()
        validation = self.make_validation()
        self.assertIs(module.validate_historical_review_validation(validation), validation)

        for overrides in (
            {"write_performed": True},
            {"truth_mutation_requested": True},
            {"scoring_mutation_requested": True},
            {"runtime_influence": True},
            {"phase4i_mutation_requested": True},
            {"validation_status": "runtime_applied"},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(module.Screen4TrendAnomalyReviewError):
                    self.make_validation(**overrides)

    def test_evaluate_historical_review_request(self) -> None:
        module = self.module()
        missing_actor = module.evaluate_historical_review_request(
            self.make_request(actor_id=None)
        )
        self.assertFalse(missing_actor.valid)
        self.assertEqual("needs_actor", missing_actor.validation_status)

        missing_target = module.evaluate_historical_review_request(
            self.make_request(review_target_id=None)
        )
        self.assertFalse(missing_target.valid)
        self.assertEqual("needs_target", missing_target.validation_status)

        missing_context = module.evaluate_historical_review_request(
            self.make_request(
                baseline_candidate_id=None,
                comparison_context_id=None,
            )
        )
        self.assertFalse(missing_context.valid)
        self.assertEqual("needs_baseline_context", missing_context.validation_status)

        valid = module.evaluate_historical_review_request(self.make_request())
        self.assertTrue(valid.valid)
        self.assertEqual("valid", valid.validation_status)
        self.assertTrue(valid.can_route_to_governance)
        self.assertFalse(valid.write_performed)
        self.assertFalse(valid.truth_mutation_requested)
        self.assertFalse(valid.scoring_mutation_requested)
        self.assertFalse(valid.runtime_influence)
        self.assertFalse(valid.phase4i_mutation_requested)

    def test_routing_intent_mapping(self) -> None:
        module = self.module()
        expected = {
            "request_trend_aware_scoring_review": "scoring_review_intent",
            "request_anomaly_sensitivity_review": "scoring_review_intent",
            "request_scoring_threshold_review": "scoring_review_intent",
            "request_learning_candidate": "learning_candidate_intent",
            "mark_anomaly_false_positive": "validation_intent",
            "dispute_trend": "human_review_intent",
            "mark_trend_insufficient": "evidence_validation_intent",
        }
        for decision, intent in expected.items():
            with self.subTest(decision=decision):
                self.assertEqual(
                    intent,
                    module.routing_intent_for_historical_decision(decision),
                )
        with self.assertRaises(module.Screen4TrendAnomalyReviewError):
            module.routing_intent_for_historical_decision("runtime_apply")

    def test_serialization_round_trips_are_deterministic(self) -> None:
        module = self.module()
        objects = (
            (
                module.historical_trend_review_record_to_dict,
                module.historical_trend_review_record_from_dict,
                self.make_trend_record(),
            ),
            (
                module.historical_anomaly_review_record_to_dict,
                module.historical_anomaly_review_record_from_dict,
                self.make_anomaly_record(),
            ),
            (
                module.historical_review_request_to_dict,
                module.historical_review_request_from_dict,
                self.make_request(),
            ),
            (
                module.historical_review_validation_to_dict,
                module.historical_review_validation_from_dict,
                self.make_validation(),
            ),
        )
        for to_dict, from_dict, value in objects:
            with self.subTest(value=type(value).__name__):
                serialized = to_dict(value)
                self.assertEqual(to_dict(from_dict(serialized)), serialized)
                self.assertEqual(
                    to_dict(from_dict(serialized)),
                    to_dict(from_dict(serialized)),
                )

    def test_deterministic_ids(self) -> None:
        module = self.module()
        ids = (
            module.create_trend_review_id("RUN-1", "AWR-1", "TREND-CPU-1"),
            module.create_anomaly_review_id("RUN-1", "AWR-1", "ANOM-CPU-1"),
            module.create_historical_review_request_id(
                "trend_metric",
                "TREND-CPU-1",
                "approve_trend",
            ),
            module.create_historical_review_validation_id(
                "SCREEN4-HIST-REQUEST-TREND-METRIC-TREND-CPU-1-APPROVE-TREND"
            ),
        )
        self.assertEqual(
            ids[0],
            module.create_trend_review_id("RUN-1", "AWR-1", "TREND-CPU-1"),
        )
        self.assertEqual(
            ids[1],
            module.create_anomaly_review_id("RUN-1", "AWR-1", "ANOM-CPU-1"),
        )
        self.assertEqual(
            ids[2],
            module.create_historical_review_request_id(
                "trend_metric",
                "TREND-CPU-1",
                "approve_trend",
            ),
        )
        self.assertEqual(
            ids[3],
            module.create_historical_review_validation_id(
                "SCREEN4-HIST-REQUEST-TREND-METRIC-TREND-CPU-1-APPROVE-TREND"
            ),
        )
        for value in ids:
            with self.subTest(value=value):
                self.assertFalse(
                    re.search(
                        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                        value.lower(),
                    )
                )

    def test_no_mutation_or_persistence_functions(self) -> None:
        names = function_names(MODULE_PATH)
        source = read_text(MODULE_PATH)
        for forbidden in FORBIDDEN_SOURCE_TERMS:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, names)
                self.assertNotIn(forbidden, source)

    def test_runtime_import_isolation(self) -> None:
        run_analysis_imports = imported_modules(ROOT / "scripts" / "run_analysis.py")
        for module_name in (
            "src.learning.screen4_trend_anomaly_review",
            "learning.screen4_trend_anomaly_review",
            "screen4_trend_anomaly_review",
        ):
            with self.subTest(module_name=module_name):
                self.assertNotIn(module_name, run_analysis_imports)

        for path in python_files(RUNTIME_IMPORT_PATHS):
            imports = imported_modules(path)
            source = read_text(path)
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("src.learning.screen4_trend_anomaly_review", imports)
                self.assertNotIn("learning.screen4_trend_anomaly_review", imports)
                self.assertNotIn("screen4_trend_anomaly_review", imports)
                self.assertNotIn("screen4_trend_anomaly_review", source)

    def test_behavior_files_are_not_modified_by_phase7bb(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git not available")
        if not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")

        try:
            changed = git_changed_paths(FORBIDDEN_BEHAVIOR_FILES)
        except RuntimeError as exc:
            self.skipTest(str(exc))

        self.assertFalse(changed, f"behavior files modified: {sorted(changed)}")

    def test_readme_links_new_docs(self) -> None:
        text = read_text(README)
        for title, filename in (
            (
                "Phase 7BB Trend / Anomaly Review Object Model",
                "phase7bb_trend_anomaly_review_model.md",
            ),
            (
                "Phase 7BB Trend / Anomaly Review Lifecycle",
                "phase7bb_trend_anomaly_review_lifecycle.md",
            ),
        ):
            with self.subTest(title=title):
                self.assertIn(title, text)
                self.assertIn(filename, text)


if __name__ == "__main__":
    unittest.main()
