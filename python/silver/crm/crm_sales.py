import os
import sys
import logging
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

#! Define expected schema for sales data
schema ={
    "sales_ord_num"       : "string",
    "sales_prd_key"       : "string",
    "sales_cust_id"       : "string",
    "sales_sales"         : "float64",
    "sales_quantity"      : "Int64",
    "sales_price"         : "float64",
    "sales_order_date_raw": "datetime64[ns]",
    "sales_ship_date_raw" : "datetime64[ns]",
    "sales_due_date_raw"  : "datetime64[ns]",
    "loaded_at"           : "datetime64[ns]"
    }

#!Schema enforcement function to ensure data types are correct and handle errors gracefully.
def enforce_schema(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """
    Applies datatype schema to a pandas DataFrame.

    Args:
        df (pd.DataFrame): Input dataframe containing raw data.
        schema (dict): Dictionary mapping column names to target datatypes.

    Returns:
        pd.DataFrame: DataFrame with updated datatypes.
    """
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

#! data normalization function to handle nulls and whitespace in string columns
def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and standardizes raw input data.

    This function performs basic normalization such as:
    - Stripping leading/trailing whitespace from string columns
    - Converting empty strings to NaN
    - Standardizing text case (lowercase)

    Args:
        df (pd.DataFrame): Raw input dataframe.

    Returns:
        pd.DataFrame: Cleaned and normalized dataframe.
    """
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
    return df



#! datetime conversion function to convert date columns and log any conversion issues
def datetime_conversion(df:pd.DataFrame) -> pd.DataFrame:
    """
    Converts raw date columns to proper datetime format and logs conversion issues.
    """
    date_cols = [col for col in df.columns if col.endswith("_date_raw")]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], format = "%Y-%m-%d", errors="coerce")
        null_count = df[col].isna().sum()
        logging.info(f"Converted {col} to datetime. Null values after conversion: {null_count}")
        logging.info(f"{col} -> {null_count} invalid dates converted to NaT")
    return df

#! data validation function
def validate_data(df: pd.DataFrame):
    """ Validates data against business rules and logs any issues found. 
        Example rules: 
        - valid_df: Records that passed validation 
        - invalid_df: Records thar failed validation and were logged for review """
    invalid_mask = (
        (df["sales_price"] < 0) |
        (df["sales_quantity"] < 0) |
        (df["sales_sales"] < 0) |
        (df["sales_order_date_raw"] > df["sales_ship_date_raw"]) |
        (df["sales_quantity"].isna()) |
        (df["sales_price"].isna())
    )

    invalid_df = df.loc[invalid_mask].copy()
    valid_df = df.loc[~invalid_mask].copy()

    if not invalid_df.empty:
        logging.warning(f"{len(invalid_df)} invalid records detected.")

    return valid_df, invalid_df

#!treating some colums [e.g sales_sales, sales_quality,sales_price]
def clean_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and standardizes sales-related numeric fields.

    - Converts columns to numeric
    - Removes negative values using absolute conversion
    - Recalculates sales as quantity * price
    Args:
        df (pd.DataFrame): Raw sales dataframe.
    Returns:
        pd.DataFrame: Cleaned sales dataframe.
    """
    cols = ["sales_price", "sales_sales", "sales_quantity"]
    df[cols] = df[cols].apply(pd.to_numeric, errors="coerce")
    # Remove negatives
    df[cols] = df[cols].abs()
    # Recalculate sales
    df["sales_sales"] = df["sales_price"] * df["sales_quantity"]

    return df

    
def main():
    df = extract_from_bronze("crm_sales_details")

    df = enforce_schema(df, schema)
    df = normalize_data(df)
    df = datetime_conversion(df)

    valid_df, invalid_df = validate_data(df)

    logging.info(f"Valid records: {len(valid_df)}")
    logging.info(f"Invalid records: {len(invalid_df)}")

    valid_df = clean_sales_data(valid_df)

    print(valid_df.head())
if __name__ == "__main__":
    main()