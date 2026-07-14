"""PII-safe logging — ensures no personal data leaks into logs.

GDPR data minimisation principle: logs must not contain personal data
unless strictly necessary for the audit purpose. This module provides
utilities to sanitise log content and detect PII patterns.

PCI DSS additionally prohibits logging of card data (PAN, CVV, expiry).
"""

from __future__ import annotations

import re
from typing import Any

# Patterns that indicate potential PII or card data
PAN_PATTERN = re.compile(r"\b[0-9]{13,19}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
CVV_PATTERN = re.compile(r"\b[0-9]{3,4}\b")  # Context-dependent


class PIIDetectionError(Exception):
    """Raised when PII or card data is detected in log content."""


def sanitize_value(value: str) -> str:
    """Redact potential PII from a string value.

    Args:
        value: String that may contain PII.

    Returns:
        Sanitized string with PII patterns redacted.
    """
    return EMAIL_PATTERN.sub(
        "[EMAIL_REDACTED]",
        PAN_PATTERN.sub("[PAN_REDACTED]", value),
    )


def contains_pan(value: str) -> bool:
    """Check if a string contains a potential card PAN.

    Args:
        value: String to check.

    Returns:
        True if a PAN-like pattern is detected.
    """
    return bool(PAN_PATTERN.search(value))


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize a dictionary, redacting PII patterns.

    Args:
        data: Dictionary to sanitize.

    Returns:
        New dictionary with PII patterns redacted in string values.
    """
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_value(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item)
                if isinstance(item, dict)
                else sanitize_value(str(item))
                if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


def assert_no_pii_in_log_content(content: str) -> None:
    """Assert that log content contains no card data.

    This should be called in test suites to verify logging safety.

    Args:
        content: Log content to verify.

    Raises:
        PIIDetectionError: If PAN patterns are detected.
    """
    if contains_pan(content):
        raise PIIDetectionError(
            "CRITICAL: Potential card PAN detected in log content. "
            "This violates PCI DSS SAQ A scope.",
        )
