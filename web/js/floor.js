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
    if (st === "classify" || st === "ingest" || st === "inbox") {
      return { x: STATIONS[0].x, y: ENV_Y };
    }
    if (st === "extract") {
      return { x: STATIONS[1].x, y: ENV_Y };
    }
    if (st === "boss") {
      return { x: STATIONS[2].x, y: ENV_Y };
    }
    if (st === "report" || st === "catalog" || st === "archive") {
      return { x: STATIONS[3].x, y: ENV_Y };
    }
    return { x: STATIONS[4].x, y: ENV_Y };
  }

  function tintFor(run) {
    const colors = {
      contract: "#7d97b5",
      corporate_record: "#659099",
      due_diligence: "#d9a866",
      correspondence: "#f2d4aa",
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

  return { update, reset, setSource, onSelect, onHover };
})();