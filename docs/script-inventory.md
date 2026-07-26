# Payment Page Script Inventory — PCI DSS Req. 6.4.3

## Requirement

PCI DSS v4.0.1 Requirement 6.4.3 mandates a documented inventory of every script loaded on payment pages, including:
- Script source URL
- SHA-256 integrity hash
- Authorization date
- Business justification

## Authorized Scripts

| Script | Source | Hash | Authorized | Justification |
|--------|--------|------|------------|---------------|
| Stripe.js | https://js.stripe.com/v3/ | (computed at deploy) | 2026-01-01 | Card tokenisation |
| React app bundle | /assets/index-*.js | (computed at build) | 2026-01-01 | Application |
| CSP nonce manager | /shared/csp-nonce.ts | (computed at build) | 2026-01-01 | Script integrity |
| Header monitor | /shared/header-monitor.ts | (computed at build) | 2026-01-01 | PCI 11.6.1 |

## Verification Process

1. **Build time**: `script-integrity-check.yml` computes SHA-256 hashes
2. **Deploy time**: Hashes compared against `compliance/pci/script-inventory.csv`
3. **Runtime**: CSP headers with nonces prevent unauthorized script execution

## Change Process

Any new script on a payment page requires:
1. Security team review and approval
2. Update `compliance/pci/script-inventory.csv`
3. Update this document
4. Pass `script-integrity-check.yml` CI workflow
