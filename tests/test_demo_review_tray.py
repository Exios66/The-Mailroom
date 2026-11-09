"""Fake llm-mailroom producer + working REVIEW-tray demo."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.fake_producer import DEMO_TOKEN, FakeProducerStore, create_fake_producer


def _auth():
    return {"Authorization": f"Bearer {DEMO_TOKEN}"}


def test_fake_producer_v1_lookup_and_resolve():
    store = FakeProducerStore()
    with TestClient(create_fake_producer(store)) as c:
        assert c.get("/v1/health").json()["status"] == "ok"
        r = c.get("/v1/lookup", params={"trace_id": "tray-review"}, headers=_auth())
        assert r.status_code == 200
        doc = r.json()["document"]
        assert doc["doc_id"] == "doc-merger-42"
        assert doc["original_filename"].endswith(".pdf")
        assert "extracted_data" in doc
        assert c.get("/v1/documents/doc-merger-42/source", headers=_auth()).status_code == 404
        posted = c.post(
            "/v1/review/doc-merger-42/resolve",
            headers=_auth(),
            json={
                "decision": "approved",
                "disposition": "resume",
                "override_doc_type": "merger_agreement",
                "notes": "ok",
            },
        )
        assert posted.status_code == 200, posted.text
        body = posted.json()
        assert body["disposition"] == "resume"
        assert body["resume"]["doc_type"] == "merger_agreement"


def test_fake_producer_complete_requires_extracted_data():
    store = FakeProducerStore()
    store.documents["doc-claim-fnol"]["extracted_data"] = {}
    with TestClient(create_fake_producer(store)) as c:
        missing = c.post(
            "/v1/review/doc-claim-fnol/resolve",
            headers=_auth(),
            json={"decision": "approved", "disposition": "complete"},
        )
        assert missing.status_code == 400
        ok = c.post(
            "/v1/review/doc-claim-fnol/resolve",
            headers=_auth(),
            json={
                "decision": "approved",
                "disposition": "complete",
                "extracted_data": {
                    "claim_number": "CL-4419",
                    "coverage_determination": "approved",
                },
            },
        )
        assert ok.status_code == 200
        assert ok.json()["disposition"] == "complete"
        assert store.documents["doc-claim-fnol"]["stage"] == "archived"


def test_fake_producer_complete_rejects_foreign_specialist_fields():
    store = FakeProducerStore()
    with TestClient(create_fake_producer(store)) as c:
        bad = c.post(
            "/v1/review/doc-merger-42/resolve",
            headers=_auth(),
            json={
                "decision": "approved",
                "disposition": "complete",
                "extracted_data": {"sender": "A Corp", "parties": ["A", "B"]},
            },
        )
        assert bad.status_code == 400
        assert "another specialist" in (bad.json().get("detail") or bad.text)


def test_fake_producer_record_on_reconsider():
    with TestClient(create_fake_producer()) as c:
        r = c.post(
            "/v1/review/doc-claim-miss/resolve",
            headers=_auth(),
            json={"decision": "approved", "disposition": "record", "notes": "paper"},
        )
        assert r.status_code == 200
        audit = c.get("/v1/audit/doc-claim-miss", headers=_auth()).json()
        assert audit["count"] >= 1


def test_demo_review_tray_check_mode(capsys):
    import sys
    import scripts.demo_review_tray as mod

    old = sys.argv
    sys.argv = ["demo_review_tray.py", "--check"]
    try:
        mod.main()
    finally:
        sys.argv = old
    out = capsys.readouterr().out
    assert "check ok" in out
    assert "tray-review" in out
    assert "doc-merger-42" in out
    assert "doc-claim-fnol" in out


def test_demo_review_tray_check_api(capsys):
    import sys
    import scripts.demo_review_tray as mod

    old = sys.argv
    sys.argv = ["demo_review_tray.py", "--check-api"]
    try:
        mod.main()
    finally:
        sys.argv = old
    out = capsys.readouterr().out
    assert "check-api ok" in out
    assert "complete" in out


def test_fake_producer_complete_uses_parked_extraction():
    store = FakeProducerStore()
    parked = {
        k: v for k, v in store.documents["doc-claim-fnol"]["extracted_data"].items()
        if not str(k).startswith("_")
    }
    with TestClient(create_fake_producer(store)) as client:
        response = client.post(
            "/v1/review/doc-claim-fnol/resolve", headers=_auth(),
            json={"decision": "approved", "disposition": "complete"},
        )
    assert response.status_code == 200
    row = store.documents["doc-claim-fnol"]
    assert row["stage"] == "archived"
    # The approved fields are kept verbatim; the archived row also carries the
    # derived report block (llm-mailroom PR #203 archives through the tail).
    assert {k: v for k, v in row["extracted_data"].items() if not str(k).startswith("_")} == parked
    assert row["extracted_data"]["_report"]["status"] == "ok"


def test_fake_producer_approve_as_is_archives_the_reviewed_fields():
    """PR #203: approving archives the parked fields through the tail instead
    of re-extracting, and the confidence stays the model's own number."""
    store = FakeProducerStore()
    parked = {
        k: v for k, v in store.documents["doc-merger-42"]["extracted_data"].items()
        if not str(k).startswith("_")
    }
    model_conf = store.documents["doc-merger-42"]["extraction_confidence"]
    with TestClient(create_fake_producer(store)) as client:
        response = client.post(
            "/v1/review/doc-merger-42/resolve", headers=_auth(),
            json={"resolution": "approve_as_is", "reviewer": "j.burleson"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["resolution"] == "approve_as_is"
    assert body["complete"]["stage"] == "archived"
    assert body["complete"]["extraction_source"] == "human"
    assert body["complete"]["extraction_confidence"] == model_conf != 1.0
    assert body["human_label"]["reviewer"] == "j.burleson"
    row = store.documents["doc-merger-42"]
    assert row["stage"] == "archived"
    assert row["human_label"]["resolution"] == "approve_as_is"
    assert {k: v for k, v in row["extracted_data"].items() if not str(k).startswith("_")} == parked
    # Reviewer evidence travels with the archived row.
    assert row["extracted_data"]["_review"]["review_causes"]


def test_fake_producer_correct_merges_field_corrections():
    store = FakeProducerStore()
    with TestClient(create_fake_producer(store)) as client:
        response = client.post(
            "/v1/review/doc-merger-42/resolve", headers=_auth(),
            json={"resolution": "correct", "field_corrections": {"indemnification": "capped"}},
        )
    assert response.status_code == 200, response.text
    applied = store.documents["doc-merger-42"]["extracted_data"]
    assert applied["indemnification"] == "capped"
    assert applied["consideration"] == "all-stock"  # untouched parked field


def test_fake_producer_reject_needs_a_reason():
    store = FakeProducerStore()
    with TestClient(create_fake_producer(store)) as client:
        missing = client.post(
            "/v1/review/doc-merger-42/resolve", headers=_auth(),
            json={"resolution": "reject"},
        )
        assert missing.status_code == 400
        assert "reject_reason" in missing.text
        ok = client.post(
            "/v1/review/doc-merger-42/resolve", headers=_auth(),
            json={"resolution": "reject", "reject_reason": "duplicate"},
        )
    assert ok.status_code == 200, ok.text
    assert store.documents["doc-merger-42"]["stage"] == "failed"
    assert store.documents["doc-merger-42"]["reject_reason"] == "duplicate"


def test_fake_producer_racing_resolve_is_409():
    store = FakeProducerStore()
    store.inflight.add("doc-merger-42")
    with TestClient(create_fake_producer(store)) as client:
        response = client.post(
            "/v1/review/doc-merger-42/resolve", headers=_auth(),
            json={"resolution": "approve_as_is"},
        )
    assert response.status_code == 409
    assert "already in progress" in response.text


def test_fake_producer_complete_that_never_archived_reports_a_warning():
    """A tail that re-parks keeps the decision but not the completion."""
    store = FakeProducerStore()
    store.archive_fails = True
    with TestClient(create_fake_producer(store)) as client:
        response = client.post(
            "/v1/review/doc-claim-fnol/resolve", headers=_auth(),
            json={"decision": "approved", "disposition": "complete"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["complete"]["stage"] == "review"
    assert "did not reach the archive" in body["warning"]
    assert store.documents["doc-claim-fnol"]["stage"] == "review"


def test_fake_producer_review_entered_at_is_serialized():
    store = FakeProducerStore()
    entered = store.documents["doc-merger-42"]["review_entered_at"]
    with TestClient(create_fake_producer(store)) as client:
        doc = client.get(
            "/v1/lookup", params={"doc_id": "doc-merger-42"}, headers=_auth(),
        ).json()["document"]
    assert doc["review_entered_at"] == entered


def test_fake_producer_mirrors_resolution_contract():
    from mailroom_ui.producer import REJECT_REASONS, RESOLUTIONS

    assert RESOLUTIONS == frozenset({"approve_as_is", "correct", "reclassify", "reject"})
    assert "not_a_legal_document" in REJECT_REASONS


def test_resolve_refuses_extracted_data_with_resume_resolution():
    """llm-mailroom #203 refuses a posted ``extracted_data`` with any resolution,
    resume included (``src/api/main.py``); the fake producer must agree."""
    with TestClient(create_fake_producer(FakeProducerStore())) as c:
        for disposition in ("resume", "complete"):
            refused = c.post(
                "/v1/review/doc-claim-fnol/resolve",
                headers=_auth(),
                json={
                    "disposition": disposition,
                    "resolution": "approve_as_is",
                    "extracted_data": {"claim_number": "CL-1"},
                },
            )
            assert refused.status_code == 400, disposition
            assert (
                "extracted_data is not used with a resolution (disposition=resume or complete)"
                in refused.json()["detail"]
            )
