"""Bitrix24 Box sync client — ONE-WAY ONLY (Blueprint §3.6, §4.3).

Core → PII Scrubber → Bitrix24 Box (prox01, internal VLAN):
1. Scheduler triggers sync (5-minute cadence in production).
2. Orders changed since last_sync are collected per tenant.
3. Each payload passes through the PII Scrubber middleware.
4. Scrubbed payload POSTed to the Bitrix24 Box REST API.
5. Every sync event is recorded in the audit hash chain.

Direction enforcement: this client exposes no inbound write path.
`apply_inbound_write` exists solely to raise — codifying the rule that
Bitrix24 never writes back to the commerce core (Blueprint §2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from jol_commerce.audit.audit_log import AuditLogger
from jol_commerce.bitrix24.pii_scrubber import PIIScrubber

if TYPE_CHECKING:
    from jol_commerce.orders.order_lifecycle import Order


class SyncWriteRejectedError(RuntimeError):
    """Raised when any inbound write from Bitrix24 is attempted."""


class SyncTransport(Protocol):
    """Transport abstraction for the Bitrix24 Box REST API (prox01)."""

    def post_deal(self, payload: dict[str, str | int]) -> str:
        """POST an upserted Deal; returns the Bitrix24 deal reference."""
        ...


@dataclass(frozen=True)
class SyncResult:
    """Outcome of one order's sync to Bitrix24."""

    order_id: str
    external_id: str
    deal_ref: str
    scrubbed_payload: dict[str, str | int]


class Bitrix24SyncClient:
    """One-way scrubbed sync from the commerce core to Bitrix24 Box."""

    def __init__(
        self,
        transport: SyncTransport,
        *,
        scrubber: PIIScrubber | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self._transport = transport
        self._scrubber = scrubber or PIIScrubber()
        self._audit = audit or AuditLogger()

    def sync_order(self, order: Order) -> SyncResult:
        """Scrub and push one order's state to Bitrix24 (§4.3).

        The payload sent is exactly the scrubber output — internal order
        IDs and all personal data are stripped before crossing the
        boundary to the dispatch system.
        """
        raw_payload: dict[str, Any] = {
            "order_id": order.order_id,
            "status": order.status.value,
            "amount_cents": order.total_amount_cents,
            "currency": order.currency,
            "branch_id": order.branch_id,
            "service_type": order.service_type,
        }
        scrubbed = self._scrubber.scrub_order_payload(
            raw_payload,
            external_id=order.external_id,
        )

        deal_ref = self._transport.post_deal(scrubbed)

        # Hash-chained audit record of the sync event (§4.3 step 8).
        self._audit.log(
            actor="bitrix24_sync",
            event_type="bitrix24.synced",
            outcome="success",
            transaction_ref=order.external_id,
            details={
                "tenant_id": order.tenant_id,
                "deal_ref": deal_ref,
                "direction": "outbound_only",
            },
        )

        return SyncResult(
            order_id=order.order_id,
            external_id=order.external_id,
            deal_ref=deal_ref,
            scrubbed_payload=scrubbed,
        )

    def sync_orders(self, orders: list[Order]) -> list[SyncResult]:
        """Sync a change batch (orders modified since last_sync)."""
        return [self.sync_order(order) for order in orders]

    @staticmethod
    def apply_inbound_write(payload: dict[str, Any]) -> None:
        """Inbound writes from Bitrix24 are architecturally prohibited.

        Dispatcher actions in Bitrix24 never affect order state in the
        commerce core (Blueprint §2 — One-Way Bitrix24 Sync).
        """
        raise SyncWriteRejectedError(
            "Bitrix24 → commerce core writes are prohibited: "
            f"sync is ONE-WAY ONLY (Blueprint v2.0 §2); rejected fields: "
            f"{sorted(payload.keys())}",
        )
