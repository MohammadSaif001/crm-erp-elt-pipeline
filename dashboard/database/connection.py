"""
database/connection.py
==============================================================================
SQLAlchemy engine factory for the dashboard.

Mirrors the pattern used by the pipeline's own `src/core/database.py`
(engine-per-database), but adds Streamlit-aware caching so the dashboard
does not open a fresh connection pool on every rerun, plus defensive error
handling so a database outage degrades gracefully in the UI instead of
crashing the app.
"""

from __future__ import annotations

import logging
from functools import cache

import pandas as pd
from config import DB_SETTINGS
from sqlalchemy import bindparam, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from utils.cache import register_cache_clearer

logger = logging.getLogger("dashboard.database")


@cache
def get_engine(database: str = DB_SETTINGS.gold_db) -> Engine:
    """
    Return a cached SQLAlchemy engine for the given database.

    Cached per process so the connection pool is reused across requests.

    Args:
        database: Logical database name (defaults to the Gold layer DB).

    Returns:
        A configured SQLAlchemy Engine.
    """
    uri = DB_SETTINGS.sqlalchemy_uri(database)
    logger.info("Creating SQLAlchemy engine for database=%s", database)
    return create_engine(
        uri,
        pool_size=DB_SETTINGS.pool_size,
        pool_recycle=DB_SETTINGS.pool_recycle,
        pool_pre_ping=True,
    )


register_cache_clearer(get_engine.cache_clear)


def test_connection(database: str = DB_SETTINGS.gold_db) -> tuple[bool, str]:
    """
    Verify connectivity to a database.

    Args:
        database: Logical database name to test.

    Returns:
        Tuple of (is_connected, message).
    """
    try:
        engine = get_engine(database)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, f"Connected to `{database}`"
    
    except OperationalError as exc:
        logger.error("Database connection failed for %s: %s", database, exc)
        return False, f"Connection failed: {exc.orig if hasattr(exc, 'orig') else exc}"
    except SQLAlchemyError as exc:
        logger.error("SQLAlchemy error for %s: %s", database, exc)
        return False, f"Database error: {exc}"


def run_query(
    sql: str, database: str = DB_SETTINGS.gold_db, params: dict | None = None
) -> pd.DataFrame:
    """
    Execute a read-only SQL query and return the result as a DataFrame.

    Args:
        sql: SQL SELECT statement.
        database: Logical database to query against.
        params: Optional bind parameters for the query.

    Returns:
        Query result as a pandas DataFrame. Returns an empty DataFrame
        (rather than raising) if the query fails, so dashboard pages can
        render a friendly "no data" state instead of crashing.
    """
    try:
        engine = get_engine(database)
        with engine.connect() as conn:
            statement = text(sql)
            query_params = params or {}
            expanding_params = [
                bindparam(name, expanding=True)
                for name, value in query_params.items()
                if isinstance(value, (list, tuple, set))
            ]
            if expanding_params:
                statement = statement.bindparams(*expanding_params)
            return pd.read_sql(statement, conn, params=query_params)
    except SQLAlchemyError as exc:
        logger.error("Query failed against %s: %s | SQL=%s", database, exc, sql)
        return pd.DataFrame()
    except Exception:
        logger.exception("Unexpected error running query against %s", database)
        return pd.DataFrame()
