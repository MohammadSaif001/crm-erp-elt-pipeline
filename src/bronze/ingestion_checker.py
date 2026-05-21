import os
import logging
import pandas as pd
from sqlalchemy  import text

logger = logging.getLogger(__name__)





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