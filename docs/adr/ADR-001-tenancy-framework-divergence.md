# ADR-001: Tenancy Framework Divergence — FastAPI Engine vs Blueprint §3.3 Django/django-tenants

**Status:** Accepted
**Date:** 2026-08-12
**Deciders:** Engineering, Security, Compliance (DPO/QSA review pending)
**Blueprint:** JOL Multi-Tenant Service-Commerce Platform, High-Level Architecture Blueprint v2.0
**Related:** `docs/architecture.md`, `backend/jol_commerce/db/sql/001_public_tenant_registry.sql`,
`backend/jol_commerce/db/sql/002_tenant_schema_template.sql`

## Context

Blueprint v2.0 §3.3 mandates the application core be built on **Django 5.1 +
Django REST Framework + `django-tenants`** with PostgreSQL schema-per-tenant.
The JOL Commerce Engine (`jol-ecommerce-engine`) is instead a **FastAPI**
service whose runtime tenancy is implemented with contextvars-bound tenant
contexts, tenant-scoped repositories, and SQL artifacts describing the
schema-per-tenant + RLS production contract.

This divergence was flagged during component-by-component validation of the
v2.0 refactor as requiring immediate attention.

Relevant facts:

1. Blueprint Next Steps §1 places the `django-tenants` scaffolding at
   `/opt/jol/repos/jol-hub/backend/django` — a separate repository that
   already contains the Django project scaffold (`core/`, `apps/organizations`,
   `apps/crm`, `apps/financial`). As of this ADR, `django-tenants` is **not
   yet** introduced there.
2. The Commerce Engine predates the blueprint, is SAQ-A scoped, and carries a
   hardened test baseline (141 tests: PCI Zero-PAN, VAT, security, audit
   integrity, tenancy).
3. Re-platforming the engine onto Django would duplicate the jol-hub
   scaffolding obligation and re-open the PCI-scoped payment surface to
   change during the same work stream.

## Decision

The Commerce Engine **retains the FastAPI runtime**. The blueprint's
schema-per-tenant mandate is satisfied through a layered equivalence strategy,
and the `django-tenants` obligation remains assigned to `jol-hub`.

**Adopted topology — two planes (accepted 2026-08-12):**

- **FastAPI Commerce Engine (this repo)** — high-throughput data plane:
  order placement, payments, notifications, Bitrix24 sync.
- **Django `jol-hub` (`django-tenants`)** — tenant management & admin plane:
  tenant onboarding, schema provisioning, staff admin, Bitrix24
  configuration. Runs `migrate_schemas` and owns `public.tenants`.
- **Hub ↔ Engine** — internal API over **mTLS**; the engine re-resolves the
  tenant on every request and never trusts caller-supplied schema names.
- **Schema provisioning on the engine plane** — `jol_commerce.db.provisioning`
  provides the tested `migrate_schemas` equivalent (create / migrate /
  rollback with per-schema `jol_schema_meta` bookkeeping), satisfying
  production-readiness condition 1 below.

### Production-readiness conditions for the FastAPI tenancy layer

1. **Schema provisioning automation** — delivered:
   `jol_commerce.db.provisioning.SchemaProvisioner` + CLI, covered by
   `tests/db/test_schema_provisioning.py` (creation from DDL template,
   ordered idempotent migration, per-tenant failure isolation, rollback
   via explicit down artifacts).
2. **Tenant isolation regression coverage** — delivered:
   cross-tenant read/write denial (`tests/orders/test_order_service.py`),
   RLS/DDL contract (`tests/security/test_rls_ddl_contract.py`), and the
   concurrent connection-pool race (`tests/tenancy/test_concurrent_isolation.py`).
3. **QSA documentation** — delivered: this ADR,
   `docs/tenancy-threat-model.md` (threats T1–T9), and the mandatory
   cross-tenant scenarios PT-T1…PT-T5 in `docs/penetration-test-scope.md`.
   The penetration test report remains **pending execution**.

### Equivalence mapping (Blueprint requirement → Engine control)

| Blueprint requirement | Engine control | Verification |
|-----------------------|----------------|--------------|
| Schema-per-tenant isolation (§3.4) | `Tenant.schema_name = tenant_{uuid-hex}`; request-scoped `contextvars` binding set/reset by `TenantResolutionMiddleware` | `tests/tenancy/test_tenant_resolution.py`, `tests/orders/test_order_service.py` |
| Tenant resolution: subdomain primary, `X-JOL-Tenant-ID` fallback (§3.2) | `TenantResolutionMiddleware`; fail-closed HTTP 400 on unknown/deactivated tenants; health, metrics, and gateway-webhook paths exempt | `tests/tenancy/test_tenant_resolution.py` |
| RLS defense-in-depth (§3.4) | `002_tenant_schema_template.sql`: `ENABLE ROW LEVEL SECURITY` + `FORCE` policies on `orders`, `payment_tokens`, `commission_ledger` keyed on `current_setting('app.current_tenant')::UUID` | DDL artifact; enforced at PostgreSQL provisioning |
| Application-layer tenant boundary | `OrderRepository` raises `TenantNotFoundError` on unbound-context queries and `CrossTenantAccessError` on cross-tenant access (SOC2 CC6.2) | `tests/orders/test_order_service.py::TestTenantIsolation` |
| Public tenant registry (§3.4) | `001_public_tenant_registry.sql`; in-memory `TenantRegistry` mirrors the contract (register/lookup/deactivate, duplicate rejection) | `tests/tenancy/test_tenant_resolution.py` |
| Immutable tenant audit trail (§2) | Hash-chained `AuditLogger` + `enforce_audit_append_only()` trigger in the schema template | `tests/audit/test_audit_log_integrity.py` |

### Disclosed residual gap

`OrderRepository.save()` permits writes when **no** tenant context is bound
(non-request scopes: tests, batch jobs manage scoping themselves). In the
PostgreSQL deployment this gap is closed by RLS `FORCE`, which denies writes
without a valid `app.current_tenant` setting regardless of application state.
Until RLS is live, all batch jobs MUST bind a tenant context explicitly.

## Consequences

- `jol-hub/backend/django` MUST introduce `django-tenants` per Blueprint Next
  Steps §1. The hub owns tenant-facing application surfaces; the Commerce
  Engine operates as a tenant-scoped domain service.
- When the hub is tenancy-aware, engine calls MUST carry the resolved tenant
  (signed tenant assertion or `X-JOL-Tenant-ID` from the hub's middleware) so
  that engine-side resolution and hub-side `search_path` agree on one tenant
  per request.
- Before production cutover, the in-memory repositories are replaced by the
  PostgreSQL implementations executing the SQL artifacts, at which point RLS
  becomes the authoritative enforcement layer and the residual gap above
  closes.
- QSA/DPO review of this ADR is required before the SOC2 Type II evidence
  window, since the equivalence argument substitutes framework-level
  multi-tenancy (`django-tenants`) with application + database controls.

## Alternatives Considered

1. **Full Django/django-tenants re-platform of the engine** — rejected:
   duplicates the jol-hub scaffolding, re-opens the PCI-scoped payment surface
   to change, and provides no isolation guarantee beyond what RLS + guarded
   repositories already deliver.
2. **Merge the engine into jol-hub as a Django app** — deferred: viable
   long-term once `django-tenants` lands in the hub; requires its own ADR and
   PCI re-scoping assessment.
3. **Keep the divergence undocumented** — rejected: violates SOC2 CC7.1 change
   management and blueprint conformance reporting.

## Review Schedule

Re-evaluate when `django-tenants` is introduced in `jol-hub`, and at every
annual architecture review thereafter.
