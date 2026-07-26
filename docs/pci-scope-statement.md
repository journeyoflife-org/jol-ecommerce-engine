# PCI DSS Scope Statement

## SAQ A Eligibility

JOL Commerce Engine qualifies for **PCI DSS SAQ A** because:
- All card data is collected via Stripe Elements hosted iframes
- No raw card data (PAN, CVV, expiry) touches JOL servers
- Only tokenized payment method IDs (pm_xxx) are processed

## CDE Boundary

The Cardholder Data Environment includes:
- `/backend/jol_commerce/payments/` — Stripe API integration
- `/backend/jol_commerce/audit/` — Transaction logging
- `/frontend/src/payment/` — Stripe Elements components
- Stripe webhook endpoint

## Scope Reduction Controls

1. **Network segmentation**: Payment services isolated from general services
2. **Tokenisation**: Stripe handles all card data collection and storage
3. **No card data storage**: JOL never stores PAN, CVV, or full expiry

## Mandatory Controls (PCI DSS v4.0.1)

- **Req. 6.4.3**: Payment page script inventory with integrity verification
- **Req. 11.6.1**: HTTP header/cookie change detection on payment pages
- **Req. 10**: Audit logging with 12-month retention, 3-month searchable
- **Req. 10.4.1.1**: Automated SIEM review (mandatory since March 2025)

## Annual Review

- [ ] SAQ A questionnaire completed
- [ ] Scope validation by security team
- [ ] Signed by: ________________
- [ ] Date: ________________
