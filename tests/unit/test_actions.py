import datetime as dt
import os
from core import clock
from actions import manager as am
from tools import bookings as bk

T0 = clock.parse_dt("2026-11-21T10:00")


def setup_clock(monkeypatch):
    monkeypatch.setenv("DEMO_NOW", "2026-11-21T10:00:00+05:30")


def test_preview_changes_nothing(db, monkeypatch):
    setup_clock(monkeypatch)
    before = db.execute("SELECT status FROM bookings WHERE booking_id='BK1001'").fetchone()[0]
    p = am.propose_cancel(db, "P001", "BK1001", T0)
    assert p["ok"] and p["quote"]["total_refund"] == 1860
    assert db.execute("SELECT status FROM bookings WHERE booking_id='BK1001'").fetchone()[0] == before
    assert db.execute("SELECT count(*) FROM booking_travellers WHERE booking_id='BK1001' AND status='CAN'").fetchone()[0] == 0


def test_confirm_cancels_and_verifies(db, monkeypatch):
    setup_clock(monkeypatch)
    p = am.propose_cancel(db, "P001", "BK1001", T0)
    r = am.confirm_action(db, p["pending_action"]["action_id"], "P001")
    assert r["ok"] and r["status"] == "done" and r["verified"] and r["result"]["refund"] == 1860
    assert bk.get_booking(db, "BK1001", "P001")["status"] == "cancelled"


def test_confirm_twice_acts_once(db, monkeypatch):
    setup_clock(monkeypatch)
    avail0 = db.execute("SELECT available FROM seats WHERE train_no='12123' AND journey_date='2026-11-24' AND class='3A'").fetchone()[0]
    aid = am.propose_cancel(db, "P001", "BK1001", T0)["pending_action"]["action_id"]
    am.confirm_action(db, aid, "P001")
    r2 = am.confirm_action(db, aid, "P001")
    assert r2["ok"] and r2["already"]
    avail1 = db.execute("SELECT available FROM seats WHERE train_no='12123' AND journey_date='2026-11-24' AND class='3A'").fetchone()[0]
    assert avail1 == avail0 + 1
    assert db.execute("SELECT refunded FROM bookings WHERE booking_id='BK1001'").fetchone()[0] == 1860


def test_only_owner_can_confirm(db, monkeypatch):
    setup_clock(monkeypatch)
    aid = am.propose_cancel(db, "P001", "BK1001", T0)["pending_action"]["action_id"]
    r = am.confirm_action(db, aid, "P002")
    assert not r["ok"] and r["reason"] == "not_found"
    assert bk.get_booking(db, "BK1001", "P001")["status"] == "confirmed"


def test_cannot_propose_on_someone_elses_booking(db):
    assert am.propose_cancel(db, "P002", "BK1001", T0)["reason"] == "not_found"


def test_expiry(db, monkeypatch):
    setup_clock(monkeypatch)
    aid = am.propose_cancel(db, "P001", "BK1001", T0)["pending_action"]["action_id"]
    monkeypatch.setenv("DEMO_NOW", "2026-11-21T10:11:00+05:30")   # 11 minutes later
    r = am.confirm_action(db, aid, "P001")
    assert not r["ok"] and r["reason"] == "expired"
    assert bk.get_booking(db, "BK1001", "P001")["status"] == "confirmed"


def test_quote_changed_between_preview_and_confirm(db, monkeypatch):
    setup_clock(monkeypatch)
    as_of = clock.parse_dt("2026-11-22T14:59:00")      # 51h01m before 18:00 on 24th -> FLAT
    monkeypatch.setenv("DEMO_NOW", "2026-11-22T14:59:00+05:30")
    aid = am.propose_cancel(db, "P001", "BK1001", as_of)["pending_action"]["action_id"]
    # real time moves on past the 48 h line within the 10-minute window
    monkeypatch.setenv("DEMO_NOW", "2026-11-22T18:02:00+05:30")
    r = am.confirm_action(db, aid, "P001")
    assert not r["ok"]
    assert r["reason"] in ("quote_changed", "expired")
    assert bk.get_booking(db, "BK1001", "P001")["status"] == "confirmed"


def test_cancel_one_traveller_keeps_booking_active(db, monkeypatch):
    setup_clock(monkeypatch)
    ids = [r[0] for r in db.execute("SELECT traveller_id FROM booking_travellers WHERE booking_id='BK1003' ORDER BY traveller_id")]
    aid = am.propose_cancel(db, "P001", "BK1003", T0, traveller_ids=[ids[1]])["pending_action"]["action_id"]
    r = am.confirm_action(db, aid, "P001")
    assert r["ok"] and r["result"]["new_status"] == "confirmed"
    assert db.execute("SELECT count(*) FROM booking_travellers WHERE booking_id='BK1003' AND status='CAN'").fetchone()[0] == 1


def test_change_boarding_ok_then_only_once(db, monkeypatch):
    setup_clock(monkeypatch)
    p = am.propose_change_boarding(db, "P001", "BK1003", "BPL", T0)      # NK -> BPL on 12123, journey 27 Nov
    assert p["ok"]
    assert bk.get_booking(db, "BK1003", "P001")["from_code"] == "NK"     # preview changed nothing
    r = am.confirm_action(db, p["pending_action"]["action_id"], "P001")
    assert r["ok"] and r["verified"] and bk.get_booking(db, "BK1003", "P001")["from_code"] == "BPL"
    assert am.propose_change_boarding(db, "P001", "BK1003", "BPL", T0)["reason"] in ("already_changed", "bad_station")


def test_change_boarding_bad_station_and_cutoff(db, monkeypatch):
    setup_clock(monkeypatch)
    assert am.propose_change_boarding(db, "P001", "BK1001", "CSMT", T0)["reason"] == "bad_station"   # CSMT is not on this train
    # BK1001 departs 24 Nov 18:00; cut-off is 24h -> 23 Nov 18:00. Ask at 23 Nov 19:00
    late = am.propose_change_boarding(db, "P001", "BK1001", "BPL", clock.parse_dt("2026-11-23T19:00"))
    assert late["reason"] == "too_late" and late["hours"] == 24
    ok = am.propose_change_boarding(db, "P001", "BK1001", "BPL", clock.parse_dt("2026-11-23T17:59"))
    assert ok["ok"]


def test_cutoff_is_12h_after_circular(db, monkeypatch):
    setup_clock(monkeypatch)
    db.execute("UPDATE bookings SET journey_date='2026-12-05' WHERE booking_id='BK1001'")
    # departure 5 Dec 18:00; new cut-off 12h -> 06:00. Ask 5 Dec 05:00 -> allowed under the new rule
    ok = am.propose_change_boarding(db, "P001", "BK1001", "BPL", clock.parse_dt("2026-12-05T05:00"))
    assert ok["ok"] and ok["preview"]["hours"] == 12 and ok["preview"]["source"]["doc_id"] == "CIR-2026-09"


def test_book_flow_assigns_status_and_updates_seats(db, monkeypatch):
    setup_clock(monkeypatch)
    trs = [{"name": "Test One", "age": 30}, {"name": "Kid Two", "age": 8}]
    p = am.propose_book(db, "P001", "12123", "2026-11-24", "PUNE", "NGP", "3A", trs, T0)
    assert p["ok"] and p["preview"]["total"] == 2040 + 1020 and p["preview"]["lines"][0]["status"] == "CNF"
    assert db.execute("SELECT count(*) FROM bookings").fetchone()[0] == 50   # preview did not book
    r = am.confirm_action(db, p["pending_action"]["action_id"], "P001")
    assert r["ok"] and r["verified"]
    assert db.execute("SELECT available FROM seats WHERE train_no='12123' AND journey_date='2026-11-24' AND class='3A'").fetchone()[0] == 10


def test_book_full_train_goes_waitlist_and_regret(db, monkeypatch):
    setup_clock(monkeypatch)
    p = am.propose_book(db, "P001", "12123", "2026-11-25", "PUNE", "NGP", "SL", [{"name": "A B", "age": 30}], T0)
    assert p["ok"] and p["preview"]["lines"][0]["status"] == "WL"
    db.execute("UPDATE seats SET waitlist=wl_capacity WHERE train_no='12123' AND journey_date='2026-11-25' AND class='SL'")
    assert am.propose_book(db, "P001", "12123", "2026-11-25", "PUNE", "NGP", "SL", [{"name": "A B", "age": 30}], T0)["reason"] == "regret"
