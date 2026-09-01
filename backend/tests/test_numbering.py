from datetime import datetime, timezone

import pytest

from app.database import SessionLocal
from app.errors import AppError
from app.models import NumberSequence, RetiredNumber
from app.services import numbering

FIXED = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_first_allocation_is_001():
    db = SessionLocal()
    try:
        a = numbering.allocate(db, "A", now=FIXED)
        db.commit()
        assert a.mgmt_no == "26-A-001"
        assert (a.seq_year, a.group_code, a.seq_no) == (2026, "A", 1)
    finally:
        db.close()


def test_sequential_allocation():
    db = SessionLocal()
    try:
        nums = []
        for _ in range(3):
            nums.append(numbering.allocate(db, "A", now=FIXED).mgmt_no)
            db.commit()
        assert nums == ["26-A-001", "26-A-002", "26-A-003"]
    finally:
        db.close()


def test_groups_have_independent_sequences():
    db = SessionLocal()
    try:
        a = numbering.allocate(db, "A", now=FIXED).mgmt_no
        db.commit()
        b = numbering.allocate(db, "B", now=FIXED).mgmt_no
        db.commit()
        assert a == "26-A-001"
        assert b == "26-B-001"
    finally:
        db.close()


def test_retire_creates_gap_and_does_not_reuse():
    db = SessionLocal()
    try:
        a1 = numbering.allocate(db, "A", now=FIXED)
        db.commit()
        numbering.retire(
            db,
            mgmt_no=a1.mgmt_no,
            seq_year=a1.seq_year,
            group_code=a1.group_code,
            seq_no=a1.seq_no,
            retired_by="Admin",
        )
        db.commit()

        a2 = numbering.allocate(db, "A", now=FIXED)
        db.commit()

        assert a2.mgmt_no == "26-A-002"  # 001 은 결번, 재사용 안 함
        assert db.query(RetiredNumber).filter_by(mgmt_no="26-A-001").count() == 1
    finally:
        db.close()


def test_seq_exhausted_over_999():
    db = SessionLocal()
    try:
        db.add(NumberSequence(seq_year=2026, group_code="A", last_seq=999))
        db.commit()
        with pytest.raises(AppError) as ei:
            numbering.allocate(db, "A", now=FIXED)
        assert ei.value.code == "SEQ_EXHAUSTED"
        assert ei.value.status_code == 409
    finally:
        db.close()


def test_year_rollover_resets():
    db = SessionLocal()
    try:
        numbering.allocate(db, "A", now=datetime(2026, 12, 31, tzinfo=timezone.utc))
        db.commit()
        nxt = numbering.allocate(db, "A", now=datetime(2027, 1, 1, tzinfo=timezone.utc))
        db.commit()
        assert nxt.mgmt_no == "27-A-001"
    finally:
        db.close()
