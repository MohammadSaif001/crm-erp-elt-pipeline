import os
import json
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from urllib.parse import quote_plus
from src.core.paths import get_config_path, get_project_root


logger = logging.getLogger(__name__)

def load_config():
   
    config_path = get_config_path()
    rel_config_path = os.path.relpath(config_path, get_project_root())
    
    
    logging.info(f"Loading config from: {rel_config_path}")

    with open(config_path, "r") as file:
        return json.load(file)


def _create_database(cfg: dict, dbname: str) -> None:
    """
    Create a database if it doesn't exist.
    Uses admin connection (no database specified).
    """
    try:
        user = cfg['user']
        pwd = cfg['password']
        host = cfg['host']
        port = cfg.get('port', 3306)
        
        pwd_quoted = quote_plus(pwd)
        # Admin connection without specifying a database
        admin_url = f"mysql+pymysql://{user}:{pwd_quoted}@{host}:{port}/"
        admin_engine = create_engine(admin_url, pool_pre_ping=True)
        
        with admin_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {dbname};"))
            conn.commit()
            logger.info(f"✓ Database '{dbname}' created/verified successfully")
            
    except Exception as e:
        logger.error(f"Failed to create database '{dbname}': {e}")
        raise


def get_engine(layer="bronze"):
    """
    # Get SQLAlchemy engine for the specified layer (bronze, silver, gold).
    - Get SQLAlchemy engine for specified layer.
    - Automatically creates database if it doesn't exist on first connection.
    """
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
    
    try:
        # Try to create engine and test connection
        engine = create_engine(url, pool_pre_ping=True)
        # Test the connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        logger.info(f"Connected to {layer} database: {dbname}")
        return engine
        
    except OperationalError as e:
        # Database likely doesn't exist
        logger.warning(f"Database '{dbname}' not found or connection failed. Attempting to create...")
        
        try:
            # Create the database
            _create_database(cfg, dbname)
            
            # Create a new engine and test connection
            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            logger.info(f"Successfully connected to newly created {layer} database: {dbname}")
            return engine
            
        except Exception as create_error:
            logger.error(f"Failed to create and connect to database '{dbname}': {create_error}")
            raise