# Risk Register

| ID | Risk | Likelihood | Impact | Owner | Mitigation | Status |
|----|------|-----------|--------|-------|-----------|--------|
| R1 | PCI scope escalation (SAQ A → SAQ D) | Low | Critical | Security | Stripe Elements, no raw card data | Active |
| R2 | VAT rate changes not reflected | Medium | High | Finance | Quarterly rate review, automated CI check | Active |
| R3 | Audit log tampering | Low | Critical | Security | Hash chain, WORM storage | Active |
| R4 | GDPR data breach | Low | Critical | DPO | Encryption, access controls, DPIA | Active |
| R5 | Penetration test overdue | Low | High | Security | Calendar tracking, annual schedule | Active |
| R6 | Estonia VAT miscalculation (old 22%) | Medium | Medium | Engineering | Date-based rate lookup, test matrix | Mitigated |
| R7 | Stripe webhook signature bypass | Low | Critical | Security | Signature verification, timestamp drift check | Active |
| R8 | Script injection on payment page | Low | Critical | Security | CSP nonces, script inventory, CI check | Active |
