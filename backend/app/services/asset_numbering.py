"""자산 유닛 채번 — specs/PURCHASE-1/tech/01-data-model.md § 5.

형식 "{상품명}-{순번}" (예: 인텔리제이-001).
- 상품별 독립 시퀀스. `asset_product_seq/{product_id}` 문서를 트랜잭션으로 read-then-write
  (`services/numbering.py`의 `number_sequences` 패턴과 동일 — 여기선 연도 개념이 없다).
- 결번: 폐기(retire)해도 `last_seq` 는 되돌리지 않는다(재사용 금지).

`*_in(transaction, ...)` 함수는 호출자가 이미 시작한 트랜잭션에 이어붙여 쓴다 — 유닛 생성은
채번과 문서 생성(+ 있으면 견적서 잠금)을 하나의 트랜잭션으로 묶어야 한다
(`routers/purchase.py: create_asset_unit`).
"""
from __future__ import annotations

from dataclasses import dataclass

from google.cloud import firestore

from ..database import run_transaction


@dataclass(frozen=True)
class UnitAllocation:
    seq_no: int
    unit_no: str


def _seq_ref(client: firestore.Client, product_id: str):
    return client.collection("asset_product_seq").document(product_id)


def allocate_unit_no_in(
    transaction: firestore.Transaction,
    client: firestore.Client,
    *,
    product_id: str,
    product_name: str,
) -> UnitAllocation:
    """이미 열려 있는 트랜잭션 안에서 시퀀스만 +1. 유닛 문서 생성은 호출자가 같은
    트랜잭션에 이어붙인다."""
    seq_ref = _seq_ref(client, product_id)
    snap = seq_ref.get(transaction=transaction)
    next_seq = (snap.get("last_seq") if snap.exists else 0) + 1

    transaction.set(seq_ref, {"last_seq": next_seq})

    return UnitAllocation(seq_no=next_seq, unit_no=f"{product_name}-{next_seq:03d}")


def allocate_unit_no(client: firestore.Client, *, product_id: str, product_name: str) -> UnitAllocation:
    """독립 트랜잭션 버전(단독 호출·테스트용)."""
    return run_transaction(
        client,
        lambda txn: allocate_unit_no_in(txn, client, product_id=product_id, product_name=product_name),
    )
