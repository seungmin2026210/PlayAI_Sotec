from __future__ import annotations

import os

# 에뮬레이터 호스트/프로젝트 — 이미 환경에 있으면(CI 등) 그 값을 존중.
os.environ.setdefault("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8090")
os.environ.setdefault("FIRESTORE_PROJECT_ID", "quote-pytest")

import pytest
from fastapi.testclient import TestClient

from app.database import get_client
from app.main import app

_COLLECTIONS = ["quotes", "number_sequences", "retired_numbers"]


def _delete_collection(client, name: str) -> None:
    for doc in client.collection(name).stream():
        doc.reference.delete()


@pytest.fixture(scope="session", autouse=True)
def _schema():
    """Firestore 는 스키마가 없다 — 에뮬레이터에 실제로 붙는지만 확인.
    (PostgreSQL 시절 `Base.metadata.create_all` 대응 — 여기선 연결 확인용 read 1회.)"""
    try:
        get_client().collection("quotes").limit(1).get()
    except Exception as exc:  # 에뮬레이터 미기동 — DB 불필요한 테스트(unit/ 등)만 실행
        pytest.skip(f"Firestore emulator unavailable: {exc}")
    yield


@pytest.fixture(autouse=True)
def _clean():
    client = get_client()
    for name in _COLLECTIONS:
        _delete_collection(client, name)
    yield


@pytest.fixture()
def db():
    return get_client()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def admin_headers(client):
    r = client.post("/api/auth/login", json={"username": "Admin", "password": "1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture()
def manager_headers(client):
    r = client.post("/api/auth/login", json={"username": "test1", "password": "1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def sample_payload(**over):
    payload = {
        "group_code": "A",
        "title": "테스트 견적",
        "issue_date": "2026-04-01",
        "issuer_name": "김담당",
        "customer_name": "테스트고객사",
        "customer_contact_name": None,
        "customer_contact_phone": None,
        "vat_included": True,
        "items": [{"name": "품목1", "qty": 2, "unit_price": 5_000_000}],
    }
    payload.update(over)
    return payload
