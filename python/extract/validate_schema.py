"""
Extract Module: Schema Validation
----------------------------------
Validates CSV column names and data types BEFORE loading into bronze.
Catches schema drift (missing/extra columns, wrong formats) early.

Usage:
    from extract.validate_schema import validate_all_schemas, validate_schema
"""
import os
import sys
import logging
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
python_folder = os.path.dirname(current_dir)
if python_folder not in sys.path:
    sys.path.append(python_folder)

from extract.read_csv_files import read_source_file

logger = logging.getLogger(__name__)

# Expected columns per source table (after header normalization: stripped + lowered).
# These match what the bronze layer expects.
EXPECTED_SCHEMAS = {
    "crm_customers_info": {
        "source": "source_crm",
        "file_name": "cust_info.csv",
        "required_columns": [
            "cst_id", "cst_key", "cst_firstname", "cst_lastname",
            "cst_marital_status", "cst_gndr", "cst_create_date",
        ],
    },
    "crm_prd_info": {
        "source": "source_crm",
        "file_name": "prd_info.csv",
        "required_columns": [
            "prd_id", "prd_key", "prd_name", "prd_cost",
            "prd_line", "prd_start_date", "prd_end_date",
        ],
    },
    "crm_sales_details": {
        "source": "source_crm",
        "file_name": "sales_details.csv",
        "required_columns": [
            "sls_ord_num", "sls_prd_key", "sls_cust_id",
            "sls_order_date", "sls_ship_date", "sls_due_date",
            "sls_sales", "sls_quantity", "sls_price",
        ],
    },
    "erp_cust_az12": {
        "source": "source_erp",
        "file_name": "CUST_AZ12.csv",
        "required_columns": ["cid", "bdate", "gen"],
    },
    "erp_location_a101": {
        "source": "source_erp",
        "file_name": "LOC_A101.csv",
        "required_columns": ["cid", "cntry"],
    },
    "erp_px_cat_g1v2": {
        "source": "source_erp",
        "file_name": "PX_CAT_G1V2.csv",
        "required_columns": ["id", "cat", "subcat", "maintenance"],
    },
}


def validate_schema(
    table_name: str,
    df: pd.DataFrame | None = None,
) -> dict:
    """
    Validate a source CSV's columns against the expected schema.

    Args:
        table_name: Key in EXPECTED_SCHEMAS (e.g. 'crm_customers_info').
        df: Optional pre-loaded DataFrame. If None, reads the CSV automatically.

    Returns:
        dict with keys:
            table, status ('PASS'|'FAIL'), missing_columns, extra_columns, actual_columns
    """
    if table_name not in EXPECTED_SCHEMAS:
        return {
            "table": table_name,
            "status": "ERROR",
            "error": f"No schema definition found for '{table_name}'",
        }

    spec = EXPECTED_SCHEMAS[table_name]
    expected = set(spec["required_columns"])

    if df is None:
        try:
            df = read_source_file(spec["source"], spec["file_name"])
        except FileNotFoundError as e:
            return {
                "table": table_name,
                "status": "ERROR",
                "error": str(e),
            }

    actual = set(df.columns)
    missing = expected - actual
    extra = actual - expected

    status = "PASS" if not missing else "FAIL"

    if missing:
        logger.warning(
            f"[SCHEMA] {table_name}: missing columns {sorted(missing)}"
        )
    if extra:
        logger.info(
            f"[SCHEMA] {table_name}: extra columns {sorted(extra)} (ignored)"
        )

    return {
        "table": table_name,
        "status": status,
        "missing_columns": sorted(missing),
        "extra_columns": sorted(extra),
        "actual_columns": sorted(actual),
        "expected_columns": sorted(expected),
    }


def validate_all_schemas() -> list[dict]:
    """
    Validate schemas for all configured source files.

    Returns:
        List of validation results (one per table).
    """
    results = []
    for table_name in EXPECTED_SCHEMAS:
        result = validate_schema(table_name)
        results.append(result)
    return results


def validate_data_types(df: pd.DataFrame, rules: dict[str, str]) -> list[dict]:
    """
    Spot-check that raw values can be coerced to expected types.

    Args:
        df: Source DataFrame (all string columns).
        rules: dict mapping column_name -> expected type
               ('int', 'float', 'date')

    Returns:
        List of dicts with column, expected_type, invalid_count, sample_invalid.
    """
    issues = []
    for col, expected_type in rules.items():
        if col not in df.columns:
            continue

        series = df[col].dropna()
        if series.empty:
            continue

        if expected_type in ("int", "float"):
            coerced = pd.to_numeric(series, errors="coerce")
            invalid = series[coerced.isna()]
        elif expected_type == "date":
            coerced = pd.to_datetime(series, errors="coerce")
            invalid = series[coerced.isna()]
        else:
            continue

        if not invalid.empty:
            issues.append({
                "column": col,
                "expected_type": expected_type,
                "invalid_count": len(invalid),
                "sample_invalid": invalid.head(5).tolist(),
            })
            logger.warning(
                f"[DTYPE] {col}: {len(invalid)} values cannot be parsed as {expected_type}"
            )

    return issues


def run_schema_validation_report() -> bool:
    """Print a full schema validation report."""
    results = validate_all_schemas()
    all_pass = all(r["status"] == "PASS" for r in results)

    print(f"\n{'='*60}")
    print(f"  SCHEMA VALIDATION REPORT")
    print(f"{'='*60}")
    for r in results:
        icon = "✓" if r["status"] == "PASS" else ("✗" if r["status"] == "FAIL" else "⚠")
        print(f"  {icon} {r['table']}: {r['status']}")
        if r.get("missing_columns"):
            print(f"      Missing: {r['missing_columns']}")
        if r.get("extra_columns"):
            print(f"      Extra:   {r['extra_columns']}")
        if r.get("error"):
            print(f"      Error:   {r['error']}")
    print(f"{'='*60}")
    print(f"  Overall: {'ALL PASSED' if all_pass else 'ISSUES FOUND'}")
    print(f"{'='*60}\n")
    return all_pass


if __name__ == "__main__":
    from utils.logger import setup_logger
    setup_logger("validate_schema")
    run_schema_validation_report()
