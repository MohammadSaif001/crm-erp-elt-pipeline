"""
pages/2_Pipeline_Run.py
==============================================================================
PIPELINE RUN REPORT
Detailed execution metrics, stage timings, and execution logs.
"""

from __future__ import annotations

import streamlit as st

from components.sidebar import render_sidebar
from components.report_shell import apply_report_styles, render_footer, render_page_intro, render_section_title, render_site_header, status_markup
from config import APP_SETTINGS
from utils.helpers import extract_batch_timings, get_latest_run_details, parse_pipeline_log

st.set_page_config(
    page_title=f"{APP_SETTINGS.app_title} — Pipeline Run",
    page_icon=APP_SETTINGS.app_icon,
    layout=APP_SETTINGS.layout,
    initial_sidebar_state="expanded",
)

apply_report_styles()
render_sidebar()
render_site_header("02 / PIPELINE RUN")

run_info = get_latest_run_details()

render_page_intro("02", "PIPELINE RUN", "A detailed view of the latest execution: when it ran, what completed, and which events need review.")

# Run Overview Table
render_section_title("01", "LATEST RUN METRICS")
st.markdown(
    f"""
    <table class="report-table">
        <tbody>
            <tr>
                <td style="width: 30%;"><b>Execution Status</b></td>
                <td style="width: 70%;">{status_markup(run_info.get('status', 'SUCCESS'))}</td>
            </tr>
            <tr>
                <td><b>Start Timestamp</b></td>
                <td><code>{run_info.get('start_time', 'Not available')}</code></td>
            </tr>
            <tr>
                <td><b>Finish Timestamp</b></td>
                <td><code>{run_info.get('end_time', 'Not available')}</code></td>
            </tr>
            <tr>
                <td><b>Duration</b></td>
                <td><code>{run_info.get('duration', 'Not available')}</code></td>
            </tr>
            <tr>
                <td><b>Log File Path</b></td>
                <td><code>{APP_SETTINGS.log_file_path}</code></td>
            </tr>
            <tr>
                <td><b>Result Summary</b></td>
                <td>{run_info.get('result_summary', 'Pipeline completed.')}</td>
            </tr>
        </tbody>
    </table>
    """,
    unsafe_allow_html=True,
)

# Stage Timing Breakdown Table
render_section_title("02", "STAGE TIMING BREAKDOWN", "Recorded batch completion times from the latest run.")
timings = run_info.get("timings", [])

if timings:
    table_rows = ""
    for t in timings:
        table_rows += f"""
        <tr>
            <td><b>{t['stage']}</b></td>
            <td><code>{t['duration_seconds']:.2f}s</code></td>
            <td><code>{t['timestamp']}</code></td>
        </tr>
        """
    st.markdown(
        f"""
        <table class="report-table">
            <thead>
                <tr>
                    <th style="width: 40%;">Pipeline Stage / Table</th>
                    <th style="width: 30%;">Duration</th>
                    <th style="width: 30%;">Timestamp</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("No detailed stage batch timings recorded for the latest run.")

# Raw Log Output for Latest Run
render_section_title("03", "EXECUTION LOG", "Raw operational events from the latest logged run.")
raw_records = run_info.get("raw_records", [])
if raw_records:
    log_text = "\n".join(
        f"{r.get('timestamp','')} | {r.get('level','INFO')} | {r.get('module','')} | {r.get('message','')}"
        for r in raw_records
    )
    st.markdown(f'<div class="log-box">{log_text}</div>', unsafe_allow_html=True)
else:
    st.info("No log events found for the latest run.")
render_footer()
