import os
import sys
import logging
import pandas as pd
from sqlalchemy import String, Integer, Float, DateTime

current_dir = os.path.dirname(os.path.abspath(__file__))
silver_folder = os.path.dirname(current_dir)
python_folder = os.path.dirname(silver_folder)

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
    
schema_products = {
    "prd_id"              : "int",
    "prd_key"             : "string",
    "prd_name"            : "string",
    "prd_cost"            : "float64",
    "prd_line"            : "string",
    "prd_start_date_raw"  : "datetime64[ns]",
    "prd_end_date_raw"    : "datetime64[ns]"
    }

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
    df["prd_name"] = df["prd_name"].str.strip().str.title()
    return df

def standardize_data(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        return df
    #! Product Line Standardization
    df["prd_line"] = (
        df["prd_line"]
        .str.strip().replace({
    "R": "Road",
	"M": "Mountain",
	"T": "Touring",
	"S": "Other sales"
        })
    )
    df["prd_line"] = df["prd_line"].fillna("Unknown")
    df["prd_cost"] = df["prd_cost"].fillna(0)
    df["prd_end_date_raw"] = df["prd_start_date_raw"].shift(-1) + pd.Timedelta(weeks=26)
    return df

#!transformation function to create new columns based on existing ones
def transform_crm_products(df: pd.DataFrame) -> pd.DataFrame:
    df["cat_id"] = df["prd_key"].str[:5]
    df["cat_id"] = df["cat_id"].str.replace("-", "_", regex=False)
    df["prd_key"] = df["prd_key"].str[6:]
    return df

#! data quality checks function to identify duplicates
def data_quality_checks(df: pd.DataFrame):  
    PRIMARY_KEY = ["prd_id"]
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
            logging.warning(
                f"[DUPLICATE FOUND] {PRIMARY_KEY[0]}={row['prd_id']} "
                f"→ occurrences={row['occurrences']}"
            )
    else:
        logging.info("No duplicates found")
    

def run_products_pipeline(table_name: str):
    df_products = extract_from_bronze(table_name)
    df_products = enforce_schema(df_products, schema_products)
    df_products = normalize_data(df_products)
    df_products = standardize_data(df_products)
    df_products = transform_crm_products(df_products)
    data_quality_checks(df_products) 
    df_products.to_sql(
        name = "crm_prd_info",
        con  = get_engine("silver"),
        if_exists = "replace",
        index=False,
        dtype={
            "prd_id"              : String(100),
            "prd_key"             : String(100),
            "cat_id"              : String(100),
            "prd_name"            : String(100),
            "prd_line"            : String(100),
            "prd_cost"            : Float(10,2),
            "prd_start_date_raw"  : DateTime(),
            "prd_end_date_raw"    : DateTime(),
            "loaded_at"           : DateTime()
         },
         chunksize=1000
         )
    

if __name__ == "__main__":
    run_products_pipeline("crm_prd_info")