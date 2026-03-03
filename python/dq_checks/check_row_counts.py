import logging
import pandas as pd
from sqlalchemy import text

import sys, os
current_dir = os.path.dirname(os.path.abspath(__file__))
python_folder = os.path.dirname(current_dir)
if python_folder not in sys.path:
    sys.path.append(python_folder)

from utils.db_connection import get_engine
from utils.logger import setup_logger

logger = setup_logger("dq_check_row_counts")

# Tables that should exist in each layer
LAYER_TABLES = {
    "bronze": [
        "crm_customers_info", "crm_prd_info", "crm_sales_details",
        "erp_cust_az12", "erp_location_a101", "erp_px_cat_g1v2",
    ],
    "silver": [
        "crm_customers_info", "crm_prd_info", "crm_sales_details",
        "erp_cust_az12", "erp_location_a101", "erp_px_cat_g1v2",
    ],
    "gold": ["dim_customers", "dim_products", "fact_sales"],
}

"""
DQ Check: Row Count Validation

Ensures tables are non-empty and compares row counts between layers
(e.g. bronze vs silver) to detect unexpected data loss.
"""
def get_row_counts(layer: str) -> dict:
    """Return { table_name: row_count } for all tables in a layer."""
    tables = LAYER_TABLES.get(layer, [])
    engine = get_engine(layer)
    counts = {}

    for table in tables:
        try:
            with engine.connect() as conn:
                query = text(f"SELECT COUNT(*) AS cnt FROM {table}")
                result = pd.read_sql(query, conn)
                counts[table] = int(result["cnt"].iloc[0])
        except Exception as e:
            logging.error(f"[ROW_COUNT] Error reading {layer}.{table}: {e}")
            counts[table] = -1  # signals error

    return counts


def check_row_counts() -> dict:
    """
    Get row counts for all layers and flag empty tables.

    Returns:
        dict with layer -> { table: { 'count': int, 'status': str } }
    """
    report = {}
    for layer in ["bronze", "silver", "gold"]:
        counts = get_row_counts(layer)
        layer_report = {}
        for table, count in counts.items():
            if count < 0:
                status = "ERROR"
            elif count == 0:
                status = "WARN"
                logging.warning(f"[ROW_COUNT] {layer}.{table} is empty!")
            else:
                status = "OK"
            layer_report[table] = {"count": count, "status": status}
        report[layer] = layer_report
    return report


def compare_layers(source_layer: str = "bronze", target_layer: str = "silver") -> dict:
    """
    Compare row counts between two layers for shared tables.
    Silver should have <= bronze rows (after dedup).

    Returns:
        dict per table with source/target counts and % delta.
    """
    source_counts = get_row_counts(source_layer)
    target_counts = get_row_counts(target_layer)

    comparison = {}
    shared_tables = set(source_counts.keys()) & set(target_counts.keys())

    for table in shared_tables:
        src = source_counts[table]
        tgt = target_counts[table]
        if src > 0:
            delta_pct = round(((tgt - src) / src) * 100, 2)
        else:
            delta_pct = None

        comparison[table] = {
            f"{source_layer}_count": src,
            f"{target_layer}_count": tgt,
            "delta_pct": delta_pct,
            "status": "OK" if tgt > 0 else "WARN",
        }

    return comparison


def run_row_count_report() -> bool:
    """Print a full row count report across all layers."""
    report = check_row_counts()
    all_ok = True

    print(f"\n{'='*60}")
    print(f"  ROW COUNT REPORT — ALL LAYERS")
    print(f"{'='*60}")

    for layer, tables in report.items():
        print(f"\n  [{layer.upper()}]")
        for table, info in tables.items():
            icon = "✓" if info["status"] == "OK" else ("⚠" if info["status"] == "WARN" else "✗")
            print(f"    {icon} {table}: {info['count']} rows")
            if info["status"] != "OK":
                all_ok = False

    # Cross-layer comparison
    print(f"\n  [BRONZE → SILVER COMPARISON]")
    comp = compare_layers("bronze", "silver")
    for table, info in comp.items():
        delta = f"{info['delta_pct']}%" if info["delta_pct"] is not None else "N/A"
        print(f"    {table}: {info['bronze_count']} → {info['silver_count']} ({delta})")

    print(f"\n{'='*60}")
    print(f"  Overall: {'ALL OK' if all_ok else 'ISSUES FOUND'}")
    print(f"{'='*60}\n")
    return all_ok


if __name__ == "__main__":
    run_row_count_report()
