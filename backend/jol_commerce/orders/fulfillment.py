"""Order fulfillment — post-payment order processing.

Handles order confirmation, shipping coordination, and delivery tracking.
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
        """Confirm payment and transition order to processing.

        Args:
            order: The order to confirm.
            payment_intent_id: Stripe payment intent reference.

        Returns:
            Fulfillment event for audit trail.
        """
        change = order.transition_to(
            OrderStatus.PAYMENT_CONFIRMED,
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

    def ship_order(self, order: Order, tracking_number: str) -> FulfillmentEvent:
        """Mark order as shipped.

        Args:
            order: The order to ship.
            tracking_number: Shipping tracking number.

        Returns:
            Fulfillment event for audit trail.
        """
        order.transition_to(
            OrderStatus.PROCESSING,
            changed_by="fulfillment_service",
            reason="Preparing for shipment",
        )
        change = order.transition_to(
            OrderStatus.SHIPPED,
            changed_by="fulfillment_service",
            reason=f"Shipped with tracking: {tracking_number}",
        )

        event = FulfillmentEvent(
            order_id=order.order_id,
            event_type="order_shipped",
            details=f"Tracking: {tracking_number}",
            timestamp=change.changed_at,
        )
        self._events.append(event)
        return event

    def get_events(self, order_id: str) -> list[FulfillmentEvent]:
        """Get fulfillment events for an order."""
        return [e for e in self._events if e.order_id == order_id]
