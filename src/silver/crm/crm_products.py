import pandas as pd
from sqlalchemy import Date, DateTime, Numeric, String

from src.core.database import get_engine, load_to_silver
from src.core.logger import setup_logger

logger = setup_logger(__name__.split(".")[-1])


def extract_from_bronze(table_name: str) -> pd.DataFrame:
    """
    Extract data from bronze layer database table.

    Retrieves all records from the specified bronze table using the bronze database engine.

    Args:
        table_name (str): Name of the bronze table to extract data from.

    Returns:
        pd.DataFrame: DataFrame containing all records from the bronze table.

    Raises:
        RuntimeError: If extraction fails due to database connection or query issues.
    """
    engine = get_engine("bronze")
    try:
        return pd.read_sql(f"SELECT * FROM {table_name}", engine)
    except Exception as e:
        raise RuntimeError(f"Failed to extract from bronze table {table_name}") from e


schema_products = {
    "prd_id": "int",
    "prd_key": "string",
    "prd_name": "string",
    "prd_cost": "float64",
    "prd_line": "string",
    "prd_start_date_raw": "datetime64[ns]",
    "prd_end_date_raw": "datetime64[ns]",
}


def enforce_schema(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """
    Enforce schema by converting DataFrame columns to specified data types.

    Applies type conversions (numeric, datetime, boolean, string) based on the provided schema.
    Logs warnings for missing columns and handles conversion errors gracefully.

    Args:
        df (pd.DataFrame): Input DataFrame to enforce schema on.
        schema (dict): Dictionary mapping column names to target data types.

    Returns:
        pd.DataFrame: DataFrame with columns converted to specified data types.
    """
    for column, dtype in schema.items():
        if column not in df.columns:
            #! log warning and skip missing columns
            logger.warning(f"[SCHEMA WARNING] Column missing: {column}")
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
    """
    Normalize string columns by cleaning whitespace and standardizing null values.

    Strips leading/trailing whitespace from all string columns and replaces various
    null representations (empty strings, 'NULL', 'null', 'None', 'nan', etc.) with pd.NA.
    Also standardizes product names to title case and removes the raw_row column.

    Args:
        df (pd.DataFrame): Input DataFrame with string columns to normalize.

    Returns:
        pd.DataFrame: DataFrame with normalized string columns and standardized nulls.
    """
    str_cols = df.select_dtypes(include="string").columns
    for col in str_cols:
        logger.info(f"Normalizing nulls in column: {col}")
        df[col] = (
            df[col]
            .str.strip()
            .replace(["", "NULL", "null", "None", "none", "nan", "NaN"], pd.NA)
        )
    df.drop("raw_row", axis=1, inplace=True)
    df["prd_name"] = df["prd_name"].str.strip().str.title()
    return df


def standardize_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize product data by mapping codes to full values and filling missing data.

    Converts product line codes (R→Road, M→Mountain, T→Touring, S→Other sales) to full names,
    fills missing product costs with 0, and calculates product end dates using a window function
    based on the next product start date for each product key.

    Args:
        df (pd.DataFrame): Input DataFrame with raw product data.

    Returns:
        pd.DataFrame: DataFrame with standardized values and filled missing data.
    """
    if df.empty:
        return df
    #! Product Line Standardization
    product_line_mapping = {
        "R": "Road",
        "M": "Mountain",
        "T": "Touring",
        "S": "Other sales",
    }
    product_lines = df["prd_line"].str.strip()
    unknown = product_lines.notna() & ~product_lines.isin(product_line_mapping)
    if unknown.any():
        logger.warning(
            "[UNMAPPED VALUE] prd_line: %s", sorted(product_lines[unknown].unique())
        )
    df["prd_line"] = product_lines.replace(product_line_mapping)
    df["prd_line"] = df["prd_line"].fillna("n/a")
    df["prd_cost"] = df["prd_cost"].fillna(0)
    # df["prd_end_date_raw"] = df["prd_start_date_raw"].shift(-1) + pd.Timedelta(weeks=26)
    #! window function [LEAD]
    df = df.sort_values(by=["prd_key", "prd_start_date_raw"])
    df["prd_end_date_raw"] = df.groupby("prd_key")["prd_start_date_raw"].shift(
        -1
    ) - pd.Timedelta(days=1)
    return df


def transform_crm_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform product data by extracting and cleaning product keys.

    Extracts category ID from the first 5 characters of product key (replacing hyphens with underscores),
    then updates product key to contain only characters from position 6 onwards.

    Args:
        df (pd.DataFrame): Input DataFrame with product data.

    Returns:
        pd.DataFrame: DataFrame with extracted cat_id and modified prd_key columns.
    """
    df["cat_id"] = df["prd_key"].str[:5]
    df["cat_id"] = df["cat_id"].str.replace("-", "_", regex=False)
    df["prd_key"] = df["prd_key"].str[6:]
    return df


def data_quality_checks(df: pd.DataFrame) -> None:
    """
    Identify and log duplicate records based on primary key(s).

    Checks for duplicate product IDs in the DataFrame and logs warnings for each duplicate found
    along with the count of occurrences. Logs an info message if no duplicates are found.

    Args:
        df (pd.DataFrame): Input DataFrame to check for duplicates.
    """
    PRIMARY_KEY = ["prd_id"]
    dup_mask = df.duplicated(subset=PRIMARY_KEY, keep=False)
    dup_rows = df[dup_mask]
    if not dup_rows.empty:
        dup_summary = (
            dup_rows.groupby(PRIMARY_KEY).size().reset_index(name="occurrences")
        )
        for _, row in dup_summary.iterrows():
            logger.warning(
                f"[DUPLICATE FOUND] {PRIMARY_KEY[0]}={row['prd_id']} "
                f"→ occurrences={row['occurrences']}"
            )
    else:
        logger.info("No duplicates found")


def run_products_pipeline(table_name: str) -> None:
    """
    Execute the complete CRM products ETL pipeline.

    Orchestrates the full data transformation workflow: extraction from bronze layer,
    schema enforcement, data normalization, standardization, transformation, and quality checks.
    Loads the processed data into the silver layer with appropriate column renaming and timestamps.

    Args:
        table_name (str): Name of the source table in bronze layer to process.
    """
    df_products = extract_from_bronze(table_name)
    df_products = enforce_schema(df_products, schema_products)
    df_products = normalize_data(df_products)
    df_products = standardize_data(df_products)
    df_products = transform_crm_products(df_products)
    before = len(df_products)
    df_products = df_products.drop_duplicates(subset=["prd_id"], keep="last")
    if len(df_products) != before:
        logger.warning(
            "[DEDUP] Removed %s duplicate product rows", before - len(df_products)
        )
    data_quality_checks(df_products)

    df_products = df_products.rename(
        columns={"prd_start_date_raw": "prd_start_dt", "prd_end_date_raw": "prd_end_dt"}
    )
    df_products["loaded_at"] = pd.Timestamp.now()

    df_products.to_sql(
        name = "crm_prd_info",
        con  = get_engine("silver"),
        if_exists = "replace",
        index=False,
        dtype={
            "prd_id": String(50),
            "prd_key": String(100),
            "cat_id": String(100),
            "prd_name": String(255),
            "prd_line": String(100),
            "prd_cost": Numeric(12, 2),
            "prd_start_dt": Date(),
            "prd_end_dt": Date(),
            "loaded_at": DateTime(),
        },
        chunksize=1000,
    )


if __name__ == "__main__":
    run_products_pipeline("crm_prd_info")