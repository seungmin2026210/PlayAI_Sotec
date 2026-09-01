"""상태 머신 + 편집/삭제 가드 — 기획서 7장 / TECH 06."""
from __future__ import annotations

from datetime import datetime, timezone

from ..config import (
    STATUS_APPROVED,
    STATUS_CANCELLED,
    STATUS_REJECTED,
    STATUS_SUBMITTED,
)
from ..errors import (
    INVALID_TRANSITION,
    NOT_FOUND,
    PURCHASE_LOCKED,
    AppError,
)
from ..models import Quote

TERMINAL_STATUSES = frozenset({STATUS_REJECTED, STATUS_CANCELLED})

# (from_status, action) -> to_status
ALLOWED: dict[tuple[str, str], str] = {
    (STATUS_SUBMITTED, "approve"): STATUS_APPROVED,
    (STATUS_SUBMITTED, "reject"): STATUS_REJECTED,
    (STATUS_SUBMITTED, "cancel"): STATUS_CANCELLED,
    (STATUS_APPROVED, "cancel"): STATUS_CANCELLED,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_read_only(quote: Quote) -> bool:
    """편집 계열 액션 불가 여부(파생). 잠금 또는 종료 상태."""
    return quote.purchase_locked or quote.status in TERMINAL_STATUSES


def assert_exists(quote: Quote | None) -> Quote:
    if quote is None or quote.deleted_at is not None:
        raise AppError(NOT_FOUND, 404, "견적서를 찾을 수 없습니다.")
    return quote


def guard_mutable(quote: Quote) -> None:
    """수정(PUT)/삭제(DELETE) 공통 선행 검사."""
    if quote.deleted_at is not None:
        raise AppError(NOT_FOUND, 404, "견적서를 찾을 수 없습니다.")
    if quote.purchase_locked:
        raise AppError(PURCHASE_LOCKED, 409, "구매관리 데이터가 반영되어 수정/삭제할 수 없습니다.")
    if quote.status in TERMINAL_STATUSES:
        raise AppError(
            INVALID_TRANSITION,
            409,
            f"'{quote.status}' 상태의 견적서는 읽기전용으로 보존됩니다.",
        )


def apply_transition(quote: Quote, action: str, *, reason: str | None = None) -> None:
    """승인/반려/취소. 잠금 검사 포함."""
    if quote.purchase_locked and action in {"cancel"}:
        raise AppError(PURCHASE_LOCKED, 409, "구매관리 데이터가 반영되어 취소할 수 없습니다.")

    target = ALLOWED.get((quote.status, action))
    if target is None:
        raise AppError(
            INVALID_TRANSITION,
            409,
            f"'{quote.status}' 상태에서는 '{action}' 처리를 할 수 없습니다.",
        )

    now = _now()
    quote.status = target
    if action == "approve":
        quote.approved_at = now
    elif action == "reject":
        quote.reject_reason = reason
        quote.rejected_at = now
    elif action == "cancel":
        quote.cancelled_at = now


def apply_purchase_lock(quote: Quote) -> bool:
    """구매관리 반영(자리표시). 이미 잠겨 있으면 no-op. 반환: 실제로 바뀌었는지."""
    if quote.purchase_locked:
        return False
    quote.purchase_locked = True
    quote.locked_at = _now()
    return True


def apply_edit_policy(quote: Quote, payload, computed) -> None:
    """open-10 임시결정 격리 지점.

    현재 정책: 전체 필드 수정 허용, 상태값 유지(되돌리지 않음), 감사로그 미기록.
    협의 후 예) 승인됨 상태에서 수정 시 제출됨으로 되돌리려면 아래에 한 줄 추가.
    """
    quote.group_code = payload.group_code
    quote.title = payload.title
    quote.issue_date = payload.issue_date
    quote.issuer_name = payload.issuer_name
    quote.customer_name = payload.customer_name
    quote.customer_contact_name = payload.customer_contact_name
    quote.customer_contact_phone = payload.customer_contact_phone
    quote.vat_included = payload.vat_included

    quote.items_raw_total = computed.raw_total
    quote.supply_amount = computed.supply_amount
    quote.vat_amount = computed.vat_amount
    quote.total_with_vat = computed.total_with_vat

    quote.updated_at = _now()
    # 협의 시 활성화 예시:
    # if quote.status == STATUS_APPROVED:
    #     quote.status = STATUS_SUBMITTED
