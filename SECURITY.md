# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x | Yes |

## Reporting a Vulnerability

**Do NOT open a public GitHub issue for security vulnerabilities.**

### Payment Data Incidents (PCI DSS)

If you discover a vulnerability involving payment card data:

1. Email: security@journeyoflife.org
2. Use the **pci-incident.yml** issue template (confidential)
3. Do NOT include actual card numbers (PANs) in any report

### General Security Vulnerabilities

1. Email: security@journeyoflife.org
2. Include: description, impact assessment, reproduction steps
3. Expected response: within 48 hours

## Security Controls

- **TLS**: 1.2 minimum, 1.3 preferred; weak ciphers disabled
- **Card data**: Stripe Elements only — no raw PAN/CVV/expiry on JOL servers
- **Audit logging**: Immutable hash chain, 12-month retention, SIEM integration
- **CSP**: Nonce-based script integrity on payment pages (PCI Req. 6.4.3)
- **Header monitoring**: Automated detection of header changes (PCI Req. 11.6.1)
- **Deployment**: Manual approval gate for production; OIDC authentication

## PCI DSS Scope

This project targets **SAQ A** compliance. See [docs/pci-scope-statement.md](docs/pci-scope-statement.md).
