from __future__ import annotations
from src.core.logger import setup_logger
from src.core.schema_manager import execute_sql_file
from src.core.database import get_engine
from src.silver.silver_pipeline import run_silver_pipeline
from src.gold.gold_pipeline import run_gold_pipeline
from src.bronze.load_bronze import run_bronze_pipeline

logger = setup_logger("pipeline")


def run() -> None:
    logger.info("Pipeline start")
    engine = get_engine()

    #! Check if the engine is None before proceeding
    if engine is None:
        logger.error("Pipeline aborted due to database connection failure.")
        return

    #! Create tables for bronze layers
    execute_sql_file(
        engine,
        "sql/bronze/create_bronze_table.sql"
    )
    #! Create tables for silver layers
    execute_sql_file(
        engine,
        "sql/silver/silver_layer_table.sql"
    )
    #! Create tables for gold layers
    execute_sql_file(
        engine,
        "sql/bootstrap/ingestion_log.sql"
    )
    run_bronze_pipeline()
    run_silver_pipeline()
    run_gold_pipeline()
    logger.info("Pipeline complete")


if __name__ == "__main__":
    run()