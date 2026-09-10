from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, Response
from google.cloud import firestore

from ..auth import CurrentUser
from ..config import STATUS_SUBMITTED
from ..database import run_transaction
from ..deps import assert_can_view, get_current_user, get_db, require_super_admin, scope_group
from ..models import Quote, QuoteItem
from ..presenter import to_list_item, to_quote_read
from ..schemas import (
    MessageResponse,
    QuoteCreate,
    QuoteListResponse,
    QuoteRead,
    QuoteUpdate,
    RejectRequest,
)
from ..services import numbering, query as query_service
from ..services.calculation import compute
from ..services.export_excel import build_list_xlsx, build_quote_xlsx, list_filename
from ..services.export_pdf import build_quote_pdf
from ..services.status import (
    apply_edit_policy,
    apply_purchase_lock,
    apply_transition,
    assert_exists,
    guard_mutable,
)

router = APIRouter(prefix="/api/quotes", tags=["quotes"])

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# --------------------------------------------------------------------------- helpers
def _load_or_404(client: firestore.Client, quote_id: str, user: CurrentUser) -> Quote:
    doc = client.collection("quotes").document(quote_id).get()
    quote = Quote.from_doc(doc.id, doc.to_dict()) if doc.exists else None
    quote = assert_exists(quote)
    assert_can_view(quote, user)
    return quote


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_items(items) -> list[QuoteItem]:
    return [
        QuoteItem(line_no=idx, name=it.name, qty=it.qty, unit_price=it.unit_price, line_amount=it.qty * it.unit_price)
        for idx, it in enumerate(items, start=1)
    ]


# --------------------------------------------------------------------------- list
@router.get("", response_model=QuoteListResponse)
def list_quotes(
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    mgmt_no: str | None = Query(default=None),
    title: str | None = Query(default=None),
    group_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
    issue_date_from: date | None = Query(default=None),
    issue_date_to: date | None = Query(default=None),
    issuer_name: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
) -> QuoteListResponse:
    quotes = query_service.list_quotes(
        client,
        scope_group=scope_group(user),  # 그룹관리자 스코프 강제
        group_code=group_code,
        status=status,
        mgmt_no=mgmt_no,
        title=title,
        issuer_name=issuer_name,
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
    )
    total = len(quotes)
    start = (page - 1) * size
    page_items = quotes[start : start + size]

    return QuoteListResponse(total=total, page=page, size=size, items=[to_list_item(q) for q in page_items])


# --------------------------------------------------------------------------- list export (declare before /{quote_id})
@router.get("/export.xlsx")
def export_list_xlsx(
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    mgmt_no: str | None = Query(default=None),
    title: str | None = Query(default=None),
    group_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
    issue_date_from: date | None = Query(default=None),
    issue_date_to: date | None = Query(default=None),
    issuer_name: str | None = Query(default=None),
) -> Response:
    quotes = query_service.list_quotes(
        client,
        scope_group=scope_group(user),
        group_code=group_code,
        status=status,
        mgmt_no=mgmt_no,
        title=title,
        issuer_name=issuer_name,
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
    )
    data = build_list_xlsx(quotes)
    return Response(
        content=data,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{list_filename()}"'},
    )


# --------------------------------------------------------------------------- create
@router.post("", response_model=QuoteRead, status_code=201)
def create_quote(
    body: QuoteCreate,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    computed = compute(body.items)
    now = _now()

    def _txn(transaction: firestore.Transaction) -> Quote:
        # 채번 + quote 문서 생성을 하나의 트랜잭션에 묶어야 SQL 시절과 동일한 원자성이 나온다
        # (12-firestore-migration.md § 5).
        alloc = numbering.allocate_in(transaction, client, body.group_code, now=now)
        quote = Quote(
            id=alloc.mgmt_no,
            mgmt_no=alloc.mgmt_no,
            seq_year=alloc.seq_year,
            group_code=alloc.group_code,
            seq_no=alloc.seq_no,
            title=body.title,
            issue_date=body.issue_date,
            issuer_name=body.issuer_name,
            customer_name=body.customer_name,
            customer_contact_name=body.customer_contact_name,
            customer_contact_phone=body.customer_contact_phone,
            vat_included=body.vat_included,
            supply_amount=computed.supply_amount,
            vat_amount=computed.vat_amount,
            total_with_vat=computed.total_with_vat,
            items_raw_total=computed.raw_total,
            items=_build_items(body.items),
            status=STATUS_SUBMITTED,
            purchase_locked=False,
            active=True,
            created_by=user.username,
            created_at=now,
        )
        transaction.set(client.collection("quotes").document(alloc.mgmt_no), quote.to_dict())
        return quote

    quote = run_transaction(client, _txn)
    return to_quote_read(quote)


# --------------------------------------------------------------------------- detail
@router.get("/{quote_id}", response_model=QuoteRead)
def get_quote(
    quote_id: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> QuoteRead:
    return to_quote_read(_load_or_404(client, quote_id, user))


# --------------------------------------------------------------------------- update
@router.put("/{quote_id}", response_model=QuoteRead)
def update_quote(
    quote_id: str,
    body: QuoteUpdate,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    quote = _load_or_404(client, quote_id, user)
    guard_mutable(quote)  # 잠금 / 종료상태 차단

    computed = compute(body.items)
    apply_edit_policy(quote, body, computed)  # open-10 정책 격리 지점
    quote.items = _build_items(body.items)

    client.collection("quotes").document(quote.id).set(quote.to_dict())
    return to_quote_read(quote)


# --------------------------------------------------------------------------- delete
@router.delete("/{quote_id}", response_model=MessageResponse)
def delete_quote(
    quote_id: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> MessageResponse:
    quote = _load_or_404(client, quote_id, user)
    guard_mutable(quote)

    now = _now()
    quote_ref = client.collection("quotes").document(quote.id)

    def _txn(transaction: firestore.Transaction) -> None:
        transaction.update(quote_ref, {"active": False, "deleted_at": now})
        numbering.retire_in(
            transaction,
            client,
            mgmt_no=quote.mgmt_no,
            seq_year=quote.seq_year,
            group_code=quote.group_code,
            seq_no=quote.seq_no,
            retired_by=user.username,
        )

    run_transaction(client, _txn)
    return MessageResponse(message=f"견적서 {quote.mgmt_no} 를 삭제했습니다. 해당 관리번호는 결번 처리됩니다.")


# --------------------------------------------------------------------------- transitions
@router.post("/{quote_id}/approve", response_model=QuoteRead)
def approve_quote(
    quote_id: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    quote = _load_or_404(client, quote_id, user)
    apply_transition(quote, "approve")
    client.collection("quotes").document(quote.id).set(quote.to_dict())
    return to_quote_read(quote)


@router.post("/{quote_id}/reject", response_model=QuoteRead)
def reject_quote(
    quote_id: str,
    body: RejectRequest,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    quote = _load_or_404(client, quote_id, user)
    apply_transition(quote, "reject", reason=body.reason)
    client.collection("quotes").document(quote.id).set(quote.to_dict())
    return to_quote_read(quote)


@router.post("/{quote_id}/cancel", response_model=QuoteRead)
def cancel_quote(
    quote_id: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    quote = _load_or_404(client, quote_id, user)
    apply_transition(quote, "cancel")
    client.collection("quotes").document(quote.id).set(quote.to_dict())
    return to_quote_read(quote)


@router.post("/{quote_id}/purchase-lock", response_model=QuoteRead)
def purchase_lock_quote(
    quote_id: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    """구매관리 데이터 반영(자리표시). idempotent. open-4."""
    quote = _load_or_404(client, quote_id, user)
    apply_purchase_lock(quote)
    client.collection("quotes").document(quote.id).set(quote.to_dict())
    return to_quote_read(quote)


@router.post("/{quote_id}/send", response_model=MessageResponse)
def send_quote(
    quote_id: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> MessageResponse:
    """발송 버튼 자리표시. 실제 SMTP 연동 없음 (기획서 4.6)."""
    _load_or_404(client, quote_id, user)
    return MessageResponse(message="이메일 발송 기능은 준비 중입니다.")


# --------------------------------------------------------------------------- individual export
@router.get("/{quote_id}/export.xlsx")
def export_quote_xlsx(
    quote_id: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    quote = _load_or_404(client, quote_id, user)
    data = build_quote_xlsx(quote)
    return Response(
        content=data,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{quote.mgmt_no}.xlsx"'},
    )


@router.get("/{quote_id}/export.pdf")
def export_quote_pdf(
    quote_id: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    quote = _load_or_404(client, quote_id, user)
    data = build_quote_pdf(quote)  # 실패 시 AppError(PDF_UNAVAILABLE, 501)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote.mgmt_no}.pdf"'},
    )
