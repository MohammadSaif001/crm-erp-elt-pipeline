"""FastAPI entry point for the dashboard."""

from __future__ import annotations

if __package__:
    from .main import app
else:  # Support launches from inside the dashboard directory.
    import sys
    from pathlib import Path

    dashboard_dir = Path(__file__).resolve().parent
    if str(dashboard_dir) not in sys.path:
        sys.path.insert(0, str(dashboard_dir))
    from main import app

__all__ = ["app"]
