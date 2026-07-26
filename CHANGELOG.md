# Changelog

All notable changes to the JOL Commerce Engine are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
