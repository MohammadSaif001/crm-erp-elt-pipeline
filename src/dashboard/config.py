from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from src.core.paths import get_config_path, get_logs_path

ENV_FILE = get_config_path()

load_dotenv(ENV_FILE)



def _database_setting(environment_name: str, default: str | None = None) -> str:
    """Read a database setting from environment variables."""
    value = os.getenv(environment_name)
    if value is not None and value.strip():
        return value

    if default is not None:
        return default

    raise RuntimeError(f"Required environment variable {environment_name} is not set.")


@dataclass(frozen=True)
class DatabaseSettings:
    """MySQL connection settings for the Gold layer database."""

    host: str = _database_setting("DB_HOST", "localhost")
    port: int = int(_database_setting("DB_PORT", "3306"))
    user: str = _database_setting("DB_USER")
    password: str = _database_setting("DB_PASSWORD")

    gold_db: str = _database_setting("GOLD_DB", "gold_db")
    silver_db: str = _database_setting("SILVER_DB", "silver_db")
    bronze_db: str = _database_setting("BRONZE_DB", "bronze_db")

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


GOLD_SCHEMA = {
    "dim_customers": {
        "table": "dim_customers",
        "columns": {
            "customer_key": "customer_key",  # ASSUMED surrogate key (ROW_NUMBER())
            "customer_id": "customer_id",  # Gold view alias
            "customer_number": "customer_number",  # Gold view alias
            "first_name": "first_name",  # ASSUMED
            "last_name": "last_name",  # ASSUMED
            "marital_status": "marital_status",  # documented (standardized)
            "gender": "gender",  # documented (CRM primary, ERP fallback)
            "birthdate": "birthday",  # from ERP CUST_AZ12.BDATE
            "country": "country",  # documented (from ERP LOC_A101)
            "create_date": "create_date",  # ASSUMED (CRM cst_create_date)
        },
    },
    "dim_products": {
        "table": "dim_products",
        "columns": {
            "product_key": "product_key",  # ASSUMED surrogate key (ROW_NUMBER())
            "product_id": "product_id",  # Gold view alias
            "product_number": "product_number",  # Gold view alias
            "product_name": "product_name",  # ASSUMED (from prd_nm)
            "category_id": "category_id",  # documented (extracted from prd_key)
            "category": "category_name",  # from ERP CAT
            "subcategory": "subcategory_name",  # from ERP SUBCAT
            "maintenance": "maintenance",  # documented (ERP MAINTENANCE)
            "cost": "product_cost",  # from prd_cost
            "product_line": "product_line",  # documented (Road/Mountain/Touring/Other)
            "start_date": "product_start_date",  # from prd_start_dt
        },
    },
    "fact_sales": {
        "table": "fact_sales",
        "columns": {
            "order_number": "order_number",  # documented
            "product_key": "product_key",  # documented (FK -> dim_products)
            "customer_key": "customer_key",  # documented (FK -> dim_customers)
            "order_date": "order_date",  # documented
            "shipping_date": "shipping_date",  # documented
            "due_date": "due_date",  # documented
            "sales_amount": "sales_amount",  # documented
            "quantity": "quantity",  # documented
            "price": "price",  # documented
        },
    },
}


def _resolve_log_path() -> str:
    """Dynamically find pipeline.log regardless of current working directory."""
    env_path = os.getenv("PIPELINE_LOG_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    log_path = get_logs_path("pipeline.log")
    return str(log_path)


# ---------------------
# APPLICATION SETTINGS
# ---------------------
@dataclass(frozen=True)
class AppSettings:
    """Global UI / behavior settings for the Streamlit app."""

    app_title: str = "ELT Pipeline Health Report"
    app_icon: str = "📋"
    layout: str = "wide"
    theme: str = "light"
    cache_ttl_seconds: int = 300
    logo_path: str = str(Path(__file__).resolve().parent / "assets" / "logo.png")
    styles_path: str = str(Path(__file__).resolve().parent / "assets" / "styles.css")
    log_file_path: str = field(default_factory=_resolve_log_path)
    max_log_lines: int = 800

    accent_color: str = "#000080"  # dark navy
    success_color: str = "#008000"  # green
    warning_color: str = "#B8860B"  # amber / goldenrod
    danger_color: str = "#CC0000"  # red
    bg_primary: str = "#FFFFFF"
    bg_secondary: str = "#F4F4F6"
    bg_card: str = "#FFFFFF"
    text_primary: str = "#000000"
    text_secondary: str = "#333333"
    text_disabled: str = "#999999"
    border_color: str = "#000000"

    pipeline_layers: tuple = field(default_factory=lambda: ("Bronze", "Silver", "Gold"))


DB_SETTINGS = DatabaseSettings()
APP_SETTINGS = AppSettings()
