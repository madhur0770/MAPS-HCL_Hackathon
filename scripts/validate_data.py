"""Checks the generated data against the brief's minimums and basic consistency. Live progress bar."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core import db as dbm, config
from core.progress import Progress

def q(d, sql, *a): return d.execute(sql, a).fetchall()
def one(d, sql, *a): return d.execute(sql, a).fetchone()[0]

def checks(d):
    C = []
    def add(name, ok, detail=""): C.append((name, bool(ok), detail))
    for t in dbm.TABLES_FROM_BRIEF:
        add("table %s exists" % t, one(d, "SELECT count(*) FROM sqlite_master WHERE name=?", t) == 1)
    add("15+ stations", one(d, "SELECT count(*) FROM stations") >= 15)
    add("25+ trains", one(d, "SELECT count(*) FROM trains") >= 25, str(one(d, "SELECT count(*) FROM trains")))
    add("25+ passengers", one(d, "SELECT count(*) FROM passengers") >= 25)
    add("50+ bookings", one(d, "SELECT count(*) FROM bookings") >= 50, str(one(d, "SELECT count(*) FROM bookings")))
    for s in ("confirmed", "rac", "waitlisted", "cancelled", "train_cancelled"):
        add("bookings with status %s" % s, one(d, "SELECT count(*) FROM bookings WHERE status=?", s) >= 1)
    add("12 rules docs", one(d, "SELECT count(*) FROM documents WHERE doc_type='rule'") >= 12)
    add("6 circulars", one(d, "SELECT count(*) FROM documents WHERE doc_type='circular'") >= 6)
    add("20 FAQs", one(d, "SELECT count(*) FROM documents WHERE doc_type='faq'") >= 20)
    add("2+ circulars change earlier rules", one(d, "SELECT count(*) FROM documents WHERE doc_type='circular' AND supersedes!=''") >= 2)
    add("1+ future-dated circular", one(d, "SELECT count(*) FROM documents WHERE doc_type='circular' AND effective_from>'2026-11-21'") >= 1)
    add("Hindi and Hinglish FAQs", one(d, "SELECT count(*) FROM documents WHERE doc_type='faq' AND language IN ('hi','hinglish')") >= 3)
    add("settings has name,value,source_doc", [r[1] for r in q(d, "PRAGMA table_info(settings)")] == ["name", "value", "source_doc"])
    add("every setting source_doc exists", one(d, "SELECT count(*) FROM settings s WHERE source_doc!='' AND source_doc NOT IN (SELECT doc_id FROM documents)") == 0)
    add("every history source_doc exists", one(d, "SELECT count(*) FROM settings_history WHERE source_doc NOT IN (SELECT doc_id FROM documents)") == 0)
    add("14 days of seats", one(d, "SELECT count(DISTINCT journey_date) FROM seats") >= 14)
    add("seat cases: full+WL, RAC-only, available",
        one(d, "SELECT count(*) FROM seats WHERE available=0 AND waitlist>0") > 0 and
        one(d, "SELECT count(*) FROM seats WHERE available=0 AND rac>0") > 0 and
        one(d, "SELECT count(*) FROM seats WHERE available>0") > 0)
    add("stops reference stations", one(d, "SELECT count(*) FROM train_stops WHERE station_code NOT IN (SELECT station_code FROM stations)") == 0)
    add("fares reference trains", one(d, "SELECT count(*) FROM fares WHERE train_no NOT IN (SELECT train_no FROM trains)") == 0)
    add("bookings reference passengers/trains", one(d, "SELECT count(*) FROM bookings WHERE passenger_id NOT IN (SELECT passenger_id FROM passengers) OR train_no NOT IN (SELECT train_no FROM trains)") == 0)
    add("every booking has a fare row", one(d, "SELECT count(*) FROM bookings b WHERE NOT EXISTS (SELECT 1 FROM fares f WHERE f.train_no=b.train_no AND f.class=b.class AND f.from_code=b.from_code AND f.to_code=b.to_code)") == 0)
    add("every booking has travellers", one(d, "SELECT count(*) FROM bookings WHERE booking_id NOT IN (SELECT booking_id FROM booking_travellers)") == 0)
    add("booking amount = sum traveller fares", one(d, "SELECT count(*) FROM bookings b WHERE amount_paid != (SELECT sum(fare_paid) FROM booking_travellers t WHERE t.booking_id=b.booking_id)") == 0)
    add("a train with after-midnight stop", one(d, "SELECT count(*) FROM train_stops WHERE day_offset>=1") > 0)
    add("a boarding stop at 00:30", one(d, "SELECT count(*) FROM train_stops WHERE departure='00:30' AND day_offset=1") > 0)
    add("no full phone numbers stored", one(d, "SELECT count(*) FROM passengers WHERE length(phone_last4)!=4") == 0)
    add("pinned booking BK1001 fare 2040", one(d, "SELECT amount_paid FROM bookings WHERE booking_id='BK1001'") == 2040)
    add("rules text matches settings (RULE-03 mentions 60/180/240)", all(x in one(d, "SELECT text FROM documents WHERE doc_id='RULE-03'") for x in ("Rs 60", "Rs 180", "Rs 240")))
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
