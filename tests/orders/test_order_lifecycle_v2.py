"""Order lifecycle tests — v2.0 state machine and payment modes (§3.3)."""

import pytest
from jol_commerce.orders.order_lifecycle import (
    VALID_TRANSITIONS,
    Order,
    OrderStatus,
    PaymentMode,
)


class TestV2StateMachine:
    def test_full_happy_path(self) -> None:
        order = Order(order_id="ORD-1")
        for status in (
            OrderStatus.RESERVED,
            OrderStatus.CONFIRMED,
            OrderStatus.IN_PROGRESS,
            OrderStatus.COMPLETED,
        ):
            order.transition_to(status, changed_by="test")
        assert order.status is OrderStatus.COMPLETED

    def test_invalid_transition_raises(self) -> None:
        order = Order(order_id="ORD-1")
        with pytest.raises(ValueError, match="Invalid transition"):
            order.transition_to(OrderStatus.COMPLETED, changed_by="test")

    def test_cancel_allowed_from_all_pre_completion_states(self) -> None:
        for start in (
            OrderStatus.DRAFT,
            OrderStatus.RESERVED,
            OrderStatus.CONFIRMED,
            OrderStatus.IN_PROGRESS,
            OrderStatus.PAYMENT_PENDING,
        ):
            order = Order(order_id="ORD-1", status=start)
            assert order.is_cancellable is True
            order.transition_to(OrderStatus.CANCELLED, changed_by="test")

    def test_completed_is_terminal(self) -> None:
        order = Order(order_id="ORD-1", status=OrderStatus.COMPLETED)
        assert VALID_TRANSITIONS[OrderStatus.COMPLETED] == set()
        with pytest.raises(ValueError):
            order.transition_to(OrderStatus.CANCELLED, changed_by="test")

    def test_deferred_charge_failure_path(self) -> None:
        """§4.2: in_progress → payment_pending → completed on retry."""
        order = Order(order_id="ORD-1", status=OrderStatus.IN_PROGRESS)
        order.transition_to(OrderStatus.PAYMENT_PENDING, changed_by="payment_service")
        order.transition_to(OrderStatus.COMPLETED, changed_by="payment_service")
        assert order.status is OrderStatus.COMPLETED

    def test_history_records_every_transition(self) -> None:
        order = Order(order_id="ORD-1")
        order.transition_to(OrderStatus.RESERVED, changed_by="api", reason="checkout")
        assert len(order.history) == 1
        assert order.history[0].from_status is OrderStatus.DRAFT
        assert order.history[0].to_status is OrderStatus.RESERVED


class TestPaymentModes:
    def test_all_four_modes_defined(self) -> None:
        assert {m.value for m in PaymentMode} == {
            "online_prepay",
            "post_service",
            "in_person",
            "mixed",
        }

    def test_order_defaults_to_online_prepay(self) -> None:
        order = Order(order_id="ORD-1")
        assert order.payment_mode is PaymentMode.ONLINE_PREPAY

    def test_external_id_is_uuid(self) -> None:
        """§3.6: order_id maps to UUID external_id for Bitrix24."""
        import uuid

        order = Order(order_id="ORD-1")
        uuid.UUID(order.external_id)  # raises if not a UUID
