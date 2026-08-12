"""Order fulfillment — post-payment service processing (Blueprint v2.0).

Service-commerce fulfillment differs from goods shipping: confirmation
moves the order into service delivery (`in_progress`) and completion is
confirmed by the priest/branch foreman or caretaker in the field.
All fulfillment events are logged to the audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass

from jol_commerce.orders.order_lifecycle import Order, OrderStatus


@dataclass
class FulfillmentEvent:
    """Record of a fulfillment action."""

    order_id: str
    event_type: str
    details: str
    timestamp: str


class FulfillmentService:
    """Manages order fulfillment after payment confirmation."""

    def __init__(self) -> None:
        self._events: list[FulfillmentEvent] = []

    def confirm_payment(self, order: Order, payment_intent_id: str) -> FulfillmentEvent:
        """Confirm payment and transition order to confirmed.

        Args:
            order: The order to confirm.
            payment_intent_id: Stripe payment intent reference.

        Returns:
            Fulfillment event for audit trail.
        """
        change = order.transition_to(
            OrderStatus.CONFIRMED,
            changed_by="stripe_webhook",
            reason=f"Payment confirmed: {payment_intent_id}",
        )

        event = FulfillmentEvent(
            order_id=order.order_id,
            event_type="payment_confirmed",
            details=f"Payment intent {payment_intent_id} confirmed",
            timestamp=change.changed_at,
        )
        self._events.append(event)
        return event

    def start_service(self, order: Order, assigned_to: str) -> FulfillmentEvent:
        """Mark the order as in progress (dispatch assignment).

        Args:
            order: The order to start.
            assigned_to: Caretaker/dispatcher assignment reference (no PII).

        Returns:
            Fulfillment event for audit trail.
        """
        change = order.transition_to(
            OrderStatus.IN_PROGRESS,
            changed_by="dispatch",
            reason=f"Service assigned: {assigned_to}",
        )

        event = FulfillmentEvent(
            order_id=order.order_id,
            event_type="service_started",
            details=f"Assigned: {assigned_to}",
            timestamp=change.changed_at,
        )
        self._events.append(event)
        return event

    def get_events(self, order_id: str) -> list[FulfillmentEvent]:
        """Get fulfillment events for an order."""
        return [e for e in self._events if e.order_id == order_id]
