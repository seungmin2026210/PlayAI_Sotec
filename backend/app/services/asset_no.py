"""자산번호 채번 `{SW|HW|EDU}-{YY}-{NNN}` — specs/ASSET-1 D6~D8, D31, tech/01-data-model.md § 2.

`asset_seq/{category}-{YY}` 문서를 트랜잭션으로 read-then-write(`services/numbering.py` 패턴).
수량 N 이면 연속 N개를 한 번에 확보한다. 되돌리지 않음(영구 결번).
구매 유닛 채번(`asset_numbering.py`)과는 별개.
"""
from __future__ import annotations

from google.cloud import firestore

from ..config import ASSET_NO_SEQ_MAX
from ..errors import SEQ_EXHAUSTED, AppError
from .asset_dates import today_kst


def asset_year(purchase_date: str | None) -> int:
    """번호 연도 = 구매일 연도, 없으면 등록 시점 KST 연도(D7, D45)."""
    return int(purchase_date[:4]) if purchase_date else today_kst().year


def format_asset_no(category: str, year: int, seq: int) -> str:
    return f"{category}-{year % 100:02d}-{seq:03d}"


def allocate_asset_nos_in(
    transaction: firestore.Transaction,
    client: firestore.Client,
    *,
    category: str,
    purchase_date: str | None,
    count: int,
) -> list[str]:
    """열린 트랜잭션 안에서 N개 확보. 999 를 넘으면 하나도 만들지 않고 409."""
    key = (category, asset_year(purchase_date))
    return allocate_groups_in(transaction, client, {key: count})[key]


def allocate_groups_in(
    transaction: firestore.Transaction,
    client: firestore.Client,
    counts: dict[tuple[str, int], int],
) -> dict[tuple[str, int], list[str]]:
    """여러 (유형, 연도) 묶음을 한 트랜잭션에서 확보(엑셀 업로드 — D50).

    Firestore 트랜잭션은 read 를 전부 끝낸 뒤 write 해야 하므로 카운터를 모두 읽고 검사한 다음 쓴다.
    하나라도 999 를 넘으면 아무것도 쓰지 않고 409."""
    refs = {key: client.collection("asset_seq").document(f"{key[0]}-{key[1] % 100:02d}") for key in counts}
    lasts = {}
    for key, ref in refs.items():
        snap = ref.get(transaction=transaction)
        lasts[key] = snap.get("last_seq") if snap.exists else 0
    for (category, year), n in counts.items():
        last = lasts[(category, year)]
        if last + n > ASSET_NO_SEQ_MAX:
            raise AppError(
                SEQ_EXHAUSTED, 409,
                f"{category}-{year % 100:02d} 번호가 부족합니다(남은 번호 {ASSET_NO_SEQ_MAX - last}개).",
            )
    out = {}
    for (category, year), n in counts.items():
        last = lasts[(category, year)]
        transaction.set(refs[(category, year)], {"last_seq": last + n})
        out[(category, year)] = [format_asset_no(category, year, s) for s in range(last + 1, last + n + 1)]
    return out
