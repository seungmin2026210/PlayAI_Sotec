"""개별 견적서 PDF — reportlab(순수 파이썬, 네이티브 시스템 라이브러리 의존 없음). TECH 09.

**엑셀과 같은 워크북을 셀 그리드째로 그대로 그린다** — `export_excel.build_quote_workbook(q)`
로 얻은, 실제 위탁계약형 템플릿(`quote_template_consignment.xlsx`)에 값이 채워진 openpyxl
워크시트를 정본으로 삼아 열 너비·행 높이·병합·테두리·배경색·정렬·굵기까지 좌표 계산해서
그대로 재현한다(엑셀 파일을 별도 프로그램으로 변환하는 게 아니라, 같은 셀 데이터를 reportlab
캔버스에 직접 그리는 방식 — 네이티브 라이브러리 의존 없이 Vercel Serverless 에서도 동작).
따라서 엑셀 서식이 바뀌면(템플릿 파일 교체) PDF 도 그대로 따라간다 — 별도로 맞출 것이 없다.

엑셀은 공급가액/세액/합계·항목별 세액을 시트 수식(`=ROUND(...)`, `=ROUNDDOWN(...)`)으로 남겨
Excel 이 열 때 재계산하지만, PDF 는 수식 엔진이 없으므로 이 값들만 `Quote`(이미 계산된 정본,
`services/calculation.py`)에서 가져와 덮어써 그린다(`_value_overrides`) — 그 외 모든 셀은
워크북에 있는 값(라벨 문구·인사말·대금결제조건 등, 위탁계약형 전면대체 이후 굵게 처리한
rich-text 포함)을 그대로 사용한다.

APPROVED 견적서의 직인은 엑셀과 같은 위치 계산(`config.SEAL_MM`/`SEAL_OFFSET_X_MM`, 대표자
셀 L4 기준)으로 별도 그린다 — openpyxl 이 이미 셀 그리드에 심어 둔 이미지 앵커를 그대로
읽지 않고 같은 상수로 재계산하는 이유는, openpyxl 의 앵커 내부 구조(OneCellAnchor/EMU)를
파싱하는 것보다 엑셀과 동일한 계산식을 그대로 재사용하는 편이 더 견고하기 때문.

이전 구현(WeasyPrint, HTML→PDF)은 시스템 라이브러리(libpango 등)가 필요해 Vercel
Serverless 같은 환경에서 동작하지 않는다(DECISIONS.md 참조). reportlab 은 순수
파이썬 + 폰트 파일 임베드만으로 동작해서 배포 환경을 가리지 않는다.
import/렌더 실패 시 AppError(PDF_UNAVAILABLE, 501) 를 던지고 서버는 계속 동작한다.
"""
from __future__ import annotations

from io import BytesIO

from ..config import (
    FONT_BOLD_PATH,
    FONT_REGULAR_PATH,
    SEAL_MM,
    SEAL_OFFSET_X_MM,
    SEAL_PATH,
    STATUS_APPROVED,
    VAT_RATE,
)
from ..errors import PDF_UNAVAILABLE, AppError
from ..models import Quote
from .calculation import format_won
from .export_excel import ITEM_FIRST_ROW, build_quote_workbook

_FONT = "NanumGothic"
_FONT_BOLD = "NanumGothic-Bold"
_MM = 72 / 25.4  # pt per mm
_CELL_PAD = 3.0  # 셀 안쪽 여백(pt, 미확대 기준)
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


def _col_widths_pt(ws) -> dict[int, float]:
    """엑셀 열 너비(문자 단위) → pt. `width*7+5` 는 Excel 기본 폰트(Calibri 11) 기준
    문자폭→픽셀 근사식(SheetJS 등에서 널리 쓰는 변환), 96dpi 픽셀을 pt 로 환산(*0.75)."""
    from openpyxl.utils import get_column_letter  # noqa: PLC0415

    default_w = ws.sheet_format.defaultColWidth or 8.43
    widths = {}
    for c in range(ws.min_column, ws.max_column + 1):
        dim = ws.column_dimensions.get(get_column_letter(c))
        w_chars = dim.width if dim and dim.width else default_w
        widths[c] = (w_chars * 7 + 5) * 0.75
    return widths


def _row_heights_pt(ws) -> dict[int, float]:
    """엑셀 행 높이는 이미 pt 단위(엑셀 내부 단위 자체가 pt)라 변환이 필요 없다."""
    default_h = ws.sheet_format.defaultRowHeight or 15.0
    heights = {}
    for r in range(ws.min_row, ws.max_row + 1):
        dim = ws.row_dimensions.get(r)
        heights[r] = dim.height if dim and dim.height else default_h
    return heights


def _cumulative(sizes: dict[int, float], keys: list[int]) -> tuple[dict[int, float], float]:
    """각 key(행/열 번호) → 콘텐츠 시작지점부터의 누적 거리(pt), 총합."""
    offsets, acc = {}, 0.0
    for k in keys:
        offsets[k] = acc
        acc += sizes[k]
    return offsets, acc


_BORDER_WIDTH_PT = {
    "hair": 0.25, "thin": 0.5, "dotted": 0.5, "dashed": 0.5, "dashDot": 0.5,
    "medium": 1.25, "mediumDashed": 1.25, "double": 1.0, "thick": 2.25,
}


def _border_width(style: str | None) -> float:
    return _BORDER_WIDTH_PT.get(style, 0.5) if style else 0.0


def _rgb_color(color):
    """openpyxl Color(theme/indexed/rgb) → reportlab Color. 알 수 없는 팔레트 색은
    검정(테두리 기본값)으로 근사 — 이 템플릿은 대부분 자동/검정 테두리만 쓴다."""
    from reportlab.lib import colors  # noqa: PLC0415

    if color is not None and getattr(color, "type", None) == "rgb" and color.rgb and len(color.rgb) == 8:
        try:
            return colors.HexColor("#" + color.rgb[-6:])
        except ValueError:
            pass
    return colors.black


def _fill_color(cell):
    from reportlab.lib import colors  # noqa: PLC0415

    fill = cell.fill
    if fill is None or fill.patternType != "solid":
        return None
    fg = fill.fgColor
    if fg is not None and getattr(fg, "type", None) == "rgb" and fg.rgb and len(fg.rgb) == 8:
        try:
            c = colors.HexColor("#" + fg.rgb[-6:])
            if c == colors.white:  # 흰 배경은 그릴 필요 없음(기본 배경과 동일)
                return None
            return c
        except ValueError:
            return None
    return None


def _edge_border(ws, r1: int, c1: int, r2: int, c2: int, side: str):
    """병합 영역의 한 변(top/bottom/left/right) 테두리 — 실제로 테두리가 그 변의 어느
    셀에 저장돼 있는지 몰라도 되게, 변을 이루는 모든 셀을 훑어 처음 발견한 스타일을 쓴다."""
    if side == "top":
        cells = [(r1, cc) for cc in range(c1, c2 + 1)]
        attr = "top"
    elif side == "bottom":
        cells = [(r2, cc) for cc in range(c1, c2 + 1)]
        attr = "bottom"
    elif side == "left":
        cells = [(rr, c1) for rr in range(r1, r2 + 1)]
        attr = "left"
    else:
        cells = [(rr, c2) for rr in range(r1, r2 + 1)]
        attr = "right"
    for rr, cc in cells:
        side_obj = getattr(ws.cell(row=rr, column=cc).border, attr)
        if side_obj is not None and side_obj.style:
            return side_obj
    return None


def _xml_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _cell_markup(ws, r: int, c: int, override) -> str | None:
    """셀 값을 reportlab Paragraph 마크업 문자열로. rich-text(부분 굵게)·전체굵게·
    개행(`\\n`, 세로 라벨용)을 반영한다. 미해결 수식(override 없는 `=...`)은 빈 문자열."""
    from openpyxl.cell.rich_text import CellRichText, TextBlock  # noqa: PLC0415

    key = (r, c)
    if key in override:
        value = override[key]
    else:
        value = ws.cell(row=r, column=c).value

    if value is None or value == "":
        return None
    if isinstance(value, str) and value.startswith("="):
        return None  # 미해결 수식 — override 에 없으면 빈칸(원본 캡처 실패 대비 안전값)

    if isinstance(value, CellRichText):
        parts = []
        for part in value:
            if isinstance(part, TextBlock):
                text = _xml_escape(part.text).replace("\n", "<br/>")
                parts.append(f"<b>{text}</b>" if part.font and part.font.b else text)
            else:
                parts.append(_xml_escape(str(part)).replace("\n", "<br/>"))
        return "".join(parts)

    if isinstance(value, (int, float)):
        cell = ws.cell(row=r, column=c)
        text = format_won(int(value)) if '"원"' in (cell.number_format or "") else f"{value:,}"
    else:
        text = _xml_escape(str(value)).replace("\n", "<br/>")

    if ws.cell(row=r, column=c).font.bold:
        return f"<b>{text}</b>"
    return text


def _paragraph_style(cell, scale: float):
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT  # noqa: PLC0415
    from reportlab.lib.styles import ParagraphStyle  # noqa: PLC0415

    size = (cell.font.size or 10.0) * scale
    is_numeric = isinstance(cell.value, (int, float))
    h_align = cell.alignment.horizontal or ("right" if is_numeric else "left")
    alignment = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT, "justify": TA_LEFT}.get(h_align, TA_LEFT)
    return ParagraphStyle(
        f"c{id(cell)}", fontName=_FONT, fontSize=size, leading=size * 1.25, alignment=alignment,
    )


def _wrap_paragraph(markup: str, cell, scale: float, avail_pt: float):
    """단순 폭 안에 텍스트를 배치. 원본 셀이 `wrap_text` 를 켜지 않은 한(이 템플릿엔
    G3 세로라벨 1곳뿐) 여러 줄로 줄바꿈하지 않고, 좁은 열(날짜 등)은 한 줄에 들어갈
    때까지 글자 크기를 줄인다(Excel "셀에 맞춤" 과 동일한 의도) — 그렇지 않으면
    "2026.06.01" 같은 한 덩어리 텍스트가 reportlab 기본 줄바꿈으로 중간에서 잘린다."""
    from reportlab.platypus import Paragraph  # noqa: PLC0415

    style = _paragraph_style(cell, scale)
    if cell.alignment.wrap_text:
        p = Paragraph(markup, style)
        w, h = p.wrap(avail_pt, 10_000)
        return p, w, h

    p = Paragraph(markup, style)
    w, h = p.wrap(avail_pt, 10_000)
    while h > style.leading * 1.05 and style.fontSize > 4:
        style.fontSize -= 0.5
        style.leading = style.fontSize * 1.25
        p = Paragraph(markup, style)
        w, h = p.wrap(avail_pt, 10_000)
    return p, w, h


def _value_overrides(q: Quote, last_item_row: int) -> dict[tuple[int, int], str]:
    """엑셀이 수식으로 남겨 두는 셀(항목별 세액 K열, 합계블록 I열, K13)만 `Quote`
    에 이미 계산된 정본 값으로 덮어쓴다 — PDF 는 수식을 계산할 수 없어서 필요."""
    overrides: dict[tuple[int, int], str] = {}
    for idx, it in enumerate(q.items):
        row = ITEM_FIRST_ROW + idx
        overrides[(row, 11)] = format_won(round(it.line_amount * VAT_RATE))  # K = 11
    for row in range(ITEM_FIRST_ROW + len(q.items), last_item_row + 1):
        overrides[(row, 11)] = ""  # 남는 템플릿 항목 행의 세액 수식 — 항목 없으니 공란
    sum_row = last_item_row + 1
    overrides[(sum_row, 9)] = format_won(q.supply_amount)      # I: 공급가액
    overrides[(sum_row + 1, 9)] = format_won(q.vat_amount)     # I: 세액
    overrides[(sum_row + 2, 9)] = format_won(q.total_with_vat)  # I: 합계
    overrides[(13, 11)] = f"(₩{q.total_with_vat:,})"            # K13
    return overrides


def _draw_seal(cvs, q: Quote, col_x: dict[int, float], row_y: dict[int, float], row_h: dict[int, float], scale: float, oy_top: float, ox: float) -> None:
    from openpyxl.utils import column_index_from_string  # noqa: PLC0415

    if q.status != STATUS_APPROVED or not SEAL_PATH.exists():
        return
    seal_pt = SEAL_MM * _MM
    offset_pt = SEAL_OFFSET_X_MM * _MM
    col = column_index_from_string("L")
    row = 4
    x1 = col_x[col] + offset_pt
    y1 = row_y[row] + max((row_h[row] - seal_pt) / 2, 0)
    cx = ox + x1 * scale
    cy = oy_top - (y1 + seal_pt) * scale
    size = seal_pt * scale
    cvs.drawImage(str(SEAL_PATH), cx, cy, width=size, height=size, mask="auto")


def _render_workbook_pdf(q: Quote) -> bytes:
    from reportlab.lib.pagesizes import A4  # noqa: PLC0415
    from reportlab.pdfgen import canvas as canvas_mod  # noqa: PLC0415

    wb, last_item_row = build_quote_workbook(q)
    ws = wb.active
    overrides = _value_overrides(q, last_item_row)

    col_w = _col_widths_pt(ws)
    row_h = _row_heights_pt(ws)
    cols = list(range(ws.min_column, ws.max_column + 1))
    rows = list(range(ws.min_row, ws.max_row + 1))
    col_x, content_w = _cumulative(col_w, cols)
    row_y, content_h = _cumulative(row_h, rows)

    pm = ws.page_margins
    margin_l = (pm.left or 0.3) * 72
    margin_r = (pm.right or 0.3) * 72
    margin_t = (pm.top or 0.4) * 72
    margin_b = (pm.bottom or 0.4) * 72

    page_w, page_h = A4
    avail_w = page_w - margin_l - margin_r
    avail_h = page_h - margin_t - margin_b
    scale = min(avail_w / content_w, avail_h / content_h, 1.0) if content_w and content_h else 1.0

    ox = margin_l
    oy_top = page_h - margin_t

    def cx(lx: float) -> float:
        return ox + lx * scale

    def cy(ly: float) -> float:
        return oy_top - ly * scale

    buf = BytesIO()
    cvs = canvas_mod.Canvas(buf, pagesize=A4)
    cvs.setTitle(f"견적서 {q.mgmt_no}")

    # ---- 병합 영역 인덱스 -----------------------------------------------------
    merge_anchor: dict[tuple[int, int], tuple[int, int, int, int]] = {}
    covered: set[tuple[int, int]] = set()
    for rng in ws.merged_cells.ranges:
        r1, c1, r2, c2 = rng.min_row, rng.min_col, rng.max_row, rng.max_col
        merge_anchor[(r1, c1)] = (r1, c1, r2, c2)
        for rr in range(r1, r2 + 1):
            for cc in range(c1, c2 + 1):
                if (rr, cc) != (r1, c1):
                    covered.add((rr, cc))

    for r in rows:
        for c in cols:
            if (r, c) in covered:
                continue
            r1, c1, r2, c2 = merge_anchor.get((r, c), (r, c, r, c))
            x1, y1 = col_x[c1], row_y[r1]
            w = sum(col_w[cc] for cc in range(c1, c2 + 1))
            h = sum(row_h[rr] for rr in range(r1, r2 + 1))

            anchor_cell = ws.cell(row=r1, column=c1)

            # 배경색
            fill = _fill_color(anchor_cell)
            if fill is not None:
                cvs.setFillColor(fill)
                cvs.rect(cx(x1), cy(y1 + h), w * scale, h * scale, stroke=0, fill=1)

            # 테두리(변마다 실제 스타일이 저장된 셀을 찾아서)
            for side, (sx1, sy1, sx2, sy2) in (
                ("top", (x1, y1, x1 + w, y1)),
                ("bottom", (x1, y1 + h, x1 + w, y1 + h)),
                ("left", (x1, y1, x1, y1 + h)),
                ("right", (x1 + w, y1, x1 + w, y1 + h)),
            ):
                b = _edge_border(ws, r1, c1, r2, c2, side)
                if b is None:
                    continue
                width = _border_width(b.style)
                if width <= 0:
                    continue
                cvs.setLineWidth(width * scale)
                cvs.setStrokeColor(_rgb_color(b.color))
                cvs.line(cx(sx1), cy(sy1), cx(sx2), cy(sy2))

            # 텍스트
            markup = _cell_markup(ws, r1, c1, overrides)
            if markup:
                avail_pt = max(w - 2 * _CELL_PAD, 4) * scale
                p, pw, ph = _wrap_paragraph(markup, anchor_cell, scale, avail_pt)
                v_align = anchor_cell.alignment.vertical or "center"
                if v_align == "top":
                    text_bottom_content = y1 + _CELL_PAD + ph / scale
                elif v_align == "bottom":
                    text_bottom_content = y1 + h - _CELL_PAD
                else:
                    text_bottom_content = y1 + (h + ph / scale) / 2
                h_align = anchor_cell.alignment.horizontal or ("right" if isinstance(anchor_cell.value, (int, float)) else "left")
                if h_align == "center":
                    text_x = x1 + (w - pw / scale) / 2
                elif h_align == "right":
                    text_x = x1 + w - _CELL_PAD - pw / scale
                else:
                    text_x = x1 + _CELL_PAD
                p.drawOn(cvs, cx(text_x), cy(text_bottom_content))

    _draw_seal(cvs, q, col_x, row_y, row_h, scale, oy_top, ox)

    cvs.showPage()
    cvs.save()
    return buf.getvalue()


def build_quote_pdf(q: Quote) -> bytes:
    try:
        _register_fonts()
    except Exception as exc:  # pragma: no cover - 환경 의존(폰트 파일 누락 등)
        raise AppError(
            PDF_UNAVAILABLE,
            501,
            "이 환경에서는 PDF 생성이 비활성화되어 있습니다. 엑셀 export 를 이용하세요.",
        ) from exc

    try:
        return _render_workbook_pdf(q)
    except Exception as exc:  # pragma: no cover
        raise AppError(
            PDF_UNAVAILABLE, 501, "PDF 생성 중 오류가 발생했습니다. 엑셀 export 를 이용하세요."
        ) from exc
