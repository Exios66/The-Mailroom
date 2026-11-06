"""Trace-source registry (ADR-006, T-4).

Document traces are what the floor displays, whichever backend stores them.
Langfuse and Phoenix are the primary sinks and are registered here; any other
backend plugs in by registering an adapter under a name, either in code
(``register_source``) or from an installed package through the
``mailroom.sources`` entry-point group. Every adapter satisfies
``sources.TraceSource`` and must pass the source conformance kit
(``tests/source_conformance.py``): the same golden document trace through
any adapter yields the same ``PipelineRun``.

``MAILROOM_SOURCE`` takes one name or a comma-separated list:

    MAILROOM_SOURCE=langfuse            # default
    MAILROOM_SOURCE=phoenix
    MAILROOM_SOURCE=langfuse,phoenix    # merged floor; first source wins id ties
    MAILROOM_SOURCE=both                # alias for langfuse,phoenix
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from importlib import metadata
from typing import Any, Callable, Optional

log = logging.getLogger("mailroom.source_registry")

ENTRY_POINT_GROUP = "mailroom.sources"
DEFAULT_SELECTOR = "langfuse"
# Legacy selector words for "every primary sink".
_ALIASES: dict[str, tuple[str, ...]] = {
    "both": ("langfuse", "phoenix"),
    "multi": ("langfuse", "phoenix"),
    "all": ("langfuse", "phoenix"),
}

SourceFactory = Callable[..., Any]


@dataclass(frozen=True)
class SourceAdapter:
    name: str
    factory: SourceFactory
    description: str = ""


_REGISTRY: dict[str, SourceAdapter] = {}
_entry_points_loaded = False


def register_source(name: str, factory: SourceFactory, *, description: str = "") -> None:
    """Register an adapter. ``factory(cache_ttl=float)`` returns a TraceSource."""
    key = name.strip().lower()
    if not key or "," in key or key in _ALIASES:
        raise ValueError(f"invalid source name: {name!r}")
    _REGISTRY[key] = SourceAdapter(key, factory, description)


def unregister_source(name: str) -> None:
    _REGISTRY.pop(name.strip().lower(), None)


def _langfuse(*, cache_ttl: float = 3.0) -> Any:
    from .langfuse_source import LangfuseSource

    return LangfuseSource(cache_ttl=cache_ttl, poll_cache_ttl=cache_ttl)


def _phoenix(*, cache_ttl: float = 5.0) -> Any:
    from .phoenix_source import PhoenixSource

    return PhoenixSource(cache_ttl=cache_ttl)


register_source("langfuse", _langfuse, description="Langfuse (primary sink)")
register_source("phoenix", _phoenix, description="Arize Phoenix (primary sink)")


def _load_entry_points() -> None:
    global _entry_points_loaded
    if _entry_points_loaded:
        return
    _entry_points_loaded = True
    try:
        eps = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except Exception as exc:  # pragma: no cover - broken metadata
        log.warning("could not read %s entry points: %s", ENTRY_POINT_GROUP, exc)
        return
    for ep in eps:
        if ep.name.lower() in _REGISTRY:
            continue  # built-ins and explicit registrations win
        try:
            register_source(ep.name, ep.load(), description=f"plugin {ep.value}")
        except Exception as exc:
            log.error("trace source plugin %s failed to load: %s", ep.name, exc)


def available_sources() -> dict[str, str]:
    """Registered adapter names -> description."""
    _load_entry_points()
    return {name: a.description for name, a in sorted(_REGISTRY.items())}


def parse_selector(selector: Optional[str] = None) -> list[str]:
    """``MAILROOM_SOURCE`` value -> ordered, de-duplicated adapter names."""
    raw = selector if selector is not None else os.environ.get("MAILROOM_SOURCE", "")
    names: list[str] = []
    for part in (raw or DEFAULT_SELECTOR).split(","):
        key = part.strip().lower()
        if not key:
            continue
        for name in _ALIASES.get(key, (key,)):
            if name not in names:
                names.append(name)
    return names or [DEFAULT_SELECTOR]


def selector_key(selector: Optional[str] = None) -> str:
    """Canonical comma-joined form (cache scoping, health payloads)."""
    return ",".join(parse_selector(selector))


def build_source(selector: Optional[str] = None, *, cache_ttl: Optional[float] = None) -> Any:
    """Instantiate the selected adapters; several are merged by MultiSource."""
    _load_entry_points()
    names = parse_selector(selector)
    unknown = [n for n in names if n not in _REGISTRY]
    if unknown:
        raise ValueError(
            f"unknown trace source {', '.join(unknown)}; "
            f"available: {', '.join(available_sources())}"
        )
    kwargs = {} if cache_ttl is None else {"cache_ttl": cache_ttl}
    sources = []
    for name in names:
        src = _REGISTRY[name].factory(**kwargs)
        if not getattr(src, "source_name", None):
            try:
                src.source_name = name  # provenance label on snapshots
            except AttributeError:
                pass
        sources.append(src)
    if len(sources) == 1:
        return sources[0]
    from .multi_source import MultiSource

    return MultiSource(sources)
