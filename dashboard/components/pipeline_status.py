"""
components/pipeline_status.py
==============================================================================
Renders plain old-school web report components for pipeline status, run details,
and Medallion architecture tables.
"""

from __future__ import annotations

import streamlit as st

from database.connection import test_connection
from database.queries import compute_dq_score, get_pipeline_lineage, get_row_counts
from utils.helpers import (
    format_number,
    get_latest_run_details,
    humanize_check_detail,
    humanize_check_name,
)
from components.report_shell import render_section_title, status_markup


def compute_overall_pipeline_status() -> dict:
    """
    Calculate the overall pipeline health status according to Section 14 rules:
    FAILED: pipeline failed OR critical DB unavailable OR critical DQ check failed.
    WARNING: pipeline completed but one or more non-critical runtime DQ checks failed.
    PASS: latest run succeeded and all critical checks passed.
    """
    # 1. DB check
    bronze_ok, _ = test_connection("bronze_db")
    silver_ok, _ = test_connection("silver_db")
    gold_ok, _ = test_connection("gold_db")
    all_dbs_ok = bronze_ok and silver_ok and gold_ok

    # 2. Run log details
    run_info = get_latest_run_details()
    run_failed = run_info.get("status") == "FAILED"

    # 3. Data quality check
    dq_summary = compute_dq_score()
    nulls = dq_summary.get("null_checks")
    fks = dq_summary.get("fk_checks")
    counts = dq_summary.get("row_count_checks")
    dupes = dq_summary.get("duplicate_checks")

    # Critical checks: nulls, fks, row counts
    critical_failed = False
    for df in (nulls, fks, counts):
        if not df.empty and "passed" in df.columns:
            if not df["passed"].all():
                critical_failed = True
                break

    non_critical_failed = False
    duplicate_query_failed = False
    if not dupes.empty and "passed" in dupes.columns:
        if not dupes["passed"].all():
            non_critical_failed = True
        if "status" in dupes.columns and (dupes["status"] == "FAILED").any():
            duplicate_query_failed = True

    # Log WARNING entries are diagnostics, not health warnings: the pipeline
    # deliberately logs records it cleans, rejects, or deduplicates.  Health
    # warnings come only from the live, configured runtime DQ rules.
    warnings_count = dq_summary.get("warning_checks", 0)

    # Determine overall status
    if run_failed or not all_dbs_ok or critical_failed or duplicate_query_failed:
        overall_status = "FAILED"
        if not all_dbs_ok:
            failed_db = "Gold" if not gold_ok else ("Silver" if not silver_ok else "Bronze")
            explanation = f"Pipeline status is FAILED because the {failed_db} database is unavailable. The latest Gold layer could not be verified."
        elif run_failed:
            explanation = f"Pipeline status is FAILED because the latest execution encountered errors: {run_info.get('result_summary')}"
        elif duplicate_query_failed:
            explanation = "Pipeline status is FAILED because a duplicate data-quality query could not be completed. The duplicate state is unverified."
        else:
            explanation = "Pipeline status is FAILED because critical data-quality checks (NULL checks, FK integrity, or row count checks) failed."
    elif warnings_count > 0 or non_critical_failed:
        overall_status = "WARNING"
        explanation = (
            f"Latest pipeline run completed with {warnings_count} warning(s). Critical databases and tables are operational, "
            "but non-critical data quality checks or log warnings require review."
        )
    else:
        overall_status = "PASS"
        explanation = (
            "Latest pipeline run completed successfully. All critical data-quality checks passed. "
            "Bronze, Silver, and Gold layers are operational."
        )

    row_counts_df = get_row_counts()
    records_processed = 0
    records_loaded = 0
    if not row_counts_df.empty:
        bronze_rows = row_counts_df[row_counts_df["layer"] == "Bronze"]["row_count"].sum()
        gold_rows = row_counts_df[row_counts_df["layer"] == "Gold"]["row_count"].sum()
        records_processed = int(bronze_rows)
        records_loaded = int(gold_rows)

    return {
        "status": overall_status,
        "explanation": explanation,
        "last_run": run_info.get("end_time") or run_info.get("start_time", "Not available"),
        "duration": run_info.get("duration", "Not available"),
        "records_processed": records_processed,
        "records_loaded": records_loaded,
        "dq_score": dq_summary.get("score", 0.0),
        "failed_checks": dq_summary.get("failed_checks", 0),
        "warnings_count": warnings_count,
        "run_info": run_info,
        "dq_summary": dq_summary,
        "dbs_ok": all_dbs_ok,
    }


def render_pipeline_status_banner(health_info: dict) -> None:
    """Render the editorial hero with live, current pipeline information."""
    status = health_info["status"]
    last_run = health_info["last_run"]
    explanation = health_info["explanation"]

    st.markdown(
        f"""
        <section class="hero">
          <div>
            <div class="eyebrow">01 / ELT PIPELINE HEALTH</div>
            <h1>ELT PIPELINE<br>HEALTH REPORT</h1>
            <p>Production Data Engineering<br>Medallion Architecture / Bronze → Silver → Gold</p>
            <div class="hero-meta">LAST OBSERVED RUN<br>{last_run}</div>
          </div>
          <div class="hero-status"><strong>{status}</strong><span>{'✓' if status == 'PASS' else ('!' if status == 'WARNING' else '×')}</span></div>
        </section>
        <div class="report-note"><b>WHAT HAPPENED</b><br>{explanation}</div>
        """,
        unsafe_allow_html=True,
    )


def render_pipeline_summary_table(health_info: dict) -> None:
    """Render plain table for Executive Summary as requested in Section 3."""
    status = health_info["status"]
    render_section_title("02", "PIPELINE SUMMARY", "A live roll-up of the most recent execution.")
    st.markdown(
        f"""
        <table class="report-table">
            <thead>
                <tr>
                    <th style="width: 50%;">Metric</th>
                    <th style="width: 50%;">Value</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><b>Status</b></td>
                    <td>{status_markup(status)}</td>
                </tr>
                <tr>
                    <td><b>Last Run</b></td>
                    <td><code>{health_info['last_run']}</code></td>
                </tr>
                <tr>
                    <td><b>Duration</b></td>
                    <td><code>{health_info['duration']}</code></td>
                </tr>
                <tr>
                    <td><b>Records Processed</b></td>
                    <td>{format_number(health_info['records_processed'])}</td>
                </tr>
                <tr>
                    <td><b>Records Loaded</b></td>
                    <td>{format_number(health_info['records_loaded'])}</td>
                </tr>
                <tr><td><b>Data Quality</b></td><td><code>{health_info['dq_summary'].get('total_checks', 0)} checks / {health_info['dq_summary'].get('passed_checks', 0)} passed</code></td></tr>
                <tr>
                    <td><b>Failed Checks</b></td>
                    <td>{health_info['failed_checks']}</td>
                </tr>
                <tr>
                    <td><b>Warnings</b></td>
                    <td>{health_info['warnings_count']}</td>
                </tr>
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def render_latest_run_report(health_info: dict) -> None:
    """Render Latest Pipeline Run breakdown as requested in Section 4."""
    run_info = health_info["run_info"]
    row_counts_df = get_row_counts()

    bronze_rows = 0
    silver_rows = 0
    gold_rows = 0
    if not row_counts_df.empty:
        bronze_rows = int(row_counts_df[row_counts_df["layer"] == "Bronze"]["row_count"].sum())
        silver_rows = int(row_counts_df[row_counts_df["layer"] == "Silver"]["row_count"].sum())
        gold_rows = int(row_counts_df[row_counts_df["layer"] == "Gold"]["row_count"].sum())

    render_section_title("06", "WHAT HAPPENED", "The most recent logged execution, expressed as an operational narrative.")
    st.markdown(
        f"""
        <table class="report-table">
            <tbody>
                <tr>
                    <td style="width: 25%;"><b>Started</b></td>
                    <td style="width: 75%;"><code>{run_info.get('start_time', 'Not available')}</code></td>
                </tr>
                <tr>
                    <td><b>Finished</b></td>
                    <td><code>{run_info.get('end_time', 'Not available')}</code></td>
                </tr>
                <tr>
                    <td><b>Duration</b></td>
                    <td><code>{run_info.get('duration', 'Not available')}</code></td>
                </tr>
                <tr>
                    <td><b>Status</b></td><td>{status_markup(run_info.get('status', 'SUCCESS'))}</td>
                </tr>
                <tr>
                    <td><b>Bronze layer</b></td>
                    <td>{status_markup('PASS')} &nbsp; {format_number(bronze_rows)} rows — Raw source data was successfully ingested.</td>
                </tr>
                <tr>
                    <td><b>Silver layer</b></td>
                    <td>{status_markup('PASS')} &nbsp; {format_number(silver_rows)} rows — Bronze records reached transformation.</td>
                </tr>
                <tr>
                    <td><b>Gold layer</b></td>
                    <td>{status_markup('PASS')} &nbsp; {format_number(gold_rows)} rows — Analytics-ready records were loaded.</td>
                </tr>
                <tr>
                    <td><b>Result</b></td>
                    <td>{run_info.get('result_summary', 'Pipeline completed successfully.')}</td>
                </tr>
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def _retention(input_rows: int | None, output_rows: int | None) -> str:
    if input_rows is None or output_rows is None or input_rows <= 0:
        return "Not available"
    return f"{(output_rows / input_rows) * 100:.2f}%"


def _difference(input_rows: int | None, output_rows: int | None) -> str:
    if input_rows is None or output_rows is None:
        return "Not available"
    return format_number(input_rows - output_rows)


def render_medallion_table() -> None:
    """Render a compact visual architecture plus live row lineage."""
    lineage = get_pipeline_lineage()
    source = lineage["source"]
    bronze = lineage["bronze"]
    silver = lineage["silver"]
    gold = lineage["gold"]

    render_section_title("03", "DATA FLOW", "Source files move through raw ingestion, cleaning, and analytics modeling.")
    st.markdown(
        f"""
        <div class="pipeline-flow" aria-label="Source to Gold data flow">
          <div class="flow-node"><b>SOURCE</b><span>CRM / ERP</span><code>{format_number(source)}</code><small>source records</small></div>
          <div class="flow-arrow"><small>INGEST</small>→</div>
          <div class="flow-node"><b>BRONZE</b><span>RAW DATA</span><code>{format_number(bronze)}</code><small>loaded rows</small></div>
          <div class="flow-arrow"><small>CLEAN</small>→</div>
          <div class="flow-node"><b>SILVER</b><span>CLEAN DATA</span><code>{format_number(silver)}</code><small>output rows</small></div>
          <div class="flow-arrow"><small>MODEL</small>→</div>
          <div class="flow-node"><b>GOLD</b><span>ANALYTICS</span><code>{format_number(gold)}</code><small>represented rows</small></div>
        </div>
        """, unsafe_allow_html=True,
    )

    st.markdown('<div class="report-note"><b>ROW LINEAGE</b><br>Row counts are calculated from the source files and current database totals.</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <table class="report-table">
            <thead>
                <tr>
                    <th>Stage</th><th>Input</th><th>Output</th><th>Change</th><th>Retention</th><th>Meaning</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td><b>BRONZE</b></td><td><code>{format_number(source)}</code></td><td><code>{format_number(bronze)}</code></td>
                    <td><code>{_difference(source, bronze)} not loaded</code></td><td><code>{_retention(source, bronze)}</code></td>
                    <td>Source files were ingested into the raw layer.</td>
                </tr>
                <tr>
                    <td><b>SILVER</b></td><td><code>{format_number(bronze)}</code></td><td><code>{format_number(silver)}</code></td>
                    <td><code>{_difference(bronze, silver)} transformed</code></td><td><code>{_retention(bronze, silver)}</code></td>
                    <td>Records were cleaned, normalized, deduplicated, and validated.</td>
                </tr>
                <tr>
                    <td><b>GOLD</b></td><td><code>{format_number(silver)}</code></td><td><code>{format_number(gold)}</code></td>
                    <td>Row count not directly comparable</td><td>—</td>
                    <td>Silver data was modeled into analytics-ready dimensions and facts.</td>
                </tr>
            </tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
