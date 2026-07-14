"""Webhook signature verification tests."""

import pytest
from jol_commerce.payments.webhook_handler import (
    StripeWebhookHandler,
    WebhookVerificationError,
)


@pytest.mark.security
class TestWebhookSignature:
    """Verify Stripe webhook signature enforcement."""

    def test_handler_initializes(self) -> None:
        handler = StripeWebhookHandler()
        assert handler._webhook_secret is not None

    def test_invalid_payload_rejected(self) -> None:
        handler = StripeWebhookHandler()
        with pytest.raises(WebhookVerificationError):
            handler.verify_signature("invalid", "invalid")

    def test_empty_payload_rejected(self) -> None:
        handler = StripeWebhookHandler()
        with pytest.raises(WebhookVerificationError):
            handler.verify_signature("", "")

    def test_max_timestamp_drift_is_300_seconds(self) -> None:
        """Stripe recommends 5-minute maximum event age."""
        assert StripeWebhookHandler.MAX_TIMESTAMP_DRIFT_SECONDS == 300
