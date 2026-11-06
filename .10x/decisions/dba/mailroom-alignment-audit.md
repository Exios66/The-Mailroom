# DBA — mailroom-alignment-audit

- [DISCOVERED] Operator desk uses SQLite (`python -m operator_desk` migrates). Visualizer stores no pipeline data; Langfuse + `trace_cache.py` only.
- [DISCOVERED] Pipeline has a SQLite catalog/audit log and a unified audit row spec (pipeline PR #151) the visualizer does not yet read.
