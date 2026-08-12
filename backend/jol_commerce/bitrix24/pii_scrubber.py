"""PII Scrubber — mandatory filtering before the Bitrix24 boundary (§3.6).

Rule table (Blueprint §3.6 — PII Scrubber Rules, Mandatory):

| Field          | Action                                        |
|----------------|-----------------------------------------------|
| customer_name  | Replace with `Order-{uuid}`                   |
| phone          | Hash (SHA-256) or remove                      |
| email          | Remove                                        |
| address        | Remove                                        |
| deceased_name  | Remove entirely (special category data, Art.9)|
| order_id       | Map to UUID `external_id`                     |
| status/amount/branch_id/service_type | Allow (aggregatable)  |

The scrubber runs on every outbound payload before it crosses into the
Bitrix24 Box dispatch system. GDPR Article 9: `deceased_name` and any
explicit special-category markers are removed entirely, never hashed.
"""

from __future__ import annotations

import hashlib
import re
from enum import Enum
from typing import Any

# Defensive patterns: strip anything PII-shaped that sneaks past the
# field-level rules inside free-text values.
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\+?\b[\d][\d\s\-()]{6,}\b")


class ScrubAction(str, Enum):
    """Action applied to a field crossing the Bitrix24 boundary."""

    REPLACE_WITH_ORDER_REF = "replace_with_order_ref"  # customer_name
    HASH_OR_REMOVE = "hash_or_remove"  # phone
    REMOVE = "remove"  # email, address, deceased_name
    MAP_TO_EXTERNAL_ID = "map_to_external_id"  # order_id
    ALLOW = "allow"  # status, amount, branch_id, service_type


# Mandatory rule table (Blueprint §3.6).
PII_FIELD_RULES: dict[str, ScrubAction] = {
    "customer_name": ScrubAction.REPLACE_WITH_ORDER_REF,
    "phone": ScrubAction.HASH_OR_REMOVE,
    "email": ScrubAction.REMOVE,
    "address": ScrubAction.REMOVE,
    "deceased_name": ScrubAction.REMOVE,  # GDPR Art. 9 special category
    "order_id": ScrubAction.MAP_TO_EXTERNAL_ID,
    # Explicitly allowed aggregatable fields:
    "external_id": ScrubAction.ALLOW,
    "status": ScrubAction.ALLOW,
    "amount": ScrubAction.ALLOW,
    "amount_cents": ScrubAction.ALLOW,
    "branch_id": ScrubAction.ALLOW,
    "service_type": ScrubAction.ALLOW,
    "currency": ScrubAction.ALLOW,
}

# Any field not in the rule table is denied by default (fail-closed).
DEFAULT_ACTION = ScrubAction.REMOVE


class PIIScrubber:
    """Scrubs outbound payloads before the Bitrix24 Box boundary."""

    def __init__(self, *, hash_phone: bool = True) -> None:
        self._hash_phone = hash_phone

    def scrub_order_payload(
        self,
        payload: dict[str, Any],
        *,
        external_id: str,
    ) -> dict[str, str | int]:
        """Produce a compliant sync payload for one order (§4.3 step 4).

        Output shape is exactly:
            {external_id, status, amount, branch_id, service_type}

        Args:
            payload: Raw order payload (may contain PII fields).
            external_id: UUID mapped from the internal order_id.

        Returns:
            Scrubbed payload safe to send to Bitrix24 Box.

        Raises:
            ValueError: If the raw order_id lacks an external_id mapping.
        """
        if not external_id:
            raise ValueError("order_id must map to a UUID external_id (§3.6)")

        scrubbed: dict[str, str | int] = {"external_id": external_id}

        for key, value in payload.items():
            action = PII_FIELD_RULES.get(key, DEFAULT_ACTION)
            if action is ScrubAction.ALLOW and key != "order_id":
                # Numeric amounts stay numeric; text is pattern-scrubbed.
                scrubbed[key] = value if isinstance(value, int) else self._scrub_value(str(value))
            elif action is ScrubAction.REPLACE_WITH_ORDER_REF:
                # Deal title carries an opaque reference, never the name.
                scrubbed["title"] = f"Order-{external_id}"
            elif action is ScrubAction.HASH_OR_REMOVE and self._hash_phone and value:
                scrubbed["phone_hash"] = self._sha256(str(value))
            # REMOVE / MAP_TO_EXTERNAL_ID: the field itself is never propagated.

        # Guaranteed core fields for the dispatch board (§4.3 step 4).
        scrubbed.setdefault("status", str(payload.get("status", "")))
        return scrubbed

    @staticmethod
    def _sha256(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _scrub_value(value: str) -> str:
        """Belt-and-braces: strip PII patterns from allowed free text."""
        return _PHONE_RE.sub("", _EMAIL_RE.sub("", value)).strip()
