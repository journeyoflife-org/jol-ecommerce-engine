# Audit Log Architecture — PCI DSS Requirement 10

## Overview

The audit logging system satisfies PCI DSS v4.0.1 Requirement 10:

- **10.2**: Audit trails for all access to cardholder data
- **10.4.1.1**: Automated log review via SIEM (mandatory since March 2025)
- **10.5.1**: 12-month retention; 3 months immediately searchable

## Log Entry Schema

Every audit entry contains:
- `entry_id` — UUID
- `timestamp` — UTC ISO 8601 (NTP-synchronized)
- `actor` — User ID or service name
- `event_type` — e.g., "payment.created", "order.shipped"
- `outcome` — "success" or "failure"
- `transaction_ref` — Payment intent ID, order ID
- `correlation_id` — Cross-service tracing
- `previous_hash` — Hash of previous entry (tamper chain)

## Tamper Detection

Entries form a **hash chain**: each entry includes the SHA-256 hash of the previous entry. Any modification to a historical entry breaks the chain and is detected by `verify_chain_integrity()`.

## Retention Policy

- **Minimum retention**: 12 months
- **Searchable window**: Most recent 3 months (hot storage)
- **Cold storage**: Older entries archived but retrievable
- **Deletion**: Never during retention period (WORM)

## SIEM Integration

PCI DSS v4.0.1 Requirement 10.4.1.1 mandates automated log review:
- Failed transaction events trigger SIEM alerts
- Unusual patterns (volume spikes, geographic anomalies) flagged
- Daily automated report (not manual review — that is no longer compliant)
