"""Extraction of incremental user event files (JSON).

Each file represents one day of clickstream-style events, arriving with a
`user_events_YYYYMMDD.json` naming convention. The pipeline discovers files
by glob so new days show up automatically with no code change, and processing
is idempotent: re-running on the same files does not duplicate rows (see
`load.warehouse.write_events`, which upserts on a deterministic event key).
"""

from __future__ import annotations

import glob
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ["user_id", "event_type", "timestamp"]


@dataclass
class ExtractionReport:
    source: str
    events_read: int
    events_valid: int
    events_rejected: int


def _parse_timestamp(value: str) -> datetime:
    # Source timestamps are ISO-8601 with a trailing "Z"; normalize to UTC.
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def extract_events(events_glob: str) -> tuple[pd.DataFrame, list[ExtractionReport]]:
    """Load every event file matching `events_glob` into one flat DataFrame.

    The variable `details` blob is preserved verbatim (as `details_raw`, a
    JSON string) alongside a handful of promoted columns so downstream
    consumers get both the flattened fields they usually need and the full
    original payload for anything unusual.
    """
    records: list[dict] = []
    reports: list[ExtractionReport] = []

    files = sorted(glob.glob(events_glob))
    if not files:
        logger.warning("No event files matched pattern: %s", events_glob)

    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            raw_events = json.load(f)

        valid = 0
        rejected = 0
        for event in raw_events:
            if not all(k in event and event[k] not in (None, "") for k in REQUIRED_FIELDS):
                rejected += 1
                logger.debug("Rejected event missing required fields: %s", event)
                continue
            try:
                ts = _parse_timestamp(event["timestamp"])
            except (ValueError, TypeError):
                rejected += 1
                logger.debug("Rejected event with unparseable timestamp: %s", event)
                continue

            details = event.get("details") or {}
            record = {
                "user_id": int(event["user_id"]),
                "event_type": str(event["event_type"]),
                "timestamp": ts,
                "details": details,
                "source_file": path,
            }
            records.append(record)
            valid += 1

        logger.info(
            "[events] %s: read=%d valid=%d rejected=%d",
            path,
            len(raw_events),
            valid,
            rejected,
        )
        reports.append(ExtractionReport(path, len(raw_events), valid, rejected))

    if not records:
        return pd.DataFrame(columns=REQUIRED_FIELDS + ["details", "source_file"]), reports

    df = pd.DataFrame.from_records(records)
    return df, reports
