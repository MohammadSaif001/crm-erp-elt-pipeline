from __future__ import annotations
import logging
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from config import DB_SETTINGS

logger = logging.getLogger("dashboard.database")


@st.cache_resource(show_spinner=False)
def get_engine(database: str = DB_SETTINGS.gold_db) -> Engine:
    """
    Return a cached SQLAlchemy engine for the given database.

    Cached via `st.cache_resource` so the connection pool is created once
    per Streamlit session/process rather than on every script rerun.

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


def run_query(sql: str, database: str = DB_SETTINGS.gold_db, params: dict | None = None) -> pd.DataFrame:
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
            return pd.read_sql(text(sql), conn, params=params or {})
    except SQLAlchemyError as exc:
        logger.error("Query failed against %s: %s | SQL=%s", database, exc, sql)
        st.session_state.setdefault("db_errors", []).append(str(exc))
        return pd.DataFrame()
    except Exception as exc:  # noqa: BLE001 — surface any unexpected failure safely
        logger.exception("Unexpected error running query against %s", database)
        st.session_state.setdefault("db_errors", []).append(str(exc))
        return pd.DataFrame()
