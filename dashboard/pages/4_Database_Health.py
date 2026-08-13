"""
pages/4_Database_Health.py
==============================================================================
DATABASE HEALTH REPORT
Connection status, server parameters, and medallion table statistics.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

from components.sidebar import render_sidebar
from components.report_shell import apply_report_styles, render_footer, render_page_intro, render_section_title, render_site_header
from config import APP_SETTINGS, DB_SETTINGS
from database.connection import test_connection
from database.queries import get_row_counts
from utils.helpers import format_number

st.set_page_config(
    page_title=f"{APP_SETTINGS.app_title} — Database Health",
    page_icon=APP_SETTINGS.app_icon,
    layout=APP_SETTINGS.layout,
    initial_sidebar_state="expanded",
)

apply_report_styles()
render_sidebar()
render_site_header("04 / DATABASE HEALTH")

render_page_intro("04", "DATABASE HEALTH", "Connectivity and inventory across the Bronze, Silver, and Gold data stores.")

# 1. Connection Status Table
render_section_title("01", "DATABASE CONNECTION STATUS", "All three layers must be reachable before a run can be considered healthy.")
db_info = [
    ("Bronze Database", DB_SETTINGS.bronze_db, "Raw Ingestion Storage"),
    ("Silver Database", DB_SETTINGS.silver_db, "Cleaned & Normalized Storage"),
    ("Gold Database", DB_SETTINGS.gold_db, "Star-Schema Business Views"),
]

connection_rows = []
for label, db_name, desc in db_info:
    ok, msg = test_connection(db_name)
    connection_rows.append({"Database": db_name, "Status": "✓ PASS" if ok else "× FAILED",
                            "Host": f"{DB_SETTINGS.host}:{DB_SETTINGS.port}",
                            "Notes": desc if ok else f"Connection error: {msg}"})
st.dataframe(pd.DataFrame(connection_rows), use_container_width=True, hide_index=True)

# 2. Server Configuration Table
render_section_title("02", "SERVER & DRIVER CONFIGURATION")
st.dataframe(pd.DataFrame([
    {"Parameter": "Database host", "Value": DB_SETTINGS.host},
    {"Parameter": "Database port", "Value": DB_SETTINGS.port},
    {"Parameter": "Database user", "Value": DB_SETTINGS.user},
    {"Parameter": "Driver / protocol", "Value": "PyMySQL / mysql+pymysql"},
    {"Parameter": "Cache TTL", "Value": f"{APP_SETTINGS.cache_ttl_seconds} seconds"},
]), use_container_width=True, hide_index=True)

# 3. Layer Table Statistics
render_section_title("03", "MEDALLION TABLE INVENTORY", "Table counts are live database observations, not estimates.")
row_counts_df = get_row_counts()

if not row_counts_df.empty:
    inventory_rows = []
    for _, r in row_counts_df.iterrows():
        layer = r["layer"]
        table = r["table"]
        rows = int(r["row_count"])
        inventory_rows.append({"Layer": layer, "Table / View": table,
                               "Rows": format_number(rows),
                               "Health": "✓ AVAILABLE" if rows > 0 else "× EMPTY"})
    st.dataframe(pd.DataFrame(inventory_rows), use_container_width=True, hide_index=True)
else:
    st.warning("Could not query medallion table inventory from database.")
render_footer()
