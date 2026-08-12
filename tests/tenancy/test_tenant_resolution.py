"""Tenancy tests — tenant resolution and isolation contracts (§3.2, §3.4)."""

import uuid

import pytest
from jol_commerce.tenancy.middleware import TenantResolutionMiddleware
from jol_commerce.tenancy.registry import TenantRegistry
from jol_commerce.tenancy.tenant import (
    TENANT_HEADER,
    Tenant,
    TenantNotFoundError,
    TenantVertical,
)
from starlette.requests import Request


@pytest.fixture()
def registry() -> TenantRegistry:
    reg = TenantRegistry()
    reg.new_tenant("st-anne", "St. Anne Parish", "faith_community", branch_id="BR-1")
    return reg


def _request(host: str = "testserver", tenant_header: str = "") -> Request:
    headers = [(b"host", host.encode())]
    if tenant_header:
        headers.append((TENANT_HEADER.lower().encode(), tenant_header.encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": headers,
        "query_string": b"",
    }
    return Request(scope)


class TestTenantRegistry:
    def test_register_and_resolve_by_slug(self, registry: TenantRegistry) -> None:
        tenant = registry.get_by_slug("st-anne")
        assert tenant.vertical is TenantVertical.FAITH_COMMUNITY
        assert tenant.branch_id == "BR-1"

    def test_resolve_unknown_slug_raises(self, registry: TenantRegistry) -> None:
        with pytest.raises(TenantNotFoundError):
            registry.get_by_slug("unknown")

    def test_duplicate_slug_rejected(self, registry: TenantRegistry) -> None:
        with pytest.raises(ValueError, match="slug"):
            registry.new_tenant("st-anne", "Duplicate", "funeral_home")

    def test_schema_name_is_uuid_derived(self, registry: TenantRegistry) -> None:
        tenant = registry.get_by_slug("st-anne")
        assert tenant.schema_name == f"tenant_{uuid.UUID(tenant.tenant_id).hex}"

    def test_default_commission_rate_is_ten_percent(self, registry: TenantRegistry) -> None:
        assert registry.get_by_slug("st-anne").commission_rate == "0.10"


class TestTenantResolutionMiddleware:
    def test_resolves_from_subdomain(self, registry: TenantRegistry) -> None:
        middleware = TenantResolutionMiddleware(app=None, registry=registry)
        context = middleware._resolve(_request(host="st-anne.journeyoflife.org"))
        assert context.resolved_from == "subdomain"
        assert context.tenant.slug == "st-anne"

    def test_resolves_from_header_fallback(self, registry: TenantRegistry) -> None:
        tenant = registry.get_by_slug("st-anne")
        middleware = TenantResolutionMiddleware(app=None, registry=registry)
        context = middleware._resolve(_request(tenant_header=tenant.tenant_id))
        assert context.resolved_from == "header"

    def test_unresolvable_request_rejected(self, registry: TenantRegistry) -> None:
        middleware = TenantResolutionMiddleware(app=None, registry=registry)
        with pytest.raises(TenantNotFoundError):
            middleware._resolve(_request())

    def test_deactivated_tenant_rejected(self, registry: TenantRegistry) -> None:
        tenant = registry.get_by_slug("st-anne")
        registry.register(
            Tenant(
                tenant_id=str(uuid.uuid4()),
                slug="closed-parish",
                name="Closed",
                vertical=TenantVertical.FAITH_COMMUNITY,
                is_active=False,
            )
        )
        middleware = TenantResolutionMiddleware(app=None, registry=registry)
        with pytest.raises(TenantNotFoundError, match="deactivated"):
            middleware._resolve(_request(host="closed-parish.journeyoflife.org"))
        assert tenant.is_active  # untouched
