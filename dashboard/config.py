"""
config.py
==============================================================================
Central configuration for the ELT Data Engineering Pipeline Dashboard.

Reads MySQL connection details from environment variables (falls back to the
same defaults used by the pipeline's `configs/db_config.json`) and exposes a
single `Settings` object used throughout the app.

SCHEMA ASSUMPTION NOTICE
--------------------------------------------------------------------------
The upstream pipeline repository (rashid-dsai/elt-data-engineering-pipeline)
documents the Gold layer as three views with a fixed column COUNT but does
not publish the literal `CREATE VIEW` SQL in its README. Column names below
are INFERRED from the repository's documented naming conventions (e.g.
`cst_id`, `prd_key`, `sls_*` prefixes, FK integrity rules) and are marked
with `# ASSUMED` wherever they are not verbatim from the README. If your
actual view definitions differ, update `GOLD_SCHEMA` below — every query in
`database/queries.py` is written against these names, in one place, so a
schema change only requires editing this file.
--------------------------------------------------------------------------
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path



@dataclass(frozen=True)
class DatabaseSettings:
    """MySQL connection settings for the Gold layer database."""

    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "3306"))
    user: str = os.getenv("DB_USER", "root")
    password: str = os.getenv("DB_PASSWORD", "841506")
    gold_db: str = os.getenv("GOLD_DB", "gold_db")
    silver_db: str = os.getenv("SILVER_DB", "silver_db")
    bronze_db: str = os.getenv("BRONZE_DB", "bronze_db")
    connect_timeout: int = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))
    pool_size: int = int(os.getenv("DB_POOL_SIZE", "5"))
    pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))

    def sqlalchemy_uri(self, database: str) -> str:
        """Build a PyMySQL SQLAlchemy URI for the given database name."""
        return (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{database}"
            f"?connect_timeout={self.connect_timeout}"
        )


# --------------------------------------------------------------------------
# GOLD LAYER SCHEMA MAP  (single source of truth for column names)
# --------------------------------------------------------------------------
# Columns confirmed directly by the README are marked "documented".
# Columns not explicitly spelled out are marked "# ASSUMED — verify against
# actual CREATE VIEW SQL" and follow the pipeline's own naming conventions.
GOLD_SCHEMA = {
    "dim_customers": {
        "table": "dim_customers",
        "columns": {
            "customer_key": "customer_key",        # ASSUMED surrogate key (ROW_NUMBER())
            "customer_id": "cst_id",                # documented (CRM source)
            "customer_number": "cst_key",           # documented (CRM source, join key)
            "first_name": "first_name",             # ASSUMED
            "last_name": "last_name",               # ASSUMED
            "marital_status": "marital_status",     # documented (standardized)
            "gender": "gender",                     # documented (CRM primary, ERP fallback)
            "birthdate": "birthdate",                # ASSUMED (from ERP CUST_AZ12.BDATE)
            "country": "country",                    # documented (from ERP LOC_A101)
            "create_date": "create_date",             # ASSUMED (CRM cst_create_date)
        },
    },
    "dim_products": {
        "table": "dim_products",
        "columns": {
            "product_key": "product_key",           # ASSUMED surrogate key (ROW_NUMBER())
            "product_id": "prd_id",                  # documented (CRM source)
            "product_number": "prd_key",              # documented (CRM source, join key)
            "product_name": "product_name",           # ASSUMED (from prd_nm)
            "category_id": "category_id",             # documented (extracted from prd_key)
            "category": "category",                   # documented (ERP CAT)
            "subcategory": "subcategory",             # documented (ERP SUBCAT)
            "maintenance": "maintenance",             # documented (ERP MAINTENANCE)
            "cost": "cost",                            # ASSUMED (from prd_cost)
            "product_line": "product_line",           # documented (Road/Mountain/Touring/Other)
            "start_date": "start_date",               # ASSUMED (from prd_start_dt)
        },
    },
    "fact_sales": {
        "table": "fact_sales",
        "columns": {
            "order_number": "order_number",           # documented
            "product_key": "product_key",             # documented (FK -> dim_products)
            "customer_key": "customer_key",           # documented (FK -> dim_customers)
            "order_date": "order_date",               # documented
            "shipping_date": "shipping_date",         # documented
            "due_date": "due_date",                   # documented
            "sales_amount": "sales_amount",           # documented
            "quantity": "quantity",                    # documented
            "price": "price",                          # documented
        },
    },
}


def _resolve_log_path() -> str:
    """Dynamically find pipeline.log regardless of current working directory."""
    env_path = os.getenv("PIPELINE_LOG_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    base_dir = Path(__file__).resolve().parent
    candidates = [
        base_dir.parent / "data" / "logs" / "pipeline.log",
        base_dir / "data" / "logs" / "pipeline.log",
        Path("data/logs/pipeline.log"),
        Path("../data/logs/pipeline.log"),
        Path("/home/mohammadsaif/Projects/data_engineering_project/data/logs/pipeline.log"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return str(base_dir.parent / "data" / "logs" / "pipeline.log")


# --------------------------------------------------------------------------
# APPLICATION SETTINGS
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class AppSettings:
    """Global UI / behavior settings for the Streamlit app."""

    app_title: str = "ELT Pipeline Health Report"
    app_icon: str = "📋"
    layout: str = "wide"
    theme: str = "light"
    cache_ttl_seconds: int = 300  # 5 minutes — balances freshness vs DB load
    logo_path: str = "assets/logo.png"
    styles_path: str = "assets/styles.css"
    log_file_path: str = field(default_factory=_resolve_log_path)
    max_log_lines: int = 800

    accent_color: str = "#000080"       # dark navy
    success_color: str = "#008000"      # green
    warning_color: str = "#B8860B"      # amber / goldenrod
    danger_color: str = "#CC0000"       # red
    bg_primary: str = "#FFFFFF"
    bg_secondary: str = "#F4F4F6"
    bg_card: str = "#FFFFFF"
    text_primary: str = "#000000"
    text_secondary: str = "#333333"
    border_color: str = "#000000"

    pipeline_layers: tuple = field(default_factory=lambda: ("Bronze", "Silver", "Gold"))


DB_SETTINGS = DatabaseSettings()
APP_SETTINGS = AppSettings()
