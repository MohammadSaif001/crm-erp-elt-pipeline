import logging
import time
from functools import wraps
"""
Module containing helper functions and decorators for loading data into 
the bronze layer database,
including logging functionalities and it is genareated by AI tool.
i have less idea how this script is work specailly @wraps part..I have
researched and found that it is used to preserve the metadata of the original function when creating decorators.
"""
def log_load(table_name:str):
    """ Decorator to log the loading process of tables."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logging.info(f"Starting to load table: {table_name}")
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            logging.info(f"Finished loading table: {table_name} in {end_time - start_time:.2f} seconds")
            return result
        return wrapper
    return decorator    