"""Notification classification + queue tests (Blueprint §3.7)."""

import pytest
from jol_commerce.notifications.classification import (
    CHANNEL_MATRIX,
    Channel,
    ChannelNotAllowedError,
    Classification,
    assert_channel_allowed,
)
from jol_commerce.notifications.notification_service import (
    MAX_DELIVERY_ATTEMPTS,
    Notification,
    NotificationQueue,
)


class TestChannelMatrix:
    def test_confidential_only_encrypted_email(self) -> None:
        assert CHANNEL_MATRIX[Classification.CONFIDENTIAL] == {Channel.ENCRYPTED_EMAIL}

    def test_restricted_only_encrypted_email(self) -> None:
        assert CHANNEL_MATRIX[Classification.RESTRICTED] == {Channel.ENCRYPTED_EMAIL}

    def test_public_channels_exclude_email(self) -> None:
        """Public notices go via push/SMS/WhatsApp — never email (§3.7)."""
        assert Channel.EMAIL not in CHANNEL_MATRIX[Classification.PUBLIC]

    def test_sms_rejected_for_confidential(self) -> None:
        with pytest.raises(ChannelNotAllowedError):
            assert_channel_allowed(Classification.CONFIDENTIAL, Channel.SMS)

    def test_push_rejected_for_internal(self) -> None:
        with pytest.raises(ChannelNotAllowedError):
            assert_channel_allowed(Classification.INTERNAL, Channel.PWA_PUSH)


class TestNotificationQueue:
    def _notification(
        self,
        classification: Classification,
        channel: Channel,
        *,
        encrypted_payload: str = "",
    ) -> Notification:
        return Notification(
            tenant_id="t-1",
            channel=channel,
            classification=classification,
            encrypted_payload=encrypted_payload,
        )

    def test_public_sms_enqueues(self) -> None:
        queue = NotificationQueue()
        queue.enqueue(self._notification(Classification.PUBLIC, Channel.SMS))
        assert queue.pending_count == 1

    def test_confidential_requires_encrypted_payload(self) -> None:
        queue = NotificationQueue()
        with pytest.raises(ValueError, match="encrypted_payload"):
            queue.enqueue(
                self._notification(Classification.CONFIDENTIAL, Channel.ENCRYPTED_EMAIL),
            )

    def test_confidential_with_encrypted_payload_enqueues(self) -> None:
        queue = NotificationQueue()
        queue.enqueue(
            self._notification(
                Classification.CONFIDENTIAL,
                Channel.ENCRYPTED_EMAIL,
                encrypted_payload="enc:v1:ciphertext",
            ),
        )
        assert queue.pending_count == 1

    def test_channel_violation_never_queued(self) -> None:
        queue = NotificationQueue()
        with pytest.raises(ChannelNotAllowedError):
            queue.enqueue(self._notification(Classification.RESTRICTED, Channel.WHATSAPP))
        assert queue.pending_count == 0

    def test_failures_move_to_dlq_after_max_attempts(self) -> None:
        queue = NotificationQueue()
        notification = queue.enqueue(self._notification(Classification.PUBLIC, Channel.SMS))
        for _ in range(MAX_DELIVERY_ATTEMPTS):
            queue.mark_failed(notification.notification_id)
        assert queue.pending_count == 0
        assert queue.dead_letter_count == 1

    def test_task_payload_contains_id_only(self) -> None:
        """Queue hygiene: no PII in task arguments (Blueprint §3.7)."""
        queue = NotificationQueue()
        notification = queue.enqueue(self._notification(Classification.PUBLIC, Channel.SMS))
        payload = queue.task_payload(notification)
        assert set(payload) == {"notification_id"}
