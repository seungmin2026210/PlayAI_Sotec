"""자산 입력값 정리 + 수량 N 등록용 순수 함수 — specs/ASSET-1 D31, P9, D41.

DB 에 의존하지 않는다(tests/unit 에서 바로 검증).
"""
from __future__ import annotations

from ..config import ASSET_BULK_MAX, ASSET_SUBCATEGORIES
from ..errors import validation

# 유형별 전용 필드. 유형에 없는 필드는 저장하지 않는다(예: HW 에 비밀번호).
_ONLY: dict[str, set[str]] = {
    "SW": {"version", "license_key", "account_id", "password"},
    "HW": {"manufacturer", "model", "serial_no", "mac_address"},
    "EDU": {"course_title", "course_url", "account_id", "password"},
}
_TYPED = set().union(*_ONLY.values())


def split_price(total: int | None, n: int) -> list[int | None]:
    """구매 금액을 N 으로 나눈다. 나머지(원)는 첫 자산에(P9) — 합계 == total."""
    if total is None:
        return [None] * n
    base, rest = divmod(total, n)
    return [base + rest] + [base] * (n - 1)


def check_quantity(n: int) -> None:
    if not 1 <= n <= ASSET_BULK_MAX:
        raise validation(f"수량은 1~{ASSET_BULK_MAX} 사이여야 합니다.")


def clean_fields(category: str, data: dict) -> dict:
    """입력 dict(부분일 수 있음)를 정리: 문자열 trim·빈 문자열 → None, 유형에 없는 전용 필드 제거,
    소분류 검증, 유효기간 순서 검증(둘 다 들어온 경우). 날짜는 ISO 문자열로."""
    out: dict = {}
    for k, v in data.items():
        if k in _TYPED and k not in _ONLY[category]:
            continue
        if isinstance(v, str):
            v = v.strip() or None
        elif hasattr(v, "isoformat"):
            v = v.isoformat()
        out[k] = v

    if "subcategory" in out:
        allowed = ASSET_SUBCATEGORIES[category]
        if not allowed:
            out["subcategory"] = None
        elif out["subcategory"] is not None and out["subcategory"] not in allowed:
            raise validation(f"{category} 소분류는 {', '.join(allowed.values())} 중 하나여야 합니다.")
    if "name" in out and not out["name"]:
        raise validation("품명을 입력해야 합니다.")
    return out


def check_valid_range(valid_from: str | None, valid_to: str | None) -> None:
    if valid_from and valid_to and valid_to < valid_from:
        raise validation("유효기간 종료일은 시작일보다 앞설 수 없습니다.")
