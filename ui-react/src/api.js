// Thin wrapper around the API. Identity is ONLY the X-Passenger-Id header.
async function call(method, path, pid, body, extra = {}) {
  try {
    const r = await fetch(path, {
      method,
      headers: { "Content-Type": "application/json", ...(pid ? { "X-Passenger-Id": pid } : {}), ...extra },
      body: body ? JSON.stringify(body) : undefined,
    });
    let data = null;
    try { data = await r.json(); } catch { data = {}; }
    return { ok: r.ok, status: r.status, data };
  } catch (e) {
    return { ok: false, status: 0, data: { detail: String(e) } };
  }
}
export const api = {
  health: () => call("GET", "/health"),
  passengers: () => call("GET", "/demo/passengers"),
  chat: (pid, session_id, message, as_of) => call("POST", "/chat", pid, { session_id, message, ...(as_of ? { as_of } : {}) }),
  confirm: (pid, id) => call("POST", `/actions/${id}/confirm`, pid),
  cancel: (pid, id) => call("POST", `/actions/${id}/cancel`, pid),
  bookings: (pid) => call("GET", "/bookings", pid),
  trace: (pid, id) => call("GET", `/trace/${id}`, pid),
  ingest: (doc) => call("POST", "/ingest", null, doc),
  reset: () => call("POST", "/admin/reset_demo"),
};
