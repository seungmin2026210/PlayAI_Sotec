"""개별 견적서 PDF — WeasyPrint(HTML→PDF). TECH 09.

WeasyPrint 는 시스템 라이브러리(GTK 등)에 의존한다. import/렌더 실패 시
AppError(PDF_UNAVAILABLE, 501) 를 던지고 서버는 계속 동작한다.
"""
from __future__ import annotations

import html

from ..config import COMPANY, GROUPS, STATUS_LABELS
from ..errors import PDF_UNAVAILABLE, AppError
from ..models import Quote
from .calculation import format_won


def _row(label: str, value: str) -> str:
    return f"<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>"


def _build_html(q: Quote) -> str:
    items_rows = "".join(
        f"<tr><td class='c'>{i.line_no}</td><td>{html.escape(i.name)}</td>"
        f"<td class='r'>{i.qty:,}</td><td class='r'>{format_won(i.unit_price)}</td>"
        f"<td class='r'>{format_won(i.line_amount)}</td></tr>"
        for i in q.items
    )
    vat_note = (
        "부가세 포함 견적입니다. 고객 실지불액은 '부가세 포함가' 기준입니다."
        if q.vat_included
        else "부가세 미포함(별도) 견적입니다. 공급가액 기준이며 부가세는 별도입니다."
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 18mm; }}
* {{ font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; }}
body {{ font-size: 11px; color: #1a1a1a; }}
h1 {{ text-align: center; letter-spacing: 8px; margin: 0 0 16px; }}
h2 {{ font-size: 12px; border-left: 4px solid #333; padding-left: 6px; margin: 16px 0 6px; }}
table.kv {{ width: 100%; border-collapse: collapse; margin-bottom: 4px; }}
table.kv th {{ width: 130px; text-align: left; background: #f4f4f4; border: 1px solid #ccc; padding: 4px 8px; }}
table.kv td {{ border: 1px solid #ccc; padding: 4px 8px; }}
table.items {{ width: 100%; border-collapse: collapse; margin-top: 6px; }}
table.items th, table.items td {{ border: 1px solid #999; padding: 5px 8px; }}
table.items th {{ background: #eee; }}
.r {{ text-align: right; }} .c {{ text-align: center; }}
table.sum {{ width: 55%; margin-left: 45%; border-collapse: collapse; margin-top: 10px; }}
table.sum th {{ text-align: left; padding: 4px 8px; }}
table.sum td {{ text-align: right; padding: 4px 8px; border-bottom: 1px solid #ddd; }}
table.sum tr.total th, table.sum tr.total td {{ font-weight: bold; border-top: 2px solid #333; border-bottom: none; }}
.note {{ margin-top: 12px; font-style: italic; color: #555; }}
</style></head><body>
<h1>견 적 서</h1>

<h2>공급자 (자사)</h2>
<table class="kv">
{_row("회사명", COMPANY["name"])}
{_row("사업자등록번호", COMPANY["biz_no"])}
{_row("대표자명", COMPANY["ceo_name"])}
{_row("주소", COMPANY.get("address", ""))}
{_row("연락처", COMPANY.get("tel", ""))}
</table>

<h2>수신처 (고객사)</h2>
<table class="kv">
{_row("고객사명", q.customer_name)}
{_row("담당자", q.customer_contact_name or "-")}
{_row("연락처", q.customer_contact_phone or "-")}
</table>

<h2>견적 정보</h2>
<table class="kv">
{_row("관리번호", q.mgmt_no)}
{_row("견적서명", q.title)}
{_row("그룹", f"{q.group_code} ({GROUPS.get(q.group_code, '')})")}
{_row("발행일자", q.issue_date.isoformat())}
{_row("발행 담당자", q.issuer_name)}
{_row("상태", STATUS_LABELS.get(q.status, q.status))}
{_row("구매관리 반영", "예(읽기전용)" if q.purchase_locked else "아니오")}
</table>

<h2>견적 항목</h2>
<table class="items">
<thead><tr><th class="c">No</th><th>품목</th><th class="r">갯수</th>
<th class="r">단가(공급가액)</th><th class="r">금액</th></tr></thead>
<tbody>{items_rows}</tbody>
</table>

<table class="sum">
<tr><th>항목 합계</th><td>{format_won(q.items_raw_total)}</td></tr>
<tr><th>공급가액 합계 (십만단위 절사)</th><td>{format_won(q.supply_amount)}</td></tr>
<tr><th>부가세 (10%)</th><td>{format_won(q.vat_amount)}</td></tr>
<tr class="total"><th>부가세 포함가</th><td>{format_won(q.total_with_vat)}</td></tr>
</table>

<p class="note">{vat_note}</p>
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
