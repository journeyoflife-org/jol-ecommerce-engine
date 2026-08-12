"""Commission reversal edge cases — chargebacks, partial refunds, currency (gap 4.5)."""

from dataclasses import dataclass

import pytest
from jol_commerce.audit.audit_log import AuditLogger
from jol_commerce.commissions.commission_engine import CommissionEngine, CommissionSplit
from jol_commerce.orders.order_lifecycle import Order, OrderStatus, PaymentMode
from jol_commerce.orders.order_repository import OrderRepository
from jol_commerce.orders.order_service import OrderService
from jol_commerce.tenancy.registry import TenantRegistry
from jol_commerce.tenancy.tenant import TenantContext, set_current_tenant


@dataclass(frozen=True)
class SettledOrderCase:
    """OrderService plus the one completed, commission-settled order it holds."""

    service: OrderService
    order: Order


@pytest.fixture()
def settled_order() -> SettledOrderCase:
    """OrderService with one completed, commission-settled 500.00 EUR order."""
    registry = TenantRegistry()
    tenant = registry.new_tenant("st-anne", "St. Anne", "faith_community")
    token = set_current_tenant(TenantContext(tenant=tenant, resolved_from="header"))
    try:
        service = OrderService(OrderRepository(), AuditLogger())
        order = Order(
            order_id="ORD-REV",
            tenant_id=tenant.tenant_id,
            total_amount_cents=50000,
            payment_mode=PaymentMode.ONLINE_PREPAY,
        )
        service.register(order, actor="api")
        service.transition(order, OrderStatus.RESERVED, actor="api")
        service.transition(order, OrderStatus.CONFIRMED, actor="stripe_webhook")
        service.transition(order, OrderStatus.IN_PROGRESS, actor="dispatch")
        service.complete(order, actor="priest-1")
        return SettledOrderCase(service=service, order=order)
    finally:
        set_current_tenant(None)
        del token


class TestEngineReversalMath:
    def test_full_reversal_is_exact_negation_source(self) -> None:
        split = CommissionEngine().calculate(50000)
        reversal = CommissionEngine.reverse(split)
        assert reversal.platform_fee_cents == 5000
        assert reversal.tenant_settlement_cents == 45000
        assert reversal.gross_amount_cents == 50000

    def test_partial_refund_adjusts_proportionally(self) -> None:
        split = CommissionEngine().calculate(50000)  # fee 5000
        reversal = CommissionEngine.reverse(split, fraction="0.5")
        assert reversal.gross_amount_cents == 25000
        assert reversal.platform_fee_cents == 2500
        assert reversal.tenant_settlement_cents == 22500

    def test_rounding_stays_balanced_on_odd_amounts(self) -> None:
        """ROUND_DOWN on gross and fee independently keeps fee+settlement==gross."""
        split = CommissionEngine().calculate(33333)  # fee 3333
        reversal = CommissionEngine.reverse(split, fraction="0.5")
        assert reversal.gross_amount_cents == 16666
        assert reversal.platform_fee_cents == 1666  # floor(3333 * 0.5)
        assert reversal.tenant_settlement_cents == 15000
        assert reversal.platform_fee_cents + reversal.tenant_settlement_cents == (
            reversal.gross_amount_cents
        )

    def test_reversal_preserves_contract_rate(self) -> None:
        split = CommissionEngine().calculate(10000, tenant_rate="0.08")
        assert CommissionEngine.reverse(split).rate_str == "0.08"

    @pytest.mark.parametrize("fraction", ["0", "-0.1", "1.01", "2"])
    def test_invalid_fraction_rejected(self, fraction: str) -> None:
        split = CommissionSplit(
            rate=CommissionEngine().calculate(1).rate,
            gross_amount_cents=100,
            platform_fee_cents=10,
            tenant_settlement_cents=90,
        )
        with pytest.raises(ValueError, match="fraction"):
            CommissionEngine.reverse(split, fraction=fraction)


class TestLedgerCorrectionFlow:
    def test_chargeback_full_reversal_nets_ledger_to_zero(
        self,
        settled_order: SettledOrderCase,
    ) -> None:
        entry = settled_order.service.record_commission_reversal(
            settled_order.order,
            actor="stripe_dispute",
            reason="chargeback",
        )

        assert entry.gross_amount_cents == -50000
        assert entry.platform_fee_cents == -5000
        balance = settled_order.service.commission_ledger.daily_reconciliation_balance(
            settled_order.order.tenant_id,
        )
        assert balance["gross_cents"] == 0
        assert balance["platform_fee_cents"] == 0
        assert balance["tenant_settlement_cents"] == 0
        # Append-only: both settlement and reversal entries exist.
        assert settled_order.service.commission_ledger.entry_count == 2

    def test_partial_refund_reverses_proportionally(
        self,
        settled_order: SettledOrderCase,
    ) -> None:
        settled_order.service.record_commission_reversal(
            settled_order.order,
            actor="support",
            fraction="0.5",
        )

        balance = settled_order.service.commission_ledger.daily_reconciliation_balance(
            settled_order.order.tenant_id,
        )
        assert balance["platform_fee_cents"] == 2500  # 5000 - 2500
        assert balance["tenant_settlement_cents"] == 22500

    def test_reversal_inherits_settlement_currency_no_fx(
        self,
        settled_order: SettledOrderCase,
    ) -> None:
        """USD-settled orders reverse in USD — the engine never converts."""
        settled_order.order.currency = "usd"
        entry = settled_order.service.record_commission_reversal(
            settled_order.order,
            actor="stripe_dispute",
        )
        assert entry.currency == "usd"

    def test_reversal_without_settlement_rejected(
        self,
        settled_order: SettledOrderCase,
    ) -> None:
        unsettled = Order(order_id="ORD-NEW", tenant_id="t-x")
        with pytest.raises(ValueError, match="no settled commission"):
            settled_order.service.record_commission_reversal(unsettled, actor="attacker")

    def test_reversal_is_audited(self, settled_order: SettledOrderCase) -> None:
        settled_order.service.record_commission_reversal(
            settled_order.order,
            actor="stripe_dispute",
        )
        events = settled_order.service._audit.get_entries(
            event_type="commission.reversed",
        )
        assert len(events) == 1
        assert events[0].details["fraction"] == "1"
