#!/usr/bin/env python3
"""Generate an extra day of synthetic event data.

The task ships with one real sample day (user_events_20231026.json). This
script fabricates a second day of plausible, randomized events for the same
users so the repository can demonstrate the pipeline's incremental,
multi-day behaviour (and the resulting multi-partition Parquet output)
without needing a live event stream.

Usage:
    python scripts/generate_sample_events.py --date 2023-10-27 --events 40
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

USER_IDS = [1, 2, 3, 4, 5]
PAGES = ["/home", "/category/electronics", "/product/xyz", "/cart", "/checkout", "/about_us"]
ITEMS = ["item_abc", "item_def", "item_ghi", "item_jkl"]


def random_event(user_id: int, ts: datetime) -> dict:
    event_type = random.choices(
        ["page_view", "button_click", "purchase", "app_open", "app_close"],
        weights=[0.45, 0.25, 0.1, 0.1, 0.1],
    )[0]

    details: dict = {}
    if event_type == "page_view":
        details = {"page_url": random.choice(PAGES), "duration_ms": random.randint(1000, 30000)}
    elif event_type == "button_click":
        details = {"button_id": random.choice(["buy_now_button", "filter_button", "add_to_cart"])}
    elif event_type == "purchase":
        details = {
            "item_id": random.choice(ITEMS),
            "price": random.choice([450000, 890000, 1200000, 2100000]),
            "quantity": random.randint(1, 3),
            "currency": "IRR",
        }
    elif event_type == "app_close":
        details = {"duration_session_ms": random.randint(60000, 3600000)}

    return {
        "user_id": user_id,
        "event_type": event_type,
        "timestamp": ts.isoformat().replace("+00:00", "Z"),
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--events", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir", default="data/raw/events")
    args = parser.parse_args()

    random.seed(args.seed)
    day = datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    events = []
    for _ in range(args.events):
        user_id = random.choice(USER_IDS)
        ts = day + timedelta(seconds=random.randint(0, 24 * 3600 - 1))
        events.append(random_event(user_id, ts))

    events.sort(key=lambda e: e["timestamp"])

    out_path = Path(args.out_dir) / f"user_events_{day.strftime('%Y%m%d')}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(events)} synthetic events to {out_path}")


if __name__ == "__main__":
    main()
