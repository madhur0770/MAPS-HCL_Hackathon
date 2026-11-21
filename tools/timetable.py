"""Stations, train search, departure times (boarding-station based, handles after-midnight)."""
import datetime as dt
import re

from core import clock


def norm(s: str) -> str:
    return re.sub(r"[^\wऀ-ॿ]+", " ", s.lower()).strip()


def station_index(db):
    idx = {}
    for r in db.execute("SELECT * FROM stations"):
        names = [r["station_code"], r["name"], r["city"]] + [x for x in (r["other_names"] or "").split(",") if x]
        for n in names:
            idx[norm(n)] = r["station_code"]
    return idx


def resolve_station(db, text: str):
    """Exact alias match first, then whole-word match inside a longer sentence. Returns code or None."""
    idx = station_index(db)
    t = norm(text)
    if t in idx:
        return idx[t]
    best = None
    for alias, code in sorted(idx.items(), key=lambda kv: -len(kv[0])):
        if len(alias) < 2:
            continue
        if re.search(r"(?<![\wऀ-ॿ])%s(?![\wऀ-ॿ])" % re.escape(alias), t):
            best = code
            break
    return best


def find_stations_in(db, text: str):
    """All stations mentioned in order of appearance (for 'Pune to Nagpur')."""
    idx = station_index(db)
    t = norm(text)
    hits = []
    for alias, code in idx.items():
        if len(alias) < 3 and alias != code.lower():
            continue
        for m in re.finditer(r"(?<![\wऀ-ॿ])%s(?![\wऀ-ॿ])" % re.escape(alias), t):
            hits.append((m.start(), -len(alias), code))
    hits.sort()
    out = []
    for pos, _, code in hits:
        if code not in out:
            out.append(code)
    return out


def station_name(db, code):
    r = db.execute("SELECT name FROM stations WHERE station_code=?", (code,)).fetchone()
    return r["name"] if r else code


def stops_of(db, train_no):
    return db.execute("SELECT * FROM train_stops WHERE train_no=? ORDER BY stop_order", (train_no,)).fetchall()


def _combine(origin_date: str, hhmm: str, day_offset: int) -> dt.datetime:
    d = dt.date.fromisoformat(origin_date) + dt.timedelta(days=day_offset)
    h, m = hhmm.split(":")
    return dt.datetime(d.year, d.month, d.day, int(h), int(m), tzinfo=clock.IST)


def departure_dt(db, train_no, journey_date, code) -> dt.datetime:
    """journey_date is the ORIGIN date. Departure from `code` = origin date + day_offset + time."""
    r = db.execute("SELECT departure, arrival, day_offset FROM train_stops WHERE train_no=? AND station_code=?",
                   (train_no, code)).fetchone()
    hhmm = r["departure"] or r["arrival"]
    return _combine(journey_date, hhmm, r["day_offset"])


def arrival_dt(db, train_no, journey_date, code) -> dt.datetime:
    r = db.execute("SELECT departure, arrival, day_offset FROM train_stops WHERE train_no=? AND station_code=?",
                   (train_no, code)).fetchone()
    hhmm = r["arrival"] or r["departure"]
    return _combine(journey_date, hhmm, r["day_offset"])


def runs_on_date(runs_on: str, origin_date: str) -> bool:
    return str(dt.date.fromisoformat(origin_date).isoweekday()) in runs_on


def search_trains(db, frm: str, to: str, travel_date: str):
    """travel_date = the date the passenger leaves their FROM station. Converted to the train's origin date."""
    out = []
    for t in db.execute("SELECT * FROM trains"):
        st = {r["station_code"]: r for r in stops_of(db, t["train_no"])}
        if frm in st and to in st and st[frm]["stop_order"] < st[to]["stop_order"]:
            off = st[frm]["day_offset"]
            origin = (dt.date.fromisoformat(travel_date) - dt.timedelta(days=off)).isoformat()
            if not runs_on_date(t["runs_on"], origin):
                continue
            dep = departure_dt(db, t["train_no"], origin, frm)
            arr = arrival_dt(db, t["train_no"], origin, to)
            out.append({"train_no": t["train_no"], "name": t["name"], "origin_date": origin, "from": frm, "to": to,
                        "departs": dep, "arrives": arr, "classes": t["classes"].split(","),
                        "after_midnight": dep.date().isoformat() != origin})
    out.sort(key=lambda x: x["departs"])
    return out
