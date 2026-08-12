"""Notification classification and channel policy (Blueprint §3.7).

Special category data (bereavement follow-ups, payment failures) must
never traverse insecure channels. The channel matrix is enforced in
code at enqueue time — fail-closed.
"""

from __future__ import annotations

from enum import Enum


class Classification(str, Enum):
    """Sensitivity classes for outbound notifications (Blueprint §3.7)."""

    PUBLIC = "public"  # e.g. "Your order #1234 is confirmed"
    INTERNAL = "internal"  # e.g. "Service scheduled for tomorrow 10:00"
    CONFIDENTIAL = "confidential"  # e.g. "Payment failed — update method"
    RESTRICTED = "restricted"  # e.g. "Bereavement follow-up resources"


class Channel(str, Enum):
    """Delivery channels (EU gateway endpoints only — Blueprint §3.7)."""

    PWA_PUSH = "pwa_push"  # Web Push via VAPID — non-sensitive only
    SMS = "sms"  # Twilio/Vonage EU gateway
    WHATSAPP = "whatsapp"  # Meta Business API (DPA executed)
    EMAIL = "email"  # SMTP-TLS / SendGrid EU region
    ENCRYPTED_EMAIL = "encrypted_email"  # confidential+ content only


class ChannelNotAllowedError(ValueError):
    """Raised when a channel is not permitted for a classification."""


# Mandatory channel matrix (Blueprint §3.7).
CHANNEL_MATRIX: dict[Classification, set[Channel]] = {
    Classification.PUBLIC: {Channel.PWA_PUSH, Channel.SMS, Channel.WHATSAPP},
    Classification.INTERNAL: {Channel.SMS, Channel.WHATSAPP, Channel.EMAIL},
    Classification.CONFIDENTIAL: {Channel.ENCRYPTED_EMAIL},
    Classification.RESTRICTED: {Channel.ENCRYPTED_EMAIL},
}


def assert_channel_allowed(classification: Classification, channel: Channel) -> None:
    """Enforce the channel matrix at enqueue time (fail-closed).

    Raises:
        ChannelNotAllowedError: If the channel is not permitted for the
            classification. PWA push additionally never carries names,
            addresses, or service details (non-sensitive only).
    """
    allowed = CHANNEL_MATRIX[classification]
    if channel not in allowed:
        raise ChannelNotAllowedError(
            f"Channel '{channel.value}' is not allowed for "
            f"classification '{classification.value}'. "
            f"Allowed: {sorted(c.value for c in allowed)}",
        )
