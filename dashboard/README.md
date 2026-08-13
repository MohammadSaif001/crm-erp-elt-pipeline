# ELT Pipeline Analytics Dashboard

An enterprise-style BI dashboard built on top of the [`elt-data-engineering-pipeline`](https://github.com/rashid-dsai/elt-data-engineering-pipeline) — a production-style ELT pipeline (Python + MySQL) implementing a **Medallion Architecture** (Bronze → Silver → Gold) and a Kimball star schema.

This dashboard doesn't just report business KPIs — it exposes the engineering behind them: live row counts per layer, a re-executed data-quality suite, and a parsed pipeline execution log.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38-FF4B4B.svg)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## Features

**Business Analytics**
- Executive KPI cards: revenue, orders, customers, products, AOV
- Monthly/daily sales trends, revenue by country/category/product line
- Sales Analytics: top orders, top customers, top products, quantity analysis
- Customer Analytics: growth, gender/country/marital-status distribution, repeat vs new, CLV
- Product Analytics: active products, category treemap, top performers, full ranking

**Engineering / Data Quality**
- Live Bronze → Silver → Gold row-count flow
- Data Quality Score (gauge) — null checks, duplicate checks, FK integrity, row-count validation, re-executed live against MySQL (mirrors the pipeline's own `database_checks/` modules)
- Pipeline Monitoring: parsed `pipeline.log`, per-stage execution timing, log-level breakdown, filterable log viewer

**UI**
- Dark, enterprise-BI theme (Fabric / Snowflake / Databricks inspired)
- Global filter bar (date range, country, category, gender, marital status)
- Hover-animated KPI cards, status badges, progress bars, Plotly interactive charts
- Cached queries (`st.cache_data`) + cached engine (`st.cache_resource`) with a manual refresh control

---

## Architecture

```
dashboard/
├── app.py                     # Entry point, redirects to Home
├── config.py                  # DB settings + GOLD_SCHEMA column map (single source of truth)
├── requirements.txt
├── .env.example
├── assets/
│   ├── logo.png
│   └── styles.css
├── database/
│   ├── connection.py          # Cached SQLAlchemy engine, safe query runner
│   └── queries.py             # All SQL, one function per chart/table
├── components/
│   ├── sidebar.py              # Logo, DB health, refresh control
│   ├── navbar.py                # Page header + status badges
│   ├── metric_cards.py         # KPI card renderer
│   ├── charts.py                # Plotly chart builders (line, bar, donut, treemap, gauge, funnel, heatmap, scatter)
│   ├── filters.py               # Global filter bar
│   ├── pipeline_status.py       # Medallion flow + latest run summary
│   └── dq_score.py              # DQ gauge + full report
├── pages/
│   ├── 1_Home.py
│   ├── 2_Executive_Dashboard.py
│   ├── 3_Sales_Analytics.py
│   ├── 4_Customer_Analytics.py
│   ├── 5_Product_Analytics.py
│   ├── 6_Data_Quality.py
│   └── 7_Pipeline_Monitoring.py
└── utils/
    ├── helpers.py               # Formatting, log parsing
    └── cache.py                 # Cache-clear helpers
```

**Data flow:** `CSV (CRM+ERP) → Bronze (raw) → Silver (cleaned) → Gold (star schema views) → this dashboard`

---

## Schema Assumption Notice

The upstream pipeline repository documents the Gold layer's **column counts** (`dim_customers`: 10, `dim_products`: 11, `fact_sales`: 9) and several column names explicitly, but does not publish the literal `CREATE VIEW` SQL in its README. Every column name used by this dashboard lives in **one place** — `config.GOLD_SCHEMA` — with inline comments marking which names are documented verbatim vs. inferred from the pipeline's naming conventions (`cst_*`, `prd_*`, `sls_*` prefixes, and the FK-integrity rules listed in the README).

**If your actual view definitions differ, you only need to edit `config.py`** — no query in `database/queries.py` hardcodes a column name outside that map.

---

## How to Run

### 1. Install dependencies
```bash
cd dashboard
pip install -r requirements.txt
```

### 2. Configure the database connection
```bash
cp .env.example .env
# edit .env with your MySQL credentials
```
Or export the variables directly:
```bash
export DB_HOST=localhost
export DB_USER=your_user
export DB_PASSWORD=your_password
```

### 3. (Optional) Point at your pipeline log
```bash
export PIPELINE_LOG_PATH=/path/to/data_engineering_project/data/logs/pipeline.log
```
Without this, the Pipeline Monitoring page still works — it just shows a friendly empty state for the log viewer instead of crashing.

### 4. Run the dashboard
```bash
streamlit run app.py
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| App framework | Streamlit |
| Charts | Plotly |
| Database access | SQLAlchemy + PyMySQL |
| Data handling | Pandas |
| Source pipeline | Python + MySQL (Medallion Architecture) |

---

## Screenshots

> _Add screenshots here after your first run:_
> - `docs/screenshots/home.png`
> - `docs/screenshots/executive.png`
> - `docs/screenshots/data_quality.png`
> - `docs/screenshots/pipeline_monitoring.png`

---

## 🔭 Future Improvements

- Swap live `PIPELINE_LOG_PATH` file parsing for a structured log table / message queue
- Add authentication (Streamlit's `st.login` or an SSO proxy) for a shared deployment
- Materialize a `pipeline_runs` audit table in Gold so run history survives log rotation
- Docker Compose bundling the pipeline + MySQL + this dashboard for one-command demo
- CI check that validates `config.GOLD_SCHEMA` against the live `information_schema`

---

## Author

**Mohammad Saif**
Data Engineer | ELT Pipeline | Medallion Architecture | Dimensional Modeling
