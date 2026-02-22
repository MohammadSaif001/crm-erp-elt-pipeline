import pandas as pd
import sys
import os
from sqlalchemy import text

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
    tables_to_check = ['crm_customers_info', 'crm_prd_info']

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
                print(f"\n Total Rows: {len(df)}")

if __name__ == "__main__":
    check_data_slim()
