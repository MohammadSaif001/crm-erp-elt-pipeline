"""
Extract Module: CSV File Reader
--------------------------------
Centralized CSV reading functions for the extract layer.
Reads raw source files from data/raw/ with consistent settings.

Usage:
    from extract.read_csv_files import read_all_sources, read_source_file
"""
import os
import sys
import logging
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
python_folder = os.path.dirname(current_dir)
if python_folder not in sys.path:
    sys.path.append(python_folder)

from utils.paths import get_raw_data_path
from utils.config_loader import load_pipeline_config

logger = logging.getLogger(__name__)


def read_source_file(source_folder: str, file_name: str) -> pd.DataFrame:
    """
    Read a single CSV file from data/raw/<source_folder>/<file_name>.

    All columns are read as strings (bronze-layer convention).
    Column headers are stripped and lowercased.

    Args:
        source_folder: Sub-folder under data/raw/ (e.g. 'source_crm')
        file_name: CSV file name (e.g. 'cust_info.csv')

    Returns:
        pd.DataFrame with string-typed columns and normalized headers.

    Raises:
        FileNotFoundError: if the CSV does not exist.
    """
    relative = os.path.join(source_folder, file_name)
    csv_path = get_raw_data_path(relative)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Source CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype=str)
    df.columns = df.columns.str.strip().str.lower()

    logger.info(
        f"[EXTRACT] Read {file_name} from {source_folder} | "
        f"Shape: {df.shape}"
    )
    return df


def read_all_sources() -> dict[str, pd.DataFrame]:
    """
    Read all source files defined in pipeline_config.yaml → bronze.targets.

    Returns:
        dict mapping target table name → DataFrame.
        Example: {'crm_customers_info': DataFrame, ...}
    """
    config = load_pipeline_config()
    targets = config.get("bronze", {}).get("targets", [])

    if not targets:
        logger.warning("[EXTRACT] No targets found in pipeline_config.yaml")
        return {}

    dataframes = {}
    succeeded, failed = 0, 0

    for target in targets:
        name = target["name"]
        source = target["source"]
        file_name = target["file_name"]

        try:
            df = read_source_file(source, file_name)
            dataframes[name] = df
            succeeded += 1
        except Exception as e:
            logger.error(f"[EXTRACT] Failed to read {source}/{file_name}: {e}")
            failed += 1

    logger.info(
        f"[EXTRACT] Finished: {succeeded} succeeded, {failed} failed "
        f"out of {len(targets)} targets"
    )
    return dataframes


def get_source_file_info() -> list[dict]:
    """
    Return metadata about all source files (path, exists, row count).

    Returns:
        List of dicts with keys: name, source, file_name, path, exists, rows.
    """
    config = load_pipeline_config()
    targets = config.get("bronze", {}).get("targets", [])
    info = []

    for target in targets:
        relative = os.path.join(target["source"], target["file_name"])
        csv_path = get_raw_data_path(relative)
        exists = os.path.exists(csv_path)
        rows = None
        if exists:
            try:
                rows = sum(1 for _ in open(csv_path)) - 1  # minus header
            except Exception:
                rows = -1

        info.append({
            "name": target["name"],
            "source": target["source"],
            "file_name": target["file_name"],
            "path": csv_path,
            "exists": exists,
            "rows": rows,
        })

    return info


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n--- Source File Info ---")
    for f in get_source_file_info():
        icon = "✓" if f["exists"] else "✗"
        print(f"  {icon} {f['name']}: {f['file_name']} ({f['rows']} rows)")

    print("\n--- Reading All Sources ---")
    dfs = read_all_sources()
    for name, df in dfs.items():
        print(f"  {name}: {df.shape[0]} rows x {df.shape[1]} cols")
