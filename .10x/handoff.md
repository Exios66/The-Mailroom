# Handoff

**From:** SDE (M1 consumer) → **To:** QA, then SDE (M2)

Done:
- M0 in both repos (The-Mailroom #63, llm-mailroom #166).
- A-1 in review (llm-mailroom #165).
- M1 consumer side stacked on #63: A-2 pin bump + vendoring, A-3 contract-driven `pipeline_schema`, F-2 conformance, T-4 source registry, T-5 source conformance kit, H-2 CircleCI.

Owner actions:
1. Enable CircleCI for Exios66/the-mailroom.
2. Merge llm-mailroom #165.

Next (M2):
1. A-7: bump the pin to pipeline main and re-vendor the contract from #165's merge commit (`python scripts/bump_producer_pin.py <sha> --version <x> --checkout ../llm-mailroom`).
2. T-1 + T-2 + T-3 (pipeline): `trace_schema` section and multi-sink OTel emission.
3. T-6: PhoenixSource reads the contract-named document spans; extend the kit with golden traces emitted by T-2.
4. A-4 dedicated classification-arbiter stage; A-5 extraction gate; A-8 unmapped-span counter; B-*.
