"""Payment flow orchestration — the four v2.0 payment scenarios (§3.5).

| Scenario             | Flow                                              | PCI Scope |
|----------------------|---------------------------------------------------|-----------|
| Online Pre-Pay       | pm_ token → PaymentIntent → immediate capture     | SAQ-A     |
| Post-Service Deferred| pm_ token → SetupIntent → charge on completion    | SAQ-A     |
| In-Person Settlement | terminal receipt_ref linked to order              | SAQ-A     |
| Mixed Payment        | partial online + deferred/in-person balance       | SAQ-A     |

Critical controls (Blueprint §3.5):
- No raw PAN in logs, headers, or database (Zero-PAN).
- Every charge request carries an Idempotency-Key.
- Only gateway references are persisted (PaymentToken).
"""

from __future__ import annotations

from dataclasses import dataclass

from jol_commerce.audit.audit_log import AuditLogger
from jol_commerce.orders.order_lifecycle import PaymentMode
from jol_commerce.payments.payment_intent import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentIntentService,
)
from jol_commerce.payments.payment_token import (
    PaymentToken,
    PaymentTokenStore,
    TokenType,
)
from jol_commerce.payments.stripe_client import StripeClient


class PaymentFlowError(ValueError):
    """Raised when a payment flow is invoked with invalid arguments."""


@dataclass(frozen=True)
class DeferredChargeResult:
    """Outcome of a deferred (off-session) charge attempt."""

    payment_intent_id: str
    status: str
    amount_cents: int
    currency: str


class PaymentFlowService:
    """Coordinates the four payment modalities over the token store."""

    def __init__(
        self,
        token_store: PaymentTokenStore | None = None,
        *,
        intent_service: PaymentIntentService | None = None,
        stripe: StripeClient | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self._tokens = token_store or PaymentTokenStore()
        self._intents = intent_service or PaymentIntentService()
        self._stripe = stripe or StripeClient()
        self._audit = audit or AuditLogger()

    @property
    def token_store(self) -> PaymentTokenStore:
        return self._tokens

    # ── Scenario 1: Online Pre-Pay ─────────────────────────────────────
    def online_prepay(
        self,
        tenant_id: str,
        request: PaymentIntentRequest,
    ) -> PaymentIntentResponse:
        """Immediate capture via Stripe Elements token (Blueprint §4.1)."""
        response = self._intents.create_intent(request)
        self._tokens.store(
            PaymentToken(
                tenant_id=tenant_id,
                order_id=request.order_id,
                gateway_ref=response.payment_intent_id,
                token_type=TokenType.PAYMENT_INTENT,
            ),
        )
        return response

    # ── Scenario 2: Post-Service Deferred ──────────────────────────────
    def authorize_deferred(
        self,
        tenant_id: str,
        order_id: str,
        payment_method_id: str,
        *,
        customer_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> PaymentToken:
        """Customer authorizes card now; charge happens on completion (§4.2).

        Only the SetupIntent ID is stored — never card data.
        """
        setup_intent = self._stripe.create_setup_intent(
            payment_method_id,
            customer_id=customer_id,
            idempotency_key=idempotency_key,
            metadata={"order_id": order_id},
        )
        token = PaymentToken(
            tenant_id=tenant_id,
            order_id=order_id,
            gateway_ref=setup_intent.id,
            token_type=TokenType.SETUP_INTENT,
        )
        self._tokens.store(token)
        self._audit.log(
            actor="payment_service",
            event_type="payment.deferred_authorized",
            outcome="success",
            transaction_ref=setup_intent.id,
            details={"tenant_id": tenant_id, "order_id": order_id},
        )
        return token

    def charge_deferred(
        self,
        token: PaymentToken,
        *,
        amount_cents: int,
        currency: str = "eur",
        payment_method_id: str,
        customer_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> DeferredChargeResult:
        """Trigger the deferred charge on service completion (§4.2 step 5).

        Args:
            token: Stored SetupIntent token for the order.
            amount_cents: Final service amount to charge.
            currency: ISO 4217 currency code.
            payment_method_id: Payment method attached during setup (pm_xxx).
            customer_id: Stripe customer ID (required off-session).
            idempotency_key: Mandatory idempotency key for the charge.

        Returns:
            DeferredChargeResult with gateway intent status.

        Raises:
            PaymentFlowError: If the token is not a SetupIntent token.
        """
        if token.token_type is not TokenType.SETUP_INTENT:
            raise PaymentFlowError(
                f"Deferred charge requires a setup_intent token, got {token.token_type.value}",
            )

        intent = self._stripe.charge_from_token(
            amount_cents,
            currency,
            payment_method_id,
            customer_id=customer_id,
            idempotency_key=idempotency_key,
            metadata={"order_id": token.order_id, "setup_intent": token.gateway_ref},
        )
        self._audit.log(
            actor="payment_service",
            event_type="payment.deferred_charged",
            outcome="success" if intent.status == "succeeded" else "failure",
            transaction_ref=intent.id,
            details={
                "tenant_id": token.tenant_id,
                "order_id": token.order_id,
                "amount_cents": amount_cents,
                "status": intent.status,
            },
        )
        return DeferredChargeResult(
            payment_intent_id=intent.id,
            status=intent.status,
            amount_cents=intent.amount,
            currency=intent.currency,
        )

    # ── Scenario 3: In-Person Settlement ───────────────────────────────
    def record_in_person(
        self,
        tenant_id: str,
        order_id: str,
        receipt_ref: str,
    ) -> PaymentToken:
        """Link a terminal receipt reference to an order (§3.5).

        The terminal (Stripe Terminal / Adyen POS) processed the card;
        only the receipt reference is stored — SAQ-A scope preserved.
        """
        if not receipt_ref:
            raise PaymentFlowError("receipt_ref is required for in-person settlement")
        token = PaymentToken(
            tenant_id=tenant_id,
            order_id=order_id,
            gateway_ref=receipt_ref,
            token_type=TokenType.RECEIPT_REF,
        )
        self._tokens.store(token)
        self._audit.log(
            actor="payment_service",
            event_type="payment.in_person_recorded",
            outcome="success",
            transaction_ref=receipt_ref,
            details={"tenant_id": tenant_id, "order_id": order_id},
        )
        return token

    # ── Scenario 4: Mixed Payment ──────────────────────────────────────
    def validate_mixed_split(
        self,
        payment_mode: PaymentMode,
        prepay_amount_cents: int,
        total_amount_cents: int,
    ) -> None:
        """Validate a mixed payment split (partial online + deferred balance).

        Raises:
            PaymentFlowError: On invalid splits or wrong payment mode.
        """
        if payment_mode is not PaymentMode.MIXED:
            raise PaymentFlowError("validate_mixed_split requires payment_mode=mixed")
        if prepay_amount_cents <= 0:
            raise PaymentFlowError("Mixed payment requires a positive prepay amount")
        if prepay_amount_cents >= total_amount_cents:
            raise PaymentFlowError(
                "Mixed prepay must be strictly less than the order total "
                "(balance settles deferred or in-person)",
            )
