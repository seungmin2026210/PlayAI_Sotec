"""ASSET-1 순수 규칙 — DB 불필요."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.auth import CurrentUser
from app.errors import AppError
from app.presenter import mask_license_key
from app.services.asset_bulk import check_quantity, clean_fields, split_price
from app.services.asset_dates import today_kst, validate_period
from app.services.asset_no import format_asset_no
from app.services.asset_query import expiry_state

ADMIN = CurrentUser("Admin", "SUPER_ADMIN", None, "전체관리자")
MANAGER = CurrentUser("test1", "GROUP_MANAGER", "A", "그룹관리자(A)")
TODAY = date(2026, 9, 28)


def test_today_kst_crosses_new_year_before_utc():
    # UTC 12/31 15:00 = KST 1/1 00:00 (D45)
    assert today_kst(datetime(2026, 12, 31, 15, 0, tzinfo=timezone.utc)) == date(2027, 1, 1)
    assert today_kst(datetime(2026, 12, 31, 14, 59, tzinfo=timezone.utc)) == date(2026, 12, 31)


def test_format_asset_no():
    assert format_asset_no("SW", 2026, 1) == "SW-26-001"
    assert format_asset_no("EDU", 2023, 12) == "EDU-23-012"


def test_split_price_remainder_goes_to_first():
    parts = split_price(1000, 3)
    assert parts == [334, 333, 333]
    assert sum(parts) == 1000
    assert split_price(None, 2) == [None, None]


@pytest.mark.parametrize("n", [0, 101])
def test_quantity_out_of_range(n):
    with pytest.raises(AppError) as e:
        check_quantity(n)
    assert e.value.status_code == 400


def test_expiry_state():
    assert expiry_state(None, TODAY) is None
    assert expiry_state("2026-09-27", TODAY) == "expired"
    assert expiry_state("2026-09-28", TODAY) == "expiring"
    assert expiry_state("2026-10-28", TODAY) == "expiring"
    assert expiry_state("2026-10-29", TODAY) is None


def test_subcategory_validated_per_category():
    assert clean_fields("SW", {"subcategory": "AI_SUB"})["subcategory"] == "AI_SUB"
    assert clean_fields("EDU", {"subcategory": "AI_SUB"})["subcategory"] is None
    with pytest.raises(AppError):
        clean_fields("HW", {"subcategory": "AI_SUB"})


def test_clean_fields_drops_fields_of_other_category():
    out = clean_fields("HW", {"password": "x", "license_key": "k", "model": " 16Z90S "})
    assert out == {"model": "16Z90S"}


def test_validate_period_rules():
    validate_period("2026-09-01", "2026-09-10", [], today=TODAY)
    with pytest.raises(AppError):  # 미래
        validate_period("2026-09-29", None, [], today=TODAY)
    with pytest.raises(AppError):  # 종료 < 시작
        validate_period("2026-09-10", "2026-09-01", [], today=TODAY)
    with pytest.raises(AppError):  # 겹침
        validate_period("2026-09-05", None, [("2026-09-01", "2026-09-10")], today=TODAY)
    with pytest.raises(AppError):  # 사용 중 이력과 겹침
        validate_period("2026-09-05", "2026-09-06", [("2026-09-01", None)], today=TODAY)
    # 경계 맞닿음(이관 같은 날 인계)은 허용
    validate_period("2026-09-10", None, [("2026-09-01", "2026-09-10")], today=TODAY)


def test_mask_license_key():
    assert mask_license_key("ABCD-EFGH-IJKL", ADMIN) == "ABCD-EFGH-IJKL"
    assert mask_license_key("ABCD-EFGH-IJKL", MANAGER) == "ABCD-****"
    assert mask_license_key("AB", MANAGER) == "****"
    assert mask_license_key(None, MANAGER) is None
