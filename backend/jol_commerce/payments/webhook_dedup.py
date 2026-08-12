"""Webhook event deduplication — replay protection (gap 4.4).

Stripe may deliver the same event more than once (retries, operational
re-sends). Without deduplication, a replayed `payment_intent.succeeded`
can fulfil an order twice, and a replayed refund event can double a
commission reversal. The store records processed event IDs for a
**24-hour minimum** window and rejects repeats.

Contract with the HTTP layer: the webhook route returns 200 to Stripe
ONLY after `StripeWebhookHandler.handle_event` completes — processing is
synchronous and the dedup claim happens before dispatch, so a crash
before completion leaves the event unclaimed and Stripe will retry.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

# Stripe retries webhooks for up to 3 days; 24h is the required minimum,
# production deployments should raise this via configuration.
MINIMUM_RETENTION = timedelta(hours=24)


@dataclass(frozen=True)
class _ProcessedEvent:
    event_id: str
    processed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class WebhookEventStore:
    """Deduplication table for processed webhook event IDs."""

    def __init__(self, retention: timedelta = MINIMUM_RETENTION) -> None:
        if retention < MINIMUM_RETENTION:
            raise ValueError(
                f"Dedup retention must be at least {MINIMUM_RETENTION} "
                "(replay window requirement, gap 4.4)",
            )
        self._retention = retention
        self._processed: dict[str, _ProcessedEvent] = {}

    def claim(self, event_id: str, *, now: datetime | None = None) -> bool:
        """Atomically claim an event for processing.

        Returns:
            True on first claim (caller must process); False if the event
            was already processed within the retention window (replay —
            caller must skip and ack).
        """
        moment = now or datetime.now(UTC)
        self.purge_expired(now=moment)
        if not event_id or event_id in self._processed:
            return False
        self._processed[event_id] = _ProcessedEvent(event_id=event_id, processed_at=moment)
        return True

    def is_processed(self, event_id: str) -> bool:
        return event_id in self._processed

    def purge_expired(self, *, now: datetime | None = None) -> int:
        """Drop entries older than the retention window."""
        moment = now or datetime.now(UTC)
        cutoff = moment - self._retention
        expired = [
            event_id for event_id, record in self._processed.items() if record.processed_at < cutoff
        ]
        for event_id in expired:
            del self._processed[event_id]
        return len(expired)

    @property
    def size(self) -> int:
        return len(self._processed)


def new_event_id() -> str:
    """Generate a Stripe-style event ID for tests/simulations."""
    return f"evt_{uuid.uuid4().hex[:24]}"
