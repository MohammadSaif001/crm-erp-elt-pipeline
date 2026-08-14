from __future__ import annotations
import streamlit as st
from components.sidebar import render_sidebar
from components.report_shell import apply_report_styles, render_footer, render_page_intro, render_section_title, render_site_header, status_markup
from config import APP_SETTINGS
from database.queries import compute_dq_score
from utils.helpers import format_number, humanize_check_detail, humanize_check_name

st.set_page_config(
    page_title=f"{APP_SETTINGS.app_title} — Data Quality",
    page_icon=APP_SETTINGS.app_icon,
    layout=APP_SETTINGS.layout,
    initial_sidebar_state="expanded",
)

apply_report_styles()
render_sidebar()
render_site_header("03 / DATA QUALITY")

dq = compute_dq_score()
score = dq.get("score", 0.0)

render_page_intro("03", "DATA QUALITY", "Field validation, referential integrity, deduplication, and row-count checks for the current data estate.")

# DQ Overview Table
render_section_title("01", "QUALITY SCORE OVERVIEW")
st.markdown(
    f"""
    <table class="report-table">
        <tbody>
            <tr>
                <td style="width: 40%;"><b>Overall Quality Score</b></td>
                <td style="width: 60%;"><b>{score:.1f}%</b></td>
            </tr>
            <tr>
                <td><b>Total Checks Evaluated</b></td>
                <td>{dq.get('total_checks', 0)}</td>
            </tr>
            <tr>
                <td><b>Passed Checks</b></td>
                <td><span class="status-text-pass"><b>{dq.get('passed_checks', 0)}</b></span></td>
            </tr>
            <tr><td><b>Warnings</b></td><td><b>{dq.get('warning_checks', 0)}</b></td></tr>
            <tr><td><b>Failed Checks</b></td><td><b>{dq.get('failed_checks', 0)}</b></td></tr>
        </tbody>
    </table>
    """,
    unsafe_allow_html=True,
)

# NULL Checks Table
render_section_title("02", "NULL CHECK RESULTS")
nulls = dq.get("null_checks")
if not nulls.empty:
    rows_html = ""
    for _, r in nulls.iterrows():
        passed = bool(r.get("passed", True))
        status_cls = "status-text-pass" if passed else "status-text-fail"
        rows_html += f"""
        <tr>
            <td><b>{humanize_check_name(str(r.get('check', '')))}</b></td>
            <td>{format_number(r.get('total_rows', 0))}</td>
            <td>{format_number(r.get('failed_rows', 0))}</td>
            <td><span class="{status_cls}"><b>{'PASS' if passed else 'FAILED'}</b></span></td>
        </tr>
        """
    st.markdown(
        f"""
        <table class="report-table">
            <thead>
                <tr>
                    <th style="width: 40%;">Check Target</th>
                    <th style="width: 20%;">Total Rows</th>
                    <th style="width: 20%;">Null Violations</th>
                    <th style="width: 20%;">Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("No NULL check results available.")

# Duplicate Checks Table
render_section_title("03", "DUPLICATE CHECK RESULTS")
dupes = dq.get("duplicate_checks")
if not dupes.empty:
    rows_html = ""
    for _, r in dupes.iterrows():
        passed = bool(r.get("passed", True))
        status = str(r.get("status", "PASS" if passed else "WARNING"))
        rows_html += f"""
        <tr>
            <td><b>{humanize_check_name(str(r.get('check', '')))}</b></td>
            <td>{format_number(r.get('duplicate_keys', 0))}</td>
            <td>{status_markup(status)}</td>
        </tr>
        """
    st.markdown(
        f"""
        <table class="report-table">
            <thead>
                <tr>
                    <th style="width: 50%;">Check Target</th>
                    <th style="width: 25%;">Duplicate Keys</th>
                    <th style="width: 25%;">Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("No duplicate check results available.")

# Foreign Key Integrity Table
render_section_title("04", "FOREIGN KEY INTEGRITY RESULTS")
fks = dq.get("fk_checks")
if not fks.empty:
    rows_html = ""
    for _, r in fks.iterrows():
        passed = bool(r.get("passed", True))
        status_cls = "status-text-pass" if passed else "status-text-fail"
        rows_html += f"""
        <tr>
            <td><b>{humanize_check_name(str(r.get('check', '')))}</b></td>
            <td>{format_number(r.get('orphaned_rows', 0))}</td>
            <td><span class="{status_cls}"><b>{'PASS' if passed else 'FAILED'}</b></span></td>
        </tr>
        """
    st.markdown(
        f"""
        <table class="report-table">
            <thead>
                <tr>
                    <th style="width: 50%;">Relationship Check</th>
                    <th style="width: 25%;">Orphaned Rows</th>
                    <th style="width: 25%;">Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("No foreign key check results available.")

# Row Count Validation
render_section_title("05", "TABLE ROW COUNT CHECKS")
counts = dq.get("row_count_checks")
if not counts.empty:
    rows_html = ""
    for _, r in counts.iterrows():
        passed = bool(r.get("passed", True))
        status_cls = "status-text-pass" if passed else "status-text-fail"
        rows_html += f"""
        <tr>
            <td><b>{r.get('layer', '')}</b></td>
            <td><code>{r.get('table', '')}</code></td>
            <td>{format_number(r.get('row_count', 0))}</td>
            <td><span class="{status_cls}"><b>{'PASS' if passed else 'FAILED'}</b></span></td>
        </tr>
        """
    st.markdown(
        f"""
        <table class="report-table">
            <thead>
                <tr>
                    <th style="width: 20%;">Layer</th>
                    <th style="width: 40%;">Table Name</th>
                    <th style="width: 20%;">Row Count</th>
                    <th style="width: 20%;">Status</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

# Action Items Block
if dq.get("failed_checks", 0) > 0:
    st.markdown(
        """
        <div class="section-heading"><span>06 / RECOMMENDED ACTION</span></div>
        <div class="action-box action-box--warning">
            <b>Attention required.</b><br>
            Review the failing rows above before the next production execution. The displayed counts are queried from the current report.
        </div>
        """,
        unsafe_allow_html=True,
    )
render_footer()
