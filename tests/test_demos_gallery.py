"""The demos notebook and markdown index must cover every still + the PR video."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
DEMOS = ROOT / "docs" / "demos"
NOTEBOOK = DEMOS / "The-Mailroom-Demos.ipynb"
INDEX = ROOT / "docs" / "demos.md"
WIKI = ROOT / "wiki" / "Demos.md"
README = ROOT / "README.md"
VIDEO = "tui-server-observatory-desk-walkthrough.mp4"


def _notebook_text() -> str:
    nb = json.loads(NOTEBOOK.read_text())
    chunks = []
    for cell in nb["cells"]:
        chunks.extend(cell.get("source") or [])
    return "".join(chunks)


def test_walkthrough_video_is_in_demos():
    path = DEMOS / VIDEO
    assert path.is_file(), path
    assert path.stat().st_size > 1_000_000
    assert (DEMOS / "walkthrough-poster.png").is_file()


def test_notebook_and_indexes_cover_every_png():
    pngs = sorted(p.name for p in SHOTS.glob("*.png"))
    assert len(pngs) >= 17, pngs
    nb = _notebook_text()
    demos_md = INDEX.read_text()
    wiki = WIKI.read_text()
    readme = README.read_text()
    for name in pngs:
        assert name in nb, f"notebook missing {name}"
        assert name in demos_md, f"docs/demos.md missing {name}"
        assert name in wiki, f"wiki/Demos.md missing {name}"
        assert name in readme, f"README missing {name}"
    for blob in (nb, demos_md, wiki, readme):
        assert VIDEO in blob
    assert "The-Mailroom-Demos.ipynb" in readme
    assert "The-Mailroom-Demos.ipynb" in demos_md
