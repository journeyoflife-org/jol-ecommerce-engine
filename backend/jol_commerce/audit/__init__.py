"""Audit module — immutable, tamper-evident audit logging.

PCI DSS v4.0.1 Requirement 10:
- Every payment event logged with identity, timestamp, outcome
- 12+ months retention; 3 months immediately searchable
- Write-once/append-only (WORM) storage
- Automated SIEM review (Req. 10.4.1.1)

Reference: https://withpci.com/requirements/10/10.5/10.5.1
"""
