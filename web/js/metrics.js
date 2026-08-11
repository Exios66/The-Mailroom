/* The-Mailroom metrics view: aggregation tiles.
 * Works with /api/metrics in live mode, or computes from local data in demo mode. */

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

  function computeLocalMetrics(runs) {
    const m = {
      total_docs: 0,
      archived: 0,
      review: 0,
      failed: 0,
      in_flight: 0,
      total_cost_usd: 0,
      total_tokens: 0,
      llm_calls: 0,
      avg_cost_usd: 0,
      avg_latency_s: 0,
      p95_generation_latency_s: null,
      verdict_counts: {},
      per_doc_type: {},
      avg_quality: null,
    };
    const latencies = [];
    const qualities = [];
    for (const r of runs) {
      m.total_docs++;
      if (r.stage === "archived") m.archived++;
      else if (r.stage === "review" || r.needs_human) m.review++;
      else if (r.stage === "failed") m.failed++;
      else m.in_flight++;
      m.total_cost_usd += r.cost_usd || 0;
      m.total_tokens += r.total_tokens || 0;
      m.llm_calls += r.llm_call_count || 0;
      if (r.latency != null) latencies.push(r.latency);
      if (r.verdict) {
        m.verdict_counts[r.verdict] = (m.verdict_counts[r.verdict] || 0) + 1;
      }
      if (r.quality != null) qualities.push(r.quality);
      if (r.doc_type) {
        m.per_doc_type[r.doc_type] = (m.per_doc_type[r.doc_type] || 0) + 1;
      }
    }
    if (m.total_docs > 0) m.avg_cost_usd = m.total_cost_usd / m.total_docs;
    if (latencies.length > 0) {
      m.avg_latency_s = latencies.reduce((a, b) => a + b, 0) / latencies.length;
    }
    if (qualities.length > 0) {
      m.avg_quality = qualities.reduce((a, b) => a + b, 0) / qualities.length;
    }
    return m;
  }

  function trendBars(runs) {
    if (!runs || !runs.length) return "";
    // Bucket by hour over the last 6 hours
    const now = Date.now();
    const buckets = new Array(6).fill(0);
    const costBuckets = new Array(6).fill(0);
    const labels = [];
    for (let i = 5; i >= 0; i--) {
      const h = new Date(now - i * 3600000);
      labels.push(`${String(h.getHours()).padStart(2,"0")}:00`);
    }
    for (const r of runs) {
      const ts = r.updated_at || r.created_at;
      if (!ts) continue;
      const age = (now - new Date(ts).getTime()) / 3600000;
      const bucket = Math.floor(5 - age);
      if (bucket >= 0 && bucket < 6) {
        buckets[bucket]++;
        costBuckets[bucket] += r.cost_usd || 0;
      }
    }
    const maxCount = Math.max(1, ...buckets);
    return `<div class="tile wide">
      <div class="tile-label" style="margin:0 0 8px">RUNS PER HOUR (last 6h)</div>
      ${buckets.map((v, i) => `<div class="bar-row">
        <span class="bar-label">${labels[i]}</span>
        <span class="bar-track"><span class="bar-fill" style="width:${Math.round((v / maxCount) * 100)}%;background:var(--blue-light)"></span></span>
        <span class="bar-num">${v}${costBuckets[i] > 0 ? ` · $${costBuckets[i].toFixed(3)}` : ""}</span>
      </div>`).join("")}
    </div>`;
  }

  function render(m, rawRuns) {
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
    html += tile("P95 GEN LATENCY", m.p95_generation_latency_s != null ? Mailroom.fmt.latency(m.p95_generation_latency_s) : "—");
    html += tile("AVG QUALITY", quality, qcls);
    if (vBars.length) html += bars("JUDGE VERDICTS", vBars, "#5f9e6e");
    if (docBars.length) html += bars("DOC TYPES", docBars, "#d9a866");
    if (rawRuns && rawRuns.length) html += trendBars(rawRuns);
    gridEl.innerHTML = html || `<div class="hint mono">NO METRICS YET</div>`;
  }

  async function refresh(since = 3600) {
    try {
      let data;
      let rawRuns = [];
      if (window.Mailroom.demoMode) {
        rawRuns = window.Mailroom.demoRuns || [];
        data = computeLocalMetrics(rawRuns);
      } else {
        data = await Mailroom.api.metrics(since);
        // Also fetch raw runs for the trend chart (optional — but V-18: a
        // failure must be visible, not silently swallowed)
        try {
          const tdata = await Mailroom.api.traces(Math.max(since, 21600), 200);
          rawRuns = tdata.runs || [];
        } catch (e) {
          console.warn("[mailroom] trend data unavailable:", e.message || e);
        }
      }
      render(data, rawRuns);
      return data;
    } catch (err) {
      gridEl.innerHTML = `<div class="insp-error">metrics unavailable — ${Mailroom.esc(err.message || String(err))}</div>`;
      throw err;
    }
  }

  return { refresh, computeLocalMetrics };
})();