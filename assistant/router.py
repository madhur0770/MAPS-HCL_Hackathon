"""The brain. One function: handle(). It follows the 9 steps:
 1 guard the input  2 understand  3 fill in context (session memory)  4 route by intent  5 run tools
 6 write the answer (templates, numbers from code)  7 correctors  8 output guard  9 audit record
No step lets the language model decide a number or change a booking."""
import datetime as dt
import json
import re
import time
import uuid

from actions import manager as am
from assistant import correctors, guardrails, handoff, i18n, language, llm, understand as und
from assistant.i18n import t
from core import clock, config
from core.text import fmt_date, fmt_dt, fmt_hours, inr
from rag import retrieval, store
from tools import bookings as bk, deadlines, fares, refund, seats, settings as cfg, timetable as tt

MAX_FOLLOWUPS = 2


# ------------------------------------------------------------------ session memory
def load_session(db, session_id, passenger_id):
    r = db.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
    if r and r["passenger_id"] == passenger_id:
        return json.loads(r["slots"] or "{}")
    return {}


def save_session(db, session_id, passenger_id, slots, as_of):
    db.execute("INSERT OR REPLACE INTO sessions VALUES(?,?,?,?)", (session_id, passenger_id, json.dumps(slots), clock.iso(as_of)))
    db.commit()


def reply(answer_type, answer, sources=None, tools=None, pending=None, handed=False, doc_text="", extra=None):
    return {"answer_type": answer_type, "answer": answer, "sources": sources or [], "tools": tools or [],
            "pending_action": pending, "handed_to_human": handed, "_doc_text": doc_text, "_extra": extra or {}}


def dedupe(src):
    out, seen = [], set()
    for s in src:
        k = (s["doc_id"], s["section"])
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


# ------------------------------------------------------------------ main entry
def handle(db, passenger_id, session_id, message, as_of_in=None, trace_id=None):
    t0 = time.time()
    trace_id = trace_id or "TR-" + uuid.uuid4().hex[:12].upper()
    as_of = clock.resolve_as_of(as_of_in)
    sess = load_session(db, session_id, passenger_id)
    lang = language.detect(message)
    if lang == "en" and len(message.split()) < 3 and sess.get("lang"):
        lang = sess["lang"]
    audit = {"trace_id": trace_id, "ts": clock.iso(as_of), "passenger_id": passenger_id, "session_id": session_id,
             "input": guardrails.mask(message), "language": lang, "steps": []}
    step = lambda _n, **kw: audit["steps"].append(dict(step=_n, **kw))  # noqa: E731

    text = message
    injected = guardrails.injection_found(message)
    if guardrails.has_secret(message):
        step("input_guard", result="secret_detected")
        r = reply("refusal", t("refuse_secret", lang))
        return finish(db, r, audit, trace_id, passenger_id, session_id, lang, sess, as_of, t0)
    if injected:
        step("input_guard", result="injection_detected", matched=injected[:60])
        text = guardrails.strip_injection(message)
    u = und.understand(db, text, as_of, sess)
    intent, slots = u["intent"], u["slots"]
    step("understand", intent=intent, slots={k: v for k, v in slots.items() if k != "topic"})

    pend_intent = sess.get("pending_intent")
    if injected and (intent in ("unknown",) or len(text.strip()) < 12):
        r = reply("refusal", t("refuse_injection", lang))
        step("route", decision="refuse_injection")
        return finish(db, r, audit, trace_id, passenger_id, session_id, lang, sess, as_of, t0)
    if injected and intent in ("cancel_request", "change_boarding", "book_ticket"):
        # an instruction was hidden in the message: still only ever PREVIEW, never act
        step("route", note="injection present; action will only be previewed")

    # continue a half-finished request (slot filling)
    if pend_intent and (intent in ("unknown", "booking_status", "search_trains") or intent == pend_intent) and not slots.get("action_id"):
        merged = dict(sess.get("collected", {}))
        for k, v in slots.items():
            if v not in (None, [], ""):
                merged[k] = v
        slots = merged
        intent = pend_intent
        step("context", note="continued earlier request %s" % pend_intent)
    elif pend_intent and intent not in ("unknown",):
        sess.pop("pending_intent", None); sess.pop("collected", None); sess["asked"] = 0

    # yes/ok typed in chat while a preview is waiting: never executes (confirm is a separate call)
    if re.match(r"^\s*(yes|y|ok|okay|confirm|confirmed|do it|go ahead|haan|ha|han|theek hai|thik hai|हाँ|हां|ठीक है|कर दो|kar do)\s*[.!]*\s*$", text, re.I):
        la = sess.get("last_action")
        if la:
            r = reply("confirm_needed", t("pending_hint", lang, aid=la["action_id"]), pending=la)
            step("route", decision="chat_yes_is_not_confirm")
            return finish(db, r, audit, trace_id, passenger_id, session_id, lang, sess, as_of, t0)

    if intent == "unknown" and llm.available():
        s = llm.suggest_intent(text, und.INTENTS)
        if s:
            intent = s
            step("understand_llm", intent=s)

    fn = {"greet": do_greet, "my_bookings": do_my_bookings, "booking_status": do_status, "refund_estimate": do_refund_estimate,
          "cancel_request": do_cancel, "change_boarding": do_change_boarding, "book_ticket": do_book, "deadline": do_deadline,
          "search_trains": do_search, "seats": do_search, "fare": do_search, "rules": do_rules,
          "handoff_request": do_handoff, "dispute": do_handoff, "forbidden": do_forbidden, "unknown": do_unknown}[intent]
    ctx = {"db": db, "pid": passenger_id, "lang": lang, "as_of": as_of, "text": text, "slots": slots, "sess": sess,
           "trace": trace_id, "intent": intent, "step": step, "session_id": session_id}
    try:
        r = fn(ctx)
    except Exception as e:                                   # never crash the conversation
        step("error", error=repr(e)[:200])
        r = reply("not_found", t("unknown", lang))
    return finish(db, r, audit, trace_id, passenger_id, session_id, lang, sess, as_of, t0)


def finish(db, r, audit, trace_id, passenger_id, session_id, lang, sess, as_of, t0):
    doc_text = r.pop("_doc_text", "")
    extra = r.pop("_extra", {})
    tool_text = json.dumps(r["tools"], ensure_ascii=False, default=str)
    others = [x[0] for x in db.execute("SELECT passenger_id FROM passengers WHERE passenger_id!=?", (passenger_id,))]
    problems = correctors.check(r["answer"], r["answer_type"], lang, r["sources"], tool_text, doc_text, passenger_id, others)
    audit["steps"].append({"step": "correctors", "problems": [list(map(str, p)) for p in problems]})
    if problems:
        # one safe revision: use the plain extract if we have one, else a safe template
        safe = extra.get("plain_answer")
        if safe and not correctors.check(safe, r["answer_type"], lang, r["sources"], tool_text, doc_text, passenger_id, others):
            r["answer"] = safe
            audit["steps"].append({"step": "revision", "used": "plain_extract"})
        else:
            r["answer"] = t("unknown", lang)
            r["answer_type"] = "clarification"
            r["sources"] = []
            audit["steps"].append({"step": "revision", "used": "safe_template"})
    r["answer"], v = guardrails.output_guard(r["answer"])
    if v:
        audit["steps"].append({"step": "output_guard", "masked": v})
    sess["lang"] = lang
    if r.get("pending_action"):
        sess["last_action"] = r["pending_action"]
    if extra.get("session_update"):
        sess.update(extra["session_update"])
    save_session(db, session_id, passenger_id, sess, as_of)
    r["trace_id"] = trace_id
    audit.update({"answer_type": r["answer_type"], "answer": r["answer"], "sources": r["sources"], "tools": r["tools"],
                  "pending_action": r.get("pending_action"), "handed_to_human": r["handed_to_human"],
                  "latency_ms": int((time.time() - t0) * 1000)})
    db.execute("INSERT OR REPLACE INTO audit VALUES(?,?,?,?,?)",
               (trace_id, clock.iso(as_of), passenger_id, session_id, json.dumps(audit, ensure_ascii=False, default=str)))
    db.commit()
    return r


# ------------------------------------------------------------------ helpers
def tool(name, output, **inp):
    return {"tool": name, "input": inp, "output": output}


def route_ask(ctx, intent, missing_keys, collected):
    """Ask for what is missing. At most 2 follow-ups, never ask the same thing twice; then hand to a human."""
    sess, lang = ctx["sess"], ctx["lang"]
    asked = sess.get("asked", 0) if sess.get("pending_intent") == intent else 0
    if asked >= MAX_FOLLOWUPS:
        names = ", ".join(t(k, lang) for k in missing_keys)
        h = handoff.create(ctx["db"], ctx["pid"], collected.get("booking_id"), "gave_up", ctx["text"],
                           ["Collected so far: %s" % json.dumps({k: v for k, v in collected.items() if k != "topic"}, ensure_ascii=False)], ctx["as_of"], ctx["trace"])
        ctx["sess"].pop("pending_intent", None); ctx["sess"].pop("collected", None); ctx["sess"]["asked"] = 0
        return reply("handed_to_human", t("gave_up", lang, missing=names) + " " + t("handoff", lang, desk=h["desk"], hid=h["handoff_id"]), handed=True,
                     tools=[tool("create_handoff", h)])
    names = ", ".join(t(k, lang) for k in missing_keys)
    sess["pending_intent"], sess["collected"], sess["asked"] = intent, collected, asked + 1
    return reply("clarification", t("ask_search", lang, missing=names), extra={})


def done_asking(ctx):
    for k in ("pending_intent", "collected"):
        ctx["sess"].pop(k, None)
    ctx["sess"]["asked"] = 0


REFERS = re.compile(r"\b(it|this|that|this one|same|same one|this booking|that booking|my last|the last one|ye|yeh|isko|isse|iska|iski|uska|uski|usko|isi|usi)\b|इसे|इस |उस |यही|वही", re.I)


def last_ref(ctx):
    """Use the booking from earlier in this chat only when the message points back to it ('cancel it', 'is booking ka')."""
    if ctx["sess"].get("last_booking") and REFERS.search(ctx["text"]):
        return ctx["sess"]["last_booking"]
    return None


def pick_booking(ctx, need_active=True):
    """Returns (booking_dict or None, reply_if_problem)."""
    db, pid, lang, slots, sess = ctx["db"], ctx["pid"], ctx["lang"], ctx["slots"], ctx["sess"]
    bid = slots.get("booking_id") or last_ref(ctx)
    if not bid:
        mine = bk.list_bookings(db, pid)
        if not mine:
            return None, reply("not_found", t("no_bookings", lang), tools=[tool("list_bookings", [])])
        lst = "; ".join("%s (%s %s→%s, %s)" % (b["booking_id"], b["train_no"], b["from_code"], b["to_code"], fmt_date(b["journey_date"])) for b in mine[:8])
        r = route_ask_booking(ctx, lst)
        return None, r
    b = bk.get_booking(db, bid, pid)
    if not b:
        ctx["step"]("tool", name="get_booking", result="not_found_or_not_owned")
        return None, reply("not_found", t("other_booking", lang, bid=bid), tools=[tool("get_booking", {"booking_id": bid, "found": False})])
    return b, None


def route_ask_booking(ctx, lst):
    sess, lang, intent = ctx["sess"], ctx["lang"], ctx["intent"]
    asked = sess.get("asked", 0) if sess.get("pending_intent") == intent else 0
    if asked >= MAX_FOLLOWUPS:
        h = handoff.create(ctx["db"], ctx["pid"], None, "gave_up", ctx["text"], ["No booking id was given after two questions."], ctx["as_of"], ctx["trace"])
        done_asking(ctx)
        return reply("handed_to_human", t("handoff", lang, desk=h["desk"], hid=h["handoff_id"]), handed=True, tools=[tool("create_handoff", h)])
    sess["pending_intent"], sess["collected"], sess["asked"] = intent, dict(ctx["slots"]), asked + 1
    return reply("clarification", t("ask_booking", lang, list=lst))


def station_label(db, code):
    return tt.station_name(db, code)


# ------------------------------------------------------------------ intents
def do_greet(ctx):
    return reply("answer", t("greet", ctx["lang"]))


def do_unknown(ctx):
    return reply("clarification", t("unknown", ctx["lang"]))


def do_my_bookings(ctx):
    db, pid, lang = ctx["db"], ctx["pid"], ctx["lang"]
    mine = bk.list_bookings(db, pid)
    if not mine:
        return reply("answer", t("no_bookings", lang), tools=[tool("list_bookings", [])])
    lines = ["%s: %s %s→%s, %s, %s, %s" % (b["booking_id"], b["train_no"], b["from_code"], b["to_code"], fmt_date(b["journey_date"]), b["class"],
                                           i18n.status_name(b["status"], lang)) for b in mine]
    return reply("answer", "\n".join(lines), tools=[tool("list_bookings", [{"booking_id": b["booking_id"], "status": b["status"]} for b in mine])])


def do_status(ctx):
    db, lang = ctx["db"], ctx["lang"]
    b, prob = pick_booking(ctx)
    if prob:
        return prob
    done_asking(ctx)
    trav = bk.travellers(db, b["booking_id"])
    tr = db.execute("SELECT name FROM trains WHERE train_no=?", (b["train_no"],)).fetchone()
    head = t("status_head", lang, bid=b["booking_id"], train=b["train_no"], name=tr["name"] if tr else "", frm=station_label(db, b["from_code"]),
             to=station_label(db, b["to_code"]), date=fmt_date(b["journey_date"]), cls=b["class"], status=i18n.status_name(b["status"], lang))
    lines = []
    for x in trav:
        seat = (" %s/%s" % (x["coach"], x["berth"])) if x["coach"] else ""
        lines.append("- %s (%s): %s%s" % (x["traveller_name"], x["age"], x["status"], seat))
    ctx["sess"]["last_booking"] = b["booking_id"]
    out = [tool("get_booking", {"booking_id": b["booking_id"], "status": b["status"], "from": b["from_code"], "to": b["to_code"],
                                 "amount_paid": b["amount_paid"], "travellers": [{"name": x["traveller_name"], "status": x["status"]} for x in trav]})]
    return reply("answer", head + "\n" + "\n".join(lines), tools=out)


def why_text(q, lang):
    parts = []
    if q["band"] == "TRAIN_CANCELLED":
        return t("why_TRAIN_CANCELLED", lang)
    if q["tatkal"] and q["band"] != "NONE":
        parts.append(t("why_TATKAL", lang))
    if any(l.get("status") == "WL" for l in q["lines"]):
        parts.append(t("why_WL", lang) + " (%s)" % inr(q["wl_clerkage"]))
    if q["waived"] and q["band"] == "FLAT":
        parts.append(t("why_WAIVER", lang))
    elif not q["tatkal"] or q["band"] == "NONE":
        if q["band"] == "FLAT":
            parts.append(t("why_FLAT", lang, cls=inr(q["charge"])))
        elif q["band"] == "MID":
            parts.append(t("why_MID", lang, pct=q["mid_pct"]))
        elif q["band"] == "LOW":
            parts.append(t("why_LOW", lang, pct=q["low_pct"]))
        else:
            parts.append(t("why_NONE", lang))
    return " ".join(parts)


def do_refund_estimate(ctx):
    db, pid, lang, as_of = ctx["db"], ctx["pid"], ctx["lang"], ctx["as_of"]
    if not ctx["slots"].get("booking_id") and not last_ref(ctx):
        ctx["slots"]["topic"] = "refund"
        r = do_rules(ctx)
        return r
    b, prob = pick_booking(ctx)
    if prob:
        return prob
    q = refund.quote_refund(db, b["booking_id"], as_of)
    if not q["ok"]:
        return reply("answer", t("already_cancelled", lang, bid=b["booking_id"]), tools=[tool("quote_refund", q)])
    done_asking(ctx)
    ctx["sess"]["last_booking"] = b["booking_id"]
    if q["hours_before"] < 0:
        return reply("answer", t("departed", lang), tools=[tool("quote_refund", q)], sources=q["sources"])
    dep = clock.parse_dt(q["departure"])
    ans = t("refund_estimate", lang, bid=b["booking_id"], hours=fmt_hours(q["hours_before"]), frm=station_label(db, q["from_code"]),
            dep=fmt_dt(dep), refund=inr(q["total_refund"]), paid=inr(q["total_paid"]), why=why_text(q, lang))
    return reply("answer", ans, sources=q["sources"], tools=[tool("quote_refund", q)])


def who_text(q):
    return ", ".join("%s (%s)" % (l["name"], inr(l["refund"])) for l in q["lines"])


def do_cancel(ctx):
    db, pid, lang, as_of, text = ctx["db"], ctx["pid"], ctx["lang"], ctx["as_of"], ctx["text"]
    b, prob = pick_booking(ctx)
    if prob:
        return prob
    trav = [x for x in bk.travellers(db, b["booking_id"]) if x["status"] != "CAN"]
    chosen = None
    if len(trav) > 1:
        named = [x["traveller_id"] for x in trav if re.search(r"\b%s\b" % re.escape(x["traveller_name"].split()[0]), text, re.I)]
        whole = re.search(r"\b(all|whole|entire|complete|poori|puri|sabhi|saari|saare|पूरी|सभी)\b", text, re.I) or re.search(r"\b(booking|बुकिंग)\b", text, re.I)
        if named and len(named) < len(trav) and not re.search(r"\b(whole|entire|all|sabhi|सभी)\b", text, re.I):
            chosen = named
    for a in db.execute("SELECT action_id FROM actions WHERE passenger_id=? AND booking_id=? AND status='pending' AND action_type='cancel_booking'", (pid, b["booking_id"])):
        db.execute("UPDATE actions SET status='cancelled', result='superseded' WHERE action_id=?", (a[0],))
    p = am.propose_cancel(db, pid, b["booking_id"], as_of, traveller_ids=chosen, trace_id=ctx["trace"])
    done_asking(ctx)
    ctx["sess"]["last_booking"] = b["booking_id"]
    if not p["ok"]:
        key = {"already_cancelled": "already_cancelled", "departed": "departed"}.get(p["reason"], "unknown")
        return reply("answer", t(key, lang, bid=b["booking_id"]), tools=[tool("propose_cancel", {k: v for k, v in p.items() if k != "quote"})])
    q = p["quote"]
    mins = cfg.get_int(db, "action_expiry_minutes", as_of, 10)
    ans = t("confirm_cancel", lang, bid=b["booking_id"], who=who_text(q), refund=inr(q["total_refund"]), paid=inr(q["total_paid"]),
            why=why_text(q, lang), mins=mins)
    src = dedupe(q["sources"] + [{"doc_id": "RULE-11", "section": "Section 1"}])
    return reply("confirm_needed", ans, sources=src, pending=p["pending_action"],
                 tools=[tool("quote_refund", q), tool("propose_cancel", p["pending_action"])])


def do_change_boarding(ctx):
    db, pid, lang, as_of, slots = ctx["db"], ctx["pid"], ctx["lang"], ctx["as_of"], ctx["slots"]
    b, prob = pick_booking(ctx)
    if prob:
        return prob
    cands = [s for s in slots.get("stations", []) if s != b["from_code"]]
    if not cands:
        return route_ask(ctx, "change_boarding", ["m_newstation"], dict(slots, booking_id=b["booking_id"]))
    new = cands[0]
    p = am.propose_change_boarding(db, pid, b["booking_id"], new, as_of, trace_id=ctx["trace"])
    done_asking(ctx)
    ctx["sess"]["last_booking"] = b["booking_id"]
    if not p["ok"]:
        r = p["reason"]
        if r == "too_late":
            dl = clock.parse_dt(p["deadline"])
            return reply("refusal", t("too_late_change", lang, bid=b["booking_id"], deadline=fmt_dt(dl), hours=p["hours"],
                                      src="%s %s" % (p["source"]["doc_id"], p["source"]["section"])),
                         sources=[p["source"]], tools=[tool("propose_change_boarding", p)])
        key = {"bad_station": "bad_station", "already_changed": "already_changed", "not_active": "not_active"}.get(r, "unknown")
        return reply("refusal", t(key, lang, bid=b["booking_id"]), tools=[tool("propose_change_boarding", p)], sources=[{"doc_id": "RULE-07", "section": "Section 2"}])
    pv = p["preview"]
    mins = cfg.get_int(db, "action_expiry_minutes", as_of, 10)
    src = [pv["source"], {"doc_id": "RULE-11", "section": "Section 1"}]
    ans = t("confirm_change", lang, bid=b["booking_id"], old=station_label(db, pv["old_code"]), new=station_label(db, pv["new_code"]),
            dep=fmt_dt(clock.parse_dt(pv["new_departure"])), hours=pv["hours"], src="%s %s" % (pv["source"]["doc_id"], pv["source"]["section"]), mins=mins)
    return reply("confirm_needed", ans, sources=src, pending=p["pending_action"], tools=[tool("propose_change_boarding", p)])


def search_for(ctx, frm, to, date_iso):
    db = ctx["db"]
    res = tt.search_trains(db, frm, to, date_iso)
    out = []
    for r in res:
        cl = {}
        for c in r["classes"]:
            av = seats.availability(db, r["train_no"], r["origin_date"], c)
            fare = fares.fare(db, r["train_no"], c, frm, to)
            cl[c] = {"availability": av, "fare": fare}
        out.append(dict(r, class_info=cl))
    return out


def seat_text(av, lang):
    if not av:
        return "n/a"
    if av["state"] == "AVAILABLE":
        return "%d %s" % (av["available"], {"en": "available", "hi": "उपलब्ध", "hinglish": "available"}[lang])
    if av["state"] == "RAC":
        return "RAC %d" % av["rac"]
    if av["state"] == "WL":
        return "WL %d" % av["waitlist"]
    return {"en": "regret (full)", "hi": "भरा हुआ", "hinglish": "full"}[lang]


def do_search(ctx):
    db, lang, slots, as_of = ctx["db"], ctx["lang"], ctx["slots"], ctx["as_of"]
    sts = slots.get("stations", [])
    missing = []
    if len(sts) < 1:
        missing.append("m_from")
    if len(sts) < 2:
        missing.append("m_to")
    if not slots.get("date"):
        missing.append("m_date")
    if missing:
        if len(sts) == 1 and "m_from" not in missing:
            pass
        return route_ask(ctx, "search_trains", missing, dict(slots))
    frm, to = sts[0], sts[1]
    done_asking(ctx)
    res = search_for(ctx, frm, to, slots["date"])
    if slots.get("train_no"):
        res = [r for r in res if r["train_no"] == slots["train_no"]]
    head_kw = dict(frm=station_label(db, frm), to=station_label(db, to), date=fmt_date(slots["date"]))
    if not res:
        return reply("answer", t("search_none", lang, **head_kw), tools=[tool("search_trains", [], frm=frm, to=to, date=slots["date"])])
    lines = [t("search_head", lang, **head_kw)]
    for r in res[:6]:
        cls = []
        for c, info in r["class_info"].items():
            if slots.get("class") and c != slots["class"]:
                continue
            cls.append("%s %s %s" % (c, seat_text(info["availability"], lang), inr(info["fare"])) if info["fare"] else c)
        lines.append("- %s %s: %s %s → %s | %s" % (r["train_no"], r["name"], {"en": "departs", "hi": "प्रस्थान", "hinglish": "departs"}[lang],
                                                    fmt_dt(r["departs"]), fmt_dt(r["arrives"]), "; ".join(cls)))
        if r["after_midnight"]:
            lines.append("  " + t("midnight_note", lang, frm=station_label(db, frm), dep=fmt_date(r["departs"]), origin=fmt_date(r["origin_date"])))
    tools = [tool("search_trains", [{"train_no": r["train_no"], "departs": clock.iso(r["departs"]), "arrives": clock.iso(r["arrives"]),
                                     "origin_date": r["origin_date"], "classes": {c: {"fare": i["fare"], "availability": i["availability"]} for c, i in r["class_info"].items()}}
                                    for r in res[:6]], frm=frm, to=to, date=slots["date"])]
    ctx["sess"]["last_search"] = {"frm": frm, "to": to, "date": slots["date"]}
    return reply("answer", "\n".join(lines), tools=tools)


def do_book(ctx):
    db, pid, lang, slots, as_of = ctx["db"], ctx["pid"], ctx["lang"], ctx["slots"], ctx["as_of"]
    sts = slots.get("stations", [])
    ls = ctx["sess"].get("last_search")
    if len(sts) < 2 and ls:
        sts = [ls["frm"], ls["to"]]
        slots.setdefault("date", ls["date"])
    missing = []
    if len(sts) < 2:
        missing += ["m_from", "m_to"] if not sts else ["m_to"]
    if not slots.get("date"):
        missing.append("m_date")
    if not slots.get("class"):
        missing.append("m_class")
    train_no = slots.get("train_no")
    res = []
    if len(sts) >= 2 and slots.get("date"):
        res = search_for(ctx, sts[0], sts[1], slots["date"])
        if not train_no:
            if len(res) == 1:
                train_no = res[0]["train_no"]
            elif len(res) > 1:
                missing.append("m_train")
    if not slots.get("travellers"):
        missing.append("m_travellers")
    col = dict(slots, stations=sts)
    if train_no:
        col["train_no"] = train_no
    if missing:
        return route_ask(ctx, "book_ticket", missing, col)
    chosen = [r for r in res if r["train_no"] == train_no]
    if not chosen:
        done_asking(ctx)
        return reply("answer", t("search_none", lang, frm=station_label(db, sts[0]), to=station_label(db, sts[1]), date=fmt_date(slots["date"])))
    origin = chosen[0]["origin_date"]
    for a in db.execute("SELECT action_id FROM actions WHERE passenger_id=? AND status='pending' AND action_type='book'", (pid,)):
        db.execute("UPDATE actions SET status='cancelled', result='superseded' WHERE action_id=?", (a[0],))
    p = am.propose_book(db, pid, train_no, origin, sts[0], sts[1], slots["class"], slots["travellers"], as_of, trace_id=ctx["trace"])
    done_asking(ctx)
    if not p["ok"]:
        r = p["reason"]
        kw = {"max": p.get("max"), "days": p.get("days")}
        key = {"regret": "regret", "departed": "departed", "too_early": "too_early", "bad_traveller_count": "too_many"}.get(r, "unknown")
        return reply("answer", t(key, lang, **kw), tools=[tool("propose_book", p)])
    pv = p["preview"]
    mins = cfg.get_int(db, "action_expiry_minutes", as_of, 10)
    who = ", ".join("%s (%s) %s %s" % (l["name"], l["age"], l["status"], inr(l["fare"])) for l in pv["lines"])
    ans = t("confirm_book", lang, train=train_no, frm=station_label(db, sts[0]), to=station_label(db, sts[1]), cls=slots["class"],
            dep=fmt_dt(clock.parse_dt(pv["departure"])), who=who, total=inr(pv["total"]), mins=mins)
    return reply("confirm_needed", ans, sources=[{"doc_id": "RULE-01", "section": "Section 1"}, {"doc_id": "RULE-11", "section": "Section 1"}],
                 pending=p["pending_action"], tools=[tool("propose_book", pv)])


def do_deadline(ctx):
    db, pid, lang, as_of, text = ctx["db"], ctx["pid"], ctx["lang"], ctx["as_of"], ctx["text"]
    if not ctx["slots"].get("booking_id") and not last_ref(ctx):
        if re.search(r"(boarding|board|station|स्टेशन)", text, re.I):
            ctx["slots"]["topic"] = "boarding_change"
        elif re.search(r"(cancel|refund|radd|रद्द|wapas|वापस)", text, re.I):
            ctx["slots"]["topic"] = "refund"
        return do_rules(ctx)
    b, prob = pick_booking(ctx)
    if prob:
        return prob
    done_asking(ctx)
    ctx["sess"]["last_booking"] = b["booking_id"]
    if re.search(r"(boarding|board|station|स्टेशन)", text, re.I):
        dl, hours, src = deadlines.boarding_change_deadline(db, b, as_of)
        ans = t("deadline_change", lang, bid=b["booking_id"], deadline=fmt_dt(dl), hours=hours, src="%s %s" % (src[0], src[1]))
        return reply("answer", ans, sources=[{"doc_id": src[0], "section": src[1]}],
                     tools=[tool("boarding_change_deadline", {"booking_id": b["booking_id"], "deadline": clock.iso(dl), "hours": hours})])
    bands = deadlines.refund_bands(db, b, as_of)
    g = lambda n, d: cfg.get_int(db, n, as_of, d)  # noqa: E731
    ans = t("deadline_refund", lang, bid=b["booking_id"], dep=fmt_dt(bands["departure"]), flat=fmt_dt(bands["flat_until"]),
            mid=g("deduct_pct_12_48h", 25), midt=fmt_dt(bands["mid_until"]), low=g("deduct_pct_4_12h", 50), lowt=fmt_dt(bands["none_after"]),
            none=fmt_dt(bands["none_after"]))
    return reply("answer", ans, sources=[{"doc_id": "RULE-03", "section": "Section 2"}, {"doc_id": "RULE-03", "section": "Section 3"}],
                 tools=[tool("refund_bands", {k: clock.iso(v) for k, v in bands.items()})])


def do_rules(ctx):
    db, lang, as_of, slots = ctx["db"], ctx["lang"], ctx["as_of"], ctx["slots"]
    idx = store.get_index(db)
    asof_d = as_of.date().isoformat()
    res = retrieval.retrieve(idx, ctx["text"], asof_d, topic=slots.get("topic"))
    ctx["step"]("retrieve", abstain=res["abstain"], winner=(res["winner"]["doc_id"] + " " + res["winner"]["section"]) if res["winner"] else None,
                overridden=[o["doc_id"] for o in res["overridden"]])
    if res["abstain"]:
        return reply("not_found", t("rules_not_found", lang))
    w = res["winner"]
    shown = w
    src = [{"doc_id": w["doc_id"], "section": w["section"]}]
    # same-language FAQ that agrees with the winner can be the readable text for Hindi/Hinglish users
    if lang in ("hi", "hinglish") and w["doc"]["language"] != lang:
        for h in res["hits"]:
            if h["doc"]["language"] == lang and h["doc"]["topic"] == w["doc"]["topic"] and retrieval.numbers_in(h["text"]) == retrieval.numbers_in(w["text"]):
                shown = h
                src.append({"doc_id": h["doc_id"], "section": h["section"]})
                break
    body = shown["text"]
    plain = "%s %s" % (t("rules_prefix", lang, src="%s %s" % (w["doc_id"], w["section"])), body)
    ans = plain
    notes = []
    for u in res["upcoming"]:
        if u["doc"]["topic"] == w["doc"]["topic"] and u["doc"]["supersedes"]:
            notes.append(t("upcoming_note", lang, doc=u["doc_id"], date=fmt_date(u["doc"]["effective_from"])))
            src.append({"doc_id": u["doc_id"], "section": u["section"]})
            break
    if res["overridden"]:
        notes.append(t("overridden_note", lang, docs=", ".join(sorted({o["doc_id"] for o in res["overridden"]}))))
    if llm.available() and shown["doc"]["language"] == "en" or (llm.available() and lang != "en"):
        rw = llm.reword(body, ctx["text"], lang)
        if rw and len(rw) < 900:
            ans = "%s %s" % (t("rules_prefix", lang, src="%s %s" % (w["doc_id"], w["section"])), rw.strip())
    doc_text = w["text"] + " " + shown["text"] + " " + " ".join(u["text"] for u in res["upcoming"])
    if notes:
        ans += "\n" + " ".join(notes)
        plain += "\n" + " ".join(notes)
    return reply("answer", ans, sources=dedupe(src), doc_text=doc_text, tools=[tool("search_documents", {"winner": w["doc_id"], "section": w["section"],
                 "overridden": [o["doc_id"] for o in res["overridden"]]})], extra={"plain_answer": plain})


def do_handoff(ctx):
    db, pid, lang, as_of = ctx["db"], ctx["pid"], ctx["lang"], ctx["as_of"]
    bid = ctx["slots"].get("booking_id") or last_ref(ctx) or ctx["sess"].get("last_booking")
    facts, tools = [], []
    if bid:
        b = bk.get_booking(db, bid, pid)
        if b:
            q = refund.quote_refund(db, bid, as_of)
            facts.append("Booking %s status %s, %s to %s on %s." % (bid, b["status"], b["from_code"], b["to_code"], b["journey_date"]))
            if q.get("ok"):
                facts.append("Refund calculated by rule now: %s of %s (band %s)." % (inr(q["total_refund"]), inr(q["total_paid"]), q["band"]))
                tools.append(tool("quote_refund", q))
        else:
            bid = None
    reason = "dispute" if ctx["intent"] == "dispute" else "human"
    h = handoff.create(db, pid, bid, reason, ctx["text"], facts, as_of, ctx["trace"])
    tools.append(tool("create_handoff", h))
    return reply("handed_to_human", t("handoff", lang, desk=h["desk"], hid=h["handoff_id"]), handed=True, tools=tools,
                 sources=[{"doc_id": "RULE-10", "section": "Section 1"}] if ctx["intent"] == "dispute" else [])


def do_forbidden(ctx):
    lang, text = ctx["lang"], ctx["text"]
    if re.search(r"(someone else|somebody|my (friend|brother|sister|colleague|neighbou?r|boss|wife|husband)|his|her|their|kisi aur|dost|bhai|behen|padosi)", text, re.I):
        return reply("refusal", t("own_only", lang), sources=[{"doc_id": "RULE-12", "section": "Section 1"}])
    if re.search(r"(jump|skip|ahead|upar|aage|waiting|waitlist)", text, re.I):
        return reply("refusal", t("refuse_policy", lang), sources=[{"doc_id": "RULE-04", "section": "Section 2"}])
    if re.search(r"(fare|kiraya|price)", text, re.I):
        return reply("refusal", t("refuse_policy", lang), sources=[{"doc_id": "RULE-02", "section": "Section 3"}])
    return reply("refusal", t("refuse_policy", lang), sources=[{"doc_id": "RULE-10", "section": "Section 2"}])
