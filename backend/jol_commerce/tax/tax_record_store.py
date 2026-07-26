"""Tax record store — persistent storage for VAT records.

Lithuanian accounting law requires financial records to be kept for
at least 7 years. This module provides the interface for storing
and retrieving VAT calculation records for compliance reporting.

Reference: EY Baltic Tax Card 2025
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal


@dataclass
class TaxRecord:
    """A stored VAT calculation record for compliance."""

    record_id: str
    order_id: str
    country_code: str
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    vat_rate: Decimal
    transaction_date: date
    invoice_number: str | None = None
    created_at: str = ""
    retention_until: date | None = None

    # Lithuanian accounting law: 7-year minimum retention
    RETENTION_YEARS: int = 7

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()
        if self.retention_until is None:
            self.retention_until = date(
                self.transaction_date.year + self.RETENTION_YEARS,
                self.transaction_date.month,
                self.transaction_date.day,
            )


class TaxRecordStore:
    """Interface for storing and querying tax records.

    Production implementation should use a database with:
    - Append-only writes (no updates/deletes during retention period)
    - 7-year minimum retention per Lithuanian law
    - GDPR data minimisation (only tax-relevant personal data)
    """

    def __init__(self) -> None:
        self._records: list[TaxRecord] = []

    def store(self, record: TaxRecord) -> None:
        """Store a tax record.

        Args:
            record: Tax record to persist.
        """
        self._records.append(record)

    def get_by_order(self, order_id: str) -> list[TaxRecord]:
        """Retrieve tax records for an order.

        Args:
            order_id: Order identifier.

        Returns:
            List of tax records for the order.
        """
        return [r for r in self._records if r.order_id == order_id]

    def get_by_country(
        self,
        country_code: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[TaxRecord]:
        """Retrieve tax records by country and optional date range.

        Args:
            country_code: ISO country code.
            from_date: Start date filter.
            to_date: End date filter.

        Returns:
            Matching tax records.
        """
        results = [r for r in self._records if r.country_code == country_code]
        if from_date:
            results = [r for r in results if r.transaction_date >= from_date]
        if to_date:
            results = [r for r in results if r.transaction_date <= to_date]
        return results

    def get_retention_report(self) -> dict[str, int]:
        """Get a report of records approaching retention expiry.

        Returns:
            Dictionary with counts by year of retention expiry.
        """
        report: dict[str, int] = {}
        for record in self._records:
            if record.retention_until:
                year = str(record.retention_until.year)
                report[year] = report.get(year, 0) + 1
        return report
