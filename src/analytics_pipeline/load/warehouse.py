"""Loading into the relational warehouse (SQLite / SQL Server / Postgres).

Writes are upserts keyed on `event_id`, so re-running the pipeline over
files it has already seen is a safe no-op rather than a duplicate-inserting
mess — a real gap in a naive "DROP + re-INSERT everything" approach.
"""

from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import Column, Engine, MetaData, String, Table, inspect
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

logger = logging.getLogger(__name__)

DIMENSION_TABLE = "dim_user_profiles"
FACT_TABLE = "fact_user_activity"


def write_profiles(profiles: pd.DataFrame, engine: Engine) -> None:
    if profiles.empty:
        logger.info("No profiles to write.")
        return
    profiles.to_sql(DIMENSION_TABLE, engine, if_exists="replace", index=False)
    logger.info("Wrote %d rows to %s", len(profiles), DIMENSION_TABLE)


def write_fact(fact: pd.DataFrame, engine: Engine) -> None:
    """Upsert the fact table on `event_id`.

    SQLite's `INSERT ... ON CONFLICT DO UPDATE` is used when the backend is
    SQLite (the project's zero-setup default and what CI runs against). For
    SQL Server / Postgres targets, swap this for a MERGE statement or a
    staging-table + MERGE pattern — noted here rather than implemented for
    every dialect to keep the reference implementation focused.
    """
    if fact.empty:
        logger.info("No fact rows to write.")
        return

    fact = fact.copy()
    fact["details_raw"] = fact["details_raw"].astype(str)
    fact["timestamp"] = fact["timestamp"].astype(str)
    fact["registration_date"] = fact["registration_date"].astype(str)
    fact["event_date"] = fact["event_date"].astype(str)

    inspector = inspect(engine)
    table_existed = FACT_TABLE in inspector.get_table_names()

    if not table_existed:
        # Create the table explicitly (rather than via pandas' to_sql
        # inference) so event_id is a real primary key and later upserts
        # via ON CONFLICT have something to key off.
        metadata = MetaData()
        columns = [Column(col, String, primary_key=(col == "event_id")) for col in fact.columns]
        Table(FACT_TABLE, metadata, *columns)
        metadata.create_all(engine)
        logger.info("Created empty %s with event_id as primary key", FACT_TABLE)

    if engine.dialect.name != "sqlite":
        # Reference implementation focuses on SQLite for portability; for a
        # real SQL Server/Postgres target, upsert via MERGE/staging table.
        fact.to_sql(FACT_TABLE, engine, if_exists="append", index=False)
        logger.info("Appended %d rows to %s", len(fact), FACT_TABLE)
        return

    metadata = MetaData()
    table = Table(FACT_TABLE, metadata, autoload_with=engine)
    rows = fact.to_dict(orient="records")

    with engine.begin() as conn:
        for row in rows:
            stmt = sqlite_insert(table).values(**row)
            update_cols = {c: stmt.excluded[c] for c in row if c != "event_id"}
            stmt = stmt.on_conflict_do_update(index_elements=["event_id"], set_=update_cols)
            conn.execute(stmt)

    logger.info("Upserted %d rows into %s", len(rows), FACT_TABLE)
