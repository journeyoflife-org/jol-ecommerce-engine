"""Payment intent management — orchestrates payment lifecycle.

All payment data flows through Stripe tokenisation. This module
coordinates PaymentIntent creation, confirmation, and status tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from jol_commerce.payments.stripe_client import StripeClient


class PaymentStatus(str, Enum):
    """Payment intent lifecycle states."""

    CREATED = "created"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    REQUIRES_ACTION = "requires_action"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class PaymentIntentRequest:
    """Request to create a payment intent.

    CRITICAL: payment_method_id must be a Stripe token (pm_xxx).
    Raw card data must never appear in this structure.
    """

    amount_cents: int
    currency: str
    payment_method_id: str  # Stripe token pm_xxx — NOT raw card data
    order_id: str
    customer_id: str | None = None
    idempotency_key: str | None = None
    metadata: dict[str, str] | None = None


@dataclass
class PaymentIntentResponse:
    """Response from payment intent operations."""

    payment_intent_id: str
    status: PaymentStatus
    amount_cents: int
    currency: str
    order_id: str
    created_at: str
    client_secret: str | None = None


class PaymentIntentService:
    """Service for managing payment intents.

    Coordinates between the Stripe API, order system, and audit log.
    """

    def __init__(self) -> None:
        self._stripe = StripeClient()

    def create_intent(self, request: PaymentIntentRequest) -> PaymentIntentResponse:
        """Create and confirm a payment intent.

        Args:
            request: Payment intent request with tokenized payment method.

        Returns:
            Payment intent response with status and client secret.

        Raises:
            ValueError: If payment method is not a valid Stripe token.
        """
        metadata = request.metadata or {}
        metadata["order_id"] = request.order_id

        intent = self._stripe.create_payment_intent(
            amount_cents=request.amount_cents,
            currency=request.currency,
            payment_method_id=request.payment_method_id,
            customer_id=request.customer_id,
            idempotency_key=request.idempotency_key,
            metadata=metadata,
        )

        return PaymentIntentResponse(
            payment_intent_id=intent.id,
            status=PaymentStatus(intent.status),
            amount_cents=intent.amount,
            currency=intent.currency,
            order_id=request.order_id,
            created_at=datetime.now(UTC).isoformat(),
            client_secret=intent.client_secret,
        )

    def get_intent(self, payment_intent_id: str) -> dict[str, Any]:
        """Retrieve a payment intent by ID.

        Args:
            payment_intent_id: Stripe PaymentIntent ID.

        Returns:
            Payment intent data as dictionary.
        """
        intent = self._stripe.retrieve_payment_intent(payment_intent_id)
        return {
            "payment_intent_id": intent.id,
            "status": intent.status,
            "amount_cents": intent.amount,
            "currency": intent.currency,
        }
