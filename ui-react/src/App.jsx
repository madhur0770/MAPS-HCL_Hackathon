import React, { useEffect, useRef, useState, useCallback } from "react";
import { api } from "./api.js";

const SAMPLES = [
  "trains from Anandpur Central to Udayabad on 26 Nov",
  "trains from Anandpur to Chetakgarh tomorrow",
  "how much will I get back if I cancel BKG0001?",
  "cancel booking BKG0001",
  "change boarding station of BKG0001 to Suryanagar",
  "mera BKG0001 cancel kar do",
  "BKG0001 रद्द करने पर कितना पैसा वापस मिलेगा",
  "what is the cancellation charge for AC2",
  "what is the Tatkal supplement for AC3",
  "I was charged twice for BKG0001",
  "book Anandpur North to Chetakgarh 22 Nov AC2 for Neha 31 and Ravi 40",
];
const TYPE_LABEL = {
  answer: "Answer", clarification: "Need more info", confirm_needed: "Waiting for your confirm", action_done: "Done",
  handed_to_human: "Passed to a human desk", not_found: "Not found", refusal: "Can't do that",
};
const STATUS_CLASS = { CNF: "ok", RAC: "warn", WL: "bad", CAN: "mute" };
const BK_CLASS = { confirmed: "ok", rac: "warn", waitlisted: "bad", cancelled: "mute", train_cancelled: "mute" };

function fmtDate(s) {
  const d = new Date(s + "T00:00:00");
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

function Sources({ sources }) {
  if (!sources?.length) return null;
  return (
    <div className="chips">
      {sources.map((s, i) => (
        <span className="chip src" key={i} title="document and section used">📄 {s.doc_id} · {s.section}</span>
      ))}
    </div>
  );
}

function Details({ reply, pid }) {
  const [open, setOpen] = useState(false);
  const [trace, setTrace] = useState(null);
  const loadTrace = async () => {
    const r = await api.trace(pid, reply.trace_id);
    setTrace(r.ok ? r.data : { error: r.data.detail || "not available" });
  };
  return (
    <div className="details">
      <button className="link" onClick={() => setOpen(!open)}>{open ? "Hide" : "How I got this"} ▾</button>
      {open && (
        <div className="detailsBody">
          <div className="muted">trace id: <code>{reply.trace_id}</code></div>
          {reply.tools?.map((t, i) => (
            <details key={i}><summary><b>{t.tool}</b></summary><pre>{JSON.stringify(t.output, null, 2)}</pre></details>
          ))}
          {!trace && <button className="link" onClick={loadTrace}>Show full audit record</button>}
          {trace && <details open><summary><b>audit record</b></summary><pre>{JSON.stringify(trace, null, 2)}</pre></details>}
        </div>
      )}
    </div>
  );
}

function Message({ m, pid, onConfirm, onCancel, busy }) {
  const r = m.reply;
  return (
    <div className={"msg " + m.role}>
      <div className="avatar">{m.role === "user" ? "🧑" : "🚆"}</div>
      <div className="bubble">
        {r && <div className={"badge t_" + r.answer_type}>{TYPE_LABEL[r.answer_type] || r.answer_type}{r.handed_to_human ? " 🧑‍💼" : ""}</div>}
        <div className="text">{m.content}</div>
        {r?.pending_action && m.open && (
          <div className="actions">
            <button className="btn primary" disabled={busy} onClick={() => onConfirm(m, r.pending_action)}>✅ Confirm</button>
            <button className="btn" disabled={busy} onClick={() => onCancel(m, r.pending_action)}>✖ Cancel</button>
            <span className="muted">expires {new Date(r.pending_action.expires_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</span>
          </div>
        )}
        {r && <Sources sources={r.sources} />}
        {r && <Details reply={r} pid={pid} />}
      </div>
    </div>
  );
}

function Bookings({ items, onAsk }) {
  if (!items) return <div className="muted">Loading…</div>;
  if (!items.length) return <div className="muted">No bookings.</div>;
  return (
    <div className="bkList">
      {[...items].sort((a, b) => (b.booked_at || "").localeCompare(a.booked_at || "")).map((b) => (
        <div className="bk" key={b.booking_id}>
          <div className="bkTop">
            <b>{b.booking_id}</b>
            <span className={"pill " + (BK_CLASS[b.status] || "")}>{b.status.replace("_", " ")}</span>
          </div>
          <div>{b.train_no} {b.train_name}</div>
          <div className="muted">{b.from_code} → {b.to_code} · {fmtDate(b.journey_date)} · {b.class} · ₹{(b.amount_paid / 100).toLocaleString('en-IN', {minimumFractionDigits: (b.amount_paid % 100) ? 2 : 0})}</div>
          <div className="trav">
            {b.travellers.map((t) => (
              <span key={t.traveller_id} className={"pill " + (STATUS_CLASS[t.status] || "")} title={t.traveller_name}>{t.traveller_name.split(" ")[0]} {t.status}</span>
            ))}
          </div>
          <div className="bkBtns">
            <button className="link" onClick={() => onAsk(`status of ${b.booking_id}`)}>Status</button>
            <button className="link" onClick={() => onAsk(`how much refund if I cancel ${b.booking_id}`)}>Refund?</button>
            <button className="link" onClick={() => onAsk(`cancel booking ${b.booking_id}`)}>Cancel</button>
          </div>
        </div>
      ))}
    </div>
  );
}

function IngestPanel({ onDone }) {
  const [text, setText] = useState("Section 3.1: From 1 January 2027 the fixed cancellation charge for SL is Rs 150 per traveller.");
  const [id, setId] = useState("CIR-099");
  const [eff, setEff] = useState("2027-01-01");
  const [topic, setTopic] = useState("refund");
  const [sup, setSup] = useState("RUL-003");
  const [out, setOut] = useState(null);
  const send = async () => {
    const r = await api.ingest({ doc_id: id, title: "Circular " + id, doc_type: "circular", effective_from: eff, topic, supersedes: sup, text });
    setOut(r.ok ? r.data : { error: r.data.detail });
    onDone?.();
  };
  return (
    <div className="ingest">
      <div className="muted">Add a circular while the app is running. Answers change at once, no restart.</div>
      <div className="row"><input value={id} onChange={(e) => setId(e.target.value)} placeholder="doc id" /><input type="date" value={eff} onChange={(e) => setEff(e.target.value)} /></div>
      <div className="row"><input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="topic" /><input value={sup} onChange={(e) => setSup(e.target.value)} placeholder="replaces (doc id)" /></div>
      <textarea rows={4} value={text} onChange={(e) => setText(e.target.value)} />
      <button className="btn primary" onClick={send}>Add document</button>
      {out && <pre>{JSON.stringify(out, null, 2)}</pre>}
    </div>
  );
}

export default function App() {
  const [people, setPeople] = useState([]);
  const [pid, setPid] = useState("P001");
  const [health, setHealth] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [input, setInput] = useState("");
  const [asOf, setAsOf] = useState("");
  const [busy, setBusy] = useState(false);
  const [bookings, setBookings] = useState(null);
  const [tab, setTab] = useState("bookings");
  const [sid, setSid] = useState(() => Math.random().toString(36).slice(2, 10));
  const endRef = useRef(null);

  const refreshBookings = useCallback(async () => {
    const r = await api.bookings(pid);
    setBookings(r.ok ? r.data : []);
  }, [pid]);

  useEffect(() => { api.passengers().then((r) => r.ok && setPeople(r.data)); api.health().then((r) => setHealth(r.ok ? r.data : null)); }, []);
  useEffect(() => { setMsgs([]); setBookings(null); setSid(Math.random().toString(36).slice(2, 10)); refreshBookings(); }, [pid, refreshBookings]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const push = (m) => setMsgs((x) => [...x, m]);

  const send = async (text) => {
    const t = (text ?? input).trim();
    if (!t || busy) return;
    setInput("");
    push({ role: "user", content: t });
    setBusy(true);
    const r = await api.chat(pid, sid, t, asOf.trim());
    setBusy(false);
    if (!r.ok) {
      push({ role: "assistant", content: `Error ${r.status}: ${r.data.detail || "something went wrong"}`, reply: { answer_type: "refusal", sources: [], tools: [], trace_id: "-" } });
      return;
    }
    push({ role: "assistant", content: r.data.answer, reply: r.data, open: !!r.data.pending_action });
    refreshBookings();
  };

  const closeOpen = (m) => setMsgs((x) => x.map((y) => (y === m ? { ...y, open: false } : y)));
  const act = async (m, pa, kind) => {
    setBusy(true);
    const r = kind === "confirm" ? await api.confirm(pid, pa.action_id) : await api.cancel(pid, pa.action_id);
    setBusy(false);
    closeOpen(m);
    const d = r.ok ? r.data : { answer: `Error ${r.status}`, answer_type: "refusal", sources: [], tools: [], trace_id: "-" };
    push({ role: "assistant", content: d.answer, reply: d, open: !!d.pending_action });
    refreshBookings();
  };

  const reset = async () => { await api.reset(); setMsgs([]); setSid(Math.random().toString(36).slice(2, 10)); refreshBookings(); };
  const me = people.find((p) => p.passenger_id === pid);

  return (
    <div className="app">
      <header>
        <div className="brand">🚆 Ujjwal Rail Assistant</div>
        <div className="grow" />
        <label className="field">Signed in as
          <select value={pid} onChange={(e) => setPid(e.target.value)}>
            {(people.length ? people : [{ passenger_id: "P001", name: "Aarav", preferred_language: "en" }]).map((p) => (
              <option key={p.passenger_id} value={p.passenger_id}>{p.passenger_id} · {p.name} ({p.preferred_language})</option>
            ))}
          </select>
        </label>
        <label className="field">Pretend it is
          <input placeholder="2026-11-22T18:01" value={asOf} onChange={(e) => setAsOf(e.target.value)} />
        </label>
        <button className="btn" onClick={reset}>Reset demo</button>
        <span className={"dot " + (health ? "up" : "down")} title={health ? `${health.documents} docs · ${health.bookings} bookings · model: ${health.llm}` : "API not reachable"} />
      </header>

      <main>
        <section className="chat">
          <div className="scroll">
            {!msgs.length && (
              <div className="welcome">
                <h2>Hello{me ? `, ${me.name.split(" ")[0]}` : ""} 👋</h2>
                <p>Ask in English, Hindi or Hinglish. I can only see <b>your own</b> bookings. Changes always show a preview first and need your Confirm.</p>
                <div className="samples">{SAMPLES.map((s) => <button key={s} className="sample" onClick={() => send(s)}>{s}</button>)}</div>
              </div>
            )}
            {msgs.map((m, i) => <Message key={i} m={m} pid={pid} busy={busy} onConfirm={(mm, pa) => act(mm, pa, "confirm")} onCancel={(mm, pa) => act(mm, pa, "cancel")} />)}
            {busy && <div className="msg assistant"><div className="avatar">🚆</div><div className="bubble typing"><span /><span /><span /></div></div>}
            <div ref={endRef} />
          </div>
          <form className="composer" onSubmit={(e) => { e.preventDefault(); send(); }}>
            <input autoFocus value={input} onChange={(e) => setInput(e.target.value)} placeholder="Type your question…  (e.g. cancel booking BKG0001)" />
            <button className="btn primary" disabled={busy || !input.trim()}>Send</button>
          </form>
        </section>

        <aside>
          <div className="tabs">
            <button className={tab === "bookings" ? "on" : ""} onClick={() => setTab("bookings")}>My bookings</button>
            <button className={tab === "docs" ? "on" : ""} onClick={() => setTab("docs")}>Add circular</button>
          </div>
          {tab === "bookings" ? <Bookings items={bookings} onAsk={send} /> : <IngestPanel onDone={() => api.health().then((r) => r.ok && setHealth(r.data))} />}
        </aside>
      </main>
    </div>
  );
}
