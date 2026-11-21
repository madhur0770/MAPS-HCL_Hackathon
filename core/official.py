"""Loads the supplied Ujjwal Rail dataset (data/official) into the database.
Nothing is generated here: stations, trains, fares, seats, passengers, bookings and the policy documents are read as given.
Money stays in PAISE (integer) everywhere in the code; only the display turns it into rupees."""
import json
import os
import re

from core import config

DIR = os.path.join(config.ROOT, "data", "official")
SYN = os.path.join(DIR, "synthetic")
POL = os.path.join(DIR, "policies")

WEEK = {"Mon": "1", "Tue": "2", "Wed": "3", "Thu": "4", "Fri": "5", "Sat": "6", "Sun": "7"}
RULE_TOPIC = {"RUL-001": "booking", "RUL-002": "classes", "RUL-003": "refund", "RUL-004": "waitlist", "RUL-005": "tatkal",
              "RUL-006": "identity", "RUL-007": "luggage", "RUL-008": "pets", "RUL-009": "concession",
              "RUL-010": "boarding_change", "RUL-011": "disruption", "RUL-012": "complaints"}
LANG = {"en": "en", "hi": "hi", "hinglish": "hinglish", "hi-Latn": "hinglish", "hi-en-Latn": "hinglish"}
SKIP_DOCS = {"RULE_INDEX", "FAQ_INDEX", "CIRCULAR_INDEX", "CIRCULAR_CHANGELOG", "OUTDATED_FAQS", "POLICY_ASSUMPTIONS"}


def _j(name):
    with open(os.path.join(SYN, name), encoding="utf-8") as f:
        return json.load(f)


def parse_frontmatter(text):
    """Tiny parser for the front matter used by these documents (scalars, and `references:` as a list of doc_id/section)."""
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    meta, refs, key = {}, [], None
    for line in m.group(1).split("\n"):
        if re.match(r"^\s+- doc_id:", line):
            refs.append({"doc_id": line.split(":", 1)[1].strip().strip('"')})
        elif re.match(r"^\s+section:", line) and refs:
            refs[-1]["section"] = line.split(":", 1)[1].strip().strip('"')
        elif re.match(r"^\s+- \S", line) and key:
            if not isinstance(meta.get(key), list):
                meta[key] = []
            meta[key].append(line.strip()[2:].strip())
        elif ":" in line and not line.startswith(" "):
            key, v = line.split(":", 1)
            key, v = key.strip(), v.strip().strip('"')
            meta[key] = v if v not in ("[]",) else []
    meta["references"] = refs
    return meta, m.group(2)


def md_to_sections(body):
    """Turn markdown headings into 'Section 3.3: Title' lines so the search index can cite them."""
    out, skip_h1 = [], True
    for line in body.split("\n"):
        if skip_h1 and line.startswith("# "):
            skip_h1 = False
            continue
        m = re.match(r"^#{2,3}\s+(\d+(?:\.\d+)?)\.?\s+(.*)$", line)
        if m:
            out.append("Section %s: %s." % (m.group(1), m.group(2)))
        else:
            out.append(line)
    text = "\n".join(out)
    text = re.sub(r"(?m)^(Section [\d.]+: [^\n]*\.)\n\s*\n(?=Section )", "", text)   # drop empty parent headings
    return text.strip()


def flatten_tables(text):
    """Markdown tables -> plain lines, so answers read well in any chat window and numbers stay next to their labels."""
    out, rows = [], []

    def flush():
        if not rows:
            return
        head = rows[0]
        body = rows[1:]
        if len(head) == 2 and head[0].lower() in ("field", "item", "setting"):
            out.extend("- %s: %s" % (r[0], r[1]) for r in body)
        else:
            for r in body:
                out.append("- " + r[0] + ": " + "; ".join("%s %s" % (h, v) for h, v in zip(head[1:], r[1:])) if len(r) > 1 else "- " + r[0])
        rows.clear()

    for line in text.split("\n"):
        if re.match(r"^\s*\|", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.match(r"^:?-{2,}:?$", c) for c in cells if c):
                continue
            rows.append(cells)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)


def trim_sections(text, typ):
    """Keep only the sections that carry facts. Rules: drop Purpose/Scope/Related. Circulars: drop Purpose/Reference. FAQs: question joins the answer.
    (Boilerplate sections match every query by title words and would hide the real answer.)"""
    parts = re.split(r"(?m)^(?=Section \d+(?:\.\d+)?: )", text)
    secs = []
    for p in parts:
        m = re.match(r"Section (\d+(?:\.\d+)?): ([^\n]*)\n?(.*)$", p.strip(), re.S)
        if m:
            secs.append([m.group(1), m.group(2), m.group(3).strip()])
    if typ == "faq":
        q = next((x for x in secs if x[0] == "1"), None)
        out = []
        for x in secs:
            if x[0] == "2":
                x[2] = ("Q: %s\nA: %s" % (q[2], x[2])) if q else x[2]
                out.append(x)
            elif x[0] == "4":
                out.append(x)
        secs = out
    else:
        drop = {"1", "2", "5"} if typ == "rule" else {"1", "2"}
        secs = [x for x in secs if x[0] not in drop] or secs
    return "\n\n".join("Section %s: %s\n%s" % (a, b, c) for a, b, c in secs)


def load_documents():
    docs, topic_of = [], dict(RULE_TOPIC)
    for sub in ("rules", "circulars", "faqs"):
        d = os.path.join(POL, sub)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md") or fn.rsplit(".", 1)[0] in SKIP_DOCS:
                continue
            with open(os.path.join(d, fn), encoding="utf-8") as f:
                meta, body = parse_frontmatter(f.read())
            if not meta.get("doc_id"):
                continue
            docs.append((meta, body))
    out = []
    for meta, body in docs:
        did = meta["doc_id"]
        typ = meta.get("document_type", "faq")
        refs = meta.get("references", [])
        topic = RULE_TOPIC.get(did) or (topic_of.get(refs[0]["doc_id"]) if refs else None)
        if topic is None and refs and refs[0]["doc_id"].startswith("CIR"):
            for m2, _ in docs:
                if m2["doc_id"] == refs[0]["doc_id"] and m2.get("references"):
                    topic = RULE_TOPIC.get(m2["references"][0]["doc_id"])
        topic = topic or "general"
        eff = (meta.get("effective_from") or meta.get("published_at") or "2026-11-01")[:10]
        sup = ""
        if typ == "circular" and meta.get("change_type") == "amendment" and refs:
            sup = refs[0]["doc_id"]
        out.append(dict(doc_id=did, doc_type=typ, title=meta.get("title", did), topic=topic, effective_from=eff,
                        authority={"rule": 1, "circular": 2, "faq": 4}[typ], supersedes=sup,
                        language=LANG.get(meta.get("language", "en"), "en"), text=flatten_tables(trim_sections(md_to_sections(body), typ)),
                        status=meta.get("status", ""), refs=refs))
    return out


def load(db, progress=None):
    P = progress or (lambda n: None)
    ins = lambda t, rows: db.executemany("INSERT INTO %s(%s) VALUES(%s)" % (t, ",".join(rows[0].keys()), ",".join("?" * len(rows[0]))), [tuple(r.values()) for r in rows])  # noqa: E731
    ins("stations", [dict(station_code=s["station_code"], name=s["name"], other_names=",".join(s["other_names"]), city=s["city"]) for s in _j("stations.json")]); P("stations")
    ins("trains", [dict(train_no=t["train_no"], name=t["name"], runs_on="".join(WEEK[d] for d in t["runs_on"]), classes=",".join(t["classes"])) for t in _j("trains.json")]); P("trains")
    ins("train_stops", [dict(train_no=s["train_no"], station_code=s["station_code"], stop_order=s["stop_order"], arrival=s["arrival"], departure=s["departure"], day_offset=s["day_offset"]) for s in _j("train_stops.json")]); P("train stops")
    fares = _j("fares.json")
    ins("fares", [dict(train_no=f["train_no"], **{"class": f["class"]}, from_code=f["from_code"], to_code=f["to_code"], fare=f["fare"]) for f in fares]); P("fares")
    ins("seats", [dict(train_no=s["train_no"], journey_date=s["journey_date"], **{"class": s["class"]}, available=s["available"], rac=s["rac"], waitlist=s["waitlist"],
                       capacity=s["confirmed_capacity"], rac_capacity=s["rac_capacity"], wl_capacity=s["waitlist_capacity"]) for s in _j("seats.json")]); P("seats")
    ins("service_cancellations", [dict(train_no=c["train_no"], journey_date=c["journey_date"], reason=c["reason"], announced_at=c["announced_at"]) for c in _j("service_cancellations.json")])
    ins("passengers", [dict(passenger_id=p["passenger_id"], name=p["name"], phone_last4=p["phone_last4"], preferred_language=p["preferred_language"], home_city=p["home_city"]) for p in _j("passengers.json")]); P("passengers")
    fare = {(f["train_no"], f["class"], f["from_code"], f["to_code"]): f["fare"] for f in fares}
    bks = _j("bookings.json")
    ins("bookings", [dict(booking_id=b["booking_id"], passenger_id=b["passenger_id"], train_no=b["train_no"], journey_date=b["journey_date"], from_code=b["from_code"], to_code=b["to_code"],
                          **{"class": b["class"]}, amount_paid=b["amount_paid"], status=b["status"], booked_at=b["booked_at"], tatkal=0, refunded=0,
                          boarding_datetime=b["boarding_datetime"], cancelled_at=b["cancelled_at"], cancellation_type=b["cancellation_type"]) for b in bks]); P("bookings")
    bk = {b["booking_id"]: b for b in bks}
    rows = []
    for t in _j("booking_travellers.json"):
        b = bk[t["booking_id"]]
        rows.append(dict(booking_id=t["booking_id"], traveller_name=t["traveller_name"], age=t["age"], status=t["status"], coach=t["coach"], berth=t["berth"],
                         fare_paid=fare[(b["train_no"], b["class"], b["from_code"], b["to_code"])]))
    ins("booking_travellers", rows); P("travellers")
    sv = json.load(open(os.path.join(DIR, "setting_versions.json"), encoding="utf-8"))
    for r in sv:
        db.execute("INSERT INTO settings_history(name,value,effective_from,source_doc,section) VALUES(?,?,?,?,?)",
                   (r["name"], r["value"], r["effective_from"][:10], r["source_doc"], ""))
    d0 = "2026-11-21"
    snap = {}
    for r in sorted(sv, key=lambda r: r["effective_from"]):
        if r["effective_from"][:10] <= d0:
            snap[r["name"]] = (r["value"], r["source_doc"])
    db.executemany("INSERT INTO settings VALUES(?,?,?)", [(k, v[0], v[1]) for k, v in snap.items()])
    docs = load_documents()
    for d in docs:
        db.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)", (d["doc_id"], d["doc_type"], d["title"], d["topic"], d["effective_from"], d["authority"],
                                                                         d["supersedes"], d["language"], d["text"], "2026-11-21T00:00:00+05:30"))
    db.commit(); P("documents")
    return {"documents": len(docs), "settings": len(sv)}
