# Problem Statement

## Context

You're the data engineer on the analytics team of **Nova Retail**, a mid-size
e-commerce platform. Two teams — Product and Marketing — need a single,
trustworthy view of "what are users doing on the platform", refreshed daily,
to power funnels, cohort analysis, and a Power BI reporting layer.

Today that view doesn't exist. The data lives in two disconnected places:

1. **A user profile export** (`user_profiles.csv`) pulled periodically from
   the CRM. Slowly-changing dimension data: `user_id`, `name`,
   `registration_date`, `location`. Small, but not always clean — CRM
   exports have shown up with BOM markers, inconsistent quoting, and the
   occasional malformed row.

2. **Daily event files** (`user_events_YYYYMMDD.json`) dropped by the
   application's event tracker. Each file is a day of raw interaction
   events: page views, button clicks, app open/close, purchases. Every
   event has a stable envelope (`user_id`, `event_type`, `timestamp`) around
   a **free-form `details` object** whose shape depends on `event_type` and
   is sometimes empty.

## Goal

Design and build a pipeline that turns these two raw, independently-evolving
sources into one **analytics-ready fact table**, and does it in a way that
survives being run every day, forever, without manual intervention.

Concretely, the pipeline must:

- **Discover input automatically.** New daily event files should be picked
  up without a code change — no hardcoded filenames.
- **Join profiles to events on `user_id`**, keeping events that don't (yet)
  have a matching profile rather than silently dropping them.
- **Flatten the useful parts of `details`** (`page_url`, `button_id`,
  `item_id`, `price`, `quantity`, `currency`, ...) into real columns, while
  preserving the original payload so nothing is lost if a new field appears.
- **Derive `event_date`** from `timestamp` for partitioning and day-level
  reporting.
- **Be idempotent.** Running the pipeline twice over the same files must not
  duplicate rows — a rerun after a failure, or a backfill, should be safe.
- **Fail loudly on bad data**, not silently. If a meaningful fraction of
  events can't be matched to a profile, or timestamps can't be parsed, the
  run should say so clearly rather than publishing a quietly-broken dataset.
- **Publish to two destinations**: a relational warehouse table (for ad hoc
  SQL and Power BI's import/DirectQuery) and **partitioned Parquet**
  (`event_date` as the partition key) for cheap, engine-agnostic analytical
  access from tools like Spark, DuckDB, or Athena.
- **Run anywhere with zero setup** — a contributor or CI runner should be
  able to clone the repo and get a working end-to-end run against the
  bundled sample data with no external database to provision, while still
  supporting a real SQL Server or Postgres warehouse via configuration.

## Non-goals

- Real-time/streaming ingestion — daily batch files are the given input
  shape; a streaming rewrite is a natural "next step" but out of scope here.
- Building the Power BI report itself — this repo stops at a clean,
  well-modeled fact + dimension table ready to be plugged into one.

## Expected output

A fact table (`fact_user_activity`) with, at minimum:

| column              | description                                   |
|---------------------|------------------------------------------------|
| event_id            | deterministic unique id for the event          |
| user_id             | joins to the profile dimension                 |
| name, location, registration_date | from the profile dimension       |
| event_type          | e.g. `page_view`, `purchase`                   |
| timestamp           | original event timestamp (UTC)                 |
| event_date          | date extracted from `timestamp`, used to partition |
| details_raw         | original `details` payload, as JSON            |
| page_url, button_id, item_id, price, quantity, currency, ... | flattened from `details` |

plus a matching `dim_user_profiles` dimension table.
