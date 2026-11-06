"""T-4 source registry and T-5 source conformance kit (ADR-006)."""

from __future__ import annotations

import pytest

from mailroom_ui import source_registry as reg
from mailroom_ui.multi_source import MultiSource
from tests.source_conformance import (
    GOLDEN_TRACES,
    RENDERERS,
    assert_conformant,
    render_langfuse,
    run_fingerprint,
)


@pytest.mark.parametrize(
    "selector, names",
    [
        (None, ["langfuse"]),
        ("", ["langfuse"]),
        ("phoenix", ["phoenix"]),
        ("both", ["langfuse", "phoenix"]),
        ("Langfuse, phoenix", ["langfuse", "phoenix"]),
        ("phoenix,langfuse,phoenix", ["phoenix", "langfuse"]),
        ("all", ["langfuse", "phoenix"]),
    ],
)
def test_selector_parsing(monkeypatch, selector, names):
    monkeypatch.delenv("MAILROOM_SOURCE", raising=False)
    assert reg.parse_selector(selector) == names


def test_selector_reads_env(monkeypatch):
    monkeypatch.setenv("MAILROOM_SOURCE", "phoenix,langfuse")
    assert reg.selector_key() == "phoenix,langfuse"


def test_unknown_source_names_the_available_ones():
    with pytest.raises(ValueError, match="available: .*langfuse.*phoenix"):
        reg.build_source("zipkin")


def test_registered_adapter_is_built_and_merged():
    built = []

    class Fake:
        def __init__(self, cache_ttl=1.0):
            built.append(cache_ttl)

    reg.register_source("otlp-test", lambda **kw: Fake(**kw), description="test")
    try:
        assert "otlp-test" in reg.available_sources()
        single = reg.build_source("otlp-test", cache_ttl=2.0)
        assert isinstance(single, Fake) and single.source_name == "otlp-test"
        multi = reg.build_source("phoenix,otlp-test", cache_ttl=2.0)
        assert isinstance(multi, MultiSource)
        assert [s.source_name for s in multi.sources] == ["phoenix", "otlp-test"]
        assert built == [2.0, 2.0]
    finally:
        reg.unregister_source("otlp-test")


@pytest.mark.parametrize("bad", ["", "a,b", "both"])
def test_reserved_names_are_refused(bad):
    with pytest.raises(ValueError):
        reg.register_source(bad, lambda **kw: None)


def test_server_uses_the_registry(monkeypatch):
    from server import main

    monkeypatch.setenv("MAILROOM_SOURCE", "phoenix")
    src = main._build_default_source()
    assert type(src).__name__ == "PhoenixSource"
    assert src.source_name == "phoenix"


def test_every_registered_adapter_has_a_conformance_renderer():
    assert set(reg.available_sources()) <= set(RENDERERS)


def test_golden_traces_use_only_contract_names():
    from mailroom_ui.pipeline_schema import CONTRACT

    names = set(CONTRACT["spans"])
    for golden in GOLDEN_TRACES:
        assert {s.name for s in golden.spans} <= names, golden.trace_id


def test_reference_renderer_interprets_the_golden_routes():
    by_id = {g.trace_id: run_fingerprint(render_langfuse(g).get_run(g.trace_id))
             for g in GOLDEN_TRACES}
    assert by_id["gold-archived"]["stage"] == "archived"
    assert by_id["gold-archived"]["total_tokens"] == 4600
    assert by_id["gold-review"]["stage"] == "review"
    assert "retry_classify" in by_id["gold-review"]["routing_path"]
    assert by_id["gold-aborted"]["stage"] == "failed"
    assert by_id["gold-aborted"]["failure_class"] == "llm_timeout"


@pytest.mark.parametrize("adapter", sorted(RENDERERS))
def test_adapter_is_conformant(adapter):
    assert_conformant(adapter, RENDERERS[adapter])
