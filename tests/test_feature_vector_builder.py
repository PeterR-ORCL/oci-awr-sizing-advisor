from __future__ import annotations

import json
import math
import sys
import types
import unittest

from src.models.parse_result import ParseResult
from src.models.run_metadata import RunMetadata


def _load_feature_vector_builder_symbols():
    try:
        from src.ingest.awr_adb_loader import (
            FEATURE_SET_VERSION,
            FEATURE_VECTOR_LOGICAL_DIMENSION_COUNT,
            FEATURE_VECTOR_LOGICAL_KEY_ORDER,
            FEATURE_VECTOR_NUMERIC_CAPACITY,
            VECTOR_VERSION,
            build_feature_vector_record,
            build_numeric_feature_vector,
        )
    except ModuleNotFoundError as exc:
        if exc.name != "dotenv":
            raise
        sys.modules.setdefault(
            "dotenv",
            types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None),
        )
        from src.ingest.awr_adb_loader import (
            FEATURE_SET_VERSION,
            FEATURE_VECTOR_LOGICAL_DIMENSION_COUNT,
            FEATURE_VECTOR_LOGICAL_KEY_ORDER,
            FEATURE_VECTOR_NUMERIC_CAPACITY,
            VECTOR_VERSION,
            build_feature_vector_record,
            build_numeric_feature_vector,
        )
    return {
        "FEATURE_SET_VERSION": FEATURE_SET_VERSION,
        "FEATURE_VECTOR_LOGICAL_DIMENSION_COUNT": FEATURE_VECTOR_LOGICAL_DIMENSION_COUNT,
        "FEATURE_VECTOR_LOGICAL_KEY_ORDER": FEATURE_VECTOR_LOGICAL_KEY_ORDER,
        "FEATURE_VECTOR_NUMERIC_CAPACITY": FEATURE_VECTOR_NUMERIC_CAPACITY,
        "VECTOR_VERSION": VECTOR_VERSION,
        "build_feature_vector_record": build_feature_vector_record,
        "build_numeric_feature_vector": build_numeric_feature_vector,
    }


class FeatureVectorBuilderTests(unittest.TestCase):
    def test_vector_length_is_256(self) -> None:
        symbols = _load_feature_vector_builder_symbols()
        vector = symbols["build_numeric_feature_vector"]({})

        self.assertEqual(len(vector), 256)

    def test_first_values_map_in_contract_order(self) -> None:
        symbols = _load_feature_vector_builder_symbols()
        key_order = symbols["FEATURE_VECTOR_LOGICAL_KEY_ORDER"]
        feature_json = {
            key_order[0]: 1.25,
            key_order[1]: 2.5,
            key_order[2]: 3.75,
        }

        vector = symbols["build_numeric_feature_vector"](feature_json)

        self.assertEqual(vector[:3], [1.25, 2.5, 3.75])

    def test_padding_uses_zeroes(self) -> None:
        symbols = _load_feature_vector_builder_symbols()
        vector = symbols["build_numeric_feature_vector"]({})
        logical_dimension_count = symbols["FEATURE_VECTOR_LOGICAL_DIMENSION_COUNT"]

        self.assertTrue(
            all(value == 0.0 for value in vector[logical_dimension_count:])
        )

    def test_missing_or_non_numeric_features_map_to_zero(self) -> None:
        symbols = _load_feature_vector_builder_symbols()
        key_order = symbols["FEATURE_VECTOR_LOGICAL_KEY_ORDER"]
        feature_json = {
            key_order[0]: None,
            key_order[1]: "not-a-number",
            key_order[2]: float("nan"),
            key_order[3]: "7.5",
        }

        vector = symbols["build_numeric_feature_vector"](feature_json)

        self.assertEqual(vector[0], 0.0)
        self.assertEqual(vector[1], 0.0)
        self.assertEqual(vector[2], 0.0)
        self.assertEqual(vector[3], 7.5)

    def test_deterministic_ordering_for_same_input(self) -> None:
        symbols = _load_feature_vector_builder_symbols()
        key_order = symbols["FEATURE_VECTOR_LOGICAL_KEY_ORDER"]
        feature_json = {
            key_order[5]: 10.0,
            key_order[0]: 1.0,
            key_order[10]: 5.0,
        }

        left = symbols["build_numeric_feature_vector"](feature_json)
        right = symbols["build_numeric_feature_vector"](dict(reversed(list(feature_json.items()))))

        self.assertEqual(left, right)

    def test_feature_vector_record_populates_vector_and_versions(self) -> None:
        symbols = _load_feature_vector_builder_symbols()
        parse_result = ParseResult(
            run_metadata=RunMetadata(
                source_file_name="case.out",
                source_file_path="",
                parse_timestamp="2026-04-28T00:00:00",
                begin_snapshot_time="2026-04-28 00:00:00",
                end_snapshot_time="2026-04-28 01:00:00",
            )
        )

        record = symbols["build_feature_vector_record"](
            parse_result=parse_result,
            awr_id=1,
            source_system_id=1,
        )
        vector = record["feature_vector"]

        self.assertEqual(record["feature_set_version"], "4H_VECTOR_1")
        self.assertEqual(record["vector_version"], "4H_VECTOR_1")
        self.assertIsNotNone(vector)
        self.assertEqual(len(vector), symbols["FEATURE_VECTOR_NUMERIC_CAPACITY"])
        self.assertTrue(all(isinstance(value, float) for value in vector))
        self.assertTrue(all(value is not None for value in vector))
        self.assertTrue(all(math.isfinite(value) for value in vector))

    def test_feature_vector_record_keeps_feature_json_authoritative_and_unchanged(self) -> None:
        symbols = _load_feature_vector_builder_symbols()
        parse_result = ParseResult(
            run_metadata=RunMetadata(
                source_file_name="case.out",
                source_file_path="",
                parse_timestamp="2026-04-28T00:00:00",
                begin_snapshot_time="2026-04-28 00:00:00",
                end_snapshot_time="2026-04-28 01:00:00",
            )
        )

        record = symbols["build_feature_vector_record"](
            parse_result=parse_result,
            awr_id=1,
            source_system_id=1,
        )
        feature_json = json.loads(record["feature_json"])
        rebuilt_vector = symbols["build_numeric_feature_vector"](feature_json)

        self.assertEqual(record["feature_vector"], rebuilt_vector)


if __name__ == "__main__":
    unittest.main()
