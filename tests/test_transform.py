from datetime import date, datetime, timezone

import pandas as pd

from analytics_pipeline.transform.transformer import build_fact_table

DETAIL_FIELDS = ["page_url", "button_id", "item_id", "price"]


def _profiles():
    return pd.DataFrame(
        [
            {
                "user_id": 1,
                "name": "Ali Ahmadi",
                "registration_date": date(2022, 1, 15),
                "location": "Tehran",
            },
        ]
    )


def _events():
    return pd.DataFrame(
        [
            {
                "user_id": 1,
                "event_type": "page_view",
                "timestamp": datetime(2023, 10, 26, 10, 0, 15, tzinfo=timezone.utc),
                "details": {"page_url": "/home"},
                "source_file": "user_events_20231026.json",
            },
            {
                "user_id": 99,  # no matching profile -> should surface as orphan
                "event_type": "app_open",
                "timestamp": datetime(2023, 10, 26, 10, 5, 30, tzinfo=timezone.utc),
                "details": {},
                "source_file": "user_events_20231026.json",
            },
        ]
    )


def test_build_fact_table_joins_and_flattens_details():
    fact = build_fact_table(_profiles(), _events(), DETAIL_FIELDS)

    assert len(fact) == 2
    assert "event_id" in fact.columns
    assert fact.loc[fact["user_id"] == 1, "page_url"].iloc[0] == "/home"
    assert fact.loc[fact["user_id"] == 1, "name"].iloc[0] == "Ali Ahmadi"


def test_build_fact_table_keeps_orphan_events_with_null_profile_fields():
    fact = build_fact_table(_profiles(), _events(), DETAIL_FIELDS)

    orphan = fact.loc[fact["user_id"] == 99].iloc[0]
    assert pd.isna(orphan["name"])


def test_event_id_is_deterministic_for_repeated_runs():
    fact1 = build_fact_table(_profiles(), _events(), DETAIL_FIELDS)
    fact2 = build_fact_table(_profiles(), _events(), DETAIL_FIELDS)

    assert list(fact1["event_id"]) == list(fact2["event_id"])
