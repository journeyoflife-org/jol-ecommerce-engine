"""Lithuania VAT tests — LT 21%."""

from datetime import date
from decimal import Decimal

from jol_commerce.tax.country_rates import get_vat_rate
from jol_commerce.tax.vat_calculator import VatCalculator


class TestVatLT:
    """Lithuania VAT calculation tests."""

    def test_lt_vat_rate_is_21_percent(self) -> None:
        rate = get_vat_rate("LT")
        assert rate == Decimal("0.21")

    def test_lt_vat_rate_case_insensitive(self) -> None:
        assert get_vat_rate("lt") == Decimal("0.21")
        assert get_vat_rate("Lt") == Decimal("0.21")

    def test_lt_vat_calculation_from_net_100(self) -> None:
        result = VatCalculator.calculate_from_net(
            Decimal("100.00"),
            "LT",
            date(2025, 7, 1),
        )
        assert result.vat_amount == Decimal("21.00")
        assert result.gross_amount == Decimal("121.00")
        assert result.vat_rate == Decimal("0.21")

    def test_lt_vat_calculation_from_net_49_99(self) -> None:
        result = VatCalculator.calculate_from_net(
            Decimal("49.99"),
            "LT",
            date(2025, 7, 1),
        )
        assert result.vat_amount == Decimal("10.50")
        assert result.gross_amount == Decimal("60.49")

    def test_lt_vat_calculation_from_gross(self) -> None:
        result = VatCalculator.calculate_from_gross(
            Decimal("121.00"),
            "LT",
            date(2025, 7, 1),
        )
        assert result.net_amount == Decimal("100.00")
        assert result.vat_amount == Decimal("21.00")
