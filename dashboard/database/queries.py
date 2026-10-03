"""
database/queries.py
==============================================================================
All SQL queries used by the dashboard, centralized in one module so that:
  1. Column-name assumptions (see config.GOLD_SCHEMA) only need to be
     corrected in one place.
  2. Every page function is a thin wrapper: build filters -> run_query ->
     cached DataFrame.

Query functions use a process-local TTL cache keyed by their arguments, so
identical requests reuse results instead of re-hitting MySQL.
"""

from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path

import pandas as pd
from config import APP_SETTINGS, DB_SETTINGS, GOLD_SCHEMA
from utils.cache import ttl_cache

from database.connection import run_query, test_connection

TTL = APP_SETTINGS.cache_ttl_seconds

_C = GOLD_SCHEMA["dim_customers"]["columns"]
_P = GOLD_SCHEMA["dim_products"]["columns"]
_F = GOLD_SCHEMA["fact_sales"]["columns"]


def _filter_clause(
    country: list[str] | None,
    category: list[str] | None,
    gender: list[str] | None,
    marital_status: list[str] | None,
    date_range: tuple[dt.date, dt.date] | None,
) -> tuple[str, dict]:
    """Build a shared WHERE clause + params dict from global filter selections."""
    clauses: list[str] = []
    params: dict = {}

    if country:
        clauses.append(f"c.{_C['country']} IN :country")
        params["country"] = tuple(country)
    if category:
        clauses.append(f"p.{_P['category']} IN :category")
        params["category"] = tuple(category)
    if gender:
        clauses.append(f"c.{_C['gender']} IN :gender")
        params["gender"] = tuple(gender)
    if marital_status:
        clauses.append(f"c.{_C['marital_status']} IN :marital_status")
        params["marital_status"] = tuple(marital_status)
    if date_range:
        clauses.append(f"f.{_F['order_date']} BETWEEN :start_date AND :end_date")
        params["start_date"], params["end_date"] = date_range

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where_sql, params


def _base_from() -> str:
    """Shared FROM/JOIN backbone: fact_sales joined to both dimensions."""
    return (
        f"FROM {GOLD_SCHEMA['fact_sales']['table']} f "
        f"JOIN {GOLD_SCHEMA['dim_customers']['table']} c "
        f"  ON f.{_F['customer_key']} = c.{_C['customer_key']} "
        f"JOIN {GOLD_SCHEMA['dim_products']['table']} p "
        f"  ON f.{_F['product_key']} = p.{_P['product_key']}"
    )


@ttl_cache(ttl_seconds=TTL)
def get_filter_options() -> dict[str, list]:
    """Fetch distinct values for every global filter dropdown."""
    countries = run_query(
        f"SELECT DISTINCT {_C['country']} AS v FROM {GOLD_SCHEMA['dim_customers']['table']} WHERE {_C['country']} IS NOT NULL ORDER BY 1"
    )
    categories = run_query(
        f"SELECT DISTINCT {_P['category']} AS v FROM {GOLD_SCHEMA['dim_products']['table']} WHERE {_P['category']} IS NOT NULL ORDER BY 1"
    )
    genders = run_query(
        f"SELECT DISTINCT {_C['gender']} AS v FROM {GOLD_SCHEMA['dim_customers']['table']} WHERE {_C['gender']} IS NOT NULL ORDER BY 1"
    )
    marital = run_query(
        f"SELECT DISTINCT {_C['marital_status']} AS v FROM {GOLD_SCHEMA['dim_customers']['table']} WHERE {_C['marital_status']} IS NOT NULL ORDER BY 1"
    )
    products = run_query(
        f"SELECT DISTINCT {_P['product_name']} AS v FROM {GOLD_SCHEMA['dim_products']['table']} WHERE {_P['product_name']} IS NOT NULL ORDER BY 1"
    )
    date_bounds = run_query(
        f"SELECT MIN({_F['order_date']}) AS min_d, MAX({_F['order_date']}) AS max_d FROM {GOLD_SCHEMA['fact_sales']['table']}"
    )

    return {
        "countries": countries["v"].dropna().tolist() if not countries.empty else [],
        "categories": categories["v"].dropna().tolist() if not categories.empty else [],
        "genders": genders["v"].dropna().tolist() if not genders.empty else [],
        "marital_statuses": marital["v"].dropna().tolist() if not marital.empty else [],
        "products": products["v"].dropna().tolist() if not products.empty else [],
        "min_date": date_bounds["min_d"].iloc[0] if not date_bounds.empty else None,
        "max_date": date_bounds["max_d"].iloc[0] if not date_bounds.empty else None,
    }


@ttl_cache(ttl_seconds=TTL)
def get_executive_kpis(
    country=None, category=None, gender=None, marital_status=None, date_range=None
) -> dict:
    """Total revenue, orders, customers, products, AOV for the KPI row."""
    where_sql, params = _filter_clause(
        country, category, gender, marital_status, date_range
    )
    sql = f"""
        SELECT
            COALESCE(SUM(f.{_F["sales_amount"]}), 0) AS total_revenue,
            COUNT(DISTINCT f.{_F["order_number"]}) AS total_orders,
            COUNT(DISTINCT c.{_C["customer_key"]}) AS total_customers,
            COUNT(DISTINCT p.{_P["product_key"]}) AS total_products,
            COALESCE(SUM(f.{_F["quantity"]}), 0) AS total_quantity
        {_base_from()}
        {where_sql}
    """
    df = run_query(sql, params=params)
    if df.empty:
        return {
            "total_revenue": 0,
            "total_orders": 0,
            "total_customers": 0,
            "total_products": 0,
            "avg_order_value": 0,
        }
    row = df.iloc[0]
    aov = (
        float(row["total_revenue"]) / row["total_orders"] if row["total_orders"] else 0
    )
    return {
        "total_revenue": float(row["total_revenue"]),
        "total_orders": int(row["total_orders"]),
        "total_customers": int(row["total_customers"]),
        "total_products": int(row["total_products"]),
        "total_quantity": int(row["total_quantity"]),
        "avg_order_value": aov,
    }


@ttl_cache(ttl_seconds=TTL)
def get_monthly_sales_trend(
    country=None, category=None, gender=None, marital_status=None, date_range=None
) -> pd.DataFrame:
    """Monthly revenue + order count trend."""
    where_sql, params = _filter_clause(
        country, category, gender, marital_status, date_range
    )
    sql = f"""
        SELECT
            DATE_FORMAT(f.{_F["order_date"]}, '%Y-%m') AS month,
            SUM(f.{_F["sales_amount"]}) AS revenue,
            COUNT(DISTINCT f.{_F["order_number"]}) AS orders
        {_base_from()}
        {where_sql}
        GROUP BY month
        ORDER BY month
    """
    return run_query(sql, params=params)


@ttl_cache(ttl_seconds=TTL)
def get_daily_sales(
    country=None, category=None, gender=None, marital_status=None, date_range=None
) -> pd.DataFrame:
    """Daily revenue trend."""
    where_sql, params = _filter_clause(
        country, category, gender, marital_status, date_range
    )
    sql = f"""
        SELECT
            DATE(f.{_F["order_date"]}) AS day,
            SUM(f.{_F["sales_amount"]}) AS revenue,
            COUNT(DISTINCT f.{_F["order_number"]}) AS orders
        {_base_from()}
        {where_sql}
        GROUP BY day
        ORDER BY day
    """
    return run_query(sql, params=params)


@ttl_cache(ttl_seconds=TTL)
def get_revenue_by_country(
    country=None, category=None, gender=None, marital_status=None, date_range=None
) -> pd.DataFrame:
    where_sql, params = _filter_clause(
        country, category, gender, marital_status, date_range
    )
    sql = f"""
        SELECT c.{_C["country"]} AS country, SUM(f.{_F["sales_amount"]}) AS revenue,
               COUNT(DISTINCT f.{_F["order_number"]}) AS orders
        {_base_from()}
        {where_sql}
        GROUP BY c.{_C["country"]}
        ORDER BY revenue DESC
    """
    return run_query(sql, params=params)


@ttl_cache(ttl_seconds=TTL)
def get_revenue_by_category(
    country=None, category=None, gender=None, marital_status=None, date_range=None
) -> pd.DataFrame:
    where_sql, params = _filter_clause(
        country, category, gender, marital_status, date_range
    )
    sql = f"""
        SELECT p.{_P["category"]} AS category, SUM(f.{_F["sales_amount"]}) AS revenue,
               SUM(f.{_F["quantity"]}) AS quantity
        {_base_from()}
        {where_sql}
        GROUP BY p.{_P["category"]}
        ORDER BY revenue DESC
    """
    return run_query(sql, params=params)


@ttl_cache(ttl_seconds=TTL)
def get_revenue_by_product_line(
    country=None, category=None, gender=None, marital_status=None, date_range=None
) -> pd.DataFrame:
    where_sql, params = _filter_clause(
        country, category, gender, marital_status, date_range
    )
    sql = f"""
        SELECT p.{_P["product_line"]} AS product_line, SUM(f.{_F["sales_amount"]}) AS revenue
        {_base_from()}
        {where_sql}
        GROUP BY p.{_P["product_line"]}
        ORDER BY revenue DESC
    """
    return run_query(sql, params=params)


@ttl_cache(ttl_seconds=TTL)
def get_top_customers(
    limit: int = 10,
    country=None,
    category=None,
    gender=None,
    marital_status=None,
    date_range=None,
) -> pd.DataFrame:
    where_sql, params = _filter_clause(
        country, category, gender, marital_status, date_range
    )
    params["limit"] = limit
    sql = f"""
        SELECT
            CONCAT(c.{_C["first_name"]}, ' ', c.{_C["last_name"]}) AS customer_name,
            c.{_C["country"]} AS country,
            SUM(f.{_F["sales_amount"]}) AS revenue,
            COUNT(DISTINCT f.{_F["order_number"]}) AS orders
        {_base_from()}
        {where_sql}
        GROUP BY customer_name, country
        ORDER BY revenue DESC
        LIMIT :limit
    """
    return run_query(sql, params=params)


@ttl_cache(ttl_seconds=TTL)
def get_top_products(
    limit: int = 10,
    country=None,
    category=None,
    gender=None,
    marital_status=None,
    date_range=None,
) -> pd.DataFrame:
    where_sql, params = _filter_clause(
        country, category, gender, marital_status, date_range
    )
    params["limit"] = limit
    sql = f"""
        SELECT
            p.{_P["product_name"]} AS product_name,
            p.{_P["category"]} AS category,
            SUM(f.{_F["sales_amount"]}) AS revenue,
            SUM(f.{_F["quantity"]}) AS quantity_sold
        {_base_from()}
        {where_sql}
        GROUP BY product_name, category
        ORDER BY revenue DESC
        LIMIT :limit
    """
    return run_query(sql, params=params)


@ttl_cache(ttl_seconds=TTL)
def get_top_orders(
    limit: int = 10,
    country=None,
    category=None,
    gender=None,
    marital_status=None,
    date_range=None,
) -> pd.DataFrame:
    where_sql, params = _filter_clause(
        country, category, gender, marital_status, date_range
    )
    params["limit"] = limit
    sql = f"""
        SELECT
            f.{_F["order_number"]} AS order_number,
            CONCAT(c.{_C["first_name"]}, ' ', c.{_C["last_name"]}) AS customer_name,
            p.{_P["product_name"]} AS product_name,
            f.{_F["order_date"]} AS order_date,
            f.{_F["sales_amount"]} AS sales_amount
        {_base_from()}
        {where_sql}
        ORDER BY f.{_F["sales_amount"]} DESC
        LIMIT :limit
    """
    return run_query(sql, params=params)


@ttl_cache(ttl_seconds=TTL)
def get_customer_growth(
    country=None, category=None, gender=None, marital_status=None, date_range=None
) -> pd.DataFrame:
    """New customers acquired per month, based on first order date."""
    where_sql, params = _filter_clause(
        country, category, gender, marital_status, date_range
    )
    sql = f"""
        SELECT DATE_FORMAT(first_order.month, '%Y-%m') AS month, COUNT(*) AS new_customers
        FROM (
            SELECT c.{_C["customer_key"]} AS customer_key, MIN(f.{_F["order_date"]}) AS month
            {_base_from()}
            {where_sql}
            GROUP BY c.{_C["customer_key"]}
        ) AS first_order
        GROUP BY month
        ORDER BY month
    """
    return run_query(sql, params=params)


@ttl_cache(ttl_seconds=TTL)
def get_customer_distribution() -> dict[str, pd.DataFrame]:
    """Gender and country distribution across the full customer base."""
    gender_df = run_query(
        f"SELECT {_C['gender']} AS gender, COUNT(*) AS customers "
        f"FROM {GOLD_SCHEMA['dim_customers']['table']} GROUP BY {_C['gender']}"
    )
    country_df = run_query(
        f"SELECT {_C['country']} AS country, COUNT(*) AS customers "
        f"FROM {GOLD_SCHEMA['dim_customers']['table']} GROUP BY {_C['country']} ORDER BY customers DESC"
    )
    marital_df = run_query(
        f"SELECT {_C['marital_status']} AS marital_status, COUNT(*) AS customers "
        f"FROM {GOLD_SCHEMA['dim_customers']['table']} GROUP BY {_C['marital_status']}"
    )
    return {"gender": gender_df, "country": country_df, "marital_status": marital_df}


@ttl_cache(ttl_seconds=TTL)
def get_repeat_vs_new_customers(date_range=None) -> pd.DataFrame:
    """Classify customers as repeat (2+ orders) vs one-time buyers."""
    where_sql, params = _filter_clause(None, None, None, None, date_range)
    sql = f"""
        SELECT
            CASE WHEN order_count > 1 THEN 'Repeat' ELSE 'One-Time' END AS customer_type,
            COUNT(*) AS customers
        FROM (
            SELECT c.{_C["customer_key"]} AS customer_key, COUNT(DISTINCT f.{_F["order_number"]}) AS order_count
            {_base_from()}
            {where_sql}
            GROUP BY c.{_C["customer_key"]}
        ) AS order_counts
        GROUP BY customer_type
    """
    return run_query(sql, params=params)


@ttl_cache(ttl_seconds=TTL)
def get_customer_lifetime_value(limit: int = 15) -> pd.DataFrame:
    """Total revenue generated per customer (CLV proxy) — top N."""
    sql = f"""
        SELECT
            CONCAT(c.{_C["first_name"]}, ' ', c.{_C["last_name"]}) AS customer_name,
            SUM(f.{_F["sales_amount"]}) AS lifetime_value,
            COUNT(DISTINCT f.{_F["order_number"]}) AS total_orders,
            MIN(f.{_F["order_date"]}) AS first_order,
            MAX(f.{_F["order_date"]}) AS last_order
        {_base_from()}
        GROUP BY customer_name
        ORDER BY lifetime_value DESC
        LIMIT :limit
    """
    return run_query(sql, params={"limit": limit})


@ttl_cache(ttl_seconds=TTL)
def get_product_analytics() -> pd.DataFrame:
    """Per-product revenue, quantity, and active status."""
    sql = f"""
        SELECT
            p.{_P["product_name"]} AS product_name,
            p.{_P["category"]} AS category,
            p.{_P["subcategory"]} AS subcategory,
            p.{_P["product_line"]} AS product_line,
            COALESCE(SUM(f.{_F["sales_amount"]}), 0) AS revenue,
            COALESCE(SUM(f.{_F["quantity"]}), 0) AS quantity_sold
        FROM {GOLD_SCHEMA["dim_products"]["table"]} p
        LEFT JOIN {GOLD_SCHEMA["fact_sales"]["table"]} f
            ON p.{_P["product_key"]} = f.{_F["product_key"]}
        GROUP BY product_name, category, subcategory, product_line
        ORDER BY revenue DESC
    """
    return run_query(sql)


@ttl_cache(ttl_seconds=TTL)
def get_active_product_count() -> int:
    """Gold dim_products is already filtered to active products only (prd_end_dt IS NULL)."""
    df = run_query(f"SELECT COUNT(*) AS n FROM {GOLD_SCHEMA['dim_products']['table']}")
    return int(df["n"].iloc[0]) if not df.empty else 0


@ttl_cache(ttl_seconds=TTL)
def get_row_counts() -> pd.DataFrame:
    """Row counts across bronze / silver / gold for the pipeline-monitoring & DQ pages."""
    layer_tables = {
        DB_SETTINGS.bronze_db: [
            "crm_customers_info",
            "crm_prd_info",
            "crm_sales_details",
            "erp_cust_az12",
            "erp_location_a101",
            "erp_px_cat_g1v2",
        ],
        DB_SETTINGS.silver_db: [
            "crm_customers_info",
            "crm_prd_info",
            "crm_sales_details",
            "erp_cust_az12",
            "erp_location_a101",
            "erp_px_cat_g1v2",
        ],
        DB_SETTINGS.gold_db: ["dim_customers", "dim_products", "fact_sales"],
    }
    rows = []
    for db, tables in layer_tables.items():
        layer_name = {
            DB_SETTINGS.bronze_db: "Bronze",
            DB_SETTINGS.silver_db: "Silver",
            DB_SETTINGS.gold_db: "Gold",
        }[db]
        for table in tables:
            df = run_query(f"SELECT COUNT(*) AS n FROM {table}", database=db)
            count = int(df["n"].iloc[0]) if not df.empty else 0
            rows.append({"layer": layer_name, "table": table, "row_count": count})
    return pd.DataFrame(rows)


_NULL_CHECK_TARGETS = [
    # Same rules as src.database_checks.check_nulls.NOT_NULL_RULES["silver"].
    (DB_SETTINGS.silver_db, "crm_customers_info", "cst_id"),
    (DB_SETTINGS.silver_db, "crm_customers_info", "cst_key"),
    (DB_SETTINGS.silver_db, "crm_customers_info", "cst_firstname"),
    (DB_SETTINGS.silver_db, "crm_customers_info", "cst_lastname"),
    (DB_SETTINGS.silver_db, "crm_prd_info", "prd_id"),
    (DB_SETTINGS.silver_db, "crm_prd_info", "prd_key"),
    (DB_SETTINGS.silver_db, "crm_prd_info", "prd_name"),
    (DB_SETTINGS.silver_db, "crm_sales_details", "sales_ord_num"),
    (DB_SETTINGS.silver_db, "crm_sales_details", "sales_prd_key"),
    (DB_SETTINGS.silver_db, "crm_sales_details", "sales_cust_id"),
    (DB_SETTINGS.silver_db, "erp_cust_az12", "cid"),
    (DB_SETTINGS.silver_db, "erp_location_a101", "cid"),
    (DB_SETTINGS.silver_db, "erp_location_a101", "country_name"),
    (DB_SETTINGS.silver_db, "erp_px_cat_g1v2", "id"),
    (DB_SETTINGS.silver_db, "erp_px_cat_g1v2", "cat"),
    (DB_SETTINGS.silver_db, "erp_px_cat_g1v2", "subcat"),
]

_DUPLICATE_CHECK_TARGETS = [
    # (database, table, primary_key_column)
    (DB_SETTINGS.silver_db, "crm_customers_info", "cst_id"),
    (DB_SETTINGS.silver_db, "crm_prd_info", "prd_id"),
    (DB_SETTINGS.silver_db, "crm_sales_details", "sales_ord_num, sales_prd_key"),
    (DB_SETTINGS.silver_db, "erp_cust_az12", "cid"),
    (DB_SETTINGS.silver_db, "erp_location_a101", "cid"),
    (DB_SETTINGS.silver_db, "erp_px_cat_g1v2", "id"),
]

_FK_CHECK_TARGETS = [
    # Same rules and exception as src.database_checks.check_fk_integrity.
    (
        "sales.sales_cust_id -> customers.cst_id",
        DB_SETTINGS.silver_db,
        "crm_sales_details",
        "sales_cust_id",
        DB_SETTINGS.silver_db,
        "crm_customers_info",
        "cst_id",
    ),
    (
        "sales.sales_prd_key -> products.prd_key",
        DB_SETTINGS.silver_db,
        "crm_sales_details",
        "sales_prd_key",
        DB_SETTINGS.silver_db,
        "crm_prd_info",
        "prd_key",
    ),
    (
        "erp_cust.cid -> customers.cst_key",
        DB_SETTINGS.silver_db,
        "erp_cust_az12",
        "cid",
        DB_SETTINGS.silver_db,
        "crm_customers_info",
        "cst_key",
    ),
    (
        "erp_location.cid -> customers.cst_key",
        DB_SETTINGS.silver_db,
        "erp_location_a101",
        "cid",
        DB_SETTINGS.silver_db,
        "crm_customers_info",
        "cst_key",
    ),
    (
        "erp_category.id -> products.cat_id",
        DB_SETTINGS.silver_db,
        "erp_px_cat_g1v2",
        "id",
        DB_SETTINGS.silver_db,
        "crm_prd_info",
        "cat_id",
    ),
]

_FK_EXCEPTIONS = {"erp_category.id -> products.cat_id": ("CO_PD",)}


@ttl_cache(ttl_seconds=TTL)
def get_null_check_results() -> pd.DataFrame:
    """Null-count per critical column across silver tables."""
    rows = []
    for db, table, col in _NULL_CHECK_TARGETS:
        connected, _ = test_connection(db)
        if not connected:
            rows.append(
                {
                    "check": f"{table}.{col} NOT NULL",
                    "total_rows": None,
                    "failed_rows": None,
                    "passed": False,
                    "status": "FAILED",
                }
            )
            continue
        df = run_query(
            f"SELECT COUNT(*) AS total, SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS nulls FROM {table}",
            database=db,
        )
        if df.empty or not {"total", "nulls"}.issubset(df.columns):
            rows.append(
                {
                    "check": f"{table}.{col} NOT NULL",
                    "total_rows": None,
                    "failed_rows": None,
                    "passed": False,
                    "status": "FAILED",
                }
            )
            continue
        total, nulls = int(df["total"].iloc[0]), int(df["nulls"].iloc[0] or 0)
        rows.append(
            {
                "check": f"{table}.{col} NOT NULL",
                "total_rows": total,
                "failed_rows": nulls,
                "passed": nulls == 0,
                "status": "PASS" if nulls == 0 else "FAILED",
            }
        )
    return pd.DataFrame(rows)


@ttl_cache(ttl_seconds=TTL)
def get_duplicate_check_results() -> pd.DataFrame:
    """Primary-key uniqueness per table, mirroring ``check_duplicates.py``.

    A failed SQL query is a FAILED check, never a zero-duplicate PASS.  The
    count is duplicate *rows* (the same metric used by the pipeline check),
    rather than the number of duplicate key groups.
    """
    rows = []
    for db, table, pk in _DUPLICATE_CHECK_TARGETS:
        connected, connection_message = test_connection(db)
        if not connected:
            rows.append(
                {
                    "check": f"{table}.{pk} UNIQUE",
                    "duplicate_keys": None,
                    "passed": False,
                    "status": "FAILED",
                    "error": connection_message,
                }
            )
            continue
        df = run_query(
            f"SELECT COALESCE(SUM(cnt), 0) AS n FROM (SELECT COUNT(*) AS cnt FROM {table} GROUP BY {pk} HAVING COUNT(*) > 1) AS dupes",
            database=db,
        )
        if df.empty or "n" not in df.columns:
            rows.append(
                {
                    "check": f"{table}.{pk} UNIQUE",
                    "duplicate_keys": None,
                    "passed": False,
                    "status": "FAILED",
                    "error": "Duplicate query did not return a result.",
                }
            )
            continue
        dupes = int(df["n"].iloc[0] or 0)
        rows.append(
            {
                "check": f"{table}.{pk} UNIQUE",
                "duplicate_keys": dupes,
                "passed": dupes == 0,
                "status": "PASS" if dupes == 0 else "WARNING",
            }
        )
    return pd.DataFrame(rows)


@ttl_cache(ttl_seconds=TTL)
def get_pipeline_lineage() -> dict[str, int | None]:
    """Return source and layer row totals used by the pipeline-flow report.

    Source totals are counted from the six CSV files used by this project;
    layer totals are live database table totals. Gold is intentionally not
    treated as a row-retention stage because it contains dimensional models.
    """
    raw_dir = Path(__file__).resolve().parents[2] / "data" / "raw"
    source_rows = 0
    source_files = list(raw_dir.glob("source_*/*.csv"))
    for csv_path in source_files:
        try:
            with csv_path.open(
                "r", encoding="utf-8", errors="replace", newline=""
            ) as handle:
                source_rows += max(sum(1 for _ in csv.reader(handle)) - 1, 0)
        except OSError:
            return {"source": None, "bronze": None, "silver": None, "gold": None}

    counts = get_row_counts()
    if counts.empty:
        return {"source": source_rows, "bronze": None, "silver": None, "gold": None}
    totals = counts.groupby("layer")["row_count"].sum().to_dict()
    return {
        "source": source_rows,
        "bronze": int(totals.get("Bronze", 0)),
        "silver": int(totals.get("Silver", 0)),
        "gold": int(totals.get("Gold", 0)),
    }


@ttl_cache(ttl_seconds=TTL)
def get_fk_integrity_results() -> pd.DataFrame:
    """Orphaned foreign-key rows per documented FK rule."""
    rows = []
    for label, cdb, ctable, ccol, pdb, ptable, pcol in _FK_CHECK_TARGETS:
        if cdb != pdb:
            # Cross-database FK check would need federated query support;
            # skip with a clear note rather than producing a wrong result.
            rows.append({"check": label, "orphaned_rows": None, "passed": None})
            continue
        excluded = _FK_EXCEPTIONS.get(label, ())
        exclusion_sql = ""
        if excluded:
            values = ", ".join(f"'{value}'" for value in excluded)
            exclusion_sql = f" AND c.{ccol} NOT IN ({values})"
        sql = f"""
            SELECT COUNT(*) AS n
            FROM {ctable} c
            LEFT JOIN {ptable} p ON c.{ccol} = p.{pcol}
            WHERE p.{pcol} IS NULL AND c.{ccol} IS NOT NULL {exclusion_sql}
        """
        df = run_query(sql, database=cdb)
        if df.empty or "n" not in df.columns:
            rows.append(
                {
                    "check": label,
                    "orphaned_rows": None,
                    "passed": False,
                    "status": "FAILED",
                }
            )
            continue
        orphaned = int(df["n"].iloc[0] or 0)
        rows.append(
            {
                "check": label,
                "orphaned_rows": orphaned,
                "passed": orphaned == 0,
                "status": "PASS" if orphaned == 0 else "FAILED",
            }
        )
    return pd.DataFrame(rows)


@ttl_cache(ttl_seconds=TTL)
def get_row_count_check_results() -> pd.DataFrame:
    """Mirror the DQ tests: non-empty Bronze/Silver tables and Silver <= Bronze."""
    df = get_row_counts()
    if df.empty:
        return df
    rows = []
    bronze = df[df["layer"] == "Bronze"].set_index("table")["row_count"].to_dict()
    silver = df[df["layer"] == "Silver"].set_index("table")["row_count"].to_dict()
    for layer_name, layer_counts in (("Bronze", bronze), ("Silver", silver)):
        for table, count in layer_counts.items():
            rows.append(
                {
                    "layer": layer_name,
                    "table": table,
                    "row_count": count,
                    "check": f"{layer_name}.{table} is not empty",
                    "passed": count > 0,
                    "status": "PASS" if count > 0 else "FAILED",
                }
            )
    for table in sorted(set(bronze) & set(silver)):
        passed = silver[table] <= bronze[table]
        rows.append(
            {
                "layer": "Bronze → Silver",
                "table": table,
                "row_count": silver[table],
                "check": f"{table}: Silver row count <= Bronze",
                "passed": passed,
                "status": "PASS" if passed else "FAILED",
            }
        )
    return pd.DataFrame(rows)


def compute_dq_score() -> dict:
    """
    Aggregate all DQ checks into a single 0-100 score plus per-category
    pass/fail counts, used by components/dq_score.py.
    """
    nulls = get_null_check_results()
    dupes = get_duplicate_check_results()
    fks = get_fk_integrity_results()
    counts = get_row_count_check_results()

    total_checks = 0
    passed_checks = 0
    warning_checks = 0
    failed_checks = 0
    for df in (nulls, dupes, fks, counts):
        if df.empty or "passed" not in df.columns:
            continue
        valid = df["passed"].dropna()
        total_checks += len(valid)
        if "status" in df.columns:
            statuses = df.loc[valid.index, "status"].fillna("FAILED")
            passed_checks += int((statuses == "PASS").sum())
            warning_checks += int((statuses == "WARNING").sum())
            failed_checks += int((statuses == "FAILED").sum())
        else:
            passed_checks += int(valid.sum())
            failed_checks += int((~valid).sum())

    score = round((passed_checks / total_checks) * 100, 1) if total_checks else 0.0
    return {
        "score": score,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "warning_checks": warning_checks,
        "failed_checks": failed_checks,
        "null_checks": nulls,
        "duplicate_checks": dupes,
        "fk_checks": fks,
        "row_count_checks": counts,
    }
