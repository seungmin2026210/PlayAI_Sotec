"""자산관리 API — specs/ASSET-1/TECH.md "API 엔드포인트". HTTP·권한·직렬화만, 로직은 services.

라우트 선언 순서: `/api/assets/` 아래 고정 경로(export.xlsx, importable, import, import/cancel, renew)를
`/{asset_no}` 계열보다 **먼저** 둔다(QUOTE-1 export.xlsx 와 같은 이유).
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query, Response
from google.cloud import firestore

from ..auth import CurrentUser
from ..config import (
    ASSET_CATEGORIES,
    ASSET_DISPOSED_REASON_DISPOSED,
    ASSET_STATUS_DELETED,
    ASSET_STATUS_DISPOSED,
    ROLE_SUPER_ADMIN,
)
from ..database import run_transaction
from ..deps import (
    assert_can_view_asset,
    can_reveal_password,
    can_see_license_key,
    get_current_user,
    get_db,
    require_super_admin,
    scope_group,
)
from ..errors import FORBIDDEN_ROLE, NOT_FOUND, AppError, validation
from ..models import Asset
from ..presenter import to_asset_list_item, to_asset_read, to_asset_unit_read
from ..schemas import (
    AssetCreate,
    AssetCreateResponse,
    AssetDeleteRequest,
    AssetImport,
    AssetListResponse,
    AssetRead,
    AssetUnitRead,
    AssetUpdate,
    AssignmentPatch,
    AssignRequest,
    RenewRequest,
    ReturnRequest,
    RevealRequest,
    RevealResponse,
    TransferRequest,
    UnitNoRequest,
)
from ..services import asset_assignment, asset_registration, asset_renewal, asset_secret
from ..services.asset_bulk import check_valid_range
from ..services.asset_query import asset_history, importable_units, list_assets
from ..services.asset_registration import has_history
from ..services.asset_status import guard_deletable, guard_disposable, guard_not_disposed
from ..services.export_excel import asset_list_filename, build_asset_list_xlsx

router = APIRouter(prefix="/api", tags=["assets"])

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(d) -> str | None:
    return d.isoformat() if d else None


def _load_or_404(client: firestore.Client, asset_no: str, user: CurrentUser) -> Asset:
    snap = client.collection("assets").document(asset_no).get()
    if not snap.exists:
        raise AppError(NOT_FOUND, 404, "자산을 찾을 수 없습니다.")
    asset = Asset.from_doc(snap.to_dict())
    assert_can_view_asset(asset, user)
    return asset


def _detail(client, asset_no: str, user: CurrentUser) -> AssetRead:
    asset = _load_or_404(client, asset_no, user)
    assignments, renewals = asset_history(client, asset_no)
    return to_asset_read(asset, user, assignments, renewals)


def _category(v: str) -> str:
    if v not in ASSET_CATEGORIES:
        raise validation(f"자산 유형은 {', '.join(ASSET_CATEGORIES)} 중 하나여야 합니다.")
    return v


def _query(client, user, category, subcategory, member_id, group, status, expiry, year, name, valid_to, q):
    if status == ASSET_STATUS_DELETED and user.role != ROLE_SUPER_ADMIN:
        return []  # D47: 삭제된 자산은 전체관리자만
    return list_assets(
        client,
        category=_category(category),
        scope_group=scope_group(user),
        include_license_key=can_see_license_key(user),
        subcategory=subcategory or None,
        member_id=member_id or None,
        group=group or None,
        status=status or None,
        expiry=expiry or None,
        year=year,
        name=name or None,
        valid_to=_iso(valid_to),
        q=q,
    )


# --------------------------------------------------------------------------- 목록 / 엑셀
@router.get("/assets", response_model=AssetListResponse)
def list_(
    category: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    subcategory: str | None = None,
    member_id: str | None = None,
    group: str | None = None,
    status: str | None = None,
    expiry: str | None = None,
    year: int | None = None,
    name: str | None = None,
    valid_to: date | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
) -> AssetListResponse:
    items = _query(client, user, category, subcategory, member_id, group, status, expiry, year, name, valid_to, q)
    start = (page - 1) * size
    return AssetListResponse(
        total=len(items), page=page, size=size,
        items=[to_asset_list_item(a, user) for a in items[start : start + size]],
    )


@router.get("/assets/export.xlsx")
def export_xlsx(
    category: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    subcategory: str | None = None,
    member_id: str | None = None,
    group: str | None = None,
    status: str | None = None,
    expiry: str | None = None,
    year: int | None = None,
    name: str | None = None,
    valid_to: date | None = None,
    q: str | None = None,
) -> Response:
    items = _query(client, user, category, subcategory, member_id, group, status, expiry, year, name, valid_to, q)
    content = build_asset_list_xlsx(category, [to_asset_list_item(a, user) for a in items])
    return Response(
        content=content, media_type=_XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{asset_list_filename(category)}"'},
    )


# --------------------------------------------------------------------------- 가져오기 · 갱신
@router.get("/assets/importable", response_model=list[AssetUnitRead])
def importable(
    category: str | None = None,
    client: firestore.Client = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> list[AssetUnitRead]:
    return [to_asset_unit_read(u) for u in importable_units(client, category)]


@router.post("/assets/import", response_model=AssetCreateResponse, status_code=201)
def import_(
    body: AssetImport,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetCreateResponse:
    data = body.model_dump(exclude={"unit_no", "quantity"})
    nos = asset_registration.import_assets(client, body.unit_no, data, body.quantity, user)
    return AssetCreateResponse(asset_nos=nos)


@router.post("/assets/import/cancel", response_model=AssetCreateResponse)
def cancel_import(
    body: UnitNoRequest,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetCreateResponse:
    return AssetCreateResponse(asset_nos=asset_registration.cancel_import(client, body.unit_no, user))


@router.post("/assets/renew", response_model=AssetCreateResponse)
def renew(
    body: RenewRequest,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetCreateResponse:
    asset_renewal.renew(
        client, body.asset_nos,
        new_valid_to=body.new_valid_to.isoformat(), new_valid_from=_iso(body.new_valid_from),
        unit_no=body.unit_no or None, user=user,
    )
    return AssetCreateResponse(asset_nos=sorted(set(body.asset_nos)))


# --------------------------------------------------------------------------- 직접 등록
@router.post("/assets", response_model=AssetCreateResponse, status_code=201)
def create(
    body: AssetCreate,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetCreateResponse:
    data = body.model_dump(exclude={"category", "quantity"})
    return AssetCreateResponse(
        asset_nos=asset_registration.create_assets(client, body.category, data, body.quantity, user)
    )


# --------------------------------------------------------------------------- 상세 / 수정 / 폐기 / 삭제
@router.get("/assets/{asset_no}", response_model=AssetRead)
def detail(
    asset_no: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> AssetRead:
    return _detail(client, asset_no, user)


@router.patch("/assets/{asset_no}", response_model=AssetRead)
def update(
    asset_no: str,
    body: AssetUpdate,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetRead:
    asset = _load_or_404(client, asset_no, user)
    guard_not_disposed(asset)
    if body.category is not None and body.category != asset.category:
        raise validation("자산 유형은 바꿀 수 없습니다. 가져오기 취소/폐기 후 다시 등록하세요.")  # D41

    raw = body.model_dump(exclude_unset=True, exclude={"category"})
    if "name" in raw and raw["name"] is None:
        raise validation("품명을 입력해야 합니다.")
    if "group_code" in raw and raw["group_code"] is None:
        raise validation("그룹을 선택해야 합니다.")
    fields = asset_registration.prepare_fields(asset.category, raw)  # password → password_enc(값 있을 때만)
    check_valid_range(fields.get("valid_from", asset.valid_from), fields.get("valid_to", asset.valid_to))
    now = _now()

    def _txn(txn):
        ref, cur = asset_assignment.load_asset_in(txn, client, asset_no)
        guard_not_disposed(cur)
        upd = {**fields, "updated_at": now, "updated_by": user.username}
        # 등록 그룹 변경: 팀원이 쓰는 중이 아니면 조회 스코프도 따라간다(D24)
        if "group_code" in fields and not cur.current_member_id:
            upd["scope_group_code"] = fields["group_code"]
        txn.update(ref, upd)

    run_transaction(client, _txn)
    return _detail(client, asset_no, user)


@router.delete("/assets/{asset_no}/password", response_model=AssetRead)
def delete_password(
    asset_no: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetRead:
    guard_not_disposed(_load_or_404(client, asset_no, user))
    client.collection("assets").document(asset_no).update(
        {"password_enc": None, "updated_at": _now(), "updated_by": user.username}
    )
    return _detail(client, asset_no, user)


@router.post("/assets/{asset_no}/password/reveal", response_model=RevealResponse)
def reveal_password(
    asset_no: str,
    body: RevealRequest,
    response: Response,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> RevealResponse:
    """GET 이 아니라 POST — 캐시·접근로그에 평문이 남지 않게(§ 8-11)."""
    asset = _load_or_404(client, asset_no, user)
    if not can_reveal_password(asset, user):
        raise AppError(FORBIDDEN_ROLE, 403, "비밀번호는 전체관리자만 볼 수 있습니다.")
    if not asset.password_enc:
        raise AppError(NOT_FOUND, 404, "저장된 비밀번호가 없습니다.")
    plain = asset_secret.decrypt(asset.password_enc)
    # 기록이 실패하면 예외가 올라가 평문도 반환되지 않는다(D44)
    client.collection("password_reveal_logs").add(
        {"asset_no": asset_no, "username": user.username, "action": body.action, "at": _now()}
    )
    response.headers["Cache-Control"] = "no-store"
    return RevealResponse(password=plain)


@router.post("/assets/{asset_no}/dispose", response_model=AssetRead)
def dispose(
    asset_no: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetRead:
    now = _now()

    def _txn(txn):
        ref, asset = asset_assignment.load_asset_in(txn, client, asset_no)
        guard_disposable(asset)
        txn.update(ref, {
            "status": ASSET_STATUS_DISPOSED, "disposed_at": now,
            "disposed_reason": ASSET_DISPOSED_REASON_DISPOSED,
            "updated_at": now, "updated_by": user.username,
        })

    run_transaction(client, _txn)
    return _detail(client, asset_no, user)


@router.post("/assets/{asset_no}/delete", response_model=AssetRead)
def delete(
    asset_no: str,
    body: AssetDeleteRequest,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetRead:
    """D47: 잘못 등록한 기록 삭제 — soft delete(번호 결번, 누가·언제·왜 기록). 되돌릴 수 없음."""
    now = _now()

    def _txn(txn):
        ref, asset = asset_assignment.load_asset_in(txn, client, asset_no)
        guard_deletable(asset, has_history(txn, client, [asset_no], include_renewals=True))
        txn.update(ref, {
            "status": ASSET_STATUS_DELETED, "deleted_at": now, "deleted_by": user.username,
            "deleted_reason": body.reason, "updated_at": now, "updated_by": user.username,
        })

    run_transaction(client, _txn)
    return _detail(client, asset_no, user)


# --------------------------------------------------------------------------- 배정 · 회수 · 이관 · 취소
@router.post("/assets/{asset_no}/assign", response_model=AssetRead)
def assign(
    asset_no: str,
    body: AssignRequest,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetRead:
    asset_assignment.assign(
        client, asset_no, member_id=body.member_id, shared_label=body.shared_label,
        start_date=body.start_date.isoformat(), note=body.note, user=user,
    )
    return _detail(client, asset_no, user)


@router.post("/assets/{asset_no}/return", response_model=AssetRead)
def return_(
    asset_no: str,
    body: ReturnRequest,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetRead:
    asset_assignment.return_asset(client, asset_no, end_date=body.end_date.isoformat(), note=body.note, user=user)
    return _detail(client, asset_no, user)


@router.post("/assets/{asset_no}/transfer", response_model=AssetRead)
def transfer(
    asset_no: str,
    body: TransferRequest,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetRead:
    asset_assignment.transfer(
        client, asset_no, member_id=body.member_id, shared_label=body.shared_label,
        date=body.date.isoformat(), note=body.note, user=user,
    )
    return _detail(client, asset_no, user)


@router.post("/assets/{asset_no}/assignment/cancel", response_model=AssetRead)
def cancel_assignment(
    asset_no: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetRead:
    asset_assignment.cancel_assignment(client, asset_no, user=user)
    return _detail(client, asset_no, user)


@router.patch("/asset-assignments/{assignment_id}", response_model=AssetRead)
def edit_assignment(
    assignment_id: str,
    body: AssignmentPatch,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(require_super_admin),
) -> AssetRead:
    kw = {}
    if "note" in body.model_fields_set:
        kw["note"] = body.note
    asset_no = asset_assignment.edit_assignment(
        client, assignment_id, start_date=_iso(body.start_date), end_date=_iso(body.end_date), user=user, **kw
    )
    return _detail(client, asset_no, user)
