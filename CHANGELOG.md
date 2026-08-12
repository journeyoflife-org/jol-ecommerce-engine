# Changelog

All notable changes to the JOL Commerce Engine are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.2.0] — 2026-08-12

Closes the seven production-readiness gaps from the pre-deployment review
(4.1–4.7): tenant provisioning CLI, audit hash-chain verification, Bitrix24
network contract, webhook replay protection, commission reversal accounting,
notification key management, and tenant-context load testing.

### Added

- **Provisioning (4.1)**: `jol-cli tenant create --slug --name --vertical` —
  registers the tenant in `public.tenants`, creates the `tenant_{uuid}`
  schema from the DDL template, and seeds the vertical-governed starter
  catalog (deterministic IDs, idempotent re-seed); installed as the
  `jol-cli` console script. No new tenant requires manual DBA intervention
  (SOC2 CC7.1)
- **Catalog (4.1)**: `seed_default_catalog()` + `CatalogRepository.vertical`
  — one placeholder-priced service per permitted service type and one
  product per permitted SKU kind; seeding never blocks provisioning
- **Audit (4.2)**: `jol_commerce.audit.chain_verifier.verify_chain` — pure
  SHA-256 chain verifier with structured reports (first broken index/id,
  reason) and an optional head checkpoint that catches terminal-entry
  tampering; usable by the background job, the CLI, and tests alike
- **Audit (4.2)**: `jol-cli audit verify --export FILE [--head-hash HEX]` —
  verifies a JSONL audit export and exits non-zero with
  `TAMPERING DETECTED …` on any broken link
- **Payments (4.4)**: `WebhookEventStore` — webhook event-ID dedup table
  with a hard 24-hour minimum retention; `StripeWebhookHandler` claims
  events before dispatch (replays are acked + audited as `duplicate`,
  never reprocessed), and 200 returns to Stripe only after processing
  completes
- **Commissions (4.5)**: `CommissionEngine.reverse(split, fraction)` —
  proportional reversal math with Decimal ROUND_DOWN that keeps
  fee+settlement == gross; `OrderService.record_commission_reversal()`
  appends a negated ledger entry (append-only correction) for chargebacks
  and partial refunds, inheriting the settlement currency (no FX in engine),
  audited as `commission.reversed`
- **Tests (4.1)**: Catalog seeding — vertical governance, idempotency,
  deterministic IDs, currency propagation
- **Tests (4.2)**: Chain verifier — intact chain, historical-tamper
  detection at the successor, deletion detection, head-checkpoint terminal
  tamper, JSONL export round-trip
- **Tests (4.4)**: Webhook dedup — claim/replay semantics, retention floor
  enforcement, expiry purge, handler replay auditing
- **Tests (4.5)**: Commission reversals — exact-negation chargeback (ledger
  nets to zero, 2 append-only entries), 50% partial refund proportional
  split, odd-amount rounding balance, rate preservation, invalid-fraction
  rejection, unsettled-order rejection, currency inheritance, audit trail
- **Tests (4.7)**: `tests/load/test_tenant_context_load.py` (marked `load`)
  — 100 concurrent requests across 20 tenants against an 8-connection pool
  with dirty schema-switching reuse: zero cross-tenant contamination, zero
  acquisition timeouts (no exhaustion/starvation), measured wait times
- **Docs (4.3)**: `docs/bitrix24-sync-network.md` — prox01 (Dell R640)
  network contract: internal-only reachability via dedicated dispatch VLAN,
  mTLS client-certificate authentication, source-IP allowlist limited to
  the app servers, pre-cutover verification checklist
- **Docs (4.6)**: `docs/notification-key-management.md` — Vault KV v2 +
  Transit envelope scheme (`enc:v{kid}:…`), 90-day data-key rotation, and
  the dual-key drain window guaranteeing no dead notifications during
  rotation

### Changed

- **Provisioning**: `jol-cli` rewritten as the single operator entry point
  (`tenant create`, `create`, `migrate`, `downgrade`, `audit verify`);
  fail-closed without `JOL_DATABASE_URL`
- **Payments**: `StripeWebhookHandler` accepts an injectable
  `WebhookEventStore` (defaults to a fresh store with the mandatory
  24-hour retention)

[2.2.0]: https://github.com/journeyoflife-org/jol-commerce-engine/releases/tag/v2.2.0

## [2.1.0] — 2026-08-12

Closes the ADR-001 production-readiness conditions for the custom tenancy
layer and adopts the two-plane topology (FastAPI data plane + Django
`jol-hub` admin plane over mTLS).

### Added

- **Provisioning**: `jol_commerce.db.provisioning.SchemaProvisioner` — the
  tested `migrate_schemas` equivalent: tenant schema creation from the DDL
  template, ordered idempotent migration of all tenant schemas, per-tenant
  failure isolation, and rollback to any revision via explicit down
  artifacts (per-schema `jol_schema_meta` bookkeeping); CLI wrapper
  (`python -m jol_commerce.db.provisioning.cli`)
- **Tests**: Schema provisioning suite — creation, idempotency, ordering,
  cross-tenant failure isolation, rollback refusal without down artifacts
- **Tests**: RLS/DDL contract guard — every tenant table must carry
  `ENABLE` + `FORCE ROW LEVEL SECURITY` bound to
  `current_setting('app.current_tenant')`; audit append-only triggers
- **Tests**: Concurrent tenant isolation — 8-thread race simulation across
  2 tenants (register + read + breach attempts) with thread-local
  subdomain/header resolution
- **Docs**: `docs/tenancy-threat-model.md` — threat register T1–T9 for the
  custom tenancy layer (QSA artifact)
- **Docs**: Mandatory cross-tenant penetration test scenarios PT-T1…PT-T5
  in `docs/penetration-test-scope.md`

### Changed

- **ADR-001**: Adopted two-plane topology (FastAPI Commerce Engine = data
  plane; Django `jol-hub` with `django-tenants` = tenant management &
  admin plane; internal mTLS); production-readiness conditions tracked as
  delivered

[2.1.0]: https://github.com/journeyoflife-org/jol-commerce-engine/releases/tag/v2.1.0

## [2.0.0] — 2026-08-12

Refactor to the **Multi-Tenant Service-Commerce Blueprint v2.0**
(SOC2 Type II · GDPR 2016/679 · PCI DSS v4.0.1 · ISO 27001:2022).

### Added

- **Tenancy**: `Tenant` model with vertical taxonomy (`faith_community`,
  `funeral_home`, `cemetery_care`), tenant registry, and request-scoped
  context binding (contextvars) mirroring schema-per-tenant isolation
- **Tenancy**: `TenantResolutionMiddleware` — subdomain primary
  (`{slug}.journeyoflife.org`), `X-JOL-Tenant-ID` header fallback,
  fail-closed 400 on unknown or deactivated tenants (§3.2)
- **Tenancy**: SQL artifacts for the public tenant registry,
  `tenant_{uuid}` schema template, RLS policies on
  `current_setting('app.current_tenant')`, and append-only audit trigger (§3.4)
- **Catalog**: Vertical-governed `Service`/`Product` taxonomy with
  per-vertical capabilities (§3.3)
- **Orders**: v2.0 state machine — `draft → reserved → confirmed →
  in_progress → completed`, cancellation from any pre-completion state
  triggering the refund workflow with a mandatory audit entry
- **Orders**: `payment_mode` support (`online_prepay | post_service |
  in_person | mixed`) and `external_id` UUID mapping for Bitrix24 deals
- **Orders**: `OrderService` orchestrator — tenant-stamped registration,
  audited transitions, completion settlement, cancellation refunds
- **Commissions**: Commission engine (10% default, tenant-configurable,
  Decimal ROUND_DOWN) and immutable `CommissionLedger` with balance
  validation and daily reconciliation totals (§3.3)
- **Payments**: Zero-PAN `PaymentToken` store rejecting raw card numbers
  at the storage boundary (§2, §3.5)
- **Payments**: SetupIntent deferred flow (`usage="off_session"`) with
  charge-on-completion, in-person `receipt_ref` recording, and mixed
  split validation (§3.5, §4.2)
- **Bitrix24**: One-way sync client with pluggable transport; inbound
  writes are always rejected (§3.6)
- **Bitrix24**: PII scrubber — names → `Order-{uuid}`, phone SHA-256 hash,
  email/address removed, `deceased_name` removed entirely (GDPR Art. 9),
  fail-closed on unknown fields (§3.6)
- **Notifications**: Classification channel matrix (public/internal/
  confidential/restricted), confidential+ requiring encrypted payloads,
  DLQ after 3 failed attempts, `notification_id`-only task payloads (§3.7)
- **API**: Tenant-scoped order routes (`POST /orders`, `GET /orders/{id}`,
  `transition`, `complete`, `cancel`), catalog capabilities endpoint
- **Audit**: Blueprint field set on audit entries — `entity_type`,
  `entity_id`, `ip_address`, `user_agent`, `current_hash` (§2)
- **Tests**: Tenancy resolution/isolation, v2.0 lifecycle, order service
  settlement and refunds, commission engine, PII scrubber, notification
  matrix, Zero-PAN token store (141 tests total)
- **Docs**: Blueprint v2.0 module mapping in `docs/architecture.md`
- **Docs**: `ADR-001` — formally accepted tenancy framework divergence
  (FastAPI engine vs Blueprint §3.3 Django/django-tenants) with equivalence
  mapping, disclosed residual gap, and the `jol-hub` `django-tenants`
  obligation

### Changed

- **Orders**: `OrderRepository` is tenant-scoped — cross-tenant reads and
  writes raise `CrossTenantAccessError`; adds `changes_since()` change feed
  for Bitrix24 sync
- **Orders**: Fulfillment service aligned with v2.0 statuses
  (`confirm_payment` → `confirmed`, `start_service` → `in_progress`)
- **Payments**: Stripe client gained `create_setup_intent` and
  `charge_from_token`, both enforcing token-form references
- **API**: Application version 2.0.0; CORS allows `X-JOL-Tenant-ID`

[2.0.0]: https://github.com/journeyoflife-org/jol-commerce-engine/releases/tag/v2.0.0

## [0.1.0] — 2026-07-14

### Added

- **Payments**: Stripe Elements integration (SAQ A — tokenisation only)
- **Payments**: PaymentIntent lifecycle management
- **Payments**: Webhook handler with signature verification
- **Payments**: Refund processing
- **Payments**: EU payment method configuration (card, SEPA, iDEAL, etc.)
- **Tax**: VAT calculator with Decimal precision for all 27 EU countries
- **Tax**: Country rate table with effective-date support (LT=21%, LV=21%, EE=24%)
- **Tax**: Invoice generator with VAT breakdown
- **Tax**: 7-year tax record retention store
- **Orders**: Order lifecycle state machine with validated transitions
- **Orders**: Order repository and fulfillment service
- **Audit**: Immutable hash-chained audit logger (PCI DSS Req. 10)
- **Audit**: Transaction log for payment events
- **Audit**: PII-safe log sanitisation
- **Security**: TLS 1.2+ enforcement with weak cipher denylist
- **Security**: CSP headers with nonce management (PCI Req. 6.4.3)
- **Security**: Idempotency key management
- **API**: FastAPI application with payment, order, and tax routes
- **Frontend**: Stripe Elements React components
- **Frontend**: CSP nonce management (PCI Req. 6.4.3)
- **Frontend**: HTTP header change monitor (PCI Req. 11.6.1)
- **Frontend**: VAT display and invoice download components
- **CI/CD**: GitHub Actions workflows (CI, CodeQL, Qodana, compliance check)
- **CI/CD**: Script integrity verification (PCI Req. 6.4.3)
- **CI/CD**: Production deploy with manual approval gate (workflow_dispatch)
- **Tests**: VAT tests for LT, LV, EE with historical rate verification
- **Tests**: Full 27-country VAT matrix tests
- **Tests**: Security tests (no raw card data, TLS, webhook signature)
- **Tests**: Audit log integrity tests (hash chain, immutability)
- **Docs**: Architecture, payment flow, PCI scope, VAT matrix
- **Docs**: Audit log architecture, script inventory, penetration test scope
- **Docs**: Incident response plan, retention policy, DPIA template
- **Compliance**: PCI, GDPR, tax, audit, and risk documentation
- **Scripts**: PAN verification, Stripe key rotation, VAT report, audit export

[0.1.0]: https://github.com/journeyoflife-org/jol-commerce-engine/releases/tag/v0.1.0
