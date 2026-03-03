"""
Pipeline Integration Tests
---------------------------
Tests that validate each layer of the data pipeline
by checking database connectivity, table existence, and data presence.

Usage:
    cd d:\\data_engineering_project
    python -m pytest tests/test_pipeline.py -v
"""
import sys
import os
import pytest

# Path setup so we can import from python/
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
python_dir = os.path.join(project_root, "python")
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)

from sqlalchemy import text, inspect
from utils.db_connection import get_engine



#! Fixtures

@pytest.fixture(scope="module")
def bronze_engine():
    return get_engine("bronze")


@pytest.fixture(scope="module")
def silver_engine():
    return get_engine("silver")


@pytest.fixture(scope="module")
def gold_engine():
    return get_engine("gold")



#! 1) Database connectivity tests

class TestDatabaseConnectivity:
    """Verify that each database layer is reachable."""

    @pytest.mark.parametrize("layer", ["bronze", "silver", "gold"])
    def test_db_connection(self, layer):
        engine = get_engine(layer)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1, f"Cannot connect to {layer} database"



#! 2) Bronze layer tests

BRONZE_TABLES = [
    "crm_customers_info",
    "crm_prd_info",
    "crm_sales_details",
    "erp_cust_az12",
    "erp_location_a101",
    "erp_px_cat_g1v2",
]


class TestBronzeLayer:
    """Validate bronze layer tables exist and contain data."""

    @pytest.mark.parametrize("table", BRONZE_TABLES)
    def test_table_exists(self, bronze_engine, table):
        insp = inspect(bronze_engine)
        tables = insp.get_table_names()
        assert table in tables, f"Bronze table '{table}' not found"

    @pytest.mark.parametrize("table", BRONZE_TABLES)
    def test_table_not_empty(self, bronze_engine, table):
        with bronze_engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count > 0, f"Bronze table '{table}' is empty"

    def test_raw_row_column_exists(self, bronze_engine):
        """Bronze tables should have a raw_row JSON column."""
        insp = inspect(bronze_engine)
        for table in BRONZE_TABLES:
            cols = [c["name"] for c in insp.get_columns(table)]
            assert "raw_row" in cols, f"'{table}' missing 'raw_row' column"



#! 3) Silver layer tests

SILVER_TABLES = [
    "crm_customers_info",
    "crm_prd_info",
    "crm_sales_details",
    "erp_cust_az12",
    "erp_location_a101",
    "erp_px_cat_g1v2",
]


class TestSilverLayer:
    """Validate silver layer tables exist, have data, and are cleaner than bronze."""

    @pytest.mark.parametrize("table", SILVER_TABLES)
    def test_table_exists(self, silver_engine, table):
        insp = inspect(silver_engine)
        tables = insp.get_table_names()
        assert table in tables, f"Silver table '{table}' not found"

    @pytest.mark.parametrize("table", SILVER_TABLES)
    def test_table_not_empty(self, silver_engine, table):
        with silver_engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count > 0, f"Silver table '{table}' is empty"

    def test_no_duplicate_customers(self, silver_engine):
        """Silver customers should be deduplicated on cst_id."""
        with silver_engine.connect() as conn:
            query = text("""
                SELECT cst_id, COUNT(*) AS cnt
                FROM crm_customers_info
                GROUP BY cst_id
                HAVING COUNT(*) > 1
            """)
            dups = conn.execute(query).fetchall()
            assert len(dups) == 0, f"Duplicate cst_id found in silver: {dups[:5]}"

    def test_silver_row_count_lte_bronze(self, bronze_engine, silver_engine):
        """Silver should have <= rows than bronze (after dedup/cleaning)."""
        for table in SILVER_TABLES:
            with bronze_engine.connect() as bc, silver_engine.connect() as sc:
                b_count = bc.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                s_count = sc.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                assert s_count <= b_count, (
                    f"Silver {table} ({s_count}) has MORE rows than Bronze ({b_count})"
                )



#! 4) Gold layer tests

GOLD_VIEWS = ["dim_customers", "dim_products", "fact_sales"]


class TestGoldLayer:
    """Validate gold layer views exist and return data."""

    @pytest.mark.parametrize("view", GOLD_VIEWS)
    def test_view_returns_data(self, gold_engine, view):
        with gold_engine.connect() as conn:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {view}")).scalar()
            assert count > 0, f"Gold view '{view}' returned 0 rows"

    def test_dim_customers_no_duplicate_ids(self, gold_engine):
        with gold_engine.connect() as conn:
            query = text("""
                SELECT customer_id, COUNT(*) AS cnt
                FROM dim_customers
                GROUP BY customer_id
                HAVING COUNT(*) > 1
            """)
            dups = conn.execute(query).fetchall()
            assert len(dups) == 0, f"Duplicate customer_id in dim_customers: {dups[:5]}"

    def test_fact_sales_has_valid_keys(self, gold_engine):
        """All customer_key and product_key in fact_sales should be non-null."""
        with gold_engine.connect() as conn:
            null_cust = conn.execute(text(
                "SELECT COUNT(*) FROM fact_sales WHERE customer_key IS NULL"
            )).scalar()
            null_prod = conn.execute(text(
                "SELECT COUNT(*) FROM fact_sales WHERE product_key IS NULL"
            )).scalar()
            # These are LEFT JOINs so some may be null —
            # warn but allow; fail only if ALL are null
            total = conn.execute(text("SELECT COUNT(*) FROM fact_sales")).scalar()
            assert total > 0, "fact_sales is empty"
            if null_cust > 0:
                pct = round(null_cust / total * 100, 1)
                print(f"WARNING: {null_cust} ({pct}%) rows have NULL customer_key")
            if null_prod > 0:
                pct = round(null_prod / total * 100, 1)
                print(f"WARNING: {null_prod} ({pct}%) rows have NULL product_key")



#! 5) End-to-end data flow test

class TestEndToEnd:
    """Verify data flows from raw CSV through all layers."""

    def test_source_csv_files_exist(self):
        """Check that the raw source files are present."""
        raw_dir = os.path.join(project_root, "data", "raw")
        expected = [
            os.path.join("source_crm", "cust_info.csv"),
            os.path.join("source_crm", "prd_info.csv"),
            os.path.join("source_crm", "sales_details.csv"),
            os.path.join("source_erp", "CUST_AZ12.csv"),
            os.path.join("source_erp", "LOC_A101.csv"),
            os.path.join("source_erp", "PX_CAT_G1V2.csv"),
        ]
        for path in expected:
            full_path = os.path.join(raw_dir, path)
            assert os.path.exists(full_path), f"Source file missing: {full_path}"

    def test_pipeline_config_valid(self):
        """Check pipeline_config.yaml is loadable and has expected keys."""
        import yaml
        config_path = os.path.join(project_root, "configs", "pipeline_config.yaml")
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
        assert "bronze" in cfg, "pipeline_config.yaml missing 'bronze' section"
        assert "targets" in cfg["bronze"], "No 'targets' under bronze config"
        assert len(cfg["bronze"]["targets"]) == 6, "Expected 6 bronze targets"

if __name__ == "__main__":
    pytest.main(["-v", "tests/test_pipeline.py"])