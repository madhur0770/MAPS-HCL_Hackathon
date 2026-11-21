"""Replay ANY csv of questions against the assistant and write a results csv. For a judge's file that has plain messages (no fixture selectors).

  python scripts/replay_csv.py cases.csv                         # in-process on fresh demo data (no server needed)
  python scripts/replay_csv.py cases.csv --url http://localhost:8000   # against the running app (docker or run_local)

Columns (only `message` is required; names are case-insensitive, `question`/`input`/`prompt` also work for message):
  message | passenger_id (default P001) | session_id (rows with the same id are one conversation, in file order) | as_of (ISO time, default 2026-11-21T10:00+05:30)
  expected_answer_type (answer, clarification, confirm_needed, refusal, not_found, handed_to_human, action_done)
  expected_contains (text that must appear; several separated by ' | ')  |  expected_not_contains (text that must NOT appear)
Writes <name>_results.csv next to the input: answer, answer_type, sources, trace_id, handed_to_human, pending action id, latency, PASS/FAIL (or n/a when nothing was expected).
Exit code 1 when any row with expectations fails."""
import csv
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.progress import Progress

AS_OF = "2026-11-21T10:00:00+05:30"


def pick(row, *names, default=""):
    low = {k.lower().strip(): v for k, v in row.items() if k}
    for n in names:
        if low.get(n) not in (None, ""):
            return low[n].strip()
    return default


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(2)
    url = None
    if "--url" in sys.argv:
        url = sys.argv[sys.argv.index("--url") + 1]
        args = [a for a in args if a != url]
    path = args[0]
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if url:
        import requests

        def post(pid, sid, msg, as_of):
            r = requests.post(url.rstrip("/") + "/chat", json={"session_id": sid, "message": msg, "as_of": as_of}, headers={"X-Passenger-Id": pid}, timeout=60)
            return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {})
    else:
        os.environ.setdefault("MOCK_LLM", "true")
        os.environ["TRAIN_NO_AUTOAPP"] = "1"
        os.environ["DEMO_NOW"] = AS_OF
        os.environ["RATE_LIMIT_PER_MIN"] = "10000000"
        import logging
        logging.disable(logging.CRITICAL)
        from fastapi.testclient import TestClient
        from core import db as dbm, seed
        from app.main import make_app
        d = dbm.connect(":memory:")
        seed.seed(d)
        cl = TestClient(make_app(d))

        def post(pid, sid, msg, as_of):
            r = cl.post("/chat", json={"session_id": sid, "message": msg, "as_of": as_of}, headers={"X-Passenger-Id": pid})
            return r.status_code, r.json()
    out, bad, checked = [], 0, 0
    p = Progress(len(rows), "replay")
    for i, row in enumerate(rows, 1):
        msg = pick(row, "message", "question", "input", "prompt", "query")
        pid = pick(row, "passenger_id", "passenger", "customer_id", default="P001")
        sid = pick(row, "session_id", "conversation_id", default="row%d" % i)
        as_of = pick(row, "as_of", default=AS_OF)
        t0 = time.time()
        try:
            code, r = post(pid, sid, msg, as_of)
        except Exception as e:
            code, r = 0, {"answer": "request failed: %r" % e, "answer_type": "error"}
        ms = int((time.time() - t0) * 1000)
        ans = r.get("answer", "") if isinstance(r, dict) else ""
        typ = r.get("answer_type", "http_%d" % code)
        exp_t = pick(row, "expected_answer_type", "expected_type")
        inc = [x.strip() for x in pick(row, "expected_contains").split("|") if x.strip()]
        exc = [x.strip() for x in pick(row, "expected_not_contains").split("|") if x.strip()]
        res, why = "n/a", []
        if exp_t or inc or exc:
            checked += 1
            if exp_t and typ != exp_t:
                why.append("type %s != %s" % (typ, exp_t))
            why += ["missing '%s'" % x for x in inc if x.lower() not in ans.lower()]
            why += ["contains '%s'" % x for x in exc if x.lower() in ans.lower()]
            res = "FAIL" if why else "PASS"
            bad += bool(why)
        pa = (r.get("pending_action") or {}).get("action_id", "") if isinstance(r, dict) else ""
        out.append(dict(row, answer=ans, answer_type=typ, http_status=code, sources="; ".join("%s %s" % (s["doc_id"], s["section"]) for s in r.get("sources", [])) if isinstance(r, dict) else "",
                        trace_id=r.get("trace_id", "") if isinstance(r, dict) else "", handed_to_human=r.get("handed_to_human", "") if isinstance(r, dict) else "", pending_action_id=pa,
                        latency_ms=ms, result=res, why="; ".join(why)))
        p.step(1, "%s %s" % (res, msg[:40]))
    p.finish("%d rows" % len(rows))
    dest = os.path.splitext(path)[0] + "_results.csv"
    cols = list(out[0].keys()) if out else []
    with open(dest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out)
    lat = sorted(o["latency_ms"] for o in out)
    print("rows %d | with expectations %d | pass %d | fail %d | p50 %d ms | p95 %d ms" % (len(out), checked, checked - bad, bad, lat[len(lat) // 2] if lat else 0, lat[int(len(lat) * .95) - 1] if lat else 0))
    print("results written to", dest)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
