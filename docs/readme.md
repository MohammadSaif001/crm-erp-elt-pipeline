# ELT Data Engineering Pipeline  
### Medallion Architecture (Bronze → Silver → Gold) | Python + MySQL  
Author: **Mohammad Saif**

---

## Overview  
This project implements a production-style **ELT pipeline** that ingests raw CSV files, loads them into a **Bronze → Silver → Gold** architecture, and produces analytics-ready dimensional models.

The design follows data engineering best practices: modular code, schema validation, logging, error handling, and data quality checks.

---

## Key Objectives  
- Ingest CSV data into structured layers  
- Clean and standardize data (Silver layer)  
- Build Star Schema: **dim_customers, dim_products, fact_sales**  
- Validate data quality (nulls, duplicates, FK integrity)  
- Orchestrate the full end-to-end ELT workflow in Python  

---

## Architecture  
**Bronze Layer:** Raw data (as-is)  
**Silver Layer:** Cleaned, validated, standardized data  
**Gold Layer:** Business-ready star schema for analytics  

---

## 🛠️ Tech Stack  
- **Python 3.10+**  
- **Pandas, SQLAlchemy, PyMySQL**  
- **MySQL**  
- **Git, VS Code**  

---

## Project Structure  
```


data_engineering_project/
│
├── configs/ # Database + pipeline configs
├── data/ # Raw, processed files, logs
├── sql/ # Table creation scripts
├── python/ # All pipeline modules
├── tests/ # Unit tests
└── README.md 
```


---

##  Source Data  
- **customers.csv** – customer profile information  
- **products.csv** – product catalog  
- **orders.csv** – transactional order data  

---

## Core Features  
- Modular ELT architecture  
- Bronze/Silver/Gold layered design  
- Data validation & cleaning  
- Star schema modeling  
- Logging & error handling  
- Data quality checks  
- Pipeline orchestrator  

---

## Running the Pipeline  

---

##  Future Enhancements  
- AWS (S3 + RDS) migration  
- Orchestration with Airflow  
- dbt-based transformations  
- Dockerization  
- Real-time ingestion with Kafka  

---

## Author  
**Mohammad Saif**
**ZawberuS**
Aspiring Data Engineer  
