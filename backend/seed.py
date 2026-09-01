"""데모 데이터 시드. `alembic upgrade head` 이후 실행.

  python seed.py            # 기존 데이터 유지, 없으면 샘플 생성
  python seed.py --reset    # quotes/items/sequences/retired 전부 삭제 후 재생성
"""
from __future__ import annotations

import sys
from datetime import date

from sqlalchemy import delete, select

from app.config import STATUS_SUBMITTED
from app.database import SessionLocal
from app.models import NumberSequence, Quote, QuoteItem, RetiredNumber
from app.services import numbering
from app.services.calculation import compute

SAMPLES = [
    dict(
        group_code="A", title="사내 형상관리 도구 라이선스 견적", issue_date=date(2026, 3, 4),
        issuer_name="김담당", customer_name="(주)가나다소프트",
        customer_contact_name="이과장", customer_contact_phone="010-1111-2222",
        vat_included=True,
        items=[("GitLab Ultimate 25석", 25, 480_000), ("도입 컨설팅", 1, 3_000_000)],
    ),
    dict(
        group_code="A", title="정적분석 SW 갱신 견적", issue_date=date(2026, 5, 20),
        issuer_name="김담당", customer_name="(주)가나다소프트",
        customer_contact_name="이과장", customer_contact_phone=None,
        vat_included=False,
        items=[("SonarQube Enterprise 연간", 1, 12_400_000)],
    ),
    dict(
        group_code="B", title="협업 메신저 엔터프라이즈 견적", issue_date=date(2026, 6, 1),
        issuer_name="박프로", customer_name="스마트커머스",
        customer_contact_name=None, customer_contact_phone=None,
        vat_included=True,
        items=[("Slack Business+ 120석", 120, 15_000), ("SSO 연동 셋업", 1, 1_500_000)],
    ),
]


class _I:
    def __init__(self, name, qty, unit_price):
        self.name, self.qty, self.unit_price = name, qty, unit_price


def reset(db) -> None:
    db.execute(delete(QuoteItem))
    db.execute(delete(Quote))
    db.execute(delete(RetiredNumber))
    db.execute(delete(NumberSequence))
    db.commit()
    print("reset: 기존 데이터 삭제 완료")


def seed(db) -> None:
    existing = db.execute(select(Quote.id).limit(1)).first()
    if existing:
        print("seed: 기존 견적서가 있어 건너뜁니다. (--reset 으로 초기화 가능)")
        return

    for s in SAMPLES:
        items = [_I(*t) for t in s["items"]]
        c = compute(items)
        alloc = numbering.allocate(db, s["group_code"], now=None)
        q = Quote(
            mgmt_no=alloc.mgmt_no, seq_year=alloc.seq_year,
            group_code=alloc.group_code, seq_no=alloc.seq_no,
            title=s["title"], issue_date=s["issue_date"], issuer_name=s["issuer_name"],
            customer_name=s["customer_name"],
            customer_contact_name=s["customer_contact_name"],
            customer_contact_phone=s["customer_contact_phone"],
            vat_included=s["vat_included"],
            supply_amount=c.supply_amount, vat_amount=c.vat_amount,
            total_with_vat=c.total_with_vat, items_raw_total=c.raw_total,
            status=STATUS_SUBMITTED, purchase_locked=False, created_by="Admin",
        )
        for idx, it in enumerate(items, start=1):
            q.items.append(QuoteItem(
                line_no=idx, name=it.name, qty=it.qty,
                unit_price=it.unit_price, line_amount=it.qty * it.unit_price,
            ))
        db.add(q)
        db.commit()
        print(f"seed: {alloc.mgmt_no}  {s['title']}")

    print("seed: 완료")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        if "--reset" in sys.argv:
            reset(db)
        seed(db)
    finally:
        db.close()
