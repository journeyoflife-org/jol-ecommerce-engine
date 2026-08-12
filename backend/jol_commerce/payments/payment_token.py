"""Payment token storage — Zero-PAN policy (Blueprint §2, §3.5).

Primary Account Numbers never touch this service. Only payment gateway
tokens and references are stored:

    PaymentToken
    ├── gateway_ref (Stripe payment_method / setup_intent ID)
    ├── token_type  (setup_intent | payment_intent | receipt_ref)
    └── encrypted_at_rest (pgcrypto AES-256 in production — §3.4)

In-person settlements store only the terminal receipt reference.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class TokenType(str, Enum):
    """Kinds of gateway references stored (never raw card data)."""

    SETUP_INTENT = "setup_intent"  # deferred authorization (§4.2)
    PAYMENT_INTENT = "payment_intent"  # immediate charge reference
    RECEIPT_REF = "receipt_ref"  # in-person terminal receipt (§3.5)


@dataclass(frozen=True)
class PaymentToken:
    """A stored gateway reference bound to a tenant and order.

    Attributes:
        tenant_id: Owning tenant (RLS boundary — §3.4).
        order_id: Order the token is linked to.
        gateway_ref: Gateway identifier (pm_xxx / seti_xxx / receipt ref).
        token_type: Classification of the gateway reference.
        encrypted_at_rest: Production stores this column pgcrypto-encrypted;
            decryption keys live in HashiCorp Vault (§3.4).
    """

    tenant_id: str
    order_id: str
    gateway_ref: str
    token_type: TokenType
    encrypted_at_rest: bool = True
    token_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stored_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class PaymentTokenStore:
    """Tenant-scoped store of gateway references (Zero-PAN)."""

    def __init__(self) -> None:
        self._tokens: dict[str, PaymentToken] = {}

    def store(self, token: PaymentToken) -> PaymentToken:
        """Persist a gateway reference; rejects anything PAN-like."""
        self._assert_zero_pan(token.gateway_ref)
        self._tokens[token.token_id] = token
        return token

    def for_order(self, tenant_id: str, order_id: str) -> list[PaymentToken]:
        """All tokens for an order inside the tenant boundary."""
        return [
            t for t in self._tokens.values() if t.tenant_id == tenant_id and t.order_id == order_id
        ]

    def get(self, token_id: str) -> PaymentToken | None:
        return self._tokens.get(token_id)

    @staticmethod
    def _assert_zero_pan(value: str) -> None:
        """Reject 13-19 digit runs — a PAN must never be stored."""
        digits = "".join(ch for ch in value if ch.isdigit())
        if 13 <= len(digits) <= 19 and value.replace(" ", "").isdigit():
            raise ValueError(
                "Zero-PAN violation: gateway_ref looks like a raw card number. "
                "Only gateway tokens (pm_xxx/seti_xxx) and receipt refs are storable.",
            )
