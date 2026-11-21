"""Checks the generated data against the brief's minimums and basic consistency. Live progress bar."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as dbm, config
from core.progress import Progress

def q(d, sql, *a): return d.execute(sql, a).fetchall()
def one(d, sql, *a): return d.execute(sql, a).fetchone()[0]

def checks(d):
    """Works on the supplied kit and on any judge-supplied data loaded the same way: nothing here names a specific station, train or booking."""
    C = []
    def add(name, ok, detail=""): C.append((name, bool(ok), detail))
    for t in dbm.TABLES_FROM_BRIEF:
        add("table %s exists" % t, one(d, "SELECT count(*) FROM sqlite_master WHERE name=?", t) == 1)
    add("15+ stations", one(d, "SELECT count(*) FROM stations") >= 15, str(one(d, "SELECT count(*) FROM stations")))
    add("25+ trains", one(d, "SELECT count(*) FROM trains") >= 25, str(one(d, "SELECT count(*) FROM trains")))
    add("25+ passengers", one(d, "SELECT count(*) FROM passengers") >= 25)
    add("50+ bookings", one(d, "SELECT count(*) FROM bookings") >= 50, str(one(d, "SELECT count(*) FROM bookings")))
    for s_ in ("CONFIRMED", "RAC", "WAITLISTED", "CANCELLED", "OPERATOR_CANCELLED"):
        add("bookings with status %s" % s_, one(d, "SELECT count(*) FROM bookings WHERE status=?", s_) >= 1)
    add("12+ rules", one(d, "SELECT count(*) FROM documents WHERE doc_type='rule'") >= 12)
    add("6+ circulars", one(d, "SELECT count(*) FROM documents WHERE doc_type='circular'") >= 6)
    add("20+ FAQs", one(d, "SELECT count(*) FROM documents WHERE doc_type='faq'") >= 20)
    add("circulars that change earlier rules", one(d, "SELECT count(*) FROM documents WHERE doc_type='circular' AND supersedes!=''") >= 2)
    add("a circular dated after the demo day", one(d, "SELECT count(*) FROM documents WHERE doc_type='circular' AND effective_from>'2026-11-21'") >= 1)
    add("Hindi / Hinglish documents", one(d, "SELECT count(*) FROM documents WHERE language IN ('hi','hinglish')") >= 3)
    add("settings has name,value,source_doc", [r[1] for r in q(d, "PRAGMA table_info(settings)")][:3] == ["name", "value", "source_doc"])
    add("93 dated setting rows or more", one(d, "SELECT count(*) FROM settings_history") >= 50, str(one(d, "SELECT count(*) FROM settings_history")))
    add("every setting source_doc exists", one(d, "SELECT count(*) FROM settings_history WHERE source_doc NOT IN ('', 'SYSTEM-CONFIG') AND source_doc NOT IN (SELECT doc_id FROM documents)") == 0)
    add("seat data for 14+ days", one(d, "SELECT count(DISTINCT journey_date) FROM seats") >= 14, str(one(d, "SELECT count(DISTINCT journey_date) FROM seats")))
    add("seat cases: waiting list, RAC, available",
        one(d, "SELECT count(*) FROM seats WHERE available=0 AND waitlist>0") > 0 and
        one(d, "SELECT count(*) FROM seats WHERE available=0 AND rac>0") > 0 and
        one(d, "SELECT count(*) FROM seats WHERE available>0") > 0)
    add("stops reference stations", one(d, "SELECT count(*) FROM train_stops WHERE station_code NOT IN (SELECT station_code FROM stations)") == 0)
    add("fares reference trains", one(d, "SELECT count(*) FROM fares WHERE train_no NOT IN (SELECT train_no FROM trains)") == 0)
    add("bookings reference passengers and trains", one(d, "SELECT count(*) FROM bookings WHERE passenger_id NOT IN (SELECT passenger_id FROM passengers) OR train_no NOT IN (SELECT train_no FROM trains)") == 0)
    add("every booking has a fare row", one(d, "SELECT count(*) FROM bookings b WHERE NOT EXISTS (SELECT 1 FROM fares f WHERE f.train_no=b.train_no AND f.class=b.class AND f.from_code=b.from_code AND f.to_code=b.to_code)") == 0)
    add("every booking has travellers", one(d, "SELECT count(*) FROM bookings WHERE booking_id NOT IN (SELECT booking_id FROM booking_travellers)") == 0)
    add("booking amount = sum of traveller fares", one(d, "SELECT count(*) FROM bookings b WHERE amount_paid != (SELECT sum(fare_paid) FROM booking_travellers t WHERE t.booking_id=b.booking_id)") == 0)
    add("a train with an after-midnight stop (day_offset)", one(d, "SELECT count(*) FROM train_stops WHERE day_offset>=1") > 0)
    add("two stations share a city name (disambiguation test)", one(d, "SELECT count(*) FROM (SELECT city FROM stations GROUP BY city HAVING count(*)>1)") >= 1)
    add("5+ station aliases", one(d, "SELECT sum(length(other_names)-length(replace(other_names, ',', ''))+1) FROM stations WHERE other_names!=''") >= 5)
    add("no full phone numbers stored", one(d, "SELECT count(*) FROM passengers WHERE length(phone_last4)!=4") == 0)
    add("seats within capacity", one(d, "SELECT count(*) FROM seats WHERE available>capacity OR rac>rac_capacity OR waitlist>wl_capacity") == 0)
    add("every rule has a topic", one(d, "SELECT count(*) FROM documents WHERE doc_type='rule' AND (topic IS NULL OR topic='')") == 0)
    return C

def main():
    d = dbm.connect(os.getenv("DB_PATH", config.db_path()))
    C = checks(d)
    p = Progress(len(C), "validate data")
    bad = []
    for name, ok, det in C:
        p.step(1, name[:40])
        if not ok: bad.append((name, det))
    p.finish("%d/%d checks passed" % (len(C) - len(bad), len(C)))
    for n, dtl in bad: print("  FAIL:", n, dtl)
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
