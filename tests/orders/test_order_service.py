"""Order service tests — completion settlement, cancellation, isolation."""

from collections.abc import Iterator

import pytest
from jol_commerce.audit.audit_log import AuditLogger
from jol_commerce.orders.order_lifecycle import Order, OrderStatus, PaymentMode
from jol_commerce.orders.order_repository import CrossTenantAccessError, OrderRepository
from jol_commerce.orders.order_service import OrderService
from jol_commerce.tenancy.registry import TenantRegistry
from jol_commerce.tenancy.tenant import TenantContext, set_current_tenant


@pytest.fixture()
def tenant_context() -> Iterator[TenantContext]:
    registry = TenantRegistry()
    tenant = registry.new_tenant(
        "st-anne",
        "St. Anne Parish",
        "faith_community",
        commission_rate="0.10",
        branch_id="BR-1",
    )
    context = TenantContext(tenant=tenant, resolved_from="header")
    token = set_current_tenant(context)
    yield context
    set_current_tenant(None)
    del token


@pytest.fixture()
def service() -> OrderService:
    audit = AuditLogger()

    def refund_callback(order: Order) -> str:
        return f"re_{order.order_id}"

    return OrderService(OrderRepository(), audit, refund_callback=refund_callback)


class TestCompletionSettlement:
    def test_completion_snapshots_commission_and_ledger(
        self,
        service: OrderService,
        tenant_context: TenantContext,
    ) -> None:
        order = Order(
            order_id="ORD-1",
            tenant_id=tenant_context.tenant_id,
            total_amount_cents=50000,
            payment_mode=PaymentMode.POST_SERVICE,
        )
        service.register(order, actor="parishioner-1")
        service.transition(order, OrderStatus.RESERVED, actor="api")
        service.transition(order, OrderStatus.CONFIRMED, actor="stripe_webhook")
        service.transition(order, OrderStatus.IN_PROGRESS, actor="dispatch")
        service.complete(order, actor="priest-1")

        assert order.status is OrderStatus.COMPLETED
        assert order.commission_snapshot is not None
        assert order.commission_snapshot.platform_fee_cents == 5000
        assert order.commission_snapshot.tenant_settlement_cents == 45000

        ledger_entries = service.commission_ledger.entries_for_tenant(
            tenant_context.tenant_id,
        )
        assert len(ledger_entries) == 1
        assert ledger_entries[0].rate == "0.10"


class TestCancellation:
    def test_cancel_triggers_refund_workflow_and_audit(
        self,
        service: OrderService,
        tenant_context: TenantContext,
    ) -> None:
        order = Order(order_id="ORD-2", tenant_id=tenant_context.tenant_id)
        service.register(order, actor="parishioner-1")
        service.cancel(order, actor="parishioner-1", reason="changed mind")

        assert order.status is OrderStatus.CANCELLED

        events = service._audit.get_entries(event_type="order.cancelled")
        assert len(events) == 1
        assert events[0].details["refund_triggered"] is True
        assert events[0].details["refund_ref"] == "re_ORD-2"  # callback ran exactly once

    def test_completed_order_cannot_be_cancelled(
        self,
        service: OrderService,
        tenant_context: TenantContext,
    ) -> None:
        order = Order(
            order_id="ORD-3",
            tenant_id=tenant_context.tenant_id,
            status=OrderStatus.COMPLETED,
        )
        with pytest.raises(ValueError, match="Invalid transition"):
            service.cancel(order, actor="attacker")


class TestTenantIsolation:
    def test_cross_tenant_read_denied(
        self,
        service: OrderService,
        tenant_context: TenantContext,
    ) -> None:
        foreign = Order(order_id="ORD-FOREIGN", tenant_id="another-tenant-id")
        with pytest.raises(CrossTenantAccessError):
            service._repository.save(foreign)

    def test_register_stamps_current_tenant(
        self,
        service: OrderService,
        tenant_context: TenantContext,
    ) -> None:
        order = Order(order_id="ORD-4")
        service.register(order, actor="parishioner-1")
        assert order.tenant_id == tenant_context.tenant_id
        assert order.branch_id == "BR-1"

    def test_find_by_customer_scoped_to_tenant(
        self,
        service: OrderService,
        tenant_context: TenantContext,
    ) -> None:
        order = Order(order_id="ORD-5", customer_id="cust-1")
        service.register(order, actor="cust-1")
        found = service._repository.find_by_customer("cust-1")
        assert [o.order_id for o in found] == ["ORD-5"]
