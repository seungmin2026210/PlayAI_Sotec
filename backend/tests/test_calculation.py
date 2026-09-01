from app.services.calculation import (
    Computed,
    compute,
    format_won,
    items_raw_total,
    truncate_supply,
    vat_of,
)


class _I:
    def __init__(self, qty, unit_price):
        self.qty = qty
        self.unit_price = unit_price


def test_items_raw_total():
    assert items_raw_total([_I(2, 1_000_000), _I(1, 345_678)]) == 2_345_678


def test_truncate_supply_rounds_down_to_100k():
    assert truncate_supply(12_345_678) == 12_300_000
    assert truncate_supply(999_999) == 900_000
    assert truncate_supply(50_000) == 0
    assert truncate_supply(0) == 0


def test_vat_is_ten_percent_of_truncated_supply():
    assert vat_of(12_300_000) == 1_230_000
    assert vat_of(900_000) == 90_000


def test_compute_end_to_end():
    c = compute([_I(1, 12_345_678)])
    assert c == Computed(
        raw_total=12_345_678,
        supply_amount=12_300_000,
        vat_amount=1_230_000,
        total_with_vat=13_530_000,
    )


def test_format_won():
    assert format_won(13_530_000) == "13,530,000원"
    assert format_won(0) == "0원"
