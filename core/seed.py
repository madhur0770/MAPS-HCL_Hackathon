"""Deterministic data generator. Same seed => same data. No LLM, no real personal data.
Everything is invented for the fictional operator Ujjwal Rail."""
import datetime as dt
import json
import random

from core import content
from core.db import init_db

ANCHOR_DEFAULT = "2026-11-21"
RATE = {"SL": 0.55, "3A": 1.55, "2A": 2.2, "1A": 3.7}
CAP = {"SL": (72, 8, 20), "3A": (64, 8, 20), "2A": (46, 6, 10), "1A": (18, 2, 6)}

STATIONS = [
    ("PUNE", "Pune Junction", "Poona,Pune Jn,पुणे", "Pune"),
    ("NGP", "Nagpur", "Nagpur Jn,नागपुर", "Nagpur"),
    ("CSMT", "Mumbai CSMT", "Bombay,CST,VT,Mumbai CST,मुंबई", "Mumbai"),
    ("NDLS", "New Delhi", "Delhi,ND,नई दिल्ली,दिल्ली", "Delhi"),
    ("BPL", "Bhopal Junction", "Bhopal,भोपाल", "Bhopal"),
    ("NK", "Nashik Road", "Nasik,Nashik,नाशिक", "Nashik"),
    ("KYN", "Kalyan Junction", "Kalyan,कल्याण", "Kalyan"),
    ("JP", "Jaipur", "Jaipur Jn,जयपुर", "Jaipur"),
    ("ADI", "Ahmedabad", "Amdavad,Ahmedabad Jn,अहमदाबाद", "Ahmedabad"),
    ("LKO", "Lucknow", "Lucknow Jn,Lakhnau,लखनऊ", "Lucknow"),
    ("HWH", "Howrah", "Kolkata,Calcutta,हावड़ा", "Kolkata"),
    ("MAS", "Chennai Central", "Madras,Chennai,चेन्नई", "Chennai"),
    ("SBC", "Bengaluru City", "Bangalore,Bengaluru,बेंगलुरु", "Bengaluru"),
    ("SC", "Secunderabad", "Hyderabad,Secunderabad Jn,हैदराबाद", "Hyderabad"),
    ("BSB", "Varanasi", "Banaras,Benares,Kashi,वाराणसी", "Varanasi"),
]

# (train_no, name, start_time, runs_on, classes, [(code, km)...]) ; reverse trains are derived
ROUTES = [
    ("12123", "Pune-Nagpur Express", "18:00", "1234567", "SL,3A,2A,1A", [("PUNE", 0), ("NK", 210), ("BPL", 620), ("NGP", 1000)]),
    ("12301", "Mumbai-Delhi Rajdhani", "16:30", "1234567", "3A,2A,1A", [("CSMT", 0), ("KYN", 55), ("BPL", 830), ("NDLS", 1380)]),
    ("12401", "Delhi-Lucknow Shatabdi", "06:10", "1234567", "3A,2A", [("NDLS", 0), ("LKO", 500)]),
    ("12501", "Mumbai-Ahmedabad Express", "21:00", "1234567", "SL,3A,2A", [("CSMT", 0), ("ADI", 520)]),
    ("12601", "Chennai-Bengaluru Mail", "22:10", "1234567", "SL,3A,2A", [("MAS", 0), ("SBC", 350)]),
    ("12701", "Hyderabad-Bengaluru Express", "19:40", "1357", "SL,3A,2A", [("SC", 0), ("SBC", 570)]),
    ("12801", "Howrah-Varanasi Express", "20:30", "1234567", "SL,3A,2A,1A", [("HWH", 0), ("BSB", 680), ("LKO", 970)]),
    ("12901", "Delhi-Jaipur Intercity", "07:00", "1234567", "SL,3A", [("NDLS", 0), ("JP", 300)]),
    ("13001", "Pune-Mumbai Deccan", "07:15", "1234567", "SL,3A", [("PUNE", 0), ("KYN", 150), ("CSMT", 190)]),
    ("13101", "Nagpur-Hyderabad Express", "21:20", "246", "SL,3A,2A", [("NGP", 0), ("SC", 580)]),
    ("13201", "Bhopal-Delhi Express", "23:50", "1234567", "SL,3A,2A", [("BPL", 0), ("JP", 550), ("NDLS", 700)]),
    ("13301", "Ahmedabad-Jaipur Express", "13:15", "1234567", "SL,3A,2A", [("ADI", 0), ("JP", 640)]),
    ("13401", "Mumbai-Chennai Mail", "11:00", "1234567", "SL,3A,2A,1A", [("CSMT", 0), ("PUNE", 190), ("SBC", 1000), ("MAS", 1350)]),
]
# forced stop times for edge cases: (train_no, code) -> (HH:MM, day_offset)
FORCE = {("12301", "KYN"): ("00:30", 1)}  # boarding after midnight: departs 00:30 next calendar day


def _hm(m):
    return "%02d:%02d" % ((m // 60) % 24, m % 60)


def _tmin(s):
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def build_trains():
    trains, stops = [], []
    all_routes = []
    for no, name, start, runs, classes, st in ROUTES:
        all_routes.append((no, name, start, runs, classes, st))
    rev_no = 12124
    for no, name, start, runs, classes, st in ROUTES[:12]:
        total = st[-1][1]
        rev = [(c, total - k) for c, k in reversed(st)]
        a, b = name.split(" ")[0], name.split(" ", 1)[1]
        parts = name.split("-")
        rname = "%s-%s" % (parts[1].split(" ")[0], parts[0]) + " " + " ".join(parts[1].split(" ")[1:]) if len(parts) > 1 else name + " (Return)"
        # simple clear return name
        rname = name + " (Return)"
        shifted = _hm((_tmin(start) + 4 * 60) % 1440)
        all_routes.append((str(rev_no + 1000 * 0), rname, shifted, runs, classes, rev))
        rev_no += 1
    seen = set()
    for no, name, start, runs, classes, st in all_routes:
        assert no not in seen, no
        seen.add(no)
        trains.append((no, name, runs, classes))
        t = _tmin(start)
        day = 0
        prev_km = 0
        for i, (code, km) in enumerate(st):
            if i > 0:
                t += int((km - prev_km) / 55.0 * 60) + 10
                while t >= 1440:
                    t -= 1440
                    day += 1
            prev_km = km
            dep = _hm(t)
            d = day
            if (no, code) in FORCE:
                dep, d = FORCE[(no, code)]
                t, day = _tmin(dep), d
            arr = "" if i == 0 else _hm(max(0, t - 5) if t >= 5 else t)
            dep_s = "" if i == len(st) - 1 else dep
            if i == len(st) - 1:
                arr = dep
            stops.append((no, code, i + 1, arr, dep_s, d, km))
    return trains, stops


def fare_for(no, cls, km):
    if no == "12123" and km == 1000 and cls in ("SL", "3A", "2A", "1A"):  # pinned for hand-calculated tests
        return {"SL": 770, "3A": 2040, "2A": 2900, "1A": 4900}[cls]
    return int(round(km * RATE[cls] / 10.0) * 10) or 10


def seed_generated(db, anchor=ANCHOR_DEFAULT, rng_seed=42, progress=None):
    rnd = random.Random(rng_seed)
    init_db(db)
    for t in ["stations", "trains", "train_stops", "fares", "seats", "passengers", "bookings", "booking_travellers",
              "actions", "settings", "settings_history", "documents", "sessions", "handoffs", "audit"]:
        db.execute("DELETE FROM %s" % t)
    P = progress or (lambda *a, **k: None)
    anchor_d = dt.date.fromisoformat(anchor)

    db.executemany("INSERT INTO stations VALUES(?,?,?,?)", STATIONS); P("stations")
    trains, stops = build_trains()
    db.executemany("INSERT INTO trains VALUES(?,?,?,?)", trains)
    db.executemany("INSERT INTO train_stops VALUES(?,?,?,?,?,?,?)", stops); P("trains+stops")

    by_train = {}
    for no, code, order, arr, dep, day, km in stops:
        by_train.setdefault(no, []).append((order, code, km))
    fares = []
    for no, name, runs, classes in trains:
        st = sorted(by_train[no])
        for i in range(len(st)):
            for j in range(i + 1, len(st)):
                for c in classes.split(","):
                    fares.append((no, c, st[i][1], st[j][1], fare_for(no, c, st[j][2] - st[i][2])))
    db.executemany("INSERT INTO fares VALUES(?,?,?,?,?)", fares); P("fares")

    seats = []
    for no, name, runs, classes in trains:
        for d in range(0, 14):
            jd = anchor_d + dt.timedelta(days=d)
            if str(jd.isoweekday()) not in runs:
                continue
            for c in classes.split(","):
                cap, rcap, wcap = CAP[c]
                mode = rnd.random()
                if mode < 0.18:      # full with waiting list
                    av, rac, wl = 0, 0, rnd.randint(1, wcap)
                elif mode < 0.30:    # only RAC left
                    av, rac, wl = 0, rnd.randint(1, rcap), 0
                elif mode < 0.38:    # nearly full
                    av, rac, wl = rnd.randint(1, 4), rcap, 0
                else:
                    av, rac, wl = rnd.randint(5, cap), rcap, 0
                seats.append((no, jd.isoformat(), c, av, rac, wl, cap, rcap, wcap))
    # pin: 12123 3A on anchor+3 has seats; SL on anchor+4 is full with WL
    pins = {("12123", (anchor_d + dt.timedelta(days=3)).isoformat(), "3A"): (12, 8, 0),
            ("12123", (anchor_d + dt.timedelta(days=4)).isoformat(), "SL"): (0, 0, 14)}
    seats = [s if (s[0], s[1], s[2]) not in pins else s[:3] + pins[(s[0], s[1], s[2])] + s[6:] for s in seats]
    db.executemany("INSERT INTO seats VALUES(?,?,?,?,?,?,?,?,?)", seats); P("seats")

    first = ["Aarav", "Vivaan", "Ananya", "Diya", "Rohan", "Priya", "Karan", "Neha", "Sanjay", "Meera", "Arjun",
             "Isha", "Vikram", "Pooja", "Rahul", "Kavya", "Amit", "Sneha", "Nikhil", "Riya", "Manoj", "Divya",
             "Suresh", "Anjali", "Deepak"]
    last = ["Sharma", "Verma", "Patil", "Singh", "Iyer", "Khan", "Reddy", "Joshi", "Gupta", "Nair", "Mehta",
            "Das", "Kulkarni", "Yadav", "Soni"]
    langs = ["en"] * 10 + ["hi"] * 7 + ["hinglish"] * 8
    rnd.shuffle(langs)
    cities = [s[3] for s in STATIONS]
    pas = []
    for i in range(25):
        pas.append(("P%03d" % (i + 1), "%s %s" % (first[i], rnd.choice(last)), "%04d" % rnd.randint(1000, 9999),
                    langs[i], rnd.choice(cities)))
    pas[0] = ("P001", "Aarav Sharma", "4821", "en", "Pune")      # demo passenger (English)
    pas[1] = ("P002", "Ananya Verma", "7305", "hi", "Delhi")     # Hindi
    pas[2] = ("P003", "Rohan Patil", "1593", "hinglish", "Nagpur")  # Hinglish
    db.executemany("INSERT INTO passengers VALUES(?,?,?,?,?)", pas); P("passengers")

    # bookings
    stop_idx = {no: sorted(v) for no, v in by_train.items()}
    fare_map = {(f[0], f[1], f[2], f[3]): f[4] for f in fares}
    tinfo = {t[0]: t for t in trains}
    bookings, travs = [], []
    seq = [1000]

    def mk(pid, no, jdoff, frm, to, cls, ntrav, status, tatkal=0, bid=None, ages=None, names=None):
        seq[0] += 1
        bid = bid or "BK%d" % seq[0]
        jd = (anchor_d + dt.timedelta(days=jdoff)).isoformat()
        base = fare_map[(no, cls, frm, to)]
        tl = []
        for k in range(ntrav):
            age = (ages or [rnd.randint(22, 60)] * ntrav)[k]
            nm = (names or [None] * ntrav)[k] or "%s %s" % (rnd.choice(first), rnd.choice(last))
            fp = base // 2 if 5 <= age <= 11 else (0 if age < 5 else base)
            if age >= 60:
                fp = int(round(base * 0.6))
            if tatkal and cls == "SL":
                fp += 150
            if status == "confirmed":
                ts = "CNF"
            elif status == "rac":
                ts = "RAC"
            elif status == "waitlisted":
                ts = "WL"
            elif status == "cancelled":
                ts = "CAN"
            else:
                ts = "CNF"
            tl.append((bid, nm, age, ts, "%s%d" % (cls[0], rnd.randint(1, 9)) if ts == "CNF" else "",
                       str(rnd.randint(1, 72)) if ts == "CNF" else "", fp))
        total = sum(t[6] for t in tl)
        booked = (dt.datetime.fromisoformat(jd) - dt.timedelta(days=rnd.randint(5, 40))).strftime("%Y-%m-%dT10:00:00+05:30")
        refunded = total if status == "train_cancelled" else 0
        bookings.append((bid, pid, no, jd, frm, to, cls, total, status, booked, tatkal, refunded))
        travs.extend(tl)
        return bid

    # scenario bookings (stable ids used by tests and the demo)
    mk("P001", "12123", 3, "PUNE", "NGP", "3A", 1, "confirmed", bid="BK1001", ages=[34], names=["Aarav Sharma"])
    mk("P001", "12123", 4, "PUNE", "NGP", "SL", 2, "waitlisted", bid="BK1002", ages=[30, 8], names=["Aarav Sharma", "Mira Sharma"])
    mk("P001", "12123", 6, "NK", "NGP", "2A", 2, "confirmed", bid="BK1003", ages=[34, 31], names=["Aarav Sharma", "Neha Sharma"])
    mk("P001", "12301", 2, "KYN", "NDLS", "3A", 1, "confirmed", bid="BK1004", ages=[34], names=["Aarav Sharma"])   # boards 00:30
    mk("P001", "12123", 1, "PUNE", "NGP", "SL", 1, "cancelled", bid="BK1005", ages=[34], names=["Aarav Sharma"])
    mk("P002", "12401", 5, "NDLS", "LKO", "3A", 1, "confirmed", bid="BK1006", ages=[41], names=["Ananya Verma"])
    mk("P002", "12901", 3, "NDLS", "JP", "SL", 2, "rac", bid="BK1007", ages=[41, 12], names=["Ananya Verma", "Ishaan Verma"])
    mk("P003", "13101", 2, "NGP", "SC", "SL", 1, "confirmed", bid="BK1008", ages=[29], names=["Rohan Patil"], tatkal=1)
    mk("P003", "13201", 7, "BPL", "NDLS", "2A", 1, "waitlisted", bid="BK1009", ages=[29], names=["Rohan Patil"])
    mk("P004", "12501", 4, "CSMT", "ADI", "3A", 2, "confirmed", bid="BK1010", ages=[45, 62])

    plan = ["confirmed"] * 16 + ["rac"] * 4 + ["waitlisted"] * 6 + ["cancelled"] * 8 + ["train_cancelled"] * 6
    rnd.shuffle(plan)
    tlist = [t for t in trains]
    for status in plan[:40]:
        no, name, runs, classes = rnd.choice(tlist)
        st = stop_idx[no]
        i = rnd.randrange(0, len(st) - 1)
        j = rnd.randrange(i + 1, len(st))
        cls = rnd.choice(classes.split(","))
        mk(rnd.choice(pas[3:])[0] if rnd.random() < 0.85 else rnd.choice(pas[:3])[0], no, rnd.randint(1, 12),
           st[i][1], st[j][1], cls, rnd.randint(1, 3), status, tatkal=1 if (rnd.random() < 0.1 and cls == "SL") else 0)
    db.executemany("INSERT INTO bookings VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", bookings)
    db.executemany("INSERT INTO booking_travellers(booking_id,traveller_name,age,status,coach,berth,fare_paid) VALUES(?,?,?,?,?,?,?)", travs)
    P("bookings")

    now = "2026-11-21T00:00:00+05:30"
    db.executemany("INSERT INTO settings_history(name,value,effective_from,source_doc,section) VALUES(?,?,?,?,?)",
                   [(n, v, e, d, s) for n, v, e, d, s in content.SETTINGS])
    for n, (v, e, d) in {k: None for k in []}.items():
        pass
    cur = content.current_settings(anchor)
    src = {}
    for n, v, e, d, s in content.SETTINGS:
        if e <= anchor:
            src[n] = d
    db.executemany("INSERT INTO settings VALUES(?,?,?)", [(k, v, src.get(k, "")) for k, v in cur.items()]); P("settings")
    for d in content.all_documents():
        db.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",
                   (d["doc_id"], d["doc_type"], d["title"], d["topic"], d["effective_from"], d["authority"],
                    d["supersedes"], d["language"], d["text"], now))
    db.commit(); P("documents")
    return {"anchor": anchor}


def seed(db, anchor=ANCHOR_DEFAULT, progress=None):
    """Loads the supplied Ujjwal Rail dataset (data/official). The old generator above is kept only as a reference."""
    from core import official
    init_db(db)
    for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
        db.execute("DELETE FROM %s" % name)          # a reload replaces everything, so it can be run again with new data
    db.commit()
    official.load(db, progress)
    try:
        from rag import store
        store.invalidate(db)
    except Exception:
        pass
    return {"anchor": ANCHOR_DEFAULT}
