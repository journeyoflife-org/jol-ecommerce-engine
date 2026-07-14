# JOL Commerce Engine

PCI DSS SAQ A compliant e-commerce engine for Journey of Life, serving 27 EU countries with Baltic-state focus (Lithuania, Latvia, Estonia).

## Architecture

- **Backend**: Python 3.12, FastAPI, PostgreSQL
- **Frontend**: React 19, TypeScript, Vite
- **Payments**: Stripe Elements (tokenisation only — no raw card data on JOL servers)
- **VAT**: Decimal-precision calculation for all 27 EU countries
- **Audit**: Immutable hash-chained audit log (PCI DSS Req. 10)

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
