from core import clock
from actions import manager as am
from tools import bookings as bk

T0 = clock.parse_dt("2026-11-21T10:00")
ONE = [{"name": "Test One", "age": 30}]


def now(monkeypatch, iso="2026-11-21T10:00:00+05:30"):
    monkeypatch.setenv("DEMO_NOW", iso)


def status(db, ref):
    return db.execute("SELECT status FROM bookings WHERE booking_id=?", (ref,)).fetchone()[0]


def test_preview_changes_nothing(db, monkeypatch):
    now(monkeypatch)
    before = status(db, "BKG0001")
    p = am.propose_cancel(db, "P001", "BKG0001", T0)
    assert p["ok"] and p["quote"]["total_refund"] == 280200       # 3062.50 - 260 fixed charge = 2802.50 -> 2802
    assert status(db, "BKG0001") == before


def test_confirm_cancels_and_verifies(db, monkeypatch):
    now(monkeypatch)
    aid = am.propose_cancel(db, "P001", "BKG0001", T0)["pending_action"]["action_id"]
    r = am.confirm_action(db, aid, "P001")
    assert r["ok"] and r["status"] == "done" and r["verified"] and r["result"]["refund"] == 280200
    assert status(db, "BKG0001") == "CANCELLED"


def test_confirm_twice_acts_once(db, monkeypatch):
    now(monkeypatch)
    seat = "SELECT available FROM seats WHERE train_no='UJ1006' AND journey_date='2026-11-25' AND class='AC2'"
    a0 = db.execute(seat).fetchone()[0]
    aid = am.propose_cancel(db, "P001", "BKG0001", T0)["pending_action"]["action_id"]
    am.confirm_action(db, aid, "P001")
    r2 = am.confirm_action(db, aid, "P001")
    assert r2["ok"] and r2["already"]
    assert db.execute(seat).fetchone()[0] == a0 + 1
    assert db.execute("SELECT refunded FROM bookings WHERE booking_id='BKG0001'").fetchone()[0] == 280200


def test_only_owner_can_confirm(db, monkeypatch):
    now(monkeypatch)
    aid = am.propose_cancel(db, "P001", "BKG0001", T0)["pending_action"]["action_id"]
    r = am.confirm_action(db, aid, "P002")
    assert not r["ok"] and r["reason"] == "not_found"
    assert status(db, "BKG0001") != "CANCELLED"


def test_other_persons_booking_looks_missing(db):
    assert am.propose_cancel(db, "P002", "BKG0001", T0)["reason"] == "not_found"
    assert am.propose_cancel(db, "P001", "UR-48213", T0)["reason"] == "not_found"


def test_expiry_after_ten_minutes(db, monkeypatch):
    now(monkeypatch)
    aid = am.propose_cancel(db, "P001", "BKG0001", T0)["pending_action"]["action_id"]
    now(monkeypatch, "2026-11-21T10:11:00+05:30")
    r = am.confirm_action(db, aid, "P001")
    assert not r["ok"] and r["reason"] == "expired"
    assert status(db, "BKG0001") != "CANCELLED"


def test_quote_changed_between_preview_and_confirm(db, monkeypatch):
    # preview 48h01m before departure (band A), confirm after the 48h line (band B)
    now(monkeypatch, "2026-11-23T09:14:00+05:30")
    aid = am.propose_cancel(db, "P001", "BKG0001", clock.parse_dt("2026-11-23T09:14"))["pending_action"]["action_id"]
    now(monkeypatch, "2026-11-23T09:16:00+05:30")
    r = am.confirm_action(db, aid, "P001")
    assert not r["ok"] and r["reason"] in ("quote_changed", "expired")
    assert status(db, "BKG0001") != "CANCELLED"


def test_operator_cancelled_needs_no_cancel(db):
    r = am.propose_cancel(db, "P008", "BKG0008", T0)
    assert not r["ok"] and r["reason"] == "operator_cancelled"


def test_boarding_change_exactly_six_hours_is_too_late(db):
    assert am.propose_change_boarding(db, "P001", "BKG0001", "SURY", clock.parse_dt("2026-11-25T03:14"))["ok"]
    late = am.propose_change_boarding(db, "P001", "BKG0001", "SURY", clock.parse_dt("2026-11-25T03:15"))
    assert late["reason"] == "too_late" and late["hours"] == 6


def test_boarding_change_rules(db, monkeypatch):
    now(monkeypatch)
    assert am.propose_change_boarding(db, "P001", "BKG0001", "ANPR", T0)["reason"] == "bad_station"   # not on this train
    assert am.propose_change_boarding(db, "P001", "BKG0001", "CHET", T0)["reason"] == "bad_station"   # destination itself
    assert am.propose_change_boarding(db, "P003", "BKG0003", "ANPN", T0)["reason"] == "has_waitlisted"


def test_boarding_change_confirm_then_only_once(db, monkeypatch):
    now(monkeypatch)
    p = am.propose_change_boarding(db, "P001", "BKG0001", "SURY", T0)
    assert bk.get_booking(db, "BKG0001", "P001")["from_code"] == "ARUN"       # preview changed nothing
    r = am.confirm_action(db, p["pending_action"]["action_id"], "P001")
    assert r["ok"] and r["verified"] and bk.get_booking(db, "BKG0001", "P001")["from_code"] == "SURY"
    assert am.propose_change_boarding(db, "P001", "BKG0001", "KAVA", T0)["reason"] == "already_changed"


def test_book_flow_confirmed_and_reference(db, monkeypatch):
    now(monkeypatch)
    trs = [{"name": "Test One", "age": 30}, {"name": "Kid Two", "age": 5}]
    n0 = db.execute("SELECT count(*) FROM bookings").fetchone()[0]
    p = am.propose_book(db, "P001", "UJ1006", "2026-11-22", "ANPN", "CHET", "AC2", trs, T0)
    assert p["ok"] and p["preview"]["total"] == 367500 and p["preview"]["lines"][0]["status"] == "CNF"
    assert db.execute("SELECT count(*) FROM bookings").fetchone()[0] == n0        # preview did not book
    r = am.confirm_action(db, p["pending_action"]["action_id"], "P001")
    assert r["ok"] and r["verified"]
    ref = db.execute("SELECT booking_id FROM bookings ORDER BY rowid DESC LIMIT 1").fetchone()[0]
    assert ref.startswith("UR-") and len(ref) == 11
    assert db.execute("SELECT available FROM seats WHERE train_no='UJ1006' AND journey_date='2026-11-22' AND class='AC2'").fetchone()[0] == 22


def test_book_waitlist_and_regret(db, monkeypatch):
    now(monkeypatch)
    p = am.propose_book(db, "P001", "UJ1001", "2026-11-21", "ANPR", "ANPN", "FP", ONE, T0)
    assert p["ok"] and p["preview"]["lines"][0]["status"] == "WL"
    assert am.propose_book(db, "P001", "UJ1003", "2026-11-21", "ANPR", "ANPN", "FP", ONE, T0)["reason"] == "not_available"


def test_booking_closes_twenty_minutes_before_departure(db, monkeypatch):
    now(monkeypatch)
    ok = am.propose_book(db, "P001", "UJ1001", "2026-11-21", "ANPR", "ANPN", "FP", ONE, clock.parse_dt("2026-11-21T23:19"))
    assert ok["ok"]
    late = am.propose_book(db, "P001", "UJ1001", "2026-11-21", "ANPR", "ANPN", "FP", ONE, clock.parse_dt("2026-11-21T23:21"))
    assert late["reason"] == "departed" and late["minutes"] == 20


def test_max_six_travellers(db, monkeypatch):
    now(monkeypatch)
    seven = [{"name": "P %d" % i, "age": 30} for i in range(7)]
    assert not am.propose_book(db, "P001", "UJ1006", "2026-11-22", "ANPN", "CHET", "AC2", seven, T0)["ok"]
