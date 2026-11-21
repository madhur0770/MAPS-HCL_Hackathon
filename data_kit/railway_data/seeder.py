"""Transactional, collision-safe loading of synthetic operational JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from policy_settings.database import DEFAULT_DB_PATH

from .database import connect, initialize_schema
from .generator import DATASET_ID


FILE_TABLES = [
    ("stations.json", "stations", ["station_code"]),
    ("trains.json", "trains", ["train_no"]),
    ("train_stops.json", "train_stops", ["train_no", "stop_order"]),
    ("train_capacities.json", "train_capacities", ["train_no", "class"]),
    ("fares.json", "fares", ["train_no", "class", "from_code", "to_code"]),
    ("service_cancellations.json", "train_service_cancellations", ["train_no", "journey_date"]),
    ("seats.json", "seats", ["train_no", "journey_date", "class"]),
    ("passengers.json", "passengers", ["passenger_id"]),
    ("bookings.json", "bookings", ["booking_id"]),
    ("booking_travellers.json", "booking_travellers", ["traveller_id"]),
]

RESET_ORDER = [
    "actions", "booking_travellers", "bookings", "seats",
    "train_service_cancellations", "fares", "train_capacities", "train_stops",
    "passengers", "trains", "stations", "edge_case_scenarios", "synthetic_datasets",
]


def _settings_snapshot(connection: Any) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    settings = [tuple(row) for row in connection.execute("SELECT * FROM settings ORDER BY name")]
    versions = [tuple(row) for row in connection.execute("SELECT * FROM setting_versions ORDER BY name, effective_from")]
    return settings, versions


def _encoded_row(row: dict[str, Any]) -> dict[str, Any]:
    encoded = dict(row)
    for key in ("other_names", "runs_on", "classes", "result"):
        if key in encoded and isinstance(encoded[key], (list, dict)):
            encoded[key] = json.dumps(encoded[key], ensure_ascii=False, sort_keys=True)
    return encoded


def _insert_or_verify(connection: Any, table: str, row: dict[str, Any], keys: list[str]) -> str:
    encoded = _encoded_row(row)
    where = " AND ".join(f"{key} = ?" for key in keys)
    existing = connection.execute(
        f"SELECT * FROM {table} WHERE {where}", tuple(encoded[key] for key in keys)
    ).fetchone()
    if existing is not None:
        conflicts = [key for key, value in encoded.items() if existing[key] != value]
        if conflicts:
            raise ValueError(f"collision in {table} for {keys}: differing fields {conflicts}")
        return "verified"
    columns = list(encoded)
    placeholders = ", ".join("?" for _ in columns)
    connection.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(encoded[column] for column in columns),
    )
    return "inserted"


def seed_dataset(
    data_dir: Path,
    *,
    db_path: Path = DEFAULT_DB_PATH,
    reset_synthetic: bool = False,
) -> dict[str, int]:
    initialize_schema(db_path)
    required = [data_dir / item[0] for item in FILE_TABLES] + [data_dir / "edge_cases.json"]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing generated files: {missing}")

    counts = {"inserted": 0, "verified": 0, "deleted": 0}
    with connect(db_path) as connection:
        before = _settings_snapshot(connection)
        if reset_synthetic:
            for table in RESET_ORDER:
                cursor = connection.execute(f"DELETE FROM {table} WHERE dataset_id = ?", (DATASET_ID,))
                counts["deleted"] += cursor.rowcount

        metadata = json.loads((data_dir / "generation_manifest.json").read_text(encoding="utf-8"))
        dataset_row = {
            "dataset_id": DATASET_ID,
            "reference_date": metadata["reference_date"],
            "random_seed": metadata["random_seed"],
            "generated_at": metadata["generated_at"],
            "source": metadata["creative_generation"],
        }
        outcome = _insert_or_verify(connection, "synthetic_datasets", dataset_row, ["dataset_id"])
        counts[outcome] += 1

        for filename, table, keys in FILE_TABLES:
            records = json.loads((data_dir / filename).read_text(encoding="utf-8"))
            for row in records:
                outcome = _insert_or_verify(connection, table, row, keys)
                counts[outcome] += 1

        edge_document = json.loads((data_dir / "edge_cases.json").read_text(encoding="utf-8"))
        for case in edge_document["cases"]:
            row = {"case_id": case["case_id"], "payload": json.dumps(case, sort_keys=True), "dataset_id": DATASET_ID}
            outcome = _insert_or_verify(connection, "edge_case_scenarios", row, ["case_id"])
            counts[outcome] += 1

        if _settings_snapshot(connection) != before:
            raise RuntimeError("settings changed during operational seeding; transaction rolled back")
    return counts
