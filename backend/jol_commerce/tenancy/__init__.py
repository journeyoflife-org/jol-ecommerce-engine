"""Multi-tenancy primitives — schema-per-tenant isolation (Blueprint v2.0 §2).

The public schema holds only the tenant registry; every tenant receives a
dedicated PostgreSQL schema with Row Level Security as defense-in-depth.
"""

from jol_commerce.tenancy.middleware import TenantResolutionMiddleware
from jol_commerce.tenancy.registry import TenantRegistry
from jol_commerce.tenancy.tenant import (
    Tenant,
    TenantContext,
    TenantNotFoundError,
    TenantVertical,
    current_tenant,
)

__all__ = [
    "Tenant",
    "TenantContext",
    "TenantNotFoundError",
    "TenantRegistry",
    "TenantResolutionMiddleware",
    "TenantVertical",
    "current_tenant",
]
