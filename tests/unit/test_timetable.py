import datetime as dt
from core import clock
from tools import timetable as tt, seats, deadlines


def test_station_aliases(db):
    assert tt.resolve_station(db, "Bombay") == "CSMT"
    assert tt.resolve_station(db, "CST") == "CSMT"
    assert tt.resolve_station(db, "मुंबई") == "CSMT"
    assert tt.resolve_station(db, "Banaras") == "BSB"
    assert tt.find_stations_in(db, "pune se nagpur kal") == ["PUNE", "NGP"]
    assert tt.find_stations_in(db, "trains from Bombay to Delhi") == ["CSMT", "NDLS"]


def test_search_pune_nagpur(db):
    r = tt.search_trains(db, "PUNE", "NGP", "2026-11-24")
    assert r and r[0]["train_no"] == "12123" and r[0]["departs"].hour == 18


def test_after_midnight_boarding_uses_next_calendar_day(db):
    # BK1004 boards KYN at 00:30 the day AFTER the origin date
    dep = tt.departure_dt(db, "12301", "2026-11-23", "KYN")
    assert dep == dt.datetime(2026, 11, 24, 0, 30, tzinfo=clock.IST)


def test_search_converts_user_date_to_origin_date(db):
    r = tt.search_trains(db, "KYN", "NDLS", "2026-11-24")
    t = [x for x in r if x["train_no"] == "12301"][0]
    assert t["origin_date"] == "2026-11-23" and t["after_midnight"]


def test_seat_states(db):
    full = seats.availability(db, "12123", "2026-11-25", "SL")
    assert full["state"] == "WL" and full["waitlist"] == 14
    ok = seats.availability(db, "12123", "2026-11-24", "3A")
    assert ok["state"] == "AVAILABLE" and ok["available"] == 12


def test_deadline_changes_with_circular(db):
    b = dict(db.execute("SELECT * FROM bookings WHERE booking_id='BK1001'").fetchone())
    _, h1, _ = deadlines.boarding_change_deadline(db, b, clock.parse_dt("2026-11-21T10:00"))
    _, h2, src = deadlines.boarding_change_deadline(db, b, clock.parse_dt("2026-12-02T10:00"))
    assert (h1, h2) == (24, 12) and src[0] == "CIR-2026-09"
