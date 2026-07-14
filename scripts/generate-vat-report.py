#!/usr/bin/env python3
"""Generate VAT report for a given period and country.

Usage:
    python scripts/generate-vat-report.py --country LT --from 2026-01-01 --to 2026-06-30
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate VAT report")
    parser.add_argument("--country", required=True, help="ISO country code (e.g., LT)")
    parser.add_argument("--from", dest="from_date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="to_date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--output", default=None, help="Output file path (JSON)")
    args = parser.parse_args()

    from_date = datetime.strptime(args.from_date, "%Y-%m-%d").replace(tzinfo=UTC).date()
    to_date = datetime.strptime(args.to_date, "%Y-%m-%d").replace(tzinfo=UTC).date()

    report = {
        "report_type": "vat_summary",
        "country": args.country.upper(),
        "period": {
            "from": from_date.isoformat(),
            "to": to_date.isoformat(),
        },
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "summary": {
            "total_transactions": 0,
            "total_net": "0.00",
            "total_vat": "0.00",
            "total_gross": "0.00",
            "vat_rate_applied": "TBD",
        },
        "note": "Connect to production database for actual data.",
    }

    output = json.dumps(report, indent=2)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Report written to {args.output}")  # noqa: T201
    else:
        print(output)  # noqa: T201


if __name__ == "__main__":
    main()
