"""Stripe webhook handler — processes payment events from Stripe.

PCI DSS Req. 10: Every webhook receipt is logged to the audit trail.
Webhook signatures are verified to ensure authenticity.

Reference: https://stripe.com/docs/webhooks
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

import stripe

from jol_commerce.audit.audit_log import AuditLogger
from jol_commerce.config import get_settings


class WebhookEventType(str, Enum):
    """Stripe webhook event types relevant to JOL Commerce."""

    PAYMENT_INTENT_SUCCEEDED = "payment_intent.succeeded"
    PAYMENT_INTENT_FAILED = "payment_intent.payment_failed"
    PAYMENT_INTENT_CANCELLED = "payment_intent.canceled"
    CHARGE_REFUNDED = "charge.refunded"
    CHARGE_DISPUTE_CREATED = "charge.dispute.created"


@dataclass
class WebhookEvent:
    """Parsed and verified webhook event."""

    event_id: str
    event_type: WebhookEventType
    payment_intent_id: str | None
    timestamp: str
    raw_payload: str


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""


class StripeWebhookHandler:
    """Handles incoming Stripe webhooks with signature verification.

    Every webhook event is:
    1. Signature-verified against the webhook secret
    2. Logged to the audit trail (PCI DSS Req. 10)
    3. Dispatched to the appropriate handler
    """

    # Stripe recommends rejecting events older than 5 minutes
    MAX_TIMESTAMP_DRIFT_SECONDS = 300

    def __init__(self) -> None:
        settings = get_settings()
        self._webhook_secret = settings.stripe_webhook_secret
        self._audit = AuditLogger()

    def verify_signature(
        self,
        payload: str,
        sig_header: str,
        tolerance_seconds: int = MAX_TIMESTAMP_DRIFT_SECONDS,
    ) -> stripe.Event:
        """Verify Stripe webhook signature.

        Args:
            payload: Raw request body.
            sig_header: Stripe-Signature header value.
            tolerance_seconds: Maximum age of the event timestamp.

        Returns:
            Verified Stripe Event object.

        Raises:
            WebhookVerificationError: If signature is invalid or event is stale.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                self._webhook_secret,
            )
        except ValueError as e:
            raise WebhookVerificationError(f"Invalid payload: {e}") from e
        except stripe.error.SignatureVerificationError as e:
            raise WebhookVerificationError(f"Invalid signature: {e}") from e

        # Check timestamp freshness
        event_age = time.time() - event.created
        if event_age > tolerance_seconds:
            raise WebhookVerificationError(
                f"Webhook event is stale: {event_age:.0f}s old (max allowed: {tolerance_seconds}s)",
            )

        return event

    def handle_event(self, event: stripe.Event) -> dict[str, str]:
        """Process a verified webhook event.

        Args:
            event: Verified Stripe event.

        Returns:
            Processing result with status.
        """
        event_type = event.type
        data = event.data.object

        # Extract payment intent ID from the event data
        payment_intent_id = None
        if hasattr(data, "payment_intent"):
            payment_intent_id = data.payment_intent
        elif hasattr(data, "id") and event_type.startswith("payment_intent"):
            payment_intent_id = data.id

        # Log the webhook receipt for PCI DSS Req. 10
        receipt = {
            "event_id": event.id,
            "event_type": event_type,
            "payment_intent_id": payment_intent_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "stripe_created": event.created,
        }
        self._audit.log(
            actor="stripe_webhook",
            event_type=f"webhook.{event_type}",
            outcome="success",
            transaction_ref=payment_intent_id or event.id,
            details=receipt,
        )

        # Dispatch to handler based on event type
        if event_type == WebhookEventType.PAYMENT_INTENT_SUCCEEDED:
            return self._handle_payment_succeeded(data, receipt)
        if event_type == WebhookEventType.PAYMENT_INTENT_FAILED:
            return self._handle_payment_failed(data, receipt)
        if event_type == WebhookEventType.CHARGE_REFUNDED:
            return self._handle_charge_refunded(data, receipt)
        return {"status": "ignored", "event_type": event_type}

    def _handle_payment_succeeded(
        self,
        data: object,
        receipt: dict[str, str],
    ) -> dict[str, str]:
        """Handle payment_intent.succeeded event."""
        receipt["status"] = "processed"
        receipt["action"] = "fulfill_order"
        return receipt

    def _handle_payment_failed(
        self,
        data: object,
        receipt: dict[str, str],
    ) -> dict[str, str]:
        """Handle payment_intent.payment_failed event."""
        receipt["status"] = "processed"
        receipt["action"] = "notify_failure"
        return receipt

    def _handle_charge_refunded(
        self,
        data: object,
        receipt: dict[str, str],
    ) -> dict[str, str]:
        """Handle charge.refunded event."""
        receipt["status"] = "processed"
        receipt["action"] = "process_refund"
        return receipt
