"""Database engine factory."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from .config import get_database_url


def get_engine(echo: bool = False) -> Engine:
    """Return a SQLAlchemy engine for whichever backend is configured.

    Using SQLAlchemy Core (rather than hand-written pyodbc calls per backend)
    means the same pipeline code runs unchanged against SQLite for local
    development/CI and against SQL Server or Postgres in production.
    """
    url = get_database_url()
    return create_engine(url, echo=echo, future=True)
