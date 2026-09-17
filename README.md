# User Analytics Data Pipeline

[![CI](https://github.com/Milad-Shabani/User-analytics-data-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Milad-Shabani/User-analytics-data-pipeline/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A small, **production-shaped** ETL pipeline that joins a slowly-changing user
profile dimension (CSV) with incremental daily user event streams (JSON)
into an analytics-ready fact table — published to both a relational
warehouse and partitioned Parquet — for product/marketing analytics and BI
dashboards (Power BI, etc.).

Built as a portfolio implementation of the problem described in
[`docs/PROBLEM_STATEMENT.md`](docs/PROBLEM_STATEMENT.md).

## Why this is more than a "read CSV, read JSON, join them" script

| Concern | How it's handled |
|---|---|
| Messy real-world CSV exports (BOM, quoted-whole-row) | `extract/profiles.py` parses defensively and reports rejected rows instead of crashing or silently dropping data |
| Events for users not (yet) in the profile dimension | Kept via a left join, not dropped — surfaced as an "orphan ratio" by the quality gate |
| Free-form, event-type-dependent `details` payload | Known fields are flattened to columns; the full original payload is kept in `details_raw` so nothing is lost |
| Re-running the pipeline over the same files | `event_id` is a deterministic hash (not a random UUID), so loads upsert instead of duplicating |
| Bad data reaching the warehouse | A configurable quality gate (`config/config.yaml`) fails the run on excessive orphan events or unparseable timestamps |
| Needing a real database to try it | Defaults to a local SQLite file (`DB_BACKEND=sqlite`); switch to SQL Server or Postgres with one environment variable |
| "Does this actually work" | Unit tests + a GitHub Actions workflow that lints, tests, and runs the CLI against the bundled sample data on every push |

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design
rationale.

### Pipeline flow

```mermaid
flowchart LR
    subgraph SRC["📥 Sources"]
        CSV[("user_profiles.csv<br/>CRM export")]
        JSON[("user_events_YYYYMMDD.json<br/>daily event drop")]
    end

    subgraph EXT["Extract"]
        EP["extract.profiles<br/>defensive CSV parsing<br/>row-level validation"]
        EE["extract.events<br/>JSON parsing<br/>timestamp & required-field checks"]
    end

    subgraph TRF["Transform"]
        TR["transform.transformer<br/>left join on user_id<br/>flatten details → columns<br/>derive event_date<br/>deterministic event_id"]
    end

    subgraph QLT["Quality gate"]
        QG{"orphan ratio ≤ 5%<br/>null timestamps = 0<br/>(config.yaml)"}
    end

    subgraph LOAD["Load"]
        WH[("Warehouse<br/>dim_user_profiles<br/>fact_user_activity<br/>SQLite / SQL Server / Postgres")]
        PQ[("Parquet<br/>partitioned by event_date")]
    end

    REJ["rejected-row report"]
    FAIL["❌ run stops<br/>quality report + non-zero exit"]
    BI["📊 Power BI / BI tools"]

    CSV --> EP --> TR
    JSON --> EE --> TR
    EP -.-> REJ
    EE -.-> REJ
    TR --> QG
    QG -- pass --> WH
    QG -- pass --> PQ
    QG -- fail --> FAIL
    WH --> BI
    PQ --> BI
```

### What happens during a single run

```mermaid
sequenceDiagram
    autonumber
    actor U as User / CI
    participant CLI as cli.py
    participant P as pipeline.py
    participant X as extract
    participant T as transform
    participant Q as quality
    participant W as load.warehouse
    participant PQ as load.parquet_writer

    U->>CLI: python -m analytics_pipeline.cli run
    CLI->>P: run_pipeline(config, fail_on_quality)
    P->>X: extract_profiles(profiles_glob)
    X-->>P: profiles + per-file reports
    P->>X: extract_events(events_glob)
    X-->>P: events + per-file reports
    P->>T: build_fact_table(profiles, events, detail_fields)
    T-->>P: fact table
    P->>Q: run_quality_checks(fact, thresholds, known_event_types)
    Q-->>P: QualityReport
    alt quality failed and fail_on_quality
        P--xCLI: RuntimeError - Quality gate failed
    else passed, or --no-fail-on-quality
        P->>W: write_profiles → dim_user_profiles (replace)
        P->>W: write_fact → fact_user_activity (upsert on event_id)
        P->>PQ: write_partitioned_parquet(partition by event_date)
        P-->>CLI: PipelineResult
        CLI-->>U: Done - profiles, events, fact rows, quality status
    end
```

### Idempotent re-runs

Because `event_id` is derived from the event itself rather than generated
randomly, processing the same file twice updates rows instead of duplicating
them (SQLite load path; SQL Server/Postgres currently append — see
*Possible next steps*).

```mermaid
flowchart LR
    A["Event row<br/>user_id · timestamp · event_type<br/>source_file · row position"] --> H["SHA-1 hash<br/>→ 16-char event_id"]
    H --> C{"event_id already in<br/>fact_user_activity?"}
    C -- no --> I["INSERT new row"]
    C -- yes --> UPD["UPDATE existing row<br/>ON CONFLICT DO UPDATE"]
    I --> R["✅ no duplicates on<br/>retries or backfills"]
    UPD --> R
```

## Quickstart

```bash
git clone https://github.com/Milad-Shabani/User-analytics-data-pipeline.git
cd User-analytics-data-pipeline
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" 2>/dev/null || { pip install -r requirements-dev.txt && pip install -e .; }

python -m analytics_pipeline.cli run
```

That runs the full pipeline against the bundled sample data
(`data/raw/profiles/user_profiles.csv`, `data/raw/events/user_events_20231026.json`)
using a local SQLite database — no external services required. You should
see something like:

```
Done: 5 profiles, 10 events -> 10 fact rows in 0.05s (quality PASSED)
```

Inspect the result:

```bash
python -c "import pandas as pd; print(pd.read_parquet('data/processed/user_activity_parquet').head())"
```

### Try it with more data

```bash
python scripts/generate_sample_events.py --date 2023-10-27 --events 40
python -m analytics_pipeline.cli run
```

This drops a second synthetic day of events into `data/raw/events/` and
re-runs the pipeline, producing a second `event_date=...` Parquet partition —
demonstrating the incremental, multi-day behaviour the design targets.

```mermaid
flowchart LR
    D1["user_events_20231026.json"] --> RUN(("pipeline<br/>run"))
    D2["user_events_20231027.json"] --> RUN
    RUN --> P1["user_activity_parquet/<br/>event_date=2023-10-26/"]
    RUN --> P2["user_activity_parquet/<br/>event_date=2023-10-27/"]
```

### Docker

```bash
docker compose up --build pipeline
```

### Point it at a real warehouse

Copy `.env.example` to `.env`, set `DB_BACKEND=mssql` (or `postgres`) and
fill in the connection details — no code changes required.

## Tests

```bash
pytest -v --cov=analytics_pipeline
```

Covers the CSV/JSON extraction edge cases, the join/flatten/event_id
transform logic, and the quality gate's pass/fail thresholds.

The same checks run in GitHub Actions on every push and pull request to `main`:

```mermaid
flowchart LR
    GH["push / PR to main"] --> M["matrix<br/>Python 3.10 · 3.11 · 3.12"]
    M --> INS["install<br/>requirements-dev + package"]
    INS --> LINT["lint<br/>flake8 + black --check"]
    LINT --> TEST["pytest<br/>+ coverage"]
    TEST --> SMOKE["CLI smoke run<br/>on bundled sample data"]
```

## Data model

See [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md) for full column
definitions of `dim_user_profiles` and `fact_user_activity` — the latter is
built to be dropped straight into a Power BI model (import or DirectQuery
against the warehouse table, or via the Parquet files) as a standard
star-schema fact table.

```mermaid
erDiagram
    DIM_USER_PROFILES |o--o{ FACT_USER_ACTIVITY : "user_id (left join)"

    DIM_USER_PROFILES {
        int user_id PK
        string name
        date registration_date
        string location
    }

    FACT_USER_ACTIVITY {
        string event_id PK "deterministic hash"
        int user_id FK "may have no matching profile"
        string name "null for orphan events"
        string location
        date registration_date
        string event_type
        datetime timestamp "UTC"
        date event_date "Parquet partition key"
        string details_raw "original JSON payload"
        string page_url
        string referrer
        int duration_ms
        string button_id
        string filter_param
        string item_id
        float price
        int quantity
        string currency
        int item_count
        int duration_session_ms
    }
```

## Possible next steps

- Swap the SQLite-specific upsert for a MERGE-based loader for SQL
  Server/Postgres targets.
- Orchestrate with Airflow/Dagster instead of a single CLI invocation,
  scheduling one run per day per new `user_events_*.json` file.
- Add a dbt layer on top of `fact_user_activity` for metric definitions
  (DAU, conversion rate, session length) shared across BI tools.

## License

MIT — see [LICENSE](LICENSE).
