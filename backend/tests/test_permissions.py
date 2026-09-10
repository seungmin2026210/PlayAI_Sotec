from tests.conftest import sample_payload


def _create(client, headers, **over):
    r = client.post("/api/quotes", json=sample_payload(**over), headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_unauthenticated_is_401(client):
    assert client.get("/api/quotes").status_code == 401


def test_group_manager_cannot_create(client, admin_headers, manager_headers):
    r = client.post("/api/quotes", json=sample_payload(), headers=manager_headers)
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "FORBIDDEN_ROLE"


def test_group_manager_list_scoped_to_own_group(client, admin_headers, manager_headers):
    _create(client, admin_headers, group_code="A", title="A건")
    _create(client, admin_headers, group_code="B", title="B건")

    r = client.get("/api/quotes", headers=manager_headers)  # test1 → group A
    assert r.status_code == 200
    groups = {row["group_code"] for row in r.json()["items"]}
    assert groups == {"A"}


def test_group_manager_other_group_detail_is_404(client, admin_headers, manager_headers):
    b = _create(client, admin_headers, group_code="B")
    r = client.get(f"/api/quotes/{b['id']}", headers=manager_headers)
    assert r.status_code == 404


def test_group_manager_can_export_own_group(client, admin_headers, manager_headers):
    a = _create(client, admin_headers, group_code="A")
    client.post(f"/api/quotes/{a['id']}/approve", headers=admin_headers)  # export는 승인됨만 허용
    r = client.get(f"/api/quotes/{a['id']}/export.xlsx", headers=manager_headers)
    assert r.status_code == 200
    assert "spreadsheet" in r.headers["content-type"]


def test_bad_login_is_401(client):
    r = client.post("/api/auth/login", json={"username": "Admin", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "INVALID_CREDENTIALS"
