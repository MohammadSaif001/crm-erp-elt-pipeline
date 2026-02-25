import os
import sys
import logging
import pandas as pd 
from sqlalchemy import String,DateTime

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

schema_customer ={
    "cid"                 : "string",
    "birth_date_raw"      : "datetime64[ns]",
    "gender_raw"          : "string"
    }

schema_location = {
    "cid"                 : "string",
    "country_name"        : "string",
}

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
#! Customer ID Standardization 
def standardize_customer_id(df: pd.DataFrame) -> pd.DataFrame:

    if "cid" not in df.columns:
        logging.warning("[CID WARNING] 'cid' column not found.")
        return df
    before = len(df)
    df = df.loc[df["cid"].str.len() >= 10].copy()
    dropped = before - len(df)
    if dropped > 0:
        logging.warning(
            f"{dropped} records dropped due to invalid CID length."
        )
    df.loc[:, "cid"] = df["cid"].astype(str).str[-10:]

    return df

customer_replacemts = {
    "gender_raw": {
        "M": "Male",
        "F": "Female",
        "": pd.NA
    }
}

location_replacements ={
    "country_name": {
        "USA" : "United States",
        "US"  : "United States",
        "DE"  : "Germany",
        ""    : pd.NA,
        "NONE": pd.NA
    }
}

def apply_value_replacements(df: pd.DataFrame,replacements: dict) -> pd.DataFrame:
    """
    Apply value mappings to multiple columns.

    Args:
        df: Input dataframe
        replacements: Dictionary of {column: {old_value: new_value}}

    Returns:
        Updated dataframe
    """

    df = df.copy()

    for column, mapping in replacements.items():

        if column not in df.columns:
            logging.warning(f"[REPLACEMENT WARNING] Column '{column}' not found.")
            continue

        df.loc[:, column] = (
            df[column]
            .str.strip()
            .replace(mapping)
        )

    return df


#! Drop technical columns that are not needed in the silver layer
def drop_technical_columns(df: pd.DataFrame,drop_columns = "raw_row") -> pd.DataFrame:
    df = df.drop(columns=drop_columns, errors="ignore")
    return df


def run_customer_pipeline():
    logging.info("Starting ERP Customers Silver Pipeline")
    try:
        df_customer = extract_from_bronze("erp_cust_az12")
        logging.info(f"Extracted {len(df_customer)} records from bronze.")
        
        df_customer = enforce_schema(df_customer, schema_customer)
        logging.info("Schema enforcement completed.")
        
        df_customer = standardize_customer_id(df_customer)
        logging.info("Customer ID standardization completed.")
        
        df_customer = apply_value_replacements(df_customer, customer_replacemts)
        logging.info("Value replacements applied.")
        
        df_customer = drop_technical_columns(df_customer)
        logging.info("Technical columns dropped.")
        
        #! Save to silver layer (not implemented here)
        df_customer.to_sql(
            schema="silver_db",
            name = "erp_cust_az12",
            con  = get_engine("silver"),
            if_exists = "replace",
            index=False,
            dtype={
                "cid" : String(100),
                "birth_date_raw": DateTime(),
                "gender_raw": String(100)
            },
            chunksize=1000
        )
        logging.info("ERP Customers Silver Pipeline completed successfully.")
    except Exception as e:
        logging.error(f"Pipeline failed: {e}", exc_info=True)
def run_location_pipeline():
    logging.info("Starting ERP Customer Locations Silver Pipeline")
    try:
        df_location = extract_from_bronze("erp_location_a101")
        logging.info(f"Extracted {len(df_location)} records from bronze for location data.")
        
        df_location = enforce_schema(df_location, schema_location)
        logging.info("Schema enforcement completed for location data.")
        
        df_location = apply_value_replacements(df_location, location_replacements)
        logging.info("Value replacements applied for location data.")
        
        df_location = drop_technical_columns(df_location)
        logging.info("Technical columns dropped for location data.")

        #! Save to silver layer (not implemented here)
        # save_to_silver(df_location, "erp_customer_locations")
        df_location.to_sql(
        schema="silver_db",
        name="erp_location_a101",
        con=get_engine("silver"),
        if_exists="replace",
        index=False,
        dtype={
            "cid": String(100),
            "country_name": String(100)
        },
    chunksize=1000
)
        logging.info("ERP Customer Locations Silver Pipeline completed successfully.")
    except Exception as e:
        logging.error(f"Location pipeline failed: {e}", exc_info=True)

def run_category_pipeline():
    logging.info("Starting ERP Product Categories Silver Pipeline")
    try:
        df_category = extract_from_bronze("erp_px_cat_g1v2")
        logging.info(f"Extracted {len(df_category)} records from bronze.")
        
        df_category = drop_technical_columns(df_category)
        logging.info("Technical columns dropped for category data.")
    
        df_category.to_sql(
            schema ="silver_db",
            name   = "erp_px_cat_g1v2",
            con  = get_engine("silver"),
            if_exists = "replace",
            index=False,
            dtype={
                "id" : String(100),
                "cat": String(100),
                "subcat": String(100)
            },
            chunksize=1000
        )
        logging.info("ERP Product Categories Silver Pipeline completed successfully.")
    except Exception as e:  
        logging.error(f"Category pipeline failed: {e}", exc_info=True)

if __name__ == "__main__":
    run_customer_pipeline()
    run_location_pipeline()
    run_category_pipeline()
