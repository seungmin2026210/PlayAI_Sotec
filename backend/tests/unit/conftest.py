"""tests/unit/ 는 DB 가 필요 없는 순수 단위 테스트만 둔다.

상위 tests/conftest.py 의 autouse 픽스처(_schema/_clean)를 no-op 로 덮어써서
PostgreSQL 없이도 실행된다.
"""
import pytest


@pytest.fixture(scope="session", autouse=True)
def _schema():
    yield


@pytest.fixture(autouse=True)
def _clean():
    yield
