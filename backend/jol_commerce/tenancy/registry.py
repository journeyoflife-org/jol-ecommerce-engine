"""Tenant registry — the application-side analog of `public.tenants`.

Blueprint v2.0 §3.4: the public schema holds only the tenant registry and
shared auth tables. In production this registry is backed by PostgreSQL
`public.tenants`; here the in-memory implementation keeps the resolution
contract testable without a database connection.
"""

from __future__ import annotations

import uuid

from jol_commerce.tenancy.tenant import Tenant, TenantNotFoundError


class TenantRegistry:
    """Registry of known tenants, addressable by slug or tenant UUID."""

    def __init__(self) -> None:
        self._by_id: dict[str, Tenant] = {}
        self._by_slug: dict[str, Tenant] = {}

    def register(self, tenant: Tenant) -> Tenant:
        """Register a tenant.

        Raises:
            ValueError: If the slug or tenant ID is already registered.
        """
        if tenant.tenant_id in self._by_id:
            raise ValueError(f"Tenant ID already registered: {tenant.tenant_id}")
        if tenant.slug in self._by_slug:
            raise ValueError(f"Tenant slug already registered: {tenant.slug}")
        self._by_id[tenant.tenant_id] = tenant
        self._by_slug[tenant.slug] = tenant
        return tenant

    def get_by_id(self, tenant_id: str) -> Tenant:
        """Resolve a tenant by UUID.

        Raises:
            TenantNotFoundError: If the tenant ID is unknown.
        """
        tenant = self._by_id.get(tenant_id)
        if tenant is None:
            raise TenantNotFoundError(f"Unknown tenant ID: {tenant_id}")
        return tenant

    def get_by_slug(self, slug: str) -> Tenant:
        """Resolve a tenant by subdomain slug.

        Raises:
            TenantNotFoundError: If the slug is unknown.
        """
        tenant = self._by_slug.get(slug)
        if tenant is None:
            raise TenantNotFoundError(f"Unknown tenant slug: {slug}")
        return tenant

    def new_tenant(
        self,
        slug: str,
        name: str,
        vertical: str,
        *,
        commission_rate: str | None = None,
        branch_id: str = "",
    ) -> Tenant:
        """Create and register a tenant with a generated UUID."""
        from jol_commerce.tenancy.tenant import TenantVertical

        kwargs: dict[str, object] = {
            "tenant_id": str(uuid.uuid4()),
            "slug": slug,
            "name": name,
            "vertical": TenantVertical(vertical),
            "branch_id": branch_id,
        }
        if commission_rate is not None:
            kwargs["commission_rate"] = commission_rate
        return self.register(Tenant(**kwargs))  # type: ignore[arg-type]

    @property
    def tenants(self) -> list[Tenant]:
        """All registered tenants (dispatcher read-only views)."""
        return list(self._by_id.values())
