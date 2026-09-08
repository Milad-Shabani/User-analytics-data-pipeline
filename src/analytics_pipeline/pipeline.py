"""Pipeline orchestration: extract -> transform -> quality gate -> load."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from .config import PipelineSettings, load_pipeline_settings
from .db import get_engine
from .extract.events import extract_events
from .extract.profiles import extract_profiles
from .load.parquet_writer import write_partitioned_parquet
from .load.warehouse import write_fact, write_profiles
from .quality.checks import QualityReport, run_quality_checks
from .transform.transformer import build_fact_table

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    profiles_loaded: int
    events_extracted: int
    fact_rows: int
    quality: QualityReport
    duration_seconds: float


def run_pipeline(
    config_path: str = "config/config.yaml", fail_on_quality: bool = True
) -> PipelineResult:
    started = time.monotonic()
    settings: PipelineSettings = load_pipeline_settings(config_path)

    logger.info("Extracting profiles from %s", settings.profiles_glob)
    profiles, profile_reports = extract_profiles(settings.profiles_glob)

    logger.info("Extracting events from %s", settings.events_glob)
    events, event_reports = extract_events(settings.events_glob)

    logger.info("Transforming: joining %d profiles with %d events", len(profiles), len(events))
    fact = build_fact_table(profiles, events, settings.detail_fields)

    quality = run_quality_checks(fact, settings.quality, settings.known_event_types)
    if not quality.passed and fail_on_quality:
        raise RuntimeError(f"Quality gate failed: {'; '.join(quality.failures)}")

    engine = get_engine()
    write_profiles(profiles, engine)
    write_fact(fact, engine)
    write_partitioned_parquet(fact, settings.parquet_dir)

    duration = time.monotonic() - started
    logger.info("Pipeline completed in %.2fs", duration)

    return PipelineResult(
        profiles_loaded=len(profiles),
        events_extracted=len(events),
        fact_rows=len(fact),
        quality=quality,
        duration_seconds=duration,
    )
