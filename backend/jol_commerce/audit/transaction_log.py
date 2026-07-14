"""Transaction log — PCI DSS Req. 10 payment event logging.

Logs every payment event: intent creation, confirmation, failure,
webhook receipt, refund, and dispute. This is the payment-specific
subset of the audit trail.

PCI DSS v4.0.1 Requirement 10.4.1.1 mandates automated log review
via SIEM — manual daily review is no longer compliant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class TransactionEventType(str, Enum):
    """Payment transaction event types."""

    INTENT_CREATED = "intent_created"
    INTENT_CONFIRMED = "intent_confirmed"
    INTENT_FAILED = "intent_failed"
    INTENT_CANCELLED = "intent_cancelled"
    WEBHOOK_RECEIVED = "webhook_received"
    REFUND_INITIATED = "refund_initiated"
    REFUND_COMPLETED = "refund_completed"
    DISPUTE_OPENED = "dispute_opened"
    DISPUTE_RESOLVED = "dispute_resolved"


@dataclass(frozen=True)
class TransactionLogEntry:
    """A single transaction log entry for a payment event."""

    event_id: str = ""
    event_type: TransactionEventType = TransactionEventType.INTENT_CREATED
    payment_intent_id: str = ""
    order_id: str = ""
    amount_cents: int = 0
    currency: str = "EUR"
    outcome: str = ""  # "success" or "failure"
    actor: str = ""  # "customer", "system", "stripe_webhook"
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    correlation_id: str = ""
    error_code: str | None = None

    # CRITICAL: No card data fields. No PAN, CVV, or expiry.
    # Only Stripe token references (pi_xxx, pm_xxx, ch_xxx) are stored.


class TransactionLogger:
    """Specialized logger for payment transaction events.

    Every payment lifecycle event produces a log entry.
    Entries are forwarded to the SIEM for automated review
    (PCI DSS v4.0.1 Req. 10.4.1.1).
    """

    def __init__(self) -> None:
        self._entries: list[TransactionLogEntry] = []

    def log_event(self, entry: TransactionLogEntry) -> None:
        """Record a transaction event.

        Args:
            entry: Transaction log entry to record.
        """
        self._entries.append(entry)

    def get_by_payment_intent(self, payment_intent_id: str) -> list[TransactionLogEntry]:
        """Get all events for a payment intent.

        Args:
            payment_intent_id: Stripe payment intent ID.

        Returns:
            List of transaction log entries.
        """
        return [e for e in self._entries if e.payment_intent_id == payment_intent_id]

    def get_by_order(self, order_id: str) -> list[TransactionLogEntry]:
        """Get all transaction events for an order.

        Args:
            order_id: Order identifier.

        Returns:
            List of transaction log entries.
        """
        return [e for e in self._entries if e.order_id == order_id]

    def get_failures(self) -> list[TransactionLogEntry]:
        """Get all failed transaction events for SIEM alerting.

        Returns:
            List of failed transaction log entries.
        """
        return [e for e in self._entries if e.outcome == "failure"]
