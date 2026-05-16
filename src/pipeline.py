from __future__ import annotations
from src.bronze.load_bronze import run_bronze_pipeline
from src.silver.silver_pipeline import run_silver_pipeline
from src.gold.gold_pipeline import run_gold_pipeline
from src.core.logger import setup_logger

logger = setup_logger("pipeline")


def run() -> None:
    logger.info("Pipeline start")
    run_bronze_pipeline()
    run_silver_pipeline()
    run_gold_pipeline()
    logger.info("Pipeline complete")


if __name__ == "__main__":
    run()