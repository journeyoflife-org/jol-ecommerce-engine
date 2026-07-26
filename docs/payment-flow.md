# Payment Flow — Data Flow Diagram

## Flow: Browser → Stripe → JOL Webhook

```
1. Customer enters card in Stripe Elements iframe (hosted by Stripe)
2. Stripe tokenizes card → returns payment method ID (pm_xxx)
3. Frontend sends pm_xxx + order details to JOL backend API
4. Backend creates Stripe PaymentIntent with pm_xxx
5. Stripe processes payment
6. Stripe sends webhook to JOL backend (payment_intent.succeeded)
7. Backend updates order status, generates invoice, logs audit entry
8. Customer sees payment confirmation
```

## Data Boundaries

| Step | Data | Where it lives |
|------|------|----------------|
| Card entry | PAN, CVV, expiry | Stripe iframe only — never JOL |
| Tokenisation | pm_xxx | Browser → JOL backend → Stripe API |
| Payment processing | pi_xxx | Stripe → JOL webhook |
| Order storage | order details, amounts | JOL database |
| Audit log | event metadata (no PII) | JOL audit store |

## PCI DSS Implications

- **SAQ A maintained** as long as raw card data stays in Stripe iframe
- If any code path touches raw PAN/CVV/expiry → scope escalates to SAQ D
- All webhook events logged per PCI Req. 10
