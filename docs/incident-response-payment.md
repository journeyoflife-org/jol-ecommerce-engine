# Incident Response — Payment Data Security

## Overview

This plan covers payment data security incidents requiring notification under:
- **PCI DSS v4.0.1** — card brand and acquirer notification
- **GDPR Art. 33** — supervisory authority notification within 72 hours
- **GDPR Art. 34** — affected individual notification (if high risk)

## Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| P1 | Confirmed cardholder data exposure | Immediate |
| P2 | Suspected cardholder data exposure | < 1 hour |
| P3 | Security control failure (no confirmed exposure) | < 4 hours |
| P4 | Near miss / control weakness | < 24 hours |

## Response Steps

### 1. Containment (Immediate)
- Identify affected systems and transactions
- Isolate compromised components
- Preserve evidence (audit logs, system state)
- **Do NOT delete or modify audit logs**

### 2. Assessment (< 4 hours)
- Determine scope: transactions affected, countries, date range
- Assess whether cardholder data was exposed
- Evaluate GDPR notification obligations
- Engage legal counsel

### 3. Notification

| Obligation | Deadline | Authority |
|-----------|----------|-----------|
| Stripe (acquirer) | Immediate | Stripe Dashboard / Support |
| GDPR Art. 33 | 72 hours | Supervisory authority |
| Card brands | Per brand rules | Via acquirer |
| Affected individuals | Without undue delay | Direct communication |

### 4. Remediation
- Root cause analysis
- Implement corrective controls
- Re-test affected security controls
- Update incident response plan

## Reporting

Use the **pci-incident.yml** issue template for all payment incidents.

**Do NOT include actual PANs or card numbers in incident reports.**
