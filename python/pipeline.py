from __future__ import annotations

from bronze.load_bronze import run_bronze_pipeline
from utils.logger import setup_logger

logger = setup_logger("pipeline")


def run() -> None:
    logger.info("Pipeline start")
    run_bronze_pipeline()
    logger.info("Pipeline complete")


if __name__ == "__main__":
    run()