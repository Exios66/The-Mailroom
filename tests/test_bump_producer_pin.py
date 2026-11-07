"""A-2: one command moves the producer pin and vendors the contract."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts import bump_producer_pin as bump

ROOT = Path(__file__).resolve().parents[1]
OLD = "a" * 40
NEW = "b" * 40


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
             "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin"},
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A tiny visualizer + pipeline pair wired into the script's paths."""
    vis = tmp_path / "vis"
    (vis / "mailroom_ui").mkdir(parents=True)
    (vis / "mailroom_ui" / "producer.py").write_text(
        f'MAILROOM_GIT_SHA = "{OLD}"\nMAILROOM_DIST_VERSION = "0.8.1"\n', encoding="utf-8"
    )
    (vis / "pyproject.toml").write_text(
        f'"mailroom @ git+https://github.com/Exios66/llm-mailroom.git@{OLD}",\n', encoding="utf-8"
    )
    (vis / "README.md").write_text(
        f"pin `@{OLD}` / **0.8.1**\nunrelated 0.8.1 line\nshort llm-mailroom @{OLD[:7]}\n",
        encoding="utf-8",
    )
    (vis / "CHANGELOG.md").write_text(f"- old pin {OLD}\n", encoding="utf-8")
    _git(vis, "init", "-q")
    _git(vis, "add", "-A")

    pipe = tmp_path / "pipe"
    (pipe / "contract").mkdir(parents=True)
    contract = json.loads((ROOT / "mailroom_ui/contract/mailroom-contract.json").read_text())
    (pipe / "contract" / "mailroom-contract.json").write_text(json.dumps(contract))
    _git(pipe, "init", "-q")
    _git(pipe, "add", "-A")
    _git(pipe, "commit", "-qm", "c")
    sha = _git(pipe, "rev-parse", "HEAD")

    monkeypatch.setattr(bump, "ROOT", vis)
    monkeypatch.setattr(bump, "PRODUCER", vis / "mailroom_ui" / "producer.py")
    monkeypatch.setattr(bump, "CONTRACT_DIR", vis / "mailroom_ui" / "contract")
    monkeypatch.setattr(bump, "CONTRACT_PATH", vis / "mailroom_ui" / "contract" / "mailroom-contract.json")
    monkeypatch.setattr(bump, "SOURCE_PATH", vis / "mailroom_ui" / "contract" / "source.json")
    return vis, pipe, sha


def test_bump_moves_every_reference_but_history(repo):
    vis, pipe, sha = repo
    assert bump.main([NEW, "--version", "0.9.2", "--contract-ref", sha, "--checkout", str(pipe)]) == 0
    producer = (vis / "mailroom_ui" / "producer.py").read_text()
    assert NEW in producer and 'MAILROOM_DIST_VERSION = "0.9.2"' in producer
    assert NEW in (vis / "pyproject.toml").read_text()
    readme = (vis / "README.md").read_text()
    assert f"`@{NEW}` / **0.9.2**" in readme
    assert "unrelated 0.8.1 line" in readme  # versions move only beside the SHA
    assert f"@{NEW[:7]}" in readme
    assert OLD in (vis / "CHANGELOG.md").read_text()  # history untouched

    source = json.loads((vis / "mailroom_ui/contract/source.json").read_text())
    assert source["pipeline_commit"] == sha
    assert source["matches_pin"] is False
    assert json.loads((vis / "mailroom_ui/contract/mailroom-contract.json").read_text())["graph"]


def test_contract_only_keeps_the_pin(repo):
    vis, pipe, sha = repo
    assert bump.main(["--contract-only", "--contract-ref", sha, "--checkout", str(pipe),
                      "--note", "provisional"]) == 0
    assert OLD in (vis / "mailroom_ui" / "producer.py").read_text()
    source = json.loads((vis / "mailroom_ui/contract/source.json").read_text())
    assert source["note"] == "provisional"


def test_check_flags_a_stale_short_sha(repo):
    vis, pipe, sha = repo
    assert bump.main(["--contract-only", "--contract-ref", sha, "--checkout", str(pipe),
                      "--note", "test"]) == 0
    stale = "959" + "bb0b"  # split so this file does not trip the repo-wide check
    (vis / "docs.md").write_text(f"mirrors llm-mailroom @{stale}\n", encoding="utf-8")
    _git(vis, "add", "docs.md")
    assert bump.main(["--check"]) == 1
    (vis / "docs.md").write_text(f"mirrors llm-mailroom @{OLD[:7]}\n", encoding="utf-8")
    assert bump.main(["--check"]) == 0


def test_check_flags_a_hand_edited_contract(repo):
    vis, pipe, sha = repo
    assert bump.main(["--contract-only", "--contract-ref", sha, "--checkout", str(pipe),
                      "--note", "test"]) == 0
    assert bump.verify_vendored() == []
    path = vis / "mailroom_ui/contract/mailroom-contract.json"
    path.write_text(path.read_text().replace('"judge"', '"judge2"'))
    assert any("edited by hand" in p for p in bump.verify_vendored())
    assert bump.main(["--check"]) == 1


def test_provisional_contract_needs_a_note(repo):
    vis, pipe, sha = repo
    assert bump.main(["--contract-only", "--contract-ref", sha, "--checkout", str(pipe)]) == 0
    assert any("no note" in p for p in bump.verify_vendored())


def test_check_flags_a_full_sha_that_only_shares_the_short_prefix(repo):
    vis, pipe, sha = repo
    assert bump.main(["--contract-only", "--contract-ref", sha, "--checkout", str(pipe),
                      "--note", "test"]) == 0
    lookalike = OLD[:7] + "c" * 33
    (vis / "docs.md").write_text(f"mirrors llm-mailroom @{lookalike}\n", encoding="utf-8")
    _git(vis, "add", "docs.md")
    assert bump.main(["--check"]) == 1


def test_failed_fetch_leaves_the_pin_alone(repo):
    vis, pipe, sha = repo
    with pytest.raises(subprocess.CalledProcessError):
        bump.main([NEW, "--version", "0.9.2", "--contract-ref", "no-such-ref",
                   "--checkout", str(pipe)])
    assert OLD in (vis / "mailroom_ui" / "producer.py").read_text()
    assert OLD in (vis / "pyproject.toml").read_text()
    assert not (vis / "mailroom_ui" / "contract" / "source.json").exists()


def test_rejects_a_short_sha(repo):
    with pytest.raises(SystemExit):
        bump.main(["abc1234"])


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_repository_names_one_pin():
    """A5: no non-history file names a different producer commit, and the
    vendored contract is byte-identical to what the bump fetched."""
    assert bump.stale_references(bump.current_pin()[0]) == []
    assert bump.verify_vendored() == []


def test_vendoring_preserves_the_fetched_contract_bytes(repo):
    vis, pipe, sha = repo
    expected = subprocess.run(
        ["git", "show", f"{sha}:contract/mailroom-contract.json"],
        cwd=pipe, check=True, capture_output=True,
    ).stdout
    assert bump.main([NEW, "--version", "0.9.2", "--contract-ref", sha,
                      "--checkout", str(pipe)]) == 0
    assert (vis / "mailroom_ui/contract/mailroom-contract.json").read_bytes() == expected
    source = json.loads((vis / "mailroom_ui/contract/source.json").read_text())
    import hashlib
    assert source["sha256"] == hashlib.sha256(expected).hexdigest()


@pytest.mark.parametrize("ref", ["main", "v0.9.1", "release/contract"])
def test_remote_symbolic_refs_record_resolved_commit_and_fetch_immutable_blob(repo, monkeypatch, ref):
    """A mutable ref is never stored as provenance or used for the blob fetch."""
    import io
    import urllib.parse

    vis, pipe, _ = repo
    expected = (pipe / "contract/mailroom-contract.json").read_bytes()
    urls = []

    def response(request, **kwargs):
        url = request if isinstance(request, str) else request.full_url
        urls.append(url)
        if len(urls) == 1:
            assert url.endswith("/commits/" + urllib.parse.quote(ref, safe=""))
            return io.BytesIO(json.dumps({"sha": NEW}).encode())
        assert url == bump.RAW_URL.format(ref=NEW)
        return io.BytesIO(expected)

    monkeypatch.setattr(bump.urllib.request, "urlopen", response)
    assert bump.main([NEW, "--version", "0.9.2", "--contract-ref", ref]) == 0
    assert len(urls) == 2
    source = json.loads((vis / "mailroom_ui/contract/source.json").read_text())
    assert source["pipeline_commit"] == NEW
    assert source["matches_pin"] is True
    assert source["fetched_from"] == bump.RAW_URL.format(ref=NEW)
    assert (vis / "mailroom_ui/contract/mailroom-contract.json").read_bytes() == expected
    assert bump.verify_vendored() == []


def test_remote_full_sha_needs_no_resolution(repo, monkeypatch):
    import io

    _, pipe, _ = repo
    expected = (pipe / "contract/mailroom-contract.json").read_bytes()
    urls = []

    def response(url, **kwargs):
        urls.append(url)
        assert url == bump.RAW_URL.format(ref=NEW)
        return io.BytesIO(expected)

    monkeypatch.setattr(bump.urllib.request, "urlopen", response)
    assert bump.fetch_contract(NEW, None) == (expected, NEW, bump.RAW_URL.format(ref=NEW))
    assert len(urls) == 1


def test_invalid_remote_resolution_leaves_pin_and_contract_untouched(repo, monkeypatch):
    import io

    vis, _, _ = repo
    urls = []

    def response(request, **kwargs):
        urls.append(request)
        return io.BytesIO(b'{"sha": "main"}')

    monkeypatch.setattr(bump.urllib.request, "urlopen", response)
    with pytest.raises(SystemExit, match="full commit SHA"):
        bump.main([NEW, "--version", "0.9.2", "--contract-ref", "main"])
    assert len(urls) == 1
    assert OLD in (vis / "mailroom_ui/producer.py").read_text()
    assert not (vis / "mailroom_ui/contract/mailroom-contract.json").exists()
    assert not (vis / "mailroom_ui/contract/source.json").exists()
