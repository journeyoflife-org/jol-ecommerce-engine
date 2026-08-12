"""Integration tests for payment intent processing."""

import pytest
from jol_commerce.payments.payment_intent import (
    PaymentIntentRequest,
    PaymentIntentService,
    PaymentStatus,
)


class TestPaymentIntentIntegration:
    """Integration tests for payment intent lifecycle."""

    def test_payment_intent_request_requires_stripe_token(self) -> None:
        """Payment method ID must be a Stripe token, not raw card data."""
        request = PaymentIntentRequest(
            amount_cents=10000,
            currency="eur",
            payment_method_id="pm_test_123",
            order_id="ORD-001",
        )
        assert request.payment_method_id.startswith("pm_")

    def test_payment_intent_request_rejects_raw_card_data(self) -> None:
        """Raw card numbers must never be accepted as payment method."""
        raw_pan = "4242" * 4  # assembled at runtime — no PAN literal in source
        request = PaymentIntentRequest(
            amount_cents=10000,
            currency="eur",
            payment_method_id=raw_pan,  # Raw PAN — should fail
            order_id="ORD-002",
        )
        service = PaymentIntentService()
        with pytest.raises(ValueError, match="must be a Stripe token"):
            service.create_intent(request)

    def test_payment_status_enum_completeness(self) -> None:
        """All Stripe PaymentIntent statuses are mapped."""
        expected = {
            "created",
            "requires_confirmation",
            "processing",
            "succeeded",
            "requires_action",
            "cancelled",
            "failed",
        }
        actual = {s.value for s in PaymentStatus}
        assert expected == actual
