"""관리번호 채번 — 기획서 6장 / TECH 05.

형식 YY-그룹코드-순번 (예: 26-A-001).
- YY = 등록 시각(서버) 연도의 뒤 2자리 (발행일자 아님).
- (연도, 그룹) 조합별 독립 시퀀스. 연도 바뀌면 001부터.
- 동시성: number_sequences 행을 SELECT ... FOR UPDATE 로 잠근 뒤 +1.
- 999 초과 시 SEQ_EXHAUSTED (open-11).
- 결번: 삭제 시 last_seq 는 되돌리지 않는다(재사용 금지). retire() 는 대장만 기록.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..config import SEQ_MAX
from ..errors import SEQ_EXHAUSTED, AppError
from ..models import NumberSequence, RetiredNumber


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


def allocate(db: Session, group_code: str, *, now: datetime | None = None) -> Allocation:
    """같은 트랜잭션 안에서 호출할 것. 커밋은 호출자 책임."""
    year = (now or _now()).year

    # 행이 없으면 만든다(경합 무시).
    db.execute(
        pg_insert(NumberSequence)
        .values(seq_year=year, group_code=group_code, last_seq=0)
        .on_conflict_do_nothing(index_elements=["seq_year", "group_code"])
    )
    db.flush()

    row = db.execute(
        select(NumberSequence)
        .where(
            NumberSequence.seq_year == year,
            NumberSequence.group_code == group_code,
        )
        .with_for_update()
    ).scalar_one()

    if row.last_seq >= SEQ_MAX:
        raise AppError(
            SEQ_EXHAUSTED,
            409,
            f"해당 그룹/연도 관리번호가 {SEQ_MAX}건을 초과했습니다. 관리자에게 문의하세요.",
        )

    row.last_seq += 1
    seq_no = row.last_seq
    db.flush()

    return Allocation(
        seq_year=year,
        group_code=group_code,
        seq_no=seq_no,
        mgmt_no=format_mgmt_no(year, group_code, seq_no),
    )


def retire(db: Session, *, mgmt_no: str, seq_year: int, group_code: str,
           seq_no: int, retired_by: str, reason: str = "DELETED") -> None:
    """삭제된 관리번호를 결번 대장에 기록. last_seq 는 건드리지 않는다."""
    db.add(
        RetiredNumber(
            mgmt_no=mgmt_no,
            seq_year=seq_year,
            group_code=group_code,
            seq_no=seq_no,
            retired_by=retired_by,
            reason=reason,
        )
    )
    db.flush()
