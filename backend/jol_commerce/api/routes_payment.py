"""Payment API routes — PCI DSS SAQ A compliant endpoints.

All payment endpoints work with tokenized Stripe payment method IDs.
Raw card data is never accepted or processed.
"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request

from jol_commerce.api.schemas import (
    CreatePaymentIntentRequest,
    PaymentIntentResponse,
    RefundRequest,
    RefundResponse,
    WebhookEventResponse,
)
from jol_commerce.payments.payment_intent import (
    PaymentIntentRequest,
    PaymentIntentService,
)
from jol_commerce.payments.refund import RefundReason, RefundService
from jol_commerce.payments.refund import RefundRequest as InternalRefundRequest
from jol_commerce.payments.webhook_handler import StripeWebhookHandler, WebhookVerificationError

router = APIRouter()
_intent_service = PaymentIntentService()
_refund_service = RefundService()
_webhook_handler = StripeWebhookHandler()


@router.post("/intents", response_model=PaymentIntentResponse)
async def create_payment_intent(request: CreatePaymentIntentRequest) -> PaymentIntentResponse:
    """Create a payment intent using a tokenized Stripe payment method.

    The payment_method_id must be a Stripe token (pm_xxx) obtained
    from Stripe Elements/Checkout — never a raw card number.
    """
    internal_request = PaymentIntentRequest(
        amount_cents=request.amount_cents,
        currency=request.currency,
        payment_method_id=request.payment_method_id,
        order_id=request.order_id,
        customer_id=request.customer_id,
        idempotency_key=request.idempotency_key,
    )
    result = _intent_service.create_intent(internal_request)
    return PaymentIntentResponse(
        payment_intent_id=result.payment_intent_id,
        status=result.status.value,
        amount_cents=result.amount_cents,
        currency=result.currency,
        order_id=result.order_id,
    )


@router.post("/refunds", response_model=RefundResponse)
async def create_refund(request: RefundRequest) -> RefundResponse:
    """Process a refund for a payment intent."""
    internal_request = InternalRefundRequest(
        payment_intent_id=request.payment_intent_id,
        amount_cents=request.amount_cents,
        reason=RefundReason(request.reason)
        if request.reason
        else RefundReason.REQUESTED_BY_CUSTOMER,
        idempotency_key=request.idempotency_key,
    )
    result = _refund_service.process_refund(internal_request)
    return RefundResponse(
        refund_id=result.refund_id,
        payment_intent_id=result.payment_intent_id,
        amount_cents=result.amount_cents,
        status=result.status.value,
    )


@router.post("/webhooks/stripe", response_model=WebhookEventResponse)
async def handle_stripe_webhook(
    request: Request,
    stripe_signature: str = Header(..., alias="Stripe-Signature"),
) -> WebhookEventResponse:
    """Receive and process Stripe webhook events.

    Signature is verified before processing. All events are logged
    to the audit trail (PCI DSS Req. 10).
    """
    payload = await request.body()

    try:
        event = _webhook_handler.verify_signature(
            payload=payload.decode("utf-8"),
            sig_header=stripe_signature,
        )
    except WebhookVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    result = _webhook_handler.handle_event(event)
    return WebhookEventResponse(status=result.get("status", "processed"))
