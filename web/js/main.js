/* The-Mailroom app shell: boot, tabs, source light, live snapshot wiring
 * (WebSocket with polling fallback), closed-state handling. */

const Main = (() => {
  const lightEl = document.getElementById("source-light");
  const sourceLabelEl = document.getElementById("source-label");
  const clockEl = document.getElementById("clock");
  const statusLeftEl = document.getElementById("status-left");
  const statusRightEl = document.getElementById("status-right");
  const hintEl = document.getElementById("floor-hint");
  const closedEl = document.getElementById("closed");
  const tabEls = Array.from(document.querySelectorAll(".tab"));

  let langfuseOk = false;
  let wsOk = false;
  let lastSnapshot = [];
  let lastIds = new Set();
  let byId = new Map();
  let pollTimer = null;
  let fallbackTimer = null;
  let activeTab = "floor";
  let demoMode = false;
  let demoTimer = null;
  let demoRuns = [];

  function p2(n) { return String(n).padStart(2, "0"); }

  function tick() {
    const d = new Date();
    clockEl.textContent = `${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`;
  }

  function setLamp(state) {
    lightEl.className = `light light-${state}`;
    floorSetSource(state);
  }

  function floorSetSource(state) {
    if (langfuseOk && wsOk) Floor.setSource("green");
    else if (!langfuseOk) Floor.setSource("red");
    else Floor.setSource("gold");
  }

  function applySource() {
    if (!langfuseOk && !demoMode) {
      setLamp("red");
      sourceLabelEl.textContent = "SOURCE: OFFLINE";
      statusLeftEl.textContent = "MAILROOM CLOSED — NO LANGFUSE CONNECTION";
      statusLeftEl.className = "st-bad mono";
      closedEl.hidden = false;
      Floor.reset();
      Floor.setSource("red");
    } else if (demoMode && !langfuseOk) {
      setLamp("gold");
      sourceLabelEl.textContent = "SOURCE: DEMO MODE";
      statusLeftEl.textContent = "MAILROOM DEMO — SIMULATED PIPELINE RUNNING";
      statusLeftEl.className = "st-warn mono";
      closedEl.hidden = true;
      Floor.setSource("gold");
      startDemo();
    } else if (demoMode && langfuseOk) {
      setLamp("gold");
      sourceLabelEl.textContent = "SOURCE: DEMO MODE (LANGFUSE UP)";
      statusLeftEl.textContent = "MAILROOM DEMO — SIMULATED PIPELINE (LANGFUSE AVAILABLE)";
      statusLeftEl.className = "st-warn mono";
      closedEl.hidden = true;
      Floor.setSource("gold");
      startDemo();
    } else {
      setLamp(wsOk ? "green" : "gold");
      sourceLabelEl.textContent = "SOURCE: LANGFUSE";
      statusLeftEl.textContent = "MAILROOM LIVE — WATCHING LANGFUSE";
      statusLeftEl.className = "st-good mono";
      closedEl.hidden = true;
      Floor.setSource(wsOk ? "green" : "gold");
      stopDemo();
    }
  }

  function startDemo() {
    if (demoTimer) return;
    demoRuns = generateDemoRuns();
    let idx = 0;
    demoTimer = setInterval(() => {
      if (!demoMode || langfuseOk) return stopDemo();
      const run = demoRuns[idx % demoRuns.length];
      run.timestamp = Date.now();
      Floor.update([run]);
      ConsoleView.log(`DEMO ${run.filename} → ${run.stage}${run.verdict ? ` · ${run.verdict}` : ""}`, "c-blue");
      idx++;
    }, 3000);
    ConsoleView.banner("DEMO MODE ACTIVE — SIMULATED PIPELINE");
  }

  function stopDemo() {
    if (demoTimer) {
      clearInterval(demoTimer);
      demoTimer = null;
    }
    if (!langfuseOk) Floor.reset();
  }

  function generateDemoRuns() {
    const stages = [
      { stage: "inbox", phase: "intake_sort", doc_type: "contract", filename: "contract_01_nda.pdf" },
      { stage: "ingest", phase: "intake_sort", doc_type: "contract", filename: "contract_02_msa.pdf" },
      { stage: "classify", phase: "intake_sort", doc_type: "contract", filename: "contract_03_sa.pdf", classification_confidence: 0.96 },
      { stage: "extract", phase: "extraction", doc_type: "contract", filename: "contract_04_jv.pdf", extraction_confidence: 0.89 },
      { stage: "boss", phase: "extraction", doc_type: "contract", filename: "contract_05_conflict.pdf", verdict: "PARTIAL", quality: 0.65 },
      { stage: "report", phase: "reporting", doc_type: "contract", filename: "contract_06_report.pdf" },
      { stage: "archive", phase: "reporting", doc_type: "contract", filename: "contract_07_archive.pdf" },
      { stage: "archived", phase: "terminal", doc_type: "contract", filename: "contract_08_done.pdf", verdict: "CORRECT", quality: 0.94 },
      { stage: "review", phase: "review", doc_type: "due_diligence", filename: "dd_01_liability.pdf", review_decision: "human review", escalation_reason: "low extraction confidence" },
      { stage: "failed", phase: "terminal", doc_type: "compliance_filing", filename: "compliance_01_filing.pdf", error_message: "extraction failed: invalid JSON" },
    ];
    return stages.map((s, i) => ({
      trace_id: `demo-run-${i}`,
      filename: s.filename,
      matter_id: "DEMO-MATTER",
      session_id: "DEMO-MATTER",
      environment: "demo",
      tags: ["mailroom", "demo", "demo-mode"],
      attempt: 1,
      stage: s.stage,
      phase: s.phase,
      doc_type: s.doc_type,
      classification_confidence: s.classification_confidence,
      extraction_confidence: s.extraction_confidence,
      review_decision: s.review_decision,
      escalation_reason: s.escalation_reason,
      error_message: s.error_message,
      verdict: s.verdict,
      quality: s.quality,
      latency: 5 + Math.random() * 20,
      llm_call_count: 2 + Math.floor(Math.random() * 4),
      total_tokens: 2000 + Math.floor(Math.random() * 3000),
      cost_usd: 0.0005 + Math.random() * 0.002,
      retried: Math.random() > 0.7,
      needs_human: s.stage === "review",
      created_at: new Date(Date.now() - Math.random() * 3600000).toISOString(),
      updated_at: new Date().toISOString(),
      routing_path: [],
    }));
  }

  function applySnapshot(runs) {
    if (!langfuseOk && !demoMode) return;
    lastSnapshot = runs;
    const ids = new Set(runs.map((r) => r.trace_id));
    const added = [...ids].filter((id) => !lastIds.has(id));
    const removed = [...lastIds].filter((id) => !ids.has(id));
    const changed = runs.filter((r) => {
      const prev = byId.get(r.trace_id);
      return prev && (prev.stage !== r.stage || prev.verdict !== r.verdict);
    });
    lastIds = ids;
    byId = new Map(runs.map((r) => [r.trace_id, r]));

    if (added.length) {
      for (const r of runs.filter((x) => added.includes(x.trace_id)).slice(0, 5)) {
        ConsoleView.log(`NEW ${r.filename || r.trace_id} → ${r.stage}`, "c-ok");
      }
      if (added.length > 5) ConsoleView.log(`… ${added.length - 5} more new runs`, "c-dim");
    }
    for (const r of changed.slice(0, 5)) {
      ConsoleView.log(`${r.filename || r.trace_id} → ${r.stage}${r.verdict ? ` · ${r.verdict}` : ""}`, "c-blue");
    }
    if (removed.length) ConsoleView.log(`${removed.length} run(s) left the window`, "c-dim");

    Floor.update(runs);
    renderStatus();
  }

  function renderStatus() {
    const envs = new Set();
    for (const r of lastSnapshot) {
      const env = Mailroom.envFromTags(r.tags);
      if (env) envs.add(env);
    }
    const envTxt = envs.size ? ` · ENV: ${[...envs].sort().join(",")}` : "";
    statusRightEl.textContent = `RUNS: ${lastSnapshot.length}${envTxt}`;
  }

  async function checkHealth() {
    try {
      const h = await Mailroom.api.health();
      langfuseOk = !!h.langfuse;
    } catch (err) {
      langfuseOk = false;
      ConsoleView.log(`health check failed: ${err.message || err}`, "c-bad");
    }
    applySource();
  }

  function onMessage(msg) {
    if (msg.type === "status") {
      if (msg.connected) {
        wsOk = true;
        ConsoleView.banner("MAILROOM ONLINE — WATCHING LANGFUSE");
      } else {
        wsOk = false;
        ConsoleView.log("connection lost — reconnecting…", "c-warn");
      }
      applySource();
    } else if (msg.type === "snapshot") {
      applySnapshot(msg.runs || []);
    }
  }

  function startFallbackPolling() {
    if (fallbackTimer) return;
    fallbackTimer = setInterval(async () => {
      if (!langfuseOk || wsOk) return;
      try {
        const data = await Mailroom.api.traces(1800, 200);
        applySnapshot(data.runs || []);
      } catch (err) {
        ConsoleView.log(`poll fallback failed: ${err.message || err}`, "c-warn");
      }
    }, 10000);
    ConsoleView.log("polling /api/traces as fallback", "c-dim");
  }

  function switchView(name) {
    activeTab = name;
    for (const t of tabEls) t.classList.toggle("active", t.dataset.view === name);
    for (const v of document.querySelectorAll(".view")) v.hidden = v.id !== `view-${name}`;
    if (name === "review") {
      ReviewView.refresh().catch(() => {});
      ConsoleView.log("review queue refreshed", "c-dim");
    } else if (name === "sessions") {
      SessionsView.refresh().catch(() => {});
      ConsoleView.log("sessions refreshed", "c-dim");
    } else if (name === "metrics") {
      MetricsView.refresh().catch(() => {});
      ConsoleView.log("metrics refreshed", "c-dim");
    }
  }

  function boot() {
    tick();
    setInterval(tick, 1000);

    ConsoleView.banner("THE MAILROOM — LLM-MAILROOM VISUAL ENGINE");

    Mailroom.api.meta()
      .then((m) => { Mailroom.meta = m; })
      .catch(() => {});

    Floor.onSelect((traceId, run) => {
      ConsoleView.log(`INSPECT ${run && run.filename ? run.filename : traceId}`, "c-blue");
      Inspector.open(traceId);
    });
    Floor.onHover((run) => {
      if (!run) {
        hintEl.textContent = "click an envelope to inspect its run";
        return;
      }
      const bits = [run.filename || run.trace_id, run.stage];
      if (run.doc_type) bits.push(run.doc_type);
      if (run.verdict) bits.push(run.verdict);
      hintEl.textContent = bits.join(" · ");
    });

    for (const t of tabEls) {
      t.addEventListener("click", () => switchView(t.dataset.view));
    }
    setInterval(() => {
      if (activeTab === "review") ReviewView.refresh().catch(() => {});
      if (activeTab === "sessions") SessionsView.refresh().catch(() => {});
      if (activeTab === "metrics") MetricsView.refresh().catch(() => {});
    }, 30000);

    document.getElementById("closed-retry").addEventListener("click", () => {
      ConsoleView.log("retrying connection…", "c-dim");
      checkHealth();
    });

    // Demo mode toggle (D key)
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "d" || ev.key === "D") {
        demoMode = !demoMode;
        ConsoleView.log(`DEMO MODE ${demoMode ? "ON" : "OFF"}`, demoMode ? "c-ok" : "c-warn");
        applySource();
      }
    });

    setInterval(checkHealth, 5000);
    checkHealth();

    setTimeout(() => {
      if (!wsOk) startFallbackPolling();
    }, 8000);

    Mailroom.connectWS(onMessage);
  }

  document.addEventListener("DOMContentLoaded", boot);
  return {};
})();
