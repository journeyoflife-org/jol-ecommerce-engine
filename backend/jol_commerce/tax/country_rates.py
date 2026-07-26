"""EU country VAT rates with effective-date annotations.

All rates verified as of July 2026. Uses Decimal for precision in
financial calculations — never float.

Sources:
- AWS EMEA VAT Tables: https://aws.amazon.com/tax-help/emea-vat-tables/
- EY Baltic Tax Card 2025: https://www.ey.com/content/dam/ey-unified-site/ey-com/en-lt/generic/documents/ey-baltic-tax-card-2025.pdf
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class VatRate:
    """VAT rate with effective date for historical accuracy."""

    rate: Decimal
    effective_from: date
    country_code: str
    country_name: str
    source: str = ""


# ── Baltic States (primary JOL markets) ─────────────────────
# Lithuania: 21% — current rate, stable
# Latvia: 21% — current rate, stable
# Estonia: 24% — raised from 22% on 1 July 2025

BALTIC_RATES: dict[str, list[VatRate]] = {
    "LT": [
        VatRate(
            rate=Decimal("0.21"),
            effective_from=date(2011, 7, 1),
            country_code="LT",
            country_name="Lithuania",
            source="EY Baltic Tax Card 2025",
        ),
    ],
    "LV": [
        VatRate(
            rate=Decimal("0.21"),
            effective_from=date(2013, 1, 1),
            country_code="LV",
            country_name="Latvia",
            source="EY Baltic Tax Card 2025",
        ),
    ],
    "EE": [
        VatRate(
            rate=Decimal("0.24"),
            effective_from=date(2025, 7, 1),
            country_code="EE",
            country_name="Estonia",
            source="AWS EMEA VAT Tables (confirmed July 2026)",
        ),
        VatRate(
            rate=Decimal("0.22"),
            effective_from=date(2024, 1, 1),
            country_code="EE",
            country_name="Estonia",
            source="AWS EMEA VAT Tables (historical — superseded 2025-07-01)",
        ),
    ],
}

# ── Full EU-27 VAT Rates (standard rates, verified July 2026) ──
EU_27_RATES: dict[str, list[VatRate]] = {
    **BALTIC_RATES,
    "AT": [VatRate(Decimal("0.20"), date(2011, 1, 1), "AT", "Austria")],
    "BE": [VatRate(Decimal("0.21"), date(2010, 1, 1), "BE", "Belgium")],
    "BG": [VatRate(Decimal("0.20"), date(2007, 1, 1), "BG", "Bulgaria")],
    "HR": [VatRate(Decimal("0.25"), date(2013, 7, 1), "HR", "Croatia")],
    "CY": [VatRate(Decimal("0.19"), date(2014, 1, 1), "CY", "Cyprus")],
    "CZ": [VatRate(Decimal("0.21"), date(2013, 1, 1), "CZ", "Czech Republic")],
    "DK": [VatRate(Decimal("0.25"), date(1992, 1, 1), "DK", "Denmark")],
    "FI": [VatRate(Decimal("0.255"), date(2024, 9, 1), "FI", "Finland")],
    "FR": [VatRate(Decimal("0.20"), date(2014, 1, 1), "FR", "France")],
    "DE": [VatRate(Decimal("0.19"), date(2021, 1, 1), "DE", "Germany")],
    "GR": [VatRate(Decimal("0.24"), date(2016, 6, 1), "GR", "Greece")],
    "HU": [VatRate(Decimal("0.27"), date(2012, 1, 1), "HU", "Hungary")],
    "IE": [VatRate(Decimal("0.23"), date(2021, 3, 1), "IE", "Ireland")],
    "IT": [VatRate(Decimal("0.22"), date(2013, 10, 1), "IT", "Italy")],
    "LU": [VatRate(Decimal("0.17"), date(2015, 1, 1), "LU", "Luxembourg")],
    "MT": [VatRate(Decimal("0.18"), date(2010, 1, 1), "MT", "Malta")],
    "NL": [VatRate(Decimal("0.21"), date(2012, 10, 1), "NL", "Netherlands")],
    "PL": [VatRate(Decimal("0.23"), date(2011, 1, 1), "PL", "Poland")],
    "PT": [VatRate(Decimal("0.23"), date(2011, 1, 1), "PT", "Portugal")],
    "RO": [VatRate(Decimal("0.19"), date(2017, 1, 1), "RO", "Romania")],
    "SK": [VatRate(Decimal("0.20"), date(2011, 1, 1), "SK", "Slovakia")],
    "SI": [VatRate(Decimal("0.22"), date(2013, 7, 1), "SI", "Slovenia")],
    "ES": [VatRate(Decimal("0.21"), date(2012, 9, 1), "ES", "Spain")],
    "SE": [VatRate(Decimal("0.25"), date(1992, 1, 1), "SE", "Sweden")],
}


def get_vat_rate(country_code: str, transaction_date: date | None = None) -> Decimal:
    """Get the applicable VAT rate for a country on a given date.

    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., 'LT', 'EE').
        transaction_date: Date of the transaction. Defaults to today.

    Returns:
        VAT rate as a Decimal (e.g., Decimal('0.21') for 21%).

    Raises:
        ValueError: If the country code is not in the EU-27 rate table.
    """
    country_code = country_code.upper()
    if country_code not in EU_27_RATES:
        raise ValueError(
            f"Unknown EU country code: {country_code}. Supported: {sorted(EU_27_RATES.keys())}",
        )

    rates = EU_27_RATES[country_code]
    if transaction_date is None:
        transaction_date = date.today()

    # Find the rate effective on or before the transaction date
    # Rates are ordered newest-first
    for vat_rate in rates:
        if transaction_date >= vat_rate.effective_from:
            return vat_rate.rate

    # If no rate matches, use the oldest rate
    return rates[-1].rate
