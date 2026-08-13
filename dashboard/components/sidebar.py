"""
components/sidebar.py
==============================================================================
Renders the simple corporate sidebar: application title, database status,
and the [ Refresh Pipeline Report ] button.
"""

from __future__ import annotations

import streamlit as st

from config import APP_SETTINGS, DB_SETTINGS
from database.connection import test_connection
from utils.cache import bump_last_refresh, clear_all_caches, get_last_refresh_key
from components.report_shell import status_markup


def render_sidebar() -> None:
    """Render the simple internal sidebar shared across pages."""
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">ELT<br><strong>PIPELINE HEALTH</strong></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">REPORT INDEX</div>', unsafe_allow_html=True)
        for label, path in [
            ("01  Home", "pages/1_Home.py"),
            ("02  Pipeline Run", "pages/2_Pipeline_Run.py"),
            ("03  Data Quality", "pages/3_Data_Quality.py"),
            ("04  Database Health", "pages/4_Database_Health.py"),
            ("05  Technical Details", "pages/5_Technical_Details.py"),
        ]:
            st.page_link(path, label=label)

        st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">SYSTEM STATUS</div>', unsafe_allow_html=True)

        st.markdown("#### Database Status")
        _render_db_status()

        st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-label">LAST REFRESH</div>', unsafe_allow_html=True)
        last_refreshed = get_last_refresh_key()
        st.markdown(f'<div class="sidebar-time">{last_refreshed}</div>', unsafe_allow_html=True)
        if st.button("[ Refresh Pipeline Report ]", use_container_width=True):
            clear_all_caches()
            bump_last_refresh()
            st.rerun()

        st.markdown('<div class="sidebar-rule"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-foot">INTERNAL OPERATIONS<br>BRONZE → SILVER → GOLD</div>', unsafe_allow_html=True)


def _render_db_status() -> None:
    """Render plain connection status for each database layer."""
    databases = [
        ("Bronze DB", DB_SETTINGS.bronze_db),
        ("Silver DB", DB_SETTINGS.silver_db),
        ("Gold DB", DB_SETTINGS.gold_db),
    ]

    for label, db_name in databases:
        ok, msg = test_connection(db_name)
        if ok:
            st.markdown(f"<div class='sidebar-status'><span>● {label}</span>{status_markup('PASS')}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='sidebar-status'><span>● {label}</span>{status_markup('FAILED')}</div>", unsafe_allow_html=True)
            with st.expander("Connection error", expanded=False):
                st.code(msg, language="text")
