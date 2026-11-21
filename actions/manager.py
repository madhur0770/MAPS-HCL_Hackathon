"""The ONLY place that changes bookings. Flow: propose (preview) -> pending -> confirm (separate call) ->
execute in ONE transaction -> verify by re-reading -> done.
Rules enforced here in code (not left to the language model):
 - nothing changes without confirm; confirm twice never acts twice (idempotent)
 - only the owner can see or confirm an action (others get 'not found')
 - a preview expires; if the refund changed since the preview, we do not act, we issue a fresh preview
"""
import datetime as dt
import json
import uuid

from core import clock
from tools import bookings as bk, deadlines, fares as fr, refund, seats as st_seats, settings as cfg, timetable as tt


def _eff_now(clock_offset: float) -> dt.datetime:
    return clock.real_now() + dt.timedelta(seconds=clock_offset)


def _new_id():
    return "ACT-" + uuid.uuid4().hex[:8].upper()


def _row(db, action_id, passenger_id):
    r = db.execute("SELECT * FROM actions WHERE action_id=? AND passenger_id=?", (action_id, passenger_id)).fetchone()
    return dict(r) if r else None


def _insert(db, passenger_id, booking_id, kind, payload, preview, as_of, trace_id):
    minutes = cfg.get_int(db, "actions.pending_expiry_minutes", as_of, 10)
    aid = _new_id()
    offset = (as_of - clock.real_now()).total_seconds()
    created = as_of
    expires = as_of + dt.timedelta(minutes=minutes)
    db.execute("INSERT INTO actions(action_id,passenger_id,booking_id,action_type,status,created_at,expires_at,result,payload,clock_offset,preview,trace_id) "
               "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
               (aid, passenger_id, booking_id, kind, "pending", clock.iso(created), clock.iso(expires), "",
                json.dumps(payload), offset, json.dumps(preview), trace_id))
    db.commit()
    return {"action_id": aid, "type": kind, "booking_id": booking_id, "expires_at": clock.iso(expires)}


# ---------------------------------------------------------------- propose
def propose_cancel(db, passenger_id, booking_id, as_of, traveller_ids=None, trace_id=""):
    b = bk.get_booking(db, booking_id, passenger_id)
    if not b:
        return {"ok": False, "reason": "not_found"}
    q = refund.quote_refund(db, booking_id, as_of, only_travellers=traveller_ids)
    if not q["ok"]:
        return {"ok": False, "reason": q["reason"], "booking_id": booking_id}
    if q["band"] == "OPERATOR":
        return {"ok": False, "reason": "operator_cancelled", "booking_id": booking_id, "quote": q}
    if q["band"] == "E":
        return {"ok": False, "reason": "departed", "booking_id": booking_id, "quote": q}
    pend = _insert(db, passenger_id, booking_id, "cancel_booking",
                   {"traveller_ids": traveller_ids}, {"quote": q}, as_of, trace_id)
    return {"ok": True, "pending_action": pend, "quote": q}


def propose_change_boarding(db, passenger_id, booking_id, new_code, as_of, trace_id=""):
    b = bk.get_booking(db, booking_id, passenger_id)
    if not b:
        return {"ok": False, "reason": "not_found"}
    if b["status"] in ("CANCELLED", "OPERATOR_CANCELLED"):
        return {"ok": False, "reason": "not_active", "booking_id": booking_id}
    if db.execute("SELECT 1 FROM booking_travellers WHERE booking_id=? AND status='WL'", (booking_id,)).fetchone():
        return {"ok": False, "reason": "has_waitlisted", "booking_id": booking_id}
    deadline, hours, src = deadlines.boarding_change_deadline(db, b, as_of)
    stops = {r["station_code"]: r["stop_order"] for r in tt.stops_of(db, b["train_no"])}
    if new_code not in stops or not (stops[b["from_code"]] < stops[new_code] < stops[b["to_code"]]):
        return {"ok": False, "reason": "bad_station", "booking_id": booking_id}
    done = db.execute("SELECT count(*) FROM actions WHERE booking_id=? AND action_type='change_boarding' AND status='done'", (booking_id,)).fetchone()[0]
    if done >= cfg.get_int(db, "boarding_change.maximum_changes", as_of, 1):
        return {"ok": False, "reason": "already_changed", "booking_id": booking_id}
    if as_of >= deadline:
        return {"ok": False, "reason": "too_late", "booking_id": booking_id, "deadline": clock.iso(deadline), "hours": hours,
                "source": {"doc_id": src[0], "section": src[1]}}
    pv = {"old_code": b["from_code"], "new_code": new_code, "deadline": clock.iso(deadline), "hours": hours,
          "source": {"doc_id": src[0], "section": src[1]},
          "new_departure": clock.iso(tt.departure_dt(db, b["train_no"], b["journey_date"], new_code))}
    pend = _insert(db, passenger_id, booking_id, "change_boarding", {"new_code": new_code}, pv, as_of, trace_id)
    return {"ok": True, "pending_action": pend, "preview": pv}


def propose_book(db, passenger_id, train_no, origin_date, frm, to, cls, travellers, as_of, trace_id=""):
    """travellers = [{'name':..,'age':..}]. Rules: RUL-001 (window, cutoff, max travellers), RUL-004 3.2 (CNF, then RAC, then WL)."""
    t = db.execute("SELECT * FROM trains WHERE train_no=?", (train_no,)).fetchone()
    if not t or cls not in t["classes"].split(","):
        return {"ok": False, "reason": "no_such_train_or_class"}
    maxn = cfg.get_int(db, "booking.max_travellers", as_of, 6)
    if not travellers or len(travellers) > maxn:
        return {"ok": False, "reason": "bad_traveller_count", "max": maxn}
    base = fr.fare(db, train_no, cls, frm, to)
    av = st_seats.availability(db, train_no, origin_date, cls)
    if base is None or av is None:
        return {"ok": False, "reason": "not_available"}
    if db.execute("SELECT 1 FROM service_cancellations WHERE train_no=? AND journey_date=? AND announced_at<=?", (train_no, origin_date, clock.iso(as_of))).fetchone():
        return {"ok": False, "reason": "service_cancelled"}
    first = tt.stops_of(db, train_no)[0]["station_code"]
    origin_dep = tt.departure_dt(db, train_no, origin_date, first)
    dep = tt.departure_dt(db, train_no, origin_date, frm)
    cutoff = cfg.get_int(db, "booking.cutoff_minutes_before_origin", as_of, 20)
    if as_of >= origin_dep - dt.timedelta(minutes=cutoff):
        return {"ok": False, "reason": "departed", "minutes": cutoff}
    adv = cfg.get_int(db, "booking.advance_window_days", as_of, 90)
    opens = dt.datetime.combine(dt.date.fromisoformat(origin_date) - dt.timedelta(days=adv), dt.time(8, 0), tzinfo=clock.IST)
    if as_of < opens:
        return {"ok": False, "reason": "too_early", "days": adv, "opens": clock.iso(opens)}
    lines = [{"name": tr["name"], "age": int(tr["age"]), "fare": int(base)} for tr in travellers]
    wl_room = db.execute("SELECT wl_capacity-waitlist FROM seats WHERE train_no=? AND journey_date=? AND class=?", (train_no, origin_date, cls)).fetchone()[0]
    left_av, left_rac = av["available"], av["rac"]
    for ln in lines:
        if left_av > 0:
            ln["status"] = "CNF"; left_av -= 1
        elif left_rac > 0:
            ln["status"] = "RAC"; left_rac -= 1
        elif wl_room > 0:
            ln["status"] = "WL"; wl_room -= 1
        else:
            return {"ok": False, "reason": "regret", "availability": av}
    total = sum(l["fare"] for l in lines)
    pv = {"train_no": train_no, "origin_date": origin_date, "from": frm, "to": to, "class": cls, "lines": lines,
          "total": total, "departure": clock.iso(dep)}
    pend = _insert(db, passenger_id, "", "book", {"train_no": train_no, "origin_date": origin_date, "from": frm, "to": to,
                                                   "class": cls, "travellers": travellers}, pv, as_of, trace_id)
    return {"ok": True, "pending_action": pend, "preview": pv}


# ---------------------------------------------------------------- confirm / cancel
def get_action(db, action_id, passenger_id):
    r = _row(db, action_id, passenger_id)
    if not r:
        return None
    r["preview"] = json.loads(r["preview"] or "{}")
    r["payload"] = json.loads(r["payload"] or "{}")
    r["result"] = json.loads(r["result"]) if r["result"] else None
    return r


def cancel_action(db, action_id, passenger_id):
    a = _row(db, action_id, passenger_id)
    if not a:
        return {"ok": False, "reason": "not_found"}
    if a["status"] == "pending":
        db.execute("UPDATE actions SET status='cancelled' WHERE action_id=?", (action_id,))
        db.commit()
        return {"ok": True, "status": "cancelled", "action_id": action_id}
    return {"ok": True, "status": a["status"], "action_id": action_id, "note": "nothing to cancel"}


def confirm_action(db, action_id, passenger_id, trace_id=""):
    a = _row(db, action_id, passenger_id)
    if not a:
        return {"ok": False, "reason": "not_found"}
    if a["status"] == "done":                                  # idempotent: second confirm does nothing
        return {"ok": True, "status": "done", "already": True, "action_id": action_id,
                "result": json.loads(a["result"]) if a["result"] else None, "action_type": a["action_type"]}
    if a["status"] in ("cancelled", "failed"):
        return {"ok": False, "reason": a["status"], "action_id": action_id}
    now = _eff_now(a["clock_offset"])
    if a["status"] == "expired" or now > clock.parse_dt(a["expires_at"]):
        db.execute("UPDATE actions SET status='expired' WHERE action_id=?", (action_id,))
        db.commit()
        return {"ok": False, "reason": "expired", "action_id": action_id}
    payload, preview = json.loads(a["payload"]), json.loads(a["preview"])
    try:
        db.execute("BEGIN IMMEDIATE")
        # re-check the world at confirm time
        if a["action_type"] == "cancel_booking":
            q = refund.quote_refund(db, a["booking_id"], now, only_travellers=payload.get("traveller_ids"))
            if not q["ok"]:
                raise _Fail(q["reason"])
            if q["total_refund"] != preview["quote"]["total_refund"]:
                db.execute("UPDATE actions SET status='expired', result=? WHERE action_id=?",
                           (json.dumps({"quote_changed": True}), action_id))
                db.commit()
                return {"ok": False, "reason": "quote_changed", "old": preview["quote"]["total_refund"], "new": q["total_refund"],
                        "action_id": action_id}
            result = _exec_cancel(db, a["booking_id"], q, payload.get("traveller_ids"))
        elif a["action_type"] == "change_boarding":
            b = bk.get_booking(db, a["booking_id"], passenger_id)
            deadline, _, _ = deadlines.boarding_change_deadline(db, b, now)
            if now >= deadline:
                raise _Fail("too_late")
            result = _exec_change(db, a["booking_id"], payload["new_code"], b)
        elif a["action_type"] == "book":
            result = _exec_book(db, passenger_id, payload, now)
        else:
            raise _Fail("unknown_action")
        db.execute("UPDATE actions SET status='done', result=? WHERE action_id=?", (json.dumps(result), action_id))
        db.commit()
    except _Fail as e:
        db.rollback()
        db.execute("UPDATE actions SET status='failed', result=? WHERE action_id=?", (json.dumps({"error": str(e)}), action_id))
        db.commit()
        return {"ok": False, "reason": str(e), "action_id": action_id}
    except Exception as e:                                       # any bug: nothing is half-changed
        db.rollback()
        db.execute("UPDATE actions SET status='failed', result=? WHERE action_id=?", (json.dumps({"error": repr(e)}), action_id))
        db.commit()
        return {"ok": False, "reason": "failed", "action_id": action_id}
    verified, vnote = verify(db, a["action_type"], result)
    return {"ok": True, "status": "done", "action_id": action_id, "action_type": a["action_type"], "result": result,
            "verified": verified, "verify_note": vnote}


class _Fail(Exception):
    pass


# ---------------------------------------------------------------- executors (inside the transaction)
def _exec_cancel(db, booking_id, q, traveller_ids):
    ids = [l["traveller_id"] for l in q["lines"]]
    b = db.execute("SELECT * FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()
    for l in q["lines"]:
        t = db.execute("SELECT status FROM booking_travellers WHERE traveller_id=?", (l["traveller_id"],)).fetchone()
        db.execute("UPDATE booking_travellers SET status='CAN' WHERE traveller_id=?", (l["traveller_id"],))
        col = {"CNF": "available", "RAC": "rac", "WL": "waitlist"}.get(t["status"])
        if col and b["status"] != "OPERATOR_CANCELLED":
            delta = -1 if col == "waitlist" else 1
            db.execute("UPDATE seats SET %s=MAX(0,%s+?) WHERE train_no=? AND journey_date=? AND class=?" % (col, col),
                       (delta, b["train_no"], b["journey_date"], b["class"]))
    db.execute("UPDATE bookings SET refunded=refunded+?, cancelled_at=?, cancellation_type='PASSENGER' WHERE booking_id=?", (q["total_refund"], q["as_of"], booking_id))
    status = bk.recompute_status(db, booking_id)
    return {"booking_id": booking_id, "cancelled_traveller_ids": ids, "refund": q["total_refund"], "new_status": status,
            "band": q["band"]}


def _exec_change(db, booking_id, new_code, b):
    db.execute("UPDATE bookings SET from_code=? WHERE booking_id=?", (new_code, booking_id))
    return {"booking_id": booking_id, "old_code": b["from_code"], "new_code": new_code}


def _exec_book(db, passenger_id, payload, now):
    no, od, frm, to, cls = payload["train_no"], payload["origin_date"], payload["from"], payload["to"], payload["class"]
    av = db.execute("SELECT * FROM seats WHERE train_no=? AND journey_date=? AND class=?", (no, od, cls)).fetchone()
    base = fr.fare(db, no, cls, frm, to)
    n = db.execute("SELECT count(*) FROM bookings").fetchone()[0] + 1
    bid = "UR-%08d" % (10000000 + n)       # RUL-001 3.4: UR- plus eight decimal digits
    while db.execute("SELECT 1 FROM bookings WHERE booking_id=?", (bid,)).fetchone():
        n += 1
        bid = "UR-%08d" % (10000000 + n)
    left_av, left_rac, wl = av["available"], av["rac"], av["waitlist"]
    total, rows, sts = 0, [], []
    for tr in payload["travellers"]:
        age = int(tr["age"])
        f = int(base)
        if left_av > 0:
            s, left_av = "CNF", left_av - 1
        elif left_rac > 0:
            s, left_rac = "RAC", left_rac - 1
        elif av["wl_capacity"] - wl > 0:
            s, wl = "WL", wl + 1
        else:
            raise _Fail("regret")
        total += f
        sts.append(s)
        rows.append((bid, tr["name"], age, s, "", "", f))
    worst = "MIXED" if len(set(sts)) > 1 else {"CNF": "CONFIRMED", "RAC": "RAC", "WL": "WAITLISTED"}[sts[0]]
    dep = tt.departure_dt(db, no, od, frm)
    db.execute("INSERT INTO bookings(booking_id,passenger_id,train_no,journey_date,from_code,to_code,class,amount_paid,status,booked_at,tatkal,refunded,boarding_datetime) "
               "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (bid, passenger_id, no, od, frm, to, cls, total, worst, clock.iso(now), 0, 0, clock.iso(dep)))
    db.executemany("INSERT INTO booking_travellers(booking_id,traveller_name,age,status,coach,berth,fare_paid) VALUES(?,?,?,?,?,?,?)", rows)
    db.execute("UPDATE seats SET available=?, rac=?, waitlist=? WHERE train_no=? AND journey_date=? AND class=?", (left_av, left_rac, wl, no, od, cls))
    return {"booking_id": bid, "status": worst, "total": total, "travellers": [{"name": r[1], "status": r[3], "fare": r[6]} for r in rows]}


# ---------------------------------------------------------------- verify (re-read from the database)
def verify(db, kind, result):
    if kind == "cancel_booking":
        ids = result["cancelled_traveller_ids"]
        marks = ",".join("?" * len(ids))
        n = db.execute("SELECT count(*) FROM booking_travellers WHERE traveller_id IN (%s) AND status='CAN'" % marks, ids).fetchone()[0]
        s = db.execute("SELECT status FROM bookings WHERE booking_id=?", (result["booking_id"],)).fetchone()[0]
        return (n == len(ids) and s == result["new_status"]), "re-read: %d/%d travellers CAN, booking status %s" % (n, len(ids), s)
    if kind == "change_boarding":
        c = db.execute("SELECT from_code FROM bookings WHERE booking_id=?", (result["booking_id"],)).fetchone()[0]
        return c == result["new_code"], "re-read: boarding station is %s" % c
    if kind == "book":
        r = db.execute("SELECT status,amount_paid FROM bookings WHERE booking_id=?", (result["booking_id"],)).fetchone()
        return bool(r) and r[1] == result["total"], "re-read: booking exists with status %s" % (r[0] if r else "missing")
    return False, "unknown"
