from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import (
    COMPANY,
    GROUPS,
    STATUS_LABELS,
    TRUNCATE_UNIT,
    VAT_RATE,
)
from ..deps import get_current_user
from ..schemas import GroupOut, MetaResponse

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta", response_model=MetaResponse)
def meta(_=Depends(get_current_user)) -> MetaResponse:
    return MetaResponse(
        groups=[GroupOut(code=c, name=n) for c, n in GROUPS.items()],
        company=dict(COMPANY),
        vat_rate=VAT_RATE,
        truncate_unit=TRUNCATE_UNIT,
        statuses=[{"code": c, "label": l} for c, l in STATUS_LABELS.items()],
    )
