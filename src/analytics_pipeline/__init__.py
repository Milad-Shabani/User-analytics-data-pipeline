"""Realtime User Analytics Pipeline.

A small, production-shaped ETL/ELT pipeline that combines a slowly-changing
user profile dimension (CSV exports) with incremental daily user event
streams (JSON) into an analytics-ready fact table, published both to a
relational warehouse and to partitioned Parquet files.
"""

__version__ = "1.0.0"
