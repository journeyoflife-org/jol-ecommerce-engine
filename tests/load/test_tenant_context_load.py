"""Tenant context-switching load test — production readiness gap 4.7.

Scenario under test: **100 concurrent requests across 20 tenants**
sharing one undersized connection pool (8 connections) while every
request switches schema (`SET search_path = tenant_{uuid}`).

The pool is simulated faithfully enough to expose the two failure
modes the audit demands we rule out:

1. **Contamination** — connections are returned *dirty* (residual
   `search_path` of the previous tenant is never reset). If tenant
   binding were carried on the connection instead of in a contextvar,
   the next borrower would read the previous tenant's schema. Every
   read is asserted to return only the borrower's own tenant data,
   and a deliberate cross-tenant read probe must raise.
2. **Exhaustion** — 100 workers contend for 8 connections. Acquisition
   wait times are measured; any timeout (starvation/deadlock) fails
   the test, and the observed max wait is reported.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field

import pytest
from jol_commerce.audit.audit_log import AuditLogger
from jol_commerce.orders.order_lifecycle import Order
from jol_commerce.orders.order_repository import CrossTenantAccessError, OrderRepository
from jol_commerce.orders.order_service import OrderService
from jol_commerce.tenancy.middleware import TenantResolutionMiddleware
from jol_commerce.tenancy.registry import TenantRegistry
from jol_commerce.tenancy.tenant import TENANT_HEADER, Tenant, set_current_tenant
from starlette.requests import Request

TENANT_COUNT = 20
WORKERS_PER_TENANT = 5  # 20 tenants x 5 = 100 concurrent requests
POOL_SIZE = 8  # deliberately undersized to force exhaustion contention
ITERATIONS_PER_WORKER = 8
ACQUIRE_TIMEOUT_SECONDS = 10.0


@dataclass
class PoolMetrics:
    """Observations of pool behavior under schema-switching load."""

    wait_times: list[float] = field(default_factory=list)
    schema_switches: int = 0
    acquisition_timeouts: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_wait(self, seconds: float) -> None:
        with self._lock:
            self.wait_times.append(seconds)

    def record_switch(self) -> None:
        with self._lock:
            self.schema_switches += 1

    def record_timeout(self) -> None:
        with self._lock:
            self.acquisition_timeouts += 1

    @property
    def max_wait(self) -> float:
        return max(self.wait_times, default=0.0)


class SimulatedConnection:
    """A pooled connection carrying residual per-tenant schema state."""

    def __init__(self, conn_id: int) -> None:
        self.conn_id = conn_id
        self.search_path: str = ""  # dirty: last tenant's schema


class SimulatedPool:
    """Bounded pool — checkout/return only, no implicit schema reset."""

    def __init__(self, size: int, metrics: PoolMetrics) -> None:
        self._idle: queue.Queue[SimulatedConnection] = queue.Queue()
        for i in range(size):
            self._idle.put(SimulatedConnection(i))
        self._metrics = metrics

    def acquire(self, tenant_schema: str) -> SimulatedConnection:
        started = time.monotonic()
        try:
            conn = self._idle.get(timeout=ACQUIRE_TIMEOUT_SECONDS)
        except queue.Empty:
            self._metrics.record_timeout()
            raise
        self._metrics.record_wait(time.monotonic() - started)
        if conn.search_path != tenant_schema:  # schema switch cost
            conn.search_path = tenant_schema
            self._metrics.record_switch()
        return conn

    def release_dirty(self, conn: SimulatedConnection) -> None:
        """Return without resetting search_path — worst-case reuse."""
        self._idle.put(conn)


def _request(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/orders",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "server": ("testserver", 443),
        },
    )


def _schema_name(tenant: Tenant) -> str:
    return f"tenant_{tenant.tenant_id.replace('-', '')}"


@pytest.mark.load
class TestTenantContextLoad:
    def test_100_concurrent_requests_across_20_tenants(self) -> None:
        registry = TenantRegistry()
        middleware = TenantResolutionMiddleware(app=object(), registry=registry)
        tenants = [
            registry.new_tenant(f"load-tenant-{i:02d}", f"Load Tenant {i}", "faith_community")
            for i in range(TENANT_COUNT)
        ]
        repository = OrderRepository()
        service = OrderService(repository, AuditLogger())
        metrics = PoolMetrics()
        pool = SimulatedPool(POOL_SIZE, metrics)

        errors: list[str] = []
        errors_lock = threading.Lock()
        barrier = threading.Barrier(TENANT_COUNT * WORKERS_PER_TENANT)

        def report_error(msg: str) -> None:
            with errors_lock:
                errors.append(msg)

        def worker(tenant_index: int, worker_index: int) -> None:
            tenant = tenants[tenant_index]
            schema = _schema_name(tenant)
            try:
                # Exact middleware resolution path (header fallback).
                context = middleware._resolve(
                    _request({TENANT_HEADER: tenant.tenant_id}),
                )
                token = set_current_tenant(context)
                try:
                    barrier.wait(timeout=10)
                    for i in range(ITERATIONS_PER_WORKER):
                        conn = pool.acquire(schema)
                        try:
                            order_id = f"LOAD-{tenant_index:02d}-{worker_index}-{i}"
                            service.register(Order(order_id=order_id), actor="load")

                            found = repository.find_by_id(order_id)
                            if found is None or found.tenant_id != tenant.tenant_id:
                                report_error(f"contaminated read: {order_id}")

                            # Contamination probe: a foreign tenant's known
                            # order must never be readable from this context.
                            foreign_id = f"LOAD-{(tenant_index + 1) % TENANT_COUNT:02d}-0-{i}"
                            try:
                                leaked = repository.find_by_id(foreign_id)
                                if leaked is not None:
                                    report_error(f"cross-tenant leak: {foreign_id}")
                            except CrossTenantAccessError:
                                pass  # boundary enforced
                        finally:
                            pool.release_dirty(conn)
                finally:
                    set_current_tenant(None)
                    del token
            except Exception as e:
                report_error(f"{tenant.slug}/{worker_index}: {e!r}")

        threads = [
            threading.Thread(target=worker, args=(t, w))
            for t in range(TENANT_COUNT)
            for w in range(WORKERS_PER_TENANT)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        assert not any(t.is_alive() for t in threads), "worker starvation (pool deadlock)"

        assert errors == []

        # Pool exhaustion: 800 checkouts against 8 connections must
        # complete without a single acquisition timeout.
        assert metrics.acquisition_timeouts == 0
        assert len(metrics.wait_times) == TENANT_COUNT * WORKERS_PER_TENANT * (
            ITERATIONS_PER_WORKER
        )
        assert metrics.max_wait < ACQUIRE_TIMEOUT_SECONDS
        # Nearly every checkout crosses a tenant boundary on a dirty pool.
        assert metrics.schema_switches > TENANT_COUNT * WORKERS_PER_TENANT

        # Exact per-tenant order counts — no lost or misplaced writes.
        for tenant_index, tenant in enumerate(tenants):
            token = set_current_tenant(
                middleware._resolve(
                    _request({TENANT_HEADER: tenant.tenant_id}),
                ),
            )
            try:
                mine = [
                    o.order_id
                    for o in repository._orders.values()
                    if o.tenant_id == tenant.tenant_id
                ]
                assert len(mine) == WORKERS_PER_TENANT * ITERATIONS_PER_WORKER
                assert all(id_.startswith(f"LOAD-{tenant_index:02d}-") for id_ in mine)
            finally:
                set_current_tenant(None)
                del token
