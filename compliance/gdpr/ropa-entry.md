# ROPA Entry — Record of Processing Activities (GDPR Art. 30)

## Controller

| Field | Value |
|-------|-------|
| Organisation | Journey of Life |
| DPO | TBD |
| Purpose | E-commerce payment processing |

## Processing Activities

| Activity | Legal Basis | Data Categories | Recipients | Retention |
|----------|-------------|----------------|------------|-----------|
| Order processing | Art. 6(1)(b) contract | Name, address, email | Fulfillment partners | 7 years |
| Payment processing | Art. 6(1)(b) contract | Payment token (pm_xxx) | Stripe (processor) | Transaction lifetime |
| VAT invoicing | Art. 6(1)(c) legal obligation | Name, address, amounts | Tax authorities (on request) | 7 years |
| Audit logging | Art. 6(1)(c) legal obligation | User ID, event type, timestamp | Internal, PCI auditors | 12 months |

## Safeguards

- Encryption at rest and in transit (TLS 1.2+)
- PII minimisation in logs
- Access controls (RBAC)
- Annual DPIA review
