"""Extraction of the user profile dimension from CSV exports.

The source system for this dataset is a CRM export. Real-world CSV exports
are frequently messy (BOM markers, whole rows wrapped in a single quoted
field, stray whitespace) — this loader is deliberately defensive about that
instead of assuming a perfectly clean file, and reports how many rows it had
to skip rather than silently swallowing bad data.
"""

from __future__ import annotations

import csv
import glob
import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = ["user_id", "name", "registration_date", "location"]


@dataclass
class ExtractionReport:
    source: str
    rows_read: int
    rows_valid: int
    rows_rejected: int


def _read_csv_robust(path: str) -> list[dict]:
    """Read a single profiles CSV, tolerating a couple of common quirks:

    - UTF-8 BOM at the start of the file
    - the entire header/row being wrapped in one extra pair of quotes,
      e.g. "1,Ali Ahmadi,2022-01-15,Tehran" instead of proper CSV quoting
    """
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header: list[str] | None = None
        for raw_row in reader:
            if not raw_row:
                continue
            # Un-wrap rows like ['1,Ali Ahmadi,2022-01-15,Tehran'] into real fields.
            if len(raw_row) == 1 and "," in raw_row[0]:
                raw_row = next(csv.reader([raw_row[0]]))

            if header is None:
                header = [h.strip() for h in raw_row]
                continue

            rows.append(dict(zip(header, (v.strip() for v in raw_row))))
    return rows


def extract_profiles(profiles_glob: str) -> tuple[pd.DataFrame, list[ExtractionReport]]:
    """Load and validate every profiles CSV matching `profiles_glob`.

    Returns a tidy, de-duplicated DataFrame (latest row wins per user_id)
    plus a per-file extraction report for observability.
    """
    all_rows: list[dict] = []
    reports: list[ExtractionReport] = []

    files = sorted(glob.glob(profiles_glob))
    if not files:
        logger.warning("No profile files matched pattern: %s", profiles_glob)

    for path in files:
        raw_rows = _read_csv_robust(path)
        valid_rows = []
        rejected = 0

        for row in raw_rows:
            if not set(EXPECTED_COLUMNS).issubset(row.keys()):
                rejected += 1
                continue
            try:
                row["user_id"] = int(row["user_id"])
                date.fromisoformat(row["registration_date"])
            except (ValueError, TypeError):
                rejected += 1
                continue
            valid_rows.append(row)

        logger.info(
            "[profiles] %s: read=%d valid=%d rejected=%d",
            path,
            len(raw_rows),
            len(valid_rows),
            rejected,
        )
        reports.append(ExtractionReport(path, len(raw_rows), len(valid_rows), rejected))
        all_rows.extend(valid_rows)

    if not all_rows:
        return pd.DataFrame(columns=EXPECTED_COLUMNS), reports

    df = pd.DataFrame(all_rows)[EXPECTED_COLUMNS]
    df["registration_date"] = pd.to_datetime(df["registration_date"]).dt.date
    df = df.drop_duplicates(subset="user_id", keep="last").reset_index(drop=True)
    return df, reports
