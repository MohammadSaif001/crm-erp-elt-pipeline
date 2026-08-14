from __future__ import annotations
import streamlit as st
from database.queries import compute_dq_score
from utils.helpers import humanize_check_detail
from components.report_shell import render_section_title, status_markup


def render_dq_summary_card() -> None:
    """Render compact DQ summary table for Home page or sidebar."""
    dq = compute_dq_score()
    score = dq.get("score", 0.0)
    failed = dq.get("failed_checks", 0)
    warnings = dq.get("warning_checks", 0)

    st.markdown(
        f"""
        <div style="border: 1px solid #000000; padding: 10px; background-color: #FFFFFF; font-size: 13px;">
            <b>Overall Data Quality:</b> {score:.1f}%<br>
            <b>Total Checks:</b> {dq.get('total_checks', 0)}<br>
            <b>Passed:</b> <span class="status-text-pass">{dq.get('passed_checks', 0)}</span><br>
            <b>Warnings:</b> {warnings}<br>
            <b>Failed:</b> <span class="{ 'status-text-fail' if failed > 0 else 'status-text-pass' }">{failed}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_full_dq_report(section_number: str = "04", include_attention: bool = True) -> None:
    """Render full DATA QUALITY REPORT as requested in Section 6."""
    dq = compute_dq_score()
    score = dq.get("score", 0.0)

    nulls = dq.get("null_checks")
    dupes = dq.get("duplicate_checks")
    fks = dq.get("fk_checks")
    counts = dq.get("row_count_checks")

    def category_status(frame, warning_on_failure: bool = False) -> str:
        if frame.empty or "passed" not in frame.columns:
            return "FAILED"
        if "status" in frame.columns and (frame["status"] == "FAILED").any():
            return "FAILED"
        if frame["passed"].all():
            return "PASS"
        return "WARNING" if warning_on_failure else "FAILED"

    null_status = category_status(nulls)
    duplicate_status = category_status(dupes, warning_on_failure=True)
    fk_status = category_status(fks)
    count_status = category_status(counts)
    duplicate_total = int(dupes["duplicate_keys"].fillna(0).sum()) if not dupes.empty and "duplicate_keys" in dupes else 0
    duplicate_detail = (
        "Duplicate query failed; result is unverified."
        if duplicate_status == "FAILED"
        else humanize_check_detail("duplicate", duplicate_status == "PASS", duplicate_total)
    )

    render_section_title(section_number, "DATA QUALITY", "Validation results explain whether data is fit for downstream use.")
    st.markdown(
        f"""
        <div class="report-note"><b>{dq.get('total_checks', 0)} checks executed</b><br>{dq.get('passed_checks', 0)} passed · {dq.get('warning_checks', 0)} warnings · {dq.get('failed_checks', 0)} failed. Quality score: {score:.1f}%.</div>
        <table class="report-table">
            <thead>
                <tr>
                    <th style="width: 35%;">Check Category</th>
                    <th style="width: 20%;">Result</th>
                    <th style="width: 45%;">Details</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><b>NULL checks</b></td>
                    <td>{status_markup(null_status)}</td>
                    <td>{humanize_check_detail('null', null_status == 'PASS')}</td>
                </tr>
                <tr>
                    <td><b>Duplicate checks</b></td>
                    <td>{status_markup(duplicate_status)}</td>
                    <td>{duplicate_detail}</td>
                </tr>
                <tr>
                    <td><b>FK integrity</b></td>
                    <td>{status_markup(fk_status)}</td>
                    <td>{humanize_check_detail('fk', fk_status == 'PASS')}</td>
                </tr>
                <tr>
                    <td><b>Row count checks</b></td>
                    <td>{status_markup(count_status)}</td>
                    <td>{humanize_check_detail('row_count', count_status == 'PASS')}</td>
                </tr>
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

    # Render ATTENTION REQUIRED block if any check failed or warned
    failed_items = []
    if not dupes.empty and "passed" in dupes.columns:
        failed_dupes = dupes[dupes["passed"] == False]
        for _, r in failed_dupes.iterrows():
            check_name = r.get("check", "")
            dupe_keys = r.get("duplicate_keys", 0)
            table_name = check_name.split(".")[0] if "." in check_name else check_name
            query_failed = r.get("status") == "FAILED"
            failed_items.append({
                "title": f"Duplicate query failed on {table_name}" if query_failed else f"Duplicate check found records on {table_name}",
                "expected": "A completed query with 0 duplicates",
                "found": "Query did not return a result" if query_failed else f"{dupe_keys} duplicate records",
                "action": "Verify database access and the duplicate check definition before rerunning the report." if query_failed else f"Review source export and primary key deduplication logic for {table_name} before the next production run.",
            })

    if not nulls.empty and "passed" in nulls.columns:
        failed_nulls = nulls[nulls["passed"] == False]
        for _, r in failed_nulls.iterrows():
            failed_items.append({
                "title": f"NULL check failed on {r.get('check', '')}",
                "expected": "0 null records",
                "found": f"{r.get('failed_rows', 0)} null records",
                "action": "Investigate upstream source pipeline missing mandatory field values.",
            })

    if failed_items and include_attention:
        render_section_title(str(int(section_number) + 1).zfill(2), "ATTENTION REQUIRED", "These checks need review before the next production run.")
        for item in failed_items:
            st.markdown(
                f"""
                <div class="action-box action-box--warning">
                    <b>{item['title']}</b><br>
                    <b>Expected:</b> {item['expected']}<br>
                    <b>Found:</b>    {item['found']}<br><br>
                    <b>Recommended action:</b><br>
                    {item['action']}
                </div>
                """,
                unsafe_allow_html=True,
            )
    elif include_attention:
        st.markdown(
            """
            <div class="action-box action-box--pass">
                <b>ATTENTION REQUIRED: None</b><br>
                All data quality checks passed cleanly. No manual action required.
            </div>
            """,
            unsafe_allow_html=True,
        )
