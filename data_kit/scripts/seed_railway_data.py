#!/usr/bin/env python3
"""Load generated operational JSON into the shared SQLite database."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from policy_settings.database import DEFAULT_DB_PATH  # noqa: E402
from railway_data.seeder import seed_dataset  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=PROJECT_ROOT / "data" / "synthetic")
    parser.add_argument("--database", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--reset-synthetic", action="store_true", help="Delete only rows tagged ujjwal-demo-v1 before loading")
    args = parser.parse_args()
    print(json.dumps(seed_dataset(args.data_dir, db_path=args.database, reset_synthetic=args.reset_synthetic), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
