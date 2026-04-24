"""
Gold Layer Pipeline
-------------------
Reads SQL view definitions from sql/gold/create_dim_customers.sql
and executes them against the MySQL gold database.
"""
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
python_folder = os.path.dirname(current_dir)

if python_folder not in sys.path:
    sys.path.append(python_folder)

from sqlalchemy import text
from utils.db_connection import get_engine
from utils.paths import get_project_root
from utils.logger import setup_logger

logger = setup_logger("gold_pipeline")


def _read_sql_file(filename: str) -> str:
    """Return the contents of a SQL file under sql/gold/."""
    sql_path = os.path.join(get_project_root(), "sql", "gold", filename)
    if not os.path.exists(sql_path):
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    with open(sql_path, "r", encoding="utf-8") as f:
        return f.read()


def _split_statements(sql_text: str) -> list[str]:
    """Split a SQL script on semicolons into individual statements,
    stripping empty entries."""
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]
    return statements


def run_gold_pipeline() -> None:
    """Execute all gold-layer SQL views."""
    logger.info("=" * 60)
    logger.info("[START] Starting Gold Layer Pipeline")

    engine = get_engine("gold")
    sql_text = _read_sql_file("create_dim_customers.sql")
    statements = _split_statements(sql_text)

    succeeded, failed = 0, 0

    with engine.connect() as conn:
        for stmt in statements:
            # Identify what we're running for logging purposes
            short = stmt[:80].replace("\n", " ")
            try:
                logger.info(f"Executing: {short} ...")
                conn.execute(text(stmt))
                conn.commit()
                succeeded += 1
                logger.info("  -> OK")
            except Exception as e:
                failed += 1
                logger.error(f"  -> FAILED: {e}")

    logger.info(
        f"Gold Layer Pipeline finished: "
        f"{succeeded} succeeded, {failed} failed out of {len(statements)}"
    )

    if failed:
        raise RuntimeError(f"Gold pipeline had {failed} failures")


if __name__ == "__main__":
    run_gold_pipeline()
