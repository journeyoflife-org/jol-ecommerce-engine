"""Audit log integrity tests — PCI DSS Req. 10."""

import pytest
from jol_commerce.audit.audit_log import AuditEntry, AuditLogger


@pytest.mark.pci
class TestAuditLogIntegrity:
    """Verify audit log is immutable, tamper-evident, and complete."""

    def test_audit_entry_has_required_fields(self) -> None:
        """Every entry must have identity, event type, timestamp, outcome."""
        entry = AuditEntry(
            actor="test_user",
            event_type="payment.created",
            outcome="success",
            transaction_ref="pi_test_123",
        )
        assert entry.actor == "test_user"
        assert entry.event_type == "payment.created"
        assert entry.outcome == "success"
        assert entry.transaction_ref == "pi_test_123"
        assert entry.timestamp  # UTC ISO timestamp
        assert entry.entry_id  # UUID

    def test_audit_entries_are_immutable(self) -> None:
        """AuditEntry is frozen — cannot be modified after creation."""
        entry = AuditEntry(actor="user1", event_type="test", outcome="success")
        with pytest.raises(AttributeError):
            entry.actor = "hacker"  # type: ignore[misc]

    def test_hash_chain_integrity(self) -> None:
        """Hash chain detects tampering."""
        logger = AuditLogger()
        logger.log("user1", "event1", "success", "txn1")
        logger.log("user2", "event2", "success", "txn2")
        logger.log("user3", "event3", "failure", "txn3")

        assert logger.entry_count == 3
        assert logger.verify_chain_integrity() is True

    def test_hash_chain_detects_tampering(self) -> None:
        """Modifying any entry breaks the hash chain."""
        logger = AuditLogger()
        logger.log("user1", "event1", "success", "txn1")
        logger.log("user2", "event2", "success", "txn2")

        # Tamper with first entry (replace the immutable tuple)
        original = logger._entries[0]
        tampered = AuditEntry(
            entry_id=original.entry_id,
            timestamp=original.timestamp,
            actor="hacker",
            event_type=original.event_type,
            outcome=original.outcome,
            transaction_ref=original.transaction_ref,
            correlation_id=original.correlation_id,
            details=original.details,
            previous_hash=original.previous_hash,
        )
        logger._entries[0] = tampered

        assert logger.verify_chain_integrity() is False

    def test_no_personal_data_in_audit_entries(self) -> None:
        """Audit entries must not contain PII values."""
        entry = AuditEntry(
            actor="user_12345",  # User ID, not name
            event_type="order.created",
            outcome="success",
            details={"order_id": "ORD-001", "country": "LT"},
        )
        # Details should contain references, not personal values
        assert "name" not in entry.details
        assert "email" not in entry.details
        assert "address" not in entry.details

    def test_query_by_event_type(self) -> None:
        logger = AuditLogger()
        logger.log("system", "payment.created", "success", "pi_1")
        logger.log("system", "order.shipped", "success", "ord_1")
        logger.log("system", "payment.created", "failure", "pi_2")

        payment_events = logger.get_entries(event_type="payment.created")
        assert len(payment_events) == 2

    def test_query_by_transaction_ref(self) -> None:
        logger = AuditLogger()
        logger.log("system", "payment.created", "success", "pi_abc")
        logger.log("webhook", "payment.confirmed", "success", "pi_abc")

        events = logger.get_entries(transaction_ref="pi_abc")
        assert len(events) == 2
