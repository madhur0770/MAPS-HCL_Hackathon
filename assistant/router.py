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
from assistant import correctors, dates, guardrails, handoff, i18n, language, llm, typos, understand as und
from assistant.i18n import t
from core import clock, config
from core.text import fmt_date, fmt_dt, fmt_hours, inr
from rag import retrieval, store
from tools import bookings as bk, deadlines, fares, refund, seats, settings as cfg, timetable as tt

MAX_FOLLOWUPS = 3


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
    if other_person(db, passenger_id, text) and not re.search(r"\b(BKG\s?-?\d|UR-?\d)", text, re.I):
        step("route", decision="asks_about_another_passenger")
        r = reply("refusal", t("own_only", lang), sources=[{"doc_id": "RUL-006", "section": "3.6"}])
        return finish(db, r, audit, trace_id, passenger_id, session_id, lang, sess, as_of, t0)
    if text.isascii():
        prot = {w for a in tt.station_index(db) for w in a.split()}
        fixed = typos.fix(text, prot)
        if fixed != text:
            step("typo_fix", before=text[:80], after=fixed[:80])
            text = fixed
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
        rp = merged.pop("role_pending", None)
        if rp:
            # earlier we asked whether the one station named is the start or the destination
            low_t = text.lower()
            ns = slots.get("stations", [])
            if slots.get("to_st") and not slots.get("from_st"):
                merged["from_st"] = rp
            elif slots.get("from_st") and not slots.get("to_st"):
                merged["to_st"] = rp
            elif not ns and re.search(r"\b(to|going|destination|dest|jaana|tak|arrive|reach)\b|तक|जाना", low_t):
                merged["to_st"] = rp; merged["stations"] = [rp]
            elif not ns and re.search(r"\b(from|start|starting|origin|se|leave|depart)\b|से", low_t):
                merged["from_st"] = rp; merged["stations"] = [rp]
            elif len(ns) == 1 and ns[0] != rp:
                merged["from_st"], merged["to_st"] = rp, ns[0]
                slots["from_st"], slots["to_st"] = rp, ns[0]
                slots["stations"] = [rp, ns[0]]
        if len(slots.get("stations", [])) == 1 and not slots.get("from_st") and not slots.get("to_st"):
            # a bare station name answers the question that was asked: fill whichever end is still missing
            if merged.get("to_st") and not merged.get("from_st"):
                slots["from_st"] = slots["stations"][0]
            elif merged.get("from_st") and not merged.get("to_st"):
                slots["to_st"] = slots["stations"][0]
        for k, v in slots.items():
            if v not in (None, [], ""):
                merged[k] = v
        role = merged.pop("amb_role", None)
        if role and len(merged.get("stations", [])) == 1 and not merged.get("from_st") and not merged.get("to_st"):
            merged["to_st" if role == "to" else "from_st"] = merged["stations"][0]      # the answer to "which Anandpur?" keeps the role it was asked for
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
          "handoff_request": do_handoff, "unsupported_change": do_unsupported_change, "dispute": do_handoff, "forbidden": do_forbidden, "unknown": do_unknown,
          "privacy_ask": do_privacy}[intent]
    ctx = {"db": db, "pid": passenger_id, "lang": lang, "as_of": as_of, "text": text, "slots": slots, "sess": sess,
           "trace": trace_id, "intent": intent, "step": step, "session_id": session_id}
    try:
        r = followup(ctx) if intent in ("unknown", "rules", "greet", "search_trains", "seats", "fare", "my_bookings", "booking_status", "book_ticket") else None
        if r is None:
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


def other_person(db, pid, text):
    """True when the message asks about ANOTHER passenger (by id or by name, even misspelled)."""
    import difflib
    for m in re.findall(r"\bP\d{3}\b", text, re.I):
        if m.upper() != pid:
            return True
    rows = db.execute("SELECT passenger_id, name FROM passengers").fetchall()
    own = next((r["name"] for r in rows if r["passenger_id"] == pid), "").lower().split()
    words = [w for w in re.findall(r"[a-zA-Z]{4,}", text.lower())]
    pointing = re.search(r"\b(for|of|about|ke|ka|ki|ko)\b|'s\b", text, re.I)
    askword = re.search(r"(ticket|booking|booked|trip|journey|status|refund|phone|detail|history|pnr|बुकिंग|टिकट)", text, re.I)
    if not (pointing and askword):
        return False
    for r in rows:
        if r["passenger_id"] == pid:
            continue
        for part in r["name"].lower().split():
            if part in own:
                continue
            if any(difflib.SequenceMatcher(None, w, part).ratio() >= 0.8 for w in words):
                return True
    return False


def route_ask(ctx, intent, missing_keys, collected):
    """Ask for what is missing. At most 2 follow-ups, never ask the same thing twice; then hand to a human."""
    sess, lang = ctx["sess"], ctx["lang"]
    asked = sess.get("asked", 0) if sess.get("pending_intent") == intent else 0
    if asked >= MAX_FOLLOWUPS:
        names = ", ".join(t(k, lang) for k in missing_keys)
        h = handoff.create(ctx["db"], ctx["pid"], collected.get("booking_id"), "gave_up", ctx["text"],
                           ["Collected so far: %s" % json.dumps({k: v for k, v in collected.items() if k != "topic"}, ensure_ascii=False)], ctx["as_of"], ctx["trace"])
        ctx["sess"].pop("pending_intent", None); ctx["sess"].pop("collected", None); ctx["sess"]["asked"] = 0
        return reply("handed_to_human", t("gave_up", lang, missing=names) + " " + handoff_text(lang, h), handed=True,
                     tools=[tool("create_handoff", h)])
    parts = [t(k, lang) for k in missing_keys[:3]]          # a few quick questions at a time, not a long form
    names = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + {"en": " and ", "hi": " और ", "hinglish": " aur "}.get(lang, " and ") + parts[-1]
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
    if not bid and slots.get("train_no"):        # "status of my ticket on UJ1006"
        on_train = [b for b in bk.list_bookings(db, pid) if b["train_no"] == slots["train_no"]]
        if len(on_train) == 1:
            bid = on_train[0]["booking_id"]
    if not bid:
        mine = bk.list_bookings(db, pid)
        if not mine:
            return None, reply("not_found", t("no_bookings", lang), tools=[tool("list_bookings", [])])
        # narrow down with what the passenger said: tomorrow / 22 Nov, 2AC, the train, the route; one match = that booking
        op = re.search(r"\b(train|service|gaadi)\b.{0,20}\b(was|got|is|has been|hua|ho gayi|hui)?\s*(cancel\w*|radd)\b", ctx["text"], re.I) and not re.search(r"\b(i|want to|wanna|please|pls)\b.{0,12}\bcancel", ctx["text"], re.I)
        if op and any(b["status"] == "OPERATOR_CANCELLED" for b in mine):
            cand = [b for b in mine if b["status"] == "OPERATOR_CANCELLED"]       # "my train got cancelled": the booking the operator cancelled
        else:
            cand = [b for b in mine if b["status"] not in ("CANCELLED", "OPERATOR_CANCELLED")] if need_active else mine
        cand = cand or mine
        for key, fn in (("date", lambda b, v: b["journey_date"] == v), ("class", lambda b, v: b["class"] == v), ("train_no", lambda b, v: b["train_no"] == v)):
            v = slots.get(key)
            if v and not (key == "train_no" and False):
                f = [b for b in cand if fn(b, v)]
                if f:
                    cand = f
        for key, field in (("from_st", "from_code"), ("to_st", "to_code")):
            if slots.get(key):
                f = [b for b in cand if b[field] == slots[key]]
                if f:
                    cand = f
        if len(cand) == 1:
            bid = cand[0]["booking_id"]
        elif len(cand) < len(mine):
            mine = cand
    if not bid:
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
        return reply("handed_to_human", handoff_text(lang, h), handed=True, tools=[tool("create_handoff", h)])
    sess["pending_intent"], sess["collected"], sess["asked"] = intent, dict(ctx["slots"]), asked + 1
    return reply("clarification", t("ask_booking", lang, list=lst))


def station_label(db, code):
    return tt.station_name(db, code)


# ------------------------------------------------------------------ intents
def do_greet(ctx):
    return reply("answer", t("greet", ctx["lang"]))


STOP_PLACE = {"the", "my", "an", "and", "you", "tomorrow", "today", "tonight", "know", "check", "see", "get", "go", "book", "cancel", "travel", "please", "kal", "aaj", "parso", "this", "that", "your", "our",
              "them", "him", "her", "any", "all", "some", "one", "two", "three", "me", "us", "it", "now", "later", "next", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
              "sunday", "central", "north", "junction", "station", "city", "road", "ticket", "tickets", "train", "trains", "morning", "evening", "night", "afternoon", "date", "time"}


def ambiguous_reply(ctx, amb):
    """A name shared by two stations (Anandpur): ask which one, remember what else was said so the answer completes the request."""
    alias, codes = amb[0]
    opts = " / ".join("%s (%s)" % (station_label(ctx["db"], c), c) for c in codes)
    kept = {k: v for k, v in ctx["slots"].items() if k != "topic"}
    kept["amb_role"] = "to" if re.search(r"\b(to|tak|ko)\b|तक", ctx["text"], re.I) and not re.search(r"\b(from|se)\b|से", ctx["text"], re.I) else "from"
    ctx["sess"]["pending_intent"], ctx["sess"]["collected"], ctx["sess"]["asked"] = "search_trains", kept, 1
    return reply("clarification", t("ambiguous_station", ctx["lang"], place=alias.title(), options=opts))


FILLER = {"need", "want", "wanna", "like", "looking", "look", "find", "show", "search", "give", "tell", "help", "can", "could", "would", "should", "will", "get", "got",
          "have", "has", "for", "with", "from", "into", "onto", "about", "just", "only", "also", "some", "reservation", "journey", "trip", "seat", "seats", "berth",
          "refund", "status", "cancel", "cancellation", "booking", "bookings", "confirmed", "confirm", "charge", "charges", "fare", "price", "seat", "available", "availability",
          "sleeper", "chair", "executive", "premium", "class", "tier", "second", "third", "first", "rules", "rule", "policy", "pet", "pets", "dog", "cat", "luggage", "baggage",
          "what", "how", "where", "when", "why", "who", "which", "does", "late", "delay", "delayed", "lost", "wallet", "bag", "luggage", "hai", "chahiye", "chahie", "karna", "karni", "karo", "jana", "jaana", "mujhe", "hamein", "ek", "bhai", "yaar", "tak", "se", "ko", "ka", "ki", "ke"}


def _place_candidates(text):
    """Words that might be a place: after a preposition (to/from/se/tak/for/near/in), else the last unexplained word
    ('i need a ticket delhi' has no 'to', the leftover word is the place)."""
    out = []
    for mm in re.finditer(r"\b(?:to|from|se|tak|for|near|in)\s+([A-Za-z]{3,}(?:\s+[A-Za-z]{3,})?)", text):
        out.append(mm.group(1).split())
    if not out and re.search(r"\b(need|want|wanna|book|booking|ticket|tickets|go|going|travel|reach|trip|journey|jana|jaana|chahiye|चाहिए|जाना)\b", text, re.I):
        left = [w for w in re.findall(r"[A-Za-z]{3,}", text) if w.lower() not in STOP_PLACE and w.lower() not in FILLER and w.lower() not in dates.MONTHS]
        if left:
            out.append([left[-1]])
    return out


def unknown_place_reply(ctx):
    """A place the passenger named that is not a station: say so, suggest the closest names, list what we serve."""
    db, text, lang = ctx["db"], ctx["text"], ctx["lang"]
    known = tt.find_stations_in(db, text)
    for words in _place_candidates(text):
        first = words[0].lower()
        if first in STOP_PLACE or first in dates.MONTHS or first in FILLER:
            continue
        phrase = " ".join(words)
        if re.search(r"\bfor\s+%s\s+\d{1,3}\b(?!\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|/|-))" % re.escape(words[0]), text, re.I):
            continue                      # "for Neha 31": a traveller, not a place
        if und.norm_class(phrase) or und.norm_class(words[0]):
            continue
        if tt.resolve_station(db, phrase) or tt.ambiguous_in(db, phrase):
            continue
        sug = tt.suggest(db, words[0]) or (tt.suggest(db, phrase) if len(words) > 1 else [])
        if sug and sug[0] in known:
            continue                      # a typo that find_stations_in already repaired
        cities = ", ".join(sorted({r[0] for r in db.execute("SELECT city FROM stations")}))
        if sug:
            names = " / ".join("%s (%s)" % (station_label(db, c), c) for c in sug)
            return reply("clarification", t("unknown_place_suggest", lang, place=words[0].title(), names=names))
        return reply("clarification", t("unknown_place", lang, place=words[0].title(), cities=cities))
    return None


def llm_places(ctx):
    """When the rules cannot read the places, ask the language model (Ollama) which stations the passenger means.
    Its answer is only used if each place resolves to a real station in the database; otherwise it is ignored."""
    if not llm.available():
        return None
    db = ctx["db"]
    cities = sorted({r[0] for r in db.execute("SELECT city FROM stations")})
    got = llm.extract_places(ctx["text"], cities)
    if not got:
        return None
    frm = tt.resolve_station(db, got.get("from") or "") if got.get("from") else None
    to = tt.resolve_station(db, got.get("to") or "") if got.get("to") else None
    if not (frm or to):
        return None
    ctx["step"]("understand_llm_places", **{"from": frm, "to": to})
    if frm:
        ctx["slots"]["from_st"] = frm
    if to:
        ctx["slots"]["to_st"] = to
    ctx["slots"]["stations"] = [c for c in (frm, to) if c]
    return do_search(ctx)



def _fmt_time(iso):
    return fmt_dt(dt.datetime.fromisoformat(iso))


def followup(ctx):
    """Short messages that only make sense with the earlier conversation: 'cheapest one?', 'book the first one', 'what about the day after',
    'Rahul 30 and Meera 28' after a search, 'what is the refund' after a booking, small talk. Uses the session memory; returns None if it is not one."""
    text, sess, slots, lang = ctx["text"].strip(), ctx["sess"], ctx["slots"], ctx["lang"]
    low = text.lower()
    short = len(low.split()) <= 9
    if re.match(r"^\s*(thanks|thank you|thx|ty|shukriya|dhanyavaad|dhanyavad|धन्यवाद|शुक्रिया)\b", low):
        return reply("answer", t("thanks", lang))
    if re.match(r"^\s*(bye|goodbye|good bye|see you|alvida|ok bye|tata)\b", low):
        return reply("answer", t("bye", lang))
    if re.match(r"^\s*(help|menu|options|start|madad)\s*[?!.]*\s*$", low):
        return reply("answer", t("help", lang))
    if re.match(r"^\s*(i |we )?(want|need|wanna|would like) to (change|modify|edit|update) (something|anything|my (booking|ticket)|it)\s*[?.!]*\s*$", low):
        return do_unsupported_change(ctx)
    if re.search(r"\b(what can you do|what do you do|how can you help|can you help me|help me|what can i ask|kya kar sakte|kya madad)\b", low) and not slots.get("booking_id"):
        return reply("answer", t("help", lang))
    db = ctx["db"]
    if re.search(r"\b(hotel|hotels|flight|flights|cab|taxi|restaurant|movie|weather|visa|cricket|stock|recipe|pizza|resort|joke|poem|song|bus ticket|shopping)\b", low) and not slots.get("booking_id"):
        return reply("not_found", t("out_of_scope", lang))
    money_w = re.search(r"refund|cancel|charge|fee|rule|polic|penalt|tatkal|wapas|paisa", low)
    free = not sess.get("pending_intent")          # not in the middle of a question we asked
    # an unknown 5-digit train number such as 12123
    m5 = re.search(r"\b(\d{5})\b", text)
    if free and m5 and not slots.get("train_no") and not slots.get("booking_id") and re.search(r"train|seat|fare|ticket|berth|gaadi|available|price", low) and not re.search(r"\bpnr\b", low):
        return reply("clarification", t("unknown_train", lang, no=m5.group(1)))
    # a train named with a seat / fare question, or just "UJ1006 25 nov": search that train over its whole route
    if free and slots.get("train_no") and not slots.get("booking_id") and not money_w and (
            re.search(r"\b(seat|seats|available|availability|vacant|berth|fare|price|cost|how much|kitna|kitne|left|khaali|rac|waiting)\b|सीट|किराया", low)
            or (slots.get("date") and len(low.split()) <= 6 and not re.search(r"status|pnr|book\b", low))):
        return do_search(dict(ctx, intent="search_trains"))
    # a personal refund question: "how much will I get back if I cancel my 2AC ticket", "kal ki train cancel karni hai, kitna paisa wapas milega"
    if (free and not slots.get("booking_id") and re.search(r"(refund|get back|money back|wapas|paisa|paise|पैसे|वापस|how much (will|would|do|can|shall) (i|we) (get|receive))", low)
            and re.search(r"\b(my|mine|mera|meri|mere|tomorrow|tomorrows|kal|aaj|today|ticket|booking)\b|मेरा|मेरी|कल|आज", low)
            and not re.search(r"polic|rule|how long|when will|kab tak|process|timeline|days|working|business", low)
            ):
        return do_refund_estimate(dict(ctx, intent="refund_estimate"))
    # "is my ticket confirmed", "mera ticket confirm hai kya"
    if free and not slots.get("booking_id") and re.search(r"\b(is|are|mera|meri|my)\b.{0,25}\b(ticket|booking|seat|tickets)\b.{0,25}\b(confirm\w*|cnf|rac|wl|waitlist\w*|clear\w*)\b|\b(ticket|booking)\b.{0,20}\bconfirm (hai|hua|ho)", low) and not money_w:
        return do_status(dict(ctx, intent="booking_status"))
    # bare "refund?" : which booking?  bare "UJ1006?" : search that train
    if free and re.match(r"^\s*(refund|refunds|my refund)\s*[?.!]*\s*$", low):
        slots["_personal"] = True
        return do_refund_estimate(dict(ctx, intent="refund_estimate"))
    if free and slots.get("train_no") and len(low.split()) <= 3 and not slots.get("booking_id"):
        return do_search(dict(ctx, intent="search_trains"))
    # a bare wish: "ticket", "i need a ticket", "i want to travel"
    if free and (re.search(r"^\s*(i |we )?(need|want|wanna|would like|looking for|chahiye)?\s*(a |one |an |to )?(ticket|tickets|travel|journey|trip|train ticket|go somewhere)\s*[.!?]*\s*$", low)
            or re.search(r"^\s*(i |we )?(need|want|wanna|would like) to (travel|go|take a train|book)\s*[.!?]*\s*$", low)):
        return do_book(dict(ctx, intent="book_ticket"))
    # a bare station name: ask whether it is the start or the end
    if tt.find_stations_in(db, text) and len(low.split()) <= 3 and not slots.get("booking_id") and not slots.get("train_no") and not sess.get("pending_intent"):
        return do_search(dict(ctx, intent="search_trains"))
    ls, lr = sess.get("last_search"), sess.get("last_results")
    if ls and lr and short:
        db = ctx["db"]
        cls = slots.get("class") or sess.get("last_class")
        def fare_of(r):
            f = r["fares"]
            if cls and cls in f:
                return f[cls]
            return min(f.values()) if f else 10 ** 12
        pick, what = None, None
        if re.search(r"\b(cheapest|cheap|lowest fare|least expensive|sasta|sasti|सस्ता|सस्ती)\b", low):
            pick, what = min((r for r in lr if r["fares"]), key=fare_of, default=None), "w_cheapest"
        elif re.search(r"\b(fastest|quickest|shortest|least time|tez|तेज़|तेज)\b", low):
            pick, what = min(lr, key=lambda r: r["mins"]), "w_fastest"
        elif re.search(r"\b(earliest|first train|first one|pehli)\b", low) and not re.search(r"\bbook\b|seat|available|berth", low) and not slots.get("class"):
            pick, what = lr[0], "w_earliest"
        elif re.search(r"\b(latest|last train|last one)\b", low) and not re.search(r"\bbook\b|seat|available|berth", low) and not slots.get("class"):
            pick, what = lr[-1], "w_latest"
        if pick and what:
            c = cls if cls in pick["fares"] else (min(pick["fares"], key=pick["fares"].get) if pick["fares"] else "")
            return reply("answer", t("pick_best", lang, what=t(what, lang), date=fmt_date(ls["date"]), frm=station_label(db, ls["frm"]), to=station_label(db, ls["to"]),
                                     train=pick["train_no"], name=pick["name"], dep=_fmt_time(pick["dep"]), arr=_fmt_time(pick["arr"]), cls=c,
                                     fare=inr(pick["fares"].get(c, 0))), tools=[tool("compare_results", {"criterion": what}, train_no=pick["train_no"], fares=pick["fares"], minutes=pick["mins"], departs=pick["dep"], arrives=pick["arr"])])
        # "book the first one / the cheapest / UJ1006"
        if re.search(r"\b(book|take|choose|select|pick|go with|confirm)\b", low) and not slots.get("train_no"):
            m = re.search(r"\b(first|second|third|last|cheapest|fastest|earliest|latest)\b", low)
            if m:
                w = m.group(1)
                tr = {"first": lr[0], "earliest": lr[0], "last": lr[-1], "latest": lr[-1], "second": lr[1] if len(lr) > 1 else None, "third": lr[2] if len(lr) > 2 else None,
                      "cheapest": min((r for r in lr if r["fares"]), key=fare_of, default=None), "fastest": min(lr, key=lambda r: r["mins"])}[w]
                if tr:
                    slots["train_no"] = tr["train_no"]
                    return do_book(dict(ctx, intent="book_ticket"))
        # travellers typed right after a search ("Rahul 30 and Meera 28") start a booking
        if slots.get("travellers") and not slots.get("booking_id"):
            if len(lr) == 1 and not slots.get("train_no"):
                slots["train_no"] = lr[0]["train_no"]
            return do_book(dict(ctx, intent="book_ticket"))
        # date moves: "the day after", "next day", "previous day"
        mv = 1 if re.search(r"\b(next day|the day after|day after$|following day|agle din|अगले दिन)\b", low) and "tomorrow" not in low else (-1 if re.search(r"\b(previous day|day before|pichle din)\b", low) else 0)
        if mv and not slots.get("date"):
            nd = (dt.date.fromisoformat(ls["date"]) + dt.timedelta(days=mv)).isoformat()
            slots["date"] = nd
            return do_search(ctx)
        if re.search(r"\b(how much|price|fare|cost|kitna|kharcha|kiraya|कितना|किराया)\b", low) and not re.search(r"refund|cancel|charge|tatkal|fee", low):
            return do_search(ctx)
    # a problem report ("my train is late", "i lost my wallet") is not a search request
    if (not slots.get("stations") and not slots.get("date") and not slots.get("train_no") and not slots.get("class") and not slots.get("booking_id")
            and re.search(r"\b(late|delayed|delay|lost|stolen|missing|misplaced|dirty|broken|rude|complain\w*|wallet|phone|not working|smell|noisy|overcrowded)\b", low)):
        r = do_rules(ctx)
        words = set(re.findall(r"late|delayed|delay|lost|stolen|missing|misplaced|dirty|broken|rude|complain\w*|wallet|phone|smell|noisy|overcrowded", low))
        need = {"late": "delay", "delayed": "delay", "delay": "delay", "lost": "lost", "missing": "lost", "misplaced": "lost", "wallet": "lost", "phone": "lost", "stolen": "stolen"}
        keys = {need.get(w, w[:6]) for w in words}
        if r["answer_type"] != "not_found" and not any(k in (r["answer"] + r.get("_doc_text", "")).lower() for k in keys):
            return reply("not_found", t("rules_not_found", lang))       # retrieved text is about something else: do not pretend it answers
        return r
    # a booking was just shown or previewed: "what is the refund", "and the status?"
    lb = sess.get("last_booking")
    if lb and short and not slots.get("booking_id") and re.search(r"\b(how much|what('s| is| will)?)\b.{0,25}\brefund\b|\brefund (amount|will i get)\b|\bkitna refund\b", low) and not re.search(r"polic|rule|process|how long|when", low):
        slots["booking_id"] = lb
        return do_refund_estimate(dict(ctx, intent="refund_estimate"))
    return None


def do_unknown(ctx):
    """Not a known request type. If it looks like a question about the rules, try the documents; otherwise say what we can do."""
    text = ctx["text"]
    if re.search(r"\b(hotel|hotels|flight|flights|cab|taxi|restaurant|bus|movie|weather|visa|cricket|stock|recipe|pizza|resort|joke|poem|song|news|match|score|shopping|order)\b", text, re.I):
        return reply("not_found", t("out_of_scope", ctx["lang"]))
    if (ctx["sess"].get("last_search") and (ctx["slots"].get("date") or ctx["slots"].get("class") or ctx["slots"].get("train_no"))
            and len(text.split()) <= 8 and not re.search(r"refund|cancel|charge|fee|rule|policy|penalt", text, re.I)):
        return do_search(ctx)                  # short follow-up to the last search: "what about 1 Dec", "AC2 only", "UJ1024 AC3?"
    if len(text.split()) >= 4 and not re.search(r"(ticket|book|need|want|go to|travel)", text, re.I) and not re.search(r"(\?|\bhow\b|\bwhat\b)", text, re.I):
        r = do_rules(ctx)
        if r["answer_type"] != "not_found":
            return r
    if re.search(r"(\?|\bhow\b|\bwhat\b|\bwhen\b|\bwhich\b|\bcan\b|\bis\b|\bare\b|\bdo\b|\bkya\b|\bkaise\b|\bkitn|\bkab\b|क्या|कैसे|कितन|कब)", text, re.I):
        r = do_rules(ctx)
        if r["answer_type"] != "not_found":
            return r
    if re.search(r"(ticket|train|book|travel|go|reach|journey|seat|gaadi|jaana|जाना|टिकट|ट्रेन)|\bfrom\b.+\bto\b", text, re.I):
        amb = tt.ambiguous_in(ctx["db"], text)
        if amb:
            return ambiguous_reply(ctx, amb)
        if not ctx["slots"].get("stations"):
            r = llm_places(ctx)
            if r:
                return r
        r = unknown_place_reply(ctx)
        if r:
            return r
        if ctx["slots"].get("stations"):          # one real station (possibly typed with a typo) and a wish to travel: ask for the rest
            return do_search(ctx)
    sl = ctx["slots"]
    if len(text.split()) >= 1 and not sl.get("booking_id") and not ((sl.get("class") or sl.get("date") or sl.get("travellers")) and len(text.split()) <= 3):
        r = do_rules(ctx)                 # last try: any short topic word ("id proof", "konsa ID chalega") may be in the documents
        if r["answer_type"] != "not_found":
            return r
    if re.search(r"(ticket|train|booking|book|seat|refund|cancel|station|fare|journey|travel|platform|berth|coach|pnr|gaadi|टिकट|ट्रेन|बुकिंग|रद्द|यात्रा)", text, re.I):
        return reply("clarification", t("unknown", ctx["lang"]))
    if sl.get("class") or sl.get("date") or sl.get("travellers") or sl.get("stations"):
        return reply("clarification", t("unknown", ctx["lang"]))              # we understood a piece but not the request: say what we can do
    return reply("not_found", t("out_of_scope", ctx["lang"]))


def do_privacy(ctx):
    return reply("refusal", t("refuse_privacy", ctx["lang"]), sources=[{"doc_id": "RUL-006", "section": "3.6"}])


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
    """Plain explanation of the calculation. Every number comes from the quote (code), never from a model."""
    if q["band"] == "OPERATOR":
        return t("why_OPERATOR", lang)
    parts = []
    cls = inr(q["charge"])
    if q["band"] == "E":
        return t("why_E", lang)
    sts = {l.get("status") for l in q["lines"]}
    if q["tatkal"] and "CNF" in sts:
        parts.append(t("why_TATKAL", lang))
    if "RAC" in sts:
        parts.append(t("why_RAC", lang, chg=inr(q["rac_charge"])))
    if "WL" in sts:
        parts.append(t("why_WL", lang, chg=inr(q["wl_charge"])))
    if "CNF" in sts and not q["tatkal"]:
        if q["band"] == "A":
            parts.append(t("why_A", lang, cls=cls))
        else:
            parts.append(t("why_" + q["band"], lang, pct=q["pct"], cls=cls))
    return " ".join(parts)


def do_refund_estimate(ctx):
    db, pid, lang, as_of = ctx["db"], ctx["pid"], ctx["lang"], ctx["as_of"]
    sl = ctx["slots"]
    personal = (sl.get("_personal") or sl.get("class") or sl.get("date") or sl.get("train_no") or sl.get("from_st") or sl.get("to_st")
                or re.search(r"\b(my|mine|mera|meri|mere|tomorrow|tomorrows|kal|aaj|today|ticket|booking)\b|मेरा|मेरी|कल|आज", ctx["text"], re.I))
    if not sl.get("booking_id") and not last_ref(ctx) and not (personal and not re.search(r"polic|rule|how long|process|timeline", ctx["text"], re.I)):
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
    if q["band"] == "OPERATOR":
        return reply("answer", t("operator_done", lang, bid=b["booking_id"], refund=inr(q["total_refund"])), tools=[tool("quote_refund", q)], sources=q["sources"])
    if q["hours_before"] <= 0:
        return reply("answer", t("departed_refund", lang, bid=b["booking_id"], refund=inr(0)), tools=[tool("quote_refund", q)], sources=q["sources"])
    dep = clock.parse_dt(q["departure"])
    ans = t("refund_estimate", lang, bid=b["booking_id"], hours=fmt_hours(q["hours_before"]), frm=station_label(db, q["from_code"]),
            dep=fmt_dt(dep), refund=inr(q["total_refund"]), paid=inr(q["total_paid"]), why=why_text(q, lang))
    return reply("answer", ans, sources=q["sources"], tools=[tool("quote_refund", q)])


def who_text(q):
    return ", ".join("%s (%s)" % (l["name"], inr(l["refund"])) for l in q["lines"])


def do_cancel(ctx):
    db, pid, lang, as_of, text = ctx["db"], ctx["pid"], ctx["lang"], ctx["as_of"], ctx["text"]
    ids = list(dict.fromkeys(re.findall(r"\bBKG\d{3,8}\b", text, re.I)))
    if re.search(r"\b(all|every|sabhi|saari|saare|everything)\b.{0,15}\b(bookings?|tickets?)\b|सभी बुकिंग", text, re.I) and not ids:
        mine = [b for b in bk.list_bookings(db, pid) if b["status"] not in ("CANCELLED", "OPERATOR_CANCELLED")]
        lst = "; ".join("%s (%s %s→%s, %s)" % (b["booking_id"], b["train_no"], b["from_code"], b["to_code"], fmt_date(b["journey_date"])) for b in mine)
        return reply("clarification", t("multi_cancel_all", lang, lst=lst))
    multi = len(ids) > 1
    if multi:
        ctx["slots"]["booking_id"] = ids[0].upper()
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
    ids_in_msg = list(dict.fromkeys(m.upper() for m in re.findall(r"\b(BKG\s?-?\d{4}|UR-?\d{8})\b", text, re.I)))
    ctx["multi"] = [x for x in ids_in_msg if x != b["booking_id"]]
    ctx["sess"]["last_booking"] = b["booking_id"]
    if not p["ok"]:
        if p["reason"] == "operator_cancelled":
            return reply("answer", t("operator_done", lang, bid=b["booking_id"], refund=inr(p["quote"]["total_refund"])), sources=p["quote"]["sources"],
                         tools=[tool("quote_refund", p["quote"])])
        key = {"already_cancelled": "already_cancelled", "departed": "departed"}.get(p["reason"], "unknown")
        return reply("answer", t(key, lang, bid=b["booking_id"]), sources=[{"doc_id": "RUL-003", "section": "3.1"}],
                     tools=[tool("propose_cancel", {k: v for k, v in p.items() if k != "quote"})])
    q = p["quote"]
    mins = cfg.get_int(db, "actions.pending_expiry_minutes", as_of, 10)
    ans = t("confirm_cancel", lang, bid=b["booking_id"], who=who_text(q), refund=inr(q["total_refund"]), paid=inr(q["total_paid"]),
            why=why_text(q, lang), mins=mins)
    if ctx.get("multi"):
        ans += " " + t("multi_note", lang, first=b["booking_id"], rest=", ".join(ctx["multi"]))
    src = dedupe(q["sources"])
    return reply("confirm_needed", ans, sources=src, pending=p["pending_action"],
                 tools=[tool("quote_refund", q), tool("propose_cancel", p["pending_action"])])


def do_change_boarding(ctx):
    db, pid, lang, as_of, slots = ctx["db"], ctx["pid"], ctx["lang"], ctx["as_of"], ctx["slots"]
    if not slots.get("booking_id") and not last_ref(ctx) and re.search(
            r"\b(can i|could i|may i|is it possible|how|what|when|until|allowed|kya|kaise|kab|sakta|sakti)\b|क्या|कैसे|कब", ctx["text"], re.I) and not slots.get("stations"):
        slots["topic"] = "boarding_change"           # a general question, not a request to change a booking
        return do_rules(ctx)
    slots.pop("from_st", None); slots.pop("to_st", None)         # the station named is the NEW boarding point, not a filter for finding the booking
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
        key = {"bad_station": "bad_station", "already_changed": "already_changed", "not_active": "not_active", "has_waitlisted": "has_waitlisted"}.get(r, "unknown")
        sec = {"bad_station": "3.3", "already_changed": "3.1", "not_active": "3.6", "has_waitlisted": "3.6"}.get(r, "3.6")
        return reply("refusal", t(key, lang, bid=b["booking_id"]), tools=[tool("propose_change_boarding", p)], sources=[{"doc_id": "RUL-010", "section": sec}])
    pv = p["preview"]
    mins = cfg.get_int(db, "actions.pending_expiry_minutes", as_of, 10)
    src = [pv["source"], {"doc_id": "RUL-010", "section": "3.5"}]
    ans = t("confirm_change", lang, bid=b["booking_id"], old=station_label(db, pv["old_code"]), new=station_label(db, pv["new_code"]),
            dep=fmt_dt(clock.parse_dt(pv["new_departure"])), hours=pv["hours"], src="%s %s" % (pv["source"]["doc_id"], pv["source"]["section"]), mins=mins)
    return reply("confirm_needed", ans, sources=src, pending=p["pending_action"], tools=[tool("propose_change_boarding", p)])


def time_window(text):
    """'after 6 pm', 'before 10 am', 'morning' -> (from_minute, to_minute) of the day, else None."""
    low = text.lower()
    def mins(h, m, ap):
        h, m = int(h), int(m or 0)
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        return h * 60 + m
    m = re.search(r"\b(after|later than|post|baad)\s+(\d{1,2})(?::(\d\d))?\s*(am|pm)?\b", low)
    if m:
        ap = m.group(4) or ("pm" if 1 <= int(m.group(2)) <= 11 and "pm" in low else None)
        return mins(m.group(2), m.group(3), ap), 24 * 60
    m = re.search(r"\b(before|earlier than|by|pehle)\s+(\d{1,2})(?::(\d\d))?\s*(am|pm)?\b", low)
    if m and not re.search(r"\b(hours?|ghante)\b", low[m.end():m.end() + 8]):
        return 0, mins(m.group(2), m.group(3), m.group(4))
    for word, lo, hi in (("morning", 300, 720), ("subah", 300, 720), ("afternoon", 720, 1020), ("dopahar", 720, 1020), ("evening", 1020, 1260), ("shaam", 1020, 1260),
                         ("night", 1260, 1440), ("raat", 1260, 1440)):
        if re.search(r"\b%s\b" % word, low):
            return lo, hi
    return None


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
        return t("no_seat_data", lang)
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
    ls = ctx["sess"].get("last_search")
    if slots.get("train_no") and len(sts) < 2 and not slots.get("from_st") and not slots.get("to_st"):
        # "is there a 3AC seat on UJ1006 on 25 Nov": no stations named, so use the train's whole route (or the route just searched)
        stops = [r[0] for r in db.execute("SELECT station_code FROM train_stops WHERE train_no=? ORDER BY stop_order", (slots["train_no"],))]
        if ls and ls["frm"] in stops and ls["to"] in stops and stops.index(ls["frm"]) < stops.index(ls["to"]):
            sts = [ls["frm"], ls["to"]]
            slots.setdefault("date", ls["date"])
        elif len(stops) >= 2:
            sts = [stops[0], stops[-1]]
        if len(sts) == 2:
            slots["stations"] = sts
            ctx["step"]("context", note="route of %s: %s->%s" % (slots["train_no"], sts[0], sts[1]))
    if (not sts and not slots.get("from_st") and not slots.get("to_st") and ls and not ctx["sess"].get("collected")
            and (slots.get("train_no") or slots.get("class") or slots.get("date") or not tt.ambiguous_in(db, ctx.get("text", "")))
            and not tt.find_stations_in(db, ctx.get("text", ""))):
        # a follow-up ("is there an AC3 seat on UJ1024", "what about tomorrow"): keep the route and date from the last search
        sts = [ls["frm"], ls["to"]]
        slots["stations"] = sts
        slots.setdefault("date", ls["date"])
        ctx["step"]("context", note="reused last search %s->%s %s" % (ls["frm"], ls["to"], ls["date"]))
    if len(sts) < 2:
        if not sts and not ctx["sess"].get("collected"):
            r = llm_places(ctx)
            if r:
                return r
        up = unknown_place_reply(ctx)
        if up:
            return up
    amb = tt.ambiguous_in(db, ctx["text"]) if ctx.get("text") else []
    if amb:
        return ambiguous_reply(ctx, amb)
    missing = []
    fs, ts = slots.get("from_st"), slots.get("to_st")
    if len(sts) == 1 and not fs and not ts and not slots.get("amb_role") and not re.search(r"\b(from|to|se|tak|for|into|towards)\b|से|तक", ctx.get("text", ""), re.I):
        # one station and no hint whether it is the start or the end: ask instead of guessing
        col = dict(slots)
        col["role_pending"] = sts[0]
        sess = ctx["sess"]
        asked = sess.get("asked", 0) if sess.get("pending_intent") == "search_trains" else 0
        if asked < MAX_FOLLOWUPS:
            sess["pending_intent"], sess["collected"], sess["asked"] = "search_trains", col, asked + 1
            return reply("clarification", t("ask_role", lang, st="%s (%s)" % (station_label(db, sts[0]), sts[0])))
    if len(sts) < 2 and fs and ts:
        sts = [fs, ts]
        slots["stations"] = sts
    if len(sts) == 1 and ts and not fs:
        missing.append("m_from")
    elif len(sts) < 1:
        missing.append("m_from")
    if len(sts) < 2 and not (len(sts) == 1 and ts and not fs):
        missing.append("m_to")
    if not slots.get("date"):
        missing.append("m_date")
    if missing:
        if len(sts) == 1 and "m_from" not in missing:
            pass
        return route_ask(ctx, "search_trains", missing, dict(slots))
    frm, to = sts[0], sts[1]
    done_asking(ctx)
    if slots["date"] < as_of.date().isoformat():
        return reply("clarification", t("past_date", lang, date=fmt_date(slots["date"]), today=fmt_date(as_of)))
    res = search_for(ctx, frm, to, slots["date"])
    if slots.get("train_no"):
        res = [r for r in res if r["train_no"] == slots["train_no"]]
    window_note = ""
    tw = time_window(ctx.get("text", ""))
    if tw and res:
        inside = [r for r in res if tw[0] <= r["departs"].hour * 60 + r["departs"].minute < tw[1]]
        if inside:
            res = inside
        else:
            window_note = t("time_none", lang) + "\n"
    head_kw = dict(frm=station_label(db, frm), to=station_label(db, to), date=fmt_date(slots["date"]))
    if res and slots.get("class"):
        with_cls = [r for r in res if slots["class"] in r["class_info"]]
        if with_cls:
            res = with_cls
        else:
            have = sorted({c for r in res for c in r["class_info"]})
            ctx["sess"]["last_search"] = {"frm": frm, "to": to, "date": slots["date"]}
            return reply("answer", t("no_class", lang, cls=slots["class"], have=", ".join(have), **head_kw), tools=[tool("search_trains", [], frm=frm, to=to, date=slots["date"])])
    if not res:
        msg = t("search_none", lang, **head_kw)
        a = [station_label(db, c) for c in tt.reachable(db, frm=frm)]
        b = [station_label(db, c) for c in tt.reachable(db, to=to)]
        if not tt.search_trains(db, frm, to, slots["date"]) and a and b:
            direct_any = any(True for d in range(0, 7) if tt.search_trains(db, frm, to, (as_of.date() + __import__("datetime").timedelta(days=d)).isoformat()))
            if not direct_any:
                msg += " " + t("search_none_hint", lang, frm=head_kw["frm"], to=head_kw["to"], a=", ".join(a), b=", ".join(b))
        return reply("answer", msg, tools=[tool("search_trains", [], frm=frm, to=to, date=slots["date"])])
    lines = [window_note + t("search_head", lang, **head_kw)]
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
    ctx["sess"]["last_class"] = slots.get("class")
    ctx["sess"]["last_results"] = [{"train_no": r["train_no"], "name": r["name"], "dep": clock.iso(r["departs"]), "arr": clock.iso(r["arrives"]),
                                    "mins": int((r["arrives"] - r["departs"]).total_seconds() // 60),
                                    "fares": {c: i["fare"] for c, i in r["class_info"].items() if i["fare"]}} for r in res[:6]]
    return reply("answer", "\n".join(lines), tools=tools)


def do_book(ctx):
    db, pid, lang, slots, as_of = ctx["db"], ctx["pid"], ctx["lang"], ctx["slots"], ctx["as_of"]
    sts = slots.get("stations", [])
    ls = ctx["sess"].get("last_search")
    if len(sts) < 2 and slots.get("train_no") and not slots.get("from_st") and not slots.get("to_st"):
        stops = [r[0] for r in db.execute("SELECT station_code FROM train_stops WHERE train_no=? ORDER BY stop_order", (slots["train_no"],))]
        if ls and ls["frm"] in stops and ls["to"] in stops and stops.index(ls["frm"]) < stops.index(ls["to"]):
            sts = [ls["frm"], ls["to"]]
            slots.setdefault("date", ls["date"])
        elif len(stops) >= 2:
            sts = [stops[0], stops[-1]]
    if len(sts) < 2 and ls:
        sts = [ls["frm"], ls["to"]]
        slots.setdefault("date", ls["date"])
    if len(sts) < 2 and ctx.get("text"):
        if not sts:
            r = llm_places(ctx)
            if r:
                return r
        amb = tt.ambiguous_in(db, ctx["text"])
        if amb:
            return ambiguous_reply(ctx, amb)
        up = unknown_place_reply(ctx)
        if up:
            return up
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
    if chosen and slots["class"] not in chosen[0]["class_info"]:
        have = ", ".join(sorted(chosen[0]["class_info"]))
        ctx["sess"]["pending_intent"], ctx["sess"]["collected"] = "book_ticket", {k: v for k, v in dict(col).items() if k != "class"}
        return reply("clarification", t("train_no_class", lang, no=train_no, cls=slots["class"], have=have))
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
        kw = {"max": p.get("max"), "days": p.get("days"), "mins": p.get("minutes"), "opens": fmt_date(p["opens"]) if p.get("opens") else ""}
        key = {"regret": "regret", "departed": "closed_b", "too_early": "too_early_b", "bad_traveller_count": "too_many", "service_cancelled": "service_cancelled"}.get(r, "unknown")
        sec = {"regret": ("RUL-004", "3.2"), "departed": ("RUL-001", "3.5"), "too_early": ("RUL-001", "3.1"), "bad_traveller_count": ("RUL-001", "3.3"),
               "service_cancelled": ("RUL-011", "3.1")}.get(r, ("RUL-001", "3.4"))
        return reply("answer", t(key, lang, **kw), sources=[{"doc_id": sec[0], "section": sec[1]}], tools=[tool("propose_book", p)])
    pv = p["preview"]
    mins = cfg.get_int(db, "actions.pending_expiry_minutes", as_of, 10)
    who = ", ".join("%s (%s) %s %s" % (l["name"], l["age"], l["status"], inr(l["fare"])) for l in pv["lines"])
    ans = t("confirm_book", lang, train=train_no, frm=station_label(db, sts[0]), to=station_label(db, sts[1]), cls=slots["class"],
            dep=fmt_dt(clock.parse_dt(pv["departure"])), who=who, total=inr(pv["total"]), mins=mins)
    return reply("confirm_needed", ans, sources=[{"doc_id": "RUL-001", "section": "3.4"}, {"doc_id": "RUL-004", "section": "3.2"}],
                 pending=p["pending_action"], tools=[tool("propose_book", pv)])


def do_deadline(ctx):
    db, pid, lang, as_of, text = ctx["db"], ctx["pid"], ctx["lang"], ctx["as_of"], ctx["text"]
    if not ctx["slots"].get("booking_id") and not last_ref(ctx) and not ctx["slots"].get("train_no"):
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
    ans = t("deadline_refund", lang, bid=b["booking_id"], dep=fmt_dt(bands["departure"]), a=fmt_dt(bands["a_until"]), b=fmt_dt(bands["b_until"]),
            c=fmt_dt(bands["c_until"]), pb=bands["pct_b"], pc=bands["pct_c"], pd=bands["pct_d"])
    return reply("answer", ans, sources=[{"doc_id": "RUL-003", "section": "3.4"}, {"doc_id": "RUL-003", "section": "3.5"}],
                 tools=[tool("refund_bands", {k: (clock.iso(v) if hasattr(v, "isoformat") else v) for k, v in bands.items()})])


SETTING_QUESTIONS = [(re.compile(r"tatkal.{0,30}(supplement|charge|fee)|(supplement|charge|fee).{0,30}tatkal|तत्काल", re.I), "tatkal_supplement_%s", "setting_tatkal"),
                     (re.compile(r"(fixed|flat|minimum|cancel\w*|radd).{0,20}(charge|fee|shulk)|cancel\w* (charge|fee)", re.I), "cancel_fixed_charge_%s", "setting_cancel")]


def setting_answer(ctx):
    """A class-specific money number is read straight from the dated settings, so the newest circular always wins."""
    cls = ctx["slots"].get("class")
    from tools import settings as cfg
    if not cls:
        for rx, key, tkey in SETTING_QUESTIONS:
            if rx.search(ctx["text"]):                    # no class named: answer for every class that has the setting
                names = [r[0] for r in ctx["db"].execute("SELECT DISTINCT name FROM settings WHERE name LIKE ? ORDER BY name", (key.replace("%s", "") + "%",))]
                parts, src, tl = [], [], []
                for n in names:
                    val = cfg.get(ctx["db"], n, ctx["as_of"])
                    if val is None:
                        continue
                    try:
                        money = inr(int(round(float(val) * 100)))
                    except ValueError:
                        continue
                    c = n.rsplit("_", 1)[-1].upper()
                    parts.append(t(tkey, ctx["lang"], cls=c, amount=money, date=fmt_date(ctx["as_of"].date().isoformat())))
                    doc, sec = cfg.source(ctx["db"], n, ctx["as_of"])
                    if doc and {"doc_id": doc, "section": sec.replace("Section ", "")} not in src:
                        src.append({"doc_id": doc, "section": sec.replace("Section ", "")})
                    tl.append({"name": n, "value": val})
                if parts:
                    return reply("answer", "\n".join(parts), sources=src, tools=[tool("get_setting", tl)])
        return None
    for rx, key, tkey in SETTING_QUESTIONS:
        if rx.search(ctx["text"]):
            name = key % cls.lower()
            val = cfg.get(ctx["db"], name, ctx["as_of"])
            if val is None:
                return None
            doc, sec = cfg.source(ctx["db"], name, ctx["as_of"])
            try:
                money = inr(int(round(float(val) * 100)))
            except ValueError:
                return None
            src = [{"doc_id": doc, "section": sec.replace("Section ", "")}] if doc else []
            return reply("answer", t(tkey, ctx["lang"], cls=cls, amount=money, date=fmt_date(ctx["as_of"].date().isoformat())), sources=src,
                         tools=[tool("get_setting", {"name": name, "value": val, "source": doc})])
    return None


def do_rules(ctx):
    db, lang, as_of, slots = ctx["db"], ctx["lang"], ctx["as_of"], ctx["slots"]
    prev = ctx["sess"].get("last_rules_q")
    if prev and len(ctx["text"].split()) <= 5 and re.match(r"^\s*(and|what about|how about|aur|or|also)\b", ctx["text"], re.I):
        ctx["text"] = prev + " " + ctx["text"]                     # "and for AC3?" continues the earlier rules question
    elif len(ctx["text"].split()) >= 2:
        ctx["sess"]["last_rules_q"] = ctx["text"]
    sa = setting_answer(ctx)
    if sa:
        return sa
    idx = store.get_index(db)
    asof_d = as_of.date().isoformat()
    res = retrieval.retrieve(idx, ctx["text"], asof_d, topic=slots.get("topic"))
    ctx["step"]("retrieve", abstain=res["abstain"], winner=(res["winner"]["doc_id"] + " " + res["winner"]["section"]) if res["winner"] else None,
                overridden=[o["doc_id"] for o in res["overridden"]])
    if res["abstain"]:
        return reply("not_found", t("rules_not_found", lang))
    w = res["winner"]
    shown = w
    secno = lambda x: x.replace("Section ", "")  # noqa: E731
    if w["doc"]["doc_type"] == "circular":
        # a circular is shown by its details + effective-date sections, not by an example paragraph
        extra = [it for it in idx.items if it["doc"]["doc_id"] == w["doc_id"] and secno(it["section"]) in ("3", "4")]
        if extra:
            w = dict(w, section="3-4" if len(extra) > 1 else secno(extra[0]["section"]), text="\n".join(it["text"] for it in extra))
            shown = w
    src = [{"doc_id": w["doc_id"], "section": secno(w["section"])}]
    # same-language FAQ that agrees with the winner can be the readable text for Hindi/Hinglish users
    if lang in ("hi", "hinglish") and w["doc"]["language"] != lang:
        for h in res["hits"]:
            if h["doc"]["language"] == lang and h["doc"]["topic"] == w["doc"]["topic"] and retrieval.numbers_in(h["text"]) == retrieval.numbers_in(w["text"]):
                shown = h
                src.append({"doc_id": h["doc_id"], "section": secno(h["section"])})
                break
    body = shown["text"]
    plain = "%s %s" % (t("rules_prefix", lang, src="%s %s" % (w["doc_id"], secno(w["section"]))), body)
    ans = plain
    notes = []
    for u in res["upcoming"]:
        if u["doc"]["topic"] == w["doc"]["topic"] and u["doc"]["supersedes"]:
            notes.append(t("upcoming_note", lang, doc=u["doc_id"], date=fmt_date(u["doc"]["effective_from"])))
            src.append({"doc_id": u["doc_id"], "section": secno(u["section"])})
            break
    if res["overridden"]:
        notes.append(t("overridden_note", lang, docs=", ".join(sorted({o["doc_id"] for o in res["overridden"]}))))
    if llm.available() and shown["doc"]["language"] == "en" or (llm.available() and lang != "en"):
        rw = llm.reword(body, ctx["text"], lang)
        if rw and len(rw) < 900:
            ans = "%s %s" % (t("rules_prefix", lang, src="%s %s" % (w["doc_id"], secno(w["section"]))), rw.strip())
    doc_text = w["text"] + " " + shown["text"] + " " + " ".join(u["text"] for u in res["upcoming"])
    if re.match(r"\s*((why|kyun|kyon|kyu|reason|what is the reason|iski wajah)\b|क्यों|क्यूँ)", ctx["text"], re.I):
        notes.append(t("no_reason_note", lang))       # the documents state rules, not their reasons: never invent one
    if notes:
        ans += "\n" + " ".join(notes)
        plain += "\n" + " ".join(notes)
    return reply("answer", ans, sources=dedupe(src), doc_text=doc_text, tools=[tool("search_documents", {"winner": w["doc_id"], "section": w["section"],
                 "overridden": [o["doc_id"] for o in res["overridden"]]})], extra={"plain_answer": plain})


def handoff_text(lang, h):
    if h.get("category") == "safety":
        return t("handoff_safety", lang, desk=h["desk"], hid=h["handoff_id"], target=h["ack_target"], channel=h["emergency_channel"])
    return t("handoff", lang, desk=h["desk"], hid=h["handoff_id"], target=h["ack_target"])


def do_unsupported_change(ctx):
    from tools import settings as cfg
    hrs = cfg.get_int(ctx["db"], "boarding_change.cutoff_hours_before_origin", ctx["as_of"], 6)
    return reply("refusal", t("unsupported_change", ctx["lang"], hours=hrs), sources=[{"doc_id": "RUL-010", "section": "3.1"}])


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
    return reply("handed_to_human", handoff_text(lang, h), handed=True, tools=tools,
                 sources=[{"doc_id": "RUL-012", "section": {"safety": "3.3", "privacy": "3.4", "refund_dispute": "3.2"}.get(h["category"], "3.5")}])


def do_forbidden(ctx):
    lang, text = ctx["lang"], ctx["text"]
    if re.search(r"(someone else|somebody|my (friend|brother|sister|colleague|neighbou?r|boss|wife|husband)|his|her|their|kisi aur|dost|bhai|behen|padosi)", text, re.I):
        return reply("refusal", t("own_only", lang), sources=[{"doc_id": "RUL-006", "section": "3.6"}])
    if re.search(r"(jump|skip|ahead|upar|aage|waiting|waitlist)", text, re.I):
        return reply("refusal", t("refuse_policy", lang), sources=[{"doc_id": "RUL-004", "section": "3.3"}])
    if re.search(r"(fare|kiraya|price)", text, re.I):
        return reply("refusal", t("refuse_policy", lang), sources=[{"doc_id": "RUL-002", "section": "3.4"}])
    return reply("refusal", t("refuse_policy", lang), sources=[{"doc_id": "RUL-012", "section": "3.6"}])
