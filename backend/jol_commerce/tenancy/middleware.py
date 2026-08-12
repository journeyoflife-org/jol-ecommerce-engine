"""Tenant resolution middleware (Blueprint v2.0 §3.2).

Resolution order:
1. Primary — subdomain: `https://{tenant-slug}.journeyoflife.org`
   → lookup in the tenant registry → bind tenant context.
2. Fallback — `X-JOL-Tenant-ID` header for API clients.

Requests that cannot be resolved to an active tenant are rejected with
400 — the platform never serves traffic outside an explicit tenant
boundary (defense against cross-tenant leakage, SOC2 CC6.2).

Paths exempt from tenant resolution (gateway/ops endpoints):
`/health`, `/metrics`, `/api/v1/payments/webhooks/*`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from jol_commerce.tenancy.tenant import (
    TENANT_HEADER,
    TenantContext,
    TenantNotFoundError,
    set_current_tenant,
)

if TYPE_CHECKING:
    from starlette.middleware.base import RequestResponseEndpoint
    from starlette.requests import Request
    from starlette.responses import Response

    from jol_commerce.tenancy.registry import TenantRegistry

# Platform apex domain for subdomain resolution.
APEX_DOMAIN = "journeyoflife.org"

# Paths that must resolve without a tenant (infra + gateway callbacks).
EXEMPT_PATH_PREFIXES = ("/health", "/metrics", "/api/v1/payments/webhooks")


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Bind a tenant context to every tenant-scoped request."""

    def __init__(self, app: object, registry: TenantRegistry) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._registry = registry

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path.startswith(EXEMPT_PATH_PREFIXES):
            return await call_next(request)

        try:
            context = self._resolve(request)
        except TenantNotFoundError as e:
            return JSONResponse(status_code=400, content={"detail": str(e)})

        token = set_current_tenant(context)
        try:
            return await call_next(request)
        finally:
            set_current_tenant(None)
            del token

    def _resolve(self, request: Request) -> TenantContext:
        """Resolve the tenant from subdomain, then header fallback."""
        tenant = None
        resolved_from = ""

        slug = self._subdomain_slug(request)
        if slug:
            tenant = self._registry.get_by_slug(slug)
            resolved_from = "subdomain"
        else:
            tenant_id = request.headers.get(TENANT_HEADER, "")
            if not tenant_id:
                raise TenantNotFoundError(
                    "Tenant not resolvable: no tenant subdomain and "
                    f"no {TENANT_HEADER} header provided",
                )
            tenant = self._registry.get_by_id(tenant_id)
            resolved_from = "header"

        if not tenant.is_active:
            raise TenantNotFoundError(f"Tenant is deactivated: {tenant.slug}")
        return TenantContext(tenant=tenant, resolved_from=resolved_from)

    @staticmethod
    def _subdomain_slug(request: Request) -> str:
        """Extract the tenant slug from the request Host, if any."""
        host = request.url.hostname or ""
        if host.endswith(f".{APEX_DOMAIN}"):
            return host.removesuffix(f".{APEX_DOMAIN}").split(".")[-1]
        return ""
