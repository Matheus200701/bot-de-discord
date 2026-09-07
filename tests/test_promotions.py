from packages.promotions.service import _money_bps


def test_percent_discount_uses_basis_points_and_rounds_down() -> None:
    assert _money_bps(999, 1500) == 149
    assert _money_bps(10000, 10000) == 10000


def test_cashback_is_integer_minor_units() -> None:
    assert (1999 * 500) // 10000 == 99


def test_zero_discount_is_zero() -> None:
    assert _money_bps(12345, 0) == 0
