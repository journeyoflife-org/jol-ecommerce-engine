## Summary

<!-- Concise description of what this PR does and why -->

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Payment flow change (requires security team review — see CODEOWNERS)
- [ ] Compliance / documentation update

## PCI DSS Impact

- [ ] This PR does **not** touch payment card data, payment pages, or audit logging
- [ ] This PR touches payment pages or payment flows — security team review required
- [ ] This PR modifies audit logging — security team review required
- [ ] This PR adds or modifies scripts on payment pages — PCI Req. 6.4.3 inventory must be updated

## Changes

<!-- Bullet list of specific changes made -->

-

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] VAT calculation tests updated (if tax logic changed)
- [ ] Security tests pass (`test_no_raw_card_data`, `test_tls_enforcement`, `test_webhook_signature`)
- [ ] `make security` passes locally

## Checklist

- [ ] Code follows project style guidelines (`make lint` passes)
- [ ] Type checking passes (`make typecheck` passes)
- [ ] No raw card data (PAN, expiry, CVV) is logged, stored, or transmitted server-side
- [ ] Audit logging added for any payment/order state changes
- [ ] `.env.example` updated if new environment variables are introduced
- [ ] Documentation updated where applicable
- [ ] `CHANGELOG.md` updated
