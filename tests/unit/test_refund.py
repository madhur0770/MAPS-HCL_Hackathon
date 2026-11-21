import datetime as dt
import pytest
from core import clock
from tools import refund

DEP = dt.datetime(2026, 11, 24, 18, 0, tzinfo=clock.IST)  # BK1001: 12123 Pune 18:00, 3A, fare 2040


def at(delta_h, delta_m=0):
    return DEP - dt.timedelta(hours=delta_h, minutes=delta_m)


@pytest.mark.parametrize("h,m,band,amount", [
    (51, 0, "FLAT", 1860), (48, 0, "FLAT", 1860), (47, 59, "MID", 1530), (12, 0, "MID", 1530),
    (11, 59, "LOW", 1020), (4, 0, "LOW", 1020), (3, 59, "NONE", 0), (0, 1, "NONE", 0)])
def test_boundaries_3A_fare_2040(db, h, m, band, amount):
    q = refund.quote_refund(db, "BK1001", at(h, m))
    assert q["band"] == band and q["total_refund"] == amount


def test_after_departure_is_zero(db):
    assert refund.quote_refund(db, "BK1001", DEP + dt.timedelta(hours=1))["total_refund"] == 0


def test_flat_charge_never_exceeds_fare(db):
    cfg = refund.get_cfg(db, at(60))
    assert refund.traveller_refund(50, "1A", "FLAT", cfg) == 0   # charge 240 > fare 50


def test_circular_changes_2A_charge_by_date(db):
    # BK1003 is 2A, 2 travellers. Same journey, ask before and after 22 Nov 2026 (CIR-2026-07)
    jd = db.execute("SELECT journey_date FROM bookings WHERE booking_id='BK1003'").fetchone()[0]
    dep = refund.departure_dt(db, "12123", jd, "NK")
    before = refund.quote_refund(db, "BK1003", dt.datetime(2026, 11, 21, 12, 0, tzinfo=clock.IST))
    after = refund.quote_refund(db, "BK1003", dt.datetime(2026, 11, 22, 12, 0, tzinfo=clock.IST))
    assert before["band"] == "FLAT" and after["band"] == "FLAT"
    assert before["total_refund"] - after["total_refund"] == 2 * 40   # 200 -> 240 per traveller
    assert any(s["doc_id"] == "CIR-2026-07" for s in after["sources"])
    assert any(s["doc_id"] == "RULE-03" for s in before["sources"])


def test_waitlist_refund_is_fare_minus_clerkage(db):
    q = refund.quote_refund(db, "BK1002", clock.parse_dt("2026-11-21T10:00"))
    assert [l["refund"] for l in q["lines"]] == [max(0, l["fare"] - 30) for l in q["lines"]]


def test_wl_clerkage_changes_after_circular(db):
    from tools import settings as st
    assert st.get_int(db, "wl_clerkage", clock.parse_dt("2026-12-14T10:00")) == 30
    assert st.get_int(db, "wl_clerkage", clock.parse_dt("2026-12-15T00:00")) == 40


def test_train_cancelled_full_refund(db):
    bid = db.execute("SELECT booking_id FROM bookings WHERE status='train_cancelled' LIMIT 1").fetchone()[0]
    q = refund.quote_refund(db, bid, clock.parse_dt("2026-11-21T10:00"))
    assert q["band"] == "TRAIN_CANCELLED" and q["total_refund"] == q["total_paid"]


def test_tatkal_not_refundable(db):
    q = refund.quote_refund(db, "BK1008", clock.parse_dt("2026-11-21T10:00"))   # tatkal booking
    assert q["total_refund"] == 0 and "Tatkal" in q["lines"][0]["why"]


def test_cancelled_booking_has_no_quote(db):
    assert refund.quote_refund(db, "BK1005", clock.parse_dt("2026-11-21T10:00"))["reason"] == "already_cancelled"


def test_partial_cancel_one_traveller(db):
    ids = [r[0] for r in db.execute("SELECT traveller_id FROM booking_travellers WHERE booking_id='BK1003' ORDER BY traveller_id")]
    q = refund.quote_refund(db, "BK1003", clock.parse_dt("2026-11-21T10:00"), only_travellers=[ids[0]])
    assert len(q["lines"]) == 1


def test_festival_waiver_full_refund_in_window(db):
    jd = "2026-12-25"
    db.execute("UPDATE bookings SET journey_date=? WHERE booking_id='BK1001'", (jd,))
    dep = refund.departure_dt(db, "12123", jd, "PUNE")
    q = refund.quote_refund(db, "BK1001", dep - dt.timedelta(hours=60))   # 2026-12-23: after waiver effective date
    assert q["total_refund"] == q["total_paid"]
