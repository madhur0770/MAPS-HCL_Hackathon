"""FastAPI service: the 7 endpoints from the brief plus two demo helpers.
Identity comes ONLY from the X-Passenger-Id header. Every handler runs under one lock (SQLite is single-writer)."""
import json
import logging
import os
import threading
import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from actions import manager as am
from app.schemas import ChatIn, IngestIn
from assistant import guardrails, router
from assistant.i18n import t
from core import clock, config, db as dbm, seed
from core.text import inr
from rag import ingest as ing
from tools import bookings as bk

log = logging.getLogger("ujjwal")
logging.basicConfig(level=logging.INFO, format="%(message)s")
LOCK = threading.RLock()
_hits = defaultdict(deque)


def make_app(db_conn=None):
    app = FastAPI(title="Ujjwal Rail Travel Assistant", version="1.0")
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
    db = db_conn or dbm.connect()
    dbm.init_db(db)
    if db.execute("SELECT count(*) FROM stations").fetchone()[0] == 0:
        seed.seed(db, anchor=os.getenv("DATA_ANCHOR", seed.ANCHOR_DEFAULT))
    app.state.db = db

    def jlog(**kw):
        log.info(json.dumps(kw, ensure_ascii=False, default=str))

    @app.middleware("http")
    async def mw(request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        t0 = time.time()
        cl = request.headers.get("content-length")
        if cl and int(cl) > config.MAX_BODY_MB() * 1024 * 1024:
            return JSONResponse({"detail": "request too large"}, status_code=413)
        pid = request.headers.get("X-Passenger-Id", "")
        if pid:
            q = _hits[pid]
            now = time.time()
            while q and q[0] < now - 60:
                q.popleft()
            q.append(now)
            if len(q) > config.RATE_LIMIT_PER_MIN():
                return JSONResponse({"detail": "too many requests"}, status_code=429)
        resp = await call_next(request)
        resp.headers["X-Request-ID"] = rid
        jlog(event="request", request_id=rid, method=request.method, path=request.url.path, status=resp.status_code,
             ms=int((time.time() - t0) * 1000), passenger=pid or None)
        return resp

    def who(x_passenger_id):
        if not x_passenger_id:
            raise HTTPException(401, "X-Passenger-Id header is required")
        with LOCK:
            r = db.execute("SELECT passenger_id FROM passengers WHERE passenger_id=?", (x_passenger_id,)).fetchone()
        if not r:
            raise HTTPException(401, "unknown passenger")
        return x_passenger_id

    def session_lang(pid):
        r = db.execute("SELECT slots FROM sessions WHERE passenger_id=? ORDER BY updated_at DESC LIMIT 1", (pid,)).fetchone()
        if r:
            return json.loads(r[0] or "{}").get("lang", "en")
        return db.execute("SELECT preferred_language FROM passengers WHERE passenger_id=?", (pid,)).fetchone()[0] or "en"

    @app.get("/health")
    def health():
        with LOCK:
            n = db.execute("SELECT count(*) FROM documents").fetchone()[0]
            b = db.execute("SELECT count(*) FROM bookings").fetchone()[0]
        return {"status": "ok", "documents": n, "bookings": b, "llm": "off (MOCK_LLM)" if config.MOCK_LLM() else config.OLLAMA_MODEL(),
                "time": clock.iso(clock.real_now())}

    @app.post("/chat")
    def chat(body: ChatIn, x_passenger_id: str = Header(None)):
        pid = who(x_passenger_id)
        try:
            if body.as_of:
                clock.parse_dt(body.as_of)
        except Exception:
            raise HTTPException(422, "as_of must be an ISO date or datetime")
        with LOCK:
            return router.handle(db, pid, body.session_id, body.message, body.as_of)

    def _answer(pid, trace, answer_type, text, sources=None, tools=None, pending=None, handed=False):
        return {"trace_id": trace, "answer_type": answer_type, "answer": text, "sources": sources or [], "tools": tools or [],
                "pending_action": pending, "handed_to_human": handed}

    def _audit_action(pid, trace, aid, what, result):
        rec = {"trace_id": trace, "ts": clock.iso(clock.real_now()), "passenger_id": pid, "session_id": "", "input": "[%s %s]" % (what, aid),
               "steps": [{"step": what, "action_id": aid, "result": result}], "answer_type": result.get("answer_type", ""), "tools": []}
        db.execute("INSERT OR REPLACE INTO audit VALUES(?,?,?,?,?)", (trace, clock.iso(clock.real_now()), pid, "", json.dumps(rec, default=str)))
        db.commit()

    @app.post("/actions/{action_id}/confirm")
    def confirm(action_id: str, x_passenger_id: str = Header(None)):
        pid = who(x_passenger_id)
        trace = "TR-" + uuid.uuid4().hex[:12].upper()
        with LOCK:
            lang = session_lang(pid)
            r = am.confirm_action(db, action_id, pid, trace)
            if r["ok"]:
                kind = r.get("action_type")
                res = r.get("result") or {}
                if r.get("already"):
                    out = _answer(pid, trace, "action_done", t("already_done", lang), tools=[{"tool": "confirm_action", "output": r}])
                elif kind == "cancel_booking":
                    txt = t("done_cancel", lang, bid=res["booking_id"], n=len(res["cancelled_traveller_ids"]), refund=inr(res["refund"]),
                            status=res["new_status"])
                    out = _answer(pid, trace, "action_done", txt, sources=[{"doc_id": "RULE-03", "section": "Section 1"}], tools=[{"tool": "confirm_action", "output": r}])
                elif kind == "change_boarding":
                    from tools import timetable as tt
                    txt = t("done_change", lang, bid=res["booking_id"], new=tt.station_name(db, res["new_code"]), old=tt.station_name(db, res["old_code"]))
                    out = _answer(pid, trace, "action_done", txt, sources=[{"doc_id": "RULE-07", "section": "Section 1"}], tools=[{"tool": "confirm_action", "output": r}])
                else:
                    txt = t("done_book", lang, bid=res["booking_id"], status=res["status"], total=inr(res["total"]))
                    out = _answer(pid, trace, "action_done", txt, sources=[{"doc_id": "RULE-01", "section": "Section 1"}], tools=[{"tool": "confirm_action", "output": r}])
            else:
                reason = r["reason"]
                if reason == "not_found":
                    out = _answer(pid, trace, "not_found", t("action_gone", lang))
                elif reason == "expired":
                    out = _answer(pid, trace, "refusal", t("expired", lang), tools=[{"tool": "confirm_action", "output": r}])
                elif reason == "quote_changed":
                    a = am.get_action(db, action_id, pid)
                    p = am.propose_cancel(db, pid, a["booking_id"], clock.real_now() + __import__("datetime").timedelta(seconds=a["clock_offset"]),
                                          traveller_ids=a["payload"].get("traveller_ids"), trace_id=trace)
                    txt = t("quote_changed", lang, old=inr(r["old"]), new=inr(r["new"]))
                    out = _answer(pid, trace, "confirm_needed", txt, tools=[{"tool": "confirm_action", "output": r}],
                                  pending=p.get("pending_action") if p.get("ok") else None)
                elif reason in ("cancelled", "failed"):
                    out = _answer(pid, trace, "refusal", t("action_failed", lang, why=reason), tools=[{"tool": "confirm_action", "output": r}])
                else:
                    out = _answer(pid, trace, "refusal", t("action_failed", lang, why=reason), tools=[{"tool": "confirm_action", "output": r}])
            _audit_action(pid, trace, action_id, "confirm", out)
            return out

    @app.post("/actions/{action_id}/cancel")
    def cancel(action_id: str, x_passenger_id: str = Header(None)):
        pid = who(x_passenger_id)
        trace = "TR-" + uuid.uuid4().hex[:12].upper()
        with LOCK:
            lang = session_lang(pid)
            r = am.cancel_action(db, action_id, pid)
            out = _answer(pid, trace, "answer" if r["ok"] else "not_found", t("action_cancelled", lang) if r["ok"] else t("action_gone", lang),
                          tools=[{"tool": "cancel_action", "output": r}])
            _audit_action(pid, trace, action_id, "cancel", out)
            return out

    @app.get("/bookings")
    def list_my_bookings(x_passenger_id: str = Header(None)):
        pid = who(x_passenger_id)
        with LOCK:
            out = []
            for b in bk.list_bookings(db, pid):
                tr = db.execute("SELECT name FROM trains WHERE train_no=?", (b["train_no"],)).fetchone()
                b["train_name"] = tr["name"] if tr else ""
                b["travellers"] = bk.travellers(db, b["booking_id"])
                out.append(b)
            return out

    @app.get("/bookings/{booking_id}")
    def get_booking(booking_id: str, x_passenger_id: str = Header(None)):
        pid = who(x_passenger_id)
        with LOCK:
            b = bk.booking_view(db, booking_id, pid)
            if not b:
                raise HTTPException(404, "booking not found")
            p = db.execute("SELECT name, phone_last4 FROM passengers WHERE passenger_id=?", (pid,)).fetchone()
            b["passenger"] = {"name": p["name"], "phone": bk.mask_phone(p["phone_last4"])}
            return b

    @app.post("/ingest")
    def ingest(body: IngestIn, x_passenger_id: str = Header(None), x_admin_key: str = Header(None)):
        if config.PROTECT_ADMIN() and x_admin_key != config.ADMIN_KEY():
            raise HTTPException(403, "admin key required")
        if not config.PROTECT_ADMIN():
            pass
        d = body.model_dump()
        ov = [s for s in (d.pop("settings") or [])] or None
        with LOCK:
            try:
                return ing.ingest(db, d, ov)
            except Exception as e:
                raise HTTPException(422, "could not ingest: %s" % e)

    @app.get("/trace/{trace_id}")
    def trace(trace_id: str, x_passenger_id: str = Header(None)):
        pid = who(x_passenger_id)
        with LOCK:
            r = db.execute("SELECT record, passenger_id FROM audit WHERE trace_id=?", (trace_id,)).fetchone()
        if not r or r["passenger_id"] != pid:
            raise HTTPException(404, "trace not found")
        return json.loads(r["record"])

    @app.get("/demo/passengers")
    def demo_passengers():
        if os.getenv("DEMO", "true").lower() not in ("1", "true", "yes"):
            raise HTTPException(404, "not found")
        with LOCK:
            return [dict(r) for r in db.execute("SELECT passenger_id, name, preferred_language FROM passengers ORDER BY passenger_id")]

    @app.post("/admin/reset_demo")
    def reset(x_admin_key: str = Header(None)):
        if config.PROTECT_ADMIN() and x_admin_key != config.ADMIN_KEY():
            raise HTTPException(403, "admin key required")
        with LOCK:
            seed.seed(db, anchor=os.getenv("DATA_ANCHOR", seed.ANCHOR_DEFAULT))
        return {"status": "reset"}

    static = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    if os.path.isdir(static):                       # the React build is served by the API itself: one URL, no CORS
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=static, html=True), name="ui")

    return app


app = make_app() if os.getenv("TRAIN_NO_AUTOAPP") != "1" else None
