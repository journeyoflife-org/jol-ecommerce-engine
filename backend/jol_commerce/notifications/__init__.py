"""Notification layer — segregated by sensitivity (Blueprint §3.7).

Channel matrix:

| Classification | Channels Allowed                |
|----------------|---------------------------------|
| public         | PWA Push, SMS, WhatsApp         |
| internal       | SMS, WhatsApp, Email            |
| confidential   | Encrypted Email only            |
| restricted     | Encrypted Email only            |

Queue hygiene (Blueprint §3.7): no PII in queue payloads — tasks carry
a `notification_id` only and fetch content from the DB at execution.
"""

from jol_commerce.notifications.classification import (
    CHANNEL_MATRIX,
    Channel,
    ChannelNotAllowedError,
    Classification,
)
from jol_commerce.notifications.notification_service import (
    Notification,
    NotificationQueue,
)

__all__ = [
    "CHANNEL_MATRIX",
    "Channel",
    "ChannelNotAllowedError",
    "Classification",
    "Notification",
    "NotificationQueue",
]
