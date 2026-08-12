"""Audit hash chain verification — cryptographic tamper detection (ADR-001).

Append-only constraints stop casual modification; a periodic verifier is
the detection layer for the case where an attacker with database access
rewrites audit rows anyway. For every entry the verifier re-derives the
SHA-256 digest and re-checks the `previous_hash` link, so:

- a modified historical entry breaks the link at its successor;
- a swapped/deleted entry breaks the link where the gap is;
- a modified terminal entry is caught by the optional head checkpoint
  (the last hash an external witness — SIEM export, notarization — holds).

The verifier is pure: it operates on any sequence of `AuditEntry` loaded
from the database, an export file, or the in-memory logger, so the same
code serves the background job, the admin CLI, and the test suite.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from jol_commerce.audit.audit_log import AuditEntry

VERDICT_INTACT = "intact"
VERDICT_TAMPERED = "tampered"


@dataclass(frozen=True)
class ChainVerificationReport:
    """Outcome of one verification pass."""

    verdict: str
    verified_count: int
    first_broken_index: int = -1
    first_broken_entry_id: str = ""
    reason: str = ""

    @property
    def is_intact(self) -> bool:
        return self.verdict == VERDICT_INTACT


def verify_chain(
    entries: Sequence[AuditEntry],
    expected_head_hash: str = "",
) -> ChainVerificationReport:
    """Verify the full hash chain of an audit entry sequence.

    Args:
        entries: Audit entries in insertion order.
        expected_head_hash: If supplied (e.g. by the SIEM checkpoint),
            the recomputed hash of the final entry must match it — this
            catches tampering with the newest entry, which has no
            successor link to break.

    Returns:
        Report with the verdict and, on tampering, the first broken
        position so operators can scope the incident.
    """
    previous_hash = ""
    for index, entry in enumerate(entries):
        if entry.previous_hash != previous_hash:
            return ChainVerificationReport(
                verdict=VERDICT_TAMPERED,
                verified_count=index,
                first_broken_index=index,
                first_broken_entry_id=entry.entry_id,
                reason="previous_hash link mismatch",
            )
        previous_hash = entry.compute_hash()

    if expected_head_hash and entries and previous_hash != expected_head_hash:
        last = entries[-1]
        return ChainVerificationReport(
            verdict=VERDICT_TAMPERED,
            verified_count=len(entries),
            first_broken_index=len(entries) - 1,
            first_broken_entry_id=last.entry_id,
            reason="head hash mismatch (terminal entry modified)",
        )

    return ChainVerificationReport(verdict=VERDICT_INTACT, verified_count=len(entries))
