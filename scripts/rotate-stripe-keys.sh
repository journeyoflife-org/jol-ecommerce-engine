#!/usr/bin/env bash
# rotate-stripe-keys.sh — Rotate Stripe API keys
#
# Stripe keys should be rotated regularly (recommended: every 90 days).
# This script documents the rotation procedure.

set -euo pipefail

echo "=== Stripe Key Rotation Procedure ==="
echo ""
echo "This is a DOCUMENTED PROCEDURE, not an automated rotation."
echo ""
echo "Steps to rotate Stripe keys:"
echo ""
echo "1. Log in to Stripe Dashboard: https://dashboard.stripe.com"
echo "2. Navigate to Developers → API keys"
echo "3. Click 'Roll key' for the secret key"
echo "4. Update the key in your secrets manager (NOT .env files)"
echo "5. Update STRIPE_SECRET_KEY in production secrets"
echo "6. Update STRIPE_WEBHOOK_SECRET if webhook endpoint was recreated"
echo "7. Restart application services"
echo "8. Verify webhook delivery in Stripe Dashboard"
echo "9. Run: bash scripts/verify-no-pan-in-logs.sh --code-only"
echo ""
echo "CRITICAL:"
echo "- Never commit Stripe keys to version control"
echo "- Never log Stripe keys in application logs"
echo "- Old key remains valid for 24 hours after rolling"
echo ""
echo "Record rotation in compliance/audit/access-review-log.md"
