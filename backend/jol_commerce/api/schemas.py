"""API request/response schemas — Pydantic models.

CRITICAL: No schema accepts raw card data (PAN, CVV, expiry).
Payment method IDs must be Stripe tokens (pm_xxx).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

# ── Payment Schemas ──────────────────────────────────────────


class CreatePaymentIntentRequest(BaseModel):
    """Request to create a payment intent."""

    amount_cents: int = Field(..., gt=0, description="Amount in cents")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    payment_method_id: str = Field(
        ...,
        pattern=r"^pm_",
        description="Stripe payment method token (pm_xxx) — NOT raw card data",
    )
    order_id: str
    customer_id: str | None = None
    idempotency_key: str | None = None


class PaymentIntentResponse(BaseModel):
    """Payment intent response."""

    payment_intent_id: str
    status: str
    amount_cents: int
    currency: str
    order_id: str


class RefundRequest(BaseModel):
    """Request to process a refund."""

    payment_intent_id: str
    amount_cents: int | None = None
    reason: str | None = None
    idempotency_key: str | None = None


class RefundResponse(BaseModel):
    """Refund response."""

    refund_id: str
    payment_intent_id: str
    amount_cents: int
    status: str


class WebhookEventResponse(BaseModel):
    """Webhook processing response."""

    status: str


# ── Order Schemas ────────────────────────────────────────────


class OrderItemSchema(BaseModel):
    """Single order item."""

    description: str
    quantity: int = Field(..., gt=0)
    unit_price_cents: int = Field(..., gt=0)


class CreateOrderRequest(BaseModel):
    """Request to create an order."""

    customer_id: str
    items: list[OrderItemSchema]
    total_amount_cents: int
    currency: str = "EUR"
    country_code: str = Field(..., min_length=2, max_length=2)


class OrderResponse(BaseModel):
    """Order response."""

    order_id: str
    status: str
    total_amount_cents: int
    currency: str


# ── Tax Schemas ──────────────────────────────────────────────


class VatCalculationRequest(BaseModel):
    """Request to calculate VAT."""

    net_amount: Decimal = Field(..., gt=0, description="Net amount before VAT")
    country_code: str = Field(..., min_length=2, max_length=2, description="ISO country code")
    transaction_date: date | None = None


class VatCalculationResponse(BaseModel):
    """VAT calculation result."""

    net_amount: str
    vat_amount: str
    gross_amount: str
    vat_rate: str
    country_code: str
    transaction_date: str
