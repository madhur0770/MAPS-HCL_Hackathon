"""Automated tests for policy setting history and precedence."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from policy_settings.repository import (
    SettingNotFoundError,
    get_setting,
    get_setting_decimal,
    get_setting_int,
)
from policy_settings.seeder import seed_database


class PolicySettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "settings.db"
        seed_database(self.db_path, as_of="2026-11-21T12:00:00+05:30")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _rows(self) -> tuple[tuple[object, ...], ...]:
        with sqlite3.connect(self.db_path) as connection:
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
        return tuple(settings + versions)

    def test_a_baseline_rule_before_amendment(self) -> None:
        setting = get_setting(
            "cancel_fixed_charge_ac2", "2026-11-14", db_path=self.db_path
        )
        self.assertEqual(setting.value, "240")
        self.assertEqual(setting.source_doc, "RUL-003")

    def test_b_effective_circular(self) -> None:
        setting = get_setting(
            "cancel_fixed_charge_ac2", "2026-11-15", db_path=self.db_path
        )
        self.assertEqual(setting.value, "260")
        self.assertEqual(setting.source_doc, "CIR-001")

    def test_c_future_circular_before_and_after(self) -> None:
        before = get_setting(
            "excess_luggage_rate_per_started_kg",
            "2026-12-31T23:59:59+05:30",
            db_path=self.db_path,
        )
        after = get_setting(
            "excess_luggage_rate_per_started_kg",
            "2027-01-01T00:00:00+05:30",
            db_path=self.db_path,
        )
        self.assertEqual((before.value, before.source_doc), ("30", "RUL-007"))
        self.assertEqual((after.value, after.source_doc), ("35", "CIR-005"))

    def test_d_unchanged_setting(self) -> None:
        before = get_setting(
            "cancel_fixed_charge_fp", "2026-11-01", db_path=self.db_path
        )
        after = get_setting(
            "cancel_fixed_charge_fp", "2027-02-01", db_path=self.db_path
        )
        self.assertEqual((before.value, before.source_doc), ("300", "RUL-003"))
        self.assertEqual((after.value, after.source_doc), ("300", "RUL-003"))

    def test_e_action_expiry(self) -> None:
        value, source = get_setting_int(
            "actions.pending_expiry_minutes", db_path=self.db_path
        )
        self.assertEqual(value, 10)
        self.assertEqual(source, "SYSTEM-CONFIG")

    def test_f_idempotent_seeding(self) -> None:
        before = self._rows()
        seed_database(self.db_path, as_of="2026-11-21T12:00:00+05:30")
        after_first = self._rows()
        seed_database(self.db_path, as_of="2026-11-21T12:00:00+05:30")
        after_second = self._rows()
        self.assertEqual(before, after_first)
        self.assertEqual(after_first, after_second)

    def test_g_invalid_setting(self) -> None:
        with self.assertRaises(SettingNotFoundError):
            get_setting("not.a.real.setting", db_path=self.db_path)

    def test_decimal_accessor_uses_decimal(self) -> None:
        value, source = get_setting_decimal(
            "tatkal_supplement_ac3", "2026-11-21", db_path=self.db_path
        )
        self.assertIsInstance(value, Decimal)
        self.assertEqual(value, Decimal("330"))
        self.assertEqual(source, "CIR-002")


if __name__ == "__main__":
    unittest.main()
