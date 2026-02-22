SHOW databases;
CREATE DATABASE IF NOT EXISTS silver_db;
USE silver_db;


CREATE TABLE IF NOT EXISTS crm_customers_info (
  ingest_id           BIGINT AUTO_INCREMENT PRIMARY KEY,
  cst_id VARCHAR(50)  NOT NULL UNIQUE,
  cst_key             VARCHAR(100) NULL,
  cst_firstname       VARCHAR(200) NULL,
  cst_lastname        VARCHAR(200) NULL,
  cst_marital_status  VARCHAR(50) NULL,
  cst_gender          VARCHAR(50) NULL,
  cst_create_date     DATE NOT NULL,
  loaded_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      source_system VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_prd_info (
  ingest_id          BIGINT AUTO_INCREMENT PRIMARY KEY,
  prd_id             VARCHAR(50) NULL,
  prd_key            VARCHAR(100) NULL,
  prd_name           VARCHAR(255) NULL,
  prd_cost           DECIMAL(12,2) NULL,
  prd_line           VARCHAR(100) NULL,
  prd_start          DATE NOT NULL,
  prd_end            DATE NOT NULL,
  loaded_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      source_system VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS crm_sales_details (
  ingest_id            BIGINT AUTO_INCREMENT PRIMARY KEY,
  sales_ord_num        VARCHAR(100) NULL,
  sales_prd_key        VARCHAR(100) NULL,
  sales_cust_id        VARCHAR(50) NULL,
  sales_order_date     DATE ,
  sales_ship_date      DATE ,
  sales_due_date       DATE ,
  sales_sales          DECIMAL(12,2) NULL,
  sales_quantity       INT NULL,
  sales_price          DECIMAL(12,2) NULL,
  loaded_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      source_system VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS erp_cust_az12 (
  ingest_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
  cid             VARCHAR(100) NULL,
  birth_date_raw  VARCHAR(100) NULL,
  gender_raw      VARCHAR(50) NULL,
  loaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  source_system VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS erp_location_al01 (
  cid             VARCHAR(100) NULL,
  country_name    VARCHAR(255) NULL,
  loaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  source_system VARCHAR(50) NOT NULL
);

CREATE TABLE IF NOT EXISTS erp_px_cat_g1v2 (
  ingest_id       BIGINT AUTO_INCREMENT PRIMARY KEY,
  id              VARCHAR(100) NULL,
  cat             VARCHAR(100) NULL,
  subcat          VARCHAR(100) NULL,
  maintenance_raw VARCHAR(100) NULL,
  loaded_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  source_system VARCHAR(50) NOT NULL
);

SHOW TABLES;

