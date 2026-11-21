"""SQLite schema. The table and column names listed in the brief are kept exactly; extra columns and
extra tables (settings_history, documents, sessions, handoffs, audit) are ours."""
import os
import sqlite3

from core import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS stations(
  station_code TEXT PRIMARY KEY, name TEXT, other_names TEXT, city TEXT);
CREATE TABLE IF NOT EXISTS trains(
  train_no TEXT PRIMARY KEY, name TEXT, runs_on TEXT, classes TEXT);
CREATE TABLE IF NOT EXISTS train_stops(
  train_no TEXT, station_code TEXT, stop_order INTEGER, arrival TEXT, departure TEXT,
  day_offset INTEGER, km INTEGER DEFAULT 0, PRIMARY KEY(train_no, stop_order));
CREATE TABLE IF NOT EXISTS fares(
  train_no TEXT, class TEXT, from_code TEXT, to_code TEXT, fare INTEGER,
  PRIMARY KEY(train_no, class, from_code, to_code));
CREATE TABLE IF NOT EXISTS seats(
  train_no TEXT, journey_date TEXT, class TEXT, available INTEGER, rac INTEGER, waitlist INTEGER,
  capacity INTEGER DEFAULT 0, rac_capacity INTEGER DEFAULT 0, wl_capacity INTEGER DEFAULT 0,
  PRIMARY KEY(train_no, journey_date, class));
CREATE TABLE IF NOT EXISTS passengers(
  passenger_id TEXT PRIMARY KEY, name TEXT, phone_last4 TEXT, preferred_language TEXT, home_city TEXT);
CREATE TABLE IF NOT EXISTS bookings(
  booking_id TEXT PRIMARY KEY, passenger_id TEXT, train_no TEXT, journey_date TEXT, from_code TEXT,
  to_code TEXT, class TEXT, amount_paid INTEGER, status TEXT, booked_at TEXT,
  tatkal INTEGER DEFAULT 0, refunded INTEGER DEFAULT 0,
  boarding_datetime TEXT, cancelled_at TEXT, cancellation_type TEXT);
CREATE TABLE IF NOT EXISTS booking_travellers(
  traveller_id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id TEXT, traveller_name TEXT, age INTEGER,
  status TEXT, coach TEXT, berth TEXT, fare_paid INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS service_cancellations(
  train_no TEXT, journey_date TEXT, reason TEXT, announced_at TEXT, PRIMARY KEY(train_no, journey_date));
CREATE TABLE IF NOT EXISTS actions(
  action_id TEXT PRIMARY KEY, passenger_id TEXT, booking_id TEXT, action_type TEXT, status TEXT,
  created_at TEXT, expires_at TEXT, result TEXT, payload TEXT, clock_offset REAL DEFAULT 0,
  preview TEXT, trace_id TEXT);
CREATE TABLE IF NOT EXISTS settings(name TEXT PRIMARY KEY, value TEXT, source_doc TEXT);
CREATE TABLE IF NOT EXISTS settings_history(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, value TEXT, effective_from TEXT,
  source_doc TEXT, section TEXT DEFAULT '', extracted INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS documents(
  doc_id TEXT PRIMARY KEY, doc_type TEXT, title TEXT, topic TEXT, effective_from TEXT,
  authority INTEGER, supersedes TEXT, language TEXT, text TEXT, added_at TEXT);
CREATE TABLE IF NOT EXISTS sessions(
  session_id TEXT PRIMARY KEY, passenger_id TEXT, slots TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS handoffs(
  handoff_id TEXT PRIMARY KEY, passenger_id TEXT, booking_id TEXT, desk TEXT, reason TEXT,
  summary TEXT, status TEXT, created_at TEXT, trace_id TEXT);
CREATE TABLE IF NOT EXISTS audit(
  trace_id TEXT PRIMARY KEY, created_at TEXT, passenger_id TEXT, session_id TEXT, record TEXT);
CREATE INDEX IF NOT EXISTS ix_bookings_p ON bookings(passenger_id);
CREATE INDEX IF NOT EXISTS ix_trav_b ON booking_travellers(booking_id);
CREATE INDEX IF NOT EXISTS ix_hist_n ON settings_history(name);
"""

TABLES_FROM_BRIEF = ["stations", "trains", "train_stops", "fares", "seats", "passengers", "bookings",
                     "booking_travellers", "actions", "settings"]


def connect(path: str = None) -> sqlite3.Connection:
    path = path or config.db_path()
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    db = sqlite3.connect(path, check_same_thread=False, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=OFF")
    if path != ":memory:":
        db.execute("PRAGMA journal_mode=WAL")
    return db


def init_db(db: sqlite3.Connection):
    db.executescript(SCHEMA)
    db.commit()
