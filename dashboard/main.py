from __future__ import annotations

import logging
import sys
from html import escape
from pathlib import Path

# Ensure dashboard directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config import APP_SETTINGS, DB_SETTINGS, GOLD_SCHEMA
from database.connection import test_connection
from database.queries import (
    compute_dq_score,
    get_pipeline_lineage,
    get_row_counts,
)
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from utils.cache import bump_last_refresh, clear_all_caches, get_last_refresh_key
from utils.health import compute_overall_pipeline_status
from utils.helpers import (
    format_currency,
    format_duration,
    format_number,
    format_timestamp,
    get_latest_run_details,
    humanize_check_detail,
    humanize_check_name,
    parse_pipeline_log,
    summarize_log_levels,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("dashboard.fastapi")

app = FastAPI(
    title=APP_SETTINGS.app_title,
    description="Operations portal for ELT Pipeline Health and Analytics",
    version="1.0.0",
)

# Static files mounting
assets_dir = BASE_DIR / "assets"
templates_dir = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(assets_dir)), name="static")

# Templates setup
templates = Jinja2Templates(directory=str(templates_dir))


def status_badge(status: str) -> str:
    """Format status with accessible symbol and styling, matching the operations portal system."""
    normalized = str(status).upper()
    if normalized in {"HEALTHY", "PASS", "SUCCESS", "AVAILABLE", "TRUE"}:
        return '<span class="status status--pass">&#10003; PASS</span>'
    if normalized in {"WARNING", "WARN"}:
        return '<span class="status status--warning">! WARNING</span>'
    return '<span class="status status--fail">&#215; FAILED</span>'


# Register Jinja custom filters and globals
templates.env.filters["status_badge"] = status_badge
templates.env.filters["format_number"] = format_number
templates.env.filters["format_currency"] = format_currency
templates.env.filters["format_duration"] = format_duration
templates.env.filters["format_timestamp"] = format_timestamp
templates.env.filters["humanize_check_name"] = humanize_check_name
templates.env.globals["status_badge"] = status_badge


def get_common_context(request: Request, active_page: str) -> dict:
    """Provides common data required by base.html shell across all pages."""
    db_configs = [
        ("Bronze DB", DB_SETTINGS.bronze_db),
        ("Silver DB", DB_SETTINGS.silver_db),
        ("Gold DB", DB_SETTINGS.gold_db),
    ]
    db_statuses = []
    for label, db_name in db_configs:
        ok, msg = test_connection(db_name)
        db_statuses.append({"name": label, "ok": ok, "message": msg})

    return {
        "request": request,
        "active_page": active_page,
        "db_statuses": db_statuses,
        "last_refreshed": get_last_refresh_key(),
        "app_settings": APP_SETTINGS,
        "db_settings": DB_SETTINGS,
    }


def _retention(input_rows: int | None, output_rows: int | None) -> str:
    if input_rows is None or output_rows is None or input_rows <= 0:
        return "Not available"
    return f"{(output_rows / input_rows) * 100:.2f}%"


def _difference(input_rows: int | None, output_rows: int | None) -> str:
    if input_rows is None or output_rows is None:
        return "Not available"
    return format_number(input_rows - output_rows)


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def root():
    """Default landing route redirects to Home."""
    return RedirectResponse(url="/home")


@app.get("/home", response_class=HTMLResponse)
def home_page(request: Request):
    """Section 01 / Home Page."""
    context = get_common_context(request, active_page="home")
    health_info = compute_overall_pipeline_status()
    lineage = get_pipeline_lineage()

    source = lineage.get("source")
    bronze = lineage.get("bronze")
    silver = lineage.get("silver")
    gold = lineage.get("gold")

    lineage_data = {
        "source": source,
        "bronze": bronze,
        "silver": silver,
        "gold": gold,
        "diff_source_bronze": _difference(source, bronze),
        "retention_source_bronze": _retention(source, bronze),
        "diff_bronze_silver": _difference(bronze, silver),
        "retention_bronze_silver": _retention(bronze, silver),
    }

    # Data quality summary categories
    dq = health_info["dq_summary"]
    nulls = dq.get("null_checks")
    dupes = dq.get("duplicate_checks")
    fks = dq.get("fk_checks")
    counts = dq.get("row_count_checks")

    def category_status(frame, warning_on_failure: bool = False) -> str:
        if frame.empty or "passed" not in frame.columns:
            return "FAILED"
        if "status" in frame.columns and (frame["status"] == "FAILED").any():
            return "FAILED"
        if frame["passed"].all():
            return "PASS"
        return "WARNING" if warning_on_failure else "FAILED"

    null_status = category_status(nulls)
    duplicate_status = category_status(dupes, warning_on_failure=True)
    fk_status = category_status(fks)
    count_status = category_status(counts)

    duplicate_total = (
        int(dupes["duplicate_keys"].fillna(0).sum())
        if not dupes.empty and "duplicate_keys" in dupes
        else 0
    )
    duplicate_detail = (
        "Duplicate query failed; result is unverified."
        if duplicate_status == "FAILED"
        else humanize_check_detail(
            "duplicate", duplicate_status == "PASS", duplicate_total
        )
    )

    dq_categories = {
        "null_status": null_status,
        "null_detail": humanize_check_detail("null", null_status == "PASS"),
        "duplicate_status": duplicate_status,
        "duplicate_detail": duplicate_detail,
        "fk_status": fk_status,
        "fk_detail": humanize_check_detail("fk", fk_status == "PASS"),
        "count_status": count_status,
        "count_detail": humanize_check_detail("row_count", count_status == "PASS"),
    }

    # Database health rows
    db_health_rows = []
    for db_name, label in [
        (DB_SETTINGS.bronze_db, "Bronze DB"),
        (DB_SETTINGS.silver_db, "Silver DB"),
        (DB_SETTINGS.gold_db, "Gold DB"),
    ]:
        ok, msg = test_connection(db_name)
        db_health_rows.append(
            {
                "Database": label,
                "Status": "PASS" if ok else "FAILED",
                "Notes": "Connection successful (localhost:3306)"
                if ok
                else f"Connection error: {msg}",
            }
        )

    # Layer counts for narrative
    row_counts_df = get_row_counts()
    bronze_rows = 0
    silver_rows = 0
    gold_rows = 0
    if not row_counts_df.empty:
        bronze_rows = int(
            row_counts_df[row_counts_df["layer"] == "Bronze"]["row_count"].sum()
        )
        silver_rows = int(
            row_counts_df[row_counts_df["layer"] == "Silver"]["row_count"].sum()
        )
        gold_rows = int(
            row_counts_df[row_counts_df["layer"] == "Gold"]["row_count"].sum()
        )

    # Attention items
    attention_items = []
    if health_info["warnings_count"] > 0 or health_info["failed_checks"] > 0:
        duplicate_rows = dq.get("duplicate_checks")
        if not duplicate_rows.empty and "passed" in duplicate_rows.columns:
            for _, result in duplicate_rows[duplicate_rows["passed"] == False].iterrows():
                check = escape(str(result.get("check", "duplicate check")))
                if result.get("status") == "FAILED":
                    attention_items.append(f"{check}: query did not complete.")
                else:
                    attention_items.append(
                        f"{check}: {int(result.get('duplicate_keys', 0))} duplicate records found."
                    )
        if not attention_items:
            attention_items.append(
                f"{dq.get('failed_checks', 0)} runtime check(s) failed and {dq.get('warning_checks', 0)} warning(s) were recorded."
            )

    context.update(
        {
            "health_info": health_info,
            "lineage": lineage_data,
            "dq": dq,
            "dq_categories": dq_categories,
            "db_health_rows": db_health_rows,
            "latest_run": health_info["run_info"],
            "counts": {"bronze": bronze_rows, "silver": silver_rows, "gold": gold_rows},
            "attention_items": attention_items,
        }
    )
    return templates.TemplateResponse(request=request, name="home.html", context=context)


@app.get("/pipeline-run", response_class=HTMLResponse)
def pipeline_run_page(request: Request):
    """Section 02 / Pipeline Run Page."""
    context = get_common_context(request, active_page="pipeline_run")
    run_info = get_latest_run_details()
    timings = run_info.get("timings", [])
    raw_records = run_info.get("raw_records", [])

    log_text = ""
    if raw_records:
        log_text = "\n".join(
            f"{r.get('timestamp', '')} | {r.get('level', 'INFO'):<7} | {r.get('module', ''):<15} | {r.get('message', '')}"
            for r in raw_records
        )

    context.update(
        {
            "run_info": run_info,
            "timings": timings,
            "log_text": log_text,
            "log_file_path": APP_SETTINGS.log_file_path,
        }
    )
    return templates.TemplateResponse(
        request=request, name="pipeline_run.html", context=context
    )


@app.get("/data-quality", response_class=HTMLResponse)
def data_quality_page(request: Request):
    """Section 03 / Data Quality Page."""
    context = get_common_context(request, active_page="data_quality")
    dq = compute_dq_score()

    nulls = dq.get("null_checks")
    null_checks = []
    if not nulls.empty:
        for _, r in nulls.iterrows():
            passed = bool(r.get("passed", True))
            null_checks.append(
                {
                    "check_name": humanize_check_name(str(r.get("check", ""))),
                    "total_rows": r.get("total_rows", 0),
                    "failed_rows": r.get("failed_rows", 0),
                    "status": "PASS" if passed else "FAILED",
                }
            )

    dupes = dq.get("duplicate_checks")
    duplicate_checks = []
    if not dupes.empty:
        for _, r in dupes.iterrows():
            passed = bool(r.get("passed", True))
            status = str(r.get("status", "PASS" if passed else "WARNING"))
            duplicate_checks.append(
                {
                    "check_name": humanize_check_name(str(r.get("check", ""))),
                    "duplicate_keys": r.get("duplicate_keys", 0),
                    "status": status,
                }
            )

    fks = dq.get("fk_checks")
    fk_checks = []
    if not fks.empty:
        for _, r in fks.iterrows():
            passed = bool(r.get("passed", True))
            fk_checks.append(
                {
                    "check_name": humanize_check_name(str(r.get("check", ""))),
                    "orphaned_rows": r.get("orphaned_rows", 0),
                    "status": "PASS" if passed else "FAILED",
                }
            )

    counts = dq.get("row_count_checks")
    row_count_checks = []
    if not counts.empty:
        for _, r in counts.iterrows():
            passed = bool(r.get("passed", True))
            row_count_checks.append(
                {
                    "layer": r.get("layer", ""),
                    "table": r.get("table", ""),
                    "row_count": r.get("row_count", 0),
                    "status": "PASS" if passed else "FAILED",
                }
            )

    context.update(
        {
            "dq": dq,
            "null_checks": null_checks,
            "duplicate_checks": duplicate_checks,
            "fk_checks": fk_checks,
            "row_count_checks": row_count_checks,
        }
    )
    return templates.TemplateResponse(
        request=request, name="data_quality.html", context=context
    )


@app.get("/database-health", response_class=HTMLResponse)
def database_health_page(request: Request):
    """Section 04 / Database Health Page."""
    context = get_common_context(request, active_page="database_health")

    db_info = [
        ("Bronze Database", DB_SETTINGS.bronze_db, "Raw Ingestion Storage"),
        ("Silver Database", DB_SETTINGS.silver_db, "Cleaned & Normalized Storage"),
        ("Gold Database", DB_SETTINGS.gold_db, "Star-Schema Business Views"),
    ]

    connection_rows = []
    for label, db_name, desc in db_info:
        ok, msg = test_connection(db_name)
        connection_rows.append(
            {
                "database": db_name,
                "status": "PASS" if ok else "FAILED",
                "host": f"{DB_SETTINGS.host}:{DB_SETTINGS.port}",
                "notes": desc if ok else f"Connection error: {msg}",
            }
        )

    server_configs = [
        {"parameter": "Database host", "value": DB_SETTINGS.host},
        {"parameter": "Database port", "value": str(DB_SETTINGS.port)},
        {"parameter": "Database user", "value": DB_SETTINGS.user},
        {"parameter": "Driver / protocol", "value": "PyMySQL / mysql+pymysql"},
        {
            "parameter": "Cache TTL",
            "value": f"{APP_SETTINGS.cache_ttl_seconds} seconds",
        },
    ]

    row_counts_df = get_row_counts()
    inventory_rows = []
    if not row_counts_df.empty:
        for _, r in row_counts_df.iterrows():
            layer = r["layer"]
            table = r["table"]
            rows = int(r["row_count"])
            inventory_rows.append(
                {
                    "layer": layer,
                    "table": table,
                    "rows": rows,
                    "available": rows > 0,
                }
            )

    context.update(
        {
            "connection_rows": connection_rows,
            "server_configs": server_configs,
            "inventory_rows": inventory_rows,
        }
    )
    return templates.TemplateResponse(
        request=request, name="database_health.html", context=context
    )


@app.get("/technical-details", response_class=HTMLResponse)
def technical_details_page(request: Request, level: str | None = "ALL"):
    """Section 05 / Technical Details Page."""
    context = get_common_context(request, active_page="technical_details")

    records = parse_pipeline_log(max_lines=1000)
    level_counts = summarize_log_levels(records)

    selected_level = (level or "ALL").upper()
    filtered_records = records
    if selected_level != "ALL":
        filtered_records = [
            r for r in records if r.get("level", "").upper() == selected_level
        ]

    log_lines = []
    for r in filtered_records:
        ts = r.get("timestamp", "")
        lvl = r.get("level", "INFO")
        mod = r.get("module", "")
        msg = r.get("message", "")
        log_lines.append(f"{ts} | {lvl:<7} | {mod:<15} | {msg}")

    log_text = "\n".join(log_lines) if log_lines else "No matching log records found."

    context.update(
        {
            "level_counts": level_counts,
            "total_records": len(records),
            "filter_level": selected_level,
            "log_text": log_text,
            "gold_schema": GOLD_SCHEMA,
        }
    )
    return templates.TemplateResponse(
        request=request, name="technical_details.html", context=context
    )


@app.post("/refresh")
def refresh_report(redirect_to: str | None = "/home"):
    """Clear all caches, bump the timestamp, and redirect back to current page."""
    clear_all_caches()
    bump_last_refresh()
    safe_redirect = redirect_to if redirect_to and redirect_to.startswith("/") else "/home"
    return RedirectResponse(url=safe_redirect, status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
