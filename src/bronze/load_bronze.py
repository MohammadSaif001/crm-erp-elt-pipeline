import json
import os
import time
from typing import Any

import numpy as np
import pandas as pd

from src.bronze.hash import generate_file_hash
from src.bronze.ingestion_checker import is_hash_processed, log_ingestion
from src.core.database import get_engine
from src.core.logger import setup_logger
from src.core.database import get_engine
from src.core.paths import get_raw_data_path
from src.extract.validate_schema import validate_schema

logger = setup_logger("bronze")


#! Bronze CSV Reader Function
def read_bronze_csv(csv_path: str) -> pd.DataFrame:
    """
    Bronze CSV reader:
    - checks file exists
    - reads all columns as string
    - normalizes headers
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found at: {csv_path}")

    df = pd.read_csv(csv_path, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    return df


def add_raw_row(df: pd.DataFrame) -> pd.DataFrame:

    # Replace NaN with None - handle both float NaN and string 'NaN'
    cleaned_df = df.replace({np.nan: None, "NaN": None, "nan": None})
    cleaned_df = cleaned_df.where(pd.notnull(cleaned_df), None)

    # Convert each row to valid JSON
    df["raw_row"] = cleaned_df.apply(lambda row: json.dumps(row.to_dict()), axis=1)

    return df


#! Database Connection Function
def data_base_connection() -> None | Any:
    try:
        engine = get_engine("bronze")
        logger.info("Database connected successfully for bronze layer.")
        return engine  # Return it!
    except Exception as e:
        logger.exception("Connection error while creating bronze DB engine: %s", e)
        return None


#! 1.Customer Load Function
def load_cust_info() -> bool:

    start_time = time.time()
    source = "source_crm"
    file_name = "cust_info.csv"
    table_name = "crm_customers_info"

    logger.info(f"[START] Loading table: {table_name}")

    engine = data_base_connection()

    if engine is None:
        logger.warning("Exiting due to database connection failure.")
        return False
    try:
        #! Read CSV (wrapped)
        csv_path = get_raw_data_path(os.path.join("source_crm", "cust_info.csv"))
        #! Generate file hash for idempotency check
        file_hash = generate_file_hash(str(csv_path))

        if is_hash_processed(engine, file_hash):
            logger.info(
                f"[SKIP] File with hash {file_hash} already processed. Skipping ingestion."
            )
            return False

        df = read_bronze_csv(str(csv_path))
        
        #! Add raw_row (wrapped)
        df = add_raw_row(df)

        check_schema = validate_schema("crm_customers_info", df=df)
        if check_schema["status"] != "PASS":
            logger.error(
                f"[ERROR] Schema validation failed for {file_name}: "
                f"missing {check_schema.get('missing_columns')}"
            )
            return False

        #! Map Columns
        # .get()
        df["cst_id"] = df.get("cst_id")
        df["cst_key"] = df.get("cst_key")
        df["cst_firstname"] = df.get("cst_firstname")
        df["cst_lastname"] = df.get("cst_lastname")
        df["cst_marital_status"] = df.get("cst_marital_status")
        df["cst_gndr"] = df.get("cst_gndr")
        df["cst_create_date_raw"] = df.get("cst_create_date")

        # * Select columns to write
        final_cols = [
            "raw_row",
            "cst_id",
            "cst_key",
            "cst_firstname",
            "cst_lastname",
            "cst_marital_status",
            "cst_gndr",
            "cst_create_date_raw",
        ]

        # * Filter dataframe to only include columns that actually exist now
        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]

        logger.info(f"Writing {len(df_final)} rowsto table '{table_name}'...")

        df_final.to_sql(
            name="crm_customers_info",
            con=engine,
            if_exists="append",
            index=False,
        )
        log_ingestion(
            engine,
            source_name=source,
            file_name=file_name,
            file_hash=file_hash,
            row_count=len(df_final),
        )

        elapsed_time = time.time() - start_time

        logger.info(
            f"[END] Loaded table: {table_name} "
            f"| Rows={len(df_final)} "
            f"| Time={elapsed_time:.2f}s"
        )

        logger.info("Success: Data loaded into bronze_db.crm_customers_info")

        return True

    except Exception as e:
        logger.exception(f"[ERROR] Loading table: {table_name} | Error: {e}")
        return False


#! Sales Load Function
def load_sales_details_info() -> bool:

    start_time = time.time()
    source = "source_crm"
    file_name = "sales_details.csv"
    table_name = "crm_sales_details"

    logger.info(f"[START] Loading table: {table_name}")

    #! Connect to Database
    engine = data_base_connection()
    if engine is None:
        logger.warning("Exiting due to database connection failure.")
        return False

    try:
        csv_path = get_raw_data_path(os.path.join("source_crm", "sales_details.csv"))
        #! Check if file already processed using hash
        file_hash = generate_file_hash(str(csv_path))
        if is_hash_processed(engine, file_hash):
            logger.info(
                f"[SKIP] File with hash {file_hash} already processed. Skipping ingestion."
            )
            return False

        #! Read CSV (wrapped)
        df = read_bronze_csv(str(csv_path))

        #! Add raw_row (wrapped)
        df = add_raw_row(df)
        check_schema = validate_schema("crm_sales_details", df=df)
        if check_schema["status"] != "PASS":
            logger.error(
                f"[ERROR] Schema validation failed for {file_name}: "
                f"missing {check_schema.get('missing_columns')}"
            )
            return False

        #! Map Columns
        df["ingest_id"] = df.get("ingest_id")
        df["sales_prd_key"] = df.get("sls_prd_key")
        df["sales_ord_num"] = df.get("sls_ord_num")
        df["sales_cust_id"] = df.get("sls_cust_id")
        df["sales_order_date_raw"] = df.get("sls_order_dt")
        df["sales_ship_date_raw"] = df.get("sls_ship_dt")
        df["sales_due_date_raw"] = df.get("sls_due_dt")
        df["sales_sales"] = df.get("sls_sales")
        df["sales_quantity"] = df.get("sls_quantity")
        df["sales_price"] = df.get("sls_price")
        df["loaded_at"] = pd.Timestamp.now()

        final_cols = [
            "ingest_id",
            "raw_row",
            "sales_prd_key",
            "sales_ord_num",
            "sales_cust_id",
            "sales_order_date_raw",
            "sales_ship_date_raw",
            "sales_due_date_raw",
            "sales_sales",
            "sales_quantity",
            "sales_price",
            "loaded_at",
        ]
        # * Filter dataframe to only include columns that actually exist now
        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]

        logger.info(f"Writing {len(df_final)} rowsto table '{table_name}'...")

        df_final.to_sql(
            name="crm_sales_details",
            con=engine,
            if_exists="append",
            index=False,
        )
        #! Log ingestion in ingestion_log table
        log_ingestion(
            engine,
            source_name=source,
            file_name=file_name,
            file_hash=file_hash,
            row_count=len(df_final),
        )

        elapsed_time = time.time() - start_time

        logger.info(
            f"[END] Loaded table: {table_name} "
            f"| Rows={len(df_final)} "
            f"| Time={elapsed_time:.2f}s"
        )

        logger.info("Success: Data loaded into bronze_db.crm_customers_info")

        return True

    except Exception as e:
        logger.exception(f"[ERROR] Loading table: {table_name} | Error: {e}")
        return False


#!Product Load Function
def load_prd_info() -> bool:

    start_time = time.time()
    source = "source_crm"
    file_name = "prd_info.csv"
    table_name = "crm_prd_info"

    logger.info(f"[START] Loading table: {table_name}")

    #! Connect to Database
    engine = data_base_connection()
    if engine is None:
        logger.warning("Exiting due to database connection failure.")
        return False

    try:
        #! 1. Read CSV
        csv_path = get_raw_data_path(os.path.join("source_crm", "prd_info.csv"))
        #! Check if file already processed using hash
        file_hash = generate_file_hash(str(csv_path))
        if is_hash_processed(engine, file_hash):
            logger.info(
                f"[SKIP] File with hash {file_hash} already processed. Skipping ingestion."
            )
            return False

        df = read_bronze_csv(str(csv_path))
        #! 2. Add raw_row
        df = add_raw_row(df)
        check_schema = validate_schema("crm_prd_info", df=df)
        if check_schema["status"] != "PASS":
            logger.error(
                f"[ERROR] Schema validation failed for {file_name}: "
                f"missing {check_schema.get('missing_columns')}"
            )
            return False
        df["prd_id"] = df.get("prd_id")
        df["prd_key"] = df.get("prd_key")
        df["prd_name"] = df.get("prd_nm")
        df["prd_cost"] = df.get("prd_cost")
        df["prd_line"] = df.get("prd_line")
        df["prd_start_date_raw"] = df.get("prd_start_dt")
        df["prd_end_date_raw"] = df.get("prd_end_dt")

        #! Select columns to write
        final_cols = [
            "raw_row",
            "prd_id",
            "prd_key",
            "prd_name",
            "prd_cost",
            "prd_line",
            "prd_start_date_raw",
            "prd_end_date_raw",
        ]

        #! Filter dataframe to only include columns that actually exist now
        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]

        #! console log
        logger.info(f"Writing {len(df_final)} rows to table 'crm_prd_info'...")
        df_final.to_sql(
            name="crm_prd_info",
            con=engine,
            if_exists="append",
            index=False,
        )

        #! Log ingestion in ingestion_log table
        log_ingestion(
            engine,
            source_name=source,
            file_name=file_name,
            file_hash=file_hash,
            row_count=len(df_final),
        )

        elapsed_time = time.time() - start_time
        logger.info(
            f"[END] Loaded table: {table_name} "
            f"| Rows={len(df_final)} "
            f"| Time={elapsed_time:.2f}s"
        )

        logger.info("Success: Data loaded into bronze_db.crm_customers_info")

        return True

    except Exception as e:
        logger.exception(f"[ERROR] Loading table: {table_name} | Error: {e}")
        return False


#! ERP Load Functions
def load_erp_cust_az12() -> bool:

    start_time = time.time()
    source = "source_erp"
    file_name = "CUST_AZ12.csv"
    table_name = "erp_cust_az12"
    logger.info(f"[START] Loading table: {table_name}")

    #! Connect to Database
    engine = data_base_connection()
    if engine is None:
        logger.warning("[WARNING] Exiting due to database connection failure.")
        return False
    try:
        #! Read CSV (wrapped)
        csv_path = get_raw_data_path(os.path.join("source_erp", "CUST_AZ12.csv"))
        #! Generate file hash for idempotency check
        file_hash = generate_file_hash(str(csv_path))

        if is_hash_processed(engine, file_hash):
            logger.info(
                f"[SKIP] File with hash {file_hash} already processed. Skipping ingestion."
            )
            return False

        df = read_bronze_csv(str(csv_path))

        #! Add raw_row (wrapped)
        df = add_raw_row(df)
        check_schema = validate_schema("erp_cust_az12", df=df)
        if check_schema["status"] != "PASS":
            logger.error(
                f"[ERROR] Schema validation failed for {file_name}: "
                f"missing {check_schema.get('missing_columns')}"
            )
            return False

        #! Colunmn Mapping
        df["ingest_id"] = df.get("ingest_id")
        df["cid"] = df.get("cid")
        df["birth_date_raw"] = df.get("bdate")
        df["gender_raw"] = df.get("gen")
        df["loaded_at"] = pd.Timestamp.now()

        # * Select columns to write
        final_cols = [
            "ingest_id",
            "raw_row",
            "cid",
            "birth_date_raw",
            "gender_raw",
            "loaded_at",
        ]

        # * Filter dataframe to only include columns that actually exist now
        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]

        #! console log
        logger.info(f"Writing {len(df_final)} rows to table 'erp_cust_az12'...")
        df_final.to_sql(
            name="erp_cust_az12",
            con=engine,
            if_exists="append",
            index=False,
        )
        log_ingestion(
            engine,
            source_name=source,
            file_name=file_name,
            file_hash=file_hash,
            row_count=len(df_final),
        )

        elapsed_time = time.time() - start_time

        logger.info(
            f"[END] Loaded table: {table_name} "
            f"| Rows={len(df_final)} "
            f"| Time={elapsed_time:.2f}s"
        )

        logger.info(f"Success: Data loaded into bronze_db.{table_name}")

        return True
    except Exception as e:
        logger.exception(f"[ERROR] Loading table: {table_name} | Error: {e}")
        return False


def load_erp_location_a101() -> bool:
    start_time = time.time()
    source = "source_erp"
    file_name = "LOC_A101.csv"
    table_name = "erp_location_a101"
    logger.info(f"[START] Loading table: {table_name}")

    logger.info("Starting Bronze Load: ERP Location.")

    #! Connect to Database
    engine = data_base_connection()
    if engine is None:
        logger.warning("Exiting due to database connection failure.")
        return False
    try:
        #! Read CSV (wrapped)
        csv_path = get_raw_data_path(os.path.join("source_erp", "LOC_A101.csv"))
        #! Generate file hash for idempotency check
        file_hash = generate_file_hash(str(csv_path))

        if is_hash_processed(engine, file_hash):
            logger.info(
                f"[SKIP] File with hash {file_hash} already processed. Skipping ingestion."
            )
            return False

        df = read_bronze_csv(str(csv_path))

        #! Add raw_row (wrapped)
        df = add_raw_row(df)
        check_schema = validate_schema("erp_location_a101", df=df)
        if check_schema["status"] != "PASS":
            logger.error(
                f"[ERROR] Schema validation failed for {file_name}: "
                f"missing {check_schema.get('missing_columns')}"
            )
            return False

        #! 3.Colunmn Mapping
        df["cid"] = df.get("cid")
        df["country_name"] = df.get("cntry")
        df["loaded_at"] = pd.Timestamp.now()

        final_cols = ["raw_row", "cid", "country_name", "loaded_at"]

        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]

        logger.info(f"Writing {len(df_final)} rowsto table '{table_name}'...")

        df_final.to_sql(
            name="erp_location_a101",
            con=engine,
            if_exists="append",
            index=False,
        )
        log_ingestion(
            engine,
            source_name=source,
            file_name=file_name,
            file_hash=file_hash,
            row_count=len(df_final),
        )

        elapsed_time = time.time() - start_time

        logger.info(
            f"[END] Loaded table: {table_name} "
            f"| Rows={len(df_final)} "
            f"| Time={elapsed_time:.2f}s"
        )

        logger.info(f"Success: Data loaded into bronze_db.{table_name}")

        return True
    except Exception as e:
        logger.exception(f"[ERROR] Loading table: {table_name} | Error: {e}")
        return False


def load_erp_px_cat_g1v2() -> bool:
    start_time = time.time()
    source = "source_erp"
    file_name = "PX_CAT_G1V2.csv"
    bronze_table = "erp_px_cat_g1v2"
    table_name = "erp_px_cat_g1v2"
    logger.info(f"[START] Loading table: {table_name}")
    logger.info("Starting Bronze Load: ERP Category.")

    #! Connect to Database
    engine = data_base_connection()
    if engine is None:
        logger.warning("Exiting due to database connection failure.")
        return False
    try:
        #! Read CSV (wrapped)
        csv_path = get_raw_data_path(os.path.join("source_erp", "PX_CAT_G1V2.csv"))
        #! Generate file hash for idempotency check
        file_hash = generate_file_hash(str(csv_path))

        if is_hash_processed(engine, file_hash):
            logger.info(
                f"[SKIP] File with hash {file_hash} already processed. Skipping ingestion."
            )
            return False

        df = read_bronze_csv(str(csv_path))

        #! Add raw_row (wrapped)
        df = add_raw_row(df)
        check_schema = validate_schema("erp_px_cat_g1v2", df=df)
        if check_schema["status"] != "PASS":
            logger.error(
                f"[ERROR] Schema validation failed for {file_name}: "
                f"missing {check_schema.get('missing_columns')}"
            )
            return False

        #! 3.Colunmn Mapping
        df["ingest_id"] = df.get("ingest_id")
        df["id"] = df.get("id")
        df["cat"] = df.get("cat")
        df["subcat"] = df.get("subcat")
        df["maintenance_raw"] = df.get("maintenance")
        df["loaded_at"] = pd.Timestamp.now()

        final_cols = [
            "ingest_id",
            "raw_row",
            "id",
            "cat",
            "subcat",
            "maintenance_raw",
            "loaded_at",
        ]

        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]

        logger.info(f"Writing {len(df_final)} rowsto table '{table_name}'...")

        df_final.to_sql(
            name="erp_px_cat_g1v2",
            con=engine,
            if_exists="append",
            index=False,
        )
        log_ingestion(
            engine,
            source_name=source,
            file_name=file_name,
            file_hash=file_hash,
            row_count=len(df_final),
        )

        elapsed_time = time.time() - start_time

        logger.info(
            f"[END] Loaded table: {table_name} "
            f"| Rows={len(df_final)} "
            f"| Time={elapsed_time:.2f}s"
        )

        logger.info(f"Success: Data loaded into bronze_db.{table_name}")

        return True
    except Exception as e:
        logger.exception(f"[ERROR] Loading table: {table_name} | Error: {e}")
        return False


#! Orchestration Function
def run_bronze_pipeline() -> None:
    """
    Orchestrates complete Bronze layer ingestion.
    Entry point for local runs, schedulers, and future Airflow DAGs.
    """
    logger.info("Starting Bronze Layer Pipeline...")

    batch_start = time.time()
    logger.info("[BATCH START] Bronze layer ingestion started")

    # CRM sources
    load_cust_info()
    load_prd_info()
    load_sales_details_info()

    # ERP sources
    load_erp_cust_az12()
    load_erp_location_a101()
    load_erp_px_cat_g1v2()

    logger.info("Bronze Layer Pipeline Completed Successfully.")
    batch_duration = time.time() - batch_start
    logger.info(
        f"[BATCH END] Bronze layer completed | Total time={batch_duration:.2f}s"
    )
    logger.info(f"Total Bronze Layer Time: {batch_duration:.2f} seconds.")


def main():
    run_bronze_pipeline()


if __name__ == "__main__":
    main()
