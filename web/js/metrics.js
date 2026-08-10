/* The-Mailroom metrics view: aggregation tiles from /api/metrics. */

const MetricsView = (() => {
  const gridEl = document.getElementById("metrics-grid");

  function tile(label, value, cls = "") {
    return `<div class="tile">
      <div class="tile-value ${cls}">${value}</div>
      <div class="tile-label">${label}</div>
    </div>`;
  }

  function bars(title, entries, color) {
    const max = Math.max(1, ...entries.map((e) => e.value));
    const rows = entries
      .map((e) => `<div class="bar-row">
        <span class="bar-label">${Mailroom.esc(e.label)}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${Math.round((e.value / max) * 100)}%;background:${color}"></span></span>
        <span class="bar-num">${e.value}</span>
      </div>`)
      .join("");
    return `<div class="tile wide">
      <div class="tile-label" style="margin:0 0 8px">${title}</div>
      ${rows}
    </div>`;
  }

  function render(m) {
    const verdictMix = (m.verdict_counts || {});
    const vColors = { CORRECT: "#5f9e6e", PARTIAL: "#f7d156", MISS: "#e26863" };
    const vBars = Object.entries(verdictMix)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => ({ label: k, value: v, color: vColors[k] || "#7d97b5" }));

    const docBars = Object.entries(m.per_doc_type || {})
      .map(([k, v]) => ({
        label: ((Mailroom.meta && Mailroom.meta.doc_classes) || {})[k] || k,
        value: v,
        color: "#d9a866",
      }));

    const quality = m.avg_quality == null ? "—" : Number(m.avg_quality).toFixed(2);
    const qcls = m.avg_quality != null ? (m.avg_quality >= 0.8 ? "good" : "warn") : "";

    let html = "";
    html += tile("TOTAL DOCS", m.total_docs ?? "—");
    html += tile("ARCHIVED", m.archived ?? "—", "good");
    html += tile("REVIEW", m.review ?? "—", "warn");
    html += tile("FAILED", m.failed ?? "—", m.failed ? "bad" : "");
    html += tile("IN FLIGHT", m.in_flight ?? "—");
    html += tile("LLM CALLS", Mailroom.fmt.tokens(m.llm_calls));
    html += tile("TOTAL COST", Mailroom.fmt.cost(m.total_cost_usd));
    html += tile("TOTAL TOKENS", Mailroom.fmt.tokens(m.total_tokens));
    html += tile("AVG COST / DOC", Mailroom.fmt.cost(m.avg_cost_usd));
    html += tile("AVG LATENCY", Mailroom.fmt.latency(m.avg_latency_s));
    html += tile("P95 GEN LATENCY", Mailroom.fmt.latency(m.p95_generation_latency_s));
    html += tile("AVG QUALITY", quality, qcls);
    if (vBars.length) html += bars("JUDGE VERDICTS", vBars, "#5f9e6e");
    if (docBars.length) html += bars("DOC TYPES", docBars, "#d9a866");
    gridEl.innerHTML = html || `<div class="hint mono">NO METRICS YET</div>`;
  }

  async function refresh(since = 3600) {
    try {
      const data = await Mailroom.api.metrics(since);
      render(data);
      return data;
    } catch (err) {
      gridEl.innerHTML = `<div class="insp-error">metrics unavailable — ${Mailroom.esc(err.message || String(err))}</div>`;
      throw err;
    }
  }

  return { refresh };
})();
