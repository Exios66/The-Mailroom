/* The-Mailroom floor: canvas conveyor renderer.
 * Every envelope is bound to one Langfuse-derived run; position, stamp and
 * tint are derived from the run's stage / doc type / verdict. */

const Floor = (() => {
  const canvas = document.getElementById("floor");
  const ctx = canvas.getContext("2d");
  const PX = 4;
  const W = 1440;
  const H = 560;

  const ENV_W = 80;
  const ENV_H = 56;
  const STAMP_W = 40;
  const STAMP_H = 32;
  const ENV_Y = 220;
  const SIDING_Y = 384;

  const STATIONS = [
    { key: "sorter", x: 24, label: "SORTER" },
    { key: "specialist_contract", x: 168, label: "CONTRACTS" },
    { key: "specialist_corporate", x: 312, label: "CORPORATE" },
    { key: "specialist_due_diligence", x: 456, label: "DUE DILIGENCE" },
    { key: "specialist_correspondence", x: 600, label: "CORRESP." },
    { key: "specialist_compliance", x: 744, label: "COMPLIANCE" },
    { key: "specialist_court", x: 888, label: "COURT OPIN." },
    { key: "boss", x: 1032, label: "BOSS" },
    { key: "reporter", x: 1176, label: "REPORTER" },
    { key: "archivist", x: 1312, label: "ARCHIVIST" },
  ];
  const STATION_BY_KEY = {};
  for (const s of STATIONS) STATION_BY_KEY[s.key] = s;

  const SPEC_BY_DOC = {
    contract: "specialist_contract",
    corporate_record: "specialist_corporate",
    due_diligence: "specialist_due_diligence",
    correspondence: "specialist_correspondence",
    compliance_filing: "specialist_compliance",
    court_opinion: "specialist_court",
  };

  const ROOM_LABELS = [
    { text: "INTAKE & SORT", x: 92 },
    { text: "EXTRACTION & ADJUDICATION", x: 612 },
    { text: "REPORTING & ARCHIVE", x: 1250 },
  ];

  function targetFor(run) {
    const st = run.stage;
    if (st === "failed") return { x: 1010, y: SIDING_Y };
    if (st === "review") return { x: 670, y: SIDING_Y };
    if (SPEC_BY_DOC[run.doc_type]) {
      const s = STATION_BY_KEY[SPEC_BY_DOC[run.doc_type]];
      return { x: s.x + 20, y: ENV_Y };
    }
    switch (st) {
      case "boss": return { x: STATION_BY_KEY.boss.x + 20, y: ENV_Y };
      case "report": return { x: STATION_BY_KEY.reporter.x + 20, y: ENV_Y };
      case "catalog":
      case "archive":
      case "archived": return { x: STATION_BY_KEY.archivist.x + 8, y: ENV_Y };
      default: return { x: 68, y: ENV_Y };
    }
  }

  function stampFor(run) {
    if (run.stage === "failed") return SPRITES.stamp_failed;
    if (run.stage === "review" || run.needs_human) return SPRITES.stamp_review;
    if (run.verdict === "CORRECT" || run.stage === "archived") return SPRITES.stamp_approved;
    return null;
  }

  const envs = new Map();
  let hoveredId = null;
  let sourceState = "gold";

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
          x: -60,
          y: 430,
          seed: Math.random() * 1000,
          alpha: 1,
        };
        envs.set(run.trace_id, e);
      }
      e.run = run;
      e.tx = t.x;
      e.ty = t.y;
      e.tint = DOC_TYPE_COLORS[run.doc_type] || DOC_TYPE_DEFAULT;
      e.stamp = stampFor(run);
      e.retried = !!run.retried;
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
      if (e.dying) continue;
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

  /* ---- drawing ---- */

  function drawWall(t) {
    ctx.fillStyle = "#17171a";
    ctx.fillRect(0, 0, W, 260);
    ctx.fillStyle = "#1d1d20";
    ctx.fillRect(0, 308, W, H - 308);
    ctx.fillStyle = "#141416";
    ctx.fillRect(0, 280, W, H - 280);

    for (const p of [156, 1164]) {
      ctx.fillStyle = "#2e2e33";
      ctx.fillRect(p, 0, 10, 276);
      ctx.fillStyle = "#1a1a1d";
      ctx.fillRect(p + 1, 0, 2, 276);
      ctx.fillStyle = "#3c3c42";
      ctx.fillRect(p + 7, 0, 2, 276);
    }

    ctx.textAlign = "center";
    ctx.font = "bold 12px 'Courier New', monospace";
    ctx.fillStyle = "#7d97b5";
    for (const r of ROOM_LABELS) ctx.fillText(r.text, r.x, 18);
  }

  function drawDesk() {
    ctx.fillStyle = "#3a2f22";
    ctx.fillRect(0, 260, W, 16);
    ctx.fillStyle = "#a48c6d";
    ctx.fillRect(0, 260, W, 3);
    ctx.fillStyle = "#684b32";
    ctx.fillRect(0, 268, W, 4);
  }

  function drawConveyor() {
    for (let x = 0; x < W; x += 64) {
      drawSprite(ctx, SPRITES.roller, x, 276, PX);
    }
    drawSprite(ctx, SPRITES.node_start, 0, 276, PX);
    drawSprite(ctx, SPRITES.node_end, 1368, 276, PX);

    const lamps = { green: SPRITES.lamp_green, gold: SPRITES.lamp_gold, red: SPRITES.lamp_red };
    drawSprite(ctx, lamps[sourceState] || SPRITES.lamp_gold, 24, 232, PX);
  }

  function drawBins(t) {
    drawSprite(ctx, SPRITES.bin_inbox, 24, 408, PX);
    drawSprite(ctx, SPRITES.bin_review, 640, 408, PX);
    drawSprite(ctx, SPRITES.bin_failed, 980, 408, PX);

    const blink = Math.floor(t / 500) % 2 === 0;
    if (blink) drawSprite(ctx, SPRITES.lamp_red, 654, 372, PX);

    ctx.font = "bold 9px 'Courier New', monospace";
    ctx.fillStyle = "#a09f9f";
    ctx.textAlign = "center";
    ctx.fillText("INBOX", 64, 466);
    ctx.fillText("REVIEW SIDING", 680, 466);
    ctx.fillText("FAILED", 1020, 466);
  }

  function drawAgents() {
    for (const s of STATIONS) {
      const rows = SPRITES[s.key];
      if (!rows) continue;
      drawSprite(ctx, rows, s.x, 132, PX);
      const prop = PROPS[s.key];
      if (prop && prop.rows) {
        drawSprite(ctx, prop.rows, s.x + prop.x * PX, 132 + prop.y * PX, PX);
      }
    }
    ctx.font = "bold 9px 'Courier New', monospace";
    ctx.fillStyle = "#e8dcc3";
    ctx.textAlign = "center";
    for (const s of STATIONS) ctx.fillText(s.label, s.x + 64, 270);
  }

  function drawEnvelopes(t) {
    for (const e of envs.values()) {
      if (!e.run) continue;
      const bob = e.y >= 300 ? 0 : Math.sin(t / 300 + e.seed) * 2;
      const y = e.y + bob;
      ctx.globalAlpha = Math.max(0, Math.min(1, e.alpha));
      drawSprite(ctx, SPRITES.envelope, e.x, y, PX, e.tint);
      if (e.stamp) drawSprite(ctx, e.stamp, e.x + 40, y, PX);
      if (e.retried) {
        ctx.fillStyle = "#f7d156";
        ctx.fillRect(e.x + 2, y + 2, 6, 6);
      }
      if (e.id === hoveredId) {
        ctx.strokeStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.strokeRect(e.x - 2, y - 2, ENV_W + 4, ENV_H + 4);
      }
    }
    ctx.globalAlpha = 1;
  }

  function draw(t) {
    ctx.clearRect(0, 0, W, H);
    ctx.imageSmoothingEnabled = false;
    drawWall(t);
    drawDesk();
    drawConveyor();
    drawBins(t);
    drawAgents();
    drawEnvelopes(t);
  }

  /* ---- animation loop ---- */

  function frame(t) {
    for (const e of envs.values()) {
      if (!e.dying) {
        e.x += (e.tx - e.x) * 0.055;
        e.y += (e.ty - e.y) * 0.055;
        if (Math.abs(e.tx - e.x) < 1) e.x = e.tx;
        if (Math.abs(e.ty - e.y) < 1) e.y = e.ty;
      } else {
        e.alpha -= 0.04;
        if (e.alpha <= 0) {
          envs.delete(e.id);
          if (hoveredId === e.id) hoveredId = null;
          continue;
        }
      }
    }
    draw(t);
    requestAnimationFrame(frame);
  }

  requestAnimationFrame(frame);

  return { update, reset, setSource, onSelect, onHover };
})();
