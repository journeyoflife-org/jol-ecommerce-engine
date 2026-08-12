"""Payment token + flow tests — Zero-PAN and the four modes (§3.5)."""

import pytest
from jol_commerce.orders.order_lifecycle import PaymentMode
from jol_commerce.payments.payment_flows import PaymentFlowError, PaymentFlowService
from jol_commerce.payments.payment_token import (
    PaymentToken,
    PaymentTokenStore,
    TokenType,
)


class TestZeroPanTokenStore:
    def test_gateway_token_storable(self) -> None:
        store = PaymentTokenStore()
        token = store.store(
            PaymentToken(
                tenant_id="t-1",
                order_id="ORD-1",
                gateway_ref="pm_test_token_123",
                token_type=TokenType.SETUP_INTENT,
            ),
        )
        assert store.get(token.token_id) is not None

    def test_raw_pan_rejected(self) -> None:
        """A 16-digit card number must never be stored (Blueprint §2)."""
        store = PaymentTokenStore()
        raw_pan = "4242" * 4  # assembled at runtime — no PAN literal in source
        with pytest.raises(ValueError, match="Zero-PAN"):
            store.store(
                PaymentToken(
                    tenant_id="t-1",
                    order_id="ORD-1",
                    gateway_ref=raw_pan,
                    token_type=TokenType.PAYMENT_INTENT,
                ),
            )

    def test_receipt_ref_storable_for_in_person(self) -> None:
        store = PaymentTokenStore()
        token = store.store(
            PaymentToken(
                tenant_id="t-1",
                order_id="ORD-1",
                gateway_ref="RCP-2026-0001",
                token_type=TokenType.RECEIPT_REF,
            ),
        )
        assert token.token_type is TokenType.RECEIPT_REF

    def test_tenant_scoped_lookup(self) -> None:
        store = PaymentTokenStore()
        store.store(
            PaymentToken(
                tenant_id="t-1",
                order_id="ORD-1",
                gateway_ref="pm_a",
                token_type=TokenType.PAYMENT_INTENT,
            ),
        )
        assert len(store.for_order("t-1", "ORD-1")) == 1
        assert store.for_order("t-2", "ORD-1") == []


class TestPaymentFlows:
    def test_deferred_charge_requires_setup_intent_token(self) -> None:
        service = PaymentFlowService()
        token = PaymentToken(
            tenant_id="t-1",
            order_id="ORD-1",
            gateway_ref="pi_test_123",
            token_type=TokenType.PAYMENT_INTENT,
        )
        with pytest.raises(PaymentFlowError, match="setup_intent"):
            service.charge_deferred(
                token,
                amount_cents=1000,
                payment_method_id="pm_test",
            )

    def test_in_person_requires_receipt_ref(self) -> None:
        service = PaymentFlowService()
        with pytest.raises(PaymentFlowError, match="receipt_ref"):
            service.record_in_person("t-1", "ORD-1", receipt_ref="")

    def test_in_person_records_token(self) -> None:
        service = PaymentFlowService()
        token = service.record_in_person("t-1", "ORD-1", receipt_ref="RCP-1")
        assert token.token_type is TokenType.RECEIPT_REF
        assert len(service.token_store.for_order("t-1", "ORD-1")) == 1

    def test_mixed_split_requires_positive_prepay(self) -> None:
        service = PaymentFlowService()
        with pytest.raises(PaymentFlowError, match="positive"):
            service.validate_mixed_split(PaymentMode.MIXED, 0, 10000)

    def test_mixed_split_prepay_must_be_partial(self) -> None:
        service = PaymentFlowService()
        with pytest.raises(PaymentFlowError, match="strictly less"):
            service.validate_mixed_split(PaymentMode.MIXED, 10000, 10000)

    def test_mixed_split_valid_partial(self) -> None:
        service = PaymentFlowService()
        service.validate_mixed_split(PaymentMode.MIXED, 3000, 10000)  # no raise

    def test_mixed_validation_requires_mixed_mode(self) -> None:
        service = PaymentFlowService()
        with pytest.raises(PaymentFlowError, match="mixed"):
            service.validate_mixed_split(PaymentMode.ONLINE_PREPAY, 3000, 10000)
