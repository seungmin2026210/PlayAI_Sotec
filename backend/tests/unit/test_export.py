"""Export 단위 테스트 — DB 불필요(순수 함수 + 가짜 Quote).

검증 대상:
- 승인(APPROVED) 견적서 xlsx 에만 직인이 합성된다(SUBMITTED 는 안 됨).
- 출력용 견적NO 표기(`혁신 2026-B 008`).
"""
from __future__ import annotations

import datetime
import io
from types import SimpleNamespace as NS

import openpyxl

from app.config import SEAL_PATH
from app.services.export_excel import build_quote_xlsx
from app.services.numbering import format_mgmt_no_display


def _quote(status: str):
    items = [NS(line_no=1, name="개발 용역", qty=1, unit_price=61_378_520, line_amount=61_378_520)]
    return NS(
        issue_date=datetime.date(2026, 7, 23),
        seq_year=2026, group_code="B", seq_no=8, mgmt_no="26-B-008",
        customer_name="삼성중공업(주)", customer_contact_name="최성인", customer_contact_phone=None,
        status=status, title="LNG 화물창 마킹로봇 운영 개발", issuer_name="홍길동", vat_included=True,
        supply_amount=61_300_000, vat_amount=6_130_000, total_with_vat=67_430_000,
        items_raw_total=61_378_520, items=items,
    )


def _image_count(xlsx_bytes: bytes) -> int:
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    return len(wb.active._images)


def test_mgmt_no_display_format():
    assert format_mgmt_no_display(2026, "B", 8) == "혁신 2026-B 008"
    assert format_mgmt_no_display(26, "A", 1) == "혁신 2026-A 001"


def test_seal_only_on_approved_xlsx():
    assert SEAL_PATH.exists(), "임시 직인 파일이 없습니다 — scripts/make_seal.py 실행"
    submitted = _image_count(build_quote_xlsx(_quote("SUBMITTED")))
    approved = _image_count(build_quote_xlsx(_quote("APPROVED")))
    assert approved == submitted + 1  # 승인 견적서에만 직인 1개 추가


def test_xlsx_always_builds():
    for st in ("SUBMITTED", "APPROVED", "REJECTED", "CANCELLED"):
        assert len(build_quote_xlsx(_quote(st))) > 0
