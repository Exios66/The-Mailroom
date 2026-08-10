/* The-Mailroom live console: a scrolling log of pipeline activity. */

const ConsoleView = (() => {
  const el = document.getElementById("console-log");
  const MAX_LINES = 500;

  function stamp() {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }

  function log(msg, cls = "") {
    const line = document.createElement("div");
    line.className = `line ${cls}`;
    line.textContent = `[${stamp()}] ${msg}`;
    el.appendChild(line);
    while (el.children.length > MAX_LINES) el.removeChild(el.firstChild);
    el.scrollTop = el.scrollHeight;
  }

  function banner(msg) {
    const line = document.createElement("div");
    line.className = "line banner";
    line.textContent = `*** ${msg} ***`;
    el.appendChild(line);
    while (el.children.length > MAX_LINES) el.removeChild(el.firstChild);
    el.scrollTop = el.scrollHeight;
  }

  return { log, banner };
})();
