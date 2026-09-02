"""엑셀 export — openpyxl. TECH 09.

개별 견적서(`build_quote_xlsx`)는 실제 견적서.jpg 양식을 따른다:
상단 자사/수신처 블록 → 인사말 → 합계금액 → 용역(계약) → 항목표(규격·세액·비고 포함)
→ 합계 블록 → 대금결제/납품/WORK SCOPE → 서명란. APPROVED 견적서는 대표자명 옆에
직인(config.SEAL_PATH)을 합성한다. 목록(`build_list_xlsx`)은 변경 없음.
"""
from __future__ import annotations

import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from ..config import (
    COMPANY,
    GROUPS,
    LOGO_PATH,
    QUOTE_AUTHOR_ROLE,
    QUOTE_AUTHOR_TEAM,
    QUOTE_CONDITIONS,
    QUOTE_GREETING,
    QUOTE_GREETING_LINES,
    QUOTE_SIGNOFF_COLS,
    QUOTE_VALIDITY_NOTE,
    SEAL_MM,
    SEAL_PATH,
    STATUS_APPROVED,
    STATUS_LABELS,
    VAT_RATE,
)
from ..models import Quote
from .numbering import format_mgmt_no_display

_WON = '#,##0"원"'
_BOLD = Font(bold=True)
_TITLE = Font(bold=True, size=20)
_ITALIC = Font(italic=True, color="666666", size=9)
_thin = Side(style="thin", color="999999")
_BOX = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)
_HEAD_FILL = PatternFill("solid", fgColor="F2F2F2")
_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
_LEFT = Alignment(horizontal="left", vertical="center", wrap_text=True)
_RIGHT = Alignment(horizontal="right", vertical="center")

_NCOLS = 9  # A..I


def _add_logo(ws) -> int:
    """워크시트 좌상단(A1)에 회사 로고. Pillow 미설치 등 실패 시 조용히 건너뛴다."""
    if not LOGO_PATH.exists():
        return 1
    try:
        from openpyxl.drawing.image import Image as XLImage  # noqa: PLC0415

        img = XLImage(str(LOGO_PATH))
        img.width, img.height = 110, 48
        ws.add_image(img, "A1")
        ws.row_dimensions[1].height = 36
        ws.row_dimensions[2].height = 20
        return 4
    except Exception:  # pragma: no cover - 환경 의존(Pillow 등)
        return 1


def _put(ws, cell: str, value, *, font=None, align=None, box=False, fill=False):
    c = ws[cell]
    c.value = value
    if font:
        c.font = font
    if align:
        c.alignment = align
    if box:
        c.border = _BOX
    if fill:
        c.fill = _HEAD_FILL
    return c


def _stamp_seal(ws, cell: str) -> None:
    """APPROVED 견적서에 직인 합성. 파일/ Pillow 없으면 조용히 생략(로고와 동일 방침)."""
    if not SEAL_PATH.exists():
        return
    try:
        from openpyxl.drawing.image import Image as XLImage  # noqa: PLC0415

        px = int(SEAL_MM / 25.4 * 96)  # mm -> px @96dpi
        img = XLImage(str(SEAL_PATH))
        img.width = img.height = px
        ws.add_image(img, cell)
    except Exception:  # pragma: no cover - 환경 의존
        pass


def build_quote_xlsx(q: Quote) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "견적서"
    ws.sheet_view.showGridLines = False
    widths = [5, 16, 12, 12, 8, 13, 14, 13, 12]  # A..I
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    r = _add_logo(ws)

    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=_NCOLS)
    _put(ws, f"A{r}", "견 적 서", font=_TITLE, align=_CENTER)
    ws.row_dimensions[r].height = 30
    r += 2

    # ---- 좌: 견적 기본정보 / 우: 공급자 -------------------------------------
    top = r
    _put(ws, f"A{r}", "견적일자", font=_BOLD)
    _put(ws, f"B{r}", q.issue_date.isoformat())
    _put(ws, f"E{r}", "[ 공급자 (자사) ]", font=_BOLD)
    r += 1
    _put(ws, f"A{r}", "견적유효기간", font=_BOLD)
    _put(ws, f"B{r}", QUOTE_VALIDITY_NOTE)
    _put(ws, f"E{r}", "등록번호", font=_BOLD)
    _put(ws, f"F{r}", COMPANY["biz_no"])
    r += 1
    _put(ws, f"A{r}", "견적 NO", font=_BOLD)
    _put(ws, f"B{r}", format_mgmt_no_display(q.seq_year, q.group_code, q.seq_no))
    _put(ws, f"E{r}", "상호", font=_BOLD)
    _put(ws, f"F{r}", COMPANY["name"])
    _put(ws, f"H{r}", "대표자", font=_BOLD)
    ceo_cell = f"I{r}"
    _put(ws, ceo_cell, f"{COMPANY['ceo_name']} (인)")
    if q.status == STATUS_APPROVED:
        _stamp_seal(ws, ceo_cell)
    r += 1
    _put(ws, f"E{r}", "주소", font=_BOLD)
    _put(ws, f"F{r}", COMPANY.get("address", ""))
    r += 1
    _put(ws, f"A{r}", "[ 수신처 (고객사) ]", font=_BOLD)
    _put(ws, f"E{r}", "업태", font=_BOLD)
    _put(ws, f"F{r}", COMPANY.get("biz_type", ""))
    _put(ws, f"H{r}", "종목", font=_BOLD)
    _put(ws, f"I{r}", COMPANY.get("biz_item", ""))
    r += 1
    _put(ws, f"A{r}", "고객사명", font=_BOLD)
    _put(ws, f"B{r}", q.customer_name)
    _put(ws, f"E{r}", "전화번호", font=_BOLD)
    _put(ws, f"F{r}", COMPANY.get("tel", ""))
    _put(ws, f"H{r}", "FAX", font=_BOLD)
    _put(ws, f"I{r}", COMPANY.get("fax", ""))
    r += 1
    _put(ws, f"A{r}", "담당자", font=_BOLD)
    _put(ws, f"B{r}", q.customer_contact_name or "")
    _put(ws, f"C{r}", q.customer_contact_phone or "")
    _put(ws, f"E{r}", "견적 작성자", font=_BOLD)
    _put(ws, f"F{r}", f"{QUOTE_AUTHOR_TEAM} {GROUPS.get(q.group_code, '')} / {QUOTE_AUTHOR_ROLE}")
    r += 1
    _put(ws, f"A{r}", "C.C", font=_BOLD)
    _put(ws, f"B{r}", "")  # 참조자 — 데이터 없음(양식 자리만)
    r = max(r, top + 8) + 2

    # ---- 인사말 ----------------------------------------------------------
    _put(ws, f"A{r}", QUOTE_GREETING, font=_BOLD)
    r += 1
    for line in QUOTE_GREETING_LINES:
        _put(ws, f"A{r}", line)
        r += 1
    r += 1

    # ---- 합계금액 요약 --------------------------------------------------
    _put(ws, f"A{r}", "합계금액 (공급가액 + 세액)", font=_BOLD, box=True, fill=True)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=4)
    tc = _put(ws, f"B{r}", q.total_with_vat, font=Font(bold=True, size=13), align=_RIGHT, box=True)
    tc.number_format = _WON
    r += 2

    # ---- 용역(계약) ---------------------------------------------------
    _put(ws, f"A{r}", "용역(계약)명", font=_BOLD)
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=_NCOLS)
    _put(ws, f"B{r}", q.title, align=_LEFT)
    r += 1
    _put(ws, f"A{r}", "용역(계약) 기간", font=_BOLD)
    _put(ws, f"B{r}", "")  # 데이터 없음(양식 자리만)
    r += 2

    # ---- 항목 표 ----------------------------------------------------
    headers = ["No", "품목", "규격", "수량", "단가", "공급가액", "세액", "비고"]
    # 품목 2칸(B:C) 병합 → 실제 열 매핑
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
    col_map = [1, 2, 4, 5, 6, 7, 8, 9]
    for h, col in zip(headers, col_map):
        _put(ws, f"{get_column_letter(col)}{r}", h, font=_BOLD, align=_CENTER, box=True, fill=True)
    ws[f"C{r}"].border = _BOX
    r += 1

    for it in q.items:
        line_vat = round(it.line_amount * VAT_RATE)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        _put(ws, f"A{r}", it.line_no, align=_CENTER, box=True)
        _put(ws, f"B{r}", it.name, align=_LEFT, box=True)
        ws[f"C{r}"].border = _BOX
        _put(ws, f"D{r}", "", box=True)  # 규격
        _put(ws, f"E{r}", it.qty, align=_RIGHT, box=True).number_format = "#,##0"
        _put(ws, f"F{r}", it.unit_price, align=_RIGHT, box=True).number_format = _WON
        _put(ws, f"G{r}", it.line_amount, align=_RIGHT, box=True).number_format = _WON
        _put(ws, f"H{r}", line_vat, align=_RIGHT, box=True).number_format = _WON
        _put(ws, f"I{r}", "", box=True)  # 비고
        r += 1
    r += 1

    # ---- 합계 블록 ------------------------------------------------
    def sum_row(label: str, value: int, *, bold=False) -> None:
        nonlocal r
        f = Font(bold=True) if bold else None
        _put(ws, f"F{r}", label, font=f or _BOLD, align=_RIGHT)
        ws.merge_cells(start_row=r, start_column=7, end_row=r, end_column=8)
        vc = _put(ws, f"G{r}", value, font=f, align=_RIGHT)
        vc.number_format = _WON
        r += 1

    sum_row("공급가액 합계 (십만단위 절사)", q.supply_amount)
    sum_row("세액 (10%)", q.vat_amount)
    sum_row("합계금액", q.total_with_vat, bold=True)
    _put(
        ws, f"A{r}",
        f"* 항목 합계 {q.items_raw_total:,}원 · 합계는 총액 기준 십만단위 절사. "
        + ("부가세 포함 견적(고객 실지불액 = 합계금액)." if q.vat_included
           else "부가세 미포함(별도) 견적."),
        font=_ITALIC,
    )
    r += 2

    # ---- 대금결제조건 / 납품조건 / WORK SCOPE -------------------
    for i, (label, text) in enumerate(QUOTE_CONDITIONS, start=3):
        _put(ws, f"A{r}", f"{i}. {label}", font=_BOLD)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=_NCOLS)
        _put(ws, f"B{r}", text, align=_LEFT)
        r += 1
    r += 1

    # ---- 서명란 -------------------------------------------------
    _put(ws, f"F{r}", "결재", font=_BOLD, align=_CENTER, box=True, fill=True)
    for j, col in enumerate(QUOTE_SIGNOFF_COLS):
        cl = get_column_letter(7 + j)
        _put(ws, f"{cl}{r}", col, font=_BOLD, align=_CENTER, box=True, fill=True)
    r += 1
    ws.row_dimensions[r].height = 44
    _put(ws, f"F{r}", "", box=True)
    for j in range(len(QUOTE_SIGNOFF_COLS)):
        _put(ws, f"{get_column_letter(7 + j)}{r}", "", box=True)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def build_list_xlsx(quotes: list[Quote]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "견적서 목록"

    header_row = _add_logo(ws)
    headers = [
        "관리번호", "그룹코드", "그룹명", "견적서명", "수신처", "발행일자",
        "발행담당자", "공급가액", "부가세", "부가세포함가", "부가세포함여부",
        "상태", "잠금여부", "등록시간",
    ]
    for c, h in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=c, value=h)
        cell.font = _BOLD
    widths = [12, 8, 18, 30, 24, 12, 12, 14, 12, 14, 12, 10, 8, 20]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=header_row, column=i).column_letter].width = w

    for offset, q in enumerate(quotes, start=1):
        row_idx = header_row + offset
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
