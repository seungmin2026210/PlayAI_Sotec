from __future__ import annotations

import os

os.environ.setdefault("QUOTE_TESTING", "1")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401
from app.main import app

_TABLES = ["quote_items", "quotes", "retired_numbers", "number_sequences"]


@pytest.fixture(scope="session", autouse=True)
def _schema():
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:  # 테스트 DB 없음 — DB 불필요한 테스트(test_export 등)만 실행
        pytest.skip(f"test DB unavailable: {exc}")
    yield
    # 세션 종료 시 스키마는 남겨둔다(재실행 시 재사용).


@pytest.fixture(autouse=True)
def _clean():
    with engine.begin() as conn:
        conn.execute(
            text(f"TRUNCATE {', '.join(_TABLES)} RESTART IDENTITY CASCADE")
        )
    yield


@pytest.fixture()
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


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
