# CTO — mailroom-alignment-audit

- [DISCOVERED] Stack: Python 3.11+ FastAPI (`server/`, `hosted/`), vanilla pixel-art SPA `web/` (no npm), hosted Observatory `/live`, optional React/Vite/Tailwind desk `ui/` (`/desk`), Textual-style TUI `tui/`, `terminal/` static site, `operator_desk/` (JWT, SQLite, watcher).
- [DISCOVERED] Langfuse is the sole source of truth; optional Phoenix source; no locally-canned data.
- [DISCOVERED] Six UI surfaces for one data feed. Strategic question: which surface is primary; consolidation vs parity maintenance is the biggest cost driver.
- [DISCOVERED] Alignment with the pipeline is maintained by hand-mirrored constants (`pipeline_schema.py`, `trace_interpreter.py`, `prompt_registry.py`). Drift is structural, not accidental.
