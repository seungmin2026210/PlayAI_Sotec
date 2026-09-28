"""자산 상태 가드 — `services/status.py` 스타일 순수 함수. specs/ASSET-1 D21, P1.

상태(IDLE/IN_USE/DISPOSED)는 직접 못 바꾼다 — 배정·회수·폐기 동작으로만.
"""
from __future__ import annotations

from ..config import ASSET_STATUS_DISPOSED, ASSET_STATUS_IDLE, ASSET_STATUS_IN_USE
from ..errors import ASSET_DISPOSED, ASSET_IN_USE, ASSET_NOT_IDLE, ASSET_NOT_IN_USE, AppError
from ..models import Asset


def guard_not_disposed(asset: Asset) -> None:
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
