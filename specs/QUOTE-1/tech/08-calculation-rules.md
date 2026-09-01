# 08. 계산 규칙 구현

모두 `services/calculation.py` 의 순수 함수. 정수(원) 연산만, 부동소수 금지.

## 입력

`items: list[{qty:int>0, unit_price:int>0}]` — unit_price 는 **공급가액 기준**.

## 함수

```python
VAT_RATE = 0.1                 # config
TRUNCATE_UNIT = 100_000        # 십만단위 절사

def line_amount(qty, unit_price) -> int:
    return qty * unit_price

def items_raw_total(items) -> int:
    return sum(line_amount(i.qty, i.unit_price) for i in items)

def supply_amount(raw_total: int) -> int:
    # 총합계 기준 십만단위 내림(절사)
    return (raw_total // TRUNCATE_UNIT) * TRUNCATE_UNIT

def vat_amount(supply: int) -> int:
    # 절사된 공급가액 * 0.1, 원 단위 반올림(정수화)
    return round(supply * VAT_RATE)

def total_with_vat(supply: int) -> int:
    return supply + vat_amount(supply)

def compute(items) -> Computed:
    raw = items_raw_total(items)
    sup = supply_amount(raw)
    vat = vat_amount(sup)
    return Computed(raw=raw, supply=sup, vat=vat, total=sup + vat)
```

## 예시

| 항목 합계(raw) | 공급가액(절사) | 부가세 | 부가세 포함가 |
|---|---|---|---|
| 12,345,678 | 12,300,000 | 1,230,000 | 13,530,000 |
| 999,999 | 900,000 | 90,000 | 990,000 |
| 50,000 | 0 | 0 | 0 |

> raw < 100,000 이면 공급가액 0 → 사실상 저장 의미 없음. 유효성에서 별도 차단하지 않음(항목 금액 자체가 양수면 통과). 필요 시 협의 후 최소금액 규칙 추가.

## 표기 (open-6 임시 결정 격리 지점)

- `format_won(n: int) -> str` → `f"{n:,}원"` (예: `13,530,000원`).
- 프론트 동일 규칙: `frontend/src/lib/money.ts: formatWon`.
- 부가세 "포함" 선택 시 화면/문서에 `공급가액 · 부가세 · 부가세 포함가` 3개 모두 표기. "미포함" 선택 시에도 계산값은 저장하되 문서에는 공급가액 중심 + 부가세 별도 표기.
