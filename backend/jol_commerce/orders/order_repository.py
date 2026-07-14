"""Order repository — persistence layer for orders."""

from __future__ import annotations

from jol_commerce.orders.order_lifecycle import Order, OrderStatus


class OrderRepository:
    """In-memory order repository (production: database-backed)."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def save(self, order: Order) -> None:
        """Persist an order."""
        self._orders[order.order_id] = order

    def find_by_id(self, order_id: str) -> Order | None:
        """Find an order by ID."""
        return self._orders.get(order_id)

    def find_by_customer(self, customer_id: str) -> list[Order]:
        """Find all orders for a customer."""
        return [o for o in self._orders.values() if o.customer_id == customer_id]

    def find_by_status(self, status: OrderStatus) -> list[Order]:
        """Find all orders with a given status."""
        return [o for o in self._orders.values() if o.status == status]
