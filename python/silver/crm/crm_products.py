import os
import sys
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

schema ={
    "prd_id"              : "int",
    "prd_key"             : "string",
    "prd_name"            : "string",
    "prd_cost"            : "float64",
    "prd_line"            : "string",
    "prd_start_date_raw"  : "datetime64[ns]",
    "prd_end_date_raw"    : "datetime64[ns]",
    "loaded_at"           : "datetime64[ns]"
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
    df["prd_key_"] = df["prd_key"].str[6:]
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
    

def main():
    df= extract_from_bronze("crm_prd_info")
    df = enforce_schema(df, schema)
    df = normalize_data(df)
    df = standardize_data(df)
    df = transform_crm_products(df)
    data_quality_checks(df)
    print(df.info())
    print(df.isnull().sum())

if __name__ == "__main__":
    main()