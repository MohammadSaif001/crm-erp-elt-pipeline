import tracemalloc
# from __future__ import annotations
from src.core.logger import setup_logger
from src.core.schema_manager import execute_sql_file
from src.core.database import get_engine
from src.silver.silver_pipeline import run_silver_pipeline
from src.gold.gold_pipeline import run_gold_pipeline
from src.bronze.load_bronze import run_bronze_pipeline

logger = setup_logger("pipeline")
tracemalloc.start()

def run() -> None:
    logger.info("Pipeline start")
    snap1 = tracemalloc.take_snapshot()
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
    snap2 = tracemalloc.take_snapshot()
    top_stats = snap2.compare_to(snap1, 'lineno')
    logger.info("Pipeline complete")
    with open("memory_usage.log", "w") as f:
        for stat in top_stats[:10]:
            f.write(str(stat) + "\n")
    
if __name__ == "__main__":
    run()