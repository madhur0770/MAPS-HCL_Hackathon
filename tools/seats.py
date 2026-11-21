def availability(db, train_no, origin_date, cls):
    r = db.execute("SELECT * FROM seats WHERE train_no=? AND journey_date=? AND class=?", (train_no, origin_date, cls)).fetchone()
    if not r:
        return None
    if r["available"] > 0:
        state = "AVAILABLE"
    elif r["rac"] > 0:
        state = "RAC"
    elif r["wl_capacity"] > r["waitlist"]:
        state = "WL"
    else:
        state = "REGRET"
    return {"available": r["available"], "rac": r["rac"], "waitlist": r["waitlist"], "state": state,
            "capacity": r["capacity"]}


def all_classes(db, train_no, origin_date):
    return {r["class"]: availability(db, train_no, origin_date, r["class"])
            for r in db.execute("SELECT class FROM seats WHERE train_no=? AND journey_date=?", (train_no, origin_date))}
