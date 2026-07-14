"""Payments module — PCI DSS SAQ A compliant.

CRITICAL: This module must NEVER handle raw card data (PAN, CVV, expiry).
All card data collection happens within Stripe Elements/Checkout iframes.
Only tokenized payment method IDs are processed server-side.
"""
