import os
import sys
import time
import logging
import pandas as pd
import json
import numpy as np
from sqlalchemy import types
from typing import Any, cast
from sqlalchemy.dialects.mysql import JSON as MYSQL_JSON

current_dir = os.path.dirname(os.path.abspath(__file__)) # .../python/bronze
python_folder = os.path.dirname(current_dir)             # .../python

if python_folder not in sys.path:
    sys.path.append(python_folder)


from utils.db_connection import get_engine
from utils.paths import get_raw_data_path

from utils.ingestion_checker import(
    PROCESSED_FILE,
    is_file_processed,
    mark_file_processed
)
print("PROCESSED_FILE PATH =", PROCESSED_FILE)

logging.basicConfig(
    filename=r"D:\data_engineering_project\data\logs\pipeline.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

#! Bronze CSV Reader Function
def read_bronze_csv(csv_path: str) -> pd.DataFrame:
    """
    Bronze CSV reader:
    - checks file exists
    - reads all columns as string
    - normalizes headers
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV not found at: {csv_path}")

    df = pd.read_csv(csv_path, dtype=str)
    df.columns = df.columns.str.strip().str.lower()
    return df

#! Add Raw Row Function
def add_raw_row(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds raw_row JSON column for Bronze layer
    """
    df_temp = df.where(pd.notnull(df), np.nan)
    df["raw_row"] = df_temp.apply(
        lambda r: json.dumps(r.to_dict(), default=str),
        axis=1
    )
    return df


#! Database Connection Function
def data_base_connection():
    try:
        engine = get_engine("bronze")
        print("Database connected successfully.")
        return engine  # Return it!
    except Exception as e:
        print(f"Connection Error: {e}")
        return None  
    
#! 1.Customer Load Function
def load_cust_info():
    
    start_time = time.time()
    source = "source_crm"
    file_name = "cust_info.csv"
    bronze_table = "crm_customers_info"
    table_name = "crm_customers_info"
    logging.info(f'[START] Loading table: {table_name}')

    print("Starting Bronze Load: Customers.")
    engine =data_base_connection()
    if engine is None:
        print("Exiting due to database connection failure.")
        return
    try:
        if is_file_processed(source, file_name, bronze_table):
            print(f"Skipping {bronze_table} - already processed.")
            logging.info(f'[SKIP] Table already processed: {table_name}')
            return

        # 1. Read CSV (wrapped)
        csv_path = get_raw_data_path(
        os.path.join("source_crm", "cust_info.csv")
    )

        df = read_bronze_csv(csv_path)
        
        # 2. Add raw_row (wrapped)
        df = add_raw_row(df)


        # 3. Map Columns 
        # .get() 
        df['cst_id']              = df.get('cst_id')
        df['cst_key']             = df.get('cst_key')
        df['cst_firstname']       = df.get('cst_firstname')
        df['cst_lastname']        = df.get('cst_lastname')
        df['cst_marital_status']  = df.get('cst_marital_status')
        df['cst_gndr']            = df.get('cst_gndr')
        df['cst_create_date_raw'] = df.get('cst_create_date')


        #* Select columns to write
        final_cols = [
            'raw_row', 
            'cst_id', 
            'cst_key',
            'cst_firstname', 
            'cst_lastname', 
            'cst_marital_status',
            'cst_gndr', 
            'cst_create_date_raw',   
        ]
        
        #* Filter dataframe to only include columns that actually exist now
        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]

        #* 6. Write to MySQL 
        dtype_map = {
            "raw_row": MYSQL_JSON,
            "cst_id": types.VARCHAR(50),
            "cst_key": types.VARCHAR(100),
            "cst_firstname": types.VARCHAR(100)
        }

        print(f"Writing {len(df_final)} rows to table 'crm_customers_info'...")
        
        df_final.to_sql(
            name='crm_customers_info',
            con=engine,
            if_exists="replace",
            index=False,
            dtype=cast(Any, dtype_map)
        )
        mark_file_processed(source, file_name, bronze_table)
        elapsed_time = time.time() - start_time
        logging.info(
            f"[END] Loaded table: {table_name} | Time taken: {elapsed_time:.2f} seconds"
            )
        print("Success: Data Loaded to bronze_db crm_customers_info table.")

    except Exception as e:
        logging.exception(
            f"[ERROR] Loading table: {table_name} | Error: {e}"
            )    
        print(f"Processing Error: {e}")

#! 2. Sales Load Function
def load_sales_details_info():
    start_time = time.time()
    source = "source_crm"
    file_name = "sales_details.csv"
    bronze_table = "crm_sales_details"
    table_name = "crm_sales_details"
    logging.info(f'[START] Loading table: {table_name}')


    print("Starting Bronze Load: Sales.")
    #! Connect to Database
    engine =data_base_connection()
    if engine is None:
        print("Exiting due to database connection failure.")
        return

    try:
        #! Check if file already processed
        if is_file_processed(source, file_name, bronze_table):
            print(f"Skipping {bronze_table} - already processed.")
            logging.info(f"[SKIP] Table already processed: {table_name}")   
            return
        
        csv_path = get_raw_data_path(
        os.path.join("source_crm", "sales_details.csv")
    )
        #! 1. Read CSV (wrapped)
        df = read_bronze_csv(csv_path)

        #! 2. Add raw_row (wrapped)
        df = add_raw_row(df)
        #! 3. Map Columns 
        #! .get() 

        df['ingest_id']            = df.get('ingest_id')
        df['sales_prd_key']        = df.get('sls_prd_key')
        df['sales_ord_num']        = df.get('sls_ord_num')
        df['sales_cust_id']        = df.get('sls_cust_id')
        df['sales_order_date_raw'] = df.get('sls_order_dt')
        df['sales_ship_date_raw']  = df.get('sls_ship_dt')
        df['sales_due_date_raw']   = df.get('sls_due_dt')
        df['sales_sales']          = df.get('sls_sales')
        df['sales_quantity']       = df.get('sls_quantity')
        df['sales_price']          = df.get('sls_price')
        df['loaded_at']            = pd.Timestamp.now()

        final_cols =['ingest_id',
                    'raw_row',
                    'sales_prd_key',
                    'sales_ord_num',
                    'sales_cust_id',
                    'sales_order_date_raw',
                    'sales_ship_date_raw',
                    'sales_due_date_raw',
                    'sales_sales',
                    'sales_quantity',
                    'sales_price',
                    'loaded_at']
        
        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]
        
        dtype_map = {
            "raw_row": MYSQL_JSON,
            "sales_order_num": types.VARCHAR(50),
            "sales_order_key": types.VARCHAR(100),
            "sales_order_id": types.VARCHAR(100)
        }
        print(f"Writing {len(df_final)} rows to table 'crm_sales_details'...")
        df_final.to_sql(
            name='crm_sales_details',
            con=engine,
            if_exists="replace",
            index=False,
            dtype=cast(Any, dtype_map)
        )
        
        print("Success: Data Loaded to bronze_db crm_sales_details table.")
        mark_file_processed(source, file_name, bronze_table)
        elapsed_time = time.time() - start_time
        logging.info(
            f"[END] Loaded table: {table_name} | Time taken: {elapsed_time:.2f} seconds"
        )
    except Exception as e:
        logging.exception(
            f"[ERROR] Loading table: {table_name} | Error: {e}"
        )
        print(f"Processing Error: {e}")

#! 3.Product Load Function
def load_prd_info():
    start_time = time.time()
    source = "source_crm"
    file_name = "prd_info.csv"
    bronze_table = "crm_prd_info"
    table_name = "crm_prd_info"
    logging.info(f'[START] Loading table: {table_name}')

    print("Starting Bronze Load: Product.")
    
    #! Connect to Database 
    engine =data_base_connection()
    if engine is None:
        print("Exiting due to database connection failure.")
        return

    try:
        #! Check if file already processed
        if is_file_processed(source, file_name, bronze_table):
            print(f"File '{file_name}' from source '{source}' already processed. Skipping ingestion.")
            logging.info(f"[SKIP] Table already processed: {table_name}")
            return
    
        #! 1. Read CSV 
        csv_path = get_raw_data_path(
        os.path.join("source_crm", "prd_info.csv")
    )
        df = read_bronze_csv(csv_path)
        #! 2. Add raw_row
        df = add_raw_row(df)
        df['prd_id']    = df.get('prd_id')
        df['prd_key']   = df.get('prd_key')
        df['prd_name']  = df.get('prd_nm')
        df['prd_cost']  = df.get('prd_cost')
        df['prd_line']  = df.get('prd_line')
        df['prd_start_date_raw'] = df.get('prd_start_dt')
        df['prd_end_date_raw'] = df.get('prd_end_dt')

        #! Select columns to write
        final_cols =['raw_row',
                    'prd_id',
                    'prd_key',
                    'prd_name',
                    'prd_cost',
                    'prd_line',
                    'prd_start_date_raw',
                    'prd_end_date_raw']
        
        #! Filter dataframe to only include columns that actually exist now
        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]
        #! Write to MySQL
        dtype_map = {
            "raw_row":  MYSQL_JSON,
            "prd_id":   types.VARCHAR(50),
            "prd_key":  types.VARCHAR(100),
            "prd_name": types.VARCHAR(100)
        }
        #! console log
        print(f"Writing {len(df_final)} rows to table 'crm_prd_info'...")
        df_final.to_sql(
            name='crm_prd_info',
            con=engine,
            if_exists="replace",
            index=False,
            dtype=cast(Any, dtype_map)
        )
        
        print("Success: Data Loaded to bronze_db crm_prd_info table.")
        elapsed_time = time.time() - start_time
        logging.info(
            f"[END] Loaded table: {table_name} | Time taken: {elapsed_time:.2f} seconds"
        )
        mark_file_processed(source, file_name, bronze_table)
    except Exception as e:
        logging.error(
            f"[ERROR] Loading table: {table_name} | Error: {e}"
        )
        print(f"Processing Error: {e}")

#! ERP Load Functions
def load_erp_cust_az12():
    start_time = time.time()
    source = "source_erp"
    file_name = "CUST_AZ12.csv"
    bronze_table = "erp_cust_az12"
    table_name = "erp_cust_az12"
    logging.info(f'[START] Loading table: {table_name}')


    print("Starting Bronze Load: ERP Customer.")
    
    #! Connect to Database
    engine =data_base_connection()
    if engine is None:
        print("Exiting due to database connection failure.")
        return
    try:
        #! Check if file already processed
        if is_file_processed(source, file_name, bronze_table):
            print(f"File '{file_name}' from source '{source}' already processed. Skipping ingestion.")
            logging.info(f"[SKIP] Table already processed: {table_name}")
            return
        csv_path = get_raw_data_path(os.path.join
                ("source_erp", "CUST_AZ12.csv"))
        #! 1. Read  CSV
        df = read_bronze_csv(csv_path)
        #! 2. Add raw_row
        df = add_raw_row(df)

        #! 3.Colunmn Mapping
        df['ingest_id']       = df.get('ingest_id')
        df['cid']             = df.get('cid')
        df['birth_date_raw']  = df.get('bdate')
        df['gender_raw']      = df.get('gen')
        df['loaded_at']       = pd.Timestamp.now()

        final_cols = ['ingest_id',
                    'raw_row',
                    'cid',
                    'birth_date_raw',
                    'gender_raw',
                    'loaded_at']
        
        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]

        #! Write to MySQL
        dtype_map = {
            "raw_row": MYSQL_JSON,
            "cid": types.VARCHAR(50)
        }
        #! console log
        print(f"Writing {len(df_final)} rows to table 'erp_cust_az12'...")
        df_final.to_sql(
            name='erp_cust_az12',
            con=engine,
            if_exists="replace",
            index=False,
            dtype=cast(Any, dtype_map)
        )
        
        print("Success: Data Loaded to bronze_db erp_cust_az12 table.")
        mark_file_processed(source, file_name, bronze_table)
        elapsed_time = time.time() - start_time
        logging.info(
            f"[END] Loaded table: {table_name} | Time taken: {elapsed_time:.2f} seconds"
        )
    except Exception as e:
        logging.exception(
            f"[ERROR] Loading table: {table_name} | Error: {e}"
        )
        print(f"Processing Error: {e}")

def load_erp_location_a101():
    start_time = time.time()
    source = "source_erp"
    file_name = "LOC_A101.csv"
    bronze_table = "erp_location_a101"
    table_name = "erp_location_a101"
    logging.info(f'[START] Loading table: {table_name}')

    print("Starting Bronze Load: ERP Location.")
    
    #! Connect to Database
    engine =data_base_connection()
    if engine is None:
        print("Exiting due to database connection failure.")
        return
    try:
        #! Check if file already processed
        if is_file_processed(source, file_name, bronze_table):
            print(f"File '{file_name}' from source '{source}' already processed. Skipping ingestion.")
            logging.info(f"[SKIP] Table already processed: {table_name}")
            return
        csv_path = get_raw_data_path(os.path.join
                ("source_erp", "LOC_A101.csv"))
        #! 1. Read  CSV
        df = read_bronze_csv(csv_path)
        #! 2. Add raw_row
        df = add_raw_row(df)

        #! 3.Colunmn Mapping
        df['cid']             = df.get('cid')
        df['country_name']    = df.get('cntry')
        df['loaded_at']       = pd.Timestamp.now()

        final_cols = ['raw_row',
                    'cid',
                    'country_name',
                    'loaded_at']
        
        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]

        #! Write to MySQL
        dtype_map = {
            "raw_row": MYSQL_JSON,
            "cid": types.VARCHAR(50)
        }
        #! console log
        print(f"Writing {len(df_final)} rows to table 'erp_location_a101'")
        df_final.to_sql(
            name='erp_location_a101',
            con=engine,
            if_exists="replace",
            index=False,
            chunksize=1000,
            dtype=cast(Any, dtype_map)
        )
        
        print("Success: Data Loaded to bronze_db erp_location_a101 table.")
        mark_file_processed(source, file_name, bronze_table)
        elapsed_time = time.time() - start_time
        logging.info(
            f"[END] Loaded table: {table_name} | Time taken: {elapsed_time:.2f} seconds"
        )
    except Exception as e:
        logging.exception(
            f"[ERROR] Loading table: {table_name} | Error: {e}"
        )

def load_erp_px_cat_g1v2():
    start_time = time.time()
    source = "source_erp"
    file_name = "PX_CAT_G1V2.csv"
    bronze_table = "erp_px_cat_g1v2"
    table_name = "erp_px_cat_g1v2"
    logging.info(f'[START] Loading table: {table_name}')
    print("Starting Bronze Load: ERP Category.")
    
    #! Connect to Database
    engine =data_base_connection()
    if engine is None:
        print("Exiting due to database connection failure.")
        return
    try:
        #! Check if file already processed
        if is_file_processed(source, file_name, bronze_table):  
            print(f"File '{file_name}' from source '{source}' already processed. Skipping ingestion.")
            logging.info(f"[SKIP] Table already processed: {table_name}")
            return
        csv_path = get_raw_data_path(os.path.join
                ("source_erp", "PX_CAT_G1V2.csv"))
        #! 1. Read  CSV
        df = read_bronze_csv(csv_path)
        #! 2. Add raw_row
        df = add_raw_row(df)

        #! 3.Colunmn Mapping
        df['ingest_id']       = df.get('ingest_id')
        df['id']              = df.get('id')
        df['cat']             = df.get('cat')
        df['subcat']         = df.get('subcat')
        df['maintenance_raw'] = df.get('maintenance')
        df['loaded_at']       = pd.Timestamp.now()

        final_cols = ['ingest_id',
                    'raw_row',
                    'id',
                    'cat',
                    'subcat',
                    'maintenance_raw',
                    'loaded_at']
        
        cols_to_write = [c for c in final_cols if c in df.columns]
        df_final = df[cols_to_write]

        #! Write to MySQL
        dtype_map = {
            "raw_row": MYSQL_JSON,
            "id": types.VARCHAR(50)
        }
        #! console log
        print(f"Writing {len(df_final)} rows to table 'erp_px_cat_g1v2'...")
        df_final.to_sql(
            name='erp_px_cat_g1v2',
            con=engine,
            if_exists="replace",
            index=False,
            dtype=cast(Any, dtype_map)
        )
        
        print("Success: Data Loaded to bronze_db erp_px_cat_g1v2 table.")
        mark_file_processed(source, file_name, bronze_table)
        elapsed_time = time.time() - start_time
        logging.info(
            f"[END] Loaded table: {table_name} | Time taken: {elapsed_time:.2f} seconds"
        )
    except Exception as e:
        logging.exception(
            f"[ERROR] Loading table: {table_name} | Error: {e}"
        )
        print(f"Processing Error: {e}")

#! Orchestration Function
def run_bronze_pipeline():
    """
    Orchestrates complete Bronze layer ingestion.
    Entry point for local runs, schedulers, and future Airflow DAGs.
    """
    print("Starting Bronze Layer Pipeline...")
    batch_start = time.time()
    logging.info("[BATCH START] Bronze layer ingestion started")
    # CRM sources
    load_cust_info()
    load_prd_info()
    load_sales_details_info()

    # ERP sources
    load_erp_cust_az12()
    load_erp_location_a101()
    load_erp_px_cat_g1v2()

    print("Bronze Layer Pipeline Completed Successfully.")
    batch_duration = time.time() - batch_start
    logging.info(
        f"[BATCH END] Bronze layer completed | Total time={batch_duration:.2f}s"
    )
    print(f"Total Bronze Layer Time: {batch_duration:.2f} seconds.")
def main():
    run_bronze_pipeline()


if __name__ == "__main__":
    main()
