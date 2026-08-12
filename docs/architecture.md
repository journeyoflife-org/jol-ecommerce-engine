# Architecture — JOL Commerce Engine

## Overview

The JOL Commerce Engine is a multi-tenant, compliance-first service-commerce
platform aligned with the **JOL Multi-Tenant Service-Commerce Platform
High-Level Architecture Blueprint v2.0** (SOC2 Type II · GDPR 2016/679 ·
PCI DSS v4.0.1 · ISO 27001:2022). It serves three verticals — faith
communities, funeral homes, and cemetery care — across 27 EU countries with
Baltic-state focus (LT, LV, EE).

## System Architecture

```
Browser → CDN/Load Balancer → FastAPI Backend → PostgreSQL
         ↓                          ↓               (schema-per-tenant + RLS)
    Stripe Elements            Stripe API
    (hosted iframe)           (tokenised)      → Bitrix24 Box (prox01, one-way)
```

## Blueprint v2.0 Module Mapping

| Blueprint section | Requirement | Module |
|-------------------|-------------|--------|
| §3.2 Tenant resolution | Subdomain primary (`{slug}.journeyoflife.org`), `X-JOL-Tenant-ID` header fallback, fail-closed on unknown tenants | `jol_commerce.tenancy` (`tenant`, `registry`, `middleware`) |
| §3.4 Schema-per-tenant + RLS | `tenant_{uuid}` schemas, RLS on `current_setting('app.current_tenant')`, append-only audit triggers | `jol_commerce/db/sql/001_public_tenant_registry.sql`, `002_tenant_schema_template.sql`; `OrderRepository` cross-tenant guards mirror RLS |
| §3.3 Catalog governance | Vertical taxonomy: services + limited products per vertical | `jol_commerce.catalog` |
| §3.3 Order lifecycle | `draft → reserved → confirmed → in_progress → completed`, `cancelled` pre-completion (refund workflow + audit) | `jol_commerce.orders` (`order_lifecycle`, `order_service`) |
| §3.3 Payment modes | `online_prepay \| post_service \| in_person \| mixed` | `jol_commerce.orders.order_lifecycle.PaymentMode`, `jol_commerce.payments.payment_flows` |
| §3.3 Commission engine | 10% default, tenant-configurable, immutable ledger, settled on completion | `jol_commerce.commissions` (`commission_engine`, `commission_ledger`) |
| §3.5 Zero-PAN | Only gateway tokens stored (`pm_`/`seti_` IDs, receipt refs); raw PAN rejected at store boundary | `jol_commerce.payments.payment_token` |
| §3.5 Deferred charging | SetupIntent (`usage="off_session"`) → charge on completion confirmation | `stripe_client.create_setup_intent`, `charge_from_token`, `payment_flows.charge_deferred` |
| §3.6 Bitrix24 sync | One-way Django→Bitrix24, PII scrubber (GDPR Art. 9 fields removed), inbound writes rejected | `jol_commerce.bitrix24` (`pii_scrubber`, `sync_client`) |
| §3.7 Notification matrix | public→push/SMS/WhatsApp, internal→SMS/WhatsApp/email, confidential/restricted→encrypted email only; DLQ after 3 attempts; `notification_id`-only task payloads | `jol_commerce.notifications` (`classification`, `notification_service`) |
| §2 Immutable audit | Append-only, SHA-256 hash-chained, actor/action/entity/timestamp/IP/user-agent | `jol_commerce.audit.audit_log` |

## Known Blueprint Divergence

**Framework choice (Blueprint §3.3):** the blueprint mandates Django 5.1 +
`django-tenants`; this engine runs on FastAPI. The divergence is formally
accepted and governed by
[ADR-001: Tenancy Framework Divergence](adr/ADR-001-tenancy-framework-divergence.md).
Schema-per-tenant isolation is delivered through a layered equivalence —
contextvars-bound tenant contexts, tenant-scoped repositories (fail-closed on
unbound/cross-tenant access), and PostgreSQL RLS (`FORCE`) policies from the
tenant schema template as the authoritative enforcement layer. QSA/DPO
sign-off on ADR-001 is pending.

**Adopted two-plane topology:** this FastAPI engine is the high-throughput
**data plane** (orders, payments, notifications, Bitrix24 sync); `jol-hub`
(Django + `django-tenants`, Blueprint Next Steps §1) is the **tenant
management & admin plane** (onboarding, schema provisioning, staff admin,
Bitrix24 configuration). They communicate via internal API over mTLS.

**QSA evidence set for the custom tenancy layer:**
[threat model](tenancy-threat-model.md) ·
[cross-tenant pen-test scenarios](penetration-test-scope.md) ·
schema provisioning automation (`jol_commerce.db.provisioning`).

## Core Design Principles (Blueprint §2)

| Principle | Implementation |
|-----------|----------------|
| Schema-per-Tenant isolation | `Tenant.schema_name = tenant_{uuid-hex}`; contextvars-bound request scope; repository-level cross-tenant denial; SQL RLS policies for defense-in-depth |
| Zero-PAN policy | `PaymentTokenStore` rejects 13–19 digit numeric strings; only `pm_*`, `seti_*`, receipt refs persist |
| One-way Bitrix24 sync | `Bitrix24SyncClient.apply_inbound_write` always raises; scrubber removes `email`, `address`, `deceased_name` (special category), hashes `phone`, maps names to `Order-{external_id}` |
| Immutable audit trail | Hash chain `previous_hash → current_hash`; DB-level append-only trigger in tenant schema template |
| Defense-in-depth RLS | SQL policies on `orders`, `payment_tokens`, `commission_ledger` keyed on `app.current_tenant` |

## Technology Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React 19, TypeScript, Vite, Stripe Elements
- **Payments**: Stripe (SAQ A — tokenisation only)
- **Audit**: Append-only log with hash chain, SIEM integration
- **CI/CD**: GitHub Actions, CodeQL, Qodana

## PCI DSS Scope

- **SAQ A** eligible: card data never touches JOL servers
- Stripe Elements/Checkout collects all card data in hosted iframes
- Only tokenized payment method IDs (pm_xxx) are processed server-side
- In-person settlements store terminal `receipt_ref` only (Blueprint §3.5)

## Key Design Decisions

1. **Decimal arithmetic** for VAT and commission calculations (no floating-point);
   commission split uses ROUND_DOWN (tenant-favoured truncation)
2. **Hash-chained audit logs** for tamper detection
3. **CSP nonces** per-request for payment page script integrity
4. **Header monitoring** for PCI Req. 11.6.1 compliance
5. **Fail-closed tenancy**: unresolvable/inactive tenants rejected with HTTP 400;
   health, metrics, and gateway-webhook paths exempt from tenant resolution
