# Controls Matrix

| Control ID | Requirement | Control | Implementation | Test | Status |
|-----------|-------------|---------|----------------|------|--------|
| C1 | PCI SAQ A | Stripe Elements tokenisation | `stripe_client.py`, `StripeElements.tsx` | `test_no_raw_card_data.py` | Active |
| C2 | PCI Req. 6.4.3 | Script inventory + integrity | `script-inventory.csv`, `script-integrity-check.yml` | CI workflow | Active |
| C3 | PCI Req. 11.6.1 | Header change detection | `header-monitor.ts` | Runtime monitoring | Active |
| C4 | PCI Req. 10 | Audit logging | `audit_log.py`, `transaction_log.py` | `test_audit_log_integrity.py` | Active |
| C5 | PCI Req. 10.4.1.1 | Automated SIEM review | `transaction_log.py` → SIEM | Alert rules | Active |
| C6 | PCI Req. 10.5.1 | 12-month log retention | WORM storage | Retention config | Active |
| C7 | PCI Req. 11.3 | Penetration testing | Annual + post-change | `penetration-test-scope.md` | Pending |
| C8 | TLS 1.2+ | TLS enforcement | `tls_enforcement.py` | `test_tls_enforcement.py` | Active |
| C9 | VAT accuracy | Decimal VAT calculation | `vat_calculator.py`, `country_rates.py` | 27-country test matrix | Active |
| C10 | GDPR Art. 6(1)(b) | Contractual lawful basis | `lawful-basis.md` | DPIA review | Active |
| C11 | 7-year retention | Tax record retention | `tax_record_store.py` | Retention policy | Active |
| C12 | Deployment gate | Manual production deploy | `prod-deploy.yml` (workflow_dispatch) | Environment approval | Active |
