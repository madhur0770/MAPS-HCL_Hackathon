"""Read effective policy settings from SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

from .database import DEFAULT_DB_PATH, connect


IST = timezone(timedelta(hours=5, minutes=30))


class SettingNotFoundError(KeyError):
    """Raised when no version of a requested setting applies."""


class AmbiguousSettingError(RuntimeError):
    """Raised when overlapping versions make a setting ambiguous."""


class InvalidSettingValueError(ValueError):
    """Raised when a value cannot be converted to the requested type."""


@dataclass(frozen=True)
class PolicySetting:
    name: str
    value: str
    source_doc: str
    effective_from: str
    effective_until: str | None
    applicability_event: str
    value_type: str
    unit: str | None


def normalize_as_of(as_of: datetime | date | str | None) -> str:
    """Normalize supported time inputs to an ISO timestamp in Asia/Kolkata."""

    if as_of is None:
        value = datetime.now(IST)
    elif isinstance(as_of, datetime):
        value = as_of
    elif isinstance(as_of, date):
        value = datetime.combine(as_of, time.min, tzinfo=IST)
    elif isinstance(as_of, str):
        text = as_of.strip()
        if not text:
            raise ValueError("as_of cannot be empty")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            if "T" not in text and " " not in text:
                value = datetime.combine(date.fromisoformat(text), time.min, tzinfo=IST)
            else:
                value = datetime.fromisoformat(text.replace(" ", "T", 1))
        except ValueError as exc:
            raise ValueError(f"invalid as_of value: {as_of!r}") from exc
    else:
        raise TypeError("as_of must be None, date, datetime, or ISO string")

    if value.tzinfo is None:
        value = value.replace(tzinfo=IST)
    return value.astimezone(IST).isoformat(timespec="seconds")


def _row_to_setting(row: object) -> PolicySetting:
    return PolicySetting(
        name=row["name"],
        value=row["value"],
        source_doc=row["source_doc"],
        effective_from=row["effective_from"],
        effective_until=row["effective_until"],
        applicability_event=row["applicability_event"],
        value_type=row["value_type"],
        unit=row["unit"],
    )


def get_setting(
    name: str,
    as_of: datetime | date | str | None = None,
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> PolicySetting:
    """Return the single setting version effective at ``as_of``.

    Validity intervals are half-open: effective_from is inclusive and
    effective_until is exclusive.
    """

    if not name or not name.strip():
        raise ValueError("setting name cannot be empty")
    timestamp = normalize_as_of(as_of)
    query = """
        SELECT name, value, source_doc, effective_from, effective_until,
               applicability_event, value_type, unit
        FROM setting_versions
        WHERE name = ?
          AND effective_from <= ?
          AND (effective_until IS NULL OR ? < effective_until)
        ORDER BY precedence DESC, effective_from DESC
    """
    with connect(db_path) as connection:
        rows = connection.execute(query, (name, timestamp, timestamp)).fetchall()
    if not rows:
        raise SettingNotFoundError(
            f"no value for setting {name!r} at {timestamp}"
        )
    if len(rows) > 1:
        sources = ", ".join(row["source_doc"] for row in rows)
        raise AmbiguousSettingError(
            f"multiple values for setting {name!r} at {timestamp}: {sources}"
        )
    return _row_to_setting(rows[0])


def get_setting_decimal(
    name: str,
    as_of: datetime | date | str | None = None,
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> tuple[Decimal, str]:
    """Return a setting as Decimal together with its source document."""

    setting = get_setting(name, as_of, db_path=db_path)
    try:
        value = Decimal(setting.value)
    except InvalidOperation as exc:
        raise InvalidSettingValueError(
            f"setting {name!r} value {setting.value!r} is not decimal"
        ) from exc
    return value, setting.source_doc


def get_setting_int(
    name: str,
    as_of: datetime | date | str | None = None,
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> tuple[int, str]:
    """Return an integral setting together with its source document."""

    decimal_value, source_doc = get_setting_decimal(name, as_of, db_path=db_path)
    if decimal_value != decimal_value.to_integral_value():
        raise InvalidSettingValueError(
            f"setting {name!r} value {decimal_value} is not an integer"
        )
    return int(decimal_value), source_doc


def list_settings(
    as_of: datetime | date | str | None = None,
    *,
    db_path: Path | str = DEFAULT_DB_PATH,
) -> list[PolicySetting]:
    """Return every unambiguous setting effective at ``as_of`` by name."""

    with connect(db_path) as connection:
        names: Iterable[str] = [
            row["name"]
            for row in connection.execute(
                "SELECT DISTINCT name FROM setting_versions ORDER BY name"
            )
        ]
    return [get_setting(name, as_of, db_path=db_path) for name in names]
