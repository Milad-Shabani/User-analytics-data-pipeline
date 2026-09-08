import pandas as pd

from analytics_pipeline.config import QualityThresholds
from analytics_pipeline.quality.checks import run_quality_checks


def _fact(names, timestamps, event_types):
    return pd.DataFrame({"name": names, "timestamp": timestamps, "event_type": event_types})


def test_quality_passes_within_thresholds():
    fact = _fact(["Ali", "Sara"], ["2023-10-26T10:00:00Z"] * 2, ["page_view", "app_open"])
    thresholds = QualityThresholds(max_orphan_event_ratio=0.5, max_null_timestamp_ratio=0.0)

    report = run_quality_checks(fact, thresholds, known_event_types=["page_view", "app_open"])

    assert report.passed
    assert report.orphan_events == 0


def test_quality_fails_when_orphan_ratio_exceeds_threshold():
    fact = _fact([None, None, "Ali"], ["2023-10-26T10:00:00Z"] * 3, ["page_view"] * 3)
    thresholds = QualityThresholds(max_orphan_event_ratio=0.1, max_null_timestamp_ratio=1.0)

    report = run_quality_checks(fact, thresholds, known_event_types=["page_view"])

    assert not report.passed
    assert report.orphan_events == 2
    assert any("orphan" in f for f in report.failures)


def test_quality_flags_unknown_event_types_without_failing():
    fact = _fact(["Ali"], ["2023-10-26T10:00:00Z"], ["mystery_event"])
    thresholds = QualityThresholds(max_orphan_event_ratio=1.0, max_null_timestamp_ratio=1.0)

    report = run_quality_checks(fact, thresholds, known_event_types=["page_view"])

    assert report.passed
    assert report.unknown_event_types == ["mystery_event"]
