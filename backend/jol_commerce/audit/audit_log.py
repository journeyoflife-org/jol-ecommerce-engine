"""Audit log — immutable, tamper-evident logging for PCI DSS Req. 10.

Every audit entry contains:
- User/service identity
- Event type
- UTC timestamp (NTP-synchronized)
- Outcome (success/failure)
- Transaction reference
- Correlation ID
- NO personal data values

Logs are append-only (WORM). No updates or deletes during retention.
Retention: 12 months minimum; 3 months immediately searchable.

Reference: PCI DSS v4.0.1 Requirement 10.5.1
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    """A single immutable audit log entry."""

    entry_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    actor: str = ""  # User ID, service name, or system identifier
    event_type: str = ""  # e.g., "payment.created", "order.status_changed"
    outcome: str = ""  # "success" or "failure"
    transaction_ref: str = ""  # Payment intent ID, order ID, etc.
    correlation_id: str = ""  # Links related events across services
    details: dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""  # Hash of the previous entry for tamper detection

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this entry for chain integrity.

        Returns:
            SHA-256 hex digest of the entry's serialized content.
        """
        content = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class AuditLogger:
    """Append-only audit logger with tamper-evident chaining.

    Each entry includes a hash of the previous entry, forming a
    hash chain that detects any modification to historical records.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._last_hash: str = ""

    def log(
        self,
        actor: str,
        event_type: str,
        outcome: str,
        transaction_ref: str = "",
        correlation_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Create an immutable audit log entry.

        Args:
            actor: Who performed the action (user ID, service name).
            event_type: Type of event (e.g., "payment.created").
            outcome: "success" or "failure".
            transaction_ref: Related transaction identifier.
            correlation_id: Correlation ID for tracing across services.
            details: Additional non-PII event details.

        Returns:
            The created AuditEntry.
        """
        entry = AuditEntry(
            actor=actor,
            event_type=event_type,
            outcome=outcome,
            transaction_ref=transaction_ref,
            correlation_id=correlation_id,
            details=details or {},
            previous_hash=self._last_hash,
        )

        self._entries.append(entry)
        self._last_hash = entry.compute_hash()

        return entry

    def get_entries(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        transaction_ref: str | None = None,
    ) -> list[AuditEntry]:
        """Query audit entries with optional filters.

        Args:
            event_type: Filter by event type.
            actor: Filter by actor.
            transaction_ref: Filter by transaction reference.

        Returns:
            Matching audit entries.
        """
        results = self._entries
        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if actor:
            results = [e for e in results if e.actor == actor]
        if transaction_ref:
            results = [e for e in results if e.transaction_ref == transaction_ref]
        return results

    def verify_chain_integrity(self) -> bool:
        """Verify the integrity of the audit log hash chain.

        Returns:
            True if the chain is intact, False if tampering detected.
        """
        previous_hash = ""
        for entry in self._entries:
            if entry.previous_hash != previous_hash:
                return False
            previous_hash = entry.compute_hash()
        return True

    @property
    def entry_count(self) -> int:
        """Total number of audit entries."""
        return len(self._entries)
