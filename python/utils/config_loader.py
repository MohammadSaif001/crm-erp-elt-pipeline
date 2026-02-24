from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml

try:
    from python.utils.paths import get_project_root
except ModuleNotFoundError:
    import sys

    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from python.utils.paths import get_project_root


def load_pipeline_config() -> Dict[str, Any]:
    """Load pipeline YAML configuration from configs/pipeline_config.yaml."""
    cfg_path = Path(get_project_root()) / "configs" / "pipeline_config.yaml"
    with cfg_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}