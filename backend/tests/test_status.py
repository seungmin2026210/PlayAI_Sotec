from tests.conftest import sample_payload


def _create(client, headers, **over):
    r = client.post("/api/quotes", json=sample_payload(**over), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_submitted_then_approve(client, admin_headers):
    q = _create(client, admin_headers)
    r = client.post(f"/api/quotes/{q['id']}/approve", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "APPROVED"
    assert body["approved_at"] is not None


def test_reject_requires_reason(client, admin_headers):
    q = _create(client, admin_headers)
    r = client.post(f"/api/quotes/{q['id']}/reject", json={"reason": "  "}, headers=admin_headers)
    assert r.status_code == 422


def test_reject_stores_reason_and_is_read_only(client, admin_headers):
    q = _create(client, admin_headers)
    r = client.post(f"/api/quotes/{q['id']}/reject", json={"reason": "예산 초과"}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "REJECTED"
    assert r.json()["reject_reason"] == "예산 초과"

    # 반려됨은 읽기전용 보존 → 수정 불가
    r2 = client.put(f"/api/quotes/{q['id']}", json=sample_payload(title="바뀜"), headers=admin_headers)
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "INVALID_TRANSITION"


def test_approved_cannot_be_rejected(client, admin_headers):
    q = _create(client, admin_headers)
    client.post(f"/api/quotes/{q['id']}/approve", headers=admin_headers)
    r = client.post(f"/api/quotes/{q['id']}/reject", json={"reason": "x"}, headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "INVALID_TRANSITION"


def test_approved_cannot_be_cancelled(client, admin_headers):
    q = _create(client, admin_headers)
    client.post(f"/api/quotes/{q['id']}/approve", headers=admin_headers)
    r = client.post(f"/api/quotes/{q['id']}/cancel", headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "INVALID_TRANSITION"


def test_approved_is_read_only(client, admin_headers):
    q = _create(client, admin_headers)
    r = client.post(f"/api/quotes/{q['id']}/approve", headers=admin_headers)
    assert r.json()["read_only"] is True

    # 승인됨은 읽기전용 보존 → 수정/삭제 불가
    r2 = client.put(f"/api/quotes/{q['id']}", json=sample_payload(title="바뀜"), headers=admin_headers)
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "INVALID_TRANSITION"

    r3 = client.delete(f"/api/quotes/{q['id']}", headers=admin_headers)
    assert r3.status_code == 409
    assert r3.json()["detail"]["code"] == "INVALID_TRANSITION"


def test_export_requires_approved(client, admin_headers):
    q = _create(client, admin_headers)

    for call in (
        lambda: client.get(f"/api/quotes/{q['id']}/export.xlsx", headers=admin_headers),
        lambda: client.get(f"/api/quotes/{q['id']}/export.pdf", headers=admin_headers),
    ):
        resp = call()
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "EXPORT_NOT_APPROVED"

    client.post(f"/api/quotes/{q['id']}/approve", headers=admin_headers)
    r = client.get(f"/api/quotes/{q['id']}/export.xlsx", headers=admin_headers)
    assert r.status_code == 200


def test_purchase_lock_blocks_mutation(client, admin_headers):
    q = _create(client, admin_headers)
    r = client.post(f"/api/quotes/{q['id']}/purchase-lock", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["purchase_locked"] is True
    assert r.json()["read_only"] is True

    for call in (
        lambda: client.put(f"/api/quotes/{q['id']}", json=sample_payload(), headers=admin_headers),
        lambda: client.delete(f"/api/quotes/{q['id']}", headers=admin_headers),
        lambda: client.post(f"/api/quotes/{q['id']}/cancel", headers=admin_headers),
    ):
        resp = call()
        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "PURCHASE_LOCKED"


def test_purchase_lock_is_idempotent(client, admin_headers):
    q = _create(client, admin_headers)
    client.post(f"/api/quotes/{q['id']}/purchase-lock", headers=admin_headers)
    r = client.post(f"/api/quotes/{q['id']}/purchase-lock", headers=admin_headers)
    assert r.status_code == 200
