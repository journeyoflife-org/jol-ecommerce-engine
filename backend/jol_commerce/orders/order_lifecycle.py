"""Order lifecycle management — state machine for order processing.

Every order state change produces an audit log entry (PCI DSS Req. 10).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class OrderStatus(str, Enum):
    """Order lifecycle states."""

    DRAFT = "draft"
    PENDING_PAYMENT = "pending_payment"
    PAYMENT_CONFIRMED = "payment_confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# Valid state transitions
VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.PENDING_PAYMENT, OrderStatus.CANCELLED},
    OrderStatus.PENDING_PAYMENT: {OrderStatus.PAYMENT_CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.PAYMENT_CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.REFUNDED},
    OrderStatus.DELIVERED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
}


@dataclass
class OrderStateChange:
    """Record of an order state transition."""

    order_id: str
    from_status: OrderStatus
    to_status: OrderStatus
    changed_at: str
    changed_by: str
    reason: str = ""


@dataclass
class Order:
    """Order entity with lifecycle management."""

    order_id: str
    status: OrderStatus = OrderStatus.DRAFT
    customer_id: str = ""
    items: list[dict[str, object]] = field(default_factory=list)
    total_amount_cents: int = 0
    currency: str = "EUR"
    country_code: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = ""
    history: list[OrderStateChange] = field(default_factory=list)

    def transition_to(
        self,
        new_status: OrderStatus,
        changed_by: str,
        reason: str = "",
    ) -> OrderStateChange:
        """Transition the order to a new status.

        Args:
            new_status: Target order status.
            changed_by: Identity of who/system making the change.
            reason: Reason for the transition.

        Returns:
            OrderStateChange record for audit logging.

        Raises:
            ValueError: If the transition is not valid.
        """
        if new_status not in VALID_TRANSITIONS.get(self.status, set()):
            raise ValueError(
                f"Invalid transition: {self.status.value} → {new_status.value}. "
                f"Allowed: {[s.value for s in VALID_TRANSITIONS.get(self.status, set())]}",
            )

        change = OrderStateChange(
            order_id=self.order_id,
            from_status=self.status,
            to_status=new_status,
            changed_at=datetime.now(UTC).isoformat(),
            changed_by=changed_by,
            reason=reason,
        )

        self.status = new_status
        self.updated_at = change.changed_at
        self.history.append(change)

        return change
