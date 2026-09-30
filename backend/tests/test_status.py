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


# --------------------------------------------------------------------------- 종결(PURCHASE-1)
def test_close_requires_approved(client, admin_headers):
    q = _create(client, admin_headers)  # SUBMITTED 상태
    r = client.post(f"/api/quotes/{q['id']}/close", headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "INVALID_TRANSITION"


def test_close_approved_quote(client, admin_headers):
    q = _create(client, admin_headers)
    client.post(f"/api/quotes/{q['id']}/approve", headers=admin_headers)

    r = client.post(f"/api/quotes/{q['id']}/close", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "CLOSED"
    assert body["status_label"] == "종결"
    assert body["closed_at"] is not None
    assert body["read_only"] is True  # 이미 승인됨이라 원래 읽기전용


def test_closed_quote_hidden_from_default_list_but_findable_by_status(client, admin_headers):
    q = _create(client, admin_headers)
    client.post(f"/api/quotes/{q['id']}/approve", headers=admin_headers)
    client.post(f"/api/quotes/{q['id']}/close", headers=admin_headers)

    default_list = client.get("/api/quotes", headers=admin_headers).json()
    assert q["id"] not in [x["id"] for x in default_list["items"]]

    closed_list = client.get("/api/quotes?status=CLOSED", headers=admin_headers).json()
    assert q["id"] in [x["id"] for x in closed_list["items"]]


def test_close_still_exportable(client, admin_headers):
    """CLOSED 는 승인 문서 자체는 그대로라 계속 export 가능해야 한다."""
    q = _create(client, admin_headers)
    client.post(f"/api/quotes/{q['id']}/approve", headers=admin_headers)
    client.post(f"/api/quotes/{q['id']}/close", headers=admin_headers)

    r = client.get(f"/api/quotes/{q['id']}/export.xlsx", headers=admin_headers)
    assert r.status_code == 200


def test_closed_quote_cannot_close_again(client, admin_headers):
    q = _create(client, admin_headers)
    client.post(f"/api/quotes/{q['id']}/approve", headers=admin_headers)
    client.post(f"/api/quotes/{q['id']}/close", headers=admin_headers)

    r = client.post(f"/api/quotes/{q['id']}/close", headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "INVALID_TRANSITION"


def test_group_manager_cannot_close(client, admin_headers, manager_headers):
    q = _create(client, admin_headers)
    client.post(f"/api/quotes/{q['id']}/approve", headers=admin_headers)

    r = client.post(f"/api/quotes/{q['id']}/close", headers=manager_headers)
    assert r.status_code == 403
