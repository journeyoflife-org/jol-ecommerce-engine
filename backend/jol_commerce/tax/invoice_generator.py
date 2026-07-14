"""Invoice generator — creates compliant invoices with VAT breakdown.

Invoices include all required fields for EU VAT compliance:
- Seller and buyer identification
- VAT rate and amount per line item
- Invoice date and unique number
- Currency and total amounts
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

from jol_commerce.tax.vat_calculator import VatCalculation, VatCalculator


@dataclass
class InvoiceLineItem:
    """A single line item on an invoice."""

    description: str
    quantity: int
    unit_price_net: Decimal
    country_code: str
    transaction_date: date = field(default_factory=date.today)

    @property
    def vat_calculation(self) -> VatCalculation:
        """Calculate VAT for this line item."""
        total_net = self.unit_price_net * self.quantity
        return VatCalculator.calculate_from_net(
            total_net,
            self.country_code,
            self.transaction_date,
        )


@dataclass
class Invoice:
    """Generated invoice with VAT breakdown."""

    invoice_number: str
    invoice_date: date
    seller_name: str
    seller_vat_number: str
    buyer_name: str
    buyer_country: str
    line_items: list[InvoiceLineItem]
    currency: str = "EUR"

    @property
    def total_net(self) -> Decimal:
        """Sum of all line item net amounts."""
        return sum((item.vat_calculation.net_amount for item in self.line_items), Decimal(0))

    @property
    def total_vat(self) -> Decimal:
        """Sum of all line item VAT amounts."""
        return sum((item.vat_calculation.vat_amount for item in self.line_items), Decimal(0))

    @property
    def total_gross(self) -> Decimal:
        """Sum of all line item gross amounts."""
        return self.total_net + self.total_vat

    def to_dict(self) -> dict[str, object]:
        """Serialize invoice to dictionary."""
        return {
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date.isoformat(),
            "seller": {
                "name": self.seller_name,
                "vat_number": self.seller_vat_number,
            },
            "buyer": {
                "name": self.buyer_name,
                "country": self.buyer_country,
            },
            "line_items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price_net": str(item.unit_price_net),
                    "net_total": str(item.vat_calculation.net_amount),
                    "vat_amount": str(item.vat_calculation.vat_amount),
                    "vat_rate": str(item.vat_calculation.vat_rate),
                    "gross_total": str(item.vat_calculation.gross_amount),
                }
                for item in self.line_items
            ],
            "totals": {
                "net": str(self.total_net),
                "vat": str(self.total_vat),
                "gross": str(self.total_gross),
                "currency": self.currency,
            },
            "generated_at": datetime.now(UTC).isoformat(),
        }


class InvoiceGenerator:
    """Generates compliant invoices with automatic VAT calculation."""

    _counter: int = 0

    @classmethod
    def generate(
        cls,
        seller_name: str,
        seller_vat_number: str,
        buyer_name: str,
        buyer_country: str,
        line_items: list[InvoiceLineItem],
        *,
        currency: str = "EUR",
    ) -> Invoice:
        """Generate an invoice with auto-incrementing number.

        Args:
            seller_name: Seller business name.
            seller_vat_number: Seller VAT registration number.
            buyer_name: Buyer name.
            buyer_country: Buyer country code.
            line_items: List of invoice line items.
            currency: Currency code (default EUR).

        Returns:
            Generated Invoice object.
        """
        cls._counter += 1
        invoice_number = f"JOL-{date.today().strftime('%Y%m')}-{cls._counter:06d}"

        return Invoice(
            invoice_number=invoice_number,
            invoice_date=date.today(),
            seller_name=seller_name,
            seller_vat_number=seller_vat_number,
            buyer_name=buyer_name,
            buyer_country=buyer_country,
            line_items=line_items,
            currency=currency,
        )
