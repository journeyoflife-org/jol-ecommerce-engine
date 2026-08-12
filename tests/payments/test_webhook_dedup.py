"""Webhook replay protection tests — dedup store + idempotent handler (gap 4.4)."""

import time
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest
from jol_commerce.payments.webhook_dedup import MINIMUM_RETENTION, WebhookEventStore
from jol_commerce.payments.webhook_handler import StripeWebhookHandler


def _event(event_id: str, event_type: str = "payment_intent.succeeded") -> Any:
    """Structural stand-in for `stripe.Event` (only the fields the handler reads)."""
    return SimpleNamespace(
        id=event_id,
        type=event_type,
        created=time.time(),
        data=SimpleNamespace(object=SimpleNamespace(id="pi_test_1")),
    )


class TestWebhookEventStore:
    def test_first_claim_succeeds_replay_rejected(self) -> None:
        store = WebhookEventStore()
        assert store.claim("evt_1") is True
        assert store.claim("evt_1") is False  # replay within 24h window
        assert store.is_processed("evt_1")

    def test_retention_below_24h_rejected(self) -> None:
        with pytest.raises(ValueError, match="at least"):
            WebhookEventStore(retention=timedelta(hours=1))

    def test_expired_entries_purged_after_window(self) -> None:
        store = WebhookEventStore()
        now = datetime.now(UTC)
        store.claim("evt_old", now=now - timedelta(hours=25))
        purged = store.purge_expired(now=now)
        assert purged == 1
        assert store.claim("evt_old", now=now) is True  # re-claimable after expiry
        # Within the window: entries survive purge and replays stay rejected.
        store.claim("evt_new", now=now)
        assert store.purge_expired(now=now) == 0
        assert store.claim("evt_new", now=now) is False

    def test_minimum_retention_is_24h(self) -> None:
        assert timedelta(hours=24) == MINIMUM_RETENTION


class TestHandlerReplayProtection:
    def test_duplicate_event_acked_without_reprocessing(self) -> None:
        handler = StripeWebhookHandler(event_store=WebhookEventStore())
        event = _event("evt_dup_1")

        first = handler.handle_event(event)
        replay = handler.handle_event(event)

        assert first["status"] == "processed"
        assert replay["status"] == "duplicate"
        # Processing ran exactly once; the replay was only acked + audited.
        entries = handler._audit.get_entries(
            event_type="webhook.payment_intent.succeeded",
        )
        assert [e.outcome for e in entries] == ["success", "duplicate"]

    def test_distinct_events_both_processed(self) -> None:
        handler = StripeWebhookHandler(event_store=WebhookEventStore())
        assert handler.handle_event(_event("evt_a"))["status"] == "processed"
        assert handler.handle_event(_event("evt_b"))["status"] == "processed"
