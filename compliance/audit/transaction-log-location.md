# Transaction Log Location

## PCI DSS Requirement 10

All payment transaction events are logged via:
- `backend/jol_commerce/audit/audit_log.py` — general audit log
- `backend/jol_commerce/audit/transaction_log.py` — payment-specific events

## Storage

| Log Type | Storage | Retention | Searchable |
|----------|---------|-----------|------------|
| Audit entries | Append-only store (WORM) | 12+ months | Last 3 months |
| Transaction events | Append-only store | 12+ months | Last 3 months |
| Webhook receipts | Audit log chain | 12+ months | Last 3 months |

## SIEM Forwarding

PCI DSS v4.0.1 Req. 10.4.1.1 mandates automated review:
- Failed events forwarded to SIEM immediately
- Daily automated summary report
- Alert rules for anomalous patterns
