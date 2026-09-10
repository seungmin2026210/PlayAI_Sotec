"""관리번호 채번 — 기획서 6장 / TECH 05, 12(Firestore 트랜잭션).

형식 YY-그룹코드-순번 (예: 26-A-001).
- YY = 등록 시각(서버) 연도의 뒤 2자리 (발행일자 아님).
- (연도, 그룹) 조합별 독립 시퀀스. 연도 바뀌면 001부터.
- 동시성: `number_sequences/{year}-{group_code}` 문서를 Firestore 트랜잭션(낙관적,
  충돌 시 클라이언트가 자동 재시도)으로 읽고 +1 — SQL `SELECT ... FOR UPDATE` 대응.
- 999 초과 시 SEQ_EXHAUSTED (open-11).
- 결번: 삭제 시 last_seq 는 되돌리지 않는다(재사용 금지). retire() 는 대장만 기록.

`*_in(transaction, ...)` 함수들은 **호출자가 이미 시작한 트랜잭션**에 이어붙여 쓴다 —
예: `routers/quotes.py: create_quote`가 채번(allocate_in)과 quote 문서 생성을 하나의
Firestore 트랜잭션으로 묶어야 Postgres 시절과 동일한 원자성이 나온다. `allocate()`/
`retire()`(트랜잭션 없이 호출)는 단독 사용·테스트용 얇은 래퍼.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from google.cloud import firestore

from ..config import MGMT_NO_DISPLAY_PREFIX, SEQ_MAX
from ..database import run_transaction
from ..errors import SEQ_EXHAUSTED, AppError


@dataclass(frozen=True)
class Allocation:
    seq_year: int
    group_code: str
    seq_no: int
    mgmt_no: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def format_mgmt_no(year: int, group_code: str, seq_no: int) -> str:
    return f"{year % 100:02d}-{group_code}-{seq_no:03d}"


def format_mgmt_no_display(seq_year: int, group_code: str, seq_no: int) -> str:
    """출력물(엑셀/PDF)용 견적NO 표기 — '혁신 2026-B 008' 꼴.

    저장 mgmt_no(26-B-008)와 채번 로직은 그대로 두고 표기만 바꾼다. 접두어는
    config.MGMT_NO_DISPLAY_PREFIX. 그룹별 독립 채번이라 (그룹, 연도) 조합의 순번이다.
    """
    year = seq_year if seq_year >= 100 else 2000 + seq_year
    return f"{MGMT_NO_DISPLAY_PREFIX} {year}-{group_code} {seq_no:03d}"


def _seq_ref(client: firestore.Client, year: int, group_code: str):
    return client.collection("number_sequences").document(f"{year}-{group_code}")


def allocate_in(
    transaction: firestore.Transaction,
    client: firestore.Client,
    group_code: str,
    *,
    now: datetime | None = None,
) -> Allocation:
    """이미 열려 있는 트랜잭션 안에서 시퀀스만 +1. 문서 생성은 호출자가 같은
    트랜잭션에 `transaction.set(quotes_ref.document(alloc.mgmt_no), ...)` 로 이어붙인다.
    """
    year = (now or _now()).year
    seq_ref = _seq_ref(client, year, group_code)

    snap = seq_ref.get(transaction=transaction)
    last_seq = snap.get("last_seq") if snap.exists else 0

    if last_seq >= SEQ_MAX:
        raise AppError(
            SEQ_EXHAUSTED,
            409,
            f"해당 그룹/연도 관리번호가 {SEQ_MAX}건을 초과했습니다. 관리자에게 문의하세요.",
        )

    next_seq = last_seq + 1
    transaction.set(seq_ref, {"seq_year": year, "group_code": group_code, "last_seq": next_seq})

    return Allocation(
        seq_year=year,
        group_code=group_code,
        seq_no=next_seq,
        mgmt_no=format_mgmt_no(year, group_code, next_seq),
    )


def allocate(client: firestore.Client, group_code: str, *, now: datetime | None = None) -> Allocation:
    """독립 트랜잭션에서 채번만 수행(단독 호출·테스트용). 실제 견적 등록은
    `routers.quotes.create_quote`가 자신의 트랜잭션 안에서 `allocate_in()`을 직접
    호출해 채번과 quote 문서 생성을 원자적으로 묶는다."""
    return run_transaction(client, lambda txn: allocate_in(txn, client, group_code, now=now))


def retire_in(
    transaction: firestore.Transaction,
    client: firestore.Client,
    *,
    mgmt_no: str,
    seq_year: int,
    group_code: str,
    seq_no: int,
    retired_by: str,
    reason: str = "DELETED",
) -> None:
    """결번 대장에 기록. `number_sequences.last_seq` 는 건드리지 않는다.

    삭제 라우터에서 quote 문서를 `active=False`로 갱신하는 것과 같은 트랜잭션에
    이어붙여 원자적으로 커밋한다."""
    ref = client.collection("retired_numbers").document(mgmt_no)
    transaction.set(
        ref,
        {
            "mgmt_no": mgmt_no,
            "seq_year": seq_year,
            "group_code": group_code,
            "seq_no": seq_no,
            "retired_at": _now(),
            "retired_by": retired_by,
            "reason": reason,
        },
    )


def retire(client: firestore.Client, **kwargs) -> None:
    """독립 트랜잭션 버전(단독 호출·테스트용)."""
    run_transaction(client, lambda txn: retire_in(txn, client, **kwargs))
