import os
import sys
import logging
current_dir = os.path.dirname(os.path.abspath(__file__))
python_folder = os.path.dirname(current_dir)

if python_folder not in sys.path:
    sys.path.append(python_folder)

from utils.logger import setup_logger
from silver.crm.crm_customers import run_customers_pipeline
from silver.crm.crm_products import run_products_pipeline
from silver.crm.crm_sales import run_sales_pipeline
from silver.erp.erp_customers import (
    run_customer_pipeline,
    run_location_pipeline,
    run_category_pipeline,
)

logger = setup_logger("silver_pipeline")


def run_silver_pipeline() -> None:
    logging.info("=" * 60)
    logging.info(f"[START] Starting Silver Layer Pipeline")

    pipelines = [
        ("CRM Customers",  lambda: run_customers_pipeline("crm_customers_info")),
        ("CRM Products",   lambda: run_products_pipeline("crm_prd_info")),
        ("CRM Sales",      lambda: run_sales_pipeline("crm_sales_details")),
        ("ERP Customers",  run_customer_pipeline),
        ("ERP Locations",  run_location_pipeline),
        ("ERP Categories", run_category_pipeline),
    ]

    succeeded, failed = 0, 0

    for name, pipeline_fn in pipelines:
        try:
            pipeline_fn()
            succeeded += 1
        except Exception as e:
            failed += 1
            logging.error(f"[ORCHESTRATOR] {name} pipeline failed: {e}")

    logging.info(
        f"Silver Layer Pipeline finished: "
        f"{succeeded} succeeded, {failed} failed out of {len(pipelines)}"
    )


if __name__ == "__main__":
    run_silver_pipeline()
