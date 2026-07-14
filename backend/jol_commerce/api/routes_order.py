"""Order API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from jol_commerce.api.schemas import CreateOrderRequest, OrderResponse
from jol_commerce.orders.order_lifecycle import Order
from jol_commerce.orders.order_repository import OrderRepository

router = APIRouter()
_repository = OrderRepository()


@router.post("/", response_model=OrderResponse)
async def create_order(request: CreateOrderRequest) -> OrderResponse:
    """Create a new order."""
    order = Order(
        order_id=f"ORD-{id(request)}",
        customer_id=request.customer_id,
        items=[item.model_dump() for item in request.items],
        total_amount_cents=request.total_amount_cents,
        currency=request.currency,
        country_code=request.country_code,
    )
    _repository.save(order)
    return OrderResponse(
        order_id=order.order_id,
        status=order.status.value,
        total_amount_cents=order.total_amount_cents,
        currency=order.currency,
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str) -> OrderResponse:
    """Retrieve an order by ID."""
    order = _repository.find_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return OrderResponse(
        order_id=order.order_id,
        status=order.status.value,
        total_amount_cents=order.total_amount_cents,
        currency=order.currency,
    )
