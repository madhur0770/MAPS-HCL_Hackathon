"""Chat screen. Pick a passenger, type in English / Hindi / Hinglish. Confirm and Cancel are real buttons (a separate API call)."""
import json
import os
import uuid

import requests
import streamlit as st

API = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="Ujjwal Rail Assistant", page_icon="🚆", layout="wide")


def api(method, path, pid, **kw):
    try:
        r = requests.request(method, API + path, headers={"X-Passenger-Id": pid}, timeout=60, **kw)
        return r.status_code, (r.json() if r.content else {})
    except Exception as e:
        return 0, {"detail": str(e)}


st.title("🚆 Ujjwal Rail Travel Assistant")
with st.sidebar:
    st.header("Signed in as")
    try:
        people = requests.get(API + "/demo/passengers", timeout=10).json()
    except Exception:
        people = []
    labels = {"%s - %s (%s)" % (p["passenger_id"], p["name"], p["preferred_language"]): p["passenger_id"] for p in people}
    pick = st.selectbox("Passenger (demo)", list(labels) or ["P001"])
    pid = labels.get(pick, "P001")
    as_of = st.text_input("Pretend it is (optional, ISO time)", "", help="Time travel for demos, e.g. 2026-11-22T18:01")
    if st.button("Reset demo data"):
        requests.post(API + "/admin/reset_demo", timeout=30)
        st.session_state.clear()
        st.rerun()
    try:
        h = requests.get(API + "/health", timeout=5).json()
        st.caption("API ok · %d documents · %d bookings · model: %s" % (h["documents"], h["bookings"], h["llm"]))
    except Exception:
        st.error("API not reachable at %s" % API)
    st.markdown("**Try:** `trains from Anandpur Central to Udayabad on 26 Nov` · `cancel booking BKG0001` · `mera BKG0001 cancel kar do` · `BKG0001 cancel karne par kitna paisa wapas milega`")

if "sid" not in st.session_state:
    st.session_state.sid = uuid.uuid4().hex[:8]
    st.session_state.msgs = []
if st.session_state.get("pid") != pid:
    st.session_state.pid, st.session_state.msgs, st.session_state.sid = pid, [], uuid.uuid4().hex[:8]


def show(m, i):
    with st.chat_message(m["role"]):
        st.write(m["content"])
        r = m.get("reply")
        if not r:
            return
        cols = st.columns([1, 1, 4])
        pa = r.get("pending_action")
        if pa and m.get("open"):
            if cols[0].button("✅ Confirm", key="c%d" % i):
                code, out = api("POST", "/actions/%s/confirm" % pa["action_id"], pid)
                m["open"] = False
                st.session_state.msgs.append({"role": "assistant", "content": out.get("answer", str(out)), "reply": out})
                st.rerun()
            if cols[1].button("✖ Cancel", key="x%d" % i):
                code, out = api("POST", "/actions/%s/cancel" % pa["action_id"], pid)
                m["open"] = False
                st.session_state.msgs.append({"role": "assistant", "content": out.get("answer", str(out)), "reply": out})
                st.rerun()
        with st.expander("How I got this  ·  type: %s%s" % (r.get("answer_type"), " · handed to human" if r.get("handed_to_human") else "")):
            if r.get("sources"):
                st.write("**Sources:** " + ", ".join("%s (%s)" % (s["doc_id"], s["section"]) for s in r["sources"]))
            for tl in r.get("tools", []):
                st.code("%s\n%s" % (tl["tool"], json.dumps(tl.get("output"), ensure_ascii=False, indent=1, default=str)[:1500]), language="json")
            st.caption("trace id: %s" % r.get("trace_id"))
            if st.button("Show full audit record", key="t%d" % i):
                code, tr = api("GET", "/trace/%s" % r["trace_id"], pid)
                st.json(tr)


for i, m in enumerate(st.session_state.msgs):
    show(m, i)

prompt = st.chat_input("Ask in English, Hindi or Hinglish…")
if prompt:
    st.session_state.msgs.append({"role": "user", "content": prompt})
    body = {"session_id": st.session_state.sid, "message": prompt}
    if as_of.strip():
        body["as_of"] = as_of.strip()
    code, out = api("POST", "/chat", pid, json=body)
    if code != 200:
        out = {"answer": "Error %s: %s" % (code, out.get("detail", out)), "answer_type": "error", "sources": [], "tools": []}
    st.session_state.msgs.append({"role": "assistant", "content": out.get("answer", ""), "reply": out, "open": bool(out.get("pending_action"))})
    st.rerun()
