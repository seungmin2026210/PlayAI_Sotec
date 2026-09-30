"""배정 · 회수 · 이관 · 이력 수정 · 배정 취소 트랜잭션 — specs/ASSET-1 tech/01-data-model.md § 8-3~8-6, 8-8.

모두 `database.run_transaction` 안에서 read 를 전부 끝낸 뒤 write 한다(Firestore 제약).
날짜 규칙은 `asset_dates.validate_period`(D36) 하나를 공유한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from ..auth import CurrentUser
from ..config import ASSET_STATUS_IDLE, ASSET_STATUS_IN_USE
from ..database import run_transaction
from ..errors import MEMBER_INACTIVE, NOT_FOUND, AppError, validation
from ..models import Asset, AssetAssignment, Member
from .asset_dates import validate_period
from .asset_status import guard_idle, guard_in_use, guard_not_disposed


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- 트랜잭션 read 헬퍼
def load_asset_in(txn, client: firestore.Client, asset_no: str) -> tuple[firestore.DocumentReference, Asset]:
    ref = client.collection("assets").document(asset_no)
    snap = ref.get(transaction=txn)
    if not snap.exists:
        raise AppError(NOT_FOUND, 404, "자산을 찾을 수 없습니다.")
    return ref, Asset.from_doc(snap.to_dict())


def _load_assignment_in(txn, client, assignment_id: str) -> tuple[firestore.DocumentReference, AssetAssignment]:
    ref = client.collection("asset_assignments").document(assignment_id)
    snap = ref.get(transaction=txn)
    if not snap.exists:
        raise AppError(NOT_FOUND, 404, "사용 이력을 찾을 수 없습니다.")
    return ref, AssetAssignment.from_doc(snap.id, snap.to_dict())


def _periods_in(txn, client, asset_no: str, *exclude_ids: str) -> list[tuple[str, str | None]]:
    q = client.collection("asset_assignments").where(filter=FieldFilter("asset_no", "==", asset_no))
    return [
        (d.get("start_date"), d.get("end_date"))
        for d in q.stream(transaction=txn)
        if d.id not in exclude_ids
    ]


@dataclass(frozen=True)
class _Target:
    member_id: str | None
    member_name: str | None
    shared_label: str | None
    external_label: str | None
    scope_group_code: str


def _resolve_target_in(
    txn, client, asset: Asset, member_id: str | None, shared_label: str | None, external_label: str | None = None
) -> _Target:
    """배정 대상 = 팀원 · 공용(D33) · 타업체 제공(D33-1) 중 정확히 하나.
    교육 자산은 내부용이라 공용·타업체 제공 둘 다 불가 — 팀원에게만 배정."""
    shared_label = (shared_label or "").strip() or None
    external_label = (external_label or "").strip() or None
    member_id = (member_id or "").strip() or None
    if sum(bool(x) for x in (member_id, shared_label, external_label)) != 1:
        raise validation("팀원 · 공용(장소/용도) · 타업체 제공 중 하나만 지정해야 합니다.")
    if shared_label:
        if asset.category == "EDU":
            raise validation("교육 자산은 공용으로 배정할 수 없습니다.")
        return _Target(None, None, shared_label, None, asset.group_code)
    if external_label:
        if asset.category == "EDU":
            raise validation("교육 자산은 내부용이라 타업체에 제공할 수 없습니다.")
        return _Target(None, None, None, external_label, asset.group_code)
    snap = client.collection("members").document(member_id).get(transaction=txn)
    if not snap.exists:
        raise AppError(NOT_FOUND, 404, "팀원을 찾을 수 없습니다.")
    member = Member.from_doc(snap.to_dict())
    if not member.active:
        raise AppError(MEMBER_INACTIVE, 409, f"퇴사 처리된 팀원({member.name})에게는 배정할 수 없습니다.")
    return _Target(member.employee_no, member.name, None, None, member.group_code)


def _current_fields(t: _Target, assignment_id: str, start_date: str) -> dict:
    return {
        "status": ASSET_STATUS_IN_USE,
        "current_member_id": t.member_id,
        "current_member_name": t.member_name,
        "current_shared_label": t.shared_label,
        "current_external_label": t.external_label,
        "current_assignment_id": assignment_id,
        "current_start_date": start_date,
        "scope_group_code": t.scope_group_code,
    }


def _idle_fields(asset: Asset) -> dict:
    return {
        "status": ASSET_STATUS_IDLE,
        "current_member_id": None,
        "current_member_name": None,
        "current_shared_label": None,
        "current_external_label": None,
        "current_assignment_id": None,
        "current_start_date": None,
        "scope_group_code": asset.group_code,
    }


def _new_assignment(asset: Asset, t: _Target, start: str, note: str | None, user: CurrentUser, now, prev_id=None) -> dict:
    return AssetAssignment(
        id="",
        asset_no=asset.asset_no,
        category=asset.category,
        asset_name=asset.name,
        member_id=t.member_id,
        member_name=t.member_name,
        shared_label=t.shared_label,
        external_label=t.external_label,
        start_date=start,
        end_date=None,
        prev_assignment_id=prev_id,
        note=(note or "").strip() or None,
        created_at=now,
        created_by=user.username,
        updated_at=now,
        updated_by=user.username,
    ).to_dict()


# --------------------------------------------------------------------------- § 8-3 배정
def assign(
    client, asset_no: str, *, member_id, shared_label, external_label=None, start_date: str, note, user: CurrentUser
) -> None:
    now = _now()

    def _txn(txn):
        ref, asset = load_asset_in(txn, client, asset_no)
        guard_idle(asset)
        target = _resolve_target_in(txn, client, asset, member_id, shared_label, external_label)
        validate_period(start_date, None, _periods_in(txn, client, asset_no))
        new_ref = client.collection("asset_assignments").document()
        txn.set(new_ref, _new_assignment(asset, target, start_date, note, user, now))
        txn.update(ref, {**_current_fields(target, new_ref.id, start_date), "updated_at": now, "updated_by": user.username})

    run_transaction(client, _txn)


# --------------------------------------------------------------------------- § 8-4 회수
def return_asset(client, asset_no: str, *, end_date: str, note, user: CurrentUser) -> None:
    now = _now()

    def _txn(txn):
        ref, asset = load_asset_in(txn, client, asset_no)
        guard_in_use(asset)
        cur_ref, cur = _load_assignment_in(txn, client, asset.current_assignment_id)
        validate_period(cur.start_date, end_date, _periods_in(txn, client, asset_no, cur.id))
        upd = {"end_date": end_date, "updated_at": now, "updated_by": user.username}
        if note and note.strip():
            upd["note"] = note.strip()
        txn.update(cur_ref, upd)
        txn.update(ref, {**_idle_fields(asset), "updated_at": now, "updated_by": user.username})

    run_transaction(client, _txn)


# --------------------------------------------------------------------------- § 8-5 사용자 변경(이관)
def transfer(
    client, asset_no: str, *, member_id, shared_label, external_label=None, date: str, note, user: CurrentUser
) -> None:
    now = _now()

    def _txn(txn):
        ref, asset = load_asset_in(txn, client, asset_no)
        guard_in_use(asset)
        cur_ref, cur = _load_assignment_in(txn, client, asset.current_assignment_id)
        target = _resolve_target_in(txn, client, asset, member_id, shared_label, external_label)
        if (target.member_id, target.shared_label, target.external_label) == (
            cur.member_id, cur.shared_label, cur.external_label,
        ):
            raise validation("현재 사용자와 같은 대상으로는 변경할 수 없습니다.")
        if date < cur.start_date:
            raise validation(f"변경일은 현재 사용 시작일({cur.start_date}) 이후여야 합니다.")
        others = _periods_in(txn, client, asset_no, cur.id)
        validate_period(cur.start_date, date, others)
        validate_period(date, None, others)

        txn.update(cur_ref, {"end_date": date, "updated_at": now, "updated_by": user.username})
        new_ref = client.collection("asset_assignments").document()
        txn.set(new_ref, _new_assignment(asset, target, date, note, user, now, prev_id=cur.id))
        txn.update(ref, {**_current_fields(target, new_ref.id, date), "updated_at": now, "updated_by": user.username})

    run_transaction(client, _txn)


# --------------------------------------------------------------------------- § 8-6 이력 수정(D20)
_UNSET = object()


def edit_assignment(client, assignment_id: str, *, start_date=None, end_date=None, note=_UNSET, user: CurrentUser) -> str:
    """날짜·비고만(사람 변경 불가). 반환: asset_no."""
    now = _now()

    def _txn(txn):
        a_ref, a = _load_assignment_in(txn, client, assignment_id)
        asset_ref, asset = load_asset_in(txn, client, a.asset_no)
        guard_not_disposed(asset)
        if a.end_date is None and end_date is not None:
            raise validation("사용 중인 이력의 종료일은 [회수] 또는 [사용자 변경]으로만 입력할 수 있습니다.")
        new_start = start_date or a.start_date
        new_end = end_date or a.end_date
        validate_period(new_start, new_end, _periods_in(txn, client, a.asset_no, a.id))

        upd = {"start_date": new_start, "end_date": new_end, "updated_at": now, "updated_by": user.username}
        if note is not _UNSET:
            upd["note"] = (note or "").strip() or None
        txn.update(a_ref, upd)
        if a.end_date is None and asset.current_assignment_id == a.id:
            txn.update(asset_ref, {"current_start_date": new_start})
        return a.asset_no

    return run_transaction(client, _txn)


# --------------------------------------------------------------------------- § 8-8 배정 취소(D34)
def cancel_assignment(client, asset_no: str, *, user: CurrentUser) -> None:
    now = _now()

    def _txn(txn):
        ref, asset = load_asset_in(txn, client, asset_no)
        guard_in_use(asset)
        cur_ref, cur = _load_assignment_in(txn, client, asset.current_assignment_id)
        if cur.prev_assignment_id is None:
            txn.delete(cur_ref)
            txn.update(ref, {**_idle_fields(asset), "updated_at": now, "updated_by": user.username})
            return

        prev_ref, prev = _load_assignment_in(txn, client, cur.prev_assignment_id)
        scope = asset.group_code
        name = prev.member_name
        if prev.member_id:
            m = client.collection("members").document(prev.member_id).get(transaction=txn)
            if m.exists:  # 복구는 "지금" 소속 그룹·이름 기준(D24, D40)
                scope, name = m.get("group_code"), m.get("name")
        target = _Target(prev.member_id, name, prev.shared_label, prev.external_label, scope)
        txn.delete(cur_ref)
        txn.update(prev_ref, {"end_date": None, "updated_at": now, "updated_by": user.username})
        txn.update(ref, {**_current_fields(target, prev.id, prev.start_date), "updated_at": now, "updated_by": user.username})

    run_transaction(client, _txn)
