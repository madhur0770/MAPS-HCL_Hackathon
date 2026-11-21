"""Automated checks for Ujjwal Rail synthetic operations."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from policy_settings.database import DEFAULT_DB_PATH  # noqa: E402
from railway_data.generator import WEEKDAYS  # noqa: E402
from railway_data.seeder import seed_dataset  # noqa: E402
from railway_data.validator import validate_dataset  # noqa: E402


DATA_DIR = PROJECT_ROOT / "data" / "synthetic"


def load(name: str):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


class RailwayDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trains = load("trains.json")
        cls.stops = load("train_stops.json")
        cls.stations = load("stations.json")
        cls.seats = load("seats.json")
        cls.bookings = load("bookings.json")
        cls.travellers = load("booking_travellers.json")
        cls.edges = load("edge_cases.json")

    def test_train_running_days(self):
        self.assertTrue(all(set(train["runs_on"]) <= set(WEEKDAYS) for train in self.trains))
        train_map = {x["train_no"]: x for x in self.trains}
        for seat in self.seats:
            day = datetime.fromisoformat(seat["journey_date"]).strftime("%a")
            self.assertIn(day, train_map[seat["train_no"]]["runs_on"])

    def test_overnight_chronology(self):
        route = sorted((x for x in self.stops if x["train_no"] == "UJ1001"), key=lambda x: x["stop_order"])
        self.assertTrue(any(x["day_offset"] > 0 for x in route[1:]))
        events = []
        for stop in route:
            value = stop["departure"] or stop["arrival"]
            hour, minute = map(int, value.split(":"))
            events.append(stop["day_offset"] * 1440 + hour * 60 + minute)
        self.assertEqual(events, sorted(events))

    def test_station_alias_ambiguity(self):
        matches = [x["station_code"] for x in self.stations if "Anandpur" in x["other_names"]]
        self.assertEqual(set(matches), {"ANPR", "ANPN"})

    def test_database_foreign_keys(self):
        with sqlite3.connect(DEFAULT_DB_PATH) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_capacity_and_remaining_inventory(self):
        report = validate_dataset(DATA_DIR, db_path=DEFAULT_DB_PATH)
        results = {x["check"]: x["status"] for x in report["checks"]}
        self.assertEqual(results["capacity_limits"], "PASS")
        self.assertEqual(results["remaining_inventory_reconciled"], "PASS")

    def test_rac_waitlist_and_unavailable(self):
        lookup = {(x["train_no"], x["journey_date"], x["class"]): x for x in self.seats}
        self.assertGreater(lookup[("UJ1002", "2026-11-21", "AC2")]["rac"], 0)
        self.assertGreater(lookup[("UJ1001", "2026-11-21", "FP")]["waitlist"], 0)
        row = lookup[("UJ1003", "2026-11-21", "FP")]
        self.assertEqual((row["available"], row["rac"], row["waitlist"]), (0, 0, 0))

    def test_mixed_status_booking(self):
        statuses = {x["status"] for x in self.travellers if x["booking_id"] == "BKG0003"}
        self.assertEqual(statuses, {"CNF", "WL"})
        booking = next(x for x in self.bookings if x["booking_id"] == "BKG0003")
        self.assertEqual(booking["status"], "MIXED")

    def test_operator_cancelled_service(self):
        cancellation = load("service_cancellations.json")[0]
        affected = [x for x in self.bookings if x["status"] == "OPERATOR_CANCELLED"]
        self.assertTrue(affected)
        self.assertTrue(all((x["train_no"], x["journey_date"]) == (cancellation["train_no"], cancellation["journey_date"]) for x in affected))

    def test_passenger_without_booking(self):
        self.assertNotIn("P025", {x["passenger_id"] for x in self.bookings})

    def test_exact_cutoff(self):
        case = next(x for x in self.edges["cases"] if x["case_id"] == "EDGE-CUTOFF-EXACT")
        booking = next(x for x in self.bookings if x["booking_id"] == case["booking_id"])
        delta = datetime.fromisoformat(booking["boarding_datetime"]) - datetime.fromisoformat(case["requested_cancellation_at"])
        expected_hours = int(case["remaining_time"].split()[1])
        self.assertEqual(delta.total_seconds(), expected_hours * 3600)

    def test_one_minute_after_cutoff(self):
        case = next(x for x in self.edges["cases"] if x["case_id"] == "EDGE-CUTOFF-AFTER-ONE-MINUTE")
        booking = next(x for x in self.bookings if x["booking_id"] == case["booking_id"])
        delta = datetime.fromisoformat(booking["boarding_datetime"]) - datetime.fromisoformat(case["requested_cancellation_at"])
        hours, minutes = [int(part) for part in case["remaining_time"].split() if part.isdigit()]
        self.assertEqual(delta.total_seconds(), hours * 3600 + minutes * 60)

    def test_idempotent_seeding(self):
        first = seed_dataset(DATA_DIR, db_path=DEFAULT_DB_PATH)
        second = seed_dataset(DATA_DIR, db_path=DEFAULT_DB_PATH)
        self.assertEqual(first["inserted"], 0)
        self.assertEqual(second["inserted"], 0)
        self.assertEqual(first["verified"], second["verified"])

    def test_settings_preserved(self):
        with sqlite3.connect(DEFAULT_DB_PATH) as connection:
            before = connection.execute("SELECT * FROM settings ORDER BY name").fetchall()
            versions_before = connection.execute("SELECT * FROM setting_versions ORDER BY name, effective_from").fetchall()
        seed_dataset(DATA_DIR, db_path=DEFAULT_DB_PATH)
        with sqlite3.connect(DEFAULT_DB_PATH) as connection:
            after = connection.execute("SELECT * FROM settings ORDER BY name").fetchall()
            versions_after = connection.execute("SELECT * FROM setting_versions ORDER BY name, effective_from").fetchall()
        self.assertEqual(before, after)
        self.assertEqual(versions_before, versions_after)


if __name__ == "__main__":
    unittest.main()
