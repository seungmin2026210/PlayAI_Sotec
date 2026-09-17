"""PDF export 단위 테스트 — DB 불필요(순수 함수 + 가짜 Quote).

`export_pdf.py` 는 엑셀과 같은 워크북(`export_excel.build_quote_workbook`)을 셀
그리드째로 그대로 그린다(`tech/09-export.md`) — 그래서 레이아웃 자체를 따로 검증할
필요는 적고(엑셀 쪽 테스트가 이미 셀 값을 검증한다), 여기서는 PDF 고유의 관심사만
확인한다: 항상 렌더링에 성공하는지, 승인 견적서에만 직인 이미지가 추가되는지
(openpyxl 처럼 이미지 개수를 셀 수 없어 바이트 수 증가로 간접 검증), 템플릿 항목
행 수 경계(`QUOTE_TEMPLATE_ITEM_ROWS`)에서 깨지지 않는지.

알려진 한계: 항목이 `QUOTE_TEMPLATE_ITEM_ROWS`(18) 을 초과하는 경우
(`export_excel._extend_item_rows` 가 `ws.insert_rows` 로 행을 늘리는 경로)는
openpyxl 의 병합 셀 처리 한계(삽입 시 기존 병합 범위가 제대로 밀리지 않고 겹치는
경우가 있음)로 세액 열이 비어 보이는 렌더링 버그가 있다 — 엑셀 자체의 기존
이슈이며 이번 PDF 작업 범위 밖이라 여기서는 다루지 않는다(별도 트래킹 필요).
"""
from __future__ import annotations

import datetime
from types import SimpleNamespace as NS

from app.config import QUOTE_TEMPLATE_ITEM_ROWS, SEAL_PATH
from app.services.export_pdf import build_quote_pdf


def _item(idx: int, amount: int = 1_000_000):
    return NS(
        line_no=idx + 1, name=f"항목 {idx + 1}", qty=1, unit_price=amount, line_amount=amount,
        period_start=None, period_end=None,
    )


def _quote(status: str, items=None):
    items = items if items is not None else [
        NS(
            line_no=1, name="개발 용역", qty=1, unit_price=61_378_520, line_amount=61_378_520,
            period_start=datetime.date(2026, 8, 1), period_end=datetime.date(2026, 10, 31),
        )
    ]
    return NS(
        mgmt_no="26-B-008",
        issue_date=datetime.date(2026, 7, 23),
        seq_year=2026, group_code="B", seq_no=8,
        customer_name="삼성중공업(주)", customer_department="자동화인프라T/F",
        customer_contact_name="최성인 TF리더님", customer_contact_phone=None, customer_cc=None,
        status=status, title="LNG 화물창 마킹로봇 운영 개발", issuer_name="홍길동", vat_included=True,
        supply_amount=61_300_000, vat_amount=6_130_000, total_with_vat=67_430_000,
        items_raw_total=61_378_520, items=items,
    )


def test_pdf_always_builds():
    for st in ("SUBMITTED", "APPROVED", "REJECTED", "CANCELLED"):
        pdf = build_quote_pdf(_quote(st))
        assert pdf.startswith(b"%PDF")


def test_pdf_builds_at_item_row_boundary():
    """템플릿이 미리 서식을 잡아둔 항목 행 수(18) 그대로 — 행 확장 경로(overflow)를
    타지 않는 가장 흔한 경우가 안 깨지는지."""
    items = [_item(i) for i in range(QUOTE_TEMPLATE_ITEM_ROWS)]
    pdf = build_quote_pdf(_quote("SUBMITTED", items=items))
    assert pdf.startswith(b"%PDF")


def test_seal_only_on_approved_pdf():
    assert SEAL_PATH.exists(), "임시 직인 파일이 없습니다 — scripts/make_seal.py 실행"
    submitted = build_quote_pdf(_quote("SUBMITTED"))
    approved = build_quote_pdf(_quote("APPROVED"))
    assert len(approved) > len(submitted)  # 승인 견적서에만 직인 이미지가 추가로 임베드된다
