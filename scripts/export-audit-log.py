#!/usr/bin/env python3
"""Export audit log entries for a given period.

PCI DSS Req. 10: Audit logs must be retrievable for at least 12 months.

Usage:
    python scripts/export-audit-log.py --from 2026-01-01 --to 2026-06-30
    python scripts/export-audit-log.py --event-type payment.created
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export audit log entries")
    parser.add_argument("--from", dest="from_date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--event-type", help="Filter by event type")
    parser.add_argument("--actor", help="Filter by actor")
    parser.add_argument("--output", default=None, help="Output file path (JSON)")
    args = parser.parse_args()

    # In production, this queries the audit log database/store
    export = {
        "export_type": "audit_log",
        "filters": {
            "from": args.from_date,
            "to": args.to_date,
            "event_type": args.event_type,
            "actor": args.actor,
        },
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "entries": [],
        "note": "Connect to production audit store for actual data.",
    }

    output = json.dumps(export, indent=2)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Audit log exported to {args.output}")  # noqa: T201
    else:
        print(output)  # noqa: T201


if __name__ == "__main__":
    main()
