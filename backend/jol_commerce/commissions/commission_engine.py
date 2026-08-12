"""Commission calculation — Blueprint v2.0 §3.3 Commission Engine.

On `completed` status the platform fee is auto-calculated:
- Default 10%, configurable per tenant contract.
- Split: remainder to the tenant settlement account, fee to JOL.

All arithmetic uses Decimal on integer cents to avoid float drift.
The engine is pure: it never mutates orders — the OrderService applies
the resulting snapshot, and the CommissionLedger persists it immutably.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

DEFAULT_COMMISSION_RATE = Decimal("0.10")


@dataclass(frozen=True)
class CommissionSplit:
    """Result of a commission calculation for one completed order.

    Amounts are in the smallest currency unit (cents), integer-exact.
    """

    rate: Decimal
    gross_amount_cents: int
    platform_fee_cents: int
    tenant_settlement_cents: int

    @property
    def rate_str(self) -> str:
        """Rate as a stable decimal string (e.g. '0.10')."""
        return str(self.rate)


class CommissionEngine:
    """Calculates platform fee splits for completed orders."""

    def __init__(self, default_rate: Decimal = DEFAULT_COMMISSION_RATE) -> None:
        self._validate_rate(default_rate)
        self._default_rate = default_rate

    def calculate(self, gross_amount_cents: int, tenant_rate: str | None = None) -> CommissionSplit:
        """Calculate the commission split for a completed order.

        Args:
            gross_amount_cents: Order total in cents.
            tenant_rate: Contractual tenant rate as decimal string
                (e.g. "0.08"). Falls back to the platform default.

        Returns:
            CommissionSplit with integer-cent amounts summing exactly
            to gross_amount_cents (fee truncated in tenant's favour).

        Raises:
            ValueError: On negative amounts or out-of-range rates.
        """
        if gross_amount_cents < 0:
            raise ValueError("gross_amount_cents must be non-negative")

        rate = Decimal(tenant_rate) if tenant_rate is not None else self._default_rate
        self._validate_rate(rate)

        fee = (Decimal(gross_amount_cents) * rate).to_integral_value(rounding=ROUND_DOWN)
        platform_fee_cents = int(fee)
        tenant_settlement_cents = gross_amount_cents - platform_fee_cents

        return CommissionSplit(
            rate=rate,
            gross_amount_cents=gross_amount_cents,
            platform_fee_cents=platform_fee_cents,
            tenant_settlement_cents=tenant_settlement_cents,
        )

    @staticmethod
    def reverse(split: CommissionSplit, fraction: str = "1") -> CommissionSplit:
        """Calculate the reversal of a settled split (gap 4.5).

        Used for chargebacks (fraction "1") and partial refunds. Amounts
        are proportional with the same ROUND_DOWN discipline as the
        original settlement, and the result stays balanced:
        `fee + settlement == gross` on the reversed amounts. Returned
        amounts are positive; the caller negates them when writing the
        reversal ledger entry (the ledger itself stays append-only).

        Currency conversion is never performed here — reversals inherit
        the settlement currency; FX is the payment gateway's concern.

        Raises:
            ValueError: If the fraction is not in (0, 1].
        """
        frac = Decimal(fraction)
        if frac <= 0 or frac > 1:
            raise ValueError(f"Reversal fraction must be within (0, 1]: {fraction}")

        gross_reversed = int(
            (Decimal(split.gross_amount_cents) * frac).to_integral_value(rounding=ROUND_DOWN),
        )
        fee_reversed = int(
            (Decimal(split.platform_fee_cents) * frac).to_integral_value(rounding=ROUND_DOWN),
        )
        return CommissionSplit(
            rate=split.rate,
            gross_amount_cents=gross_reversed,
            platform_fee_cents=fee_reversed,
            tenant_settlement_cents=gross_reversed - fee_reversed,
        )

    @staticmethod
    def _validate_rate(rate: Decimal) -> None:
        if rate < 0 or rate > 1:
            raise ValueError(f"Commission rate must be within [0, 1]: {rate}")
