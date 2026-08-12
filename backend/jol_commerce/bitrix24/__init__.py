"""Bitrix24 Box integration — one-way dispatch sync (Blueprint §3.6).

Django/FastAPI core → PII Scrubber → Bitrix24 Box (prox01).
Sync direction is ONE-WAY ONLY: Bitrix24 never writes back, and
dispatcher actions in Bitrix24 do not affect order state.
"""

from jol_commerce.bitrix24.pii_scrubber import PII_FIELD_RULES, PIIScrubber
from jol_commerce.bitrix24.sync_client import (
    Bitrix24SyncClient,
    SyncTransport,
    SyncWriteRejectedError,
)

__all__ = [
    "PII_FIELD_RULES",
    "Bitrix24SyncClient",
    "PIIScrubber",
    "SyncTransport",
    "SyncWriteRejectedError",
]
