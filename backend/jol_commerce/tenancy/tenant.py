"""Tenant entity and request-scoped tenant context.

Blueprint v2.0 §2 — Schema-per-Tenant Isolation:
- Each church/funeral home/cemetery-care provider receives a dedicated
  PostgreSQL schema (`tenant_{uuid}`).
- The `public` schema holds only the tenant registry and auth mappings.
- Tenant context is bound per-request and propagated via contextvars so
  repositories and audit logging always operate within the tenant boundary.
"""

from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass
from enum import Enum

# Percent rate charged to the tenant on completed orders (Blueprint §3.3).
DEFAULT_COMMISSION_RATE = "0.10"

# Request header fallback for API clients (Blueprint §3.2).
TENANT_HEADER = "X-JOL-Tenant-ID"


class TenantVertical(str, Enum):
    """Business verticals served by the platform (Blueprint §1)."""

    FAITH_COMMUNITY = "faith_community"  # Catholic, Protestant, Orthodox parishes
    FUNERAL_HOME = "funeral_home"  # Bereavement services, limited catalog
    CEMETERY_CARE = "cemetery_care"  # Grave cleaning, monument restoration


class TenantNotFoundError(LookupError):
    """Raised when tenant resolution fails (unknown slug or tenant ID)."""


@dataclass(frozen=True)
class Tenant:
    """A registered tenant (row in `public.tenants`).

    Attributes:
        tenant_id: Stable UUID — also names the schema (`tenant_{uuid}`).
        slug: Public subdomain label (`{slug}.journeyoflife.org`).
        name: Human-readable tenant name (never leaves tenant schema).
        vertical: Business vertical for catalog and UX role mapping.
        commission_rate: Contractual platform-fee rate, decimal string
            (default 10%, configurable per tenant contract — Blueprint §3.3).
        branch_id: Branch identifier propagated to Bitrix24 sync payloads.
        is_active: Soft-deactivation flag; inactive tenants reject requests.
    """

    tenant_id: str
    slug: str
    name: str
    vertical: TenantVertical
    commission_rate: str = DEFAULT_COMMISSION_RATE
    branch_id: str = ""
    is_active: bool = True

    @property
    def schema_name(self) -> str:
        """PostgreSQL schema dedicated to this tenant."""
        # UUID hex form keeps the identifier safe for SQL interpolation by
        # schema-per-tenant middleware (no user-supplied strings).
        return f"tenant_{uuid.UUID(self.tenant_id).hex}"


@dataclass(frozen=True)
class TenantContext:
    """Resolved tenant bound to the current request."""

    tenant: Tenant
    resolved_from: str  # "subdomain" | "header"

    @property
    def tenant_id(self) -> str:
        return self.tenant.tenant_id

    @property
    def schema_name(self) -> str:
        return self.tenant.schema_name


# Request-scoped tenant binding. Set by TenantResolutionMiddleware and read
# by repositories, the audit logger, and outbound sync clients.
_current_tenant: contextvars.ContextVar[TenantContext | None] = contextvars.ContextVar(
    "jol_current_tenant",
    default=None,
)


def set_current_tenant(context: TenantContext | None) -> contextvars.Token[TenantContext | None]:
    """Bind a tenant context to the current execution scope."""
    return _current_tenant.set(context)


def current_tenant() -> TenantContext:
    """Return the tenant bound to the current request.

    Raises:
        TenantNotFoundError: If no tenant context is bound. Callers must
            never operate outside an explicit tenant boundary.
    """
    context = _current_tenant.get()
    if context is None:
        raise TenantNotFoundError("No tenant context bound to this request")
    return context


def current_tenant_or_none() -> TenantContext | None:
    """Return the bound tenant context, or None (for optional paths)."""
    return _current_tenant.get()
