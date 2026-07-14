#!/usr/bin/env bash
# verify-no-pan-in-logs.sh — Scan logs for PAN patterns (CRITICAL)
#
# PCI DSS SAQ A: No raw card numbers (PANs) should appear in any
# application logs, database fields, or error messages.
#
# Usage:
#   ./scripts/verify-no-pan-in-logs.sh              # Full scan
#   ./scripts/verify-no-pan-in-logs.sh --code-only   # Source code only

set -euo pipefail

PAN_REGEX='\b[0-9]{13,19}\b'
SCAN_LOGS=true
VIOLATIONS=0

if [[ "${1:-}" == "--code-only" ]]; then
    SCAN_LOGS=false
fi

echo "=== PCI DSS PAN Verification ==="
echo "Scanning for Primary Account Number (PAN) patterns..."
echo ""

# Scan Python source code in payments module
echo "--- Scanning payment module source code ---"
PAYMENT_FILES=$(find backend/jol_commerce/payments -name "*.py" ! -name "test_*" 2>/dev/null || true)

for file in $PAYMENT_FILES; do
    # Skip comments and known safe patterns
    MATCHES=$(grep -nE "$PAN_REGEX" "$file" 2>/dev/null | grep -v "^\s*#" | grep -v "pm_" | grep -v "pi_" | grep -v "stripe" | grep -v "test" | grep -v "example" || true)
    if [ -n "$MATCHES" ]; then
        echo "VIOLATION: Potential PAN found in $file:"
        echo "$MATCHES"
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
done

# Scan for forbidden card data field names
echo ""
echo "--- Scanning for forbidden card data field names ---"
FORBIDDEN="card_number|card_cvv|card_cvc|card_expiry|pan_raw|raw_card"
FORBIDDEN_MATCHES=$(grep -rnE "$FORBIDDEN" backend/jol_commerce/payments/ --include="*.py" 2>/dev/null | grep -v "^\s*#" || true)

if [ -n "$FORBIDDEN_MATCHES" ]; then
    echo "VIOLATION: Forbidden card data field names found:"
    echo "$FORBIDDEN_MATCHES"
    VIOLATIONS=$((VIOLATIONS + 1))
fi

# Scan log files if requested
if [ "$SCAN_LOGS" = true ]; then
    echo ""
    echo "--- Scanning log files ---"
    LOG_DIR="${LOG_DIR:-logs}"
    if [ -d "$LOG_DIR" ]; then
        LOG_MATCHES=$(grep -rnE "$PAN_REGEX" "$LOG_DIR" 2>/dev/null || true)
        if [ -n "$LOG_MATCHES" ]; then
            echo "VIOLATION: PAN patterns found in log files:"
            echo "$LOG_MATCHES" | head -20
            VIOLATIONS=$((VIOLATIONS + 1))
        else
            echo "PASS: No PAN patterns found in logs."
        fi
    else
        echo "INFO: Log directory '$LOG_DIR' not found (skipping log scan)."
    fi
fi

echo ""
echo "=== Results ==="
if [ "$VIOLATIONS" -gt 0 ]; then
    echo "CRITICAL: $VIOLATIONS violation(s) found!"
    echo "Raw card data must NEVER appear in source code, logs, or database."
    exit 1
else
    echo "PASS: No PAN violations detected."
    exit 0
fi
