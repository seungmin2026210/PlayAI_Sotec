"""의존성 + 권한 판정 (TECH 07, 12).

open-1(그룹관리자 조회 전용) / open-3(역할별 화면) 격리 지점.
권한 규칙 변경이 필요하면 이 파일만 수정한다.
"""
from __future__ import annotations

from fastapi import Depends, Header
from google.cloud import firestore

from .auth import CurrentUser, resolve_token
from .config import ASSET_STATUS_DELETED, ROLE_GROUP_MANAGER, ROLE_SUPER_ADMIN
from .database import get_client
from .errors import FORBIDDEN_ROLE, NOT_AUTHENTICATED, NOT_FOUND, AppError
from .models import Asset, AssetUnit, Member, Quote


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


def assert_can_view_asset_unit(unit: AssetUnit, user: CurrentUser) -> None:
    """PURCHASE-1: 그룹관리자는 본인 그룹 자산만(quotes와 동일 원칙 — 존재 은닉)."""
    if user.role == ROLE_GROUP_MANAGER and unit.group_code != user.group_code:
        raise AppError(NOT_FOUND, 404, "자산을 찾을 수 없습니다.")


# --------------------------------------------------------------------------- ASSET-1
def assert_can_view_asset(asset: Asset, user: CurrentUser) -> None:
    """그룹관리자는 `scope_group_code`(= 현재 사용자 그룹, 미사용·공용이면 등록 그룹 — D24)가
    본인 그룹인 자산만. 타 그룹은 404(존재 은닉). 삭제된 자산(D47)은 전체관리자만."""
    if user.role == ROLE_GROUP_MANAGER and (
        asset.scope_group_code != user.group_code or asset.status == ASSET_STATUS_DELETED
    ):
        raise AppError(NOT_FOUND, 404, "자산을 찾을 수 없습니다.")


def assert_can_view_member(member: Member, user: CurrentUser) -> None:
    """D46: 그룹관리자는 본인 그룹 팀원만."""
    if user.role == ROLE_GROUP_MANAGER and member.group_code != user.group_code:
        raise AppError(NOT_FOUND, 404, "팀원을 찾을 수 없습니다.")


def can_reveal_password(asset: Asset, user: CurrentUser) -> bool:
    """비밀번호 열람 판정 격리 지점(D16). 지금은 전체관리자만.
    팀원 로그인 도입 시 `asset.current_member_id == <로그인 팀원 사번>` 조건만 추가한다."""
    return user.role == ROLE_SUPER_ADMIN


def can_see_license_key(user: CurrentUser) -> bool:
    """D38: 라이선스키 전체 표시·키워드 검색은 전체관리자만. 마스킹은 presenter.mask_license_key."""
    return user.role == ROLE_SUPER_ADMIN
