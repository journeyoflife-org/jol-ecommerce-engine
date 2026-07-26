"""Integration tests for Stripe webhook handling."""

import pytest
from jol_commerce.payments.webhook_handler import (
    StripeWebhookHandler,
    WebhookEventType,
    WebhookVerificationError,
)


class TestStripeWebhookIntegration:
    """Integration tests for webhook processing."""

    def test_webhook_handler_initializes_with_config(self) -> None:
        handler = StripeWebhookHandler()
        assert handler._webhook_secret is not None

    def test_invalid_signature_raises_error(self) -> None:
        handler = StripeWebhookHandler()
        with pytest.raises(WebhookVerificationError):
            handler.verify_signature(
                payload="invalid_payload",
                sig_header="invalid_signature",
            )

    def test_webhook_event_types_cover_payment_lifecycle(self) -> None:
        """Verify all critical payment events are handled."""
        expected_events = {
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
            "payment_intent.canceled",
            "charge.refunded",
            "charge.dispute.created",
        }
        actual_events = {e.value for e in WebhookEventType}
        assert expected_events == actual_events
