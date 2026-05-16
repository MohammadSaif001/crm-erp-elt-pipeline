from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CONFIG_DIR = PROJECT_ROOT / "configs"
DATA_DIR = PROJECT_ROOT / "data"

RAW_DATA_DIR = DATA_DIR / "raw"
LOG_DIR = DATA_DIR / "logs"
PROCESSED_DIR = DATA_DIR / "processed"



def get_raw_data_path(filename: str) -> Path:
    """
    # Returns the absolute path to a raw data file in the data/raw directory."""
    return RAW_DATA_DIR / filename

def get_project_root() -> Path:
    """
    # Returns the absolute path to the root 'data_engineering_project' folder."""
    return PROJECT_ROOT

def get_logs_path(filename: str) -> Path:
    """
    # Returns the absolute path to a log file in the data/logs directory."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / filename


def get_config_path()-> Path:
    """Returns absolute path to configs/db_config.json"""
    return get_project_root() / "configs" / "db_config.json"
