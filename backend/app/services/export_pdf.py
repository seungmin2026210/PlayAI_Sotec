"""개별 견적서 PDF — reportlab(순수 파이썬, 네이티브 시스템 라이브러리 의존 없음). TECH 09.

레이아웃은 엑셀(`export_excel.build_quote_xlsx`)과 동일한 실제 견적서.jpg 양식.
APPROVED 견적서는 대표자명 옆에 직인을 합성한다.

이전 구현(WeasyPrint, HTML→PDF)은 시스템 라이브러리(libpango 등)가 필요해 Vercel
Serverless 같은 환경에서 동작하지 않는다(DECISIONS.md 참조). reportlab 은 순수
파이썬 + 폰트 파일 임베드만으로 동작해서 배포 환경을 가리지 않는다.
import/렌더 실패 시 AppError(PDF_UNAVAILABLE, 501) 를 던지고 서버는 계속 동작한다.
"""
from __future__ import annotations

from io import BytesIO

from ..config import (
    COMPANY,
    FONT_BOLD_PATH,
    FONT_REGULAR_PATH,
    GROUPS,
    QUOTE_AUTHOR_ROLE,
    QUOTE_AUTHOR_TEAM,
    QUOTE_CONDITIONS,
    QUOTE_GREETING,
    QUOTE_GREETING_LINES,
    QUOTE_SIGNOFF_COLS,
    QUOTE_VALIDITY_NOTE,
    SEAL_MM,
    SEAL_PATH,
    LOGO_PATH,
    STATUS_APPROVED,
    VAT_RATE,
)
from ..errors import PDF_UNAVAILABLE, AppError
from ..models import Quote
from .calculation import format_won
from .numbering import format_mgmt_no_display

_FONT = "NanumGothic"
_FONT_BOLD = "NanumGothic-Bold"
_PAGE_MARGIN_MM = 14
_fonts_registered = False


def _register_fonts() -> None:
    """폰트 임베드는 프로세스당 1번만(reportlab 전역 레지스트리 재등록은 무해하지만 낭비)."""
    global _fonts_registered
    if _fonts_registered:
        return
    from reportlab.pdfbase import pdfmetrics  # noqa: PLC0415
    from reportlab.pdfbase.ttfonts import TTFont  # noqa: PLC0415

    pdfmetrics.registerFont(TTFont(_FONT, str(FONT_REGULAR_PATH)))
    pdfmetrics.registerFont(TTFont(_FONT_BOLD, str(FONT_BOLD_PATH)))
    _fonts_registered = True


def _build_story(q: Quote) -> list:
    from reportlab.lib import colors  # noqa: PLC0415
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT  # noqa: PLC0415
    from reportlab.lib.styles import ParagraphStyle  # noqa: PLC0415
    from reportlab.lib.units import mm  # noqa: PLC0415
    from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle  # noqa: PLC0415

    normal = ParagraphStyle("normal", fontName=_FONT, fontSize=9, leading=12)
    bold = ParagraphStyle("bold", fontName=_FONT_BOLD, fontSize=9, leading=12)
    title = ParagraphStyle(
        "title", fontName=_FONT_BOLD, fontSize=22, leading=26, alignment=TA_CENTER
    )
    greeting_bold = ParagraphStyle("greeting_bold", fontName=_FONT_BOLD, fontSize=10, leading=14)
    total_label = ParagraphStyle("total_label", fontName=_FONT_BOLD, fontSize=11, leading=15)
    total_value = ParagraphStyle(
        "total_value", fontName=_FONT_BOLD, fontSize=13, leading=17, alignment=TA_RIGHT
    )
    foot_note = ParagraphStyle(
        "foot_note", fontName=_FONT, fontSize=8, leading=11, textColor=colors.HexColor("#666666")
    )
    sum_label = ParagraphStyle("sum_label", fontName=_FONT, fontSize=9, alignment=TA_RIGHT)
    sum_value = ParagraphStyle("sum_value", fontName=_FONT, fontSize=9, alignment=TA_RIGHT)
    sum_value_bold = ParagraphStyle(
        "sum_value_bold", fontName=_FONT_BOLD, fontSize=10, alignment=TA_RIGHT
    )

    def kv_table(rows: list[tuple[str, object]], col_widths=(28 * mm, None)) -> Table:
        """label(볼드, 배경) | value 2열 kv 표. value 가 이미 flowable이면 그대로 쓴다."""
        data = []
        for label, value in rows:
            v = value if hasattr(value, "wrap") else Paragraph(str(value), normal)
            data.append([Paragraph(label, bold), v])
        t = Table(data, colWidths=list(col_widths))
        t.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f4f4f4")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        return t

    story: list = []

    if LOGO_PATH.exists():
        story.append(Image(str(LOGO_PATH), width=28 * mm, height=12 * mm))
        story.append(Spacer(1, 4))
    story.append(Paragraph("견 적 서", title))
    story.append(Spacer(1, 10))

    # ---- 좌: 견적 기본정보 + 수신처 / 우: 공급자 ---------------------------
    left = [
        kv_table(
            [
                ("견적일자", q.issue_date.isoformat()),
                ("견적유효기간", QUOTE_VALIDITY_NOTE),
                ("견적 NO", format_mgmt_no_display(q.seq_year, q.group_code, q.seq_no)),
            ]
        ),
        Spacer(1, 6),
        Paragraph("[ 수신처 (고객사) ]", bold),
        Spacer(1, 2),
        kv_table(
            [
                ("고객사명", q.customer_name),
                (
                    "담당자",
                    f"{q.customer_contact_name or '-'} {q.customer_contact_phone or ''}".strip(),
                ),
                ("C.C", ""),
            ]
        ),
    ]

    ceo_value = f"{COMPANY['ceo_name']} (인)"
    ceo_cell = Paragraph(ceo_value, normal)
    if q.status == STATUS_APPROVED and SEAL_PATH.exists():
        ceo_row = Table(
            [[ceo_cell, Image(str(SEAL_PATH), width=SEAL_MM * mm, height=SEAL_MM * mm)]],
            colWidths=[None, SEAL_MM * mm + 2],
        )
        ceo_row.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        ceo_value_flowable = ceo_row
    else:
        ceo_value_flowable = ceo_cell

    right = [
        Paragraph("[ 공급자 (자사) ]", bold),
        Spacer(1, 2),
        kv_table(
            [
                ("등록번호", COMPANY["biz_no"]),
                ("상호", COMPANY["name"]),
                ("대표자", ceo_value_flowable),
                ("주소", COMPANY.get("address", "")),
                ("업태 / 종목", f"{COMPANY.get('biz_type', '')} / {COMPANY.get('biz_item', '')}"),
                ("전화 / FAX", f"{COMPANY.get('tel', '')} / {COMPANY.get('fax', '')}"),
                (
                    "견적 작성자",
                    f"{QUOTE_AUTHOR_TEAM} {GROUPS.get(q.group_code, '')} / {QUOTE_AUTHOR_ROLE}",
                ),
            ]
        ),
    ]

    head = Table([[left, right]], colWidths=["48%", "52%"])
    head.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(head)
    story.append(Spacer(1, 12))

    # ---- 인사말 -----------------------------------------------------------
    story.append(Paragraph(QUOTE_GREETING, greeting_bold))
    for line in QUOTE_GREETING_LINES:
        story.append(Paragraph(line, normal))
    story.append(Spacer(1, 10))

    # ---- 합계금액 요약 -----------------------------------------------------
    total_box = Table(
        [[Paragraph("합계금액 (공급가액 + 세액)", total_label), Paragraph(format_won(q.total_with_vat), total_value)]],
        colWidths=["60%", "40%"],
    )
    total_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#333333")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7f7f7")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(total_box)
    story.append(Spacer(1, 10))

    # ---- 용역(계약) --------------------------------------------------------
    story.append(kv_table([("용역(계약)명", q.title), ("용역(계약) 기간", "")]))
    story.append(Spacer(1, 10))

    # ---- 항목 표 ------------------------------------------------------------
    header_style = ParagraphStyle("items_head", fontName=_FONT_BOLD, fontSize=9, alignment=TA_CENTER)
    headers = ["No", "품목", "규격", "수량", "단가", "공급가액", "세액", "비고"]
    rows = [[Paragraph(h, header_style) for h in headers]]
    for it in q.items:
        line_vat = round(it.line_amount * VAT_RATE)
        rows.append(
            [
                Paragraph(str(it.line_no), ParagraphStyle("c", fontName=_FONT, fontSize=9, alignment=TA_CENTER)),
                Paragraph(it.name, normal),
                "",
                Paragraph(f"{it.qty:,}", ParagraphStyle("r", fontName=_FONT, fontSize=9, alignment=TA_RIGHT)),
                Paragraph(format_won(it.unit_price), ParagraphStyle("r2", fontName=_FONT, fontSize=9, alignment=TA_RIGHT)),
                Paragraph(format_won(it.line_amount), ParagraphStyle("r3", fontName=_FONT, fontSize=9, alignment=TA_RIGHT)),
                Paragraph(format_won(line_vat), ParagraphStyle("r4", fontName=_FONT, fontSize=9, alignment=TA_RIGHT)),
                "",
            ]
        )
    items_table = Table(
        rows, colWidths=[10 * mm, None, 16 * mm, 14 * mm, 22 * mm, 24 * mm, 20 * mm, 16 * mm]
    )
    items_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 6))

    # ---- 합계 블록 -----------------------------------------------------------
    sum_rows = [
        [Paragraph("공급가액 합계 (십만단위 절사)", sum_label), Paragraph(format_won(q.supply_amount), sum_value)],
        [Paragraph("세액 (10%)", sum_label), Paragraph(format_won(q.vat_amount), sum_value)],
        [Paragraph("합계금액", ParagraphStyle("sl2", fontName=_FONT_BOLD, fontSize=10, alignment=TA_RIGHT)), Paragraph(format_won(q.total_with_vat), sum_value_bold)],
    ]
    sum_table = Table(sum_rows, colWidths=[None, 40 * mm], hAlign="RIGHT")
    sum_table.setStyle(
        TableStyle(
            [
                ("LINEBELOW", (0, 0), (-1, 1), 0.5, colors.HexColor("#dddddd")),
                ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#333333")),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(sum_table)

    vat_note = (
        "부가세 포함 견적입니다. 고객 실지불액은 '합계금액' 기준입니다."
        if q.vat_included
        else "부가세 미포함(별도) 견적입니다. 공급가액 기준이며 부가세는 별도입니다."
    )
    story.append(
        Paragraph(f"* 항목 합계 {q.items_raw_total:,}원 · 합계는 총액 기준 십만단위 절사. {vat_note}", foot_note)
    )
    story.append(Spacer(1, 10))

    # ---- 대금결제조건 / 납품조건 / WORK SCOPE ---------------------------------
    for n, (label, text) in enumerate(QUOTE_CONDITIONS, start=3):
        story.append(Paragraph(f"<b>{n}. {label}</b> : {text}", normal))
    story.append(Spacer(1, 14))

    # ---- 서명란 ---------------------------------------------------------------
    signoff_head = [Paragraph(c, header_style) for c in QUOTE_SIGNOFF_COLS]
    signoff = Table([signoff_head, ["", "", ""]], colWidths=[25 * mm] * len(QUOTE_SIGNOFF_COLS), rowHeights=[8 * mm, 16 * mm], hAlign="RIGHT")
    signoff.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    story.append(signoff)
    return story


def build_quote_pdf(q: Quote) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4  # noqa: PLC0415
        from reportlab.lib.units import mm  # noqa: PLC0415
        from reportlab.platypus import SimpleDocTemplate  # noqa: PLC0415

        _register_fonts()
    except Exception as exc:  # pragma: no cover - 환경 의존(폰트 파일 누락 등)
        raise AppError(
            PDF_UNAVAILABLE,
            501,
            "이 환경에서는 PDF 생성이 비활성화되어 있습니다. 엑셀 export 를 이용하세요.",
        ) from exc

    try:
        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=_PAGE_MARGIN_MM * mm,
            rightMargin=_PAGE_MARGIN_MM * mm,
            topMargin=_PAGE_MARGIN_MM * mm,
            bottomMargin=_PAGE_MARGIN_MM * mm,
            title=f"견적서 {q.mgmt_no}",
        )
        doc.build(_build_story(q))
        return buf.getvalue()
    except Exception as exc:  # pragma: no cover
        raise AppError(
            PDF_UNAVAILABLE, 501, "PDF 생성 중 오류가 발생했습니다. 엑셀 export 를 이용하세요."
        ) from exc
