"""Add or replace a document while the service runs (no restart).
 1. remove instruction-like sentences (text is data, never orders)
 2. save the document with its metadata (type, effective date, supersedes, topic, language)
 3. read numbers out of the text into settings_history (shown to the operator to verify) or take an explicit override
 4. rebuild the search index"""
import datetime as dt
import re

from assistant import guardrails, language
from core import clock
from rag import store

AUTH = {"rule": 1, "circular": 2, "faq": 4}
CLS = {"sleeper": "SL", "sl": "SL", "3a": "3A", "3ac": "3A", "2a": "2A", "2ac": "2A", "1a": "1A", "1ac": "1A"}
MONEY = r"(?:Rs\.?|₹)\s?(\d[\d,]*)"


def sanitize(text: str):
    sentences = re.split(r"(?<=[.!?])\s+|\n", text)
    keep, removed = [], 0
    for s in sentences:
        if guardrails.injection_found(s):
            removed += 1
        else:
            keep.append(s)
    return "\n".join(keep), removed


def class_codes(db=None):
    codes = {"FP", "AC2", "AC3", "EC", "SL", "CC"}
    if db is not None:
        for r in db.execute("SELECT classes FROM trains"):
            codes |= {x.strip().upper() for x in (r[0] or "").split(",") if x.strip()}
    return codes


CLASS_WORDS = {"first premium": "FP", "executive chair": "EC", "city chair": "CC", "sleeper": "SL", "3ac": "AC3", "3a": "AC3", "2ac": "AC2", "2a": "AC2", "ac 3": "AC3", "ac 2": "AC2"}


def _cls_of(token, codes):
    t = token.lower().strip()
    return CLASS_WORDS.get(t) or (t.upper() if t.upper() in codes else None)


def extract_settings(text: str, db=None):
    """Best-effort extraction, in two ways. The operator verifies the result (it is returned by /ingest) and can send a 'settings' override.
    1. a circular that names its own setting key:   'Setting key: `cancel_fixed_charge_ac2`' ... 'Revised value: INR 260'
    2. a plain sentence:                            'the fixed cancellation charge for AC2 is Rs 260'  /  'Tatkal supplement for AC3 is Rs 330'"""
    out = []
    codes = class_codes(db)
    for m in re.finditer(r"(?is)setting key[^`\n]*[`:|\s]+`?([a-z0-9_.]+)`?.{0,400}?(?:revised|new) value[^\d\n]{0,12}?(?:INR|Rs\.?|₹)?\s?(\d[\d,.]*)", text):
        out.append({"name": m.group(1), "value": m.group(2).replace(",", "").rstrip("."), "section": "", "sentence": "setting key + revised value"})
    cls_rx = r"(first premium|executive chair|city chair|sleeper|3ac|3a|2ac|2a|ac ?3|ac ?2|" + "|".join(sorted((c.lower() for c in codes), key=len, reverse=True)) + r")"
    for m in re.finditer(r"(?m)^\s*(Section\s+[\d.]+)\s*:\s*(.*)$|^(.+)$", text):
        sec = m.group(1) or ""
        body = m.group(2) if m.group(2) is not None else m.group(3)
        for sent in re.split(r"(?<=[.;])\s+", body or ""):
            low = sent.lower()
            money = re.search(MONEY, sent) or re.search(r"(?:INR)\s?(\d[\d,]*)", sent)
            if "tatkal" in low and ("supplement" in low or "charge" in low):
                for cm in re.finditer(cls_rx + r"[^.;\d]{0,60}?(?:INR|Rs\.?|₹)\s?(\d[\d,]*)", sent, re.I):
                    c = _cls_of(cm.group(1).replace(" ", ""), codes) or _cls_of(cm.group(1), codes)
                    if c:
                        out.append({"name": "tatkal_supplement_" + c.lower(), "value": cm.group(2).replace(",", ""), "section": sec, "sentence": sent.strip()})
            elif "cancel" in low and ("charge" in low or "fee" in low) and "rac" not in low and "waitlist" not in low:
                for cm in re.finditer(cls_rx + r"[^.;\d]{0,60}?(?:INR|Rs\.?|₹)\s?(\d[\d,]*)", sent, re.I):
                    c = _cls_of(cm.group(1).replace(" ", ""), codes) or _cls_of(cm.group(1), codes)
                    if c:
                        out.append({"name": "cancel_fixed_charge_" + c.lower(), "value": cm.group(2).replace(",", ""), "section": sec, "sentence": sent.strip()})
            if "rac" in low.split() or " rac " in low:
                if money and "charge" in low or money and "deduct" in low:
                    out.append({"name": "cancellation.rac.charge", "value": money.group(1).replace(",", ""), "section": sec, "sentence": sent.strip()})
            if re.search(r"waiting ?list|\bwl\b|clerkage", low) and money and ("charge" in low or "clerkage" in low or "deduct" in low):
                out.append({"name": "cancellation.waitlist.charge", "value": money.group(1).replace(",", ""), "section": sec, "sentence": sent.strip()})
            if "boarding" in low and re.search(r"(\d+|six|twelve|four|three|two)\s*hours?", low):
                w = {"two": 2, "three": 3, "four": 4, "six": 6, "twelve": 12}
                h = re.search(r"(\d+|six|twelve|four|three|two)\s*hours?", low).group(1)
                out.append({"name": "boarding_change.cutoff_hours_before_origin", "value": str(w.get(h, h)), "section": sec, "sentence": sent.strip()})
    seen, res = set(), []
    for o in out:
        k = (o["name"], o["value"])
        if k not in seen:
            seen.add(k)
            res.append(o)
    return res


def refresh_current(db, today: dt.date):
    """Rebuild the 'settings' table (what is in force today) from the history."""
    rows = db.execute("SELECT name,value,effective_from,source_doc FROM settings_history WHERE effective_from<=? ORDER BY effective_from, id",
                      (today.isoformat(),)).fetchall()
    cur = {}
    for r in rows:
        cur[r["name"]] = (r["value"], r["source_doc"])
    db.execute("DELETE FROM settings")
    db.executemany("INSERT INTO settings VALUES(?,?,?)", [(k, v[0], v[1]) for k, v in cur.items()])


def infer_topic(text):
    for rx, tp in ((r"tatkal", "tatkal"), (r"\bpets?\b|assistance animal", "pets"), (r"luggage|baggage", "luggage"), (r"identity|\bid proof|photo id", "identity"),
                   (r"concession|discount", "concession"), (r"operator cancel|train (is |was )?cancel|delay", "disruption"),
                   (r"waiting ?list|\bwl\b|\brac\b", "waitlist"), (r"boarding", "boarding_change"), (r"refund|cancel", "refund"),
                   (r"complaint|harass|safety", "complaints"), (r"booking window|advance|opens", "booking")):
        if re.search(rx, text, re.I):
            return tp
    return "general"


def ingest(db, doc: dict, settings_override=None):
    from core import official
    raw = doc["text"]
    meta, body = official.parse_frontmatter(raw) if raw.lstrip().startswith("---") else ({}, raw)
    if meta:            # a full policy file (front matter + markdown) can be posted as it is
        doc = dict(doc)
        doc.setdefault("doc_id", None)
        doc["doc_id"] = doc.get("doc_id") or meta.get("doc_id")
        doc["title"] = doc.get("title") or meta.get("title")
        doc["doc_type"] = meta.get("document_type") or doc.get("doc_type") or "circular"
        doc["effective_from"] = doc.get("effective_from") or (meta.get("effective_from") or meta.get("published_at") or "")[:10] or None
        doc["language"] = doc.get("language") or official.LANG.get(meta.get("language", ""), None)
        refs = meta.get("references") or []
        if refs and not doc.get("supersedes") and meta.get("change_type") == "amendment":
            doc["supersedes"] = refs[0]["doc_id"]
        if refs and not doc.get("topic"):
            doc["topic"] = official.RULE_TOPIC.get(refs[0]["doc_id"], "")
        body = official.flatten_tables(official.trim_sections(official.md_to_sections(body), doc["doc_type"]))
        doc["text"] = body
    text, removed = sanitize(doc["text"])
    doc_type = doc.get("doc_type", "circular")
    doc_type = {"policy": "rule", "rules": "rule", "circulars": "circular", "faqs": "faq", "FAQ": "faq"}.get(doc_type, doc_type)
    doc_id = doc.get("doc_id") or "DOC-%s" % dt.datetime.now().strftime("%Y%m%d%H%M%S")
    eff = doc.get("effective_from") or clock.real_now().date().isoformat()
    lang = doc.get("language") or language.detect(text)
    lang = "hinglish" if lang == "hinglish" else lang
    topic = doc.get("topic") or infer_topic(doc.get("title", "") + " " + text)
    added = clock.real_now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    db.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
    db.execute("DELETE FROM settings_history WHERE source_doc=?", (doc_id,))
    db.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",
               (doc_id, doc_type, doc.get("title") or doc_id, topic, eff, AUTH.get(doc_type, 4), doc.get("supersedes") or "", lang, text, added))
    items = settings_override if settings_override else (extract_settings(raw if meta else text, db) if doc_type in ("rule", "circular") else [])
    applied = []
    for it in items:
        db.execute("INSERT INTO settings_history(name,value,effective_from,source_doc,section,extracted) VALUES(?,?,?,?,?,?)",
                   (it["name"], str(it["value"]), eff, doc_id, it.get("section", ""), 0 if settings_override else 1))
        applied.append({"name": it["name"], "value": str(it["value"]), "effective_from": eff, "section": it.get("section", ""),
                        "from": "override" if settings_override else "extracted"})
    refresh_current(db, clock.real_now().date())
    db.commit()
    store.invalidate(db)
    return {"doc_id": doc_id, "effective_from": eff, "authority": AUTH.get(doc_type, 4), "language": lang,
            "settings_applied": applied, "instruction_sentences_removed": removed,
            "note": "Check the extracted numbers; send a 'settings' override to correct them." if applied and not settings_override else ""}
