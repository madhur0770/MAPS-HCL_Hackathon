#!/usr/bin/env python3
"""Validate settings, precedence, source attribution, and idempotency."""

from pathlib import Path
import argparse
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from policy_settings.database import DEFAULT_DB_PATH
from policy_settings.validation import validate_database


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--as-of", help="ISO snapshot time to compare against settings")
    parser.add_argument(
        "--skip-idempotency",
        action="store_true",
        help="Skip the repeat-seeding equivalence check",
    )
    args = parser.parse_args()
    errors = validate_database(
        args.db,
        as_of=args.as_of,
        check_idempotency=not args.skip_idempotency,
    )
    if errors:
        print("Settings validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Settings validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
