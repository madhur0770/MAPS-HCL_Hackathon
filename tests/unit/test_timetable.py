import datetime as dt
from core import clock
from tools import timetable as tt, seats, deadlines


def test_station_aliases(db):
    assert tt.resolve_station(db, "Surya Nagar") == "SURY"
    assert tt.resolve_station(db, "Chetak Fort") == "CHET"
    assert tt.find_stations_in(db, "Anandpur Central to Chetakgarh") == ["ANPR", "CHET"]


def test_shared_name_is_ambiguous(db):
    # "Anandpur" is the city of both ANPR and ANPN: never guess
    assert tt.find_stations_in(db, "Anandpur to Chetakgarh") == ["CHET"]
    amb = tt.ambiguous_in(db, "trains from Anandpur to Chetakgarh")
    assert amb and amb[0][1] == ["ANPN", "ANPR"]
    assert not tt.ambiguous_in(db, "Anandpur North to Chetakgarh")


def test_overnight_train_arrival_next_day(db):
    r = [x for x in tt.search_trains(db, "ANPR", "ANPN", "2026-11-21") if x["train_no"] == "UJ1001"][0]
    assert r["departs"] == dt.datetime(2026, 11, 21, 23, 40, tzinfo=clock.IST)
    assert r["arrives"] == dt.datetime(2026, 11, 22, 0, 55, tzinfo=clock.IST)


def test_search_direct_only_and_sorted(db):
    r = tt.search_trains(db, "ANPR", "UDAY", "2026-11-26")
    assert [x["train_no"] for x in r][:2] == ["UJ1007", "UJ1019"]
    assert tt.search_trains(db, "ANPR", "CHET", "2026-11-25") == []


def test_seat_states(db):
    assert seats.availability(db, "UJ1002", "2026-11-21", "AC2")["state"] == "RAC"
    assert seats.availability(db, "UJ1001", "2026-11-21", "FP")["state"] == "WL"
    assert seats.availability(db, "UJ1003", "2026-11-21", "FP")["state"] == "WL"


def test_boarding_change_deadline_is_six_hours_before_origin(db):
    b = dict(db.execute("SELECT * FROM bookings WHERE booking_id='BKG0001'").fetchone())
    dl, hrs, src = deadlines.boarding_change_deadline(db, b, clock.parse_dt("2026-11-21T10:00"))
    assert dl == dt.datetime(2026, 11, 25, 3, 15, tzinfo=clock.IST) and hrs == 6 and src[0] == "RUL-010"


def test_train_found_by_name_and_unknown_city_named(db):
    from assistant import understand as u
    assert u.find_train(db, "what is my booking id for neelkanth rapid") == "UJ1020"
    assert u.find_train(db, "UJ 1006 timings") == "UJ1006"
