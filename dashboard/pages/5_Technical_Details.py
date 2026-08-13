"""
pages/5_Technical_Details.py
==============================================================================
TECHNICAL DETAILS & LOGS
Low-priority technical diagnostics, environment parameters, raw logs, and schema maps.
"""

from __future__ import annotations

import os

import streamlit as st

from components.sidebar import render_sidebar
from components.report_shell import apply_report_styles, render_footer, render_page_intro, render_section_title, render_site_header
from config import APP_SETTINGS, DB_SETTINGS, GOLD_SCHEMA
from utils.helpers import parse_pipeline_log, summarize_log_levels

st.set_page_config(
    page_title=f"{APP_SETTINGS.app_title} — Technical Details",
    page_icon=APP_SETTINGS.app_icon,
    layout=APP_SETTINGS.layout,
    initial_sidebar_state="expanded",
)

apply_report_styles()
render_sidebar()
render_site_header("05 / TECHNICAL DETAILS")

render_page_intro("05", "SYSTEM ENVIRONMENT & LOGS", "A detailed operational view of the ELT runtime, database connections, configuration, and execution log.")

# 1. System & Environment Table
render_section_title("01", "SYSTEM ENVIRONMENT")
st.markdown(
    f"""
    <table class="report-table">
        <tbody>
            <tr>
                <td style="width: 35%;"><b>Pipeline Log File Path</b></td>
                <td style="width: 65%;"><code>{APP_SETTINGS.log_file_path}</code></td>
            </tr>
            <tr>
                <td><b>Database Host</b></td>
                <td><code>{DB_SETTINGS.host}:{DB_SETTINGS.port}</code></td>
            </tr>
            <tr>
                <td><b>Bronze Database</b></td>
                <td><code>{DB_SETTINGS.bronze_db}</code></td>
            </tr>
            <tr>
                <td><b>Silver Database</b></td>
                <td><code>{DB_SETTINGS.silver_db}</code></td>
            </tr>
            <tr>
                <td><b>Gold Database</b></td>
                <td><code>{DB_SETTINGS.gold_db}</code></td>
            </tr>
            <tr>
                <td><b>Dashboard Cache TTL</b></td>
                <td>{APP_SETTINGS.cache_ttl_seconds} seconds</td>
            </tr>
            <tr>
                <td><b>Maximum Log Lines Parsed</b></td>
                <td>{APP_SETTINGS.max_log_lines} lines</td>
            </tr>
        </tbody>
    </table>
    """,
    unsafe_allow_html=True,
)

# 2. Log File Viewer with Level Filter
render_section_title("02", "PIPELINE LOG", "Filter the parsed operational events without changing the original log file.")

records = parse_pipeline_log(max_lines=1000)
level_counts = summarize_log_levels(records)

st.markdown(
    f'''<div class="log-summary">
        <span>{level_counts["INFO"]} INFO EVENTS</span>
        <span>{level_counts["WARNING"]} WARNING EVENTS</span>
        <span>{level_counts["ERROR"]} ERROR EVENTS</span>
        <span>{len(records)} TOTAL RECORDS</span>
    </div>''',
    unsafe_allow_html=True,
)

filter_level = st.selectbox("Filter Log Level:", ["ALL", "INFO", "WARNING", "ERROR"], index=0)

filtered_records = records
if filter_level != "ALL":
    filtered_records = [r for r in records if r.get("level", "").upper() == filter_level]

log_lines = []
for r in filtered_records:
    ts = r.get("timestamp", "")
    lvl = r.get("level", "INFO")
    mod = r.get("module", "")
    msg = r.get("message", "")
    log_lines.append(f"{ts} | {lvl:<7} | {mod:<15} | {msg}")

log_text = "\n".join(log_lines) if log_lines else "No matching log records found."
st.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)

# 3. Gold Schema Map Definition
with st.expander("GOLD SCHEMA DEFINITION MAP", expanded=False):
    st.caption("Star Schema Table & Column Mapping Configuration:")
    for view_name, cols in GOLD_SCHEMA.items():
        st.markdown(f"**{view_name}** ({len(cols)} columns):")
        st.code(", ".join(cols), language="text")
render_footer()
