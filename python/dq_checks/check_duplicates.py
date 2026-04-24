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

logger = setup_logger("dq_check_duplicates")

# Define primary/unique keys per layer and table
TABLE_KEYS = {
    "bronze": {
        "crm_customers_info": ["cst_id"],
        "crm_prd_info": ["prd_id"],
        "crm_sales_details": ["sales_ord_num", "sales_prd_key"],
        "erp_cust_az12": ["cid"],
        "erp_location_a101": ["cid"],
        "erp_px_cat_g1v2": ["id"],
    },
    "silver": {
        "crm_customers_info": ["cst_id"],
        "crm_prd_info": ["prd_id"],
        "crm_sales_details": ["sales_ord_num", "sales_prd_key"],
        "erp_cust_az12": ["cid"],
        "erp_location_a101": ["cid"],
        "erp_px_cat_g1v2": ["id"],
    },
}
"""
DQ Check: Duplicate Detection

Checks for duplicate rows on primary/unique key columns across all layers.
"""

def check_duplicates(layer: str = "silver") -> dict:
    """
    Check for duplicates on defined key columns for each table in a layer.

    Returns:
        dict mapping table_name -> { 'duplicate_count': int, 'total_rows': int, 'status': 'PASS'|'FAIL' }
    """
    tables = TABLE_KEYS.get(layer, {})
    if not tables:
        logger.warning(f"No tables configured for layer: {layer}")
        return {}

    engine = get_engine(layer)
    results = {}

    for table, keys in tables.items():
        key_cols = ", ".join(keys)
        query = text(f"""
            SELECT {key_cols}, COUNT(*) AS cnt
            FROM {table}
            GROUP BY {key_cols}
            HAVING COUNT(*) > 1
        """)
        total_query = text(f"SELECT COUNT(*) AS total FROM {table}")

        try:
            with engine.connect() as conn:
                df_dups = pd.read_sql(query, conn)
                df_total = pd.read_sql(total_query, conn)
                total_rows = int(df_total["total"].iloc[0])
                dup_count = int(df_dups["cnt"].sum()) if not df_dups.empty else 0

                status = "PASS" if dup_count == 0 else "FAIL"
                results[table] = {
                    "duplicate_count": dup_count,
                    "total_rows": total_rows,
                    "key_columns": keys,
                    "status": status,
                }

                if status == "FAIL":
                    logger.warning(
                        f"[DUPLICATES] {layer}.{table} has {dup_count} duplicate rows on {keys}"
                    )
                else:
                    logger.info(f"[DUPLICATES] {layer}.{table} — PASS (no duplicates)")
        except Exception as e:
            logger.error(f"[DUPLICATES] Error checking {layer}.{table}: {e}")
            results[table] = {"status": "ERROR", "error": str(e)}

    return results


def run_duplicate_checks(layer: str = "silver") -> bool:
    """Run duplicate checks and return True if all pass."""
    results = check_duplicates(layer)
    all_pass = all(r.get("status") == "PASS" for r in results.values())

    print(f"\n{'='*60}")
    print(f"  DUPLICATE CHECK REPORT — {layer.upper()} LAYER")
    print(f"{'='*60}")
    for table, info in results.items():
        icon = "✓" if info["status"] == "PASS" else "✗"
        print(f"  {icon} {table}: {info['status']}")
        if info["status"] == "FAIL":
            print(f"      Duplicates: {info['duplicate_count']} on keys {info.get('key_columns')}")
        elif info["status"] == "ERROR":
            print(f"      Error: {info.get('error')}")
    print(f"{'='*60}")
    print(f"  Overall: {'ALL PASSED' if all_pass else 'ISSUES FOUND'}")
    print(f"{'='*60}\n")
    return all_pass


if __name__ == "__main__":
    for layer in ["bronze", "silver"]:
        run_duplicate_checks(layer)
