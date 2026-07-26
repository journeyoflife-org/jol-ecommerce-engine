# DPIA Template — Data Protection Impact Assessment

## Processing Activity

**Activity**: Payment processing for e-commerce transactions
**GDPR Article**: Art. 6(1)(b) — contractual necessity

## Data Categories

| Category | Source | Purpose | Retention |
|----------|--------|---------|-----------|
| Name | Customer input | Order fulfillment | 7 years (tax law) |
| Address | Customer input | Delivery, VAT | 7 years (tax law) |
| Email | Customer input | Order confirmation | Account lifetime |
| Payment token (pm_xxx) | Stripe | Payment processing | Transaction lifetime |

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Card data exposure | Low | Critical | SAQ A — Stripe Elements iframe |
| PII in audit logs | Low | High | PII sanitisation, field allowlist |
| Data breach | Low | Critical | Encryption, TLS 1.2+, access controls |
| Over-retention | Medium | Medium | Automated retention policy |

## DPO Sign-off

- [ ] Review complete
- [ ] Risks acceptable
- [ ] Signed: ________________
- [ ] Date: ________________
