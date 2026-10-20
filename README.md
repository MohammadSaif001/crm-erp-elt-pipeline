# CRM ERP ELT Pipeline

An end-to-end Python and MySQL ELT pipeline that combines CRM and ERP source
data into a three-layer Medallion architecture. The project includes
data-quality checks, ingestion logging, analytical Gold tables, and a FastAPI
operations dashboard.

## Overview

The pipeline loads six CSV files, standardizes and validates the records, and
publishes analytics-ready customer, product, and sales data:

```text
CRM + ERP CSV files
        │
        ▼
Bronze ── raw source-aligned data and ingestion metadata
        │
        ▼
Silver ── cleaned, standardized, validated, deduplicated data
        │
        ▼
Gold ──── customer and product dimensions plus the sales fact table
        │
        ▼
FastAPI dashboard and data-quality reports
```

## Key capabilities

- Loads CRM customer, product, and sales data alongside ERP customer,
  location, and product-category data.
- Tracks source-file ingestion and supports repeatable pipeline runs.
- Applies transformations in separate Bronze, Silver, and Gold stages.
- Checks nulls, duplicate keys, row counts, and foreign-key integrity.
- Provides an operations dashboard with pipeline health, run details,
  database status, data quality, and technical information.
- Keeps credentials and local environment settings outside version control.

## Repository layout

```text
configs/
└── pipeline_config.yaml        # Bronze source-to-table mappings
data/
├── raw/source_crm/             # CRM input CSV files
├── raw/source_erp/             # ERP input CSV files
└── logs/pipeline.log           # Generated pipeline log
dashboard/
├── app.py                      # FastAPI application import target
├── main.py                     # Dashboard routes and request context
├── templates/                  # Jinja HTML templates
├── database/                   # Dashboard database queries
└── utils/                      # Health, caching, formatting, and log helpers
docs/data_catalog.md            # Gold-layer table and column reference
sql/
├── bootstrap/                  # Pipeline metadata tables
├── bronze/                     # Bronze-layer DDL
└── silver/ and gold/           # Downstream-layer DDL
src/
├── extract/                    # CSV reading and schema validation
├── bronze/                     # Raw ingestion
├── silver/                     # CRM and ERP transformations
├── gold/                       # Analytics-layer preparation
├── database_checks/            # Data-quality checks
└── core/                       # Configuration, paths, logging, and database helpers
tests/                          # Unit, dashboard, and integration tests
```

## Requirements

- Python 3.14 or newer
- MySQL 8.0 or newer
- A MySQL user with permission to create and write the Bronze, Silver, and
  Gold databases

The project uses [`uv`](https://docs.astral.sh/uv/) as its package manager.
Dependencies are declared in [`pyproject.toml`](pyproject.toml) and pinned in
[`uv.lock`](uv.lock). The repository also includes
[`requirements.txt`](requirements.txt) for installing the pipeline's core
dependencies with pip.

## Installation

Install `uv` first if it is not already available, then run the following from
the repository root:

```bash
uv sync
```

`uv sync` creates or updates the project virtual environment and installs the
locked dependencies. Use `uv run` for project commands so they always run in
that environment; manual activation is not required.

```bash
uv run python --version
```

## Configure MySQL

Create a root-level `.env` file for the pipeline and dashboard database
settings. The dashboard's example file includes the required variable names:

```bash
cp dashboard/.env.example .env
```

Set `DB_HOST`, `DB_PORT`, `DB_USER`, and `DB_PASSWORD`. The database names
`BRONZE_DB`, `SILVER_DB`, and `GOLD_DB` default to `bronze_db`, `silver_db`,
and `gold_db`. Optional connection pool and timeout settings are
`DB_CONNECT_TIMEOUT`, `DB_POOL_SIZE`, and `DB_POOL_RECYCLE`. The MySQL user
needs permission to create databases and tables as well as read and write
their data; the pipeline creates a layer database if it does not exist.

The source files and their Bronze targets are defined in
[`configs/pipeline_config.yaml`](configs/pipeline_config.yaml). The expected
Gold-layer schema is documented in [`docs/data_catalog.md`](docs/data_catalog.md).

## Run the pipeline

Run the full ELT process from the repository root:

```bash
uv run python -m src.pipeline --run-pipeline
```

The pipeline reads the six CSV files under `data/raw/`, creates the configured
Bronze, Silver, and Gold databases and tables, and writes execution details to
`data/logs/pipeline.log`. You can run an individual layer with
`--run-bronze`, `--run-silver`, or `--run-gold` instead of `--run-pipeline`.
Each invocation requires exactly one of these flags.

## Run the dashboard

The dashboard is built with FastAPI, Jinja, and SQLAlchemy. It can be started
from the repository root:

```bash
uv run uvicorn dashboard.app:app --reload --port 8000
```

The dashboard can also be launched through the pipeline CLI with
`uv run python -m src.pipeline --run-dashboard`.

| Page | URL | Purpose |
| --- | --- | --- |
| Home | `/home` | Overall pipeline health and row lineage |
| Pipeline Run | `/pipeline-run` | Run timestamps, stage timings, and logs |
| Data Quality | `/data-quality` | Null, duplicate, foreign-key, and row-count checks |
| Database Health | `/database-health` | MySQL status and Medallion table inventory |
| Technical Details | `/technical-details` | Runtime configuration, logs, and Gold schema |

The dashboard uses the same root `.env` file as the pipeline. Set
`PIPELINE_LOG_PATH` there only if you want to override the default log path.
If the log file is absent, the dashboard shows an empty log state. The root URL
redirects to `/home`.

## Run tests

Run the default unit and dashboard test suite:

```bash
uv run pytest
```

Run focused tests:

```bash
uv run pytest tests/test_transformations.py
uv run pytest tests/test_dashboard_html.py
```

Database integration tests require reachable and configured Bronze, Silver, and
Gold databases:

```bash
uv run pytest -m integration tests/test_pipeline.py tests/test_data_quality.py
```

## Data quality

The quality checks cover:

- Missing values in required fields
- Duplicate business and surrogate keys
- Row-count expectations between layers
- Foreign-key integrity between Gold dimensions and facts

The dashboard presents these checks against the current MySQL state. See
[`tests/README.md`](tests/README.md) for the test categories and their
database requirements.

## Troubleshooting

- **Cannot connect to MySQL:** verify that MySQL is running, the configured
  port is reachable, and the user has permissions for all three databases.
- **Missing configuration:** confirm that the root `.env` file exists and
  contains `DB_USER` and `DB_PASSWORD` along with the appropriate host and port.
- **Empty pipeline log:** set `PIPELINE_LOG_PATH` to the generated
  `data/logs/pipeline.log` path.
- **Integration tests fail locally:** run the unit tests first, then run the
  integration marker only after the MySQL layers are available.

## Security and Git hygiene

- Never commit `.env`, passwords, or API keys.
- Keep raw and generated data separate from source code.
- Review changes to SQL and pipeline configuration before running them against
  shared databases.

## License

This project is licensed under the [MIT License](LICENSE).
