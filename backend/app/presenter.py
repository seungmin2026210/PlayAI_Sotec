"""모델 -> 응답 스키마 변환 (파생 필드 계산)."""
from __future__ import annotations

from .config import COMPANY, GROUPS, STATUS_LABELS
from .models import Quote
from .schemas import ItemOut, QuoteListItem, QuoteRead
from .services.status import is_read_only


def to_quote_read(q: Quote) -> QuoteRead:
    return QuoteRead(
        id=q.id,
        mgmt_no=q.mgmt_no,
        seq_year=q.seq_year,
        group_code=q.group_code,
        group_name=GROUPS.get(q.group_code, q.group_code),
        seq_no=q.seq_no,
        title=q.title,
        issue_date=q.issue_date,
        issuer_name=q.issuer_name,
        customer_name=q.customer_name,
        customer_contact_name=q.customer_contact_name,
        customer_contact_phone=q.customer_contact_phone,
        vat_included=q.vat_included,
        supply_amount=q.supply_amount,
        vat_amount=q.vat_amount,
        total_with_vat=q.total_with_vat,
        items_raw_total=q.items_raw_total,
        status=q.status,
        status_label=STATUS_LABELS.get(q.status, q.status),
        reject_reason=q.reject_reason,
        purchase_locked=q.purchase_locked,
        read_only=is_read_only(q),
        created_by=q.created_by,
        created_at=q.created_at,
        updated_at=q.updated_at,
        approved_at=q.approved_at,
        rejected_at=q.rejected_at,
        cancelled_at=q.cancelled_at,
        locked_at=q.locked_at,
        company=dict(COMPANY),
        items=[
            ItemOut(
                line_no=i.line_no,
                name=i.name,
                qty=i.qty,
                unit_price=i.unit_price,
                line_amount=i.line_amount,
            )
            for i in q.items
        ],
    )


def to_list_item(q: Quote) -> QuoteListItem:
    return QuoteListItem(
        id=q.id,
        mgmt_no=q.mgmt_no,
        group_code=q.group_code,
        group_name=GROUPS.get(q.group_code, q.group_code),
        title=q.title,
        customer_name=q.customer_name,
        issue_date=q.issue_date,
        issuer_name=q.issuer_name,
        supply_amount=q.supply_amount,
        vat_amount=q.vat_amount,
        total_with_vat=q.total_with_vat,
        vat_included=q.vat_included,
        status=q.status,
        status_label=STATUS_LABELS.get(q.status, q.status),
        purchase_locked=q.purchase_locked,
        created_at=q.created_at,
    )
