"""Convert a JSON Lines event log into a CSV file.

This utility reads an event log produced by ``EventStore`` (a JSON
Lines file containing entries with ``type`` and ``data`` fields) and
writes a comma‑separated values (CSV) file.  Each row in the CSV
corresponds to one event.  The default behaviour extracts a set of
common fields across event types and leaves missing values blank.

Usage::

    python event_log_to_csv.py --input artifacts/events/events.jsonl \
        --output artifacts/events/events.csv

If the ``--input`` argument is omitted, the script looks for the
``EVENT_STORE_PATH`` environment variable.  The ``--fields`` option
allows you to specify a comma‑separated list of fields to include in
the CSV.  By default the script includes::

    event_type, timestamp, product_id, side, size, price,
    client_order_id, daily_pnl

Fields not present in a given event are left blank in the output.

The script assumes that each line of the input file contains a
JSON object with at least a ``type`` key and a ``data`` key.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert event log to CSV")
    parser.add_argument(
        "--input",
        "-i",
        default=os.environ.get("EVENT_STORE_PATH"),
        help="Path to the JSON Lines event log. Defaults to ENV EVENT_STORE_PATH.",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Path to the output CSV file. Defaults to input path with .csv extension.",
    )
    parser.add_argument(
        "--fields",
        "-f",
        default="event_type,timestamp,product_id,side,size,price,client_order_id,daily_pnl",
        help="Comma‑separated list of fields to include in the CSV."
        "The 'event_type' field is always included.",
    )
    return parser.parse_args()


def read_events(path: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            # Each entry expected to have 'type' and 'data'
            event_type = obj.get("type")
            data = obj.get("data") or {}
            if not isinstance(data, dict):
                data = {}
            record = {"event_type": event_type}
            record.update(data)
            events.append(record)
    return events


def write_csv(events: List[Dict[str, Any]], output_path: str, fields: List[str]) -> None:
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for event in events:
            row = {key: event.get(key, "") for key in fields}
            writer.writerow(row)


def main() -> None:
    args = parse_args()
    input_path = args.input
    if not input_path:
        raise SystemExit("Input file must be specified via --input or EVENT_STORE_PATH")
    output_path = args.output or (os.path.splitext(input_path)[0] + ".csv")
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]
    # Always include event_type
    if "event_type" not in fields:
        fields.insert(0, "event_type")
    events = read_events(input_path)
    write_csv(events, output_path, fields)
    print(f"Wrote {len(events)} events to {output_path}")


if __name__ == "__main__":
    main()
