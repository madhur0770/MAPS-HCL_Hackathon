#!/usr/bin/env python3
"""Validate generated JSON and its seeded SQLite representation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from policy_settings.database import DEFAULT_DB_PATH  # noqa: E402
from railway_data.validator import validate_dataset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "data" / "synthetic")
    parser.add_argument("--database", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--report", type=Path, default=PROJECT_ROOT / "data" / "synthetic" / "validation_report.json")
    args = parser.parse_args()
    report = validate_dataset(args.data_dir, db_path=args.database)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for result in report["checks"]:
        print(f"{result['status']:4} {result['check']}: {result['detail']}")
    print(json.dumps(report["summary"]))
    return 1 if report["summary"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
