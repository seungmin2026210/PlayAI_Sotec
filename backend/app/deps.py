"""의존성 + 권한 판정 (TECH 07).

open-1(그룹관리자 조회 전용) / open-3(역할별 화면) 격리 지점.
권한 규칙 변경이 필요하면 이 파일만 수정한다.
"""
from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Header
from sqlalchemy import Select
from sqlalchemy.orm import Session

from .auth import CurrentUser, resolve_token
from .config import ROLE_GROUP_MANAGER, ROLE_SUPER_ADMIN
from .database import SessionLocal
from .errors import FORBIDDEN_ROLE, NOT_AUTHENTICATED, NOT_FOUND, AppError
from .models import Quote


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(NOT_AUTHENTICATED, 401, "로그인이 필요합니다.")
    token = authorization.split(" ", 1)[1].strip()
    return resolve_token(token)


def require_super_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != ROLE_SUPER_ADMIN:
        raise AppError(FORBIDDEN_ROLE, 403, "조회 전용 권한입니다. 이 작업은 전체관리자만 가능합니다.")
    return user


def apply_scope(stmt: Select, user: CurrentUser) -> Select:
    """그룹관리자는 본인 그룹으로 강제 필터. 전체관리자는 무제한."""
    if user.role == ROLE_GROUP_MANAGER:
        return stmt.where(Quote.group_code == user.group_code)
    return stmt


def assert_can_view(quote: Quote, user: CurrentUser) -> None:
    if user.role == ROLE_GROUP_MANAGER and quote.group_code != user.group_code:
        # 존재 은닉
        raise AppError(NOT_FOUND, 404, "견적서를 찾을 수 없습니다.")
