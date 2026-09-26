"""모델 -> 응답 스키마 변환 (파생 필드 계산)."""
from __future__ import annotations

from .config import (
    ASSET_CATEGORY_LABELS,
    ASSET_UNIT_STATUS_LABELS,
    ASSET_UNIT_TYPE_LABELS,
    COMPANY,
    GROUPS,
    STATUS_LABELS,
)
from .models import AssetProduct, AssetUnit, Quote
from .schemas import (
    AssetProductRead,
    AssetUnitListItem,
    AssetUnitRead,
    ItemOut,
    QuoteListItem,
    QuoteRead,
)
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
        customer_department=q.customer_department,
        customer_contact_name=q.customer_contact_name,
        customer_contact_phone=q.customer_contact_phone,
        customer_cc=q.customer_cc,
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
                period_start=i.period_start,
                period_end=i.period_end,
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


# --------------------------------------------------------------------------- PURCHASE-1
def to_asset_product_read(p: AssetProduct) -> AssetProductRead:
    return AssetProductRead(
        id=p.id,
        name=p.name,
        vendor=p.vendor,
        asset_category=p.asset_category,
        asset_category_label=ASSET_CATEGORY_LABELS.get(p.asset_category, p.asset_category),
        is_active=p.is_active,
        created_at=p.created_at,
    )


def to_asset_unit_read(u: AssetUnit) -> AssetUnitRead:
    return AssetUnitRead(
        id=u.id,
        unit_no=u.unit_no,
        product_id=u.product_id,
        product_name=u.product_name,
        asset_category=u.asset_category,
        asset_category_label=ASSET_CATEGORY_LABELS.get(u.asset_category, u.asset_category),
        purchase_date=u.purchase_date,
        purchased_from=u.purchased_from,
        price=u.price,
        unit_type=u.unit_type,
        unit_type_label=ASSET_UNIT_TYPE_LABELS.get(u.unit_type) if u.unit_type else None,
        key_value=u.key_value,
        expire_date=u.expire_date,
        status=u.status,
        status_label=ASSET_UNIT_STATUS_LABELS.get(u.status, u.status),
        source_quote_id=u.source_quote_id,
        group_code=u.group_code,
        group_name=GROUPS.get(u.group_code, u.group_code),
        created_at=u.created_at,
        updated_at=u.updated_at,
        retired_at=u.retired_at,
    )


def to_asset_unit_list_item(u: AssetUnit) -> AssetUnitListItem:
    return AssetUnitListItem(
        id=u.id,
        unit_no=u.unit_no,
        product_name=u.product_name,
        asset_category=u.asset_category,
        asset_category_label=ASSET_CATEGORY_LABELS.get(u.asset_category, u.asset_category),
        purchase_date=u.purchase_date,
        price=u.price,
        status=u.status,
        status_label=ASSET_UNIT_STATUS_LABELS.get(u.status, u.status),
        group_code=u.group_code,
        group_name=GROUPS.get(u.group_code, u.group_code),
    )
