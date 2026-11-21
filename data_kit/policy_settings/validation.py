"""Consistency checks for the Ujjwal Rail settings database."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from .database import DEFAULT_DB_PATH, PROJECT_ROOT, connect
from .repository import get_setting, normalize_as_of
from .seed_data import reviewed_setting_seeds, verify_seed_sources
from .seeder import seed_database


SUPPORTED_CLASSES = ("fp", "ac2", "ac3", "ec", "sl", "cc")


def _logical_rows(db_path: Path | str) -> tuple[tuple[object, ...], ...]:
    with connect(db_path) as connection:
        settings = connection.execute(
            "SELECT name, value, source_doc FROM settings ORDER BY name"
        ).fetchall()
        versions = connection.execute(
            """
            SELECT name, value, source_doc, effective_from, effective_until,
                   precedence, applicability_event, value_type, unit, note
            FROM setting_versions
            ORDER BY name, effective_from, source_doc
            """
        ).fetchall()
    return tuple(tuple(row) for row in settings + versions)


def validate_database(
    db_path: Path | str = DEFAULT_DB_PATH,
    *,
    as_of: str | None = None,
    check_idempotency: bool = True,
) -> list[str]:
    """Return validation errors. An empty list means the database passed."""

    errors: list[str] = []
    timestamp = normalize_as_of(as_of)

    evidence_problems = verify_seed_sources(reviewed_setting_seeds())
    errors.extend(evidence_problems)

    with connect(db_path) as connection:
        empty_rows = connection.execute(
            """
            SELECT name FROM settings
            WHERE trim(name) = '' OR trim(value) = '' OR trim(source_doc) = ''
            """
        ).fetchall()
        if empty_rows:
            errors.append("settings contains empty name, value, or source_doc")

        version_empty_rows = connection.execute(
            """
            SELECT name FROM setting_versions
            WHERE trim(name) = '' OR trim(value) = '' OR trim(source_doc) = ''
            """
        ).fetchall()
        if version_empty_rows:
            errors.append("setting_versions contains empty required fields")

        source_docs = {
            row["source_doc"]
            for row in connection.execute(
                "SELECT DISTINCT source_doc FROM setting_versions"
            )
        }

        overlaps = connection.execute(
            """
            SELECT a.name, a.source_doc AS source_a, b.source_doc AS source_b
            FROM setting_versions a
            JOIN setting_versions b
              ON a.name = b.name
             AND (a.effective_from < b.effective_from OR
                  (a.effective_from = b.effective_from AND a.source_doc < b.source_doc))
             AND (a.effective_until IS NULL OR b.effective_from < a.effective_until)
             AND (b.effective_until IS NULL OR a.effective_from < b.effective_until)
            """
        ).fetchall()
        for row in overlaps:
            errors.append(
                f"overlapping versions for {row['name']}: {row['source_a']} and {row['source_b']}"
            )

        all_versions = connection.execute(
            "SELECT name, value, source_doc, unit FROM setting_versions"
        ).fetchall()
        current_rows = {
            row["name"]: (row["value"], row["source_doc"])
            for row in connection.execute(
                "SELECT name, value, source_doc FROM settings"
            )
        }

    declared_docs = {"SYSTEM-CONFIG"}
    for folder in ("rules", "circulars"):
        for path in (PROJECT_ROOT / "data" / "policies" / folder).glob("*.md"):
            content = path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("doc_id: "):
                    declared_docs.add(line.split(":", 1)[1].strip())
                    break
    missing_sources = sorted(source_docs - declared_docs)
    if missing_sources:
        errors.append(f"unknown source documents: {', '.join(missing_sources)}")

    for class_code in SUPPORTED_CLASSES:
        for prefix in ("cancel_fixed_charge_", "tatkal_supplement_"):
            name = prefix + class_code
            try:
                get_setting(name, "2026-11-01", db_path=db_path)
            except Exception as exc:  # validation should report all failures
                errors.append(f"missing class setting {name}: {exc}")

    expected_brackets = {
        "cancellation.band_a.lower_hours_exclusive": "48",
        "cancellation.band_b.lower_hours_exclusive": "12",
        "cancellation.band_b.upper_hours_inclusive": "48",
        "cancellation.band_c.lower_hours_exclusive": "4",
        "cancellation.band_c.upper_hours_inclusive": "12",
        "cancellation.band_d.lower_hours_exclusive": "0",
        "cancellation.band_d.upper_hours_inclusive": "4",
        "cancellation.band_e.upper_hours_inclusive": "0",
    }
    for name, expected in expected_brackets.items():
        try:
            actual = get_setting(name, "2026-11-01", db_path=db_path).value
            if actual != expected:
                errors.append(f"{name} is {actual}, expected {expected}")
        except Exception as exc:
            errors.append(f"invalid cancellation bracket {name}: {exc}")
    if not (48 > 12 > 4 > 0):
        errors.append("internal cancellation boundary definition is invalid")

    expected_versions = {
        ("cancel_fixed_charge_ac2", "2026-11-14"): ("240", "RUL-003"),
        ("cancel_fixed_charge_ac2", "2026-11-15"): ("260", "CIR-001"),
        ("cancel_fixed_charge_ac3", "2026-11-14"): ("200", "RUL-003"),
        ("cancel_fixed_charge_ac3", "2026-11-15"): ("220", "CIR-001"),
        ("tatkal_supplement_ac2", "2026-11-19"): ("400", "RUL-005"),
        ("tatkal_supplement_ac2", "2026-11-20"): ("450", "CIR-002"),
        ("tatkal_supplement_ac3", "2026-11-19"): ("300", "RUL-005"),
        ("tatkal_supplement_ac3", "2026-11-20"): ("330", "CIR-002"),
        ("excess_luggage_rate_per_started_kg", "2026-12-31"): ("30", "RUL-007"),
        ("excess_luggage_rate_per_started_kg", "2027-01-01"): ("35", "CIR-005"),
    }
    for (name, when), expected in expected_versions.items():
        try:
            setting = get_setting(name, when, db_path=db_path)
            actual = (setting.value, setting.source_doc)
            if actual != expected:
                errors.append(f"{name} at {when} is {actual}, expected {expected}")
        except Exception as exc:
            errors.append(f"cannot resolve {name} at {when}: {exc}")

    for row in all_versions:
        if row["unit"] in {
            "INR",
            "INR_per_started_kg",
            "percent",
            "hours",
            "minutes",
            "days",
            "business_days",
            "kg",
            "travellers",
            "changes",
            "years",
            "digits",
            "classes",
            "calendar_days",
            "pets",
            "km",
        }:
            try:
                value = Decimal(row["value"])
            except InvalidOperation:
                errors.append(f"non-numeric value for {row['name']}: {row['value']}")
                continue
            if value < 0:
                errors.append(f"negative value for {row['name']}: {value}")

    try:
        expiry = get_setting(
            "actions.pending_expiry_minutes", timestamp, db_path=db_path
        )
        if expiry.value != "10" or expiry.source_doc != "SYSTEM-CONFIG":
            errors.append("action expiry is not 10 minutes from SYSTEM-CONFIG")
    except Exception as exc:
        errors.append(f"action expiry is unavailable: {exc}")

    for name, stored in current_rows.items():
        try:
            resolved = get_setting(name, timestamp, db_path=db_path)
            if stored != (resolved.value, resolved.source_doc):
                errors.append(
                    f"current snapshot mismatch for {name}: {stored} vs "
                    f"{(resolved.value, resolved.source_doc)}"
                )
        except Exception as exc:
            errors.append(f"current snapshot cannot resolve {name}: {exc}")

    if check_idempotency:
        before = _logical_rows(db_path)
        seed_database(db_path, as_of=timestamp)
        middle = _logical_rows(db_path)
        seed_database(db_path, as_of=timestamp)
        after = _logical_rows(db_path)
        if before != middle or middle != after:
            errors.append("seeding is not idempotent")

    return errors
