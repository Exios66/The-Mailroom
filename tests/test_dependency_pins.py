"""Optional extras must resolve immutable, mutually compatible refs.

The 2026-10-25 drift audit flagged the visualizer for pinning a *movable*
release tag while the pipeline pinned an exact commit, and for extras that
demanded different Dojo versions. These tests parse the real ``pyproject``
so re-introducing a tag (or drifting the extras apart) fails here.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]
DOJO_PIN_COMMIT = "1cd4aba76d82eea20c6e8dfcc0d760881bf84924"
PIPELINE_PIN_COMMIT = "9e8f30b279e7626c056b03511f823105760f80d7"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _extras() -> dict[str, list[str]]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return data["project"]["optional-dependencies"]


def _ref(dep: str) -> str:
    return dep.rsplit("@", 1)[-1]


def test_eval_extra_pins_the_immutable_dojo_commit():
    deps = [d for d in _extras()["eval"] if d.startswith("llm-dojo-scoring")]
    assert len(deps) == 1
    ref = _ref(deps[0])
    assert _SHA_RE.match(ref), f"eval pin is not an immutable commit: {ref}"
    assert ref == DOJO_PIN_COMMIT


def test_pipeline_extra_pins_an_immutable_producer_commit():
    deps = [d for d in _extras()["pipeline"] if d.startswith("mailroom @")]
    assert len(deps) == 1
    ref = _ref(deps[0])
    assert _SHA_RE.match(ref), f"pipeline pin is not an immutable commit: {ref}"
    assert ref == PIPELINE_PIN_COMMIT


def test_combined_extras_only_reference_immutable_commits():
    """`pip install -e ".[eval,pipeline]"` resolves both extras at once."""
    combined = _extras()["eval"] + _extras()["pipeline"]
    refs = {
        _ref(d)
        for d in combined
        if d.startswith(("llm-dojo-scoring", "mailroom @"))
    }
    assert refs == {DOJO_PIN_COMMIT, PIPELINE_PIN_COMMIT}


@pytest.mark.skipif(
    os.environ.get("MAILROOM_TEST_EXTRAS_INSTALL") != "1",
    reason="opt-in resolver integration test requires network and pip",
)
def test_combined_extras_installation(tmp_path):
    """Resolve real upstream metadata, including the producer's Dojo pin."""
    report = tmp_path / "install.json"
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--dry-run",
         "--ignore-installed", "--report", str(report), ".[eval,pipeline]"],
        cwd=ROOT, check=True, timeout=600,
    )
    packages = {
        item["metadata"]["name"]: item
        for item in json.loads(report.read_text())["install"]
    }
    producer = packages["mailroom"]
    dojo = packages["llm-dojo-scoring"]
    assert producer["download_info"]["vcs_info"]["commit_id"] == PIPELINE_PIN_COMMIT
    assert dojo["download_info"]["vcs_info"]["commit_id"] == DOJO_PIN_COMMIT
    upstream_dojo, = [
        Requirement(dep) for dep in producer["metadata"]["requires_dist"]
        if Requirement(dep).name == "llm-dojo-scoring"
    ]
    assert upstream_dojo.url == Requirement(_extras()["eval"][0]).url
    from mailroom_ui.producer import MAILROOM_DIST_VERSION

    assert producer["metadata"]["version"] == MAILROOM_DIST_VERSION
