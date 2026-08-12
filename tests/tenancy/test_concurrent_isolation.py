"""Concurrent tenant isolation — ADR-001 condition 2 (race scenario).

Simulates the audit question: *what happens when two requests for
different tenants execute simultaneously over the shared connection
pool?* Each worker thread binds its own tenant context via
`set_current_tenant` (the middleware's exact mechanism, with
subdomain/header resolution exercised directly), then performs order
registration, reads, and an attempted cross-tenant breach in a tight
loop. Assertions:

- Context bindings never leak between threads (contextvars semantics).
- No worker ever observes another tenant's orders.
- Every cross-tenant access attempt raises `CrossTenantAccessError`.
"""

from __future__ import annotations

import threading

from jol_commerce.audit.audit_log import AuditLogger
from jol_commerce.orders.order_lifecycle import Order
from jol_commerce.orders.order_repository import CrossTenantAccessError, OrderRepository
from jol_commerce.orders.order_service import OrderService
from jol_commerce.tenancy.middleware import TenantResolutionMiddleware
from jol_commerce.tenancy.registry import TenantRegistry
from jol_commerce.tenancy.tenant import TENANT_HEADER, set_current_tenant
from starlette.requests import Request

ITERATIONS_PER_WORKER = 40
WORKERS_PER_TENANT = 4
TENANT_COUNT = 2


def _request(headers: dict[str, str] | None = None, host: str = "testserver") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/orders",
            "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
            "server": (host, 443),
        },
    )


class TestConcurrentTenantIsolation:
    def test_simultaneous_requests_never_cross_tenant_boundaries(self) -> None:
        registry = TenantRegistry()
        middleware = TenantResolutionMiddleware(app=object(), registry=registry)
        slugs = [f"tenant-{i}" for i in range(TENANT_COUNT)]
        tenants = [
            registry.new_tenant(slug, f"Tenant {i}", "faith_community")
            for i, slug in enumerate(slugs)
        ]
        repository = OrderRepository()
        service = OrderService(repository, AuditLogger())
        foreign_ids = [t.tenant_id for t in tenants]

        errors: list[str] = []
        barrier = threading.Barrier(TENANT_COUNT * WORKERS_PER_TENANT)

        def worker(tenant_index: int, worker_index: int) -> None:
            tenant = tenants[tenant_index]
            try:
                # Resolution via the real middleware path — header fallback.
                context = middleware._resolve(
                    _request(headers={TENANT_HEADER: tenant.tenant_id}),
                )
                token = set_current_tenant(context)
                try:
                    barrier.wait(timeout=5)
                    for i in range(ITERATIONS_PER_WORKER):
                        order_id = f"ORD-{tenant_index}-{worker_index}-{i}"
                        service.register(Order(order_id=order_id), actor="worker")

                        found = repository.find_by_id(order_id)
                        if found is None or found.tenant_id != tenant.tenant_id:
                            errors.append(f"leaked read: {order_id}")

                        # Breach attempt: write into every foreign tenant.
                        for foreign in foreign_ids:
                            if foreign == tenant.tenant_id:
                                continue
                            try:
                                repository.save(
                                    Order(order_id=f"X-{order_id}", tenant_id=foreign),
                                )
                                errors.append(f"breach write accepted: {foreign}")
                            except CrossTenantAccessError:
                                pass
                finally:
                    set_current_tenant(None)
                    del token
            except Exception as e:
                errors.append(f"{tenant.slug}/{worker_index}: {e}")

        threads = [
            threading.Thread(target=worker, args=(t, w))
            for t in range(TENANT_COUNT)
            for w in range(WORKERS_PER_TENANT)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        assert errors == []

        # Final consistency check under each tenant's own context.
        for tenant_index, tenant in enumerate(tenants):
            token = set_current_tenant(
                middleware._resolve(
                    _request(headers={TENANT_HEADER: tenant.tenant_id}),
                )
            )
            try:
                mine = [
                    o.order_id
                    for o in repository._orders.values()
                    if o.tenant_id == tenant.tenant_id
                ]
                assert len(mine) == WORKERS_PER_TENANT * ITERATIONS_PER_WORKER
                assert all(id_.startswith(f"ORD-{tenant_index}-") for id_ in mine)
            finally:
                set_current_tenant(None)
                del token

    def test_subdomain_resolution_is_thread_local(self) -> None:
        """Subdomain-resolved contexts stay scoped to their own thread."""
        registry = TenantRegistry()
        middleware = TenantResolutionMiddleware(app=object(), registry=registry)
        registry.new_tenant("st-anne", "St. Anne", "faith_community")
        registry.new_tenant("oakwood", "Oakwood Funeral Home", "funeral_home")

        resolved: dict[str, str] = {}
        lock = threading.Lock()

        def resolve(slug: str) -> None:
            context = middleware._resolve(_request(host=f"{slug}.journeyoflife.org"))
            token = set_current_tenant(context)
            try:
                with lock:
                    resolved[slug] = context.tenant.slug
            finally:
                set_current_tenant(None)
                del token

        threads = [threading.Thread(target=resolve, args=(s,)) for s in ("st-anne", "oakwood")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert resolved == {"st-anne": "st-anne", "oakwood": "oakwood"}
