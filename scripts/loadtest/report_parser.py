from __future__ import annotations

import csv
import sys
from pathlib import Path


def parse_stats_csv(stats_csv: Path) -> dict:
    rows = []
    with stats_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Type") in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                rows.append(row)

    def as_float(value: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    top_by_p95 = sorted(rows, key=lambda r: as_float(r.get("95%", "0")), reverse=True)[:10]
    top_by_failures = sorted(rows, key=lambda r: as_float(r.get("Failure Count", "0")), reverse=True)[:10]

    total_requests = sum(as_float(r.get("Request Count", "0")) for r in rows)
    total_failures = sum(as_float(r.get("Failure Count", "0")) for r in rows)

    return {
        "total_requests": int(total_requests),
        "total_failures": int(total_failures),
        "failure_rate": (total_failures / total_requests * 100.0) if total_requests else 0.0,
        "top_by_p95": top_by_p95,
        "top_by_failures": top_by_failures,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/loadtest/report_parser.py <locust_stats.csv>")
        return 1

    stats_csv = Path(sys.argv[1])
    if not stats_csv.exists():
        print(f"File not found: {stats_csv}")
        return 1

    summary = parse_stats_csv(stats_csv)
    print(f"total_requests: {summary['total_requests']}")
    print(f"total_failures: {summary['total_failures']}")
    print(f"failure_rate: {summary['failure_rate']:.2f}%")

    print("\nTop 10 by p95")
    for row in summary["top_by_p95"]:
        print(f"- {row.get('Type')} {row.get('Name')} p95={row.get('95%')} failures={row.get('Failure Count')}")

    print("\nTop 10 by failures")
    for row in summary["top_by_failures"]:
        print(f"- {row.get('Type')} {row.get('Name')} failures={row.get('Failure Count')} p95={row.get('95%')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
