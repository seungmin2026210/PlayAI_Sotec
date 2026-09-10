"""견적서 목록 조회 — Firestore 등호 필터 + 애플리케이션 레벨 텍스트/날짜 필터.

TECH 12-firestore-migration.md § 3. Firestore 는 `ILIKE '%x%'` 부분일치·임의 필드
조합의 range 쿼리를 지원하지 않는다. 이 프로젝트 규모(내부 도구)에서는:
- 인덱스 친화적인 등호 필터(그룹/상태/active)만 Firestore 쿼리로 걸고,
- 부분일치 텍스트(mgmt_no/title/issuer_name)·날짜 range·페이지네이션은 애플리케이션에서 처리.

그룹 스코프(그룹관리자)와 목록 필터의 group_code 가 둘 다 있고 서로 다르면, SQL 시절
`WHERE group_code=A AND group_code=B` 와 동일하게 **항상 빈 결과**를 반환한다.
"""
from __future__ import annotations

from datetime import date

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from ..models import Quote


def list_quotes(
    client: firestore.Client,
    *,
    scope_group: str | None,
    group_code: str | None = None,
    status: str | None = None,
    mgmt_no: str | None = None,
    title: str | None = None,
    issuer_name: str | None = None,
    issue_date_from: date | None = None,
    issue_date_to: date | None = None,
) -> list[Quote]:
    if scope_group is not None:
        if group_code is not None and group_code != scope_group:
            return []
        effective_group = scope_group
    else:
        effective_group = group_code

    q = client.collection("quotes").where(filter=FieldFilter("active", "==", True))
    if effective_group:
        q = q.where(filter=FieldFilter("group_code", "==", effective_group))
    if status:
        q = q.where(filter=FieldFilter("status", "==", status))
    q = q.order_by("created_at", direction=firestore.Query.DESCENDING)

    quotes = [Quote.from_doc(doc.id, doc.to_dict()) for doc in q.stream()]

    if mgmt_no:
        quotes = [x for x in quotes if mgmt_no in x.mgmt_no]
    if title:
        quotes = [x for x in quotes if title in x.title]
    if issuer_name:
        quotes = [x for x in quotes if issuer_name in x.issuer_name]
    if issue_date_from:
        quotes = [x for x in quotes if x.issue_date >= issue_date_from]
    if issue_date_to:
        quotes = [x for x in quotes if x.issue_date <= issue_date_to]
    return quotes
