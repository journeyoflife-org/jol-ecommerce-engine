"""Idempotency key management for payment operations.

Prevents duplicate payment processing when requests are retried.
Each payment mutation must include an idempotency key to ensure
exactly-once processing semantics.
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any


class IdempotencyManager:
    """Manages idempotency keys for payment operations.

    Payment mutations (create intent, capture, refund) must be idempotent
    to prevent double-charging on network retries.
    """

    def __init__(self, secret_key: str) -> None:
        """Initialize with the application secret key.

        Args:
            secret_key: Application secret used for key validation.
        """
        self._secret_key = secret_key
        self._used_keys: dict[str, dict[str, Any]] = {}

    def validate_key(self, idempotency_key: str) -> bool:
        """Validate that an idempotency key is well-formed.

        Args:
            idempotency_key: Client-provided idempotency key.

        Returns:
            True if the key is valid.
        """
        return bool(idempotency_key and len(idempotency_key) >= 16)

    def is_duplicate(self, idempotency_key: str) -> bool:
        """Check if this idempotency key has already been used.

        Args:
            idempotency_key: Client-provided idempotency key.

        Returns:
            True if the key was previously processed.
        """
        return idempotency_key in self._used_keys

    def get_previous_response(self, idempotency_key: str) -> dict[str, Any] | None:
        """Retrieve the cached response for a previously processed key.

        Args:
            idempotency_key: Client-provided idempotency key.

        Returns:
            Cached response dict or None if not found.
        """
        entry = self._used_keys.get(idempotency_key)
        if entry:
            return entry.get("response")
        return None

    def record(
        self,
        idempotency_key: str,
        response: dict[str, Any],
        operation: str,
    ) -> None:
        """Record a processed idempotency key and its response.

        Args:
            idempotency_key: Client-provided idempotency key.
            response: The response that was returned.
            operation: Description of the operation performed.
        """
        self._used_keys[idempotency_key] = {
            "response": response,
            "operation": operation,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def compute_signature(self, idempotency_key: str, payload: str) -> str:
        """Compute HMAC signature for idempotency key + payload binding.

        Args:
            idempotency_key: The idempotency key.
            payload: The request payload.

        Returns:
            HMAC-SHA256 hex digest.
        """
        message = f"{idempotency_key}:{payload}"
        return hmac.new(
            self._secret_key.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
