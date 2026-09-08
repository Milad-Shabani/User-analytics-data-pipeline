"""Core transformation: join profiles + events into the analytics fact table.

Design notes
------------
- `event_id` is generated deterministically from (user_id, timestamp,
  event_type, source_file, row position) rather than being a random UUID or
  an auto-increment identity. That makes re-runs on the same input files
  idempotent: the same input always produces the same event_id, which the
  load layer uses as the natural key for upserts.
- Fields inside the free-form `details` blob that the business cares about
  today (page_url, button_id, item_id, ...) are promoted to real columns;
  the full original blob is kept as `details_raw` so nothing is lost if a
  new field shows up in `details` tomorrow.
"""

from __future__ import annotations

import hashlib
import json
import logging

import pandas as pd

logger = logging.getLogger(__name__)


def _make_event_id(row: pd.Series) -> str:
    basis = "|".join(
        [
            str(row["user_id"]),
            row["timestamp"].isoformat(),
            str(row["event_type"]),
            str(row.get("source_file", "")),
            str(row.get("_row_seq", "")),
        ]
    )
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]


def build_fact_table(
    profiles: pd.DataFrame,
    events: pd.DataFrame,
    detail_fields: list[str],
) -> pd.DataFrame:
    """Join profiles onto events and flatten the `details` payload.

    Events for users missing from the profile dimension are kept (as a
    left join) rather than silently dropped, with profile fields left null,
    so the quality layer can measure and report the orphan rate instead of
    the pipeline hiding data loss.
    """
    if events.empty:
        return pd.DataFrame()

    events = events.copy()
    events["_row_seq"] = range(len(events))
    events["event_id"] = events.apply(_make_event_id, axis=1)
    events["event_date"] = events["timestamp"].dt.date
    events["details_raw"] = events["details"].apply(lambda d: json.dumps(d, ensure_ascii=False))

    for field in detail_fields:
        events[field] = events["details"].apply(lambda d, f=field: d.get(f))

    fact = events.merge(profiles, on="user_id", how="left", suffixes=("", "_profile"))

    ordered_cols = [
        "event_id",
        "user_id",
        "name",
        "location",
        "registration_date",
        "event_type",
        "timestamp",
        "event_date",
        "details_raw",
    ] + detail_fields
    ordered_cols = [c for c in ordered_cols if c in fact.columns]
    fact = fact[ordered_cols]

    orphan_count = fact["name"].isna().sum()
    if orphan_count:
        logger.warning(
            "%d of %d events (%.1f%%) have no matching user profile",
            orphan_count,
            len(fact),
            100 * orphan_count / len(fact),
        )

    return fact.reset_index(drop=True)
