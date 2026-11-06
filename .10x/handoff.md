# Handoff

**From:** SDE (M0) → **To:** SDE (M1 consumer), QA

Done: M0 in both repos; the pipeline contract export (A-1) is in review as llm-mailroom#165.
Next (M1 consumer, The-Mailroom):
1. A-2 `scripts/bump_producer_pin.py` (moves the SHA in all locations; vendors `mailroom_ui/contract/mailroom-contract.json` from the pinned commit).
2. A-3 `pipeline_schema` loads classes, agents, failure classes, subclasses, fields and observation types from the contract.
3. F-2 conformance tests: every contract node and span maps to a `Stage` with a phase and a floor station.
4. Fix what F-2 flags (A-4 `classification_arbiter`, A-6 roster).
Pin to llm-mailroom#165's merge commit once merged; until then, vendor from the PR head and say so.
