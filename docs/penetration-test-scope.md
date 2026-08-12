# Penetration Test Scope — PCI DSS Requirement 11.3

## Requirement

PCI DSS v4.0.1 Requirement 11.3 mandates:
- Penetration testing at minimum **annually**
- Re-test after any **significant infrastructure change**
- Segmentation validation every **6 months** (if used for scope reduction)

## Test Scope

### Application Layer
- Payment API endpoints (`/api/v1/payments/*`)
- Webhook endpoint signature verification
- Authentication and authorization controls
- Input validation (especially payment method ID format)
- CSP header enforcement on payment pages

### Multi-Tenancy (cross-tenant access — MANDATORY, ADR-001)

Required by the custom-tenancy equivalence argument: with a hand-rolled
tenancy layer, the QSA evidence must include a penetration test that
specifically targets tenant isolation. Threat register:
[`docs/tenancy-threat-model.md`](tenancy-threat-model.md).

| Scenario | Attack | Expected result |
|----------|--------|-----------------|
| PT-T1 | Read another tenant's order by ID enumeration / direct object reference (authenticated as tenant A) | 404/403, audit entry, zero rows leaked |
| PT-T2 | Write with forged `tenant_id` / forged `X-JOL-Tenant-ID` / forged subdomain `Host` header | Request rejected (400) or `CrossTenantAccessError`; no foreign rows created |
| PT-T3 | Race: concurrent requests for different tenants against the shared connection pool (worker reuse, stale tenant context) | No context bleed; every response scoped to its own tenant |
| PT-T4 | Bypass application guards: connect directly to PostgreSQL with the app role (or owner role), query across schemas with/without `app.current_tenant` set | RLS (`FORCE`) returns zero foreign rows; writes without the setting denied |
| PT-T5 | Schema-name injection via crafted tenant identifiers | Identifier validation rejects; no SQL execution outside `tenant_{uuid-hex}` |

The live-database variants (PT-T4, PT-T5) require a staging PostgreSQL
provisioned from `backend/jol_commerce/db/sql/` artifacts.

### Network Layer
- CDE perimeter (payment service network segment)
- Segmentation between CDE and non-CDE networks
- TLS configuration (1.2+ enforcement, weak cipher rejection)
- Firewall rules and access controls

### Infrastructure
- Cloud hosting environment (AWS eu-central-1)
- Database access controls
- Secrets management (Stripe keys, webhook secrets)
- Deployment pipeline security

## Pre-Go-Live Checklist

- [ ] Penetration test scope defined and approved
- [ ] Qualified penetration tester engaged (internal or third-party)
- [ ] Test completed with findings documented
- [ ] Critical/high findings remediated
- [ ] Re-test of remediated findings passed
- [ ] Report signed and filed in `compliance/pci/pentest-evidence/`

## Schedule

| Test | Due Date | Status |
|------|----------|--------|
| Initial pre-go-live | Before production launch | Pending |
| Annual re-test | 12 months from initial | Pending |
| Segmentation validation | 6 months from initial | Pending |
