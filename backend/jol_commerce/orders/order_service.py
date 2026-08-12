"""Order service — orchestrates the v2.0 order lifecycle (Blueprint §3.3).

Responsibilities:
- Tenant-scoped order creation (tenant ID taken from the bound context).
- State transitions with audit log entries for every change.
- Completion handling: capture commission snapshot + append immutable
  ledger entry (Commission Engine, Blueprint §3.3).
- Cancellation: trigger refund workflow + mandatory audit entry
  (Blueprint §3.3 state machine).

Refund execution is injected as a callback so the service stays
decoupled from the Stripe client (and unit-testable).
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from typing import TYPE_CHECKING

from jol_commerce.commissions.commission_engine import CommissionEngine, CommissionSplit
from jol_commerce.commissions.commission_ledger import CommissionLedger, LedgerEntry
from jol_commerce.orders.order_lifecycle import (
    CommissionSnapshot,
    Order,
    OrderStateChange,
    OrderStatus,
)
from jol_commerce.tenancy.tenant import current_tenant_or_none

if TYPE_CHECKING:
    from jol_commerce.audit.audit_log import AuditLogger
    from jol_commerce.orders.order_repository import OrderRepository

# Refund callback: (order) -> gateway refund reference (or "" if none).
RefundCallback = Callable[[Order], str]


class OrderService:
    """Lifecycle orchestration with auditing, commission, and refunds."""

    def __init__(
        self,
        repository: OrderRepository,
        audit: AuditLogger,
        *,
        commission_engine: CommissionEngine | None = None,
        commission_ledger: CommissionLedger | None = None,
        refund_callback: RefundCallback | None = None,
    ) -> None:
        self._repository = repository
        self._audit = audit
        self._commission_engine = commission_engine or CommissionEngine()
        self._commission_ledger = commission_ledger or CommissionLedger()
        self._refund_callback = refund_callback

    @property
    def commission_ledger(self) -> CommissionLedger:
        return self._commission_ledger

    def register(self, order: Order, actor: str) -> Order:
        """Persist a new order inside the current tenant boundary."""
        self._bind_tenant(order)
        self._repository.save(order)
        self._audit.log(
            actor=actor,
            event_type="order.created",
            outcome="success",
            transaction_ref=order.order_id,
            details={
                "tenant_id": order.tenant_id,
                "payment_mode": order.payment_mode.value,
                "amount_cents": order.total_amount_cents,
            },
        )
        return order

    def transition(
        self, order: Order, new_status: OrderStatus, actor: str, reason: str = ""
    ) -> OrderStateChange:
        """Apply a state transition, audit it, and run side effects."""
        change = order.transition_to(new_status, changed_by=actor, reason=reason)
        self._repository.save(order)
        self._audit.log(
            actor=actor,
            event_type="order.status_changed",
            outcome="success",
            transaction_ref=order.order_id,
            details={
                "tenant_id": order.tenant_id,
                "from_status": change.from_status.value,
                "to_status": change.to_status.value,
            },
        )

        if new_status is OrderStatus.COMPLETED:
            self._settle_commission(order, actor)
        return change

    def complete(
        self, order: Order, actor: str, reason: str = "Service completed"
    ) -> OrderStateChange:
        """Priest/caretaker completion confirmation (Blueprint §4.2 step 4)."""
        return self.transition(order, OrderStatus.COMPLETED, actor, reason)

    def cancel(self, order: Order, actor: str, reason: str = "") -> OrderStateChange:
        """Cancel an order: refund workflow + mandatory audit entry."""
        change = self.transition(order, OrderStatus.CANCELLED, actor, reason)

        refund_ref = self._refund_callback(order) if self._refund_callback else ""
        self._audit.log(
            actor=actor,
            event_type="order.cancelled",
            outcome="success",
            transaction_ref=order.order_id,
            details={
                "tenant_id": order.tenant_id,
                "refund_triggered": bool(refund_ref),
                "refund_ref": refund_ref,
                "reason_present": bool(reason),
            },
        )
        return change

    def record_commission_reversal(
        self,
        order: Order,
        actor: str,
        *,
        fraction: str = "1",
        reason: str = "",
    ) -> LedgerEntry:
        """Reverse settled commission after refund/chargeback (gap 4.5).

        The ledger is append-only, so corrections are negative reversal
        entries — never edits of the original settlement. `fraction`
        supports chargebacks ("1") and partial refunds (e.g. "0.5");
        the reversed amounts stay balance-invariant and inherit the
        order's settlement currency (no FX conversion in the engine).
        """
        snapshot = order.commission_snapshot
        if snapshot is None:
            raise ValueError(f"Order {order.order_id} has no settled commission to reverse")

        settled = CommissionSplit(
            rate=Decimal(snapshot.rate),
            gross_amount_cents=snapshot.platform_fee_cents + snapshot.tenant_settlement_cents,
            platform_fee_cents=snapshot.platform_fee_cents,
            tenant_settlement_cents=snapshot.tenant_settlement_cents,
        )
        reversal = CommissionEngine.reverse(settled, fraction)
        entry = LedgerEntry(
            tenant_id=order.tenant_id,
            order_id=order.order_id,
            currency=order.currency,
            gross_amount_cents=-reversal.gross_amount_cents,
            platform_fee_cents=-reversal.platform_fee_cents,
            tenant_settlement_cents=-reversal.tenant_settlement_cents,
            rate=snapshot.rate,
        )
        self._commission_ledger.append(entry)
        self._audit.log(
            actor=actor,
            event_type="commission.reversed",
            outcome="success",
            transaction_ref=order.order_id,
            details={
                "tenant_id": order.tenant_id,
                "fraction": fraction,
                "reversed_fee_cents": reversal.platform_fee_cents,
                "reason_present": bool(reason),
            },
        )
        return entry

    def _settle_commission(self, order: Order, actor: str) -> None:
        """On completion: snapshot the split and append a ledger entry."""
        tenant = current_tenant_or_none()
        tenant_rate = tenant.tenant.commission_rate if tenant else None

        split = self._commission_engine.calculate(
            order.total_amount_cents,
            tenant_rate=tenant_rate,
        )
        order.commission_snapshot = CommissionSnapshot(
            rate=split.rate_str,
            platform_fee_cents=split.platform_fee_cents,
            tenant_settlement_cents=split.tenant_settlement_cents,
        )
        self._commission_ledger.append(
            LedgerEntry(
                tenant_id=order.tenant_id,
                order_id=order.order_id,
                currency=order.currency,
                gross_amount_cents=split.gross_amount_cents,
                platform_fee_cents=split.platform_fee_cents,
                tenant_settlement_cents=split.tenant_settlement_cents,
                rate=split.rate_str,
            ),
        )
        self._audit.log(
            actor=actor,
            event_type="commission.settled",
            outcome="success",
            transaction_ref=order.order_id,
            details={
                "tenant_id": order.tenant_id,
                "rate": split.rate_str,
                "platform_fee_cents": split.platform_fee_cents,
                "tenant_settlement_cents": split.tenant_settlement_cents,
            },
        )

    @staticmethod
    def _bind_tenant(order: Order) -> None:
        """Stamp the order with the current tenant (cross-tenant guard)."""
        if order.tenant_id:
            return
        tenant = current_tenant_or_none()
        if tenant is not None:
            order.tenant_id = tenant.tenant_id
            if not order.branch_id:
                order.branch_id = tenant.tenant.branch_id
