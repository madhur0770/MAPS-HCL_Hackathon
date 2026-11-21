"""Refund calculator. Pure code, integer rupees, Decimal with round-half-up. No language model involved."""
import datetime as dt
from decimal import Decimal, ROUND_HALF_UP

from core import clock
from tools import settings as st
from tools.timetable import departure_dt


def rupees(x) -> int:
    return int(Decimal(x).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def band_for(delta: dt.timedelta, free_h, mid_h, none_h) -> str:
    if delta >= dt.timedelta(hours=free_h):
        return "FLAT"          # 48h or more
    if delta >= dt.timedelta(hours=mid_h):
        return "MID"           # 12h to <48h
    if delta >= dt.timedelta(hours=none_h):
        return "LOW"           # 4h to <12h
    return "NONE"              # <4h or already departed


def traveller_refund(fare: int, cls: str, band: str, cfg: dict) -> int:
    fare = int(fare)
    if band == "FLAT":
        return max(0, fare - min(fare, cfg["charge"][cls]))
    if band == "MID":
        return rupees(Decimal(fare) * (100 - cfg["mid_pct"]) / 100)
    if band == "LOW":
        return rupees(Decimal(fare) * (100 - cfg["low_pct"]) / 100)
    return 0


def get_cfg(db, as_of):
    g = lambda n, d=0: st.get_int(db, n, as_of, d)  # noqa: E731
    return {
        "charge": {c: g("cancel_charge_" + c) for c in ("SL", "3A", "2A", "1A")},
        "mid_pct": g("deduct_pct_12_48h", 25), "low_pct": g("deduct_pct_4_12h", 50),
        "free_h": g("refund_free_hours", 48), "mid_h": g("refund_mid_hours", 12), "none_h": g("refund_none_hours", 4),
        "wl_clerkage": g("wl_clerkage", 30), "tatkal_refund": g("tatkal_refund", 0),
        "festival": g("festival_waiver", 0),
        "festival_start": st.get(db, "festival_waiver_start", as_of) or "9999-01-01",
        "festival_end": st.get(db, "festival_waiver_end", as_of) or "0000-01-01",
        "train_cancel_pct": g("train_cancelled_refund_pct", 100),
    }


def quote_refund(db, booking_id: str, as_of: dt.datetime, only_travellers=None) -> dict:
    """Returns the full calculation. only_travellers = list of traveller_ids to cancel (default: all active)."""
    b = db.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
    if not b:
        return {"ok": False, "reason": "not_found"}
    trav = db.execute("SELECT * FROM booking_travellers WHERE booking_id=? ORDER BY traveller_id", (booking_id,)).fetchall()
    active = [t for t in trav if t["status"] in ("CNF", "RAC", "WL")]
    if only_travellers is not None:
        active = [t for t in active if t["traveller_id"] in set(only_travellers)]
    if b["status"] == "cancelled" or not active:
        return {"ok": False, "reason": "already_cancelled", "booking_id": booking_id}
    cfg = get_cfg(db, as_of)
    dep = departure_dt(db, b["train_no"], b["journey_date"], b["from_code"])
    delta = dep - as_of
    hours = delta.total_seconds() / 3600.0
    sources = []
    src = lambda n: st.source(db, n, as_of)  # noqa: E731
    lines, total = [], 0
    if b["status"] == "train_cancelled":
        band = "TRAIN_CANCELLED"
        for t in active:
            r = rupees(Decimal(t["fare_paid"]) * cfg["train_cancel_pct"] / 100)
            lines.append({"traveller_id": t["traveller_id"], "name": t["traveller_name"], "fare": t["fare_paid"], "refund": r, "why": "train cancelled by operator"})
            total += r
        sources.append(("RULE-05", "Section 1"))
    else:
        band = band_for(delta, cfg["free_h"], cfg["mid_h"], cfg["none_h"])
        waived = (cfg["festival"] == 1 and cfg["festival_start"] <= b["journey_date"] <= cfg["festival_end"])
        for t in active:
            fare = int(t["fare_paid"])
            if t["status"] == "WL":
                r = max(0, fare - cfg["wl_clerkage"]) if delta.total_seconds() > 0 else 0
                why = "waiting list: fare minus clerkage Rs %d" % cfg["wl_clerkage"]
            elif b["tatkal"] and band != "NONE":
                r, why = cfg["tatkal_refund"], "Tatkal ticket: not refundable"
            elif band == "FLAT" and waived:
                r, why = fare, "festival waiver: full refund"
            else:
                r = traveller_refund(fare, b["class"], band, cfg)
                why = {"FLAT": "fare minus flat charge Rs %d" % min(fare, cfg["charge"][b["class"]]),
                       "MID": "%d%% deducted" % cfg["mid_pct"], "LOW": "%d%% deducted" % cfg["low_pct"],
                       "NONE": "less than %d hours before departure: no refund" % cfg["none_h"]}[band]
            lines.append({"traveller_id": t["traveller_id"], "name": t["traveller_name"], "fare": fare, "refund": r, "why": why, "status": t["status"]})
            total += r
        if any(t["status"] == "WL" for t in active):
            sources.append(("RULE-04", "Section 1") if src("wl_clerkage")[0] == "RULE-04" else src("wl_clerkage"))
        if b["tatkal"]:
            sources.append(src("tatkal_refund"))
        if waived:
            sources.append(src("festival_waiver"))
        n = {"FLAT": "cancel_charge_" + b["class"], "MID": "deduct_pct_12_48h", "LOW": "deduct_pct_4_12h"}.get(band)
        if n:
            sources.append(src(n))
        sources.append(("RULE-03", "Section 1"))
    paid = sum(int(t["fare_paid"]) for t in active)
    uniq = []
    for s in sources:
        if s and s[0] and s not in uniq:
            uniq.append(tuple(s))
    return {"ok": True, "booking_id": booking_id, "band": band, "hours_before": hours, "departure": clock.iso(dep),
            "as_of": clock.iso(as_of), "total_refund": total, "total_paid": paid, "deduction": paid - total,
            "lines": lines, "sources": [{"doc_id": a, "section": c} for a, c in uniq], "class": b["class"],
            "train_no": b["train_no"], "journey_date": b["journey_date"], "from_code": b["from_code"], "to_code": b["to_code"]}
