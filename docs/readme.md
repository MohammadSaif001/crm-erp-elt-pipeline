# ELT Data Engineering Pipeline

### Medallion Architecture (Bronze > Silver > Gold) | Python + MySQL

**Author:** Mohammad Saif | Data Engineer  
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://www.python.org/) [![MySQL](https://img.shields.io/badge/MySQL-8.0-orange)](https://www.mysql.com/)

---

## Overview

This project implements a production-style **ELT (Extract, Load, Transform) pipeline** that ingests raw CSV data from CRM and ERP source systems, loads it into a three-layer **Medallion Architecture** (Bronze > Silver > Gold), and produces analytics-ready dimensional models stored in MySQL.

The pipeline processes 6 source files across two systems, applies schema enforcement, data cleaning, standardization, deduplication, and business rule validation, then builds a **star schema** with dimension and fact views suitable for BI tools and analytics.

---

## Key Objectives

- Ingest CSV data from CRM and ERP systems into a structured Bronze layer
- Clean, validate, and standardize data in the Silver layer
- Build a Star Schema with **dim_customers**, **dim_products**, and **fact_sales**
- Validate data quality across layers (nulls, duplicates, row counts, FK integrity)
- Orchestrate the full end-to-end ELT workflow with a single entry point
- Ensure idempotent ingestion (prevents duplicate loading of the same files)

---

## Architecture

```
  CSV Files (CRM + ERP)
          |
          v
  +---------------+
  |  BRONZE LAYER |  Raw data loaded as-is (all VARCHAR/JSON)
  |   bronze_db   |  6 tables, raw_row JSON audit column
  +---------------+
          |
          v
  +---------------+
  |  SILVER LAYER |  Cleaned, validated, standardized
  |   silver_db   |  6 tables, proper data types
  +---------------+
          |
          v
  +---------------+
  |   GOLD LAYER  |  Star schema views for analytics
  |    gold_db    |  dim_customers, dim_products, fact_sales
  +---------------+
          |
          v
    BI / Analytics
```

### Layer Details

| Layer  | Database  | Objects   | Purpose                                          |
|--------|-----------|-----------|--------------------------------------------------|
| Bronze | bronze_db | 6 tables  | Raw landing zone, preserves original data as JSON |
| Silver | silver_db | 6 tables  | Cleaned, typed, deduplicated, validated           |
| Gold   | gold_db   | 3 views   | Business-ready star schema for reporting          |

---

## Tech Stack

- **Python 3.10+** -- Pipeline orchestration and transformations
- **Pandas** -- Data manipulation and cleaning
- **SQLAlchemy** -- Database abstraction and ORM
- **PyMySQL** -- MySQL Python connector
- **PyYAML** -- Configuration file parsing
- **NumPy** -- Numerical operations
- **Pytest** -- Testing framework
- **MySQL** -- Relational database (3 databases: bronze, silver, gold)

---

## Project Structure

```
data_engineering_project/
|
|-- configs/
|   |-- db_config.json            # MySQL connection credentials
|   |-- pipeline_config.yaml      # Bronze layer source-to-target mapping
|
|-- data/
|   |-- raw/
|   |   |-- source_crm/           # CRM source files
|   |   |   |-- cust_info.csv         # Customer profiles
|   |   |   |-- prd_info.csv          # Product catalog
|   |   |   |-- sales_details.csv     # Sales transactions
|   |   |-- source_erp/           # ERP source files
|   |       |-- CUST_AZ12.csv         # Customer supplemental data
|   |       |-- LOC_A101.csv          # Customer locations/geography
|   |       |-- PX_CAT_G1V2.csv       # Product categories
|   |-- logs/
|   |   |-- pipeline.log          # Centralized pipeline log
|   |-- processed/
|       |-- processed_files.csv   # Idempotency tracking ledger
|
|-- python/
|   |-- pipeline.py               # Main orchestrator (entry point)
|   |-- check_data.py             # Data inspection and DQ reporting
|   |-- bronze/
|   |   |-- load_bronze.py        # Bronze ingestion (6 loaders)
|   |   |-- helper.py             # CSV reader + raw_row builder
|   |-- silver/
|   |   |-- silver_pipeline.py    # Silver orchestrator
|   |   |-- crm/
|   |   |   |-- crm_customers.py  # Customer cleaning & dedup
|   |   |   |-- crm_products.py   # Product standardization
|   |   |   |-- crm_sales.py      # Sales validation & cleaning
|   |   |-- erp/
|   |       |-- erp_customers.py  # ERP customer, location, category
|   |-- gold/
|   |   |-- gold_pipeline.py      # Gold view creation
|   |-- extract/
|   |   |-- read_csv_files.py     # CSV extraction utilities
|   |   |-- validate_schema.py    # Schema validation
|   |-- dq_checks/
|   |   |-- check_nulls.py       # NOT NULL constraint checks
|   |   |-- check_duplicates.py  # Primary key uniqueness checks
|   |   |-- check_row_counts.py  # Row count validation across layers
|   |   |-- check_fk_integrity.py # Foreign key referential integrity
|   |-- utils/
|       |-- db_connection.py      # SQLAlchemy engine factory
|       |-- config_loader.py      # YAML config reader
|       |-- logger.py             # Centralized logging setup
|       |-- paths.py              # Cross-platform path utilities
|       |-- ingestion_checker.py  # Idempotency tracker
|
|-- sql/
|   |-- bronze/
|   |   |-- create_bronze_table.sql   # Bronze DDL (6 tables)
|   |-- silver/
|   |   |-- silver_layer_table.sql    # Silver DDL (6 tables)
|   |-- gold/
|       |-- create_dim_customers.sql  # Gold views (3 views)
|
|-- tests/
|   |-- test_pipeline.py          # Integration tests (DB, tables, data)
|   |-- test_data_quality.py      # DQ check validations
|   |-- test_transformations.py   # Unit tests for silver transforms
|
|-- docs/
|   |-- readme.md                 # This file
|   |-- data_catalog.md           # Gold layer schema documentation
|
|-- requirements.txt              # Python dependencies
|-- .gitignore
```

---

## Source Data

The pipeline ingests 6 CSV files from two source systems:

### CRM (Customer Relationship Management)

| File               | Description               | Key Columns                                    |
|--------------------|---------------------------|------------------------------------------------|
| cust_info.csv      | Customer profiles         | cst_id, cst_key, name, gender, marital_status  |
| prd_info.csv       | Product catalog           | prd_id, prd_key, prd_name, cost, product_line  |
| sales_details.csv  | Sales transactions        | order_num, prd_key, cust_id, dates, amounts    |

### ERP (Enterprise Resource Planning)

| File               | Description               | Key Columns                                    |
|--------------------|---------------------------|------------------------------------------------|
| CUST_AZ12.csv      | Customer supplemental     | cid, bdate, gen                                |
| LOC_A101.csv       | Customer geography        | cid, cntry                                     |
| PX_CAT_G1V2.csv    | Product categories        | id, cat, subcat, maintenance                   |

---

## Pipeline Stages

### 1. Bronze Layer (Raw Ingestion)

- Reads all 6 CSV files with all columns as strings (no type casting)
- Adds a `raw_row` JSON column preserving the original row for auditing
- Adds a `loaded_at` timestamp
- Checks idempotency via `processed_files.csv` to prevent re-ingestion
- Writes to `bronze_db` using pandas `to_sql` with SQLAlchemy

### 2. Silver Layer (Cleaning and Transformation)

Each source gets a dedicated transformation module:

**CRM Customers** (`crm_customers.py`):
- Schema enforcement (proper string/date types)
- Null normalization (`"NULL"`, `"None"`, `"nan"`, `""` converted to actual NULL)
- Gender standardization (m -> Male, f -> Female)
- Marital status standardization (s -> Single, m -> Married)
- Name cleanup (strip whitespace, title case)
- Deduplication (keep latest record per customer by create_date)
- Primary key null removal

**CRM Products** (`crm_products.py`):
- Schema enforcement (int, float, string, datetime)
- Product line mapping (R -> Road, M -> Mountain, T -> Touring, S -> Other)
- Category ID extraction from product key
- End date calculation using window function (LEAD equivalent)

**CRM Sales** (`crm_sales.py`):
- Date string to datetime conversion
- Business rule validation (no negatives, order_date <= ship_date, required fields)
- Data cleaning (absolute values, recalculate sales = quantity x price)
- Invalid records logged separately

**ERP Customers** (`erp_customers.py`):
- Customer ID standardization (extract last 10 characters)
- Country mapping (US/USA -> United States, DE -> Germany)
- Gender mapping and birth date parsing

### 3. Gold Layer (Star Schema)

Creates three SQL views that join silver tables into a dimensional model:

**dim_customers** (10 columns):
- Joins CRM customers + ERP customers + ERP locations
- Generates surrogate key via ROW_NUMBER()
- Uses CRM as primary source, ERP as fallback for gender

**dim_products** (11 columns):
- Joins CRM products + ERP categories
- Filters to active products only (prd_end_dt IS NULL)
- Generates surrogate key via ROW_NUMBER()

**fact_sales** (9 columns):
- Joins sales to dim_products and dim_customers via surrogate keys
- Contains order_date, shipping_date, due_date, sales_amount, quantity, price

---

## Data Quality Framework

The pipeline includes four data quality check modules:

| Check              | Module                | What It Validates                              |
|--------------------|-----------------------|------------------------------------------------|
| Null checks        | check_nulls.py        | Critical columns are NOT NULL                  |
| Duplicate checks   | check_duplicates.py   | Primary key uniqueness per table               |
| Row count checks   | check_row_counts.py   | Tables are non-empty; silver <= bronze counts   |
| FK integrity       | check_fk_integrity.py | Referential integrity between related tables   |

FK integrity rules validated:
- `sales.sales_cust_id` -> `customers.cst_id`
- `sales.sales_prd_key` -> `products.prd_key`
- `erp_cust.cid` -> `customers.cst_key`
- `erp_location.cid` -> `customers.cst_key`
- `erp_category.id` -> `products.cat_id`

---

## Prerequisites

- Python 3.10 or higher
- MySQL Server running on localhost:3306
- Three MySQL databases created: `bronze_db`, `silver_db`, `gold_db`
- Tables and views created using the SQL scripts in `sql/`

---

## Setup and Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MohammadSaif001/data-engineer-project.git
   cd data_engineering_project
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the database connection:**

   Create `configs/db_config.json`:
   ```json
   {
     "mysql": {
       "host": "localhost",
       "port": 3306,
       "user": "your_user",
       "password": "your_password",
       "bronze_db": "bronze_db",
       "silver_db": "silver_db",
       "gold_db": "gold_db"
     }
   }
   ```

4. **Create the MySQL databases and tables:**
   ```sql
   CREATE DATABASE IF NOT EXISTS bronze_db;
   CREATE DATABASE IF NOT EXISTS silver_db;
   CREATE DATABASE IF NOT EXISTS gold_db;
   ```
   Then run the DDL scripts:
   - `sql/bronze/create_bronze_table.sql`
   - `sql/silver/silver_layer_table.sql`
   - `sql/gold/create_dim_customers.sql` (run after silver is populated)

---

## Running the Pipeline

Run the full end-to-end pipeline:

```bash
python python/pipeline.py
```
**Expected Output**
```2026-03-09 01:04:32,101 | INFO | pipeline | Pipeline start
2026-03-09 01:04:32,101 | INFO | [BATCH START] Bronze layer ingestion started
2026-03-09 01:04:32,101 | INFO | [START] Loading table: crm_customers_info
2026-03-09 01:04:32,101 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:32,229 | INFO | [SKIP] Table already processed: crm_customers_info
2026-03-09 01:04:32,229 | INFO | [START] Loading table: crm_prd_info
2026-03-09 01:04:32,229 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:32,231 | INFO | [SKIP] Table already processed: crm_prd_info
2026-03-09 01:04:32,231 | INFO | [START] Loading table: crm_sales_details
2026-03-09 01:04:32,233 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:32,235 | INFO | [SKIP] Table already processed: crm_sales_details
2026-03-09 01:04:32,235 | INFO | [START] Loading table: erp_cust_az12
2026-03-09 01:04:32,235 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:32,236 | INFO | [SKIP] Table already processed: erp_cust_az12
2026-03-09 01:04:32,236 | INFO | [START] Loading table: erp_location_a101
2026-03-09 01:04:32,236 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:32,236 | INFO | [SKIP] Table already processed: erp_location_a101
2026-03-09 01:04:32,236 | INFO | [START] Loading table: erp_px_cat_g1v2
2026-03-09 01:04:32,236 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:32,243 | INFO | [SKIP] Table already processed: erp_px_cat_g1v2
2026-03-09 01:04:32,243 | INFO | [BATCH END] Bronze layer completed | Total time=0.14s
2026-03-09 01:04:32,243 | INFO | ============================================================
2026-03-09 01:04:32,243 | INFO | [START] Starting Silver Layer Pipeline
2026-03-09 01:04:32,243 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:32,570 | INFO | Normalizing nulls in column: cst_id
2026-03-09 01:04:32,581 | INFO | Normalizing nulls in column: cst_key
2026-03-09 01:04:32,591 | INFO | Normalizing nulls in column: cst_firstname
2026-03-09 01:04:32,602 | INFO | Normalizing nulls in column: cst_lastname
2026-03-09 01:04:32,611 | INFO | Normalizing nulls in column: cst_marital_status
2026-03-09 01:04:32,619 | INFO | Normalizing nulls in column: cst_gndr
2026-03-09 01:04:32,647 | WARNING | [NULL PRIMARY KEY REMOVED] 4 rows removed where cst_id is NULL
2026-03-09 01:04:32,651 | INFO | [DUPLICATE FOUND] cst_id=29433 \u2192 occurrences=2
2026-03-09 01:04:32,651 | INFO | [DUPLICATE FOUND] cst_id=29449 \u2192 occurrences=2
2026-03-09 01:04:32,651 | INFO | [DUPLICATE FOUND] cst_id=29466 \u2192 occurrences=3
2026-03-09 01:04:32,651 | INFO | [DUPLICATE FOUND] cst_id=29473 \u2192 occurrences=2
2026-03-09 01:04:32,651 | INFO | [DUPLICATE FOUND] cst_id=29483 \u2192 occurrences=2
2026-03-09 01:04:32,666 | INFO | [DEDUP] Total rows   : 18490
2026-03-09 01:04:32,666 | INFO | [DEDUP] Kept rows    : 18484
2026-03-09 01:04:32,666 | INFO | [DEDUP] Deleted rows : 6
2026-03-09 01:04:32,667 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:33,311 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:33,322 | INFO | Normalizing nulls in column: prd_key
2026-03-09 01:04:33,322 | INFO | Normalizing nulls in column: prd_name
2026-03-09 01:04:33,322 | INFO | Normalizing nulls in column: prd_line
2026-03-09 01:04:33,340 | INFO | No duplicates found
2026-03-09 01:04:33,340 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:33,434 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:34,187 | INFO | Normalizing nulls in column: sales_prd_key
2026-03-09 01:04:34,226 | INFO | Normalizing nulls in column: sales_ord_num
2026-03-09 01:04:34,268 | INFO | Normalizing nulls in column: sales_cust_id
2026-03-09 01:04:34,336 | INFO | Converted sales_order_date_raw to datetime. Null values after conversion: 19
2026-03-09 01:04:34,336 | INFO | sales_order_date_raw -> 19 invalid dates converted to NaT
2026-03-09 01:04:34,342 | INFO | Converted sales_ship_date_raw to datetime. Null values after conversion: 0
2026-03-09 01:04:34,342 | INFO | sales_ship_date_raw -> 0 invalid dates converted to NaT
2026-03-09 01:04:34,347 | INFO | Converted sales_due_date_raw to datetime. Null values after conversion: 0
2026-03-09 01:04:34,347 | INFO | sales_due_date_raw -> 0 invalid dates converted to NaT
2026-03-09 01:04:34,362 | WARNING | 15 invalid records detected.
2026-03-09 01:04:34,362 | INFO | Valid records: 60383
2026-03-09 01:04:34,362 | INFO | Invalid records: 15
2026-03-09 01:04:34,377 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:36,627 | INFO | Starting ERP Customers Silver Pipeline
2026-03-09 01:04:36,627 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:36,768 | INFO | Extracted 18484 records from bronze.
2026-03-09 01:04:36,784 | INFO | Schema enforcement completed.
2026-03-09 01:04:36,784 | INFO | Customer ID standardization completed.
2026-03-09 01:04:36,800 | INFO | Value replacements applied.
2026-03-09 01:04:36,800 | INFO | Technical columns dropped.
2026-03-09 01:04:36,800 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:37,204 | INFO | ERP Customers Silver Pipeline completed successfully.
2026-03-09 01:04:37,205 | INFO | Starting ERP Customer Locations Silver Pipeline
2026-03-09 01:04:37,205 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:37,367 | INFO | Extracted 18484 records from bronze for location data.
2026-03-09 01:04:37,368 | INFO | Schema enforcement completed for location data.
2026-03-09 01:04:37,378 | INFO | Value replacements applied for location data.
2026-03-09 01:04:37,379 | INFO | Technical columns dropped for location data.
2026-03-09 01:04:37,382 | INFO | CID transformation completed for location data.
2026-03-09 01:04:37,382 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:37,712 | INFO | ERP Customer Locations Silver Pipeline completed successfully.
2026-03-09 01:04:37,712 | INFO | Starting ERP Product Categories Silver Pipeline
2026-03-09 01:04:37,712 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:37,727 | INFO | Extracted 37 records from bronze.
2026-03-09 01:04:37,728 | INFO | Technical columns dropped for category data.
2026-03-09 01:04:37,728 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:37,785 | INFO | ERP Product Categories Silver Pipeline completed successfully.
2026-03-09 01:04:37,785 | INFO | Silver Layer Pipeline finished: 6 succeeded, 0 failed out of 6
2026-03-09 01:04:37,785 | INFO | ============================================================
2026-03-09 01:04:37,785 | INFO | [START] Starting Gold Layer Pipeline
2026-03-09 01:04:37,785 | INFO | Loading config from: d:\data_engineering_project\configs\db_config.json
2026-03-09 01:04:37,813 | INFO | Executing: DROP VIEW IF EXISTS gold_db.dim_customers ...
2026-03-09 01:04:37,824 | INFO |   -> OK
2026-03-09 01:04:37,824 | INFO | Executing: CREATE VIEW gold_db.dim_customers AS SELECT     ROW_NUMBER() OVER (ORDER BY ci.c ...
2026-03-09 01:04:37,831 | INFO |   -> OK
2026-03-09 01:04:37,831 | INFO | Executing: DROP VIEW IF EXISTS gold_db.dim_products ...
2026-03-09 01:04:37,836 | INFO |   -> OK
2026-03-09 01:04:37,837 | INFO | Executing: CREATE VIEW gold_db.dim_products AS SELECT      ROW_NUMBER() OVER( ORDER BY pn.p ...
2026-03-09 01:04:37,844 | INFO |   -> OK
2026-03-09 01:04:37,844 | INFO | Executing: DROP VIEW IF EXISTS gold_db.fact_sales ...
2026-03-09 01:04:37,844 | INFO |   -> OK
2026-03-09 01:04:37,844 | INFO | Executing: CREATE VIEW gold_db.fact_sales AS SELECT      sd.sales_ord_num AS order_number,  ...
2026-03-09 01:04:37,844 | INFO |   -> OK
2026-03-09 01:04:37,844 | INFO | Gold Layer Pipeline finished: 6 succeeded, 0 failed out of 6
2026-03-09 01:04:37,844 | INFO | pipeline | Pipeline complete
```

This executes in order:
1. **Bronze pipeline** -- Loads all 6 CSV files into bronze_db
2. **Silver pipeline** -- Transforms and loads cleaned data into silver_db
3. **Gold pipeline** -- Creates star schema views in gold_db

### Inspect the data:

```bash
# Data quality checks 
python python/check_data.py

```

This displays sample data from each bronze table and runs all data quality checks.

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test suites
pytest tests/test_pipeline.py -v          # Integration tests
pytest tests/test_data_quality.py -v      # Data quality checks
pytest tests/test_transformations.py -v   # Unit tests for transforms
```

---

## Key Design Decisions

- **Idempotent ingestion**: `processed_files.csv` tracks which files have been loaded, preventing duplicate bronze ingestion on re-runs.
- **Raw row preservation**: Every bronze record includes a `raw_row` JSON column containing the original CSV row, enabling full data lineage and debugging.
- **Views over tables in Gold**: The gold layer uses SQL views rather than materialized tables, ensuring the analytics layer always reflects the latest silver data.
- **Modular transformations**: Each source table has its own transformation module with dedicated functions for schema enforcement, normalization, standardization, and validation.
- **Cross-platform paths**: Uses `pathlib` and `os.path` for Windows/Linux compatibility.

---

## Future Enhancements

- Cloud migration (AWS S3 + RDS or Azure Data Lake + Azure SQL)
- Orchestration with Apache Airflow for scheduling and monitoring
- dbt-based transformations to replace Python silver layer
- Dockerization for environment consistency
- Real-time ingestion with Apache Kafka
- CI/CD pipeline with automated testing on pull requests
- Data lineage and metadata catalog integration

---

## Author

**Mohammad Saif**
Data Engineer | ELT Pipeline | Medallion
Architecture  | Dimensional and Star Modeling

[![GitHub](https://img.shields.io/badge/GitHub-MohammadSaif001-black?logo=github)](https://github.com/MohammadSaif001)
