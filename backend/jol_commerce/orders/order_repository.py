"""Order repository — tenant-scoped persistence layer for orders.

Blueprint v2.0 §3.4: orders live in the per-tenant schema, and RLS
policies enforce the tenant boundary even if application filters fail.
The in-memory implementation mirrors that contract: every query runs
within the tenant bound to the current request, and cross-tenant reads
raise instead of silently returning foreign data.
"""

from __future__ import annotations

from jol_commerce.orders.order_lifecycle import Order, OrderStatus
from jol_commerce.tenancy.tenant import TenantNotFoundError, current_tenant_or_none


class CrossTenantAccessError(PermissionError):
    """Raised when an order access crosses the tenant boundary."""


class OrderRepository:
    """Tenant-scoped order repository (production: schema-per-tenant DB)."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def save(self, order: Order) -> None:
        """Persist an order within its tenant schema."""
        self._check_tenant(order.tenant_id)
        self._orders[order.order_id] = order

    def find_by_id(self, order_id: str) -> Order | None:
        """Find an order by ID inside the current tenant boundary."""
        order = self._orders.get(order_id)
        if order is None:
            return None
        self._check_tenant(order.tenant_id)
        return order

    def find_by_customer(self, customer_id: str) -> list[Order]:
        """Find all orders for a customer (current tenant only)."""
        tenant_id = self._require_tenant_id()
        return [
            o
            for o in self._orders.values()
            if o.tenant_id == tenant_id and o.customer_id == customer_id
        ]

    def find_by_status(self, status: OrderStatus) -> list[Order]:
        """Find all orders with a given status (current tenant only)."""
        tenant_id = self._require_tenant_id()
        return [o for o in self._orders.values() if o.tenant_id == tenant_id and o.status == status]

    def changes_since(self, timestamp: str) -> list[Order]:
        """Orders updated after `timestamp` — Bitrix24 sync change feed (§4.3)."""
        tenant_id = self._require_tenant_id()
        return [
            o
            for o in self._orders.values()
            if o.tenant_id == tenant_id and o.updated_at and o.updated_at > timestamp
        ]

    @staticmethod
    def _require_tenant_id() -> str:
        tenant = current_tenant_or_none()
        if tenant is None:
            raise TenantNotFoundError("Order repository requires a bound tenant context")
        return tenant.tenant_id

    @staticmethod
    def _check_tenant(tenant_id: str) -> None:
        """Reject operations outside the bound tenant boundary."""
        tenant = current_tenant_or_none()
        if tenant is None:
            return  # non-request scopes (tests, batch jobs) manage scoping themselves
        if tenant_id and tenant_id != tenant.tenant_id:
            raise CrossTenantAccessError(
                "Cross-tenant order access denied (SOC2 CC6.2, Blueprint §2 RLS)",
            )
