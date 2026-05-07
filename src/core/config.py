from __future__ import annotations
import yaml
from pathlib import Path
from typing import Any, Dict
from src.core.paths import get_project_root


def load_pipeline_config() -> Dict[str, Any]:
    """Load pipeline YAML configuration from configs/pipeline_config.yaml."""
    cfg_path = Path(get_project_root()) / "configs" / "pipeline_config.yaml"
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}