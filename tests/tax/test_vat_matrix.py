"""Full 27-country EU VAT matrix tests.

Validates VAT rates for all 27 EU member states.
Required before production goes live.
"""

from datetime import date
from decimal import Decimal

import pytest
from jol_commerce.tax.country_rates import EU_27_RATES, get_vat_rate

# Expected standard VAT rates for all 27 EU member states (verified July 2026)
EXPECTED_EU_27_RATES: dict[str, Decimal] = {
    "AT": Decimal("0.20"),
    "BE": Decimal("0.21"),
    "BG": Decimal("0.20"),
    "HR": Decimal("0.25"),
    "CY": Decimal("0.19"),
    "CZ": Decimal("0.21"),
    "DK": Decimal("0.25"),
    "EE": Decimal("0.24"),  # Changed from 22% to 24% on 2025-07-01
    "FI": Decimal("0.255"),
    "FR": Decimal("0.20"),
    "DE": Decimal("0.19"),
    "GR": Decimal("0.24"),
    "HU": Decimal("0.27"),
    "IE": Decimal("0.23"),
    "IT": Decimal("0.22"),
    "LV": Decimal("0.21"),
    "LT": Decimal("0.21"),
    "LU": Decimal("0.17"),
    "MT": Decimal("0.18"),
    "NL": Decimal("0.21"),
    "PL": Decimal("0.23"),
    "PT": Decimal("0.23"),
    "RO": Decimal("0.19"),
    "SK": Decimal("0.20"),
    "SI": Decimal("0.22"),
    "ES": Decimal("0.21"),
    "SE": Decimal("0.25"),
}


class TestVatMatrix:
    """Full 27-country EU VAT rate matrix."""

    def test_all_27_countries_present(self) -> None:
        """Verify all 27 EU member states are in the rate table."""
        assert len(EU_27_RATES) == 27

    @pytest.mark.parametrize(
        "country_code,expected_rate",
        list(EXPECTED_EU_27_RATES.items()),
        ids=list(EXPECTED_EU_27_RATES.keys()),
    )
    def test_vat_rate(self, country_code: str, expected_rate: Decimal) -> None:
        """Verify current VAT rate for each EU country."""
        actual = get_vat_rate(country_code, date(2026, 7, 1))
        assert actual == expected_rate, f"{country_code}: expected {expected_rate}, got {actual}"

    def test_baltic_rates_consistency(self) -> None:
        """LT and LV at 21%, EE at 24% (from 2025-07-01)."""
        assert get_vat_rate("LT", date(2026, 1, 1)) == Decimal("0.21")
        assert get_vat_rate("LV", date(2026, 1, 1)) == Decimal("0.21")
        assert get_vat_rate("EE", date(2026, 1, 1)) == Decimal("0.24")

    def test_unknown_country_raises_error(self) -> None:
        """Non-EU country codes should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown EU country code"):
            get_vat_rate("US")

    def test_highest_rate_is_hungary(self) -> None:
        """Hungary has the highest standard VAT rate at 27%."""
        highest = max(get_vat_rate(cc, date(2026, 7, 1)) for cc in EU_27_RATES)
        assert highest == Decimal("0.27")

    def test_lowest_rate_is_luxembourg(self) -> None:
        """Luxembourg has the lowest standard VAT rate at 17%."""
        lowest = min(get_vat_rate(cc, date(2026, 7, 1)) for cc in EU_27_RATES)
        assert lowest == Decimal("0.17")
