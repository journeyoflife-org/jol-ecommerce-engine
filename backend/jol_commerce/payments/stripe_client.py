"""Stripe client — tokenisation only. No raw card data touches this server.

PCI DSS SAQ A compliance: card numbers, CVV, and expiry are collected
exclusively within Stripe Elements/Checkout hosted iframes. This module
only handles Stripe API calls using tokenized payment method IDs.

Reference: https://stripe.com/guides/pci-compliance
"""

from __future__ import annotations

import stripe

from jol_commerce.config import get_settings


class StripeClient:
    """Wrapper around the Stripe SDK enforcing tokenisation-only usage.

    No method in this class accepts raw card numbers, CVV, or expiry dates.
    All card data flows: browser → Stripe iframe → token → this server.
    """

    def __init__(self) -> None:
        """Initialize the Stripe client with the configured API key."""
        settings = get_settings()
        stripe.api_key = settings.stripe_secret_key
        stripe.api_version = "2024-12-18.acacia"

    @staticmethod
    def create_payment_intent(
        amount_cents: int,
        currency: str,
        payment_method_id: str,
        *,
        customer_id: str | None = None,
        idempotency_key: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> stripe.PaymentIntent:
        """Create a Stripe PaymentIntent using a tokenized payment method.

        Args:
            amount_cents: Amount in the smallest currency unit (e.g., cents).
            currency: ISO 4217 currency code (e.g., 'eur').
            payment_method_id: Stripe payment method ID (pm_xxx) — tokenized, not raw.
            customer_id: Optional Stripe customer ID.
            idempotency_key: Idempotency key for retry safety.
            metadata: Optional metadata dict (must NOT contain card data).

        Returns:
            Stripe PaymentIntent object.

        Raises:
            stripe.StripeError: On Stripe API errors.
            ValueError: If payment_method_id is not a valid Stripe token format.
        """
        if not payment_method_id.startswith("pm_"):
            raise ValueError(
                "payment_method_id must be a Stripe token (pm_xxx). "
                "Raw card data must never be passed to this method.",
            )

        params: dict[str, object] = {
            "amount": amount_cents,
            "currency": currency,
            "payment_method": payment_method_id,
            "confirm": True,
            "automatic_payment_methods": {
                "enabled": True,
                "allow_redirects": "never",
            },
        }
        if customer_id:
            params["customer"] = customer_id
        if metadata:
            params["metadata"] = metadata

        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        return stripe.PaymentIntent.create(
            **params, stripe_account=None, **({"headers": headers} if headers else {})
        )

    @staticmethod
    def retrieve_payment_intent(payment_intent_id: str) -> stripe.PaymentIntent:
        """Retrieve a PaymentIntent by ID.

        Args:
            payment_intent_id: Stripe PaymentIntent ID (pi_xxx).

        Returns:
            Stripe PaymentIntent object.
        """
        return stripe.PaymentIntent.retrieve(payment_intent_id)

    @staticmethod
    def create_refund(
        payment_intent_id: str,
        *,
        amount_cents: int | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> stripe.Refund:
        """Create a refund for a PaymentIntent.

        Args:
            payment_intent_id: Stripe PaymentIntent ID (pi_xxx).
            amount_cents: Partial refund amount. None for full refund.
            reason: Reason for the refund.
            idempotency_key: Idempotency key for retry safety.

        Returns:
            Stripe Refund object.
        """
        params: dict[str, object] = {"payment_intent": payment_intent_id}
        if amount_cents is not None:
            params["amount"] = amount_cents
        if reason:
            params["reason"] = reason

        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        return stripe.Refund.create(**params, **({"headers": headers} if headers else {}))
