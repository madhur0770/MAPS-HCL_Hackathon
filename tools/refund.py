"""Refund calculator for RUL-003 / RUL-004 / RUL-005 / RUL-011. Pure code, integer PAISE, Decimal. No language model involved.
Settings (fixed charges, percentages) are read for the moment of the request, so circulars apply from their effective date."""
import datetime as dt
import math
from decimal import Decimal

from core import clock
from tools import settings as st
from tools.timetable import departure_dt

PAISE = 100
ACTIVE = ("CNF", "RAC", "WL")


def up_to_5_rupees(paise: Decimal) -> int:
    """Deduction rounding: up to the next INR 5 (RUL-003 3.6 step 3)."""
    return int(math.ceil(Decimal(paise) / (5 * PAISE))) * 5 * PAISE


def down_to_rupee(paise: Decimal) -> int:
    """Final refund rounding: down to a whole INR (RUL-003 3.6 step 6)."""
    return int(Decimal(paise) // PAISE) * PAISE


def band_for(hours: Decimal) -> str:
    """A: t>48   B: 12<t<=48   C: 4<t<=12   D: 0<t<=4   E: t<=0   (RUL-003 3.4). t is in hours."""
    if hours > 48:
        return "A"
    if hours > 12:
        return "B"
    if hours > 4:
        return "C"
    if hours > 0:
        return "D"
    return "E"


def get_cfg(db, as_of):
    g = lambda n, d=0: st.get_int(db, n, as_of, d)  # noqa: E731
    return {
        "charge": {c: g("cancel_fixed_charge_" + c.lower()) * PAISE for c in ("FP", "AC2", "AC3", "EC", "SL", "CC")},
        "pct": {"B": g("cancellation.band_b.deduction_percent", 25), "C": g("cancellation.band_c.deduction_percent", 50),
                "D": g("cancellation.band_d.deduction_percent", 75), "E": g("cancellation.band_e.deduction_percent", 100)},
        "rac": g("cancellation.rac.charge", 40) * PAISE, "wl": g("cancellation.waitlist.charge", 20) * PAISE,
    }


def fixed_source(db, cls, as_of):
    return st.source(db, "cancel_fixed_charge_" + cls.lower(), as_of)


def traveller_line(t, cls, band, cfg, tatkal, delta_s):
    fare = int(t["fare_paid"])
    base = dict(traveller_id=t["traveller_id"], name=t["traveller_name"], fare=fare, status=t["status"])
    if delta_s <= 0:
        return dict(base, refund=0, deduction=fare, why="departed", rule="at_or_after_departure")
    if t["status"] == "RAC":
        ded = cfg["rac"]
        return dict(base, refund=down_to_rupee(max(0, fare - ded)), deduction=min(fare, ded), why="rac", rule="status_charge")
    if t["status"] == "WL":
        ded = cfg["wl"]
        return dict(base, refund=down_to_rupee(max(0, fare - ded)), deduction=min(fare, ded), why="wl", rule="status_charge")
    if tatkal:
        return dict(base, refund=0, deduction=fare, why="tatkal", rule="tatkal")
    fixed = cfg["charge"][cls]
    if band == "A":
        ded, why = fixed, "fixed"
    else:
        pct_amt = up_to_5_rupees(Decimal(fare) * cfg["pct"][band] / 100)
        ded = max(pct_amt, fixed)
        why = "fixed_is_greater" if fixed >= pct_amt else "percent"
    if band == "E":
        ded, why = fare, "none"
    return dict(base, refund=down_to_rupee(max(0, fare - ded)), deduction=min(fare, ded), why=why, rule="cnf_table")


def operator_cancelled(db, b, as_of):
    if b["status"] == "OPERATOR_CANCELLED":
        return True
    r = db.execute("SELECT announced_at FROM service_cancellations WHERE train_no=? AND journey_date=?", (b["train_no"], b["journey_date"])).fetchone()
    return bool(r and clock.parse_dt(r["announced_at"]) <= as_of)


def quote_refund(db, booking_id: str, as_of: dt.datetime, only_travellers=None) -> dict:
    """Full calculation. only_travellers = traveller_ids to cancel (default: all active)."""
    b = db.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
    if not b:
        return {"ok": False, "reason": "not_found"}
    trav = db.execute("SELECT * FROM booking_travellers WHERE booking_id=? ORDER BY traveller_id", (booking_id,)).fetchall()
    if b["status"] == "CANCELLED":
        return {"ok": False, "reason": "already_cancelled", "booking_id": booking_id}
    op = operator_cancelled(db, b, as_of)
    active = [t for t in trav if t["status"] in ACTIVE] if not op else list(trav)
    if only_travellers is not None:
        active = [t for t in active if t["traveller_id"] in set(only_travellers)]
    if not active:
        return {"ok": False, "reason": "already_cancelled", "booking_id": booking_id}
    cfg = get_cfg(db, as_of)
    dep = departure_dt(db, b["train_no"], b["journey_date"], b["from_code"])
    delta = dep - as_of
    hours = Decimal(delta.total_seconds()) / 3600
    lines, total, sources = [], 0, []
    src = lambda n: st.source(db, n, as_of)  # noqa: E731
    if op:
        band = "OPERATOR"
        for t in active:
            lines.append(dict(traveller_id=t["traveller_id"], name=t["traveller_name"], fare=int(t["fare_paid"]), refund=int(t["fare_paid"]),
                              deduction=0, why="operator", rule="operator_cancelled", status=t["status"]))
        sources.append(("RUL-011", "3.1"))
    else:
        band = band_for(hours)
        tatkal = bool(b["tatkal"])
        for t in active:
            lines.append(traveller_line(t, b["class"], band, cfg, tatkal, delta.total_seconds()))
        sources.append(("RUL-003", "3.4"))
        sources.append(("RUL-003", "3.6"))
        if band != "E" and any(l["rule"] == "cnf_table" for l in lines):
            s = fixed_source(db, b["class"], as_of)
            sources.append((s[0], "3.3"))
        if any(l["rule"] == "status_charge" for l in lines):
            sources.append(("RUL-003", "3.7"))
        if tatkal:
            sources.append(("RUL-005", "3.4"))
    total = sum(l["refund"] for l in lines)
    paid = sum(l["fare"] for l in lines)
    uniq = []
    for s in sources:
        if s not in uniq:
            uniq.append(s)
    fixed_doc = fixed_source(db, b["class"], as_of)[0]
    return {"ok": True, "booking_id": booking_id, "band": band, "hours_before": float(hours), "departure": clock.iso(dep),
            "as_of": clock.iso(as_of), "total_refund": total, "total_paid": paid, "deduction": paid - total, "lines": lines,
            "sources": [{"doc_id": a, "section": c} for a, c in uniq], "class": b["class"], "charge": cfg["charge"][b["class"]],
            "fixed_doc": fixed_doc, "pct": cfg["pct"].get(band), "rac_charge": cfg["rac"], "wl_charge": cfg["wl"], "tatkal": bool(b["tatkal"]),
            "operator": op, "train_no": b["train_no"], "journey_date": b["journey_date"], "from_code": b["from_code"], "to_code": b["to_code"]}
