import os
import sys
import logging
import pandas as pd
from sqlalchemy import String, DateTime

current_dir = os.path.dirname(os.path.abspath(__file__))
silver_folder = os.path.dirname(current_dir)
python_folder = os.path.dirname(silver_folder)

if python_folder not in sys.path:
    sys.path.append(python_folder)             # .../python

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
schema_customer ={
    "cst_id"              : "string",
    "cst_key"             : "string",
    "cst_firstname"       : "string",
    "cst_lastname"        : "string",
    "cst_marital_status"  : "string",
    "cst_gndr"            : "string",
    "cst_create_date_raw" : "datetime64[ns]"
    }

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
    TIMESTAMP_COL = "cst_create_date_raw"

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
    

    #! Logging
    logging.info(f"[DEDUP] Total rows   : {len(df)}")
    logging.info(f"[DEDUP] Kept rows    : {len(kept_rows)}")
    logging.info(f"[DEDUP] Deleted rows : {len(deleted_rows)}")
    return kept_rows, deleted_rows

def run_customers_pipeline(table_name: str):
    df_customers = extract_from_bronze(table_name)
    df_customers = enforce_schema(df_customers, schema_customer) # object → string, datetime → datetime64, etc.
    df_customers = normalize_data(df_customers)           
    df_customers = standardize_data(df_customers) # standardize gender and marital status values  

    data_quality_checks(df_customers) # log any duplicates found into log file (but do not remove yet)
    df_customers, df_duplicates = deduplicate(df_customers) # remove duplicates based on cst_id, keep latest loaded_at record
    
    df_customers.to_sql(
        name = "crm_customers_info",
        con  = get_engine("silver"),
         if_exists = "replace",
         index=False,
         dtype={
            "cst_id"              : String(100),
            "cst_key"             : String(100),
            "cst_firstname"       : String(100),
            "cst_lastname"        : String(100),
            "cst_marital_status"  : String(100),
            "cst_gndr"            : String(100),
            "cst_create_date_raw" : DateTime()
         },
         chunksize=1000
         )

if __name__ == "__main__":
    run_customers_pipeline("crm_customers_info")