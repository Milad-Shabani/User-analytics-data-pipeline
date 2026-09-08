import json
from pathlib import Path

from analytics_pipeline.extract.events import extract_events
from analytics_pipeline.extract.profiles import extract_profiles


def test_extract_profiles_handles_quoted_and_bom_rows(tmp_path: Path):
    csv_content = (
        '\ufeff"user_id,name,registration_date,location"\r\n'
        '"1,Ali Ahmadi,2022-01-15,Tehran"\r\n'
        '"2,Sara Mohammadi,2022-03-10,Isfahan"\r\n'
    )
    p = tmp_path / "user_profiles.csv"
    p.write_text(csv_content, encoding="utf-8")

    df, reports = extract_profiles(str(tmp_path / "*.csv"))

    assert len(df) == 2
    assert set(df["user_id"]) == {1, 2}
    assert reports[0].rows_rejected == 0


def test_extract_profiles_rejects_malformed_rows(tmp_path: Path):
    csv_content = (
        "user_id,name,registration_date,location\n"
        "1,Ali,not-a-date,Tehran\n"
        "2,Sara,2022-03-10,Isfahan\n"
    )
    p = tmp_path / "user_profiles.csv"
    p.write_text(csv_content, encoding="utf-8")

    df, reports = extract_profiles(str(tmp_path / "*.csv"))

    assert len(df) == 1
    assert reports[0].rows_rejected == 1


def test_extract_events_parses_details_and_timestamp(tmp_path: Path):
    events = [
        {
            "user_id": 1,
            "event_type": "page_view",
            "timestamp": "2023-10-26T10:00:15Z",
            "details": {"page_url": "/home", "duration_ms": 5000},
        },
        {
            "user_id": 2,
            "event_type": "app_open",
            "timestamp": "2023-10-26T10:05:30Z",
            "details": {},
        },
    ]
    p = tmp_path / "user_events_20231026.json"
    p.write_text(json.dumps(events), encoding="utf-8")

    df, reports = extract_events(str(tmp_path / "*.json"))

    assert len(df) == 2
    assert reports[0].events_valid == 2
    assert df.iloc[0]["details"]["page_url"] == "/home"


def test_extract_events_rejects_missing_required_fields(tmp_path: Path):
    events = [
        {
            "user_id": 1,
            "event_type": "page_view",
            "timestamp": "2023-10-26T10:00:15Z",
            "details": {},
        },
        {
            "event_type": "page_view",
            "timestamp": "2023-10-26T10:00:15Z",
            "details": {},
        },  # missing user_id
    ]
    p = tmp_path / "user_events_20231026.json"
    p.write_text(json.dumps(events), encoding="utf-8")

    df, reports = extract_events(str(tmp_path / "*.json"))

    assert len(df) == 1
    assert reports[0].events_rejected == 1
