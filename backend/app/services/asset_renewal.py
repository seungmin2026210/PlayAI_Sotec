"""갱신 = 기존 자산 유효기간 일괄 연장 — specs/ASSET-1 D32, tech/01-data-model.md § 8-10.

번호·사용자는 그대로. 갱신 구매 유닛은 선택적으로 연결(`asset_link_kind = RENEWED`).
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..auth import CurrentUser
from ..config import ASSET_BULK_MAX, ASSET_LINK_RENEWED
from ..database import run_transaction
from ..errors import NOT_FOUND, AppError, validation
from ..models import Asset
from .asset_dates import next_day
from .asset_registration import check_linkable
from .asset_status import guard_not_disposed


def renew(
    client,
    asset_nos: list[str],
    *,
    new_valid_to: str,
    new_valid_from: str | None,
    unit_no: str | None,
    user: CurrentUser,
) -> str:
    """반환: 생성된 asset_renewals 문서 ID."""
    asset_nos = sorted(set(asset_nos))
    if not asset_nos:
        raise validation("갱신할 자산을 선택하세요.")
    if len(asset_nos) > ASSET_BULK_MAX:
        raise validation(f"한 번에 {ASSET_BULK_MAX}건까지 갱신할 수 있습니다.")
    now = datetime.now(timezone.utc)

    def _txn(txn):
        refs = [client.collection("assets").document(n) for n in asset_nos]
        snaps = list(client.get_all(refs, transaction=txn))
        if len(snaps) != len(refs) or not all(s.exists for s in snaps):
            raise AppError(NOT_FOUND, 404, "자산을 찾을 수 없습니다.")
        assets = [Asset.from_doc(s.to_dict()) for s in snaps]
        for a in assets:
            guard_not_disposed(a)
        ends = {a.valid_to for a in assets}
        if None in ends:
            raise validation("유효기간 종료일이 없는 자산은 갱신할 수 없습니다.")
        if len(ends) > 1:
            raise validation("종료일이 같은 자산끼리만 한꺼번에 갱신할 수 있습니다.")
        prev_to = ends.pop()
        if new_valid_to <= prev_to:
            raise validation(f"새 종료일은 기존 종료일({prev_to})보다 뒤여야 합니다.")
        valid_from = new_valid_from or next_day(prev_to)
        if valid_from > new_valid_to:
            raise validation("새 시작일은 새 종료일보다 앞서야 합니다.")

        unit_ref = None
        if unit_no:
            unit_ref = client.collection("asset_units").document(unit_no)
            unit = check_linkable(unit_ref.get(transaction=txn))
            if unit.asset_category != assets[0].category:
                raise validation("자산과 유형이 다른 구매 기록은 연결할 수 없습니다.")

        for ref in refs:
            txn.update(ref, {
                "valid_from": valid_from, "valid_to": new_valid_to,
                "updated_at": now, "updated_by": user.username,
            })
        ren_ref = client.collection("asset_renewals").document()
        txn.set(ren_ref, {
            "asset_nos": asset_nos,
            "name": assets[0].name,
            "prev_valid_to": prev_to,
            "new_valid_from": valid_from,
            "new_valid_to": new_valid_to,
            "unit_no": unit_no or None,
            "created_at": now,
            "created_by": user.username,
        })
        if unit_ref is not None:
            txn.update(unit_ref, {"asset_link_kind": ASSET_LINK_RENEWED, "asset_nos": asset_nos, "updated_at": now})
        return ren_ref.id

    return run_transaction(client, _txn)
