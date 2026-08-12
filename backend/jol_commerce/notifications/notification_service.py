"""Notification queue — PII-free task payloads (Blueprint §3.7).

Queue hygiene rules:
- No PII in queue keys or task arguments: tasks carry `notification_id`
  only; the payload is fetched from the DB at execution time.
- `confidential`+ payloads are stored encrypted (encrypted_payload).
- Delivery failures retry with exponential backoff; after 3 attempts
  the notification moves to the dead-letter queue (DLQ).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from jol_commerce.notifications.classification import (
    Channel,
    Classification,
    assert_channel_allowed,
)

MAX_DELIVERY_ATTEMPTS = 3


@dataclass(frozen=True)
class Notification:
    """A queued notification (Blueprint §3.3 NotificationQueue model).

    Attributes:
        notification_id: The ONLY value safe to carry in queue payloads.
        channel: Delivery channel (validated against the matrix).
        classification: Sensitivity class governing channel choice.
        encrypted_payload: For confidential+ content (encrypted at rest).
        recipient_ref: Opaque recipient reference (never a raw address
            in queue context; resolved from DB at execution time).
    """

    tenant_id: str
    channel: Channel
    classification: Classification
    notification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    recipient_ref: str = ""
    encrypted_payload: str = ""
    queued_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    attempts: int = 0


class NotificationQueue:
    """Enqueue with classification enforcement, retry, and DLQ."""

    def __init__(self) -> None:
        self._pending: list[Notification] = []
        self._delivered: list[Notification] = []
        self._dead_letter: list[Notification] = []

    def enqueue(self, notification: Notification) -> Notification:
        """Queue a notification after validating the channel matrix.

        Raises:
            ChannelNotAllowedError: Channel invalid for the classification.
            ValueError: If confidential+ content lacks an encrypted payload.
        """
        assert_channel_allowed(notification.classification, notification.channel)
        if (
            notification.classification in (Classification.CONFIDENTIAL, Classification.RESTRICTED)
            and not notification.encrypted_payload
        ):
            raise ValueError(
                f"{notification.classification.value} notifications require "
                "an encrypted_payload (Blueprint §3.3)",
            )
        self._pending.append(notification)
        return notification

    def mark_delivered(self, notification_id: str) -> None:
        """Move a notification from pending to delivered."""
        notification = self._pop_pending(notification_id)
        self._delivered.append(notification)

    def mark_failed(self, notification_id: str) -> Notification:
        """Record a delivery failure; DLQ after MAX_DELIVERY_ATTEMPTS.

        Returns:
            The notification, requeued or moved to the dead-letter queue.
        """
        notification = self._pop_pending(notification_id)
        # Frozen dataclass: re-create with incremented attempt count.
        retried = Notification(
            tenant_id=notification.tenant_id,
            channel=notification.channel,
            classification=notification.classification,
            notification_id=notification.notification_id,
            recipient_ref=notification.recipient_ref,
            encrypted_payload=notification.encrypted_payload,
            queued_at=notification.queued_at,
            attempts=notification.attempts + 1,
        )
        if retried.attempts >= MAX_DELIVERY_ATTEMPTS:
            self._dead_letter.append(retried)
        else:
            self._pending.append(retried)
        return retried

    def task_payload(self, notification: Notification) -> dict[str, str]:
        """Queue-safe task payload: ID only, no PII (Blueprint §3.7)."""
        return {"notification_id": notification.notification_id}

    def _pop_pending(self, notification_id: str) -> Notification:
        for index, notification in enumerate(self._pending):
            if notification.notification_id == notification_id:
                return self._pending.pop(index)
        raise LookupError(f"Notification not in pending queue: {notification_id}")

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def dead_letter_count(self) -> int:
        return len(self._dead_letter)

    @property
    def delivered_count(self) -> int:
        return len(self._delivered)
