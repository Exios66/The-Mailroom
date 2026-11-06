# ADR-005: Retire Railway; the HF Space pair is the hosted target

**Status:** Accepted (2026-11-06)
**Date:** 2026-11-06
**Feature:** mailroom-alignment-audit

## Context
Railway stops honouring `railway.json` on 2026-12-01. The owner considers the Railway integration deprecated.

## Decision
Remove Railway config, Railway-specific code, tests and docs from both repos. Keep the generic platform `PORT` handling (`listen_port()`), which any container host uses. The hosted deployment is the Hugging Face Docker Space pair (Observatory + producer), plus gh-pages for the static snapshot.

## Alternatives Considered
| Alternative | Pros | Cons | Why Not |
|---|---|---|---|
| Migrate to Railway IaC | Keeps the current host | Beta SDK; owner deprecated the platform | Owner decision |
| Leave the files in place | No work | Dead config that breaks on 2026-12-01 and misleads | Drift |

## Consequences
- The producer's public URL for REVIEW resolve must point at the HF producer Space; verify it with `probe_hosted_spaces.py` before removal.
- Any live Railway services should be shut down by the owner in the Railway dashboard (outside this repo).
