import os
import logging
import pandas as pd
from sqlalchemy  import text

logger = logging.getLogger(__name__)


# PROJECT_ROOT = os.path.abspath(
#     os.path.join(os.path.dirname(__file__), "..", "..")
# )

# PROCESSED_FILE = os.path.join(
#     PROJECT_ROOT,
#     "data",
#     "processed",
#     "processed_files.csv"
# )

# def is_file_processed(source, file_name, bronze_table):
#     """
#     Check whether a (source, file, table) combination
#     has already been ingested into bronze.
#     """
#     if not os.path.exists(PROCESSED_FILE):
#         return False

#     if os.path.getsize(PROCESSED_FILE) == 0:
#         return False

#     try:
#         df = pd.read_csv(PROCESSED_FILE)
    
#     except pd.errors.EmptyDataError:
#         return False

#     return (
#         (df["source"].str.lower().str.strip() == source.lower().strip()) &
#         (df["file_name"].str.lower().str.strip() == file_name.lower().strip()) &
#         (df["bronze_table"].str.lower().str.strip() == bronze_table.lower().strip())
#     ).any()


# def mark_file_processed(source, file_name, bronze_table):
#     """
#     Mark a file as processed after successful bronze load.
#     """
#     row = pd.DataFrame(
#         [[source, file_name, bronze_table]],
#         columns=["source", "file_name", "bronze_table"]
#     )
#     logger.info(f"Marking file as processed: Table={bronze_table}")
#     os.makedirs(os.path.dirname(PROCESSED_FILE), exist_ok=True)

#     if os.path.exists(PROCESSED_FILE) and os.path.getsize(PROCESSED_FILE) > 0:
#         row.to_csv(PROCESSED_FILE, mode="a", header=False, index=False)
#     else:
#         row.to_csv(PROCESSED_FILE, index=False)


def is_hash_processed(engine, file_hash):

    query   = text(""" 
                    SELECT COUNT(*) 
        FROM ingestion_log
        WHERE file_hash = :file_hash
    """)

    with engine.connect() as connection:
        result = connection.execute(
               query, 
               {"file_hash": file_hash})
        count = result.scalar()
    return count > 0

def log_ingestion(
        engine,
        source_name: str,
        file_name: str,
        file_hash: str,
        row_count: int):
    
    insert_query = text("""
                        INSERT INTO  ingestion_log(
                        source_name,
                        file_name,
                        file_hash,
                        row_count)

                        VALUES (
                        :source_name,
                        :file_name,
                        :file_hash,
                        :row_count)
                     """)
    with engine.connect() as connection:
        connection.execute(
            insert_query,
            {
                "source_name": source_name,
                "file_name": file_name,
                "file_hash": file_hash,
                "row_count": row_count
            }
        )
        connection.commit()