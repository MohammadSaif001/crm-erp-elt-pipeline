import logging
import os
import re

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.exc import IntegrityError

from src.core.paths import get_config_path

ENV_FILE = get_config_path()

load_dotenv(ENV_FILE)

logger = logging.getLogger(__name__)


def load_config():
    def required(name: str):
        value = os.getenv(name)
        if value is None or not value.strip():
            raise ValueError(f"Required environment variable {name} is not set.")
        return value

    mysql_config = {
        "user": required("DB_USER"),
        "password": required("DB_PASSWORD"),
        "host": required("DB_HOST"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "bronze_db": os.getenv("BRONZE_DB", "bronze_db"),
        "silver_db": os.getenv("SILVER_DB", "silver_db"),
        "gold_db": os.getenv("GOLD_DB", "gold_db"),
    }
    return {"mysql": mysql_config}


def get_engine(layer: str = "bronze") -> Engine:
    """Create a missing layer database and return its SQLAlchemy engine."""
    cfg = load_config()["mysql"]

    db_map = {
        "bronze": cfg["bronze_db"],
        "silver": cfg["silver_db"],
        "gold": cfg["gold_db"],
    }

    if layer not in db_map:
        raise ValueError(f"Unknown layer: {layer}")

    dbname = db_map[layer]

    # Database names are SQL identifiers, not query parameters.
    # Restrict their format before using them in CREATE DATABASE.
    if not re.fullmatch(r"[A-Za-z0-9_]+", dbname):
        raise ValueError(f"Invalid database name: {dbname!r}")

    connect_args = {
        "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
    }

    # Connect to the MySQL server without selecting a database.
    server_url = URL.create(
        drivername="mysql+pymysql",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=cfg["port"],
    )

    server_engine = create_engine(
        server_url,
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    try:
        with server_engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    SELECT SCHEMA_NAME
                    FROM INFORMATION_SCHEMA.SCHEMATA
                    WHERE SCHEMA_NAME = :dbname
                    """
                ),
                {"dbname": dbname},
            )

            database_exists = result.scalar_one_or_none() is not None

            if not database_exists:
                conn.execute(text(f"CREATE DATABASE `{dbname}`"))
                logger.info("Created missing database: %s", dbname)
            else:
                logger.info("Database already exists: %s", dbname)
    finally:
        server_engine.dispose()

    # Connect to the requested layer database.
    database_url = URL.create(
        drivername="mysql+pymysql",
        username=cfg["user"],
        password=cfg["password"],
        host=cfg["host"],
        port=cfg["port"],
        database=dbname,
    )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
        connect_args=connect_args,
    )

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        logger.info("Connected to %s database: %s", layer, dbname)
        return engine
    except Exception:
        engine.dispose()
        logger.exception(
            "Failed to connect to %s database %s",
            layer,
            dbname,
        )
        raise

def load_to_silver(
    df: pd.DataFrame,
    table_name: str,
    engine,
    dtype: dict,
    chunksize: int = 1000,
) -> None:
    """Refresh a pre-created Silver table without replacing its DDL."""
    if not table_name.replace("_", "").isalnum():
        raise ValueError(f"Invalid table name: {table_name!r}")

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name}"))

    try:
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists="append",
            index=False,
            dtype=dtype,
            chunksize=chunksize,
        )
    except IntegrityError as e:
        logger.error(f"[SILVER LOAD] '{table_name}' violated a DB constraint: {e}")
        raise
