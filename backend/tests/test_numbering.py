from datetime import datetime, timezone

import pytest

from app.errors import AppError
from app.services import numbering

FIXED = datetime(2026, 6, 1, tzinfo=timezone.utc)


def test_first_allocation_is_001(db):
    a = numbering.allocate(db, "A", now=FIXED)
    assert a.mgmt_no == "26-A-001"
    assert (a.seq_year, a.group_code, a.seq_no) == (2026, "A", 1)


def test_sequential_allocation(db):
    nums = [numbering.allocate(db, "A", now=FIXED).mgmt_no for _ in range(3)]
    assert nums == ["26-A-001", "26-A-002", "26-A-003"]


def test_groups_have_independent_sequences(db):
    a = numbering.allocate(db, "A", now=FIXED).mgmt_no
    b = numbering.allocate(db, "B", now=FIXED).mgmt_no
    assert a == "26-A-001"
    assert b == "26-B-001"


def test_retire_creates_gap_and_does_not_reuse(db):
    a1 = numbering.allocate(db, "A", now=FIXED)
    numbering.retire(
        db,
        mgmt_no=a1.mgmt_no,
        seq_year=a1.seq_year,
        group_code=a1.group_code,
        seq_no=a1.seq_no,
        retired_by="Admin",
    )

    a2 = numbering.allocate(db, "A", now=FIXED)

    assert a2.mgmt_no == "26-A-002"  # 001 은 결번, 재사용 안 함
    assert db.collection("retired_numbers").document("26-A-001").get().exists


def test_seq_exhausted_over_999(db):
    db.collection("number_sequences").document("2026-A").set(
        {"seq_year": 2026, "group_code": "A", "last_seq": 999}
    )
    with pytest.raises(AppError) as ei:
        numbering.allocate(db, "A", now=FIXED)
    assert ei.value.code == "SEQ_EXHAUSTED"
    assert ei.value.status_code == 409


def test_year_rollover_resets(db):
    numbering.allocate(db, "A", now=datetime(2026, 12, 31, tzinfo=timezone.utc))
    nxt = numbering.allocate(db, "A", now=datetime(2027, 1, 1, tzinfo=timezone.utc))
    assert nxt.mgmt_no == "27-A-001"
