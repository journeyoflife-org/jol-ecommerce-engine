"""VAT calculator — computes VAT amounts using Decimal precision.

All calculations use Python's Decimal type to avoid floating-point
rounding errors in financial computations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from jol_commerce.tax.country_rates import get_vat_rate


@dataclass(frozen=True)
class VatCalculation:
    """Result of a VAT calculation."""

    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    vat_rate: Decimal
    country_code: str
    transaction_date: date

    def to_dict(self) -> dict[str, str]:
        """Serialize to dictionary with string values."""
        return {
            "net_amount": str(self.net_amount),
            "vat_amount": str(self.vat_amount),
            "gross_amount": str(self.gross_amount),
            "vat_rate": str(self.vat_rate),
            "country_code": self.country_code,
            "transaction_date": self.transaction_date.isoformat(),
        }


class VatCalculator:
    """Calculates VAT for EU transactions.

    Uses Decimal arithmetic exclusively to prevent rounding errors.
    Supports historical rate lookups for retrospective calculations.
    """

    @staticmethod
    def calculate_from_net(
        net_amount: Decimal,
        country_code: str,
        transaction_date: date | None = None,
    ) -> VatCalculation:
        """Calculate VAT from a net (pre-tax) amount.

        Args:
            net_amount: Amount before VAT.
            country_code: ISO 3166-1 alpha-2 country code.
            transaction_date: Date of transaction. Defaults to today.

        Returns:
            VatCalculation with net, VAT, and gross amounts.
        """
        if transaction_date is None:
            transaction_date = date.today()

        vat_rate = get_vat_rate(country_code, transaction_date)
        vat_amount = (net_amount * vat_rate).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        gross_amount = net_amount + vat_amount

        return VatCalculation(
            net_amount=net_amount,
            vat_amount=vat_amount,
            gross_amount=gross_amount,
            vat_rate=vat_rate,
            country_code=country_code,
            transaction_date=transaction_date,
        )

    @staticmethod
    def calculate_from_gross(
        gross_amount: Decimal,
        country_code: str,
        transaction_date: date | None = None,
    ) -> VatCalculation:
        """Calculate VAT from a gross (tax-inclusive) amount.

        Args:
            gross_amount: Amount including VAT.
            country_code: ISO 3166-1 alpha-2 country code.
            transaction_date: Date of transaction. Defaults to today.

        Returns:
            VatCalculation with net, VAT, and gross amounts.
        """
        if transaction_date is None:
            transaction_date = date.today()

        vat_rate = get_vat_rate(country_code, transaction_date)
        net_amount = (gross_amount / (Decimal("1") + vat_rate)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        vat_amount = gross_amount - net_amount

        return VatCalculation(
            net_amount=net_amount,
            vat_amount=vat_amount,
            gross_amount=gross_amount,
            vat_rate=vat_rate,
            country_code=country_code,
            transaction_date=transaction_date,
        )
