#!/usr/bin/env python3
"""Move the reviewed llm-mailroom pin and vendor its display contract.

One command replaces the hand edits that let the pin drift between files
(audit finding A5: code said one SHA, the CHANGELOG another, schema comments a
third). It does two things:

1. Rewrites the current full pin SHA (read from ``mailroom_ui/producer.py``)
   to the new SHA in every tracked file except history (CHANGELOG, release
   notes, ``.10x/``). On lines that carry the SHA it also rewrites the old
   package version, and it updates ``MAILROOM_DIST_VERSION``.
2. Copies ``contract/mailroom-contract.json`` from the pipeline at a ref into
   ``mailroom_ui/contract/mailroom-contract.json`` and records where it came
   from in ``mailroom_ui/contract/source.json``.

Usage::

    # move the pin and vendor the contract from the same commit
    python scripts/bump_producer_pin.py <sha> --version 0.9.2 --checkout ../llm-mailroom

    # vendor the contract only (e.g. from an open PR head), pin unchanged
    python scripts/bump_producer_pin.py --contract-only --contract-ref <ref> --checkout ../llm-mailroom

    # CI / tests: fail on a stale pin reference or a hand-edited contract
    python scripts/bump_producer_pin.py --check

Without ``--checkout`` the contract is fetched from raw.githubusercontent.com.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "mailroom_ui" / "producer.py"
CONTRACT_DIR = ROOT / "mailroom_ui" / "contract"
CONTRACT_PATH = CONTRACT_DIR / "mailroom-contract.json"
SOURCE_PATH = CONTRACT_DIR / "source.json"
CONTRACT_IN_PIPELINE = "contract/mailroom-contract.json"
RAW_URL = "https://raw.githubusercontent.com/Exios66/llm-mailroom/{ref}/" + CONTRACT_IN_PIPELINE

# History is allowed to name old pins; everything else must name the current one.
HISTORY = ("CHANGELOG.md", "docs/releases.md", "wiki/Releases.md", ".10x/")
SKIP_SUFFIXES = (".png", ".jpg", ".gif", ".webp", ".ico", ".woff", ".woff2", ".lock")

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PIN_RE = re.compile(r'^MAILROOM_GIT_SHA = "([0-9a-f]{40})"', re.M)
_VER_RE = re.compile(r'^MAILROOM_DIST_VERSION = "([^"]+)"', re.M)


def current_pin() -> tuple[str, str]:
    text = PRODUCER.read_text(encoding="utf-8")
    sha = _PIN_RE.search(text)
    ver = _VER_RE.search(text)
    if not sha or not ver:
        raise SystemExit("could not read MAILROOM_GIT_SHA / MAILROOM_DIST_VERSION from producer.py")
    return sha.group(1), ver.group(1)


def _tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.decode()
    files = []
    for rel in filter(None, out.split("\0")):
        if rel.startswith(HISTORY) or rel.endswith(SKIP_SUFFIXES):
            continue
        path = ROOT / rel
        if path.is_file():
            files.append(path)
    return files


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def stale_references(pin: str) -> list[str]:
    """Non-history lines naming an old pin form (short or full) of a mailroom SHA."""
    pattern = re.compile(r"llm-mailroom(?:\.git)? ?@ ?([0-9a-f]{7,40})|mailroom`? `?@ ?`?([0-9a-f]{7,40})")
    bad = []
    for path in _tracked_files():
        text = _read(path)
        if text is None:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for match in pattern.finditer(line):
                ref = match.group(1) or match.group(2)
                if not pin.startswith(ref):  # any prefix of the pin, short or full
                    bad.append(f"{path.relative_to(ROOT)}:{lineno}: {ref}")
    return bad


def move_pin(old: str, new: str, old_ver: str, new_ver: str | None) -> list[Path]:
    changed = []
    for path in _tracked_files():
        text = _read(path)
        if text is None or (old not in text and old[:7] not in text):
            continue
        lines = []
        for line in text.splitlines(keepends=True):
            if old in line or old[:7] in line:
                line = line.replace(old, new).replace(old[:7], new[:7])
                if new_ver and old_ver != new_ver:
                    line = re.sub(rf"(?<![\w.]){re.escape(old_ver)}(?![\w])", new_ver, line)
            lines.append(line)
        updated = "".join(lines)
        if path == PRODUCER and new_ver:
            updated = _VER_RE.sub(f'MAILROOM_DIST_VERSION = "{new_ver}"', updated)
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(path)
    return changed


def fetch_contract(ref: str, checkout: Path | None) -> tuple[bytes, str, str]:
    if checkout is not None:
        sha = subprocess.run(
            ["git", "rev-parse", f"{ref}^{{commit}}"], cwd=checkout, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
        blob = subprocess.run(
            ["git", "show", f"{sha}:{CONTRACT_IN_PIPELINE}"], cwd=checkout, check=True,
            capture_output=True,
        ).stdout
        return blob, sha, f"git checkout ({checkout.name})"
    url = RAW_URL.format(ref=ref)
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 - fixed host
        blob = resp.read()
    return blob, ref, url


def load_contract(ref: str, checkout: Path | None) -> tuple[dict, bytes, str, str]:
    """Fetch and validate the contract at ``ref``; writes nothing."""
    blob, sha, origin = fetch_contract(ref, checkout)
    contract = json.loads(blob)
    if "contract_version" not in contract or "graph" not in contract:
        raise SystemExit("fetched file is not a mailroom display contract")
    return contract, blob, sha, origin


def vendor_contract(fetched: tuple[dict, bytes, str, str], pin: str, note: str | None) -> dict:
    """Write a contract from ``load_contract`` and its provenance."""
    contract, body, sha, origin = fetched
    CONTRACT_DIR.mkdir(parents=True, exist_ok=True)
    # Provenance identifies the producer's actual blob, including whitespace.
    CONTRACT_PATH.write_bytes(body)
    source = {
        "sha256": hashlib.sha256(body).hexdigest(),
        "pipeline_commit": sha,
        "pipeline_version": contract.get("pipeline_version"),
        "contract_version": contract["contract_version"],
        "fetched_from": origin,
        "matches_pin": sha == pin,
    }
    if note:
        source["note"] = note
    SOURCE_PATH.write_text(json.dumps(source, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return source


def contract_digest() -> str:
    return hashlib.sha256(CONTRACT_PATH.read_bytes()).hexdigest()


def verify_vendored() -> list[str]:
    """Offline: the vendored contract is byte-identical to what was fetched."""
    problems = []
    if not SOURCE_PATH.exists() or not CONTRACT_PATH.exists():
        return ["no vendored contract; run bump_producer_pin.py"]
    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    if source.get("sha256") != contract_digest():
        problems.append("mailroom-contract.json was edited by hand; re-run bump_producer_pin.py")
    pin, _ = current_pin()
    if source.get("pipeline_commit") != pin and not source.get("note"):
        problems.append("contract comes from another commit than the pin and has no note")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sha", nargs="?", help="new 40-char llm-mailroom commit")
    parser.add_argument("--version", help="package version at that commit (e.g. 0.9.2)")
    parser.add_argument("--checkout", type=Path, help="local llm-mailroom checkout to read the contract from")
    parser.add_argument("--contract-ref", help="ref to vendor the contract from (default: the pin)")
    parser.add_argument("--contract-only", action="store_true", help="vendor the contract, leave the pin")
    parser.add_argument("--note", help="free-text provenance note stored in source.json")
    parser.add_argument("--check", action="store_true", help="report stale pin references and exit")
    args = parser.parse_args(argv)

    old, old_ver = current_pin()

    if args.check:
        bad = [f"stale pin: {line}" for line in stale_references(old)] + verify_vendored()
        for line in bad:
            print(line)
        return 1 if bad else 0

    pin = old
    if not args.contract_only:
        if not args.sha or not _SHA_RE.match(args.sha):
            parser.error("a full 40-char commit SHA is required (or pass --contract-only)")
        pin = args.sha

    # Fetch before writing anything, so a failed fetch leaves the old pin and
    # the old contract together instead of a new pin beside a stale contract.
    fetched = load_contract(args.contract_ref or pin, args.checkout)
    if pin != old:
        for path in move_pin(old, pin, old_ver, args.version):
            print(f"pin moved: {path.relative_to(ROOT)}")
    source = vendor_contract(fetched, pin, args.note)
    print(f"contract vendored from {source['pipeline_commit']} ({source['fetched_from']})")
    if not source["matches_pin"]:
        print("warning: vendored contract does not come from the pinned commit", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
