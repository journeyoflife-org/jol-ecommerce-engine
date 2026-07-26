# Penetration Test Scope — PCI DSS Requirement 11.3

## Requirement

PCI DSS v4.0.1 Requirement 11.3 mandates:
- Penetration testing at minimum **annually**
- Re-test after any **significant infrastructure change**
- Segmentation validation every **6 months** (if used for scope reduction)

## Test Scope

### Application Layer
- Payment API endpoints (`/api/v1/payments/*`)
- Webhook endpoint signature verification
- Authentication and authorization controls
- Input validation (especially payment method ID format)
- CSP header enforcement on payment pages

### Network Layer
- CDE perimeter (payment service network segment)
- Segmentation between CDE and non-CDE networks
- TLS configuration (1.2+ enforcement, weak cipher rejection)
- Firewall rules and access controls

### Infrastructure
- Cloud hosting environment (AWS eu-central-1)
- Database access controls
- Secrets management (Stripe keys, webhook secrets)
- Deployment pipeline security

## Pre-Go-Live Checklist

- [ ] Penetration test scope defined and approved
- [ ] Qualified penetration tester engaged (internal or third-party)
- [ ] Test completed with findings documented
- [ ] Critical/high findings remediated
- [ ] Re-test of remediated findings passed
- [ ] Report signed and filed in `compliance/pci/pentest-evidence/`

## Schedule

| Test | Due Date | Status |
|------|----------|--------|
| Initial pre-go-live | Before production launch | Pending |
| Annual re-test | 12 months from initial | Pending |
| Segmentation validation | 6 months from initial | Pending |
