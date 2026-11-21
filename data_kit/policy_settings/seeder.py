"""Idempotent database seeding and current-snapshot refresh."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

from .database import DEFAULT_DB_PATH, connect, initialize_database
from .repository import normalize_as_of
from .seed_data import SettingSeed, reviewed_setting_seeds, verify_seed_sources


class SeedValidationError(RuntimeError):
    """Raised when reviewed mappings or version intervals are invalid."""


def build_version_rows(seeds: list[SettingSeed]) -> list[tuple[SettingSeed, str | None]]:
    """Build non-overlapping half-open intervals for every setting name."""

    grouped: dict[str, list[SettingSeed]] = defaultdict(list)
    for seed in seeds:
        grouped[seed.name].append(seed)

    rows: list[tuple[SettingSeed, str | None]] = []
    for name, versions in grouped.items():
        versions.sort(key=lambda item: (item.effective_from, item.precedence, item.source_doc))
        seen: set[str] = set()
        for index, version in enumerate(versions):
            if version.effective_from in seen:
                raise SeedValidationError(
                    f"conflicting versions for {name!r} at {version.effective_from}"
                )
            seen.add(version.effective_from)
            effective_until = (
                versions[index + 1].effective_from if index + 1 < len(versions) else None
            )
            rows.append((version, effective_until))
    return rows


def seed_database(
    db_path: Path | str = DEFAULT_DB_PATH,
    *,
    as_of: datetime | date | str | None = None,
) -> dict[str, int | str]:
    """Seed all reviewed versions and refresh the current settings snapshot."""

    initialize_database(db_path)
    seeds = reviewed_setting_seeds()
    problems = verify_seed_sources(seeds)
    if problems:
        raise SeedValidationError("\n".join(problems))
    version_rows = build_version_rows(seeds)
    managed_names = sorted({seed.name for seed in seeds})
    timestamp = normalize_as_of(as_of)

    with connect(db_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        for seed, effective_until in version_rows:
            connection.execute(
                """
                INSERT INTO setting_versions (
                    name, value, source_doc, effective_from, effective_until,
                    precedence, applicability_event, value_type, unit, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name, effective_from, source_doc) DO UPDATE SET
                    value = excluded.value,
                    effective_until = excluded.effective_until,
                    precedence = excluded.precedence,
                    applicability_event = excluded.applicability_event,
                    value_type = excluded.value_type,
                    unit = excluded.unit,
                    note = excluded.note
                """,
                (
                    seed.name,
                    seed.value,
                    seed.source_doc,
                    seed.effective_from,
                    effective_until,
                    seed.precedence,
                    seed.applicability_event,
                    seed.value_type,
                    seed.unit,
                    seed.note,
                ),
            )

        placeholders = ",".join("?" for _ in managed_names)
        connection.execute(
            f"DELETE FROM settings WHERE name IN ({placeholders})", managed_names
        )
        for name in managed_names:
            rows = connection.execute(
                """
                SELECT value, source_doc
                FROM setting_versions
                WHERE name = ?
                  AND effective_from <= ?
                  AND (effective_until IS NULL OR ? < effective_until)
                ORDER BY precedence DESC, effective_from DESC
                """,
                (name, timestamp, timestamp),
            ).fetchall()
            if len(rows) != 1:
                raise SeedValidationError(
                    f"expected one current version for {name!r} at {timestamp}; found {len(rows)}"
                )
            connection.execute(
                "INSERT INTO settings(name, value, source_doc) VALUES (?, ?, ?)",
                (name, rows[0]["value"], rows[0]["source_doc"]),
            )

    return {
        "settings": len(managed_names),
        "versions": len(version_rows),
        "as_of": timestamp,
    }
