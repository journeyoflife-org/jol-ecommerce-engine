# Retention Policy

## Legal Obligations

| Category | Retention Period | Legal Basis |
|----------|-----------------|-------------|
| Financial records (invoices, VAT) | 7 years | Lithuanian accounting law |
| Payment transaction records | 7 years | LT/LV/EE tax law |
| Audit logs (PCI DSS) | 12 months minimum | PCI DSS Req. 10.5.1 |
| Audit logs (searchable) | 3 months immediately | PCI DSS Req. 10.5.1 |
| Customer account data | Account lifetime + erasure request | GDPR Art. 17 |

## GDPR Data Minimisation

Personal data within financial records must be minimised to only what tax law requires:
- **Retained**: Name, address (for VAT invoice), transaction amounts, dates
- **Minimised**: Email (pseudonymised after order completion)
- **Not retained**: Raw card data (never stored), browsing history, preferences

## Deletion Schedule

| Data Type | Auto-delete After | Method |
|-----------|-------------------|--------|
| Session cookies | Browser close | Browser |
| Failed payment attempts | 30 days | Automated |
| Completed order PII | 7 years | Automated (GDPR minimisation) |
| Audit log entries | Never during retention | Manual review for archival |

## Review Schedule

- Annual review of retention compliance
- Automated alerts 6 months before retention expiry
- GDPR erasure requests processed within 30 days

## Sources

- [EY Baltic Tax Card 2025](https://www.ey.com/content/dam/ey-unified-site/ey-com/en-lt/generic/documents/ey-baltic-tax-card-2025.pdf)
- [ICO — Lawful Basis: Contract](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/a-guide-to-lawful-basis/contract/)
