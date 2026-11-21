#!/usr/bin/env python3
"""Seed reviewed rule and circular values into SQLite."""

from pathlib import Path
import argparse
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from policy_settings.database import DEFAULT_DB_PATH
from policy_settings.seeder import seed_database


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument(
        "--as-of",
        help="ISO date/time for the settings snapshot; defaults to current Asia/Kolkata time",
    )
    args = parser.parse_args()
    result = seed_database(args.db, as_of=args.as_of)
    print(
        f"Seeded {result['settings']} settings and {result['versions']} versions "
        f"at {result['as_of']} into {args.db}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
