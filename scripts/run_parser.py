import json
from pathlib import Path
from dataclasses import asdict, is_dataclass

from src.parser.awr_parser import parse_awr_file

if __name__ == "__main__":
    result = parse_awr_file("data/input/sample_awr_01.out")

    print("Run Metadata:")
    if is_dataclass(result.run_metadata):
        metadata_dict = asdict(result.run_metadata)
    elif hasattr(result.run_metadata, "to_dict"):
        metadata_dict = result.run_metadata.to_dict()
    elif hasattr(result.run_metadata, "model_dump"):
        metadata_dict = result.run_metadata.model_dump()
    else:
        metadata_dict = dict(result.run_metadata)

    for key, value in metadata_dict.items():
        print(f"  {key}: {value}")

    print("\nSection Counts:")
    print(f"  cpu_metrics: {len(result.cpu_metrics)}")
    print(f"  wait_events: {len(result.wait_events)}")
    print(f"  top_sql: {len(result.top_sql)}")
    print(f"  io_metrics: {len(result.io_metrics)}")
    print(f"  session_metrics: {len(result.session_metrics)}")

    print("\nSample CPU Metrics:")
    for row in result.cpu_metrics[:3]:
        print(f"  {row}")

    print("\nSample Wait Events:")
    for row in result.wait_events[:3]:
        print(f"  {row}")

    print(f"  top_sql: {len(result.top_sql)}")

    print("\nSample Top SQL:")
    for row in result.top_sql[:3]:
        print(f"  {row}")

    print("\nWarnings:")
    if result.parse_warnings:
        for warning in result.parse_warnings:
            print(f"  - {warning}")
    else:
        print("  None")

    print("\nErrors:")
    if result.parse_errors:
        for error in result.parse_errors:
            print(f"  - {error}")
    else:
        print("  None")

    output_path = Path("data/output/parse_result.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2)

    print(f"\nWrote parse result to: {output_path}")
