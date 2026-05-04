#!/usr/bin/env python3
"""CLI helper for recording Phase 6 action history rows."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from src.memory import memory_orchestrator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record a manual/operator action for an AWR advisory run.",
    )
    parser.add_argument("--run-history-id", required=True, type=int)
    parser.add_argument("--recommendation-history-id", type=int)
    parser.add_argument("--action-type", required=True)
    parser.add_argument("--action-status", default="RECORDED")
    parser.add_argument("--action-summary", required=True)
    parser.add_argument("--actor")
    parser.add_argument("--notes")
    parser.add_argument("--metadata")
    return parser


def parse_metadata(raw_metadata: str | None) -> dict[str, Any] | None:
    if raw_metadata is None:
        return None
    try:
        parsed = json.loads(raw_metadata)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"--metadata must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--metadata must be a JSON object")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        metadata = parse_metadata(args.metadata)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    result = memory_orchestrator.record_action(
        run_history_id=args.run_history_id,
        recommendation_history_id=args.recommendation_history_id,
        action_type=args.action_type,
        action_status=args.action_status,
        action_summary=args.action_summary,
        actor=args.actor,
        notes=args.notes,
        action_metadata=metadata,
    )
    _print_result(result)
    if not result.get("enabled"):
        return 0
    return 0 if result.get("success") else 1


def _print_result(result: dict[str, Any]) -> None:
    print("Action Tracking:")
    print(f"  enabled: {str(bool(result.get('enabled'))).lower()}")
    if not result.get("enabled"):
        skipped = result.get("skipped") or []
        print(f"  skipped: {', '.join(skipped) if skipped else 'none'}")
        return
    print(f"  success: {str(bool(result.get('success'))).lower()}")
    if result.get("success"):
        print(f"  action_history_id: {result.get('action_history_id')}")
        print(f"  run_history_id: {result.get('run_history_id')}")
        print(f"  action_type: {result.get('action_type')}")
        print(f"  action_status: {result.get('action_status')}")
    elif result.get("errors"):
        print(f"  error: {result['errors'][0]}")
    for warning in result.get("warnings") or []:
        print(f"  warning: {warning}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
