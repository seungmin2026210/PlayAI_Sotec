"""구매관리 API — 유닛(무엇을 언제 얼마에 샀는지) 등록/목록/조회/폐기.

배정(누구에게 줬는지)은 이 라우터 범위가 아니다 — 자산관리 탭(`asset_assignments`)은
별도로 구현된다(specs/PURCHASE-1/DECISIONS.md "구매관리·자산관리 관심사 분리").
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from google.cloud import firestore

from ..auth import CurrentUser
from ..config import ASSET_UNIT_STATUS_AVAILABLE, ASSET_UNIT_STATUS_EXPIRED
from ..database import run_transaction
from ..deps import assert_can_view_asset_unit, get_current_user, get_db, require_super_admin, scope_group
from ..errors import ALREADY_RETIRED, NOT_FOUND, PRODUCT_INACTIVE, AppError
from ..models import AssetProduct, AssetUnit, Quote
from ..presenter import to_asset_unit_list_item, to_asset_unit_read
from ..schemas import AssetUnitCreate, AssetUnitListResponse, AssetUnitPatch, AssetUnitRead
from ..services import asset_numbering
from ..services.asset_query import list_asset_units as query_asset_units
from ..services.status import apply_purchase_lock

router = APIRouter(prefix="/api/asset-units", tags=["asset-units"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_product_or_404(client: firestore.Client, product_id: str) -> AssetProduct:
    doc = client.collection("asset_products").document(product_id).get()
    if not doc.exists:
        raise AppError(NOT_FOUND, 404, "상품을 찾을 수 없습니다.")
    return AssetProduct.from_doc(doc.id, doc.to_dict())


def _load_unit_or_404(client: firestore.Client, unit_no: str, user: CurrentUser) -> AssetUnit:
    doc = client.collection("asset_units").document(unit_no).get()
    if not doc.exists:
        raise AppError(NOT_FOUND, 404, "자산을 찾을 수 없습니다.")
    unit = AssetUnit.from_doc(doc.id, doc.to_dict())
    assert_can_view_asset_unit(unit, user)
    return unit


# --------------------------------------------------------------------------- list
@router.get("", response_model=AssetUnitListResponse)
def list_asset_units(
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    product_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    group_code: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
) -> AssetUnitListResponse:
    units = query_asset_units(
        client,
        scope_group=scope_group(user),
        group_code=group_code,
        product_id=product_id,
        status=status,
    )
    total = len(units)
    start = (page - 1) * size
    page_items = units[start : start + size]
    return AssetUnitListResponse(
        total=total, page=page, size=size, items=[to_asset_unit_list_item(u) for u in page_items]
    )


# --------------------------------------------------------------------------- create
@router.post("", response_model=AssetUnitRead, status_code=201)
def create_asset_unit(
    body: AssetUnitCreate,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetUnitRead:
    product = _load_product_or_404(client, body.product_id)
    if not product.is_active:
        raise AppError(
            PRODUCT_INACTIVE, 409, "사용 중지된 상품입니다. 상품을 다시 활성화하거나 다른 상품을 선택하세요."
        )

    now = _now()

    def _txn(transaction: firestore.Transaction) -> AssetUnit:
        # Firestore 트랜잭션은 모든 read 가 write 보다 먼저여야 한다 — 견적서를 먼저 읽고,
        # 그 다음 채번(내부적으로 read-then-write)을 호출한 뒤에야 쓰기를 시작한다.
        quote_ref = None
        quote: Quote | None = None
        if body.source_quote_id:
            quote_ref = client.collection("quotes").document(body.source_quote_id)
            quote_doc = quote_ref.get(transaction=transaction)
            if quote_doc.exists:
                quote = Quote.from_doc(quote_doc.id, quote_doc.to_dict())

        alloc = asset_numbering.allocate_unit_no_in(
            transaction, client, product_id=product.id, product_name=product.name
        )

        unit = AssetUnit(
            id=alloc.unit_no,
            unit_no=alloc.unit_no,
            product_id=product.id,
            product_name=product.name,
            asset_category=product.asset_category,
            purchase_date=body.purchase_date,
            purchased_from=body.purchased_from,
            price=body.price,
            unit_type=body.unit_type,
            key_value=body.key_value,
            expire_date=body.expire_date,
            status=ASSET_UNIT_STATUS_AVAILABLE,
            source_quote_id=body.source_quote_id,
            group_code=body.group_code,
            created_at=now,
        )
        transaction.set(client.collection("asset_units").document(alloc.unit_no), unit.to_dict())

        # 견적 연동 시 견적서 자동 잠금 — QUOTE-1의 기존 apply_purchase_lock 재사용
        # (specs/QUOTE-1/DECISIONS.md open-4 "구매관리 반영 트리거"를 여기서 실연동).
        if quote is not None and apply_purchase_lock(quote):
            transaction.update(quote_ref, {"purchase_locked": True, "locked_at": quote.locked_at})

        return unit

    unit = run_transaction(client, _txn)
    return to_asset_unit_read(unit)


# --------------------------------------------------------------------------- detail
@router.get("/{unit_no}", response_model=AssetUnitRead)
def get_asset_unit(
    unit_no: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> AssetUnitRead:
    return to_asset_unit_read(_load_unit_or_404(client, unit_no, user))


# --------------------------------------------------------------------------- update
@router.patch("/{unit_no}", response_model=AssetUnitRead)
def patch_asset_unit(
    unit_no: str,
    body: AssetUnitPatch,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetUnitRead:
    """구매 정보 수정. 삭제는 없음(번호 영구 보존 원칙) — 잘못 등록했으면 여기서 고친다.
    상품·유닛번호·연동 견적서는 바꾸지 않는다. 이미 폐기된 유닛은 수정도 막는다."""
    unit = _load_unit_or_404(client, unit_no, user)
    if unit.status == ASSET_UNIT_STATUS_EXPIRED:
        raise AppError(ALREADY_RETIRED, 409, "폐기된 자산은 수정할 수 없습니다.")

    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(unit, field, value)
    unit.updated_at = _now()

    # AssetUnit.to_dict() 저장 규칙과 동일하게 date 필드는 isoformat 문자열로 변환해서 씀
    date_fields = {"purchase_date", "expire_date"}
    stored = {k: (v.isoformat() if k in date_fields and v is not None else v) for k, v in changes.items()}
    client.collection("asset_units").document(unit_no).update({**stored, "updated_at": unit.updated_at})
    return to_asset_unit_read(unit)


# --------------------------------------------------------------------------- retire
@router.post("/{unit_no}/retire", response_model=AssetUnitRead)
def retire_asset_unit(
    unit_no: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetUnitRead:
    """만료/폐기 — 물리 삭제 없음. 번호는 영구 보존(재사용 안 함).

    아직 배정 중(`ASSIGNED`)인 유닛의 반납은 자산관리 탭(팀원 구현) 소관이라 여기선
    상태값만 보고 판단한다 — 이 PR 범위에서 생성되는 유닛은 항상 AVAILABLE 이므로
    실제로 ASSIGNED 상태를 다루는 건 자산관리 기능이 붙은 뒤부터다."""
    unit = _load_unit_or_404(client, unit_no, user)
    if unit.status == ASSET_UNIT_STATUS_EXPIRED:
        raise AppError(ALREADY_RETIRED, 409, "이미 폐기 처리된 자산입니다.")

    now = _now()
    client.collection("asset_units").document(unit_no).update(
        {"status": ASSET_UNIT_STATUS_EXPIRED, "retired_at": now, "updated_at": now}
    )
    unit.status = ASSET_UNIT_STATUS_EXPIRED
    unit.retired_at = now
    unit.updated_at = now
    return to_asset_unit_read(unit)
