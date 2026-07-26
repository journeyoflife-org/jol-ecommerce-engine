# Architecture — JOL Commerce Engine

## Overview

The JOL Commerce Engine is a PCI DSS SAQ A compliant e-commerce platform serving 27 EU countries with Baltic-state focus (LT, LV, EE).

## System Architecture

```
Browser → CDN/Load Balancer → FastAPI Backend → PostgreSQL
         ↓                          ↓
    Stripe Elements            Stripe API
    (hosted iframe)           (tokenised)
```

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

## Key Design Decisions

1. **Decimal arithmetic** for all VAT calculations (no floating-point)
2. **Hash-chained audit logs** for tamper detection
3. **CSP nonces** per-request for payment page script integrity
4. **Header monitoring** for PCI Req. 11.6.1 compliance
