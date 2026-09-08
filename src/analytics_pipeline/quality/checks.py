"""Lightweight data-quality gate.

Rather than a heavyweight framework, this is a handful of explicit checks
that produce a structured report and can fail the run when a configured
threshold is breached — enough to catch "the join silently dropped half the
events" or "a whole day of timestamps failed to parse" before bad data
reaches the warehouse or a dashboard.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from ..config import QualityThresholds

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    total_events: int
    orphan_events: int
    orphan_ratio: float
    null_timestamp_ratio: float
    unknown_event_types: list[str]
    passed: bool
    failures: list[str]


def run_quality_checks(
    fact: pd.DataFrame,
    thresholds: QualityThresholds,
    known_event_types: list[str],
) -> QualityReport:
    if fact.empty:
        return QualityReport(0, 0, 0.0, 0.0, [], True, [])

    total = len(fact)
    orphans = int(fact["name"].isna().sum())
    orphan_ratio = orphans / total
    null_ts_ratio = float(fact["timestamp"].isna().mean())
    unknown_types = sorted(set(fact["event_type"].unique()) - set(known_event_types))

    failures: list[str] = []
    if orphan_ratio > thresholds.max_orphan_event_ratio:
        failures.append(
            f"orphan event ratio {orphan_ratio:.2%} exceeds threshold "
            f"{thresholds.max_orphan_event_ratio:.2%}"
        )
    if null_ts_ratio > thresholds.max_null_timestamp_ratio:
        failures.append(
            f"null timestamp ratio {null_ts_ratio:.2%} exceeds threshold "
            f"{thresholds.max_null_timestamp_ratio:.2%}"
        )

    report = QualityReport(
        total_events=total,
        orphan_events=orphans,
        orphan_ratio=orphan_ratio,
        null_timestamp_ratio=null_ts_ratio,
        unknown_event_types=unknown_types,
        passed=not failures,
        failures=failures,
    )

    if unknown_types:
        logger.info("Encountered event types not in known_event_types: %s", unknown_types)
    if not report.passed:
        logger.error("Quality checks FAILED: %s", "; ".join(failures))
    else:
        logger.info(
            "Quality checks passed (orphan_ratio=%.2f%%, null_ts_ratio=%.2f%%)",
            orphan_ratio * 100,
            null_ts_ratio * 100,
        )

    return report
