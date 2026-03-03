import pandas as pd
import sys
import os
import logging
from sqlalchemy import text
from dq_checks.check_nulls import check_nulls, run_null_checks
from dq_checks.check_row_counts import get_row_counts, run_row_count_report
from dq_checks.check_duplicates import check_duplicates, run_duplicate_checks
from dq_checks.check_fk_integrity import check_fk_integrity, run_fk_integrity_report

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from utils.db_connection import get_engine

def check_data_slim():
    # Pandas settings for clean output
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    engine = get_engine("bronze")
    tables_to_check = ['crm_customers_info', 'crm_prd_info','crm_sales_details',
                       'erp_location_a101','erp_cust_az12','erp_px_cat_g1v2']

    for table in tables_to_check:
        print(f"\n{'='*60}")
        print(f"TABLE: {table.upper()} (Without Raw JSON)")
        print(f"{'='*60}")
        
        with engine.connect() as conn:
            # Query
            query = text(f"SELECT * FROM {table} LIMIT 5")
            df = pd.read_sql(query, conn)
            
            if df.empty:
                print("Table is empty!")
            else:
                
                if 'raw_row' in df.columns:
                    df_display = df.drop(columns=['raw_row'])
                else:
                    df_display = df
                
                print(df_display.to_string(index=False))
                print(f"\nTotal Rows: {len(df)}")

if __name__ == "__main__":
    check_data_slim()
    # Each returns True if all checks pass, False otherwise
    all_ok = run_row_count_report()
    no_dups = run_duplicate_checks("silver")
    no_nulls = run_null_checks("silver")
    fk_ok = run_fk_integrity_report()
