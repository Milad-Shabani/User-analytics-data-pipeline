"""Write the analytics fact table to partitioned Parquet.

Partitioning by `event_date` is what lets downstream engines (Spark, DuckDB,
Athena/Presto, or even pandas with a date filter) prune to just the relevant
files instead of scanning the whole dataset for a query about "yesterday".
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def write_partitioned_parquet(fact: pd.DataFrame, output_dir: str) -> None:
    if fact.empty:
        logger.info("No fact rows to write to Parquet.")
        return

    fact = fact.copy()
    fact["event_date"] = pd.to_datetime(fact["event_date"])

    fact.to_parquet(
        output_dir,
        engine="pyarrow",
        partition_cols=["event_date"],
        index=False,
        existing_data_behavior="overwrite_or_ignore",
    )
    logger.info("Wrote %d rows to partitioned Parquet at %s", len(fact), output_dir)
