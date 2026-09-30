"""구매관리(PURCHASE-1) — 상품 마스터 · 유닛 등록/채번/폐기/견적잠금 · 권한.

specs/PURCHASE-1/DECISIONS.md 의 결정 사항을 코드 레벨에서 검증한다.
"""
from __future__ import annotations

from .conftest import sample_payload


def _create_product(client, admin_headers, **over):
    payload = {"name": "인텔리제이", "vendor": "JetBrains", "asset_category": "SW"}
    payload.update(over)
    r = client.post("/api/asset-products", json=payload, headers=admin_headers)
    assert r.status_code == 201, r.text
    return r.json()


def _create_unit(client, admin_headers, product_id, **over):
    payload = {
        "product_id": product_id,
        "purchase_date": "2026-01-10",
        "purchased_from": "마이크로소프트 리셀러",
        "price": 1200000,
        "unit_type": "KEY",
        "key_value": "ref-001",
        "expire_date": None,
        "group_code": "A",
    }
    payload.update(over)
    r = client.post("/api/asset-units", json=payload, headers=admin_headers)
    return r


# --------------------------------------------------------------------------- 상품 마스터
def test_create_product_requires_super_admin(client, manager_headers):
    r = client.post(
        "/api/asset-products",
        json={"name": "인텔리제이", "vendor": "JetBrains", "asset_category": "SW"},
        headers=manager_headers,
    )
    assert r.status_code == 403


def test_create_product_rejects_invalid_category(client, admin_headers):
    r = client.post(
        "/api/asset-products",
        json={"name": "인텔리제이", "asset_category": "NOPE"},
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_deactivate_product_does_not_delete(client, admin_headers):
    product = _create_product(client, admin_headers)
    r = client.patch(
        f"/api/asset-products/{product['id']}", json={"is_active": False}, headers=admin_headers
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    listed = client.get("/api/asset-products", headers=admin_headers).json()["items"]
    assert any(p["id"] == product["id"] for p in listed)  # 여전히 목록에 존재(삭제 안 됨)


# --------------------------------------------------------------------------- 채번
def test_unit_numbering_is_sequential_per_product(client, admin_headers):
    product = _create_product(client, admin_headers)
    r1 = _create_unit(client, admin_headers, product["id"])
    r2 = _create_unit(client, admin_headers, product["id"])
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    assert r1.json()["unit_no"] == "인텔리제이-001"
    assert r2.json()["unit_no"] == "인텔리제이-002"


def test_unit_numbering_independent_per_product(client, admin_headers):
    p1 = _create_product(client, admin_headers, name="인텔리제이")
    p2 = _create_product(client, admin_headers, name="비주얼스튜디오", vendor="Microsoft")
    r1 = _create_unit(client, admin_headers, p1["id"])
    r2 = _create_unit(client, admin_headers, p2["id"])
    assert r1.json()["unit_no"] == "인텔리제이-001"
    assert r2.json()["unit_no"] == "비주얼스튜디오-001"  # 서로 다른 상품이면 001부터 독립


def test_retired_unit_no_is_never_reused(client, admin_headers):
    product = _create_product(client, admin_headers)
    r1 = _create_unit(client, admin_headers, product["id"])
    unit_no = r1.json()["unit_no"]

    client.post(f"/api/asset-units/{unit_no}/retire", headers=admin_headers)
    r2 = _create_unit(client, admin_headers, product["id"])
    assert r2.json()["unit_no"] == "인텔리제이-002"  # 001은 폐기돼도 결번으로 남고 재사용 안 됨


def test_create_unit_rejects_inactive_product(client, admin_headers):
    product = _create_product(client, admin_headers)
    client.patch(f"/api/asset-products/{product['id']}", json={"is_active": False}, headers=admin_headers)
    r = _create_unit(client, admin_headers, product["id"])
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "PRODUCT_INACTIVE"


# --------------------------------------------------------------------------- 폐기(soft delete)
def test_retire_is_soft_delete_not_physical(client, admin_headers):
    product = _create_product(client, admin_headers)
    unit_no = _create_unit(client, admin_headers, product["id"]).json()["unit_no"]

    r = client.post(f"/api/asset-units/{unit_no}/retire", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "EXPIRED"

    detail = client.get(f"/api/asset-units/{unit_no}", headers=admin_headers)
    assert detail.status_code == 200  # 문서 자체는 그대로 조회 가능(물리삭제 아님)
    assert detail.json()["retired_at"] is not None


def test_retire_twice_is_rejected(client, admin_headers):
    product = _create_product(client, admin_headers)
    unit_no = _create_unit(client, admin_headers, product["id"]).json()["unit_no"]
    client.post(f"/api/asset-units/{unit_no}/retire", headers=admin_headers)

    r = client.post(f"/api/asset-units/{unit_no}/retire", headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "ALREADY_RETIRED"


# --------------------------------------------------------------------------- 견적 연동 잠금
# --------------------------------------------------------------------------- 수정
def test_patch_unit_updates_fields(client, admin_headers):
    product = _create_product(client, admin_headers)
    unit_no = _create_unit(client, admin_headers, product["id"]).json()["unit_no"]

    r = client.patch(
        f"/api/asset-units/{unit_no}",
        json={"price": 900000, "purchased_from": "새 구매처", "key_value": "new-key"},
        headers=admin_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["price"] == 900000
    assert body["purchased_from"] == "새 구매처"
    assert body["key_value"] == "new-key"
    assert body["updated_at"] is not None
    assert body["unit_no"] == unit_no  # 번호는 그대로


def test_patch_unit_does_not_delete_or_renumber(client, admin_headers):
    """"삭제 후 재등록" 대신 수정으로 고치는 시나리오 — 번호가 안 바뀌는지 확인."""
    product = _create_product(client, admin_headers)
    unit_no = _create_unit(client, admin_headers, product["id"], price=100).json()["unit_no"]

    r = client.patch(f"/api/asset-units/{unit_no}", json={"price": 500000}, headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["unit_no"] == unit_no

    detail = client.get(f"/api/asset-units/{unit_no}", headers=admin_headers)
    assert detail.json()["price"] == 500000


def test_patch_retired_unit_is_rejected(client, admin_headers):
    product = _create_product(client, admin_headers)
    unit_no = _create_unit(client, admin_headers, product["id"]).json()["unit_no"]
    client.post(f"/api/asset-units/{unit_no}/retire", headers=admin_headers)

    r = client.patch(f"/api/asset-units/{unit_no}", json={"price": 1}, headers=admin_headers)
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "ALREADY_RETIRED"


def test_group_manager_cannot_patch_unit(client, admin_headers, manager_headers):
    product = _create_product(client, admin_headers)
    unit_no = _create_unit(client, admin_headers, product["id"]).json()["unit_no"]

    r = client.patch(f"/api/asset-units/{unit_no}", json={"price": 1}, headers=manager_headers)
    assert r.status_code == 403


def test_unit_creation_locks_source_quote(client, admin_headers):
    quote = client.post("/api/quotes", json=sample_payload(), headers=admin_headers).json()
    assert quote["purchase_locked"] is False

    product = _create_product(client, admin_headers, asset_category="HW")
    r = _create_unit(
        client,
        admin_headers,
        product["id"],
        unit_type=None,
        key_value=None,
        source_quote_id=quote["id"],
    )
    assert r.status_code == 201, r.text
    assert r.json()["source_quote_id"] == quote["id"]

    locked_quote = client.get(f"/api/quotes/{quote['id']}", headers=admin_headers).json()
    assert locked_quote["purchase_locked"] is True
    assert locked_quote["locked_at"] is not None
    assert locked_quote["read_only"] is True  # 잠긴 견적서는 더 이상 수정 불가(guard_mutable)


# --------------------------------------------------------------------------- 권한 · 스코프
def test_list_units_scoped_to_group_manager(client, admin_headers, manager_headers):
    """manager_headers(test1)는 A 그룹 소속(conftest) — 다른 그룹 유닛은 안 보여야 함."""
    product = _create_product(client, admin_headers)
    _create_unit(client, admin_headers, product["id"], group_code="A")
    _create_unit(client, admin_headers, product["id"], group_code="B")

    r = client.get("/api/asset-units", headers=manager_headers)
    assert r.status_code == 200
    groups_seen = {item["group_code"] for item in r.json()["items"]}
    assert groups_seen == {"A"}


def test_group_manager_other_group_detail_is_404(client, admin_headers, manager_headers):
    product = _create_product(client, admin_headers)
    unit_no = _create_unit(client, admin_headers, product["id"], group_code="B").json()["unit_no"]

    r = client.get(f"/api/asset-units/{unit_no}", headers=manager_headers)
    assert r.status_code == 404  # 존재 은닉(quotes와 동일 원칙)


def test_group_manager_cannot_create_unit(client, admin_headers, manager_headers):
    product = _create_product(client, admin_headers)
    r = client.post(
        "/api/asset-units",
        json={
            "product_id": product["id"], "purchase_date": "2026-01-10", "price": 100,
            "group_code": "A",
        },
        headers=manager_headers,
    )
    assert r.status_code == 403


def test_group_manager_cannot_retire_unit(client, admin_headers, manager_headers):
    product = _create_product(client, admin_headers)
    unit_no = _create_unit(client, admin_headers, product["id"]).json()["unit_no"]
    r = client.post(f"/api/asset-units/{unit_no}/retire", headers=manager_headers)
    assert r.status_code == 403
