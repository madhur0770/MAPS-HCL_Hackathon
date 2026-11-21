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


def extract_settings(text: str):
    """Best-effort extraction. Returns [{name, value, section, sentence}] - the operator verifies these."""
    out = []
    for m in re.finditer(r"(?m)^\s*(Section\s+\d+)\s*:\s*(.+)$", text):
        sec, body = m.group(1), m.group(2)
        for sent in re.split(r"(?<=[.;])\s+", body):
            low = sent.lower()
            if "cancellation charge" in low or "cancel" in low and "charge" in low:
                for cm in re.finditer(r"\b(sleeper|sl|3a|3ac|2a|2ac|1a|1ac)\b[^.;\d]{0,60}?" + MONEY, sent, re.I):
                    out.append({"name": "cancel_charge_" + CLS[cm.group(1).lower()], "value": cm.group(2).replace(",", ""), "section": sec, "sentence": sent.strip()})
            if "tatkal" in low:
                m2 = re.search(r"(?:sleeper|\bsl\b)[^.;\d]{0,80}?" + MONEY, sent, re.I) or re.search(MONEY, sent)
                if m2 and "charge" in low:
                    out.append({"name": "tatkal_charge_SL", "value": m2.group(1).replace(",", ""), "section": sec, "sentence": sent.strip()})
            if "boarding" in low and re.search(r"(\d+)\s*hours?", low):
                h = re.search(r"(\d+)\s*hours?", low).group(1)
                out.append({"name": "boarding_change_cutoff_hours", "value": h, "section": sec, "sentence": sent.strip()})
            if "clerkage" in low:
                m3 = re.search(MONEY, sent)
                if m3:
                    out.append({"name": "wl_clerkage", "value": m3.group(1).replace(",", ""), "section": sec, "sentence": sent.strip()})
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


def ingest(db, doc: dict, settings_override=None):
    text, removed = sanitize(doc["text"])
    doc_type = doc.get("doc_type", "circular")
    doc_id = doc.get("doc_id") or "DOC-%s" % dt.datetime.now().strftime("%Y%m%d%H%M%S")
    eff = doc.get("effective_from") or clock.real_now().date().isoformat()
    lang = doc.get("language") or language.detect(text)
    lang = "hinglish" if lang == "hinglish" else lang
    topic = doc.get("topic") or ""
    added = clock.real_now().strftime("%Y-%m-%dT%H:%M:%S.%f")
    db.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
    db.execute("DELETE FROM settings_history WHERE source_doc=?", (doc_id,))
    db.execute("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",
               (doc_id, doc_type, doc.get("title") or doc_id, topic, eff, AUTH.get(doc_type, 4), doc.get("supersedes") or "", lang, text, added))
    items = settings_override if settings_override else (extract_settings(text) if doc_type in ("rule", "circular") else [])
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
