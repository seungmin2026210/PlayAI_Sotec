"""금액 계산 — 순수 함수, 정수(원) 연산. 기획서 5장 / TECH 08.

- 항목 금액(unit_price)은 항상 공급가액 기준.
- 공급가액 합계 = 항목 합계에 십만단위 절사(내림, 총합계 기준).
- 부가세 = 절사 공급가액 * 0.1.
- 부가세 포함가 = 공급가액 + 부가세 (부가세 "포함" 선택 시 병기).
"""
from __future__ import annotations

from dataclasses import dataclass

from ..config import TRUNCATE_UNIT, VAT_RATE


@dataclass(frozen=True)
class Computed:
    raw_total: int      # 절사 전 항목 합계
    supply_amount: int  # 십만단위 절사 후 공급가액 합계
    vat_amount: int     # 부가세
    total_with_vat: int # 부가세 포함가


def line_amount(qty: int, unit_price: int) -> int:
    return qty * unit_price


def items_raw_total(items) -> int:
    return sum(line_amount(i.qty, i.unit_price) for i in items)


def truncate_supply(raw_total: int) -> int:
    """십만단위 절사(내림). 예: 12,345,678 -> 12,300,000."""
    if raw_total <= 0:
        return 0
    return (raw_total // TRUNCATE_UNIT) * TRUNCATE_UNIT


def vat_of(supply_amount: int) -> int:
    return round(supply_amount * VAT_RATE)


def compute(items) -> Computed:
    raw = items_raw_total(items)
    supply = truncate_supply(raw)
    vat = vat_of(supply)
    return Computed(
        raw_total=raw,
        supply_amount=supply,
        vat_amount=vat,
        total_with_vat=supply + vat,
    )


def format_won(n: int) -> str:
    """open-6 임시결정: 천단위 콤마 + '원'. 통화기호 미사용. 표기 규칙 격리 지점."""
    return f"{n:,}원"
