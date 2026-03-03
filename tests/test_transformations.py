"""
Transformation Unit Tests
--------------------------
Tests for silver-layer transformation functions (normalize, schema enforce,
standardize, dedup, validate, clean) using in-memory DataFrames — no DB needed.

Usage:
    cd d:\\data_engineering_project
    python -m pytest tests/test_transformations.py -v
"""
import sys
import os
import pytest
import pandas as pd
import numpy as np

# Path setup
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
python_dir = os.path.join(project_root, "python")
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)

# Import transformation functions from each silver module
from silver.crm.crm_customers import (
    normalize_data as cust_normalize,
    enforce_schema as cust_enforce_schema,
    standardize_data as cust_standardize,
    deduplicate_latest_by_date,
    remove_null_primary_keys,
    schema_customer,
)
from silver.crm.crm_products import (
    normalize_data as prod_normalize,
    enforce_schema as prod_enforce_schema,
    standardize_data as prod_standardize,
    transform_crm_products,
    schema_products,
)
from silver.crm.crm_sales import (
    normalize_data as sales_normalize,
    enforce_schema as sales_enforce_schema,
    datetime_conversion,
    validate_data,
    clean_sales_data,
    schema_sales,
)
from silver.erp.erp_customers import (
    standardize_customer_id,
    apply_value_replacements,
    transform_erp_cid_column,
    customer_replacemts,
    location_replacements,
)


# ==========================================================================
# Helpers: build small test DataFrames
# ==========================================================================
def _make_customer_df():
    """Minimal customer dataframe mimicking bronze output."""
    return pd.DataFrame({
        "raw_row": ['{"a":1}', '{"b":2}', '{"c":3}'],
        "cst_id": ["1", "2", "3"],
        "cst_key": ["AW00011000", "AW00011001", "AW00011002"],
        "cst_firstname": ["  john  ", "  JANE  ", "  bob  "],
        "cst_lastname": ["  doe  ", "  SMITH  ", "  jones  "],
        "cst_marital_status": ["m", "s", "m"],
        "cst_gndr": ["M", "F", "M"],
        "cst_create_date_raw": ["2024-01-01", "2024-02-15", "2024-03-20"],
    })


def _make_product_df():
    return pd.DataFrame({
        "raw_row": ['{"r":1}', '{"r":2}'],
        "prd_id": ["1", "2"],
        "prd_key": ["CO_PD-FR-R92B-56", "CO_PD-FR-R92B-57"],
        "prd_name": ["  mountain bike  ", "  road bike  "],
        "prd_cost": ["100.50", "200.00"],
        "prd_line": ["M", "R"],
        "prd_start_date_raw": ["2024-01-01", "2024-06-01"],
        "prd_end_date_raw": ["2024-12-31", "2025-01-01"],
    })


def _make_sales_df():
    return pd.DataFrame({
        "raw_row": ['{"s":1}', '{"s":2}', '{"s":3}'],
        "ingest_id": [1, 2, 3],
        "sales_ord_num": ["SO001", "SO002", "SO003"],
        "sales_prd_key": ["P1", "P2", "P3"],
        "sales_cust_id": ["C1", "C2", "C3"],
        "sales_sales": ["100.0", "200.0", "-50.0"],
        "sales_quantity": ["2", "3", "1"],
        "sales_price": ["50.0", "66.67", "-50.0"],
        "sales_order_date_raw": ["2024-01-01", "2024-02-01", "2024-03-01"],
        "sales_ship_date_raw": ["2024-01-10", "2024-02-10", "2024-03-10"],
        "sales_due_date_raw": ["2024-01-15", "2024-02-15", "2024-03-15"],
    })


# ==========================================================================
# 1) Customer transformations
# ==========================================================================
class TestCustomerEnforceSchema:
    def test_types_are_enforced(self):
        df = _make_customer_df()
        df = cust_enforce_schema(df, schema_customer)
        assert df["cst_id"].dtype == "string"
        assert pd.api.types.is_datetime64_any_dtype(df["cst_create_date_raw"])

    def test_missing_column_does_not_raise(self):
        df = pd.DataFrame({"cst_id": ["1"]})
        # Should warn but not crash
        result = cust_enforce_schema(df, schema_customer)
        assert "cst_id" in result.columns


class TestCustomerNormalize:
    def test_strips_whitespace(self):
        df = _make_customer_df()
        df = cust_enforce_schema(df, schema_customer)
        df = cust_normalize(df)
        assert df["cst_firstname"].iloc[0] == "John"
        assert df["cst_lastname"].iloc[1] == "Smith"

    def test_drops_raw_row(self):
        df = _make_customer_df()
        df = cust_enforce_schema(df, schema_customer)
        df = cust_normalize(df)
        assert "raw_row" not in df.columns

    def test_null_strings_become_na(self):
        df = pd.DataFrame({
            "raw_row": ['{}'],
            "cst_id": ["1"],
            "cst_key": ["NULL"],
            "cst_firstname": ["  "],
            "cst_lastname": ["none"],
            "cst_marital_status": [""],
            "cst_gndr": ["nan"],
            "cst_create_date_raw": ["2024-01-01"],
        })
        df = cust_enforce_schema(df, schema_customer)
        df = cust_normalize(df)
        assert pd.isna(df["cst_key"].iloc[0])
        assert pd.isna(df["cst_gndr"].iloc[0])


class TestCustomerStandardize:
    def test_gender_mapping(self):
        df = _make_customer_df()
        df = cust_enforce_schema(df, schema_customer)
        df = cust_normalize(df)
        df = cust_standardize(df)
        assert df["cst_gndr"].iloc[0] == "Male"
        assert df["cst_gndr"].iloc[1] == "Female"

    def test_marital_status_mapping(self):
        df = _make_customer_df()
        df = cust_enforce_schema(df, schema_customer)
        df = cust_normalize(df)
        df = cust_standardize(df)
        assert df["cst_marital_status"].iloc[0] == "Married"
        assert df["cst_marital_status"].iloc[1] == "Single"

    def test_empty_df_returns_empty(self):
        df = pd.DataFrame(columns=["cst_gndr", "cst_marital_status"])
        result = cust_standardize(df)
        assert result.empty


class TestDeduplicateLatestByDate:
    def test_keeps_latest_record(self):
        df = pd.DataFrame({
            "cst_id": ["1", "1", "2"],
            "cst_create_date_raw": pd.to_datetime(
                ["2024-01-01", "2024-06-01", "2024-03-01"]
            ),
            "name": ["old", "new", "only"],
        })
        kept, deleted = deduplicate_latest_by_date(df, "cst_id", "cst_create_date_raw")
        assert len(kept) == 2
        assert len(deleted) == 1
        # The kept row for cst_id=1 should be the one with 2024-06-01
        row_1 = kept[kept["cst_id"] == "1"].iloc[0]
        assert row_1["name"] == "new"

    def test_no_duplicates_unchanged(self):
        df = pd.DataFrame({
            "cst_id": ["1", "2"],
            "cst_create_date_raw": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        })
        kept, deleted = deduplicate_latest_by_date(df, "cst_id", "cst_create_date_raw")
        assert len(kept) == 2
        assert len(deleted) == 0

    def test_empty_df(self):
        df = pd.DataFrame(columns=["cst_id", "cst_create_date_raw"])
        kept, deleted = deduplicate_latest_by_date(df, "cst_id", "cst_create_date_raw")
        assert kept.empty
        assert deleted.empty


class TestRemoveNullPrimaryKeys:
    def test_removes_null_ids(self):
        df = pd.DataFrame({"cst_id": ["1", None, "3", pd.NA]})
        result = remove_null_primary_keys(df, "cst_id")
        assert len(result) == 2

    def test_all_valid(self):
        df = pd.DataFrame({"cst_id": ["1", "2", "3"]})
        result = remove_null_primary_keys(df, "cst_id")
        assert len(result) == 3


# ==========================================================================
# 2) Product transformations
# ==========================================================================
class TestProductNormalize:
    def test_strips_product_names(self):
        df = _make_product_df()
        df = prod_enforce_schema(df, schema_products)
        df = prod_normalize(df)
        assert df["prd_name"].iloc[0] == "Mountain Bike"
        assert df["prd_name"].iloc[1] == "Road Bike"


class TestProductStandardize:
    def test_product_line_mapping(self):
        df = _make_product_df()
        df = prod_enforce_schema(df, schema_products)
        df = prod_normalize(df)
        df = prod_standardize(df)
        assert df["prd_line"].iloc[0] == "Mountain"
        assert df["prd_line"].iloc[1] == "Road"

    def test_null_cost_filled_with_zero(self):
        df = pd.DataFrame({
            "raw_row": ['{}'],
            "prd_id": ["1"],
            "prd_key": ["K1"],
            "prd_name": ["Test"],
            "prd_cost": [None],
            "prd_line": ["M"],
            "prd_start_date_raw": ["2024-01-01"],
            "prd_end_date_raw": [None],
        })
        df = prod_enforce_schema(df, schema_products)
        df = prod_normalize(df)
        df = prod_standardize(df)
        assert df["prd_cost"].iloc[0] == 0


class TestTransformCrmProducts:
    def test_cat_id_extraction(self):
        df = pd.DataFrame({
            "prd_key": ["CO-PD-FR-R92B-56", "HE-AD-FR-R92B-57"],
        })
        df = transform_crm_products(df)
        assert df["cat_id"].iloc[0] == "CO_PD"
        assert df["cat_id"].iloc[1] == "HE_AD"

    def test_prd_key_trimmed(self):
        df = pd.DataFrame({
            "prd_key": ["CO-PD-FR-R92B-56"],
        })
        df = transform_crm_products(df)
        # prd_key should be everything after the first 6 chars
        assert df["prd_key"].iloc[0] == "FR-R92B-56"


# ==========================================================================
# 3) Sales transformations
# ==========================================================================
class TestSalesEnforceSchema:
    def test_types_are_enforced(self):
        df = _make_sales_df()
        df = sales_enforce_schema(df, schema_sales)
        assert df["sales_ord_num"].dtype == "string"
        assert pd.api.types.is_float_dtype(df["sales_sales"])
        assert df["sales_quantity"].dtype == "Int64"


class TestSalesNormalize:
    def test_drops_raw_row(self):
        df = _make_sales_df()
        df = sales_enforce_schema(df, schema_sales)
        df = sales_normalize(df)
        assert "raw_row" not in df.columns


class TestDatetimeConversion:
    def test_converts_date_columns(self):
        df = pd.DataFrame({
            "sales_order_date_raw": ["2024-01-01", "invalid_date"],
            "sales_ship_date_raw": ["2024-01-10", "2024-02-10"],
            "sales_due_date_raw": ["2024-01-15", "2024-02-15"],
        })
        result = datetime_conversion(df)
        assert pd.api.types.is_datetime64_any_dtype(result["sales_order_date_raw"])
        # Invalid date becomes NaT
        assert pd.isna(result["sales_order_date_raw"].iloc[1])


class TestValidateData:
    def test_separates_valid_and_invalid(self):
        df = pd.DataFrame({
            "sales_price": [50.0, -10.0, 30.0],
            "sales_quantity": [2, 3, None],
            "sales_sales": [100.0, -30.0, 90.0],
            "sales_order_date_raw": pd.to_datetime(
                ["2024-01-01", "2024-02-01", "2024-03-01"]
            ),
            "sales_ship_date_raw": pd.to_datetime(
                ["2024-01-10", "2024-02-10", "2024-03-10"]
            ),
        })
        valid, invalid = validate_data(df)
        assert len(valid) == 1  # only first row is fully valid
        assert len(invalid) == 2


class TestCleanSalesData:
    def test_negatives_become_absolute(self):
        df = pd.DataFrame({
            "sales_price": [-50.0],
            "sales_sales": [-100.0],
            "sales_quantity": [-2],
        })
        result = clean_sales_data(df)
        assert result["sales_price"].iloc[0] == 50.0
        assert result["sales_quantity"].iloc[0] == 2

    def test_recalculates_sales(self):
        df = pd.DataFrame({
            "sales_price": [25.0],
            "sales_sales": [999.0],  # wrong — should be recalculated
            "sales_quantity": [4],
        })
        result = clean_sales_data(df)
        assert result["sales_sales"].iloc[0] == 100.0  # 25 * 4


# ==========================================================================
# 4) ERP transformations
# ==========================================================================
class TestStandardizeCustomerId:
    def test_trims_to_last_10_chars(self):
        df = pd.DataFrame({"cid": ["NAS-AW00011000", "NAS-AW00011001"]})
        result = standardize_customer_id(df)
        assert result["cid"].iloc[0] == "AW00011000"
        assert result["cid"].iloc[1] == "AW00011001"

    def test_drops_short_cids(self):
        df = pd.DataFrame({"cid": ["SHORT", "NAS-AW00011000"]})
        result = standardize_customer_id(df)
        assert len(result) == 1

    def test_missing_cid_column(self):
        df = pd.DataFrame({"other": [1, 2]})
        result = standardize_customer_id(df)
        assert "other" in result.columns  # df returned unchanged


class TestApplyValueReplacements:
    def test_gender_replacement(self):
        df = pd.DataFrame({"gender_raw": ["M", "F", ""]})
        result = apply_value_replacements(df, customer_replacemts)
        assert result["gender_raw"].iloc[0] == "Male"
        assert result["gender_raw"].iloc[1] == "Female"

    def test_country_replacement(self):
        df = pd.DataFrame({"country_name": ["USA", "US", "DE"]})
        result = apply_value_replacements(df, location_replacements)
        assert result["country_name"].iloc[0] == "United States"
        assert result["country_name"].iloc[1] == "United States"
        assert result["country_name"].iloc[2] == "Germany"


class TestTransformErpCid:
    def test_removes_dashes(self):
        df = pd.DataFrame({"cid": ["NAS-AW00011000"]})
        result = transform_erp_cid_column(df)
        assert "-" not in result["cid"].iloc[0]

    def test_empty_df(self):
        df = pd.DataFrame(columns=["cid"])
        result = transform_erp_cid_column(df)
        assert result.empty
