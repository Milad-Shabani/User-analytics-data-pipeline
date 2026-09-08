"""Configuration loading.

Reads config/config.yaml for pipeline settings and environment variables
(optionally from a .env file) for anything environment-specific or secret,
such as database credentials. Keeping these separate means the same
config.yaml works unchanged across a developer laptop, CI, and production.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()  # no-op if there is no .env file (e.g. in CI)


@dataclass
class QualityThresholds:
    max_orphan_event_ratio: float = 0.05
    max_null_timestamp_ratio: float = 0.0


@dataclass
class PipelineSettings:
    profiles_glob: str
    events_glob: str
    processed_dir: str
    parquet_dir: str
    detail_fields: list[str]
    known_event_types: list[str]
    quality: QualityThresholds = field(default_factory=QualityThresholds)


def load_pipeline_settings(config_path: str | Path = "config/config.yaml") -> PipelineSettings:
    with open(config_path, "r", encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    return PipelineSettings(
        profiles_glob=raw["paths"]["profiles_glob"],
        events_glob=raw["paths"]["events_glob"],
        processed_dir=raw["paths"]["processed_dir"],
        parquet_dir=raw["paths"]["parquet_dir"],
        detail_fields=raw["pipeline"]["detail_fields"],
        known_event_types=raw["pipeline"]["known_event_types"],
        quality=QualityThresholds(
            max_orphan_event_ratio=raw["quality"]["max_orphan_event_ratio"],
            max_null_timestamp_ratio=raw["quality"]["max_null_timestamp_ratio"],
        ),
    )


def get_database_url() -> str:
    """Build a SQLAlchemy connection URL from environment variables.

    Defaults to a local SQLite file so the project runs out of the box with
    zero external services. Set DB_BACKEND=mssql or DB_BACKEND=postgres to
    target a real warehouse instead.
    """
    backend = os.getenv("DB_BACKEND", "sqlite").lower()

    if backend == "sqlite":
        sqlite_path = os.getenv("SQLITE_PATH", "./data/processed/warehouse.db")
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{sqlite_path}"

    if backend == "mssql":
        host = os.getenv("MSSQL_HOST", "localhost")
        port = os.getenv("MSSQL_PORT", "1433")
        db = os.getenv("MSSQL_DB", "AnalyticsDW")
        user = os.getenv("MSSQL_USER", "sa")
        password = os.getenv("MSSQL_PASSWORD", "")
        driver = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server").replace(" ", "+")
        return f"mssql+pyodbc://{user}:{password}@{host}:{port}/{db}" f"?driver={driver}"

    if backend == "postgres":
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "analytics")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

    raise ValueError(f"Unsupported DB_BACKEND: {backend!r}")
