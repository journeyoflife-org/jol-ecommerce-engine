# JOL Commerce Engine

PCI DSS SAQ A compliant e-commerce engine for Journey of Life, serving 27 EU countries with Baltic-state focus (Lithuania, Latvia, Estonia).

## Architecture

- **Backend**: Python 3.12, FastAPI, PostgreSQL
- **Frontend**: React 19, TypeScript, Vite
- **Payments**: Stripe Elements (tokenisation only — no raw card data on JOL servers)
- **VAT**: Decimal-precision calculation for all 27 EU countries
- **Audit**: Immutable hash-chained audit log (PCI DSS Req. 10)

## Cross-Plane Tenancy Contract (with jol-hub)

Per [ADR-001](docs/adr/ADR-001-tenancy-framework-divergence.md), tenancy is a
two-plane system: **jol-hub** (Django + django-tenants) is the tenant
management & admin plane that provisions tenant schemas; **this engine**
(FastAPI) is the data plane that assumes those schemas are isolation-hardened.

**The engine assumes — and cannot detect otherwise — that every tenant
schema created by the jol-hub migration runner carries the same RLS posture
as the engine's own provisioning path.** The source of truth is
[`backend/jol_commerce/db/sql/002_tenant_schema_template.sql`](backend/jol_commerce/db/sql/002_tenant_schema_template.sql);
the jol-hub runner must apply its full content to every new `tenant_{uuid}`
schema:

| Requirement | DDL |
|---|---|
| RLS enabled **and forced** on every tenant table (`orders`, `payment_tokens`, `commission_ledger`, and any future tenant-owned table) | `ALTER TABLE {t} ENABLE ROW LEVEL SECURITY; ALTER TABLE {t} FORCE ROW LEVEL SECURITY;` |
| Isolation policy per table, bound to the per-request session setting — never a literal | `CREATE POLICY tenant_isolation_{t} ON {t} USING (tenant_id = current_setting('app.current_tenant')::UUID);` |
| Append-only audit log | `BEFORE UPDATE`/`BEFORE DELETE` triggers on `audit_log` |

Notes:

- `FORCE` is mandatory: without it the table **owner** bypasses RLS, and a
  Django migration connection typically runs as that owner.
- A schema provisioned by Django **without** these policies is an isolation
  gap the engine cannot detect at runtime — its
  [`tests/security/test_rls_ddl_contract.py`](tests/security/test_rls_ddl_contract.py)
  guard only verifies the engine's own template, not live schemas. jol-hub
  must assert the live state after provisioning (e.g. query
  `pg_class.relrowsecurity`/`relforcerowsecurity` for every tenant table)
  and fail the provisioning transaction otherwise.
- Live leak testing of this contract is in the penetration-test scope
  ([`docs/penetration-test-scope.md`](docs/penetration-test-scope.md), PT-T series).

The identical contract is documented in the jol-hub README
(Database & Migrations → Tenant Schema Provisioning).

## Quick Start

```bash
# Install dependencies
make dev

# Configure environment
cp .env.example .env
# Edit .env with your values

# Run development server
make run

# Run tests
make test

# Run security checks
make security
```

## VAT Rates

| Country | Rate | Effective Date |
|---------|------|----------------|
| Lithuania (LT) | 21% | Current |
| Latvia (LV) | 21% | Current |
| Estonia (EE) | **24%** | Since 2025-07-01 |

See [docs/vat-matrix.md](docs/vat-matrix.md) for the full EU-27 matrix.

## PCI DSS Compliance

This project is designed for **SAQ A** eligibility:
- All card data collected via Stripe Elements hosted iframes
- No raw card data (PAN, CVV, expiry) touches JOL servers
- Script inventory and integrity verification (PCI Req. 6.4.3)
- HTTP header change monitoring (PCI Req. 11.6.1)
- 12-month audit log retention with tamper-evident hash chain

See [docs/pci-scope-statement.md](docs/pci-scope-statement.md) for full scope documentation.

## Project Structure

```
backend/jol_commerce/    Python backend (payments, tax, orders, audit, API)
frontend/src/            TypeScript frontend (payment, tax, shared)
tests/                   Test suites (unit, integration, tax, security, audit)
docs/                    Architecture, compliance, and operational documentation
compliance/              PCI, GDPR, tax, audit, and risk compliance records
scripts/                 Operational scripts (PAN verification, key rotation, reports)
```

## Prerequisites

- Python 3.12+
- Node.js 20 LTS
- PostgreSQL 15+
- Stripe account (test keys for development)

## License

MIT — see [LICENSE](LICENSE).
