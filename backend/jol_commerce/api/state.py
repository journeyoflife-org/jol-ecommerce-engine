"""Application state wiring — shared singletons for the API layer.

In production these are replaced by DI-provided, database-backed
implementations (schema-per-tenant repositories). The composition root
lives here so middleware and routers share one tenant registry, audit
chain, and order service.
"""

from __future__ import annotations

from jol_commerce.audit.audit_log import AuditLogger
from jol_commerce.orders.order_repository import OrderRepository
from jol_commerce.orders.order_service import OrderService
from jol_commerce.tenancy.registry import TenantRegistry

# Shared tenant registry — the public-schema analog (Blueprint §3.4).
tenant_registry = TenantRegistry()

# One audit chain per deployment; hash-chained and append-only.
audit_logger = AuditLogger()

order_repository = OrderRepository()

order_service = OrderService(order_repository, audit_logger)
