"""대시보드 갱신 위젯 API — specs/ASSET-1 D28, D29, D39. 그룹관리자는 자기 그룹 스코프만."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from google.cloud import firestore

from ..auth import CurrentUser
from ..deps import get_current_user, get_db, scope_group
from ..schemas import RenewalCalendarResponse, RenewalGroup, RenewalKpi
from ..services.asset_query import renewal_calendar

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/renewals", response_model=RenewalCalendarResponse)
def renewals(
    date_from: date = Query(alias="from"),
    date_to: date = Query(alias="to"),
    client: firestore.Client = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> RenewalCalendarResponse:
    items, kpi = renewal_calendar(
        client, scope_group=scope_group(user), date_from=date_from.isoformat(), date_to=date_to.isoformat()
    )
    return RenewalCalendarResponse(items=[RenewalGroup(**i) for i in items], kpi=RenewalKpi(**kpi))
