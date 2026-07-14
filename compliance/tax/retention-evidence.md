# Tax Record Retention Evidence

## Requirement

Lithuanian accounting law requires financial records to be kept for at least 7 years.

## Records Subject to Retention

- Invoices (with VAT breakdown)
- Payment transaction records
- VAT calculation records
- Tax filing evidence

## Storage Controls

- Append-only writes (no modification during retention)
- Encrypted at rest
- Access restricted to finance and compliance teams
- Automated retention expiry tracking

## Evidence Location

| Record Type | Storage Location | Retention Until |
|-------------|-----------------|-----------------|
| Invoices | PostgreSQL + S3 archive | Transaction date + 7 years |
| VAT records | `tax_record_store` | Transaction date + 7 years |
| Payment records | PostgreSQL | Transaction date + 7 years |
