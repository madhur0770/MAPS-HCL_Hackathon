"""Booking lookups. Every function takes the passenger id: other people's bookings look like 'not found'."""


def get_booking(db, booking_id, passenger_id):
    b = db.execute("SELECT * FROM bookings WHERE booking_id=? AND passenger_id=?", (booking_id, passenger_id)).fetchone()
    if not b:
        return None
    return dict(b)


def travellers(db, booking_id):
    return [dict(r) for r in db.execute("SELECT * FROM booking_travellers WHERE booking_id=? ORDER BY traveller_id", (booking_id,))]


def list_bookings(db, passenger_id, active_only=False):
    sql = "SELECT * FROM bookings WHERE passenger_id=?"
    if active_only:
        sql += " AND status NOT IN ('CANCELLED','OPERATOR_CANCELLED')"
    return [dict(r) for r in db.execute(sql + " ORDER BY journey_date, booking_id", (passenger_id,))]


def mask_phone(last4):
    return "XXXXXX" + last4 if last4 else ""


def booking_view(db, booking_id, passenger_id):
    b = get_booking(db, booking_id, passenger_id)
    if not b:
        return None
    b["travellers"] = travellers(db, booking_id)
    return b


def recompute_status(db, booking_id):
    """Booking status from its travellers: CANCELLED when all are CAN; MIXED when active travellers differ; else CONFIRMED / RAC / WAITLISTED."""
    ts = [r["status"] for r in db.execute("SELECT status FROM booking_travellers WHERE booking_id=?", (booking_id,))]
    cur = db.execute("SELECT status FROM bookings WHERE booking_id=?", (booking_id,)).fetchone()["status"]
    if cur == "OPERATOR_CANCELLED":
        return cur
    act = [x for x in ts if x != "CAN"]
    if not act:
        s = "CANCELLED"
    elif len(set(act)) > 1:
        s = "MIXED"
    else:
        s = {"CNF": "CONFIRMED", "RAC": "RAC", "WL": "WAITLISTED"}.get(act[0], "CONFIRMED")
    db.execute("UPDATE bookings SET status=? WHERE booking_id=?", (s, booking_id))
    return s
