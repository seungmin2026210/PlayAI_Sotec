from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


def _db_url() -> str:
    # 테스트 실행 시 conftest 가 QUOTE_TESTING=1 을 세팅한다.
    if os.getenv("QUOTE_TESTING") == "1":
        return settings.database_url_test
    return settings.database_url


engine = create_engine(_db_url(), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass
