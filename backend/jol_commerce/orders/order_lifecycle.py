"""Order lifecycle management — v2.0 state machine (Blueprint §3.3).

State machine:

    [draft] ─▶ [reserved] ─▶ [confirmed] ─▶ [in_progress] ─▶ [completed]
        │           │              │               │
        └───────────┴──────────────┴───────────────┘
                        ↓
                 [cancelled]  (triggers refund workflow + audit entry)

    [in_progress] ─▶ [payment_pending] when a deferred charge fails;
    [payment_pending] ─▶ [completed] on retry success (Blueprint §4.2).

Every order carries:
- payment_mode: online_prepay | post_service | in_person | mixed
- commission_snapshot captured on completion (default 10%, tenant-
  configurable — Blueprint §3.3 Commission Engine).

Every state change produces an audit log entry (PCI DSS Req. 10).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class OrderStatus(str, Enum):
    """Order lifecycle states (Blueprint v2.0 §3.3)."""

    DRAFT = "draft"
    RESERVED = "reserved"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    PAYMENT_PENDING = "payment_pending"  # deferred charge failed (§4.2)
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PaymentMode(str, Enum):
    """Supported payment modalities (Blueprint v2.0 §3.5)."""

    ONLINE_PREPAY = "online_prepay"  # Stripe Elements → immediate capture
    POST_SERVICE = "post_service"  # SetupIntent → charge on completion
    IN_PERSON = "in_person"  # Terminal receipt_ref linked to order
    MIXED = "mixed"  # Partial online + deferred/in-person balance


# Valid state transitions (Blueprint §3.3 state machine).
VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.DRAFT: {OrderStatus.RESERVED, OrderStatus.CANCELLED},
    OrderStatus.RESERVED: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED},
    OrderStatus.IN_PROGRESS: {
        OrderStatus.COMPLETED,
        OrderStatus.PAYMENT_PENDING,
        OrderStatus.CANCELLED,
    },
    OrderStatus.PAYMENT_PENDING: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}

# States from which cancellation (and refund workflow) is permitted.
CANCELLABLE_STATES = {
    OrderStatus.DRAFT,
    OrderStatus.RESERVED,
    OrderStatus.CONFIRMED,
    OrderStatus.IN_PROGRESS,
    OrderStatus.PAYMENT_PENDING,
}


@dataclass(frozen=True)
class CommissionSnapshot:
    """Commission split captured at order completion (Blueprint §3.3).

    Amounts are in the smallest currency unit (cents). The snapshot is
    immutable: later changes to the tenant contract rate must not alter
    historical settlements.
    """

    rate: str  # e.g. "0.10"
    platform_fee_cents: int
    tenant_settlement_cents: int


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
    """Order entity with lifecycle management (Blueprint §3.3 domain model)."""

    order_id: str
    tenant_id: str = ""
    status: OrderStatus = OrderStatus.DRAFT
    payment_mode: PaymentMode = PaymentMode.ONLINE_PREPAY
    customer_id: str = ""
    items: list[dict[str, object]] = field(default_factory=list)
    total_amount_cents: int = 0
    currency: str = "EUR"
    country_code: str = ""
    branch_id: str = ""
    service_type: str = ""  # propagated to Bitrix24 sync (scrubbed payload)
    external_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    commission_snapshot: CommissionSnapshot | None = None
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

    @property
    def is_cancellable(self) -> bool:
        """Cancellation is allowed up to (but not after) completion."""
        return self.status in CANCELLABLE_STATES
