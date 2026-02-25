USE bronze_db;

CREATE TABLE IF NOT EXISTS crm_customers_info (
  ingest_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  raw_row JSON NOT NULL,                -- original row preserved
  cst_id VARCHAR(50) NULL,
  cst_key VARCHAR(100) NULL,
  cst_firstname VARCHAR(200) NULL,
  cst_lastname VARCHAR(200) NULL,
  cst_marital_status VARCHAR(50) NULL,
  cst_gndr VARCHAR(50) NULL,            -- keep original field name from file
  cst_create_date_raw VARCHAR(100) NULL,-- raw date string if present
  loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crm_prd_info (
  ingest_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  raw_row JSON NOT NULL,
  prd_id VARCHAR(50) NULL,
  prd_key VARCHAR(100) NULL,
  prd_name VARCHAR(255) NULL,
  prd_cost DECIMAL(12,2) NULL,
  prd_line VARCHAR(100) NULL,
  prd_start_date_raw VARCHAR(100) NULL,
  prd_end_date_raw VARCHAR(100) NULL,
  loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS crm_sales_details (
  ingest_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  raw_row JSON NOT NULL,
  sales_ord_num VARCHAR(100) NULL,
  sales_prd_key VARCHAR(100) NULL,
  sales_cust_id VARCHAR(50) NULL,
  sales_order_date_raw VARCHAR(100) NULL,
  sales_ship_date_raw VARCHAR(100) NULL,
  sales_due_date_raw VARCHAR(100) NULL,
  sales_sales DECIMAL(12,2) NULL,
  sales_quantity INT NULL,
  sales_price DECIMAL(12,2) NULL,
  loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS erp_cust_az12 (
  ingest_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  raw_row JSON NOT NULL,
  cid VARCHAR(100) NULL,
  birth_date_raw VARCHAR(100) NULL,
  gender_raw VARCHAR(50) NULL,
  loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS erp_location_a101 (
  raw_row JSON NOT NULL,
  cid VARCHAR(100) NULL,
  country_name VARCHAR(255) NULL,
  loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS erp_px_cat_g1v2 (
  ingest_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  raw_row JSON NOT NULL,
  id VARCHAR(100) NULL,
  cat VARCHAR(100) NULL,
  subcat VARCHAR(100) NULL,
  maintenance_raw VARCHAR(100) NULL,
  loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
