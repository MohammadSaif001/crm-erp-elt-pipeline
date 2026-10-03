# ELT Pipeline Health Dashboard

A server-rendered operations dashboard for the Bronze, Silver, and Gold layers of the ELT pipeline. FastAPI serves the pages, Jinja renders the templates, and SQLAlchemy reads live MySQL status and data-quality results.

## Pages

- **Home** — pipeline health, row lineage, data-quality summary, database status, and latest run.
- **Pipeline Run** — run timestamps, stage timings, and execution log.
- **Data Quality** — null, duplicate, foreign-key, and row-count checks.
- **Database Health** — connections, server settings, and medallion table inventory.
- **Technical Details** — runtime configuration, filterable logs, and Gold schema map.

## Run locally

From the repository root:

```bash
python -m pip install -r dashboard/requirements.txt
uvicorn dashboard.app:app --reload --port 8000
```

Open <http://127.0.0.1:8000/>. The individual pages are available at `/home`, `/pipeline-run`, `/data-quality`, `/database-health`, and `/technical-details`.

You can also run from the `dashboard/` directory:

```bash
python -m pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

## Configuration

The dashboard reads database settings from `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and the `BRONZE_DB`, `SILVER_DB`, and `GOLD_DB` environment variables. For local development, it also reads the pipeline's `configs/db_config.json`. See [.env.example](.env.example) for the environment variable names.

Set `PIPELINE_LOG_PATH` to override the detected pipeline log location. Without a log file, run details and the technical log viewer show an empty state.

## Project layout

```text
dashboard/
├── app.py                 # FastAPI import target
├── main.py                # Routes and request context
├── templates/             # Jinja page templates
├── assets/styles.css      # Shared HTML styles
├── database/              # SQLAlchemy connection and query layer
├── components/            # Pipeline health calculations
└── utils/                 # Formatting, log parsing, and TTL caching
```
