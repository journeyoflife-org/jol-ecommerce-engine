"""Hash chain verification tests — cryptographic tamper detection (gap 4.2)."""

from dataclasses import replace

import pytest
from jol_commerce.audit.audit_log import AuditLogger
from jol_commerce.audit.chain_verifier import verify_chain
from jol_commerce.db.provisioning.cli import export_entries_jsonl


@pytest.fixture()
def logger() -> AuditLogger:
    audit = AuditLogger()
    for i in range(5):
        audit.log(
            actor="tester",
            event_type="order.created",
            outcome="success",
            transaction_ref=f"ORD-{i}",
        )
    return audit


class TestChainVerifier:
    def test_intact_chain_verifies(self, logger: AuditLogger) -> None:
        report = verify_chain(logger._entries)
        assert report.is_intact
        assert report.verified_count == 5

    def test_tampered_historical_entry_detected_at_successor(
        self,
        logger: AuditLogger,
    ) -> None:
        """Rewriting history breaks the link at the next entry."""
        entries = list(logger._entries)
        entries[2] = replace(entries[2], outcome="failure")  # attacker edit
        report = verify_chain(entries)
        assert not report.is_intact
        assert report.first_broken_index == 3
        assert "link mismatch" in report.reason

    def test_deleted_entry_detected(self, logger: AuditLogger) -> None:
        entries = list(logger._entries)
        del entries[1]  # attacker removes a row
        report = verify_chain(entries)
        assert not report.is_intact
        assert report.first_broken_index == 1

    def test_terminal_tampering_caught_by_head_checkpoint(
        self,
        logger: AuditLogger,
    ) -> None:
        """A modified newest entry has no successor — the checkpoint catches it."""
        entries = list(logger._entries)
        head_checkpoint = entries[-1].compute_hash()
        entries[-1] = replace(entries[-1], actor="attacker")
        report = verify_chain(entries, expected_head_hash=head_checkpoint)
        assert not report.is_intact
        assert "head hash mismatch" in report.reason

    def test_head_checkpoint_passes_when_intact(self, logger: AuditLogger) -> None:
        entries = logger._entries
        report = verify_chain(entries, expected_head_hash=entries[-1].compute_hash())
        assert report.is_intact


class TestAuditExportFormat:
    def test_export_round_trips_through_verification(self, logger: AuditLogger) -> None:
        import json

        from jol_commerce.audit.audit_log import AuditEntry

        dump = export_entries_jsonl(logger._entries)
        reloaded = [AuditEntry(**json.loads(line)) for line in dump.splitlines()]
        assert verify_chain(reloaded).is_intact
