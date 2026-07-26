#!/usr/bin/env bash
# collect-pci-evidence.sh — Collect PCI DSS compliance evidence
#
# Gathers all compliance evidence into a single archive for
# PCI DSS assessment or audit.

set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="pci-evidence-${TIMESTAMP}"

echo "=== PCI DSS Evidence Collection ==="
echo "Output directory: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"

# Collect compliance documentation
echo "--- Collecting compliance documentation ---"
cp -r compliance/ "$OUTPUT_DIR/compliance/" 2>/dev/null || echo "WARNING: compliance/ directory not found"

# Collect security configuration
echo "--- Collecting security configuration ---"
mkdir -p "$OUTPUT_DIR/security"
cp backend/jol_commerce/security/*.py "$OUTPUT_DIR/security/" 2>/dev/null || true

# Run PAN verification
echo "--- Running PAN verification ---"
bash scripts/verify-no-pan-in-logs.sh --code-only > "$OUTPUT_DIR/pan-verification-report.txt" 2>&1 || true

# Collect test results
echo "--- Collecting test evidence ---"
mkdir -p "$OUTPUT_DIR/tests"
cp -r tests/security/ "$OUTPUT_DIR/tests/security/" 2>/dev/null || true
cp -r tests/tax/ "$OUTPUT_DIR/tests/tax/" 2>/dev/null || true
cp -r tests/audit/ "$OUTPUT_DIR/tests/audit/" 2>/dev/null || true

# Collect CI/CD configuration
echo "--- Collecting CI/CD configuration ---"
mkdir -p "$OUTPUT_DIR/ci"
cp .github/workflows/*.yml "$OUTPUT_DIR/ci/" 2>/dev/null || true

# Generate evidence manifest
echo "--- Generating evidence manifest ---"
find "$OUTPUT_DIR" -type f | sort > "$OUTPUT_DIR/MANIFEST.txt"

echo ""
echo "=== Evidence collection complete ==="
echo "Directory: $OUTPUT_DIR"
echo "Files: $(find "$OUTPUT_DIR" -type f | wc -l)"
echo ""
echo "Review $OUTPUT_DIR/MANIFEST.txt for full file listing."
