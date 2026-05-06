from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.loader.awr_loader import load_awr_sources, loader_file_paths
from src.models.parse_diagnostics import ParseDiagnostics, UnknownParserElement
from src.models.parse_result import ParseResult
from src.models.run_metadata import RunMetadata
from src.parser.awr_parser import build_parser_result_contract


class LoaderParserBoundaryTests(unittest.TestCase):
    def _sample_parse_result(self) -> ParseResult:
        return ParseResult(
            run_metadata=RunMetadata(
                source_file_name="sample.out",
                source_file_path="/tmp/sample.out",
                parse_timestamp="2026-05-05T00:00:00",
                platform="Linux x86 64-bit",
                db_version="19c",
            ),
            sections_found={"cpu": {"start_line": 1, "end_line": 2}},
            cpu_metrics=[{"metric_name": "DB CPU(s)", "per_second": 1.0}],
            topology_signals={"rac_detected": False, "data_guard_detected": True},
            parse_diagnostics=ParseDiagnostics(
                source_file_name="sample.out",
                sections_found=["cpu"],
                sections_missing=["waits"],
                parse_completeness_ratio=0.5,
                unknown_sections=[
                    UnknownParserElement(
                        parser_stage="section_locator",
                        raw_text="Unknown Header",
                        line_number=12,
                    )
                ],
            ),
            parse_warnings=["Optional section not found: waits"],
        )

    def test_loader_result_contains_source_inventory_not_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir)
            awr_path = input_dir / "sample.out"
            awr_path.write_text("AWR sample\n", encoding="utf-8")
            (input_dir / "ignored.txt").write_text("not awr\n", encoding="utf-8")

            loader_result = load_awr_sources(input_dir)

        self.assertEqual(loader_result["source_type"], "LOCAL")
        self.assertEqual(loader_result["files_discovered"], 1)
        self.assertEqual(loader_result["loader_status"], "READY")
        self.assertEqual(loader_result["files"][0]["file_name"], "sample.out")
        self.assertEqual(loader_result["files"][0]["read_status"], "READY")
        self.assertNotIn("metrics", loader_result)
        self.assertNotIn("sections_detected", loader_result)

    def test_loader_file_paths_returns_ready_parser_handoff_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_dir = Path(temp_dir)
            awr_path = input_dir / "sample.out"
            awr_path.write_text("AWR sample\n", encoding="utf-8")

            loader_result = load_awr_sources(input_dir)
            handoff_paths = loader_file_paths(loader_result)

        self.assertEqual(handoff_paths, [awr_path])

    def test_parser_contract_contains_parser_metadata_not_source_discovery(self) -> None:
        parser_contract = build_parser_result_contract(self._sample_parse_result())

        self.assertEqual(parser_contract["file_name"], "sample.out")
        self.assertEqual(parser_contract["parse_status"], "PARSED")
        self.assertEqual(parser_contract["sections_detected"], ["cpu"])
        self.assertEqual(parser_contract["sections_missing"], ["waits"])
        self.assertEqual(parser_contract["parse_confidence"], 0.5)
        self.assertIn("cpu_metrics", parser_contract["metrics"])
        self.assertEqual(len(parser_contract["unknown_signals"]), 1)
        self.assertNotIn("source_path", parser_contract)
        self.assertNotIn("files_discovered", parser_contract)
        self.assertNotIn("source_type", parser_contract)

    def test_parser_contract_returns_exact_boundary_keys(self) -> None:
        parser_contract = build_parser_result_contract(self._sample_parse_result())

        self.assertEqual(
            set(parser_contract.keys()),
            {
                "file_name",
                "parse_status",
                "sections_detected",
                "sections_missing",
                "metrics",
                "topology_hints",
                "platform_hints",
                "parse_confidence",
                "parser_notes",
                "unknown_signals",
            },
        )

    def test_parser_contract_helper_is_importable_and_callable(self) -> None:
        self.assertTrue(callable(build_parser_result_contract))
        parser_contract = build_parser_result_contract(self._sample_parse_result())
        self.assertIn("metrics", parser_contract)
        self.assertIn("sections_detected", parser_contract)
        self.assertIn("sections_missing", parser_contract)
        self.assertIn("parse_confidence", parser_contract)
        self.assertIn("unknown_signals", parser_contract)


if __name__ == "__main__":
    unittest.main()
