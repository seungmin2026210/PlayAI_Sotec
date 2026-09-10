"""개별 견적서 PDF — WeasyPrint(HTML→PDF). TECH 09.

레이아웃은 엑셀(`export_excel.build_quote_xlsx`)과 동일한 실제 견적서.jpg 양식.
APPROVED 견적서는 대표자명 옆에 직인을 합성한다.

WeasyPrint 는 시스템 라이브러리(Windows 는 GTK3 런타임)에 의존한다. import/렌더
실패 시 AppError(PDF_UNAVAILABLE, 501) 를 던지고 서버는 계속 동작한다.
"""
from __future__ import annotations

import base64
import html
import os

from ..config import (
    COMPANY,
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

# ponytail: Windows 는 winget(tschoonj.GTKForWindows) 설치 후에도 GTK bin 이 프로세스
# PATH 에 없으면 import 가 깨진다. 표준 설치 경로가 있으면 앞에 얹는다.
if os.name == "nt":
    _gtk_bin = r"C:\Program Files\GTK3-Runtime Win64\bin"
    if os.path.isdir(_gtk_bin) and _gtk_bin not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _gtk_bin + os.pathsep + os.environ.get("PATH", "")


def _data_uri(path) -> str:
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


_LOGO_DATA_URI = _data_uri(LOGO_PATH)
_SEAL_DATA_URI = _data_uri(SEAL_PATH)


def _esc(v) -> str:
    return html.escape("" if v is None else str(v))


def _build_html(q: Quote) -> str:
    items_rows = "".join(
        f"<tr><td class='c'>{i.line_no}</td><td>{_esc(i.name)}</td><td></td>"
        f"<td class='r'>{i.qty:,}</td><td class='r'>{format_won(i.unit_price)}</td>"
        f"<td class='r'>{format_won(i.line_amount)}</td>"
        f"<td class='r'>{format_won(round(i.line_amount * VAT_RATE))}</td><td></td></tr>"
        for i in q.items
    )
    greeting_lines = "".join(f"<p>{_esc(l)}</p>" for l in QUOTE_GREETING_LINES)
    conditions = "".join(
        f"<p><b>{n}. {_esc(label)}</b> : {_esc(text)}</p>"
        for n, (label, text) in enumerate(QUOTE_CONDITIONS, start=3)
    )
    signoff_head = "".join(f"<th>{_esc(c)}</th>" for c in QUOTE_SIGNOFF_COLS)
    signoff_body = "".join("<td></td>" for _ in QUOTE_SIGNOFF_COLS)
    seal_img = (
        f"<img class='seal' src='{_SEAL_DATA_URI}' alt='직인'>"
        if q.status == STATUS_APPROVED and _SEAL_DATA_URI
        else ""
    )
    vat_note = (
        "부가세 포함 견적입니다. 고객 실지불액은 '합계금액' 기준입니다."
        if q.vat_included
        else "부가세 미포함(별도) 견적입니다. 공급가액 기준이며 부가세는 별도입니다."
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 16mm; }}
* {{ font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; box-sizing: border-box; }}
body {{ font-size: 10.5px; color: #1a1a1a; }}
.doc-logo {{ height: 26px; }}
h1 {{ text-align: center; letter-spacing: 10px; margin: 4px 0 14px; font-size: 24px; }}
.head {{ display: flex; gap: 12px; align-items: stretch; }}
.head > div {{ flex: 1; }}
/* 좌 열: 견적일자·수신처를 붙여 두고, 남는 높이는 표 행을 늘려 채운다(중간 공백 없이 우 공급자 열과 상·하단 정렬) */
.head .basic {{ display: flex; flex-direction: column; }}
.head .basic > table, .head .basic > .receiver {{ flex: 1 1 auto; }}
.head .basic > .receiver {{ display: flex; flex-direction: column; }}
.head .basic > .receiver > table {{ flex: 1 1 auto; }}
table {{ border-collapse: collapse; width: 100%; }}
.kv th {{ width: 84px; text-align: left; background: #f4f4f4; border: 1px solid #ccc; padding: 3px 6px; font-weight: bold; }}
.kv td {{ border: 1px solid #ccc; padding: 3px 6px; }}
.supplier {{ position: relative; }}
.seal {{ position: absolute; right: 6px; top: 30px; width: {SEAL_MM}mm; height: {SEAL_MM}mm; opacity: .9; }}
.block-title {{ font-weight: bold; margin: 12px 0 4px; }}
.greeting p {{ margin: 2px 0; }}
.total-box {{ margin: 10px 0; border: 1px solid #333; padding: 6px 10px; font-weight: bold; font-size: 12px;
  display: flex; justify-content: space-between; background: #f7f7f7; }}
.items th, .items td {{ border: 1px solid #999; padding: 4px 6px; }}
.items th {{ background: #eee; }}
.r {{ text-align: right; }} .c {{ text-align: center; }}
.sum {{ width: 58%; margin-left: 42%; margin-top: 8px; }}
.sum th {{ text-align: right; padding: 3px 8px; font-weight: normal; }}
.sum td {{ text-align: right; padding: 3px 8px; border-bottom: 1px solid #ddd; }}
.sum tr.total th, .sum tr.total td {{ font-weight: bold; border-top: 2px solid #333; border-bottom: none; }}
.foot-note {{ margin-top: 6px; font-style: italic; color: #555; font-size: 9px; }}
.conditions {{ margin-top: 12px; }}
.conditions p {{ margin: 2px 0; }}
.signoff {{ width: 45%; margin-left: 55%; margin-top: 14px; text-align: center; }}
.signoff th, .signoff td {{ border: 1px solid #999; padding: 4px; }}
.signoff td {{ height: 40px; }}
</style></head><body>
{f'<img class="doc-logo" src="{_LOGO_DATA_URI}" alt="{_esc(COMPANY["name"])}">' if _LOGO_DATA_URI else ""}
<h1>견 적 서</h1>

<div class="head">
  <div class="basic">
    <table class="kv">
      <tr><th>견적일자</th><td>{_esc(q.issue_date.isoformat())}</td></tr>
      <tr><th>견적유효기간</th><td>{_esc(QUOTE_VALIDITY_NOTE)}</td></tr>
      <tr><th>견적 NO</th><td>{_esc(format_mgmt_no_display(q.seq_year, q.group_code, q.seq_no))}</td></tr>
    </table>
    <div class="receiver">
      <div class="block-title">[ 수신처 (고객사) ]</div>
      <table class="kv">
        <tr><th>고객사명</th><td>{_esc(q.customer_name)}</td></tr>
        <tr><th>담당자</th><td>{_esc(q.customer_contact_name or "-")} {_esc(q.customer_contact_phone or "")}</td></tr>
        <tr><th>C.C</th><td></td></tr>
      </table>
    </div>
  </div>
  <div class="supplier">
    {seal_img}
    <div class="block-title">[ 공급자 (자사) ]</div>
    <table class="kv">
      <tr><th>등록번호</th><td>{_esc(COMPANY["biz_no"])}</td></tr>
      <tr><th>상호</th><td>{_esc(COMPANY["name"])}</td></tr>
      <tr><th>대표자</th><td>{_esc(COMPANY["ceo_name"])} (인)</td></tr>
      <tr><th>주소</th><td>{_esc(COMPANY.get("address", ""))}</td></tr>
      <tr><th>업태 / 종목</th><td>{_esc(COMPANY.get("biz_type", ""))} / {_esc(COMPANY.get("biz_item", ""))}</td></tr>
      <tr><th>전화 / FAX</th><td>{_esc(COMPANY.get("tel", ""))} / {_esc(COMPANY.get("fax", ""))}</td></tr>
      <tr><th>견적 작성자</th><td>{_esc(QUOTE_AUTHOR_TEAM)} {_esc(GROUPS.get(q.group_code, ""))} / {_esc(QUOTE_AUTHOR_ROLE)}</td></tr>
    </table>
  </div>
</div>

<div class="greeting">
  <p><b>{_esc(QUOTE_GREETING)}</b></p>
  {greeting_lines}
</div>

<div class="total-box"><span>합계금액 (공급가액 + 세액)</span><span>{format_won(q.total_with_vat)}</span></div>

<table class="kv">
  <tr><th>용역(계약)명</th><td>{_esc(q.title)}</td></tr>
  <tr><th>용역(계약) 기간</th><td></td></tr>
</table>

<table class="items">
<thead><tr><th class="c">No</th><th>품목</th><th>규격</th><th class="r">수량</th>
<th class="r">단가</th><th class="r">공급가액</th><th class="r">세액</th><th>비고</th></tr></thead>
<tbody>{items_rows}</tbody>
</table>

<table class="sum">
<tr><th>공급가액 합계 (십만단위 절사)</th><td>{format_won(q.supply_amount)}</td></tr>
<tr><th>세액 (10%)</th><td>{format_won(q.vat_amount)}</td></tr>
<tr class="total"><th>합계금액</th><td>{format_won(q.total_with_vat)}</td></tr>
</table>
<p class="foot-note">* 항목 합계 {q.items_raw_total:,}원 · 합계는 총액 기준 십만단위 절사. {_esc(vat_note)}</p>

<div class="conditions">{conditions}</div>

<table class="signoff">
<thead><tr>{signoff_head}</tr></thead>
<tbody><tr>{signoff_body}</tr></tbody>
</table>
</body></html>"""


def build_quote_pdf(q: Quote) -> bytes:
    try:
        from weasyprint import HTML  # noqa: PLC0415  (지연 import: 환경 이슈 격리)
    except Exception as exc:  # pragma: no cover - 환경 의존
        raise AppError(
            PDF_UNAVAILABLE,
            501,
            "이 환경에서는 PDF 생성이 비활성화되어 있습니다. 엑셀 export 를 이용하세요.",
        ) from exc

    try:
        return HTML(string=_build_html(q)).write_pdf()
    except Exception as exc:  # pragma: no cover
        raise AppError(
            PDF_UNAVAILABLE, 501, "PDF 생성 중 오류가 발생했습니다. 엑셀 export 를 이용하세요."
        ) from exc
