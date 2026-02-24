import os

def get_project_root():
    """Returns the absolute path to the root 'data_engineering_project' folder.
       - Current file: .../python/utils/paths.py
       - utils -> python -> data_engineering_project
    # """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    return project_root

def get_config_path():
    """Returns absolute path to configs/db_config.json"""
    return os.path.join(get_project_root(), "configs", "db_config.json")

def get_raw_data_path(relative_path):
    """
    Returns absolute path to a file inside data/raw/
    Example: get_raw_data_path('source_crm/cust_info.csv') 
    -> .../data_engineering_project/data/raw/source_crm/cust_info.csv
    """
    return os.path.join(get_project_root(), "data", "raw", relative_path)

def get_logs_path(relative_path):
    """Returns absolute path to a file inside data/logs/."""
    return os.path.join(get_project_root(), "data", "logs", relative_path)