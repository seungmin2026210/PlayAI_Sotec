"""자산 유닛 목록 조회 — services/query.py(견적서)와 동일 원칙.

등호 필터(그룹/상품/상태)만 Firestore 쿼리로 걸고, 정렬은 created_at desc. 이 범위(구매관리)는
부분일치 텍스트 검색이 필요하다는 요구가 아직 없어 추가하지 않았다(YAGNI) — 필요해지면
services/query.py의 패턴을 그대로 가져오면 된다.
"""
from __future__ import annotations

from datetime import date, timedelta

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from ..config import (
    ASSET_CATEGORIES,
    ASSET_EXPIRING_DAYS,
    ASSET_RENEWAL_KPI_FAR_DAYS,
    ASSET_STATUS_DISPOSED,
    ASSET_STATUS_IN_USE,
)
from ..models import Asset, AssetAssignment, AssetRenewal, AssetUnit, Member
from .asset_dates import today_kst


def list_asset_units(
    client: firestore.Client,
    *,
    scope_group: str | None,
    group_code: str | None = None,
    product_id: str | None = None,
    status: str | None = None,
) -> list[AssetUnit]:
    if scope_group is not None:
        if group_code is not None and group_code != scope_group:
            return []
        effective_group = scope_group
    else:
        effective_group = group_code

    q = client.collection("asset_units")
    if effective_group:
        q = q.where(filter=FieldFilter("group_code", "==", effective_group))
    if product_id:
        q = q.where(filter=FieldFilter("product_id", "==", product_id))
    if status:
        q = q.where(filter=FieldFilter("status", "==", status))
    q = q.order_by("created_at", direction=firestore.Query.DESCENDING)

    return [AssetUnit.from_doc(doc.id, doc.to_dict()) for doc in q.stream()]


def importable_units(client: firestore.Client, category: str | None) -> list[AssetUnit]:
    """ASSET-1: 가져오기/갱신 연결 후보 — 연결 안 됨(`asset_link_kind` 없음)·미폐기. 재판매품 포함 전부."""
    q = client.collection("asset_units")
    if category:
        q = q.where(filter=FieldFilter("asset_category", "==", category))
    units = [AssetUnit.from_doc(d.id, d.to_dict()) for d in q.stream()]
    units = [u for u in units if not u.asset_link_kind and u.retired_at is None]
    return sorted(units, key=lambda u: u.created_at, reverse=True)


# =========================================================================== ASSET-1 자산
# 원칙(tech/01-data-model.md § 9): 등호 필터만 Firestore, 나머지는 애플리케이션 레벨.
# 등호 필터만 쓰면 복합 인덱스가 필요 없다(Firestore 가 단일 필드 인덱스 병합으로 처리).
_KEYWORD_FIELDS = (
    "asset_no", "name", "serial_no", "account_id", "manufacturer", "model",
    "course_title", "quote_no", "contract_no", "note",
)


def expiry_state(valid_to: str | None, today: date) -> str | None:
    """"expired" | "expiring"(ASSET_EXPIRING_DAYS 이내) | None. 날짜 = KST 오늘(D45)."""
    if not valid_to:
        return None
    t = today.isoformat()
    if valid_to < t:
        return "expired"
    if valid_to <= (today + timedelta(days=ASSET_EXPIRING_DAYS)).isoformat():
        return "expiring"
    return None


def _scoped_assets(client: firestore.Client, scope_group: str | None, category: str | None = None) -> list[Asset]:
    q = client.collection("assets")
    if category:
        q = q.where(filter=FieldFilter("category", "==", category))
    if scope_group is not None:
        q = q.where(filter=FieldFilter("scope_group_code", "==", scope_group))
    return [Asset.from_doc(d.to_dict()) for d in q.stream()]


def list_assets(
    client: firestore.Client,
    *,
    category: str,
    scope_group: str | None,
    include_license_key: bool,
    subcategory: str | None = None,
    member_id: str | None = None,
    group: str | None = None,
    status: str | None = None,
    expiry: str | None = None,
    year: int | None = None,
    name: str | None = None,
    valid_to: str | None = None,
    q: str | None = None,
) -> list[Asset]:
    if scope_group is not None and group and group != scope_group:
        return []
    today = today_kst()
    kw_fields = _KEYWORD_FIELDS + (("license_key",) if include_license_key else ())  # D38
    kw = (q or "").strip().lower()

    def keep(a: Asset) -> bool:
        if status:
            if a.status != status:
                return False
        elif a.status == ASSET_STATUS_DISPOSED:  # 기본: 폐기 숨김
            return False
        if subcategory and a.subcategory != subcategory:
            return False
        if group and a.scope_group_code != group:
            return False
        if member_id == "SHARED":
            if not (a.status == ASSET_STATUS_IN_USE and a.current_shared_label):
                return False
        elif member_id == "EXTERNAL":
            if not (a.status == ASSET_STATUS_IN_USE and a.current_external_label):
                return False
        elif member_id and a.current_member_id != member_id:
            return False
        if expiry:
            st = expiry_state(a.valid_to, today)
            if (expiry == "ok" and st is not None) or (expiry in ("expired", "expiring") and st != expiry):
                return False
        if year and not (a.purchase_date or "").startswith(f"{year:04d}"):
            return False
        if name and a.name != name:
            return False
        if valid_to and a.valid_to != valid_to:
            return False
        if kw and not any(kw in str(getattr(a, f) or "").lower() for f in kw_fields):
            return False
        return True

    items = [a for a in _scoped_assets(client, scope_group, category) if keep(a)]
    return sorted(items, key=lambda a: a.asset_no, reverse=True)


def asset_history(client: firestore.Client, asset_no: str) -> tuple[list[AssetAssignment], list[AssetRenewal]]:
    a_q = client.collection("asset_assignments").where(filter=FieldFilter("asset_no", "==", asset_no))
    r_q = client.collection("asset_renewals").where(filter=FieldFilter("asset_nos", "array_contains", asset_no))
    assignments = sorted(
        (AssetAssignment.from_doc(d.id, d.to_dict()) for d in a_q.stream()),
        key=lambda a: (a.start_date, a.created_at), reverse=True,
    )
    renewals = sorted(
        (AssetRenewal.from_doc(d.id, d.to_dict()) for d in r_q.stream()),
        key=lambda r: r.created_at, reverse=True,
    )
    return assignments, renewals


# --------------------------------------------------------------------------- 사용자별 탭
def list_members(client: firestore.Client, scope_group: str | None) -> list[tuple[Member, dict[str, int]]]:
    """팀원 + 유형별 현재 사용 개수. 그룹관리자는 본인 그룹 팀원만(D46). 공용은 집계 제외."""
    q = client.collection("members")
    if scope_group is not None:
        q = q.where(filter=FieldFilter("group_code", "==", scope_group))
    members = [Member.from_doc(d.to_dict()) for d in q.stream()]

    counts: dict[str, dict[str, int]] = {}
    in_use = client.collection("assets").where(filter=FieldFilter("status", "==", ASSET_STATUS_IN_USE))
    for d in in_use.stream():
        mid = d.get("current_member_id")
        if mid:
            c = counts.setdefault(mid, dict.fromkeys(ASSET_CATEGORIES, 0))
            c[d.get("category")] = c.get(d.get("category"), 0) + 1

    members.sort(key=lambda m: (not m.active, m.name))
    return [(m, counts.get(m.employee_no, dict.fromkeys(ASSET_CATEGORIES, 0))) for m in members]


def member_assignments(
    client: firestore.Client, employee_no: str, scope_group: str | None
) -> list[tuple[AssetAssignment, bool]]:
    """한 사람의 현재+과거 이력. 두 번째 값 = linkable(D37): 그룹관리자에게 지금 다른 그룹
    스코프인 자산은 줄만 보이고 상세 링크 없음."""
    q = client.collection("asset_assignments").where(filter=FieldFilter("member_id", "==", employee_no))
    rows = sorted(
        (AssetAssignment.from_doc(d.id, d.to_dict()) for d in q.stream()),
        key=lambda a: a.start_date, reverse=True,
    )
    rows.sort(key=lambda a: a.end_date is not None)  # 안정 정렬: 현재 사용 중 먼저, 각 묶음은 최신순
    if scope_group is None:
        return [(a, True) for a in rows]
    refs = [client.collection("assets").document(n) for n in {a.asset_no for a in rows}]
    scope = {s.id: s.get("scope_group_code") for s in client.get_all(refs) if s.exists} if refs else {}
    return [(a, scope.get(a.asset_no) == scope_group) for a in rows]


# --------------------------------------------------------------------------- 대시보드(D28, D29, D39)
def renewal_calendar(
    client: firestore.Client, *, scope_group: str | None, date_from: str, date_to: str
) -> tuple[list[dict], dict[str, int]]:
    """유효기간 종료일이 있는 미폐기 자산을 (종료일, 품명, 유형)으로 묶는다 + KPI."""
    today = today_kst()
    t = today.isoformat()
    d30 = (today + timedelta(days=ASSET_EXPIRING_DAYS)).isoformat()
    d90 = (today + timedelta(days=ASSET_RENEWAL_KPI_FAR_DAYS)).isoformat()
    assets = [
        a for a in _scoped_assets(client, scope_group)
        if a.valid_to and a.status != ASSET_STATUS_DISPOSED
    ]
    kpi = {
        "expired": sum(a.valid_to < t for a in assets),
        "d30": sum(t <= a.valid_to <= d30 for a in assets),
        "d90": sum(t <= a.valid_to <= d90 for a in assets),
    }
    groups: dict[tuple[str, str, str], list[str]] = {}
    for a in assets:
        if date_from <= a.valid_to <= date_to:
            groups.setdefault((a.valid_to, a.name, a.category), []).append(a.asset_no)
    items = [
        {"date": d, "name": n, "category": c, "count": len(nos), "asset_nos": sorted(nos)}
        for (d, n, c), nos in sorted(groups.items())
    ]
    return items, kpi
