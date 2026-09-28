"""상품 마스터 API — specs/PURCHASE-1/DECISIONS.md "상품 마스터 도입"."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from google.cloud import firestore

from ..auth import CurrentUser
from ..deps import get_current_user, get_db, require_super_admin
from ..errors import NOT_FOUND, AppError
from ..models import AssetProduct
from ..presenter import to_asset_product_read
from ..schemas import AssetProductCreate, AssetProductListResponse, AssetProductPatch, AssetProductRead

router = APIRouter(prefix="/api/asset-products", tags=["asset-products"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_or_404(client: firestore.Client, product_id: str) -> AssetProduct:
    doc = client.collection("asset_products").document(product_id).get()
    if not doc.exists:
        raise AppError(NOT_FOUND, 404, "상품을 찾을 수 없습니다.")
    return AssetProduct.from_doc(doc.id, doc.to_dict())


@router.get("", response_model=AssetProductListResponse)
def list_asset_products(
    client: firestore.Client = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
    is_active: bool | None = Query(default=None),
) -> AssetProductListResponse:
    docs = client.collection("asset_products").stream()
    products = [AssetProduct.from_doc(d.id, d.to_dict()) for d in docs]
    if is_active is not None:
        products = [p for p in products if p.is_active == is_active]
    products.sort(key=lambda p: p.created_at)
    return AssetProductListResponse(items=[to_asset_product_read(p) for p in products])


@router.post("", response_model=AssetProductRead, status_code=201)
def create_asset_product(
    body: AssetProductCreate,
    client: firestore.Client = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> AssetProductRead:
    ref = client.collection("asset_products").document()
    product = AssetProduct(
        id=ref.id,
        name=body.name,
        vendor=body.vendor,
        asset_category=body.asset_category,
        is_active=True,
        created_at=_now(),
    )
    ref.set(product.to_dict())
    return to_asset_product_read(product)


@router.patch("/{product_id}", response_model=AssetProductRead)
def patch_asset_product(
    product_id: str,
    body: AssetProductPatch,
    client: firestore.Client = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> AssetProductRead:
    """이름/벤더/사용여부만 수정. 비활성화(`is_active=false`)는 삭제가 아니라 신규 구매
    드롭다운에서만 숨기는 것 — 이미 만들어진 유닛은 그대로 이 상품을 참조한다."""
    product = _load_or_404(client, product_id)
    if body.name is not None:
        product.name = body.name
    if body.vendor is not None:
        product.vendor = body.vendor
    if body.is_active is not None:
        product.is_active = body.is_active

    client.collection("asset_products").document(product_id).set(product.to_dict())
    return to_asset_product_read(product)
