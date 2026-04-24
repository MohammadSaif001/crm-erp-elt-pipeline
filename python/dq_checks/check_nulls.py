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

logger = setup_logger("dq_check_nulls")

# Columns that should NEVER be null per table (silver layer expectations)
NOT_NULL_RULES = {
    "silver": {
        "crm_customers_info": ["cst_id", "cst_key", "cst_firstname", "cst_lastname"],
        "crm_prd_info": ["prd_id", "prd_key", "prd_name"],
        "crm_sales_details": ["sales_ord_num", "sales_prd_key", "sales_cust_id"],
        "erp_cust_az12": ["cid"],
        "erp_location_a101": ["cid", "country_name"],
        "erp_px_cat_g1v2": ["id", "cat", "subcat"],
    },
    "gold": {
        "dim_customers": ["customer_id", "customer_number", "first_name", "last_name"],
        "dim_products": ["product_id", "product_number", "product_name"],
        "fact_sales": ["order_number", "order_date"],
    },
}
"""
DQ Check: Null / Missing Value Detection

Checks for unexpected NULLs in critical (NOT NULL) columns.
"""

def check_nulls(layer: str = "silver") -> dict:
    """
    Check for NULL values in critical columns.

    Returns:
        dict mapping table_name -> list of { 'column': str, 'null_count': int, 'status': str }
    """
    rules = NOT_NULL_RULES.get(layer, {})
    if not rules:
        logger.warning(f"No null-check rules configured for layer: {layer}")
        return {}

    engine = get_engine(layer)
    results = {}

    for table, columns in rules.items():
        table_results = []
        try:
            with engine.connect() as conn:
                for col in columns:
                    query = text(f"SELECT COUNT(*) AS null_count FROM {table} WHERE {col} IS NULL")
                    df = pd.read_sql(query, conn)
                    null_count = int(df["null_count"].iloc[0])
                    status = "PASS" if null_count == 0 else "FAIL"
                    table_results.append({
                        "column": col,
                        "null_count": null_count,
                        "status": status,
                    })
                    if status == "FAIL":
                        logger.warning(
                            f"[NULLS] {layer}.{table}.{col} has {null_count} NULL values"
                        )
        except Exception as e:
            logger.error(f"[NULLS] Error checking {layer}.{table}: {e}")
            table_results.append({"column": "*", "status": "ERROR", "error": str(e)})

        results[table] = table_results

    return results


def run_null_checks(layer: str = "silver") -> bool:
    """Run null checks and return True if all pass."""
    results = check_nulls(layer)
    all_pass = True

    print(f"\n{'='*60}")
    print(f"  NULL CHECK REPORT — {layer.upper()} LAYER")
    print(f"{'='*60}")
    for table, checks in results.items():
        fails = [c for c in checks if c["status"] == "FAIL"]
        if fails:
            all_pass = False
            print(f"  ✗ {table}:")
            for f in fails:
                print(f"      {f['column']}: {f['null_count']} NULLs")
        else:
            print(f"  ✓ {table}: PASS (no unexpected NULLs)")
    print(f"{'='*60}")
    print(f"  Overall: {'ALL PASSED' if all_pass else 'ISSUES FOUND'}")
    print(f"{'='*60}\n")
    return all_pass


if __name__ == "__main__":
    for layer in ["silver", "gold"]:
        run_null_checks(layer)
