from __future__ import annotations

import logging
from pathlib import Path

from .paths import get_logs_path


def setup_logger(name: str = "data_pipeline", level: int = logging.INFO) -> logging.Logger:
    """Centralized logger setup for the project."""
    log_path = Path(get_logs_path("pipeline.log"))
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.propagate = False
    return logger