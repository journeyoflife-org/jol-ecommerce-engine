"""Commission engine + ledger tests (Blueprint §3.3)."""

import pytest
from jol_commerce.commissions.commission_engine import CommissionEngine
from jol_commerce.commissions.commission_ledger import CommissionLedger, LedgerEntry


class TestCommissionEngine:
    def test_default_rate_is_ten_percent(self) -> None:
        split = CommissionEngine().calculate(10000)
        assert split.platform_fee_cents == 1000
        assert split.tenant_settlement_cents == 9000
        assert split.rate_str == "0.10"

    def test_tenant_contract_rate_override(self) -> None:
        split = CommissionEngine().calculate(10000, tenant_rate="0.08")
        assert split.platform_fee_cents == 800
        assert split.tenant_settlement_cents == 9200

    def test_split_always_sums_to_gross(self) -> None:
        engine = CommissionEngine()
        for amount in (1, 333, 999, 10000, 123456):
            split = engine.calculate(amount, tenant_rate="0.10")
            assert split.platform_fee_cents + split.tenant_settlement_cents == amount

    def test_rounding_favours_tenant(self) -> None:
        """Fee truncates down; tenant keeps the remainder."""
        split = CommissionEngine().calculate(999)
        assert split.platform_fee_cents == 99  # floor(99.9)
        assert split.tenant_settlement_cents == 900

    def test_negative_amount_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            CommissionEngine().calculate(-1)

    def test_out_of_range_rate_rejected(self) -> None:
        with pytest.raises(ValueError, match="rate"):
            CommissionEngine().calculate(100, tenant_rate="1.5")


class TestCommissionLedger:
    def _entry(self, **overrides: object) -> LedgerEntry:
        base = {
            "tenant_id": "t-1",
            "order_id": "ORD-1",
            "currency": "EUR",
            "gross_amount_cents": 10000,
            "platform_fee_cents": 1000,
            "tenant_settlement_cents": 9000,
            "rate": "0.10",
        }
        base.update(overrides)
        return LedgerEntry(**base)  # type: ignore[arg-type]

    def test_unbalanced_entry_rejected(self) -> None:
        with pytest.raises(ValueError, match="unbalanced"):
            self._entry(platform_fee_cents=2000)

    def test_entries_are_immutable(self) -> None:
        entry = self._entry()
        with pytest.raises(AttributeError):
            entry.platform_fee_cents = 0  # type: ignore[misc]

    def test_tenant_scoped_queries(self) -> None:
        ledger = CommissionLedger()
        ledger.append(self._entry())
        ledger.append(self._entry(tenant_id="t-2", order_id="ORD-2"))
        assert len(ledger.entries_for_tenant("t-1")) == 1
        assert ledger.entry_count == 2

    def test_daily_reconciliation_balance(self) -> None:
        ledger = CommissionLedger()
        ledger.append(self._entry())
        ledger.append(self._entry(order_id="ORD-2"))
        totals = ledger.daily_reconciliation_balance("t-1")
        assert totals == {
            "gross_cents": 20000,
            "platform_fee_cents": 2000,
            "tenant_settlement_cents": 18000,
        }
