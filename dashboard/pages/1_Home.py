"""
pages/1_Home.py
==============================================================================
ELT PIPELINE HEALTH REPORT (Home Page)
Operational health report for production pipeline monitoring.
"""

from __future__ import annotations

from html import escape

import streamlit as st
import pandas as pd

from components.dq_score import render_full_dq_report
from components.pipeline_status import (
    compute_overall_pipeline_status,
    render_latest_run_report,
    render_medallion_table,
    render_pipeline_status_banner,
    render_pipeline_summary_table,
)
from components.sidebar import render_sidebar
from components.report_shell import apply_report_styles, render_footer, render_section_title, render_site_header
from config import APP_SETTINGS, DB_SETTINGS
from database.connection import test_connection

st.set_page_config(
    page_title="ELT Pipeline Health",
    page_icon=APP_SETTINGS.app_icon,
    layout=APP_SETTINGS.layout,
    initial_sidebar_state="expanded",
)

apply_report_styles()
render_sidebar()
render_site_header("01 / HOME")

# Compute live pipeline health metrics
health_info = compute_overall_pipeline_status()

# 1. Pipeline Health Status Banner & Human-readable Explanation
render_pipeline_status_banner(health_info)

# 2. Executive Pipeline Summary Table
render_pipeline_summary_table(health_info)

# 3. Pipeline architecture and live data flow
render_medallion_table()

# 4. Data quality report; action is summarized once at the end of the Home page.
render_full_dq_report(section_number="04", include_attention=False)

# 6. Database Health
render_section_title("05", "DATABASE HEALTH", "Reachability is checked against each configured pipeline database.")
db_rows = []
for db_name, label in [("bronze_db", "Bronze DB"), ("silver_db", "Silver DB"), ("gold_db", "Gold DB")]:
    ok, msg = test_connection(db_name)
    db_rows.append({
        "Database": db_name,
        "Status": "✓ PASS" if ok else "× FAILED",
        "Notes": "Connection successful (localhost:3306)" if ok else f"Connection error: {msg}"
    })

st.dataframe(pd.DataFrame(db_rows), use_container_width=True, hide_index=True)

if not health_info["dbs_ok"]:
    st.markdown("""
        <div class="action-box action-box--fail">
            <b>Database Outage Notice:</b> One or more pipeline databases are unavailable. The Gold layer could not be verified.
        </div>
    """, unsafe_allow_html=True)

# 6. Latest execution narrative
render_latest_run_report(health_info)

# 7. Warnings / Recommended Actions
render_section_title("07", "ATTENTION REQUIRED")
if health_info["warnings_count"] > 0 or health_info["failed_checks"] > 0:
    dq = health_info["dq_summary"]
    duplicate_rows = dq.get("duplicate_checks")
    duplicate_messages = []
    if not duplicate_rows.empty:
        for _, result in duplicate_rows[duplicate_rows["passed"] == False].iterrows():
            check = escape(str(result.get("check", "duplicate check")))
            if result.get("status") == "FAILED":
                duplicate_messages.append(f"{check}: query did not complete.")
            else:
                duplicate_messages.append(f"{check}: {int(result.get('duplicate_keys', 0))} duplicate records found.")
    reason = " ".join(duplicate_messages) or (
        f"{dq.get('failed_checks', 0)} runtime check(s) failed and {dq.get('warning_checks', 0)} warning(s) were recorded."
    )
    st.markdown(
        f"""
        <div class="action-box action-box--warning">
            <b>Review required.</b><br>
            {reason}<br><br>
            Review the live Data Quality results before the next production execution.
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div class="action-box action-box--pass">
            <b>No action required.</b><br>
            The latest pipeline run completed successfully and all critical checks passed.
        </div>
        """,
        unsafe_allow_html=True,
    )

render_section_title("08", "TECHNICAL DETAILS", "Logs, runtime configuration, and schema references are kept secondary to this health report.")
st.page_link("pages/5_Technical_Details.py", label="Open technical details and execution logs →")

render_footer()
