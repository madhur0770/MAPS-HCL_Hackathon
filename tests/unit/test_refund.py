"""Refund engine against hand calculations (RUL-003). Every expected number below is worked out on paper, not by calling the engine.
Money is paise inside the code, so Rs 3062.50 is 306250."""
import math
import pytest
from fractions import Fraction
from core import clock
from tools import refund


def at(s):
    return clock.parse_dt(s + ":00+05:30" if len(s) == 16 else s)


def q(db, bid, when):
    r = refund.quote_refund(db, bid, at(when))
    assert r["ok"], r
    return r


def hand(fare_rs, pct, fixed_rs):
    """greater of (pct of fare rounded UP to next Rs 5) and fixed charge; refund rounded DOWN to whole rupee."""
    f = Fraction(str(fare_rs))
    ded = max(math.ceil(f * pct / 100 / 5) * 5, fixed_rs)
    return int(max(0, f - ded) // 1)


# BKG0001: AC2, base fare Rs 3062.50, boards 25 Nov 09:15. From 15 Nov the AC2 fixed charge is Rs 260 (CIR-001), before that Rs 240.
@pytest.mark.parametrize("when,band,refund_rs", [
    ("2026-11-21T10:00", "A", 2802),     # 95h15 before: 3062.50 - 260 = 2802.50 -> 2802
    ("2026-11-23T09:15", "B", 2292),     # exactly 48h is band B: 25% = 765.625 -> Rs 770 ; 3062.50 - 770 = 2292.50
    ("2026-11-23T09:14", "A", 2802),     # 48h + 1 minute is still band A
    ("2026-11-23T09:16", "B", 2292),     # 47h59 is band B
    ("2026-11-24T21:15", "C", 1527),     # exactly 12h is band C: 50% = 1531.25 -> Rs 1535 ; 3062.50 - 1535 = 1527.50
    ("2026-11-24T21:14", "B", 2292),     # 12h + 1 minute is band B
    ("2026-11-25T05:15", "D", 762),      # exactly 4h is band D: 75% = 2296.875 -> Rs 2300 ; 3062.50 - 2300 = 762.50
    ("2026-11-25T05:14", "C", 1527),     # 4h + 1 minute is band C
    ("2026-11-25T09:14", "D", 762),      # 1 minute before departure
    ("2026-11-25T09:15", "E", 0),        # at departure: no refund
    ("2026-11-25T09:16", "E", 0),
])
def test_bands_at_every_cutoff(db, when, band, refund_rs):
    r = q(db, "BKG0001", when)
    assert r["band"] == band
    assert r["total_refund"] == refund_rs * 100


def test_circular_changes_fixed_charge_from_its_effective_date(db):
    before = q(db, "BKG0001", "2026-11-14T23:59")        # one minute before CIR-001 takes effect: Rs 240 -> 3062.50 - 240 = 2822.50
    after = q(db, "BKG0001", "2026-11-15T00:00")         # from 00:00 on 15 Nov: Rs 260
    assert before["charge"] == 24000 and before["total_refund"] == 282200
    assert after["charge"] == 26000 and after["total_refund"] == 280200
    assert before["sources"] and any(s["doc_id"] == "CIR-001" for s in after["sources"])


def test_fixed_charge_wins_when_percentage_is_smaller(db):
    cfg = refund.get_cfg(db, at("2026-11-21T10:00"))
    t = {"traveller_id": 1, "traveller_name": "X", "fare_paid": 80000, "status": "CNF"}          # fare Rs 800, band B: 25% = 200 < fixed 260
    line = refund.traveller_line(t, "AC2", "B", cfg, False, 40 * 3600)
    assert line["refund"] == hand(800, 25, 260) * 100 == 54000 and line["why"] == "fixed_is_greater"


def test_refund_never_negative(db):
    cfg = refund.get_cfg(db, at("2026-11-21T10:00"))
    t = {"traveller_id": 1, "traveller_name": "X", "fare_paid": 20000, "status": "CNF"}          # fare Rs 200 < fixed charge
    assert refund.traveller_line(t, "AC2", "A", cfg, False, 100 * 3600)["refund"] == 0


def test_second_booking_other_class(db):
    r = q(db, "BKG0002", "2026-11-24T10:03")               # AC3 Rs 1395, 47h59 before 26 Nov 10:02 -> band B
    assert r["band"] == "B" and r["total_refund"] == hand(1395, 25, 220) * 100 == 104500


def test_mixed_status_booking_each_traveller_alone(db):
    r = q(db, "BKG0003", "2026-11-21T10:00")               # FP Rs 2550 each, boards 21 Nov 23:40 (13h40 before): CNF band B, WL flat Rs 20
    by = {l["status"]: l for l in r["lines"]}
    assert by["CNF"]["refund"] == hand(2550, 25, 300) * 100 == 191000
    assert by["WL"]["refund"] == 253000
    assert r["total_refund"] == 444000


def test_rac_and_wl_use_status_charges_not_the_cnf_table(db):
    rac = q(db, "BKG0005", "2026-11-21T00:00")             # RAC Rs 2410, 6h07 before: Rs 40 deducted
    wl = q(db, "BKG0007", "2026-11-21T00:00")              # WL Rs 4275: Rs 20 deducted
    assert rac["total_refund"] == 237000 and wl["total_refund"] == 425500


def test_operator_cancelled_booking_refunds_everything(db):
    for bid, paid in (("BKG0008", 244000), ("BKG0009", 184000), ("BKG0016", 204000)):
        r = q(db, bid, "2026-11-21T10:00")
        assert r["band"] == "OPERATOR" and r["total_refund"] == paid


def test_service_cancellation_applies_only_after_it_is_announced(db):
    # train UJ1005 on 26 Nov is cancelled by the operator, announced 23 Nov 10:00. A live booking on it is a normal voluntary cancellation before that.
    db.execute("UPDATE bookings SET status='CONFIRMED' WHERE booking_id='BKG0008'")
    early = refund.quote_refund(db, "BKG0008", at("2026-11-22T12:00"))
    late = refund.quote_refund(db, "BKG0008", at("2026-11-23T10:00"))
    assert early["band"] != "OPERATOR" and late["band"] == "OPERATOR" and late["total_refund"] == 244000


def test_already_cancelled_and_unknown(db):
    assert refund.quote_refund(db, "BKG0010", at("2026-11-21T10:00"))["reason"] == "already_cancelled"
    assert refund.quote_refund(db, "NOPE", at("2026-11-21T10:00"))["reason"] == "not_found"


def test_tatkal_confirmed_gets_no_base_refund(db):
    db.execute("UPDATE bookings SET tatkal=1 WHERE booking_id='BKG0001'")
    assert q(db, "BKG0001", "2026-11-21T10:00")["total_refund"] == 0


def test_partial_cancellation_one_traveller(db):
    ids = [r["traveller_id"] for r in db.execute("SELECT traveller_id FROM booking_travellers WHERE booking_id='BKG0011'")]
    db.execute("UPDATE bookings SET status='CONFIRMED' WHERE booking_id='BKG0011'")
    r = refund.quote_refund(db, "BKG0011", at("2026-11-21T10:00"), only_travellers=[ids[0]])
    assert len(r["lines"]) == 1 and r["total_paid"] == 131250      # SL Rs 1312.50 per traveller; band A, fixed Rs 120 -> 1192.50 -> 1192
    assert r["total_refund"] == 119200
