"""Latvia VAT tests — LV 21%."""

from datetime import date
from decimal import Decimal

from jol_commerce.tax.country_rates import get_vat_rate
from jol_commerce.tax.vat_calculator import VatCalculator


class TestVatLV:
    """Latvia VAT calculation tests."""

    def test_lv_vat_rate_is_21_percent(self) -> None:
        rate = get_vat_rate("LV")
        assert rate == Decimal("0.21")

    def test_lv_vat_rate_case_insensitive(self) -> None:
        assert get_vat_rate("lv") == Decimal("0.21")
        assert get_vat_rate("Lv") == Decimal("0.21")

    def test_lv_vat_calculation_from_net_100(self) -> None:
        result = VatCalculator.calculate_from_net(
            Decimal("100.00"),
            "LV",
            date(2025, 7, 1),
        )
        assert result.vat_amount == Decimal("21.00")
        assert result.gross_amount == Decimal("121.00")
        assert result.vat_rate == Decimal("0.21")

    def test_lv_vat_calculation_from_net_200(self) -> None:
        result = VatCalculator.calculate_from_net(
            Decimal("200.00"),
            "LV",
            date(2025, 7, 1),
        )
        assert result.vat_amount == Decimal("42.00")
        assert result.gross_amount == Decimal("242.00")

    def test_lv_vat_calculation_from_gross(self) -> None:
        result = VatCalculator.calculate_from_gross(
            Decimal("121.00"),
            "LV",
            date(2025, 7, 1),
        )
        assert result.net_amount == Decimal("100.00")
        assert result.vat_amount == Decimal("21.00")
