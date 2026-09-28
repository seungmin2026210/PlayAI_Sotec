"""팀원 명단 — specs/ASSET-1 D10, D40, P2, P3, tech/01-data-model.md § 8-7.

이름·그룹을 바꾸면 그 사람이 **지금 쓰는** 자산의 `current_member_name`·`scope_group_code` 를
같은 트랜잭션에서 갱신한다. 과거 이력(`asset_assignments.member_name`)은 스냅샷이라 그대로.
"""
from __future__ import annotations

from datetime import datetime, timezone

from google.cloud.firestore_v1.base_query import FieldFilter

from ..database import run_transaction
from ..errors import NOT_FOUND, AppError
from ..models import Member


def update_member(client, employee_no: str, changes: dict) -> tuple[Member, int]:
    """반환: (갱신된 팀원, 그 사람이 지금 사용 중인 자산 수) — 퇴사 처리 경고(P2)용."""
    now = datetime.now(timezone.utc)

    def _txn(txn):
        ref = client.collection("members").document(employee_no)
        snap = ref.get(transaction=txn)
        if not snap.exists:
            raise AppError(NOT_FOUND, 404, "팀원을 찾을 수 없습니다.")
        member = Member.from_doc(snap.to_dict())
        q = client.collection("assets").where(filter=FieldFilter("current_member_id", "==", employee_no))
        in_use = [d.reference for d in q.stream(transaction=txn)]

        asset_upd = {}
        if "name" in changes and changes["name"] != member.name:
            asset_upd["current_member_name"] = changes["name"]
        if "group_code" in changes and changes["group_code"] != member.group_code:
            asset_upd["scope_group_code"] = changes["group_code"]  # P3

        for k, v in changes.items():
            setattr(member, k, v)
        member.updated_at = now
        txn.update(ref, {**changes, "updated_at": now})
        if asset_upd:
            for a_ref in in_use:
                txn.update(a_ref, asset_upd)
        return member, len(in_use)

    return run_transaction(client, _txn)
