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


_DIGITS = ("", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구")
_SMALL_UNITS = ("", "십", "백", "천")
_BIG_UNITS = ("", "만", "억", "조", "경")


def _four_digit_word(n: int) -> str:
    """0~9999 → 한글 숫자말. 십/백/천 자리의 '일'은 생략(예: 10 -> 십, 1000 -> 천)."""
    word = ""
    for i, d in enumerate(f"{n:04d}"):
        digit = int(d)
        place = 3 - i
        if digit == 0:
            continue
        word += _SMALL_UNITS[place] if digit == 1 and place > 0 else _DIGITS[digit] + _SMALL_UNITS[place]
    return word


def korean_amount_words(n: int) -> str:
    """정수 원화 금액 → 한글 금액말(만/억/조 단위). 위탁계약형 엑셀 "일금 ○○○원정" 표기용.

    예: 44000000 -> '사천사백만'. 개별 견적서 export(`services/export_excel.py`)
    전용 — 통화 표기 규칙 격리 지점은 `format_won`과 동일하게 이 함수.
    """
    if n <= 0:
        return "영"
    groups: list[int] = []
    remaining = n
    while remaining > 0:
        groups.append(remaining % 10_000)
        remaining //= 10_000
    words = []
    for i in range(len(groups) - 1, -1, -1):
        g = groups[i]
        if g == 0:
            continue
        words.append(_four_digit_word(g) + _BIG_UNITS[i])
    return "".join(words)
