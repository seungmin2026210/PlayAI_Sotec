"""팀원 명단 API — specs/ASSET-1 D10, D25, D37, D46, P2."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from google.api_core.exceptions import Conflict
from google.cloud import firestore

from ..auth import CurrentUser
from ..config import ASSET_CATEGORIES
from ..deps import assert_can_view_member, get_current_user, get_db, require_super_admin, scope_group
from ..errors import MEMBER_EXISTS, NOT_FOUND, AppError, validation
from ..models import Member
from ..presenter import to_assignment_read, to_member_read
from ..schemas import MemberCreate, MemberDetail, MemberHistoryRow, MemberListResponse, MemberPatch, MemberRead
from ..services.asset_query import list_members, member_assignments
from ..services.members import update_member

router = APIRouter(prefix="/api/members", tags=["members"])


@router.get("", response_model=MemberListResponse)
def list_(
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> MemberListResponse:
    return MemberListResponse(items=[to_member_read(m, c) for m, c in list_members(client, scope_group(user))])


@router.post("", response_model=MemberRead, status_code=201)
def create(
    body: MemberCreate,
    client: firestore.Client = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> MemberRead:
    now = datetime.now(timezone.utc)
    member = Member(employee_no=body.employee_no, name=body.name, group_code=body.group_code,
                    active=True, created_at=now, updated_at=now)
    try:
        # create() 는 이미 있으면 실패 — 사번 = 문서 ID 유일(P5)
        client.collection("members").document(body.employee_no).create(member.to_dict())
    except Conflict:
        raise AppError(MEMBER_EXISTS, 409, f"이미 등록된 사번입니다({body.employee_no}).")
    return to_member_read(member, dict.fromkeys(ASSET_CATEGORIES, 0))


@router.get("/{employee_no}", response_model=MemberDetail)
def detail(
    employee_no: str,
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> MemberDetail:
    snap = client.collection("members").document(employee_no).get()
    if not snap.exists:
        raise AppError(NOT_FOUND, 404, "팀원을 찾을 수 없습니다.")
    member = Member.from_doc(snap.to_dict())
    assert_can_view_member(member, user)
    rows = member_assignments(client, employee_no, scope_group(user))
    counts = dict.fromkeys(ASSET_CATEGORIES, 0)
    for a, _ in rows:
        if a.end_date is None:
            counts[a.category] = counts.get(a.category, 0) + 1
    return MemberDetail(
        **to_member_read(member, counts).model_dump(),
        assignments=[MemberHistoryRow(**to_assignment_read(a).model_dump(), linkable=ok) for a, ok in rows],
    )


@router.patch("/{employee_no}", response_model=MemberRead)
def patch(
    employee_no: str,
    body: MemberPatch,
    client: firestore.Client = Depends(get_db),
    _: CurrentUser = Depends(require_super_admin),
) -> MemberRead:
    changes = {k: (v.strip() if isinstance(v, str) else v) for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if changes.get("name") == "":
        raise validation("이름을 입력해야 합니다.")
    member, in_use = update_member(client, employee_no, changes)
    warning = None
    if changes.get("active") is False and in_use:
        # P2: 경고만, 자동 회수 안 함
        warning = f"퇴사 처리했습니다. 이 팀원이 아직 사용 중인 자산이 {in_use}건 있습니다 — 회수 또는 사용자 변경이 필요합니다."
    return to_member_read(member, dict.fromkeys(ASSET_CATEGORIES, 0), warning)
