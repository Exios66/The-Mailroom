#!/usr/bin/env python3
"""Mirror the Lucius-Morningstar/docclass-pilot HF dataset INTO Langfuse.

Creates/updates the Langfuse dataset `docclass-pilot` (the pilot-run default
corpus) so pipeline runs can execute against it as a managed eval dataset:

- config `default`      -> item input  {filename, prompt, metadata}
- config `ground_truth` -> item expected_output {expected, expected_subclass,
  claim fields, ...}

Rows are joined on filename across the two configs. Items are upserted
(deterministic ids derived from filename), so re-running only refreshes.
Rows are read via the HF datasets-server REST API — no huggingface_hub dep.

Usage:
    python scripts/sync_pilot_dataset.py            # full sync
    python scripts/sync_pilot_dataset.py --dry-run  # counts only, no writes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

DATASET_ID = "Lucius-Morningstar/docclass-pilot"
LF_DATASET_NAME = "docclass-pilot"
ROWS_API = "https://datasets-server.huggingface.co/rows"


def _get_json(url: str, tries: int = 3) -> dict:
    last: Exception | None = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # transient HF hiccups are common
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"HF fetch failed after {tries} tries: {url}: {last}")


def _rows(config: str, split: str) -> list[dict]:
    out: list[dict] = []
    offset = 0
    while True:
        url = f"{ROWS_API}?dataset={urllib.parse.quote(DATASET_ID, safe='')}" \
              f"&config={config}&split={split}&offset={offset}&length=100"
        page = _get_json(url)
        rows = page.get("rows") or []
        if not rows:
            break
        out.extend(r["row"] for r in rows)
        if len(rows) < 100:
            break
        offset += len(rows)
    return out


def _item_id(filename: str) -> str:
    return "dcp-" + hashlib.sha1(filename.encode()).hexdigest()[:24]


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync docclass-pilot into Langfuse datasets.")
    parser.add_argument("--dry-run", action="store_true", help="Count rows without writing.")
    args = parser.parse_args()

    default_rows = _rows("default", "train") + _rows("default", "test")
    gt_rows = _rows("ground_truth", "train") + _rows("ground_truth", "test")
    gt_by_file = {r["filename"]: r for r in gt_rows}

    print(f"{DATASET_ID}: {len(default_rows)} default rows, "
          f"{len(gt_rows)} ground-truth rows, "
          f"{sum(1 for r in default_rows if r['filename'] in gt_by_file)} joined")

    unmatched = [r["filename"] for r in default_rows if r["filename"] not in gt_by_file]
    if unmatched:
        print(f"  WARNING: {len(unmatched)} default rows without ground truth: "
              f"{unmatched[:5]}{'…' if len(unmatched) > 5 else ''}")

    if args.dry_run:
        print("dry run — nothing written")
        return 0

    missing = [k for k in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY") if not os.environ.get(k)]
    if missing:
        sys.exit(f"missing env vars: {', '.join(missing)} (copy .env.example -> .env and fill in)")
    from langfuse import Langfuse

    client = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com"),
    )
    try:
        client.auth_check()
    except Exception as exc:
        sys.exit(f"Langfuse rejected the configured credentials ({str(exc)[:120]}).")

    dataset = client.create_dataset(
        name=LF_DATASET_NAME,
        description="Pilot corpus mirrored from Lucius-Morningstar/docclass-pilot "
                    "(configs: default + ground_truth). Valid doc classes: contract, "
                    "merger_agreement, corporate_record, correspondence, insurance_claim.",
        metadata={"source": f"https://huggingface.co/datasets/{DATASET_ID}",
                  "sync": "scripts/sync_pilot_dataset.py"},
    )

    created = updated = skipped = 0
    known_items: dict[str, object] = {}
    try:
        ds_client = client.get_dataset(LF_DATASET_NAME)
        for item in getattr(ds_client, "items", []) or []:
            sig = getattr(item, "id", None)
            if sig:
                known_items[sig] = item
    except Exception:
        pass

    for row in default_rows:
        fn = row["filename"]
        gt = gt_by_file.get(fn) or {}
        item_input = {"filename": fn, "prompt": row.get("prompt"),
                      "metadata": row.get("metadata")}
        expected_output = {k: v for k, v in gt.items()
                           if k != "filename" and v not in (None, "", [])} or None
        iid = _item_id(fn)
        if iid in known_items:
            skipped += 1
            continue
        client.create_dataset_item(
            dataset_name=LF_DATASET_NAME,
            id=iid,
            input=item_input,
            expected_output=expected_output,
            metadata={"subclass": gt.get("expected_subclass"),
                      "hf_split": gt.get("split")},
        )
        created += 1

    client.flush()
    print(f"dataset '{LF_DATASET_NAME}' ({dataset.id}): "
          f"{created} items added, {skipped} already present")
    host = os.environ.get("LANGFUSE_HOST", "https://us.cloud.langfuse.com").rstrip("/")
    print(f"Dataset live at {host}/datasets/{LF_DATASET_NAME}")
    client.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
