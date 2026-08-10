/* The-Mailroom floor: canvas conveyor renderer.
 * Clean, bright pixel envelopes flowing through stations.
 * Archived items leave the floor entirely. */

const Floor = (() => {
  const canvas = document.getElementById("floor");
  const ctx = canvas.getContext("2d");
  const W = 1440;
  const H = 480;

  // 6 stations: x positions evenly distributed
  const STATIONS = [
    { key: "sorter", x: 80, label: "SORTER", color: "#7d97b5" },
    { key: "extract", x: 320, label: "EXTRACT", color: "#d9a866" },
    { key: "boss", x: 560, label: "BOSS", color: "#95272e" },
    { key: "report", x: 800, label: "REPORT", color: "#659099" },
    { key: "archive", x: 1040, label: "ARCHIVE", color: "#5f9e6e" },
    { key: "review", x: 1280, label: "REVIEW", color: "#f7d156" },
  ];

  const ENV_Y = 240;       // y position for envelopes on conveyor
  const ENV_W = 32;        // envelope width in pixels
  const ENV_H = 22;        // envelope height in pixels

  const envs = new Map();
  let hoveredId = null;
  let sourceState = "gold";

  function targetFor(run) {
    const st = run.stage;
    // Archived/failed items leave the floor
    if (st === "archived" || st === "failed") {
      return { x: 1500, y: 440, remove: true };
    }
    if (st === "review" || run.needs_human) {
      return { x: STATIONS[5].x, y: ENV_Y };
    }
    if (st === "classify" || st === "retry_classify" || st === "ingest" || st === "inbox" || st === "unknown") {
      return { x: STATIONS[0].x, y: ENV_Y };
    }
    if (st === "extract" || st === "retry_extract") {
      return { x: STATIONS[1].x, y: ENV_Y };
    }
    if (st === "boss") {
      return { x: STATIONS[2].x, y: ENV_Y };
    }
    if (st === "report" || st === "catalog" || st === "archive") {
      return { x: STATIONS[3].x, y: ENV_Y };
    }
    return { x: STATIONS[0].x, y: ENV_Y };
  }

  function tintFor(run) {
    const colors = {
      contract: "#7d97b5",
      corporate_record: "#659099",
      due_diligence: "#d9a866",
      correspondence: "#e8b478",
      compliance_filing: "#8fd0a0",
      court_opinion: "#e26863",
    };
    return colors[run.doc_type] || "#a09f9f";
  }

  function drawEnvelope(x, y, tint) {
    // Border (black)
    ctx.fillStyle = "#000000";
    ctx.fillRect(x, y, ENV_W, ENV_H);
    // Paper body (cream)
    ctx.fillStyle = "#faf3e6";
    ctx.fillRect(x + 1, y + 1, ENV_W - 2, ENV_H - 2);
    // Color stripe at top-left
    ctx.fillStyle = tint;
    ctx.fillRect(x + 2, y + 2, 6, 6);
    // Fold lines
    ctx.fillStyle = "#e8dcc3";
    ctx.fillRect(x + 2, y + ENV_H / 2 - 1, ENV_W - 4, 2);
    ctx.fillRect(x + 2, y + ENV_H / 2 + 3, ENV_W - 4, 2);
    // Re-draw border
    ctx.fillStyle = "#000000";
    ctx.fillRect(x, y, ENV_W, 1);
    ctx.fillRect(x, y + ENV_H - 1, ENV_W, 1);
    ctx.fillRect(x, y, 1, ENV_H);
    ctx.fillRect(x + ENV_W - 1, y, 1, ENV_H);
  }

  function drawStation(s) {
    // Station desk/marker
    ctx.fillStyle = "#3a2f22";
    ctx.fillRect(s.x - 20, ENV_Y + ENV_H + 4, 120, 4);
    ctx.fillStyle = "#a48c6d";
    ctx.fillRect(s.x - 20, ENV_Y + ENV_H + 4, 120, 1);
    // Station color bar above
    ctx.fillStyle = s.color;
    ctx.fillRect(s.x - 10, ENV_Y - 20, 100, 4);
    // Label
    ctx.font = "bold 10px 'Courier New', monospace";
    ctx.fillStyle = s.color;
    ctx.textAlign = "center";
    ctx.fillText(s.label, s.x + 40, ENV_Y - 26);
  }

  function drawConveyor() {
    // Conveyor belt
    ctx.fillStyle = "#2a2a2e";
    ctx.fillRect(0, ENV_Y + ENV_H + 10, W, 24);
    ctx.fillStyle = "#3a3a3e";
    ctx.fillRect(0, ENV_Y + ENV_H + 10, W, 2);
    // Belt segments
    ctx.fillStyle = "#1a1a1d";
    for (let x = 0; x < W; x += 32) {
      ctx.fillRect(x, ENV_Y + ENV_H + 10, 1, 24);
    }
  }

  function drawBackground() {
    ctx.fillStyle = "#141416";
    ctx.fillRect(0, 0, W, H);
    // Room labels
    ctx.font = "bold 9px 'Courier New', monospace";
    ctx.fillStyle = "#7d97b5";
    ctx.textAlign = "center";
    ctx.fillText("INTAKE & SORT", 160, 30);
    ctx.fillText("EXTRACTION & ADJUDICATION", 560, 30);
    ctx.fillText("REPORTING & ARCHIVE", 1040, 30);
    ctx.fillText("REVIEW SIDING", 1280, 30);
  }

  function update(runs) {
    const seen = new Set();
    for (const run of runs) {
      if (!run || !run.trace_id) continue;
      seen.add(run.trace_id);
      const t = targetFor(run);
      let e = envs.get(run.trace_id);
      if (!e) {
        e = {
          id: run.trace_id,
          x: -50,
          y: ENV_Y,
          seed: Math.random() * 1000,
          alpha: 1,
          run: run,
        };
        envs.set(run.trace_id, e);
      }
      e.run = run;
      e.tx = t.x;
      e.ty = t.y;
      e.remove = !!t.remove;
      e.tint = tintFor(run);
      e.dying = false;
    }
    for (const [id, e] of envs) {
      if (!seen.has(id)) e.dying = true;
    }
  }

  function reset() {
    envs.clear();
  }

  function setSource(state) {
    sourceState = state;
  }

  function posFromEvent(ev) {
    const rect = canvas.getBoundingClientRect();
    return {
      x: ((ev.clientX - rect.left) / rect.width) * W,
      y: ((ev.clientY - rect.top) / rect.height) * H,
    };
  }

  function hitTest(p) {
    for (const e of [...envs.values()].reverse()) {
      if (e.dying || e.alpha <= 0.3) continue;
      if (p.x >= e.x && p.x <= e.x + ENV_W && p.y >= e.y && p.y <= e.y + ENV_H) {
        return e;
      }
    }
    return null;
  }

  function onSelect(cb) { callbacks.select = cb; }
  function onHover(cb) { callbacks.hover = cb; }
  const callbacks = { select: null, hover: null };

  canvas.addEventListener("click", (ev) => {
    const e = hitTest(posFromEvent(ev));
    if (e && callbacks.select) callbacks.select(e.id, e.run);
  });

  canvas.addEventListener("mousemove", (ev) => {
    const e = hitTest(posFromEvent(ev));
    const id = e ? e.id : null;
    if (id !== hoveredId) {
      hoveredId = id;
      canvas.style.cursor = e ? "pointer" : "default";
      if (callbacks.hover) callbacks.hover(e ? e.run : null);
    }
  });

  canvas.addEventListener("mouseleave", () => {
    hoveredId = null;
    canvas.style.cursor = "default";
    if (callbacks.hover) callbacks.hover(null);
  });

  function drawEnvelopes(t) {
    for (const e of envs.values()) {
      if (e.alpha <= 0) continue;
      const y = e.y;
      ctx.globalAlpha = e.alpha;
      drawEnvelope(e.x, y, e.tint);
      if (e.id === hoveredId && !e.dying) {
        ctx.strokeStyle = "#f7d156";
        ctx.lineWidth = 2;
        ctx.strokeRect(e.x - 2, y - 2, ENV_W + 4, ENV_H + 4);
      }
    }
    ctx.globalAlpha = 1;
  }

  function drawStatus(t) {
    const active = [...envs.values()].filter((e) => !e.dying && e.alpha > 0.3).length;
    ctx.font = "bold 11px 'Courier New', monospace";
    ctx.fillStyle = "#7d97b5";
    ctx.textAlign = "left";
    ctx.fillText(`ACTIVE: ${active}`, 20, 460);
    const statusColor = sourceState === "red" ? "#e26863" :
                        sourceState === "green" ? "#5f9e6e" : "#f7d156";
    ctx.fillStyle = statusColor;
    ctx.fillText(`SOURCE: ${sourceState.toUpperCase()}`, 20, 475);
  }

  function draw(t) {
    ctx.clearRect(0, 0, W, H);
    drawBackground();
    for (const s of STATIONS) drawStation(s);
    drawConveyor();
    drawEnvelopes(t);
    drawStatus(t);
  }

  function frame(t) {
    for (const e of [...envs.values()]) {
      if (!e.dying) {
        e.x += (e.tx - e.x) * 0.08;
        e.y += (e.ty - e.y) * 0.08;
        // Remove archived/failed items that reach offscreen
        if (e.remove && Math.abs(e.x - e.tx) < 5) {
          e.dying = true;
        }
      } else {
        e.alpha -= 0.06;
        if (e.alpha <= 0) {
          envs.delete(e.id);
          if (hoveredId === e.id) hoveredId = null;
        }
      }
    }
    draw(t);
    requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);

  /* ---- replay ---- */

  let replayTimers = [];
  let replayState = null;

  function clearReplayTimers() {
    for (const t of replayTimers) clearTimeout(t);
    replayTimers = [];
  }

  function replay(runData) {
    clearReplayTimers();
    // Clear any current envelopes except the one being replayed
    const replayId = runData.trace_id;
    for (const [id, e] of envs) {
      if (id !== replayId) e.dying = true;
    }
    replayState = { id: replayId, startTime: Date.now(), steps: [] };

    // Build the stage sequence from routing_path (most accurate) or spans
    const routingPath = runData.routing_path || [];
    const spans = runData.spans || [];

    // Compute per-stage timing from spans
    const stageOrder = ["ingest", "classify", "extract", "boss", "review", "report", "catalog", "archive", "archived"];
    const stageTimes = {}; // stage -> first start_time
    const spanToStage = {
      "ingest-document": "ingest",
      "classify-document": "classify",
      "extract-fields": "extract",
      "adjudicate-conflict": "boss",
      "route-for-review": "review",
      "compile-report": "report",
      "write-catalog": "catalog",
      "archive-document": "archive",
    };
    for (const s of spans) {
      const st = spanToStage[s.name];
      if (st && !stageTimes[st] && s.start_time) {
        stageTimes[st] = new Date(s.start_time).getTime();
      }
    }

    // Compute the sequence: if we have timing data, use it; otherwise use routing_path
    let sequence;
    if (Object.keys(stageTimes).length > 0) {
      sequence = Object.entries(stageTimes)
        .sort((a, b) => a[1] - b[1])
        .map(([st]) => st);
    } else if (routingPath.length > 0) {
      sequence = routingPath;
    } else {
      sequence = ["classify", "extract", "archived"];
    }

    // Create the envelope at the start
    const stageToTarget = {
      inbox: 0, ingest: 0, classify: 0, retry_classify: 0, unknown: 0,
      extract: 1, retry_extract: 1, boss: 2,
      report: 3, catalog: 3, archive: 3, archived: 4,
      review: 5, failed: 5,
    };
    const stationIdx = (st) => {
      const idx = stageToTarget[st];
      return idx != null ? idx : 0;
    };

    const baseRun = {
      trace_id: replayId,
      filename: runData.filename,
      doc_type: runData.doc_type,
      verdict: runData.verdict,
      quality: runData.quality,
      stage: "archived", // start neutral; will animate through stages
      needs_human: false,
      retried: false,
    };
    // Create envelope at the first station
    let e = envs.get(replayId);
    if (!e) {
      e = {
        id: replayId,
        x: STATIONS[0].x,
        y: ENV_Y,
        seed: Math.random() * 1000,
        alpha: 1,
        run: { ...baseRun, stage: sequence[0] },
      };
      envs.set(replayId, e);
    } else {
      e.x = STATIONS[0].x;
      e.y = ENV_Y;
      e.run = { ...baseRun, stage: sequence[0] };
      e.dying = false;
    }
    e.tint = tintFor(baseRun);
    e.tx = STATIONS[0].x;
    e.ty = ENV_Y;

    // Animate through each stage in sequence
    let cumulativeDelay = 600; // initial pause so user sees the envelope appear
    for (let i = 0; i < sequence.length; i++) {
      const stg = sequence[i];
      const idx = stationIdx(stg);
      const t = cumulativeDelay;
      const timer = setTimeout(() => {
        const current = envs.get(replayId);
        if (!current || current.dying) return;
        current.tx = STATIONS[idx].x;
        current.ty = ENV_Y;
        current.run.stage = stg;
        current.tint = tintFor(current.run);
        ConsoleView.log(`REPLAY → ${stg}`, "c-blue");
      }, t);
      replayTimers.push(timer);
      cumulativeDelay += 700;
    }

    // After the sequence finishes, archive it (slide off the floor)
    const endTimer = setTimeout(() => {
      const current = envs.get(replayId);
      if (!current) return;
      current.run.stage = "archived";
      current.tx = 1500;
      current.ty = 440;
      current.remove = true;
      ConsoleView.banner(`REPLAY COMPLETE — ${runData.filename || replayId}`);
    }, cumulativeDelay + 800);
    replayTimers.push(endTimer);
  }

  return { update, reset, setSource, onSelect, onHover, replay };
})();