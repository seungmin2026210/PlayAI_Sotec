"""모델 -> 응답 스키마 변환 (파생 필드 계산)."""
from __future__ import annotations

from .auth import CurrentUser
from .config import (
    ASSET_CATEGORY_LABELS,
    ASSET_DISPOSED_REASON_LABELS,
    ASSET_LINK_LABELS,
    ASSET_MENU_CATEGORY_LABELS,
    ASSET_HIDDEN_STATUSES,
    ASSET_STATUS_LABELS,
    ASSET_SUBCATEGORIES,
    ASSET_UNIT_STATUS_LABELS,
    ASSET_UNIT_TYPE_LABELS,
    COMPANY,
    GROUPS,
    STATUS_LABELS,
)
from .deps import can_see_license_key
from .models import Asset, AssetAssignment, AssetProduct, AssetRenewal, AssetUnit, Member, Quote
from .schemas import (
    AssetListItem,
    AssetProductRead,
    AssetRead,
    AssetUnitListItem,
    AssetUnitRead,
    AssignmentRead,
    ItemOut,
    MemberRead,
    QuoteListItem,
    QuoteRead,
    RenewalRead,
)
from .services.asset_dates import today_kst
from .services.asset_query import expiry_state
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
        **_unit_link(u),
    )


def _unit_link(u: AssetUnit) -> dict:
    return dict(
        asset_link_kind=u.asset_link_kind,
        asset_link_label=ASSET_LINK_LABELS.get(u.asset_link_kind) if u.asset_link_kind else None,
        asset_nos=list(u.asset_nos),
    )


# --------------------------------------------------------------------------- ASSET-1
def mask_license_key(value: str | None, user: CurrentUser) -> str | None:
    """D38 격리 지점: 그룹관리자에겐 앞 4자리 + `-****`. 목록·상세·엑셀 공용."""
    if not value or can_see_license_key(user):
        return value
    return f"{value[:4]}-****" if len(value) > 4 else "****"


def expiry_badge(asset: Asset) -> str | None:
    """"EXPIRED" | "EXPIRING" | None — KST 오늘 기준(D21, D45). 폐기·삭제 자산엔 배지 없음."""
    if asset.status in ASSET_HIDDEN_STATUSES:
        return None
    st = expiry_state(asset.valid_to, today_kst())
    return st.upper() if st else None


def _asset_base(a: Asset, user: CurrentUser) -> dict:
    return dict(
        asset_no=a.asset_no,
        category=a.category,
        category_label=ASSET_MENU_CATEGORY_LABELS.get(a.category, a.category),
        subcategory=a.subcategory,
        subcategory_label=ASSET_SUBCATEGORIES.get(a.category, {}).get(a.subcategory) if a.subcategory else None,
        name=a.name,
        status=a.status,
        status_label=ASSET_STATUS_LABELS.get(a.status, a.status),
        group_code=a.group_code,
        group_name=GROUPS.get(a.group_code, a.group_code),
        scope_group_code=a.scope_group_code,
        scope_group_name=GROUPS.get(a.scope_group_code, a.scope_group_code),
        current_member_id=a.current_member_id,
        current_member_name=a.current_member_name,
        current_shared_label=a.current_shared_label,
        current_start_date=a.current_start_date,
        purchase_date=a.purchase_date,
        price=a.price,
        valid_from=a.valid_from,
        valid_to=a.valid_to,
        expiry_badge=expiry_badge(a),
        version=a.version,
        license_key=mask_license_key(a.license_key, user),
        account_id=a.account_id,
        has_password=bool(a.password_enc),
        manufacturer=a.manufacturer,
        model=a.model,
        serial_no=a.serial_no,
        mac_address=a.mac_address,
        course_title=a.course_title,
        course_url=a.course_url,
        quote_no=a.quote_no,
        contract_no=a.contract_no,
        source_unit_no=a.source_unit_no,
        purchased_from=a.purchased_from,
        note=a.note,
        disposed_reason=a.disposed_reason,
        disposed_reason_label=ASSET_DISPOSED_REASON_LABELS.get(a.disposed_reason) if a.disposed_reason else None,
        read_only=a.status in ASSET_HIDDEN_STATUSES,
    )


def to_asset_list_item(a: Asset, user: CurrentUser) -> AssetListItem:
    return AssetListItem(**_asset_base(a, user))


def to_assignment_read(x: AssetAssignment) -> AssignmentRead:
    return AssignmentRead(
        id=x.id, asset_no=x.asset_no, category=x.category, asset_name=x.asset_name,
        member_id=x.member_id, member_name=x.member_name, shared_label=x.shared_label,
        start_date=x.start_date, end_date=x.end_date, note=x.note,
        created_by=x.created_by, updated_at=x.updated_at, updated_by=x.updated_by,
    )


def to_asset_read(
    a: Asset, user: CurrentUser, assignments: list[AssetAssignment], renewals: list[AssetRenewal]
) -> AssetRead:
    return AssetRead(
        **_asset_base(a, user),
        disposed_at=a.disposed_at,
        deleted_at=a.deleted_at,
        deleted_by=a.deleted_by,
        deleted_reason=a.deleted_reason,
        created_at=a.created_at,
        created_by=a.created_by,
        updated_at=a.updated_at,
        updated_by=a.updated_by,
        assignments=[to_assignment_read(x) for x in assignments],
        renewals=[
            RenewalRead(
                id=r.id, prev_valid_to=r.prev_valid_to, new_valid_from=r.new_valid_from,
                new_valid_to=r.new_valid_to, unit_no=r.unit_no, count=len(r.asset_nos),
                created_at=r.created_at, created_by=r.created_by,
            )
            for r in renewals
        ],
    )


def to_member_read(m: Member, counts: dict[str, int], warning: str | None = None) -> MemberRead:
    return MemberRead(
        employee_no=m.employee_no, name=m.name, group_code=m.group_code,
        group_name=GROUPS.get(m.group_code, m.group_code), active=m.active,
        counts=counts, warning=warning,
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
        **_unit_link(u),
    )
