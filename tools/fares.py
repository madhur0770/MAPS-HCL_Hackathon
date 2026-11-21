def fare(db, train_no, cls, frm, to):
    r = db.execute("SELECT fare FROM fares WHERE train_no=? AND class=? AND from_code=? AND to_code=?", (train_no, cls, frm, to)).fetchone()
    return r["fare"] if r else None
