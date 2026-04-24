
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

logger = setup_logger("dq_check_fk_integrity")

# FK rules: (child_table, child_col, parent_table, parent_col, layer)
FK_RULES = [
    # Silver layer
    {
        "name": "sales → customers",
        "layer": "silver",
        "child_table": "crm_sales_details",
        "child_col": "sales_cust_id",
        "parent_table": "crm_customers_info",
        "parent_col": "cst_id",
    },
    {
        "name": "sales → products",
        "layer": "silver",
        "child_table": "crm_sales_details",
        "child_col": "sales_prd_key",
        "parent_table": "crm_prd_info",
        "parent_col": "prd_key",
    },
    {
        "name": "erp_cust → crm_cust (via key)",
        "layer": "silver",
        "child_table": "erp_cust_az12",
        "child_col": "cid",
        "parent_table": "crm_customers_info",
        "parent_col": "cst_key",
    },
    {
        "name": "erp_location → crm_cust (via key)",
        "layer": "silver",
        "child_table": "erp_location_a101",
        "child_col": "cid",
        "parent_table": "crm_customers_info",
        "parent_col": "cst_key",
    },
    {
        "name": "erp_category → crm_products (via cat_id)",
        "layer": "silver",
        "child_table": "erp_px_cat_g1v2",
        "child_col": "id",
        "parent_table": "crm_prd_info",
        "parent_col": "cat_id",
    },
]
"""
DQ Check: Foreign Key Integrity

Validates referential integrity between tables across layers,
e.g. every sales_cust_id in sales should exist in customers.
"""

def check_fk_integrity() -> list[dict]:
    """
    Run all FK integrity checks.

    Returns:
        list of dicts with rule name, orphan_count, sample orphans, and status.
    """
    results = []

    for rule in FK_RULES:
        layer = rule["layer"]
        engine = get_engine(layer)
        child = rule["child_table"]
        child_col = rule["child_col"]
        parent = rule["parent_table"]
        parent_col = rule["parent_col"]

        query = text(f"""
            SELECT c.{child_col}, COUNT(*) AS cnt
            FROM {child} c
            LEFT JOIN {parent} p ON c.{child_col} = p.{parent_col}
            WHERE p.{parent_col} IS NULL
              AND c.{child_col} IS NOT NULL
            GROUP BY c.{child_col}
        """)

        try:
            with engine.connect() as conn:
                df = pd.read_sql(query, conn)
                orphan_count = int(df["cnt"].sum()) if not df.empty else 0
                sample = df[child_col].head(5).tolist() if not df.empty else []

                status = "PASS" if orphan_count == 0 else "FAIL"
                results.append({
                    "rule": rule["name"],
                    "layer": layer,
                    "orphan_count": orphan_count,
                    "sample_orphans": sample,
                    "status": status,
                })

                if status == "FAIL":
                    logger.warning(
                        f"[FK] {rule['name']}: {orphan_count} orphan rows "
                        f"({child}.{child_col} not in {parent}.{parent_col})"
                    )
                else:
                    logger.info(f"[FK] {rule['name']} — PASS")
        except Exception as e:
            logger.error(f"[FK] Error on rule '{rule['name']}': {e}")
            results.append({
                "rule": rule["name"],
                "layer": layer,
                "status": "ERROR",
                "error": str(e),
            })

    return results


def run_fk_integrity_report() -> bool:
    """Run FK integrity checks and print a report."""
    results = check_fk_integrity()
    all_pass = all(r["status"] == "PASS" for r in results)

    print(f"\n{'='*60}")
    print(f"  FOREIGN KEY INTEGRITY REPORT")
    print(f"{'='*60}")
    for r in results:
        icon = "✓" if r["status"] == "PASS" else "✗"
        print(f"  {icon} {r['rule']}: {r['status']}")
        if r["status"] == "FAIL":
            print(f"      Orphan rows: {r['orphan_count']}")
            print(f"      Samples: {r.get('sample_orphans', [])}")
        elif r["status"] == "ERROR":
            print(f"      Error: {r.get('error')}")
    print(f"{'='*60}")
    print(f"  Overall: {'ALL PASSED' if all_pass else 'ISSUES FOUND'}")
    print(f"{'='*60}\n")
    return all_pass


if __name__ == "__main__":
    run_fk_integrity_report()
