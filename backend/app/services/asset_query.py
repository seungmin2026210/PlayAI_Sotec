"""자산 유닛 목록 조회 — services/query.py(견적서)와 동일 원칙.

등호 필터(그룹/상품/상태)만 Firestore 쿼리로 걸고, 정렬은 created_at desc. 이 범위(구매관리)는
부분일치 텍스트 검색이 필요하다는 요구가 아직 없어 추가하지 않았다(YAGNI) — 필요해지면
services/query.py의 패턴을 그대로 가져오면 된다.
"""
from __future__ import annotations

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from ..models import AssetUnit


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
