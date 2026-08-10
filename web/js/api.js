/* The-Mailroom API client: Langfuse-backed fetch endpoints + WebSocket
 * with reconnect. All display data flows through this module; nothing is
 * fabricated client-side. */

const Mailroom = (() => {
  const api = {
    health: () => get("/api/health"),
    meta: () => get("/api/meta"),
    traces: (since = 1800, limit = 200) => get(`/api/traces?since=${since}&limit=${limit}`),
    run: (id) => get(`/api/traces/${encodeURIComponent(id)}`),
    metrics: (since = 3600) => get(`/api/metrics?since=${since}`),
    sessions: (limit = 50) => get(`/api/sessions?limit=${limit}`),
    reviewQueue: (since = 604800) => get(`/api/review-queue?since=${since}`),
  };

  async function get(path) {
    const res = await fetch(path, { headers: { "Accept": "application/json" } });
    if (!res.ok) throw new Error(`HTTP ${res.status} ${path}`);
    return res.json();
  }

  const fmt = {
    cost: (v) => (v == null ? "—" : `$${Number(v).toFixed(2)}`),
    tokens: (v) => (v == null ? "—" : Number(v).toLocaleString("en-US")),
    latency: (v) => {
      if (v == null) return "—";
      const s = Number(v);
      if (s < 60) return `${s.toFixed(1)}s`;
      return `${Math.floor(s / 60)}m ${(s % 60).toFixed(0)}s`;
    },
    conf: (v) => (v == null ? "—" : `${(Number(v) * 100).toFixed(0)}%`),
    time: (iso) => {
      if (!iso) return "—";
      const d = new Date(iso);
      return isNaN(d) ? "—" : d.toLocaleTimeString("en-US", { hour12: false });
    },
    dateTime: (iso) => {
      if (!iso) return "—";
      const d = new Date(iso);
      return isNaN(d) ? "—" : d.toLocaleString("en-US", { month: "short", day: "2-digit", hour12: false });
    },
    short: (s, n = 26) => {
      if (s == null) return "—";
      s = String(s);
      return s.length > n ? `${s.slice(0, n - 1)}…` : s;
    },
  };

  const esc = (s) => {
    if (s == null) return "";
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  };

  let ws = null;
  let wsTimer = null;
  let wsRetry = 0;
  let connected = false;

  function wsURL() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${location.host}/ws`;
  }

  function connectWS(onMessage) {
    clearTimeout(wsTimer);
    try {
      if (ws) ws.close();
    } catch (e) { /* noop */ }
    ws = new WebSocket(wsURL());
    ws.onopen = () => {
      wsRetry = 0;
      connected = true;
      onMessage({ type: "status", connected: true });
    };
    ws.onmessage = (ev) => {
      try {
        onMessage(JSON.parse(ev.data));
      } catch (e) { /* non-JSON frame ignored */ }
    };
    ws.onclose = () => {
      connected = false;
      onMessage({ type: "status", connected: false });
      const delay = Math.min(30000, 1000 * 2 ** wsRetry++);
      wsTimer = setTimeout(() => connectWS(onMessage), delay);
    };
    ws.onerror = () => {
      try { ws.close(); } catch (e) { /* noop */ }
    };
  }

  function envFromTags(tags) {
    if (!Array.isArray(tags)) return null;
    const known = new Set(["live", "pilot", "dev", "test", "demo", "prod", "staging"]);
    for (const t of tags) if (known.has(t)) return t;
    return null;
  }

  return { api, fmt, esc, connectWS, envFromTags, get wsConnected() { return connected; } };
})();
