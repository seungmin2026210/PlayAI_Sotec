"""의존성 + 권한 판정 (TECH 07, 12).

open-1(그룹관리자 조회 전용) / open-3(역할별 화면) 격리 지점.
권한 규칙 변경이 필요하면 이 파일만 수정한다.
"""
from __future__ import annotations

from fastapi import Depends, Header
from google.cloud import firestore

from .auth import CurrentUser, resolve_token
from .config import ROLE_GROUP_MANAGER, ROLE_SUPER_ADMIN
from .database import get_client
from .errors import FORBIDDEN_ROLE, NOT_AUTHENTICATED, NOT_FOUND, AppError
from .models import Quote


def get_db() -> firestore.Client:
    """이름은 SQLAlchemy 시절과 동일하게 유지(라우터 의존성 시그니처 변경 최소화).
    실제로는 Firestore 클라이언트를 반환한다."""
    return get_client()


def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(NOT_AUTHENTICATED, 401, "로그인이 필요합니다.")
    token = authorization.split(" ", 1)[1].strip()
    return resolve_token(token)


def require_super_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user.role != ROLE_SUPER_ADMIN:
        raise AppError(FORBIDDEN_ROLE, 403, "조회 전용 권한입니다. 이 작업은 전체관리자만 가능합니다.")
    return user


def scope_group(user: CurrentUser) -> str | None:
    """그룹관리자는 본인 그룹으로 강제 스코프. 전체관리자는 None(무제한).

    SQLAlchemy 시절 `apply_scope(stmt, user)`가 `Select`에 `.where(...)`를 얹던 것을
    대체 — Firestore 쿼리는 이 값을 그대로 `where("group_code", "==", ...)`에 쓴다
    (12-firestore-migration.md § 3)."""
    if user.role == ROLE_GROUP_MANAGER:
        return user.group_code
    return None


def assert_can_view(quote: Quote, user: CurrentUser) -> None:
    if user.role == ROLE_GROUP_MANAGER and quote.group_code != user.group_code:
        # 존재 은닉
        raise AppError(NOT_FOUND, 404, "견적서를 찾을 수 없습니다.")
