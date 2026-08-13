"""
app.py
==============================================================================
Entry point for the ELT Data Engineering Pipeline Analytics Dashboard.

Run with:
    streamlit run app.py

Streamlit's native multi-page routing (the `pages/` directory) drives
navigation — this file renders the landing redirect plus global logging
setup shared across every page.
"""

from __future__ import annotations

import logging

import streamlit as st

from config import APP_SETTINGS

# --------------------------------------------------------------------------
# Global logging configuration (applies to every module in the app)
# --------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("dashboard")

st.set_page_config(
    page_title="ELT Pipeline Health",
    page_icon=APP_SETTINGS.app_icon,
    layout=APP_SETTINGS.layout,
    initial_sidebar_state="expanded",
)

logger.info("Dashboard app booted — redirecting to Home page")

# Streamlit's multipage app auto-discovers everything under pages/. This
# top-level app.py acts as the default entry; we forward straight to the
# Home page so `streamlit run app.py` lands on a fully rendered dashboard
# rather than a blank router page.
try:
    st.switch_page("pages/1_Home.py")
except Exception:  # noqa: BLE001 — older Streamlit versions without switch_page
    st.title(f"{APP_SETTINGS.app_icon} {APP_SETTINGS.app_title}")
    st.info("Use the sidebar navigation to open the **Home** page and explore the dashboard.")
