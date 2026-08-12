"""PII scrubber + one-way Bitrix24 sync tests (Blueprint §3.6, §4.3)."""

import pytest
from jol_commerce.bitrix24.pii_scrubber import PIIScrubber
from jol_commerce.bitrix24.sync_client import (
    Bitrix24SyncClient,
    SyncWriteRejectedError,
)
from jol_commerce.orders.order_lifecycle import Order, OrderStatus

EXTERNAL_ID = "6f9a1c2e-4b7d-4e8a-9c1f-2d3e4f5a6b7c"

RAW_PAYLOAD = {
    "order_id": "ORD-SECRET-1",
    "customer_name": "Jonas Žemaitis",
    "phone": "+370 600 12345",
    "email": "jonas@example.com",
    "address": "Vilniaus g. 1, Vilnius",
    "deceased_name": "Marija Žemaitienė",  # GDPR Art. 9 special category
    "status": "in_progress",
    "amount_cents": 15000,
    "currency": "EUR",
    "branch_id": "BR-7",
    "service_type": "funeral_package",
}


class TestPIIScrubber:
    def test_scrubbed_payload_carries_only_allowed_fields(self) -> None:
        scrubbed = PIIScrubber().scrub_order_payload(RAW_PAYLOAD, external_id=EXTERNAL_ID)
        assert scrubbed["external_id"] == EXTERNAL_ID
        assert scrubbed["status"] == "in_progress"
        assert scrubbed["amount_cents"] == 15000
        assert scrubbed["branch_id"] == "BR-7"
        assert scrubbed["service_type"] == "funeral_package"

    def test_special_category_data_removed_entirely(self) -> None:
        scrubbed = PIIScrubber().scrub_order_payload(RAW_PAYLOAD, external_id=EXTERNAL_ID)
        for forbidden in ("deceased_name", "email", "address", "customer_name", "order_id"):
            assert forbidden not in scrubbed
        # Values must not appear anywhere, not even under other keys.
        flat = str(scrubbed)
        assert "Marija" not in flat
        assert "jonas@" not in flat
        assert "Vilniaus" not in flat
        assert "ORD-SECRET-1" not in flat

    def test_customer_name_replaced_with_order_ref(self) -> None:
        scrubbed = PIIScrubber().scrub_order_payload(RAW_PAYLOAD, external_id=EXTERNAL_ID)
        assert scrubbed["title"] == f"Order-{EXTERNAL_ID}"

    def test_phone_hashed_not_plaintext(self) -> None:
        scrubbed = PIIScrubber().scrub_order_payload(RAW_PAYLOAD, external_id=EXTERNAL_ID)
        assert "phone" not in scrubbed
        phone_hash = scrubbed["phone_hash"]
        assert isinstance(phone_hash, str)
        assert phone_hash != RAW_PAYLOAD["phone"]
        assert len(phone_hash) == 64  # SHA-256 hex

    def test_missing_external_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="external_id"):
            PIIScrubber().scrub_order_payload(RAW_PAYLOAD, external_id="")

    def test_unknown_fields_removed_fail_closed(self) -> None:
        payload = {**RAW_PAYLOAD, "internal_note": "family dispute"}
        scrubbed = PIIScrubber().scrub_order_payload(payload, external_id=EXTERNAL_ID)
        assert "internal_note" not in scrubbed


class FakeTransport:
    def __init__(self) -> None:
        self.posted: list[dict[str, str | int]] = []

    def post_deal(self, payload: dict[str, str | int]) -> str:
        self.posted.append(payload)
        return f"DEAL-{len(self.posted)}"


class TestOneWaySync:
    def test_sync_posts_only_scrubbed_payload(self) -> None:
        transport = FakeTransport()
        client = Bitrix24SyncClient(transport)
        order = Order(
            order_id="ORD-SECRET-1",
            tenant_id="t-1",
            status=OrderStatus.IN_PROGRESS,
            total_amount_cents=15000,
            branch_id="BR-7",
            service_type="funeral_package",
            external_id=EXTERNAL_ID,
        )
        result = client.sync_order(order)

        assert result.deal_ref == "DEAL-1"
        sent = transport.posted[0]
        assert sent["external_id"] == EXTERNAL_ID
        assert "ORD-SECRET-1" not in str(sent)
        assert "customer_name" not in sent

    def test_sync_event_recorded_in_audit_chain(self) -> None:
        client = Bitrix24SyncClient(FakeTransport())
        order = Order(order_id="ORD-1", tenant_id="t-1", external_id=EXTERNAL_ID)
        client.sync_order(order)
        entries = client._audit.get_entries(event_type="bitrix24.synced")
        assert len(entries) == 1
        assert entries[0].details["direction"] == "outbound_only"

    def test_inbound_writes_always_rejected(self) -> None:
        with pytest.raises(SyncWriteRejectedError, match="ONE-WAY"):
            Bitrix24SyncClient.apply_inbound_write({"status": "completed"})
