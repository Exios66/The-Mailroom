"""What a REVIEW-desk click sends (web/js/review_plan.js), checked against the
llm-mailroom resolve contract (``pipeline/review_resolve.py:plan_resolution``).

The planner is a pure, DOM-free module shared by the pixel console and the
hosted Observatory (same pattern as ``bert_panels.js``): node evaluates it, no
browser needed. Skipped when node is not on PATH; the static wiring tests
always run.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MODULE = ROOT / "web" / "js" / "review_plan.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node not on PATH")

PARKED = {"parties": ["A", "B"], "consideration": "all-stock", "indemnification": None}


def _js(expr: str):
    code = (
        f"const P = require({json.dumps(str(MODULE))});\n"
        f"process.stdout.write(JSON.stringify({expr}));"
    )
    res = subprocess.run([NODE, "-e", code], capture_output=True, text=True, timeout=30)
    assert res.returncode == 0, f"node failed:\n{res.stdout}\n{res.stderr}"
    return json.loads(res.stdout)


def _plan(**kw):
    base = {
        "resolution": "",
        "disposition": "resume",
        "docType": "merger_agreement",
        "docSubclass": "",
        "baseType": "merger_agreement",
        "baseSub": "",
        "rawExtracted": "",
        "parkedRaw": json.dumps(PARKED),
    }
    base.update(kw)
    return _js(f"P.plan({json.dumps(base)})")


def _edited(**fields):
    return json.dumps({**PARKED, **fields})


# ---- wiring (always runs) -------------------------------------------------

def test_both_desks_load_and_use_the_shared_planner():
    web = (ROOT / "web" / "js" / "api.js").read_text(encoding="utf-8")
    hosted = (ROOT / "hosted" / "js" / "app.js").read_text(encoding="utf-8")
    for src in (web, hosted):
        assert "ReviewPlan.plan(" in src
        assert "function fieldEdits" not in src  # one copy, in review_plan.js
    assert "review_plan.js" in (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "review_plan.js" in (ROOT / "hosted" / "index.html").read_text(encoding="utf-8")


def test_both_desks_hand_the_form_to_onDone():
    """The status the producer warning rides on is saved per form; both desks must
    pass ``form`` (the hosted desk used to call ``onDone(result)``)."""
    for rel in ("web/js/api.js", "hosted/js/app.js"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert 'onDone(result, form)' in src, rel
        assert "onDone(result);" not in src, rel


def test_planner_module_is_pure():
    src = MODULE.read_text(encoding="utf-8")
    for needle in ("document.", "fetch(", "XMLHttpRequest", "localStorage"):
        assert needle not in src
    assert "module.exports" in src


# ---- Correct --------------------------------------------------------------

@needs_node
def test_correct_sends_only_the_changed_fields():
    out = _plan(resolution="correct", rawExtracted=_edited(indemnification="capped"))
    assert out == {
        "resolution": "correct",
        "corrections": {"indemnification": "capped"},
        "extractedData": json.loads(_edited(indemnification="capped")),
    }


@needs_node
def test_correct_with_complete_disposition_still_sends_resolution_and_corrections():
    """Finding 1: the producer merges field_corrections under resolution=correct
    for disposition=complete too, so the desk sends exactly that (and the planner
    never adds extracted_data to a resolution; the caller drops it)."""
    out = _plan(
        resolution="correct", disposition="complete",
        rawExtracted=_edited(indemnification="capped"),
    )
    assert out["resolution"] == "correct"
    assert out["corrections"] == {"indemnification": "capped"}


@needs_node
def test_correct_without_edits_is_refused():
    out = _plan(resolution="correct", rawExtracted=json.dumps(PARKED))
    assert "No field changes" in out["error"]
    assert _plan(resolution="correct", rawExtracted="")["error"].startswith("No field changes")


@needs_node
def test_removed_keys_travel_as_null_corrections():
    """Finding 3: field_corrections MERGE over the parked fields, so a key the
    reviewer deleted must be sent as an explicit null or it survives."""
    edited = {k: v for k, v in PARKED.items() if k != "consideration"}
    out = _plan(resolution="correct", rawExtracted=json.dumps(edited))
    assert out["corrections"] == {"consideration": None}


@needs_node
def test_removing_an_already_empty_field_is_not_an_edit():
    edited = {k: v for k, v in PARKED.items() if k != "indemnification"}
    out = _plan(resolution="correct", rawExtracted=json.dumps(edited))
    assert "No field changes" in out["error"]


@needs_node
def test_blank_textarea_never_means_delete_everything():
    assert _js('P.fieldEdits({"a": 1}, undefined)') == {}
    assert _js('P.fieldEdits({"a": 1}, null)') == {}


@needs_node
def test_underscore_keys_are_producer_bookkeeping_and_never_sent():
    out = _js('P.fieldEdits({"a": 1, "_review": {"x": 1}}, {"a": 1, "_report": {}})')
    assert out == {}


@needs_node
def test_no_parked_snapshot_sends_every_field_as_a_correction():
    out = _plan(resolution="correct", parkedRaw="", rawExtracted='{"consideration": "cash"}')
    assert out["corrections"] == {"consideration": "cash"}


# ---- class change ---------------------------------------------------------

@needs_node
def test_correct_after_a_class_change_is_reclassify():
    """Finding 2: the producer refuses resolution=correct with a new doc_type
    ("use resolution=reclassify"), and reclassify takes no field_corrections."""
    out = _plan(resolution="correct", docType="contract", rawExtracted=json.dumps(PARKED))
    assert out["resolution"] == "reclassify"
    assert out.get("corrections") is None


@needs_node
def test_correct_after_a_subclass_change_is_reclassify():
    out = _plan(resolution="correct", docSubclass="all_stock", rawExtracted=json.dumps(PARKED))
    assert out["resolution"] == "reclassify"


@needs_node
def test_approve_as_is_after_a_class_change_is_reclassify_even_with_blank_json():
    out = _plan(resolution="approve_as_is", docType="contract")
    assert out["resolution"] == "reclassify"
    assert out.get("corrections") is None


@needs_node
def test_field_edits_with_a_class_change_are_refused_not_dropped():
    out = _plan(
        resolution="correct", docType="contract",
        rawExtracted=_edited(indemnification="capped"),
    )
    assert "class changed" in out["error"]


# ---- the other buttons ----------------------------------------------------

@needs_node
def test_approve_as_is_with_an_edited_textarea_becomes_a_correction():
    out = _plan(resolution="approve_as_is", rawExtracted=_edited(consideration="cash"))
    assert out["resolution"] == "correct"
    assert out["corrections"] == {"consideration": "cash"}


@needs_node
def test_approve_as_is_untouched_stays_approve_as_is():
    out = _plan(resolution="approve_as_is", rawExtracted=json.dumps(PARKED))
    assert out["resolution"] == "approve_as_is"
    assert out.get("corrections") is None


@needs_node
def test_legacy_complete_posts_the_full_object_and_no_resolution():
    """No resolution: extracted_data is a FULL replacement (the only true delete)."""
    out = _plan(disposition="complete", rawExtracted='{"consideration": "cash"}')
    assert out["resolution"] == ""
    assert out.get("corrections") is None
    assert out["extractedData"] == {"consideration": "cash"}


@needs_node
def test_legacy_complete_needs_a_json_object():
    assert "Complete needs" in _plan(disposition="complete", rawExtracted="")["error"]
    assert "not valid JSON" in _plan(disposition="complete", rawExtracted="{")["error"]
    assert "must be a JSON object" in _plan(disposition="complete", rawExtracted="[1]")["error"]


@needs_node
def test_reextract_and_reject_pass_through():
    for res in ("", "reject"):
        out = _plan(resolution=res)
        assert out["resolution"] == res
        assert out.get("corrections") is None
