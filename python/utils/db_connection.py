# File: python/utils/db_connection.py
import json
import logging
import os
from sqlalchemy import create_engine
from urllib.parse import quote_plus

try:
    from .paths import get_config_path, get_project_root
except ImportError:
    from utils.paths import get_config_path, get_project_root

def load_config():
   
    config_path = get_config_path()
    rel_config_path = os.path.relpath(config_path, get_project_root())
    
    
    logging.info(f"Loading config from: {rel_config_path}")

    with open(config_path, "r") as file:
        return json.load(file)

def get_engine(layer="bronze"):
    full_config = load_config()
    
    # Ensure 'mysql' key exists
    if 'mysql' not in full_config:
        raise KeyError("'mysql' section missing in db_config.json")

    cfg = full_config['mysql']
    
    user = cfg['user']
    pwd = cfg['password']
    host = cfg['host']
    port = cfg.get('port', 3306)
    
    db_map = {
        "bronze": cfg['bronze_db'],
        "silver": cfg['silver_db'],
        "gold": cfg['gold_db']
    }
    
    if layer not in db_map:
        raise ValueError(f"Unknown layer: {layer}")
        
    dbname = db_map[layer]
    pwd_quoted = quote_plus(pwd)
    
    url = f"mysql+pymysql://{user}:{pwd_quoted}@{host}:{port}/{dbname}"
    
    return create_engine(url, pool_pre_ping=True)