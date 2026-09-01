"""엑셀 export — openpyxl. TECH 09."""
from __future__ import annotations

import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, Side

from ..config import COMPANY, GROUPS, STATUS_LABELS
from ..models import Quote

_WON = '#,##0"원"'
_BOLD = Font(bold=True)
_TITLE = Font(bold=True, size=14)
_thin = Side(style="thin", color="999999")
_BOX = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)


def _kv(ws, row: int, label: str, value) -> int:
    ws.cell(row=row, column=1, value=label).font = _BOLD
    ws.cell(row=row, column=2, value=value)
    return row + 1


def build_quote_xlsx(q: Quote) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "견적서"
    ws.column_dimensions["A"].width = 18
    for col in ("B", "C", "D", "E"):
        ws.column_dimensions[col].width = 20

    r = 1
    ws.cell(row=r, column=1, value="견 적 서").font = _TITLE
    r += 2

    ws.cell(row=r, column=1, value="[ 공급자 (자사) ]").font = _BOLD
    r += 1
    r = _kv(ws, r, "회사명", COMPANY["name"])
    r = _kv(ws, r, "사업자등록번호", COMPANY["biz_no"])
    r = _kv(ws, r, "대표자명", COMPANY["ceo_name"])
    r = _kv(ws, r, "주소", COMPANY.get("address", ""))
    r = _kv(ws, r, "연락처", COMPANY.get("tel", ""))
    r += 1

    ws.cell(row=r, column=1, value="[ 수신처 (고객사) ]").font = _BOLD
    r += 1
    r = _kv(ws, r, "고객사명", q.customer_name)
    r = _kv(ws, r, "담당자", q.customer_contact_name or "")
    r = _kv(ws, r, "연락처", q.customer_contact_phone or "")
    r += 1

    ws.cell(row=r, column=1, value="[ 견적 정보 ]").font = _BOLD
    r += 1
    r = _kv(ws, r, "관리번호", q.mgmt_no)
    r = _kv(ws, r, "견적서명", q.title)
    r = _kv(ws, r, "그룹", f"{q.group_code} ({GROUPS.get(q.group_code, '')})")
    r = _kv(ws, r, "발행일자", q.issue_date.isoformat())
    r = _kv(ws, r, "발행 담당자", q.issuer_name)
    r = _kv(ws, r, "상태", STATUS_LABELS.get(q.status, q.status))
    r = _kv(ws, r, "구매관리 반영", "예(읽기전용)" if q.purchase_locked else "아니오")
    r += 1

    # 항목 표
    headers = ["No", "품목", "갯수", "단가(공급가액)", "금액"]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=r, column=c, value=h)
        cell.font = _BOLD
        cell.border = _BOX
        cell.alignment = Alignment(horizontal="center")
    r += 1

    for item in q.items:
        ws.cell(row=r, column=1, value=item.line_no).border = _BOX
        ws.cell(row=r, column=2, value=item.name).border = _BOX
        c3 = ws.cell(row=r, column=3, value=item.qty)
        c3.border = _BOX
        c3.number_format = "#,##0"
        c4 = ws.cell(row=r, column=4, value=item.unit_price)
        c4.border = _BOX
        c4.number_format = _WON
        c5 = ws.cell(row=r, column=5, value=item.line_amount)
        c5.border = _BOX
        c5.number_format = _WON
        r += 1

    r += 1
    # 합계 블록
    def money_row(label: str, value: int) -> None:
        nonlocal r
        ws.cell(row=r, column=4, value=label).font = _BOLD
        vc = ws.cell(row=r, column=5, value=value)
        vc.number_format = _WON
        r += 1

    money_row("항목 합계", q.items_raw_total)
    money_row("공급가액 합계(십만단위 절사)", q.supply_amount)
    money_row("부가세 (10%)", q.vat_amount)
    money_row("부가세 포함가", q.total_with_vat)
    r += 1
    ws.cell(
        row=r, column=1,
        value=("부가세 포함 견적입니다. 고객 실지불액은 '부가세 포함가' 기준입니다."
               if q.vat_included
               else "부가세 미포함(별도) 견적입니다. 공급가액 기준이며 부가세는 별도입니다."),
    ).font = Font(italic=True)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_list_xlsx(quotes: list[Quote]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "견적서 목록"

    headers = [
        "관리번호", "그룹코드", "그룹명", "견적서명", "수신처", "발행일자",
        "발행담당자", "공급가액", "부가세", "부가세포함가", "부가세포함여부",
        "상태", "잠금여부", "등록시간",
    ]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = _BOLD
    widths = [12, 8, 18, 30, 24, 12, 12, 14, 12, 14, 12, 10, 8, 20]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = w

    for row_idx, q in enumerate(quotes, start=2):
        vals = [
            q.mgmt_no,
            q.group_code,
            GROUPS.get(q.group_code, ""),
            q.title,
            q.customer_name,
            q.issue_date.isoformat(),
            q.issuer_name,
            q.supply_amount,
            q.vat_amount,
            q.total_with_vat,
            "포함" if q.vat_included else "미포함",
            STATUS_LABELS.get(q.status, q.status),
            "잠금" if q.purchase_locked else "",
            q.created_at.strftime("%Y-%m-%d %H:%M") if q.created_at else "",
        ]
        for c, v in enumerate(vals, start=1):
            cell = ws.cell(row=row_idx, column=c, value=v)
            if c in (8, 9, 10):
                cell.number_format = _WON

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def list_filename() -> str:
    return f"quotes_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
