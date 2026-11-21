"""Non-destructive SQLite schema for synthetic Ujjwal Rail operations."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from policy_settings.database import DEFAULT_DB_PATH


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS synthetic_datasets (
    dataset_id TEXT PRIMARY KEY,
    reference_date TEXT NOT NULL,
    random_seed INTEGER NOT NULL,
    generated_at TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stations (
    station_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    other_names TEXT NOT NULL,
    city TEXT NOT NULL,
    dataset_id TEXT
);

CREATE TABLE IF NOT EXISTS trains (
    train_no TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    runs_on TEXT NOT NULL,
    classes TEXT NOT NULL,
    dataset_id TEXT
);

CREATE TABLE IF NOT EXISTS train_stops (
    train_no TEXT NOT NULL,
    station_code TEXT NOT NULL,
    stop_order INTEGER NOT NULL CHECK (stop_order > 0),
    arrival TEXT,
    departure TEXT,
    day_offset INTEGER NOT NULL CHECK (day_offset >= 0),
    dataset_id TEXT,
    PRIMARY KEY (train_no, stop_order),
    UNIQUE (train_no, station_code),
    FOREIGN KEY (train_no) REFERENCES trains(train_no),
    FOREIGN KEY (station_code) REFERENCES stations(station_code)
);

CREATE TABLE IF NOT EXISTS train_capacities (
    train_no TEXT NOT NULL,
    class TEXT NOT NULL,
    confirmed_capacity INTEGER NOT NULL CHECK (confirmed_capacity >= 0),
    rac_capacity INTEGER NOT NULL CHECK (rac_capacity >= 0),
    waitlist_capacity INTEGER NOT NULL CHECK (waitlist_capacity >= 0),
    dataset_id TEXT,
    PRIMARY KEY (train_no, class),
    FOREIGN KEY (train_no) REFERENCES trains(train_no)
);

CREATE TABLE IF NOT EXISTS fares (
    train_no TEXT NOT NULL,
    class TEXT NOT NULL,
    from_code TEXT NOT NULL,
    to_code TEXT NOT NULL,
    fare INTEGER NOT NULL CHECK (fare > 0),
    dataset_id TEXT,
    PRIMARY KEY (train_no, class, from_code, to_code),
    FOREIGN KEY (train_no) REFERENCES trains(train_no),
    FOREIGN KEY (from_code) REFERENCES stations(station_code),
    FOREIGN KEY (to_code) REFERENCES stations(station_code)
);

CREATE TABLE IF NOT EXISTS train_service_cancellations (
    train_no TEXT NOT NULL,
    journey_date TEXT NOT NULL,
    reason TEXT NOT NULL,
    announced_at TEXT NOT NULL,
    dataset_id TEXT,
    PRIMARY KEY (train_no, journey_date),
    FOREIGN KEY (train_no) REFERENCES trains(train_no)
);

CREATE TABLE IF NOT EXISTS seats (
    train_no TEXT NOT NULL,
    journey_date TEXT NOT NULL,
    class TEXT NOT NULL,
    available INTEGER NOT NULL CHECK (available >= 0),
    rac INTEGER NOT NULL CHECK (rac >= 0),
    waitlist INTEGER NOT NULL CHECK (waitlist >= 0),
    confirmed_capacity INTEGER NOT NULL CHECK (confirmed_capacity >= 0),
    rac_capacity INTEGER NOT NULL CHECK (rac_capacity >= 0),
    waitlist_capacity INTEGER NOT NULL CHECK (waitlist_capacity >= 0),
    service_status TEXT NOT NULL CHECK (service_status IN ('SCHEDULED', 'CANCELLED')),
    dataset_id TEXT,
    PRIMARY KEY (train_no, journey_date, class),
    FOREIGN KEY (train_no, class) REFERENCES train_capacities(train_no, class)
);

CREATE TABLE IF NOT EXISTS passengers (
    passenger_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone_last4 TEXT NOT NULL CHECK (length(phone_last4) = 4),
    preferred_language TEXT NOT NULL,
    home_city TEXT NOT NULL,
    dataset_id TEXT
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id TEXT PRIMARY KEY,
    passenger_id TEXT NOT NULL,
    train_no TEXT NOT NULL,
    journey_date TEXT NOT NULL,
    from_code TEXT NOT NULL,
    to_code TEXT NOT NULL,
    class TEXT NOT NULL,
    amount_paid INTEGER NOT NULL CHECK (amount_paid > 0),
    status TEXT NOT NULL CHECK (status IN ('CONFIRMED','RAC','WAITLISTED','MIXED','CANCELLED','OPERATOR_CANCELLED')),
    booked_at TEXT NOT NULL,
    boarding_datetime TEXT NOT NULL,
    cancelled_at TEXT,
    cancellation_type TEXT CHECK (cancellation_type IN ('PASSENGER','OPERATOR') OR cancellation_type IS NULL),
    dataset_id TEXT,
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
    FOREIGN KEY (train_no) REFERENCES trains(train_no),
    FOREIGN KEY (from_code) REFERENCES stations(station_code),
    FOREIGN KEY (to_code) REFERENCES stations(station_code),
    FOREIGN KEY (train_no, class) REFERENCES train_capacities(train_no, class)
);

CREATE TABLE IF NOT EXISTS booking_travellers (
    traveller_id TEXT PRIMARY KEY,
    booking_id TEXT NOT NULL,
    traveller_name TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age > 0),
    status TEXT NOT NULL CHECK (status IN ('CNF','RAC','WL')),
    coach TEXT,
    berth TEXT,
    dataset_id TEXT,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS actions (
    action_id TEXT PRIMARY KEY,
    passenger_id TEXT NOT NULL,
    booking_id TEXT,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    result TEXT,
    dataset_id TEXT,
    FOREIGN KEY (passenger_id) REFERENCES passengers(passenger_id),
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);

CREATE TABLE IF NOT EXISTS edge_case_scenarios (
    case_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    dataset_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_stops_station ON train_stops(station_code);
CREATE INDEX IF NOT EXISTS idx_seats_date ON seats(journey_date, train_no);
CREATE INDEX IF NOT EXISTS idx_bookings_passenger ON bookings(passenger_id, journey_date);
CREATE INDEX IF NOT EXISTS idx_bookings_train ON bookings(train_no, journey_date);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_travellers_booking ON booking_travellers(booking_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON actions(status, expires_at);
"""


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_schema(db_path: Path = DEFAULT_DB_PATH) -> None:
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)
