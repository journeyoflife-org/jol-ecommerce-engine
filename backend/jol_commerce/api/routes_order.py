"""Order API routes — v2.0 lifecycle (Blueprint §3.3).

All routes run inside the tenant bound by TenantResolutionMiddleware;
orders are stamped with the current tenant and cannot cross boundaries.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from jol_commerce.api import state
from jol_commerce.api.schemas import (
    CreateOrderRequest,
    OrderResponse,
    OrderTransitionRequest,
)
from jol_commerce.orders.order_lifecycle import Order, OrderStatus, PaymentMode
from jol_commerce.tenancy.tenant import TenantContext, TenantNotFoundError, current_tenant

router = APIRouter()


@router.post("/", response_model=OrderResponse)
async def create_order(request: CreateOrderRequest) -> OrderResponse:
    """Create a new order inside the current tenant schema."""
    tenant = _require_tenant()
    order = Order(
        order_id=f"ORD-{uuid.uuid4().hex[:12]}",
        tenant_id=tenant.tenant_id,
        payment_mode=PaymentMode(request.payment_mode),
        customer_id=request.customer_id,
        items=[item.model_dump() for item in request.items],
        total_amount_cents=request.total_amount_cents,
        currency=request.currency,
        country_code=request.country_code,
        branch_id=tenant.tenant.branch_id,
        service_type=request.service_type,
    )
    state.order_service.register(order, actor=request.customer_id)
    return _to_response(order)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str) -> OrderResponse:
    """Retrieve an order by ID (tenant boundary enforced)."""
    order = state.order_repository.find_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return _to_response(order)


@router.post("/{order_id}/transition", response_model=OrderResponse)
async def transition_order(order_id: str, request: OrderTransitionRequest) -> OrderResponse:
    """Apply a lifecycle transition (reserved/confirmed/in_progress/...)."""
    order = _get_order_or_404(order_id)
    try:
        state.order_service.transition(
            order,
            OrderStatus(request.status),
            actor=request.actor,
            reason=request.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _to_response(order)


@router.post("/{order_id}/complete", response_model=OrderResponse)
async def complete_order(order_id: str, request: OrderTransitionRequest) -> OrderResponse:
    """Priest/caretaker completion confirmation — settles commission (§4.2)."""
    order = _get_order_or_404(order_id)
    try:
        state.order_service.complete(order, actor=request.actor, reason=request.reason)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _to_response(order)


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(order_id: str, request: OrderTransitionRequest) -> OrderResponse:
    """Cancel an order — triggers the refund workflow + audit entry (§3.3)."""
    order = _get_order_or_404(order_id)
    try:
        state.order_service.cancel(order, actor=request.actor, reason=request.reason)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return _to_response(order)


def _get_order_or_404(order_id: str) -> Order:
    order = state.order_repository.find_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


def _require_tenant() -> TenantContext:
    try:
        return current_tenant()
    except TenantNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def _to_response(order: Order) -> OrderResponse:
    snapshot = order.commission_snapshot
    return OrderResponse(
        order_id=order.order_id,
        tenant_id=order.tenant_id,
        status=order.status.value,
        payment_mode=order.payment_mode.value,
        total_amount_cents=order.total_amount_cents,
        currency=order.currency,
        external_id=order.external_id,
        commission_rate=snapshot.rate if snapshot else None,
        platform_fee_cents=snapshot.platform_fee_cents if snapshot else None,
    )
