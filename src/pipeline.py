import argparse

from src.bronze.load_bronze import run_bronze_pipeline
from src.core.database import get_engine
from src.core.logger import setup_logger
from src.core.schema_manager import execute_sql_file
from src.gold.gold_pipeline import run_gold_pipeline
from src.silver.silver_pipeline import run_silver_pipeline

logger = setup_logger("pipeline")


# ================================
# Main Pipeline Execution
# ===============================
def run(args) -> None:
    logger.info("Pipeline start")

    engine = get_engine()

    #! Check if the engine is None before proceeding
    if engine is None:
        logger.error("Pipeline aborted due to database connection failure.")
        return

    #! Create tables for bronze layers
    execute_sql_file(engine, "sql/bronze/create_bronze_table.sql")
    #! Create tables for silver layers
    execute_sql_file(engine, "sql/silver/silver_layer_table.sql")
    #! Create tables for gold layers
    execute_sql_file(engine, "sql/bootstrap/ingestion_log.sql")
    if args.run_pipeline:  # For running the entire pipeline
        run_bronze_pipeline()
        run_silver_pipeline()
        run_gold_pipeline()
    elif args.run_bronze:  # For running only the bronze layer
        run_bronze_pipeline()
    elif args.run_silver:  # For running only the silver layer
        run_silver_pipeline()
    elif args.run_gold:  # For running only the gold layer
        run_gold_pipeline()

    logger.info("Pipeline complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the data pipeline.")
    run_group = parser.add_mutually_exclusive_group(required=True)
    run_group.add_argument(
        "--run-pipeline",
        action="store_true",
        help="Run the entire data pipeline (bronze, silver, gold).",
    )
    run_group.add_argument(
        "--run-bronze",
        action="store_true",
        help="Run only the bronze layer of the data pipeline.",
    )

    run_group.add_argument(
        "--run-silver",
        action="store_true",
        help="Run only the silver layer of the data pipeline.",
    )
    run_group.add_argument(
        "--run-gold",
        action="store_true",
        help="Run only the gold layer of the data pipeline.",
    )

    args = parser.parse_args()

    run(args)


if __name__ == "__main__":
    main()
