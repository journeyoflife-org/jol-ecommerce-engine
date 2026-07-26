"""Refund processing — PCI DSS compliant refund operations.

Refunds are processed via Stripe API using PaymentIntent references.
No raw card data is involved in refund operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum


class RefundStatus(str, Enum):
    """Refund lifecycle states."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "canceled"


class RefundReason(str, Enum):
    """Standard refund reasons."""

    DUPLICATE = "duplicate"
    FRAUDULENT = "fraudulent"
    REQUESTED_BY_CUSTOMER = "requested_by_customer"
    ORDER_NOT_FULFILLED = "order_not_fulfilled"


@dataclass
class RefundRequest:
    """Request to process a refund.

    Only references existing Stripe payment intents — no card data.
    """

    payment_intent_id: str
    amount_cents: int | None = None  # None = full refund
    reason: RefundReason = RefundReason.REQUESTED_BY_CUSTOMER
    idempotency_key: str | None = None
    notes: str | None = None


@dataclass
class RefundResponse:
    """Response from a refund operation."""

    refund_id: str
    payment_intent_id: str
    amount_cents: int
    status: RefundStatus
    reason: RefundReason
    created_at: str


class RefundService:
    """Service for processing refunds via Stripe.

    All refund operations are:
    1. Validated for idempotency
    2. Logged to the audit trail (PCI DSS Req. 10)
    3. Processed via Stripe API
    """

    def process_refund(self, request: RefundRequest) -> RefundResponse:
        """Process a refund for a payment intent.

        Args:
            request: Refund request with payment intent reference.

        Returns:
            Refund response with status and details.
        """
        # Import here to avoid circular dependency at module level
        from jol_commerce.payments.stripe_client import StripeClient

        stripe_refund = StripeClient.create_refund(
            payment_intent_id=request.payment_intent_id,
            amount_cents=request.amount_cents,
            reason=request.reason.value,
            idempotency_key=request.idempotency_key,
        )

        return RefundResponse(
            refund_id=stripe_refund.id,
            payment_intent_id=request.payment_intent_id,
            amount_cents=stripe_refund.amount,
            status=RefundStatus(stripe_refund.status),
            reason=request.reason,
            created_at=datetime.now(UTC).isoformat(),
        )
