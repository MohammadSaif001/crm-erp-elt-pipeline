from pathlib import Path

def get_project_root()-> Path:
    """Returns the absolute path to the root 'data_engineering_project' folder.
       - Current file: .../python/utils/paths.py
       - utils -> python -> data_engineering_project
    # """
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent
    return project_root

def get_config_path()-> Path:
    """Returns absolute path to configs/db_config.json"""
    return get_project_root() / "configs" / "db_config.json"

def get_raw_data_path(relative_path: str)-> Path:
    """
    Returns absolute path to a file inside data/raw/
    Example: get_raw_data_path('source_crm/cust_info.csv') 
    -> .../data_engineering_project/data/raw/source_crm/cust_info.csv
    """
    return get_project_root() / "data" / "raw" / relative_path

def get_logs_path(relative_path: str)-> Path:
    """Returns absolute path to a file inside data/logs/.
    Creates the logs directory if it does not exist."""
    logs_dir = get_project_root() / "data" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / relative_path