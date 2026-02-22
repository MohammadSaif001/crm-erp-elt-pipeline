import os
import sys
import time
import logging
import numpy as np
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
silver_folder = os.path.dirname(current_dir)
python_folder = os.path.dirname(silver_folder)

if python_folder not in sys.path:
    sys.path.append(python_folder)             # .../python

if python_folder not in sys.path:
    sys.path.append(python_folder)


from utils.db_connection import get_engine
from utils.paths import get_raw_data_path

def extract_from_bronze(table_name: str) -> pd.DataFrame:
    engine = get_engine("bronze")
    try:
        return pd.read_sql(f"SELECT * FROM {table_name}", engine)
    except Exception as e:
        raise RuntimeError(f"Failed to extract from bronze table {table_name}") from e
    
logging.basicConfig(
    filename=r"D:\data_engineering_project\data\logs\pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
#! Define schema for data types
schema ={
    "cst_id"              : "string",
    "cst_key"             : "string",
    "cst_firstname"       : "string",
    "cst_lastname"        : "string",
    "cst_marital_status"  : "string",
    "cst_gndr"            : "string",
    "cst_create_date_raw" : "datetime64[ns]",
    "loaded_at"          : "datetime64[ns]"
    }
# TODO : Implement the remaining functions below as needed in ETL process or pipeline.
#! combined normalization function for all string columns in the dataframe
def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    str_cols = df.select_dtypes(include="string").columns
    for col in str_cols:
        logging.info(f"Normalizing nulls in column: {col}")
        df[col] = (
            df[col]
            .str.strip()
            .replace(
                ["", "NULL", "null", "None", "none", "nan", "NaN"], 
                pd.NA
                )
        )
    df.drop("raw_row",axis=1,inplace=True)
    df[["cst_firstname","cst_lastname"]] = df[["cst_firstname","cst_lastname"]].apply(lambda x: x.str.strip().str.title())
    return df

#! high level schema enforcement function 
def enforce_schema(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    for column, dtype in schema.items():

        if column not in df.columns:
            #! log warning and skip missing columns
            logging.warning(f"[SCHEMA WARNING] Column missing: {column}")
            continue
        if dtype in ("Int64", "int64", "float64"):
            df[column] = pd.to_numeric(df[column], errors="coerce")
            if dtype == "Int64":
                df[column] = df[column].astype("Int64")
        elif dtype.startswith("datetime"):
            df[column] = pd.to_datetime(df[column], errors="coerce")
        elif dtype == "boolean":
            df[column] = df[column].astype("boolean")
        elif dtype == "string":
            df[column] = df[column].astype("string")
        else:
            # fallback (rare cases)
            df[column] = df[column].astype(dtype)

    return df

#! data quality checks function to identify duplicates based on
#!primary key and log the summary of duplicates found in the dataframe
def data_quality_checks(df: pd.DataFrame):  
    PRIMARY_KEY = ["cst_id"]
    dup_mask = df.duplicated(subset=PRIMARY_KEY, keep=False)
    dup_rows = df[dup_mask]
    if not dup_rows.empty:
        dup_summary = (
        dup_rows
        .groupby(PRIMARY_KEY)
        .size()
        .reset_index(name="occurrences")
        )
        for _, row in dup_summary.iterrows():
            logging.info(
                f"[DUPLICATE FOUND] {PRIMARY_KEY[0]}={row['cst_id']} "
                f"→ occurrences={row['occurrences']}"
            )
    else:
        logging.info("No duplicates found")
    

def standardize_data(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        return df
    #! Gender Standardization
    df["cst_gndr"] = (
        df["cst_gndr"]
        .str.lower()
        .map({
            "m": "Male",
            "f": "Female",
        })
    )
    # Fill unmapped (including NULL) with Unknown
    df["cst_gndr"] = df["cst_gndr"].fillna("Unknown")


    #!Marital Status Standardization
    df["cst_marital_status"] = (
        df["cst_marital_status"]
        .str.lower()
        .map({
            "s": "Single",
            "m": "Married",
        })
    )

    df["cst_marital_status"] = df["cst_marital_status"].fillna("Unknown")

    return df

#! clean function for deleting duplicate records 
def deduplicate(df: pd.DataFrame):
    PRIMARY_KEY = ["cst_id"]
    TIMESTAMP_COL = "loaded_at"

    if df.empty:
        logging.info("[DEDUP] Empty DataFrame.")
        return df, pd.DataFrame()
    #!Sort so latest loaded_at comes first
    df_sorted = df.sort_values(
        by=TIMESTAMP_COL,
        ascending=False
    )
    #!Identify duplicates (keep latest)
    dup_mask = df_sorted.duplicated(
        subset=PRIMARY_KEY,
        keep="first"
    )
    #! Separate kept vs deleted rows
    kept_rows = df_sorted[~dup_mask].copy()
    deleted_rows = df_sorted[dup_mask].copy()
    if not deleted_rows.empty:
        logging.info(f"[DEDUP] Found {len(deleted_rows)} duplicate rows based on {PRIMARY_KEY}")
        # logging.info(f"[DEDUP] Sample duplicates:\n{deleted_rows.head()}")

    #! Logging
    logging.info(f"[DEDUP] Total rows   : {len(df)}")
    logging.info(f"[DEDUP] Kept rows    : {len(kept_rows)}")
    logging.info(f"[DEDUP] Deleted rows : {len(deleted_rows)}")
    return kept_rows, deleted_rows

def run_silver_pipeline(table_name: str):
    df = extract_from_bronze(table_name)
    df = enforce_schema(df, schema)     # object → string, datetime → datetime64, etc.
    df = normalize_data(df)           
    df = standardize_data(df) # standardize gender and marital status values  

    data_quality_checks(df)

    print(df.head(10))

#     # # check nulls after normalization
#     # df_clean, df_deleted = deduplicate(df)
#     # load_to_silver(df_clean, table_name)

if __name__ == "__main__":
    run_silver_pipeline("crm_customers_info")