# Threat Model — Custom Tenancy Layer

**Scope:** `jol_commerce.tenancy`, tenant-scoped repositories, schema
provisioning, and the PostgreSQL RLS contract (Blueprint v2.0 §3.2/§3.4,
ADR-001).
**Audience:** QSA, SOC2 auditor, penetration testers.
**Last reviewed:** 2026-08-12

## 1. Assets

| Asset | Classification | Location |
|-------|----------------|----------|
| Orders, customer references | Confidential (GDPR Art. 9 adjacent) | `tenant_{uuid}` schema |
| Payment token references (`pm_`/`seti_`) | Restricted (Zero-PAN) | `tenant_{uuid}.payment_tokens` |
| Commission ledger | Confidential (financial) | `tenant_{uuid}.commission_ledger` |
| Audit trail | Internal, tamper-evident | `tenant_{uuid}.audit_log` |
| Tenant registry | Internal | `public.tenants` |

## 2. Trust Boundaries

1. **Edge → Engine:** tenant asserted by subdomain or `X-JOL-Tenant-ID`;
   resolution is fail-closed (HTTP 400) for unknown/deactivated tenants.
2. **Hub → Engine (future):** `jol-hub` (admin plane) will call the engine
   over internal mTLS, carrying the resolved tenant — the engine re-resolves
   and never trusts caller-supplied schema names.
3. **Engine → PostgreSQL:** every connection must set
   `app.current_tenant` and pin `search_path` to the tenant schema; RLS
   (`FORCE`) is the authoritative boundary.
4. **Engine → Bitrix24:** one-way, PII-scrubbed (see `bitrix24` module).

## 3. Threat Register

| ID | Threat | Vector | Mitigation | Verification |
|----|--------|--------|------------|--------------|
| T1 | Cross-tenant read | Forged/absent tenant header, direct object reference by order ID | Middleware fail-closed resolution; `OrderRepository.find_by_id` re-checks the bound tenant; RLS policy as backstop | `tests/orders/test_order_service.py::TestTenantIsolation`; pen-test scenario PT-T1 |
| T2 | Cross-tenant write | Caller supplies a foreign `tenant_id` on order creation | `register()` stamps the bound tenant; repository rejects mismatched `tenant_id` (`CrossTenantAccessError`); RLS `FORCE` | `test_order_service.py`; `tests/tenancy/test_concurrent_isolation.py`; PT-T2 |
| T3 | Tenant-context leakage under concurrency | Shared connection pool / worker reuse with stale contextvars | contextvars per-task binding, middleware resets binding in `finally`; repositories raise on unbound context for queries | `tests/tenancy/test_concurrent_isolation.py` (thread race simulation); PT-T3 |
| T4 | Tenant impersonation via subdomain | Attacker-controlled `Host` header | Registry lookup only resolves registered, active slugs; apex-domain suffix match; deactivated tenants rejected | `tests/tenancy/test_tenant_resolution.py` |
| T5 | Schema-name injection | Tenant ID interpolated into SQL identifiers | `schema_name` derived from `uuid.UUID(...).hex` (validated UUID, hex charset only); provisioner regex-rejects anything else | `tests/db/test_schema_provisioning.py` |
| T6 | Privileged bypass of RLS | Table owner/superuser connection ignoring policies | `FORCE ROW LEVEL SECURITY` on every tenant table; app role is non-owner in production provisioning | `tests/security/test_rls_ddl_contract.py`; PT-T4 |
| T7 | Audit tampering after breach | UPDATE/DELETE on `audit_log` to hide cross-tenant access | Append-only triggers; SHA-256 hash chain detects historical edits | `tests/audit/test_audit_log_integrity.py`; DDL contract test |
| T8 | Provisioning-time corruption | Failed migration leaves schema half-migrated | Per-schema `jol_schema_meta` bookkeeping; explicit down artifacts required for rollback; one tenant's failure never blocks others | `tests/db/test_schema_provisioning.py` |
| T9 | Unbound-context batch write | Background job runs without tenant binding (disclosed ADR-001 residual gap) | Jobs MUST bind a tenant explicitly; RLS `FORCE` denies writes without `app.current_tenant` once PostgreSQL is live | Operational control + RLS contract test |

## 4. Out of Scope / Deferred

- Live-database RLS leak test (requires PostgreSQL in CI or the annual
  penetration test — see `penetration-test-scope.md`, Multi-Tenancy section).
- Gateway-layer tenant assertion (Kong) — owned by the infrastructure repo.

## 5. Review Triggers

Re-model when: tenant resolution sources change, a new tenant-owned table is
added (must join the RLS contract test), `django-tenants` lands in `jol-hub`,
or after any pen-test finding in this scope.
