import pandas as pd
from sqlalchemy import Date, DateTime, String

from src.core.database import get_engine, load_to_silver
from src.core.logger import setup_logger

logger = setup_logger("crm_customers")


def extract_from_bronze(table_name: str) -> pd.DataFrame:
    engine = get_engine("bronze")
    try:
        return pd.read_sql(f"SELECT * FROM {table_name}", engine)
    except Exception as e:
        raise RuntimeError(f"Failed to extract from bronze table {table_name}") from e


#! Define schema for data types
schema_customer = {
    "cst_id": "string",
    "cst_key": "string",
    "cst_firstname": "string",
    "cst_lastname": "string",
    "cst_marital_status": "string",
    "cst_gndr": "string",
    "cst_create_date_raw": "datetime64[ns]",
}


#! combined normalization function for all string columns in the dataframe
def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    # Normalize string columns
    - columns by stripping whitespace and standardizing null representations,
    with logging for each column processed.

    Args:
        df (pd.DataFrame): _description_

    Returns:
        pd.DataFrame: _description_
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
    df[["cst_firstname", "cst_lastname"]] = df[["cst_firstname", "cst_lastname"]].apply(
        lambda x: x.str.strip().str.title()
    )
    return df


#! high level schema enforcement function
def enforce_schema(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """# Enforce schema
        - Enforce data types based on provided schema, with error handling
         and logging for any issues encountered during conversion.

    Args:
        df (pd.DataFrame)
        schema (dict)

    Returns:
        pd.DataFrame
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


def data_quality_checks(df: pd.DataFrame) -> None:
    """
    # Data Quality Check:
    - Identify and log duplicate records based on primary key(s).

    Args:
        df (pd.DataFrame): _description_
    """
    PRIMARY_KEY = ["cst_id"]
    dup_mask = df.duplicated(subset=PRIMARY_KEY, keep=False)
    dup_rows = df[dup_mask]
    if not dup_rows.empty:
        dup_summary = (
            dup_rows.groupby(PRIMARY_KEY).size().reset_index(name="occurrences")
        )
        for _, row in dup_summary.iterrows():
            logger.info(
                f"[DUPLICATE FOUND] {PRIMARY_KEY[0]}={row['cst_id']} "
                f"→ occurrences={row['occurrences']}"
            )
    else:
        logger.info("No duplicates found")


# * Standardization function for gender and marital status columns, with logging for any unmapped values
def standardize_data(df: pd.DataFrame) -> pd.DataFrame:

    if df.empty:
        return df
    #! Gender Standardization
    gender_mapping = {
        "m": "Male",
        "f": "Female",
    }
    marital_mapping = {
        "s": "Single",
        "m": "Married",
    }
    for column, mapping in (
        ("cst_gndr", gender_mapping),
        ("cst_marital_status", marital_mapping),
    ):
        normalized = df[column].str.strip()
        normalized_keys = normalized.str.lower()
        unknown = normalized.notna() & ~normalized_keys.isin(mapping)
        if unknown.any():
            logger.warning(
                "[UNMAPPED VALUE] %s: %s", column, sorted(normalized[unknown].unique())
            )
        df[column] = normalized.replace(
            {
                **mapping,
                **{key.upper(): value for key, value in mapping.items()},
            }
        )

    df[["cst_gndr", "cst_marital_status"]] = df[
        ["cst_gndr", "cst_marital_status"]
    ].fillna("n/a")

    return df


#! clean function for deleting duplicate records
def deduplicate_latest_by_date(
    df: pd.DataFrame, primary_key: str, date_col: str
) -> tuple[pd.DataFrame, pd.DataFrame]:

    if df.empty:
        logger.info("[DEDUP] Empty DataFrame.")
        return df, pd.DataFrame()

    df = df.copy()

    sort_cols = [primary_key, date_col]
    ascending_order = [True, False]

    # Sort so latest records come first per primary key
    df_sorted = df.sort_values(by=sort_cols, ascending=ascending_order)

    # Keep latest per primary key
    kept_rows = df_sorted.drop_duplicates(subset=primary_key, keep="first")

    #! Identify deleted rows based on index difference
    deleted_rows = df_sorted[~df_sorted.index.isin(kept_rows.index)]

    #! logging into log file for debugging and monitoring how many duplicates were found and removed
    logger.info(f"[DEDUP] Total rows   : {len(df)}")
    logger.info(f"[DEDUP] Kept rows    : {len(kept_rows)}")
    logger.info(f"[DEDUP] Deleted rows : {len(deleted_rows)}")
    return kept_rows, deleted_rows


#! delete null values in the dataframe and log how many rows were deleted form PRIMARY_KEY column
def remove_null_primary_keys(df: pd.DataFrame, primary_key: str) -> pd.DataFrame:
    initial_count = len(df)

    df_clean = df.dropna(subset=[primary_key])

    removed_count = initial_count - len(df_clean)

    if removed_count > 0:
        logger.warning(
            f"[NULL PRIMARY KEY REMOVED] {removed_count} rows removed where {primary_key} is NULL"
        )

    return df_clean


def run_customers_pipeline(table_name: str) -> None:
    df_customers = extract_from_bronze(table_name)
    df_customers = enforce_schema(
        df_customers, schema_customer
    )  # object → string, datetime → datetime64, etc.
    df_customers = normalize_data(df_customers)
    df_customers = df_customers.drop(columns=["ingest_id"], errors="ignore")
    df_customers = standardize_data(
        df_customers
    )  # standardize gender and marital status values
    df_customers = remove_null_primary_keys(df_customers, primary_key="cst_id")

    data_quality_checks(
        df_customers
    )  # log any duplicates found into log file (but do not remove yet)
    df_customers, df_duplicates = deduplicate_latest_by_date(
        df_customers, primary_key="cst_id", date_col="cst_create_date_raw"
    )  # remove duplicates based on cst_id, keep latest loaded_at record

    df_customers = df_customers.rename(
        columns={"cst_gndr": "cst_gender", "cst_create_date_raw": "cst_create_date"}
    )
    df_customers["loaded_at"] = pd.Timestamp.now()

    load_to_silver(
        df_customers,
        "crm_customers_info",
        get_engine("silver"),
        dtype={
            "cst_id": String(50),
            "cst_key": String(100),
            "cst_firstname": String(200),
            "cst_lastname": String(200),
            "cst_marital_status": String(50),
            "cst_gender": String(50),
            "cst_create_date": Date(),
            "loaded_at": DateTime(),
        },
        chunksize=1000,
    )


if __name__ == "__main__":
    run_customers_pipeline("crm_customers_info")