from tests.conftest import sample_payload


def test_full_flow(client, admin_headers):
    # 등록
    r = client.post("/api/quotes", json=sample_payload(), headers=admin_headers)
    assert r.status_code == 201
    q = r.json()
    assert q["mgmt_no"] == "26-A-001"
    assert q["status"] == "SUBMITTED"
    # 계산: 2 * 5,000,000 = 10,000,000 (절사 불필요), vat 1,000,000
    assert q["supply_amount"] == 10_000_000
    assert q["vat_amount"] == 1_000_000
    assert q["total_with_vat"] == 11_000_000

    qid = q["id"]

    # 목록 노출
    r = client.get("/api/quotes", headers=admin_headers)
    assert r.json()["total"] == 1

    # 상세
    assert client.get(f"/api/quotes/{qid}", headers=admin_headers).status_code == 200

    # 수정 (상태 유지)
    r = client.put(
        f"/api/quotes/{qid}",
        json=sample_payload(title="수정된 견적", items=[{"name": "품목", "qty": 1, "unit_price": 12_345_678}]),
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "수정된 견적"
    assert r.json()["status"] == "SUBMITTED"
    assert r.json()["supply_amount"] == 12_300_000  # 십만단위 절사
    assert r.json()["updated_at"] is not None

    # 승인
    assert client.post(f"/api/quotes/{qid}/approve", headers=admin_headers).status_code == 200

    # export
    assert client.get("/api/quotes/export.xlsx", headers=admin_headers).status_code == 200
    assert client.get(f"/api/quotes/{qid}/export.xlsx", headers=admin_headers).status_code == 200

    # 발송 (자리표시)
    r = client.post(f"/api/quotes/{qid}/send", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["message"] == "이메일 발송 기능은 준비 중입니다."

    # 삭제 → 목록에서 사라짐 + 결번
    assert client.delete(f"/api/quotes/{qid}", headers=admin_headers).status_code == 200
    assert client.get(f"/api/quotes/{qid}", headers=admin_headers).status_code == 404
    assert client.get("/api/quotes", headers=admin_headers).json()["total"] == 0

    # 다음 등록은 002 (001 결번)
    r = client.post("/api/quotes", json=sample_payload(), headers=admin_headers)
    assert r.json()["mgmt_no"] == "26-A-002"


def test_validation_rejects_zero_price(client, admin_headers):
    r = client.post(
        "/api/quotes",
        json=sample_payload(items=[{"name": "x", "qty": 1, "unit_price": 0}]),
        headers=admin_headers,
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_meta_endpoint(client, admin_headers):
    r = client.get("/api/meta", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert [g["code"] for g in body["groups"]] == ["A", "B", "C", "D", "E"]
    assert body["vat_rate"] == 0.1
    assert body["truncate_unit"] == 100_000
