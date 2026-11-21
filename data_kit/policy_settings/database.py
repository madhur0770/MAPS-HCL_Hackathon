"""Database schema and connection helpers for policy settings."""

from __future__ import annotations

import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "ujjwal_rail.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    name TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    source_doc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS setting_versions (
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    source_doc TEXT NOT NULL,
    effective_from TEXT NOT NULL,
    effective_until TEXT,
    precedence INTEGER NOT NULL DEFAULT 0,
    applicability_event TEXT NOT NULL,
    value_type TEXT NOT NULL,
    unit TEXT,
    note TEXT,
    PRIMARY KEY (name, effective_from, source_doc),
    CHECK (effective_until IS NULL OR effective_until > effective_from)
);

CREATE INDEX IF NOT EXISTS idx_setting_versions_lookup
ON setting_versions (name, effective_from, effective_until, precedence);
"""


def connect(db_path: Path | str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Open a configured SQLite connection without modifying existing rows."""

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: Path | str = DEFAULT_DB_PATH) -> None:
    """Create required tables and indexes. Safe to run repeatedly."""

    with connect(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
