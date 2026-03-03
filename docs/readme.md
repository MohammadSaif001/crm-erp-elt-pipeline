# ELT Data Engineering Pipeline

### Medallion Architecture (Bronze > Silver > Gold) | Python + MySQL

Author: **Mohammad Saif**

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
   git clone <repository-url>
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

This executes in order:
1. **Bronze pipeline** -- Loads all 6 CSV files into bronze_db
2. **Silver pipeline** -- Transforms and loads cleaned data into silver_db
3. **Gold pipeline** -- Creates star schema views in gold_db

### Inspect the data:

```bash
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
Aspiring Data Engineer
