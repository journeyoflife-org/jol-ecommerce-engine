"""Estonia VAT tests — EE 24% (from 2025-07-01), 22% (before 2025-07-01).

Estonia raised its standard VAT rate from 22% to 24% on 1 July 2025.
Source: https://aws.amazon.com/tax-help/emea-vat-tables/
"""

from datetime import date
from decimal import Decimal

from jol_commerce.tax.country_rates import get_vat_rate
from jol_commerce.tax.vat_calculator import VatCalculator


class TestVatEE:
    """Estonia VAT calculation tests — verifies rate change on 2025-07-01."""

    def test_ee_vat_rate_is_24_percent_from_2025_07_01(self) -> None:
        """Estonia VAT is 24% from 1 July 2025 onwards."""
        rate = get_vat_rate("EE", date(2025, 7, 1))
        assert rate == Decimal("0.24")

    def test_ee_vat_rate_is_24_percent_current(self) -> None:
        """Estonia VAT is 24% for current transactions."""
        rate = get_vat_rate("EE", date(2026, 1, 15))
        assert rate == Decimal("0.24")

    def test_ee_vat_rate_was_22_percent_before_2025_07_01(self) -> None:
        """Estonia VAT was 22% before 1 July 2025."""
        rate = get_vat_rate("EE", date(2025, 6, 30))
        assert rate == Decimal("0.22")

    def test_ee_vat_rate_was_22_percent_in_2024(self) -> None:
        """Estonia VAT was 22% throughout 2024."""
        rate = get_vat_rate("EE", date(2024, 6, 15))
        assert rate == Decimal("0.22")

    def test_ee_vat_calculation_24_percent_from_net_100(self) -> None:
        """100 EUR net at 24% VAT (from 2025-07-01)."""
        result = VatCalculator.calculate_from_net(
            Decimal("100.00"),
            "EE",
            date(2025, 7, 1),
        )
        assert result.vat_rate == Decimal("0.24")
        assert result.vat_amount == Decimal("24.00")
        assert result.gross_amount == Decimal("124.00")

    def test_ee_vat_calculation_22_percent_from_net_100(self) -> None:
        """100 EUR net at 22% VAT (before 2025-07-01)."""
        result = VatCalculator.calculate_from_net(
            Decimal("100.00"),
            "EE",
            date(2025, 6, 30),
        )
        assert result.vat_rate == Decimal("0.22")
        assert result.vat_amount == Decimal("22.00")
        assert result.gross_amount == Decimal("122.00")

    def test_ee_vat_calculation_from_gross_24_percent(self) -> None:
        """124 EUR gross at 24% VAT."""
        result = VatCalculator.calculate_from_gross(
            Decimal("124.00"),
            "EE",
            date(2025, 7, 1),
        )
        assert result.net_amount == Decimal("100.00")
        assert result.vat_amount == Decimal("24.00")

    def test_ee_vat_calculation_from_gross_22_percent(self) -> None:
        """122 EUR gross at 22% VAT."""
        result = VatCalculator.calculate_from_gross(
            Decimal("122.00"),
            "EE",
            date(2025, 6, 30),
        )
        assert result.net_amount == Decimal("100.00")
        assert result.vat_amount == Decimal("22.00")
