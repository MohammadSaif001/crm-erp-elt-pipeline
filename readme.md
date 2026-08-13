# ELT Data Engineering Pipeline

Python and MySQL ELT pipeline using a Medallion architecture, with a Streamlit dashboard for monitoring the pipeline and its data quality.

## What it does

`CSV files (CRM + ERP) → Bronze → Silver → Gold → Dashboard`

- **Bronze:** loads the six source CSV files without changing the raw data.
- **Silver:** cleans, validates, standardizes, and deduplicates records.
- **Gold:** creates `dim_customers`, `dim_products`, and `fact_sales` views for analytics.
- **Dashboard:** shows pipeline status, data-quality results, database health, and technical details.

## Project layout

```text
configs/       Pipeline and local database configuration
data/raw/      CRM and ERP source CSV files
src/           Pipeline, transformations, and data-quality checks
sql/           MySQL table and view definitions
dashboard/     Streamlit monitoring dashboard
tests/          Pipeline and transformation tests
```

## Prerequisites

- Python 3.10+
- MySQL 8+

## Run the pipeline

Install dependencies from the project root:

```bash
pip install -r requirements.txt
```

Create `configs/db_config.json` locally with your MySQL credentials. This file is intentionally ignored by Git.

```json
{
  "mysql": {
    "host": "localhost",
    "port": 3306,
    "user": "your_user",
    "password": "your_password",
    "bronze_db": "bronze_db",
    "silver_db": "silver_db",
    "gold_db": "gold_db"
  }
}
```

Run the full pipeline:

```bash
python -m src.pipeline
```

## Run the dashboard

The dashboard has five pages: **Home**, **Pipeline Run**, **Data Quality**, **Database Health**, and **Technical Details**.

```bash
cd dashboard
pip install -r requirements.txt
cp .env.example .env
```

Set the database values in `.env`, then load them and start Streamlit:

```bash
set -a; source .env; set +a
streamlit run app.py
```

`PIPELINE_LOG_PATH` is optional. When set, the dashboard displays the latest pipeline log; otherwise the log section shows an empty state.

## Data-quality checks

The pipeline validates null values, duplicate keys, row counts, and foreign-key integrity. The dashboard runs and presents these checks against the current MySQL data.

## Notes on Git

- Keep `configs/db_config.json`, `.env`, and `.streamlit/secrets.toml` private.
- Commit shared configuration such as `configs/pipeline_config.yaml` and `.streamlit/config.toml`.
