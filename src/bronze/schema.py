"""Small idempotent migrations for existing Bronze databases."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


BRONZE_TABLES = (
    "crm_customers_info",
    "crm_prd_info",
    "crm_sales_details",
    "erp_cust_az12",
    "erp_location_a101",
    "erp_px_cat_g1v2",
)


def ensure_bronze_schema(engine: Engine) -> None:
    """Add batch metadata and preserve numeric source columns as strings."""
    existing_tables = set(inspect(engine).get_table_names())

    with engine.begin() as connection:
        inspector = inspect(connection)
        for table in BRONZE_TABLES:
            if table not in existing_tables:
                continue
            options = inspector.get_table_options(table)
            if str(options.get("mysql_engine", "")).upper() != "INNODB":
                connection.execute(text(f"ALTER TABLE `{table}` ENGINE=InnoDB"))
            column_specs = {
                column["name"]: column for column in inspector.get_columns(table)
            }
            columns = set(column_specs)
            if "batch_id" not in columns:
                connection.execute(
                    text(f"ALTER TABLE `{table}` ADD COLUMN batch_id CHAR(36) NULL")
                )

        if "crm_prd_info" in existing_tables:
            product_columns = {
                column["name"]: column
                for column in inspector.get_columns("crm_prd_info")
            }
            if not str(product_columns["prd_cost"]["type"]).upper().startswith(
                "VARCHAR"
            ):
                connection.execute(
                    text(
                        "ALTER TABLE `crm_prd_info` "
                        "MODIFY `prd_cost` VARCHAR(100) NULL"
                    )
                )
        if "crm_sales_details" in existing_tables:
            sales_columns = {
                spec["name"]: spec
                for spec in inspector.get_columns("crm_sales_details")
            }
            for column in ("sales_sales", "sales_quantity", "sales_price"):
                if str(sales_columns[column]["type"]).upper().startswith("VARCHAR"):
                    continue
                connection.execute(
                    text(
                        f"ALTER TABLE `crm_sales_details` "
                        f"MODIFY `{column}` VARCHAR(100) NULL"
                    )
                )

        if "ingestion_log" in existing_tables:
            options = inspector.get_table_options("ingestion_log")
            if str(options.get("mysql_engine", "")).upper() != "INNODB":
                connection.execute(
                    text("ALTER TABLE `ingestion_log` ENGINE=InnoDB")
                )
            log_columns = {
                column["name"]
                for column in inspector.get_columns("ingestion_log")
            }
            if "batch_id" not in log_columns:
                connection.execute(
                    text(
                        "ALTER TABLE `ingestion_log` "
                        "ADD COLUMN batch_id CHAR(36) NULL"
                    )
                )
            indexes = {
                index["name"] for index in inspector.get_indexes("ingestion_log")
            }
            index_name = "uq_ingestion_source_file_hash"
            if index_name not in indexes:
                # Keep the first historical record for duplicate keys before
                # enforcing idempotency for future batches.
                connection.execute(
                    text(
                        """
                        DELETE older FROM ingestion_log AS older
                        JOIN ingestion_log AS newer
                          ON older.source_name = newer.source_name
                         AND older.file_name = newer.file_name
                         AND older.file_hash = newer.file_hash
                         AND older.id > newer.id
                        """
                    )
                )
                connection.execute(
                    text(
                        "ALTER TABLE `ingestion_log` "
                        "ADD UNIQUE KEY `uq_ingestion_source_file_hash` "
                        "(`source_name`, `file_name`, `file_hash`)"
                    )
                )
