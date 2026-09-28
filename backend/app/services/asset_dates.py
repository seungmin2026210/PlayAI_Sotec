"""자산관리 날짜 기준 + 날짜 규칙 — specs/ASSET-1 D36, D45.

"오늘"·"올해"는 전부 KST. `today_kst()` 가 유일한 계산처다(채번 연도·만료 배지·기본 날짜·
미래 날짜 검사). 서버(Vercel)는 UTC 라 `date.today()` 를 쓰면 1/1 09시 전에 전년도가 된다.

날짜는 `YYYY-MM-DD` 문자열로 다룬다(ISO 사전순 = 날짜순).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Iterable

from ..config import ASSET_TZ_OFFSET_HOURS
from ..errors import validation

KST = timezone(timedelta(hours=ASSET_TZ_OFFSET_HOURS))
_OPEN_END = "9999-12-31"  # 종료일 없음(사용 중) = 무한대


def today_kst(now: datetime | None = None) -> date:
    """`now` 는 테스트용(UTC aware datetime). 기본은 현재 시각."""
    return (now or datetime.now(timezone.utc)).astimezone(KST).date()


def validate_period(
    start: str,
    end: str | None,
    others: Iterable[tuple[str, str | None]],
    *,
    today: date | None = None,
) -> None:
    """배정·회수·이관·이력수정 공통 날짜 규칙(D36). 위반 시 400 VALIDATION_ERROR.

    - 미래 날짜 불가(오늘 = KST)
    - 종료일 ≥ 시작일
    - 같은 자산의 다른 이력(`others`: (start, end|None))과 기간 겹침 불가.
      경계가 맞닿는 것(앞 이력 종료일 == 새 이력 시작일)은 허용 — 이관은 같은 날 인계다.
    """
    today_s = (today or today_kst()).isoformat()
    if start > today_s or (end is not None and end > today_s):
        raise validation("미래 날짜는 입력할 수 없습니다(오늘까지만 가능).")
    if end is not None and end < start:
        raise validation("종료일은 시작일보다 앞설 수 없습니다.")
    my_end = end or _OPEN_END
    for o_start, o_end in others:
        if start < (o_end or _OPEN_END) and o_start < my_end:
            raise validation(
                f"같은 자산의 다른 사용 이력({o_start} ~ {o_end or '사용 중'})과 기간이 겹칩니다."
            )


def next_day(d: str) -> str:
    return (date.fromisoformat(d) + timedelta(days=1)).isoformat()
