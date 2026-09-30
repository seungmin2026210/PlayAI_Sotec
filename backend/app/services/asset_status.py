"""자산 상태 가드 — `services/status.py` 스타일 순수 함수. specs/ASSET-1 D21, P1.

상태(IDLE/IN_USE/DISPOSED/DELETED)는 직접 못 바꾼다 — 배정·회수·폐기·삭제 동작으로만.
"""
from __future__ import annotations

from ..config import ASSET_STATUS_DELETED, ASSET_STATUS_DISPOSED, ASSET_STATUS_IDLE, ASSET_STATUS_IN_USE
from ..errors import (
    ASSET_DELETED,
    ASSET_DISPOSED,
    ASSET_HAS_HISTORY,
    ASSET_IMPORTED,
    ASSET_IN_USE,
    ASSET_NOT_IDLE,
    ASSET_NOT_IN_USE,
    AppError,
)
from ..models import Asset


def guard_not_disposed(asset: Asset) -> None:
    """폐기·삭제된 자산은 읽기전용(D47)."""
    if asset.status == ASSET_STATUS_DELETED:
        raise AppError(ASSET_DELETED, 409, "삭제된 자산은 변경할 수 없습니다.")
    if asset.status == ASSET_STATUS_DISPOSED:
        raise AppError(ASSET_DISPOSED, 409, "폐기된 자산은 변경할 수 없습니다.")


def guard_idle(asset: Asset) -> None:
    guard_not_disposed(asset)
    if asset.status != ASSET_STATUS_IDLE:
        raise AppError(ASSET_NOT_IDLE, 409, "이미 사용 중인 자산입니다. 먼저 회수하거나 사용자 변경을 하세요.")


def guard_in_use(asset: Asset) -> None:
    guard_not_disposed(asset)
    if asset.status != ASSET_STATUS_IN_USE:
        raise AppError(ASSET_NOT_IN_USE, 409, "사용 중인 자산이 아닙니다.")


def guard_disposable(asset: Asset) -> None:
    """임시 결정 P1: 사용 중이면 바로 폐기 불가 — 먼저 회수."""
    guard_not_disposed(asset)
    if asset.status == ASSET_STATUS_IN_USE:
        raise AppError(ASSET_IN_USE, 409, "사용 중인 자산은 폐기할 수 없습니다. 먼저 회수하세요.")


def guard_deletable(asset: Asset, has_history: bool) -> None:
    """D47: 잘못 등록한 기록만 삭제 — 미사용 · 배정/갱신 이력 없음 · 직접 등록(가져온 자산은 가져오기 취소로)."""
    guard_not_disposed(asset)
    if asset.source_unit_no:
        raise AppError(ASSET_IMPORTED, 409, "구매에서 가져온 자산은 삭제할 수 없습니다. [가져오기 취소]를 사용하세요.")
    if asset.status != ASSET_STATUS_IDLE or has_history:
        raise AppError(ASSET_HAS_HISTORY, 409, "배정·갱신 이력이 있는 자산은 삭제할 수 없습니다. 폐기하세요.")
