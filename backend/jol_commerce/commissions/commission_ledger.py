"""Commission ledger — immutable settlement record (Blueprint §3.3).

Ledger entries are append-only and reconciled daily. In production this
is a PostgreSQL table with the same append-only trigger protection as
the audit log (see db/sql/002_tenant_schema_template.sql); the
in-memory implementation enforces the same contract in Python.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal


@dataclass(frozen=True)
class LedgerEntry:
    """One immutable commission settlement entry."""

    tenant_id: str
    order_id: str
    currency: str
    gross_amount_cents: int
    platform_fee_cents: int
    tenant_settlement_cents: int
    rate: str  # stable decimal string, e.g. "0.10"
    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    settled_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if self.platform_fee_cents + self.tenant_settlement_cents != self.gross_amount_cents:
            raise ValueError(
                "Ledger entry is unbalanced: fee + settlement != gross "
                f"({self.platform_fee_cents} + {self.tenant_settlement_cents} "
                f"!= {self.gross_amount_cents})",
            )


class CommissionLedger:
    """Append-only commission ledger, tenant-scoped queries."""

    def __init__(self) -> None:
        self._entries: list[LedgerEntry] = []

    def append(self, entry: LedgerEntry) -> LedgerEntry:
        """Append a settlement entry. Entries can never be mutated or removed."""
        self._entries.append(entry)
        return entry

    def entries_for_tenant(self, tenant_id: str) -> list[LedgerEntry]:
        """All settlement entries for one tenant (reconciliation view)."""
        return [e for e in self._entries if e.tenant_id == tenant_id]

    def platform_fee_total(self, tenant_id: str | None = None) -> int:
        """Total platform fee in cents, optionally per tenant."""
        entries = self.entries_for_tenant(tenant_id) if tenant_id else self._entries
        return sum(e.platform_fee_cents for e in entries)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    def daily_reconciliation_balance(self, tenant_id: str | None = None) -> dict[str, int]:
        """Reconciliation totals (Blueprint: ledger reconciled daily)."""
        entries = self.entries_for_tenant(tenant_id) if tenant_id else self._entries
        return {
            "gross_cents": sum(e.gross_amount_cents for e in entries),
            "platform_fee_cents": sum(e.platform_fee_cents for e in entries),
            "tenant_settlement_cents": sum(e.tenant_settlement_cents for e in entries),
        }


def rate_to_decimal(rate: str) -> Decimal:
    """Parse a stored rate string ('0.10') into a Decimal."""
    return Decimal(rate)
