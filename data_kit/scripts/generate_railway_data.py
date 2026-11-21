#!/usr/bin/env python3
"""Generate deterministic Ujjwal Rail operational JSON."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from policy_settings.database import DEFAULT_DB_PATH  # noqa: E402
from railway_data.generator import generate_dataset  # noqa: E402


CREATIVE_PROMPT_PATH = PROJECT_ROOT / "data_generation" / "railway_generation_prompt.md"


def _ollama_catalog(model: str) -> dict:
    prompt = CREATIVE_PROMPT_PATH.read_text(encoding="utf-8")
    process = subprocess.run(
        ["ollama", "run", model, prompt], capture_output=True, text=True, check=True, timeout=180
    )
    response = process.stdout.strip()
    if response.startswith("```"):
        response = response.split("\n", 1)[1].rsplit("```", 1)[0]
    catalog = json.loads(response)
    return catalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference-date", type=date.fromisoformat, default=date(2026, 11, 21))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "data" / "synthetic")
    parser.add_argument("--database", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--ollama-model", help="Optional installed Ollama model for creative catalog JSON")
    args = parser.parse_args()

    catalog = None
    source = "deterministic-curated-fallback (no external LLM invoked)"
    if args.ollama_model:
        catalog = _ollama_catalog(args.ollama_model)
        source = f"Ollama model {args.ollama_model}"
    manifest = generate_dataset(
        args.output_dir,
        reference_date=args.reference_date,
        seed=args.seed,
        db_path=args.database,
        creative_catalog=catalog,
        creative_generation=source,
    )
    log = {
        "model_provider": "Ollama" if args.ollama_model else None,
        "actual_model_name": args.ollama_model,
        "external_model_invoked": bool(args.ollama_model),
        "generation_parameters": {"random_seed": args.seed, "reference_date": args.reference_date.isoformat()},
        "generation_timestamp": manifest["generated_at"],
        "prompt_file": "data_generation/railway_generation_prompt.md",
        "output_files": manifest["files"] + ["generation_manifest.json"],
        "deterministic_corrections": [
            "Python assigned IDs and keys", "Python calculated routes, dates, fares and boarding datetimes",
            "Python allocated CNF/RAC/WL inventory", "Python created and reconciled edge cases",
        ],
        "limitation": None if args.ollama_model else "Ollama service was inaccessible; creative content uses the checked-in curated fallback catalog.",
    }
    log_path = PROJECT_ROOT / "data_generation" / "railway_generation_log.json"
    log_path.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
