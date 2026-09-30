"""자산 등록(직접 · 구매에서 가져오기, 수량 N) · 가져오기 취소 — specs/ASSET-1 § 8-1, 8-2, 8-9.

입력 정리·금액 분할은 `asset_bulk`(순수 함수), 채번은 `asset_no`. 비밀번호 암호화는 트랜잭션
**밖에서** 먼저 한다 — 키가 없으면(501) 아무것도 쓰기 전에 실패(D43).
"""
from __future__ import annotations

from datetime import datetime, timezone

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from ..auth import CurrentUser
from ..config import (
    ASSET_DISPOSED_REASON_IMPORT_CANCELLED,
    ASSET_LINK_IMPORTED,
    ASSET_HIDDEN_STATUSES,
    ASSET_STATUS_DISPOSED,
    ASSET_STATUS_IDLE,
    ASSET_STATUS_IN_USE,
)
from ..database import run_transaction
from ..errors import ALREADY_IMPORTED, ALREADY_RETIRED, ASSET_HAS_HISTORY, NOT_FOUND, AppError, validation
from ..models import Asset, AssetUnit
from . import asset_secret
from .asset_bulk import check_quantity, check_valid_range, clean_fields, split_price
from .asset_no import allocate_asset_nos_in


def _now() -> datetime:
    return datetime.now(timezone.utc)


def prepare_fields(category: str, data: dict) -> dict:
    """등록/수정 공용: 정리 + 비밀번호 암호화(password → password_enc, 값이 있을 때만 — D42)."""
    out = clean_fields(category, data)
    password = out.pop("password", None)
    if password:
        out["password_enc"] = asset_secret.encrypt(password)
    return out


def _build(asset_no: str, category: str, fields: dict, price, user: CurrentUser, now) -> dict:
    asset = Asset(
        asset_no=asset_no,
        category=category,
        name=fields["name"],
        group_code=fields["group_code"],
        scope_group_code=fields["group_code"],
        status=ASSET_STATUS_IDLE,
        created_at=now,
        created_by=user.username,
        updated_at=now,
        updated_by=user.username,
    )
    for k, v in fields.items():
        if k not in ("name", "group_code") and hasattr(asset, k):
            setattr(asset, k, v)
    asset.price = price
    return asset.to_dict()


def _register(client, category: str, fields: dict, quantity: int, prices: list, user, unit_ref=None, unit_check=None) -> list[str]:
    check_valid_range(fields.get("valid_from"), fields.get("valid_to"))
    now = _now()

    def _txn(txn):
        if unit_ref is not None:
            unit_check(unit_ref.get(transaction=txn))
        nos = allocate_asset_nos_in(
            txn, client, category=category, purchase_date=fields.get("purchase_date"), count=quantity
        )
        for no, price in zip(nos, prices):
            txn.set(client.collection("assets").document(no), _build(no, category, fields, price, user, now))
        if unit_ref is not None:
            txn.update(unit_ref, {"asset_link_kind": ASSET_LINK_IMPORTED, "asset_nos": nos, "updated_at": now})
        return nos

    return run_transaction(client, _txn)


# --------------------------------------------------------------------------- § 8-2 직접 등록
def create_assets(client, category: str, data: dict, quantity: int, user: CurrentUser) -> list[str]:
    check_quantity(quantity)
    fields = prepare_fields(category, data)
    return _register(client, category, fields, quantity, [fields.get("price")] * quantity, user)


# --------------------------------------------------------------------------- § 8-1 구매에서 가져오기
def check_linkable(snap) -> AssetUnit:
    """가져오기·갱신 연결 공통 검사(§ 8-1 1단계)."""
    if not snap.exists:
        raise AppError(NOT_FOUND, 404, "구매 기록을 찾을 수 없습니다.")
    unit = AssetUnit.from_doc(snap.id, snap.to_dict())
    if unit.retired_at is not None:
        raise AppError(ALREADY_RETIRED, 409, "폐기된 구매 기록은 가져올 수 없습니다.")
    if unit.asset_link_kind:
        raise AppError(ALREADY_IMPORTED, 409, "이미 자산으로 가져왔거나 갱신에 사용된 구매 기록입니다.")
    return unit


def unit_defaults(unit: AssetUnit) -> dict:
    """구매 유닛 → 자산 값 매핑(COORDINATION C5). 폼이 비워 둔 칸만 이 값으로 채운다(D2 복사)."""
    d = {
        "name": unit.product_name,
        "group_code": unit.group_code,
        "purchase_date": unit.purchase_date.isoformat(),
        "purchased_from": unit.purchased_from,
        "quote_no": unit.source_quote_id,
        "valid_to": unit.expire_date.isoformat() if unit.expire_date else None,
    }
    if unit.asset_category == "EDU":
        d["course_title"] = unit.product_name
    if unit.unit_type == "KEY" and unit.asset_category == "SW":
        d["license_key"] = unit.key_value
    elif unit.unit_type == "ACCOUNT":
        d["account_id"] = unit.key_value
    return d


def import_assets(client, unit_no: str, data: dict, quantity: int, user: CurrentUser) -> list[str]:
    check_quantity(quantity)
    unit_ref = client.collection("asset_units").document(unit_no)
    unit = check_linkable(unit_ref.get())  # 매핑값을 얻으려고 먼저 한 번 읽고, 트랜잭션 안에서 다시 검사
    merged = {
        **unit_defaults(unit),
        **{k: v for k, v in data.items() if v not in (None, "")},
        "source_unit_no": unit.unit_no,
    }
    fields = prepare_fields(unit.asset_category, merged)
    total = fields.get("price") if data.get("price") is not None else unit.price
    return _register(
        client, unit.asset_category, fields, quantity, split_price(total, quantity), user,
        unit_ref=unit_ref, unit_check=check_linkable,
    )


# --------------------------------------------------------------------------- § 8-9 가져오기 취소(D35)
def cancel_import(client, unit_no: str, user: CurrentUser) -> list[str]:
    now = _now()

    def _txn(txn):
        unit_ref = client.collection("asset_units").document(unit_no)
        snap = unit_ref.get(transaction=txn)
        if not snap.exists:
            raise AppError(NOT_FOUND, 404, "구매 기록을 찾을 수 없습니다.")
        if snap.get("asset_link_kind") != ASSET_LINK_IMPORTED:
            raise validation("자산으로 가져온 구매 기록이 아닙니다.")
        q = client.collection("assets").where(filter=FieldFilter("source_unit_no", "==", unit_no))
        assets = [Asset.from_doc(d.to_dict()) for d in q.stream(transaction=txn)]
        assets = [a for a in assets if a.status not in ASSET_HIDDEN_STATUSES]
        nos = [a.asset_no for a in assets]
        if any(a.status == ASSET_STATUS_IN_USE for a in assets) or has_history(txn, client, nos):
            raise AppError(
                ASSET_HAS_HISTORY, 409,
                "사용 이력이 있는 자산이 포함돼 있어 가져오기를 취소할 수 없습니다. 먼저 배정 취소하세요.",
            )
        for no in nos:
            txn.update(client.collection("assets").document(no), {
                "status": ASSET_STATUS_DISPOSED,
                "disposed_reason": ASSET_DISPOSED_REASON_IMPORT_CANCELLED,
                "disposed_at": now,
                "updated_at": now,
                "updated_by": user.username,
            })
        txn.update(unit_ref, {"asset_link_kind": None, "asset_nos": [], "updated_at": now})
        return nos

    return run_transaction(client, _txn)


def has_history(txn, client: firestore.Client, asset_nos: list[str], *, include_renewals: bool = False) -> bool:
    """배정 이력(D35) — 삭제(D47)는 갱신 기록까지 본다."""
    for i in range(0, len(asset_nos), 30):  # Firestore "in" 은 30개까지
        q = (
            client.collection("asset_assignments")
            .where(filter=FieldFilter("asset_no", "in", asset_nos[i : i + 30]))
            .limit(1)
        )
        if any(True for _ in q.stream(transaction=txn)):
            return True
    if include_renewals:
        for no in asset_nos:
            q = client.collection("asset_renewals").where(filter=FieldFilter("asset_nos", "array_contains", no)).limit(1)
            if any(True for _ in q.stream(transaction=txn)):
                return True
    return False
