# Synthetic railway data module

This module generates reviewable JSON and seeds it into the existing `data/ujjwal_rail.db` without recreating or updating policy settings.

From the project root:

```bash
python3 scripts/generate_railway_data.py
python3 scripts/seed_railway_data.py
python3 scripts/validate_railway_data.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The generator defaults to reference date `2026-11-21`, seed `42`, and `data/synthetic`. Override them with `--reference-date`, `--seed`, `--output-dir`, or `--database`. To use a functioning local Ollama service for the creative catalog, pass `--ollama-model MODEL`; the exact prompt and actual invocation metadata are recorded under `data_generation/`. Without that flag the script truthfully records the deterministic curated fallback.

Seeding uses one transaction, enables SQLite foreign keys, inserts only missing records, and verifies identical existing rows. It fails on primary-key collisions instead of overwriting user or judge data. `--reset-synthetic` is explicit and removes only rows whose `dataset_id` is `ujjwal-demo-v1`; it never deletes settings rows. The `actions` table starts empty and is ready for later confirmation workflows.

Canonical values use JSON arrays for station aliases, running days and class lists; SQLite stores these arrays as JSON text. Money is integer paise. Seat `available`, `rac`, and `waitlist` fields mean remaining train/class-level quota after active booking allocation. JSON remains the reviewable generation output and SQLite is the serving copy.
