from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..auth import CurrentUser
from ..config import STATUS_SUBMITTED
from ..deps import apply_scope, assert_can_view, get_current_user, get_db, require_super_admin
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
from ..services import numbering
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
def _base_stmt():
    return select(Quote).where(Quote.deleted_at.is_(None))


def _apply_filters(
    stmt,
    *,
    mgmt_no: str | None,
    title: str | None,
    group_code: str | None,
    status: str | None,
    issue_date_from: date | None,
    issue_date_to: date | None,
    issuer_name: str | None,
):
    if mgmt_no:
        stmt = stmt.where(Quote.mgmt_no.ilike(f"%{mgmt_no}%"))
    if title:
        stmt = stmt.where(Quote.title.ilike(f"%{title}%"))
    if group_code:
        stmt = stmt.where(Quote.group_code == group_code)
    if status:
        stmt = stmt.where(Quote.status == status)
    if issue_date_from:
        stmt = stmt.where(Quote.issue_date >= issue_date_from)
    if issue_date_to:
        stmt = stmt.where(Quote.issue_date <= issue_date_to)
    if issuer_name:
        stmt = stmt.where(Quote.issuer_name.ilike(f"%{issuer_name}%"))
    return stmt


def _load_or_404(db: Session, quote_id: int, user: CurrentUser) -> Quote:
    q = db.execute(
        select(Quote).options(selectinload(Quote.items)).where(Quote.id == quote_id)
    ).scalar_one_or_none()
    q = assert_exists(q)
    assert_can_view(q, user)
    return q


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- list
@router.get("", response_model=QuoteListResponse)
def list_quotes(
    db: Session = Depends(get_db),
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
    stmt = _apply_filters(
        _base_stmt(),
        mgmt_no=mgmt_no,
        title=title,
        group_code=group_code,
        status=status,
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
        issuer_name=issuer_name,
    )
    stmt = apply_scope(stmt, user)  # 그룹관리자 스코프 강제

    total = db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()

    rows = db.execute(
        stmt.order_by(Quote.created_at.desc()).offset((page - 1) * size).limit(size)
    ).scalars().all()

    return QuoteListResponse(
        total=total, page=page, size=size, items=[to_list_item(q) for q in rows]
    )


# --------------------------------------------------------------------------- list export (declare before /{quote_id})
@router.get("/export.xlsx")
def export_list_xlsx(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    mgmt_no: str | None = Query(default=None),
    title: str | None = Query(default=None),
    group_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
    issue_date_from: date | None = Query(default=None),
    issue_date_to: date | None = Query(default=None),
    issuer_name: str | None = Query(default=None),
) -> Response:
    stmt = _apply_filters(
        _base_stmt(),
        mgmt_no=mgmt_no,
        title=title,
        group_code=group_code,
        status=status,
        issue_date_from=issue_date_from,
        issue_date_to=issue_date_to,
        issuer_name=issuer_name,
    )
    stmt = apply_scope(stmt, user)
    rows = db.execute(stmt.order_by(Quote.created_at.desc())).scalars().all()
    data = build_list_xlsx(list(rows))
    return Response(
        content=data,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{list_filename()}"'},
    )


# --------------------------------------------------------------------------- create
@router.post("", response_model=QuoteRead, status_code=201)
def create_quote(
    body: QuoteCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    computed = compute(body.items)
    alloc = numbering.allocate(db, body.group_code)  # 같은 트랜잭션 내 FOR UPDATE 채번

    quote = Quote(
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
        status=STATUS_SUBMITTED,
        purchase_locked=False,
        created_by=user.username,
        created_at=_now(),
    )
    for idx, it in enumerate(body.items, start=1):
        quote.items.append(
            QuoteItem(
                line_no=idx,
                name=it.name,
                qty=it.qty,
                unit_price=it.unit_price,
                line_amount=it.qty * it.unit_price,
            )
        )
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return to_quote_read(quote)


# --------------------------------------------------------------------------- detail
@router.get("/{quote_id}", response_model=QuoteRead)
def get_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> QuoteRead:
    return to_quote_read(_load_or_404(db, quote_id, user))


# --------------------------------------------------------------------------- update
@router.put("/{quote_id}", response_model=QuoteRead)
def update_quote(
    quote_id: int,
    body: QuoteUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    quote = _load_or_404(db, quote_id, user)
    guard_mutable(quote)  # 잠금 / 종료상태 차단

    computed = compute(body.items)
    apply_edit_policy(quote, body, computed)  # open-10 정책 격리 지점

    quote.items.clear()
    db.flush()
    for idx, it in enumerate(body.items, start=1):
        quote.items.append(
            QuoteItem(
                line_no=idx,
                name=it.name,
                qty=it.qty,
                unit_price=it.unit_price,
                line_amount=it.qty * it.unit_price,
            )
        )
    db.commit()
    db.refresh(quote)
    return to_quote_read(quote)


# --------------------------------------------------------------------------- delete
@router.delete("/{quote_id}", response_model=MessageResponse)
def delete_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> MessageResponse:
    quote = _load_or_404(db, quote_id, user)
    guard_mutable(quote)

    quote.deleted_at = _now()
    numbering.retire(
        db,
        mgmt_no=quote.mgmt_no,
        seq_year=quote.seq_year,
        group_code=quote.group_code,
        seq_no=quote.seq_no,
        retired_by=user.username,
    )
    db.commit()
    return MessageResponse(message=f"견적서 {quote.mgmt_no} 를 삭제했습니다. 해당 관리번호는 결번 처리됩니다.")


# --------------------------------------------------------------------------- transitions
@router.post("/{quote_id}/approve", response_model=QuoteRead)
def approve_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    quote = _load_or_404(db, quote_id, user)
    apply_transition(quote, "approve")
    db.commit()
    db.refresh(quote)
    return to_quote_read(quote)


@router.post("/{quote_id}/reject", response_model=QuoteRead)
def reject_quote(
    quote_id: int,
    body: RejectRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    quote = _load_or_404(db, quote_id, user)
    apply_transition(quote, "reject", reason=body.reason)
    db.commit()
    db.refresh(quote)
    return to_quote_read(quote)


@router.post("/{quote_id}/cancel", response_model=QuoteRead)
def cancel_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    quote = _load_or_404(db, quote_id, user)
    apply_transition(quote, "cancel")
    db.commit()
    db.refresh(quote)
    return to_quote_read(quote)


@router.post("/{quote_id}/purchase-lock", response_model=QuoteRead)
def purchase_lock_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> QuoteRead:
    """구매관리 데이터 반영(자리표시). idempotent. open-4."""
    quote = _load_or_404(db, quote_id, user)
    apply_purchase_lock(quote)
    db.commit()
    db.refresh(quote)
    return to_quote_read(quote)


@router.post("/{quote_id}/send", response_model=MessageResponse)
def send_quote(
    quote_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> MessageResponse:
    """발송 버튼 자리표시. 실제 SMTP 연동 없음 (기획서 4.6)."""
    _load_or_404(db, quote_id, user)
    return MessageResponse(message="이메일 발송 기능은 준비 중입니다.")


# --------------------------------------------------------------------------- individual export
@router.get("/{quote_id}/export.xlsx")
def export_quote_xlsx(
    quote_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    quote = _load_or_404(db, quote_id, user)
    data = build_quote_xlsx(quote)
    return Response(
        content=data,
        media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{quote.mgmt_no}.xlsx"'},
    )


@router.get("/{quote_id}/export.pdf")
def export_quote_pdf(
    quote_id: int,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Response:
    quote = _load_or_404(db, quote_id, user)
    data = build_quote_pdf(quote)  # 실패 시 AppError(PDF_UNAVAILABLE, 501)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{quote.mgmt_no}.pdf"'},
    )
