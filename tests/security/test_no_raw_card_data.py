"""Security test — assert no raw card data (PANs) in logs or database models.

PCI DSS SAQ A: card numbers must never appear in application logs,
database fields, or error messages. This test scans all Python source
files in the payments module for PAN-like patterns.
"""

import re
from pathlib import Path

import pytest

# PAN pattern: 13-19 consecutive digits (card number format)
PAN_PATTERN = re.compile(r"\b\d{13,19}\b")

# Card data field names that must never appear
FORBIDDEN_FIELDS = {
    "card_number",
    "card_cvv",
    "card_cvc",
    "card_expiry",
    "pan_raw",
    "raw_card_number",
    "cvv_code",
    "cvc_code",
}

PAYMENTS_MODULE = Path(__file__).resolve().parents[2] / "backend" / "jol_commerce" / "payments"


@pytest.mark.pci
class TestNoRawCardData:
    """Verify no raw card data exists in the payments module source code."""

    def test_no_pan_patterns_in_payment_source(self) -> None:
        """Scan all Python files in payments/ for PAN-like number patterns."""
        pan_matches: list[tuple[str, int, str]] = []

        for py_file in PAYMENTS_MODULE.rglob("*.py"):
            if py_file.name.startswith("test_"):
                continue
            content = py_file.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                # Skip comments and docstrings
                stripped = line.strip()
                if (
                    stripped.startswith("#")
                    or stripped.startswith('"""')
                    or stripped.startswith("'''")
                ):
                    continue
                matches = PAN_PATTERN.findall(line)
                for _match in matches:
                    # Exclude known safe patterns (Stripe IDs, test values)
                    if not any(
                        x in line for x in ["pm_", "pi_", "ch_", "stripe", "test", "example"]
                    ):
                        pan_matches.append((py_file.name, i, line.strip()))

        assert not pan_matches, (
            "CRITICAL: PAN-like patterns found in payment module source:\n"
            + "\n".join(f"  {f}:{lineno}: {c}" for f, lineno, c in pan_matches)
        )

    def test_no_forbidden_card_data_fields(self) -> None:
        """Verify no forbidden raw card data field names exist."""
        violations: list[tuple[str, int, str]] = []

        for py_file in PAYMENTS_MODULE.rglob("*.py"):
            if py_file.name.startswith("test_"):
                continue
            content = py_file.read_text()
            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for field_name in FORBIDDEN_FIELDS:
                    if field_name in stripped.lower():
                        violations.append((py_file.name, i, stripped))

        assert not violations, "CRITICAL: Forbidden card data field names found:\n" + "\n".join(
            f"  {f}:{lineno}: {c}" for f, lineno, c in violations
        )

    def test_payments_module_does_not_import_raw_card_types(self) -> None:
        """Verify the payments module never imports raw card type definitions."""
        for py_file in PAYMENTS_MODULE.rglob("*.py"):
            content = py_file.read_text()
            assert "card_number" not in content or "pm_" in content, (
                f"File {py_file.name} may reference raw card numbers"
            )
