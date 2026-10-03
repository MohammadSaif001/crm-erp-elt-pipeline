"""
components/pipeline_status.py
==============================================================================
Renders plain old-school web report components for pipeline status, run details,
and Medallion architecture tables.
"""

from __future__ import annotations

<<<<<<< Updated upstream
import streamlit as st

=======
from config import DB_SETTINGS
>>>>>>> Stashed changes
from database.connection import test_connection
from database.queries import compute_dq_score, get_row_counts
from utils.helpers import get_latest_run_details


def compute_overall_pipeline_status() -> dict:
    """
    Calculate the overall pipeline health status according to Section 14 rules:
    FAILED: pipeline failed OR critical DB unavailable OR critical DQ check failed.
    WARNING: pipeline completed but one or more non-critical runtime DQ checks failed.
    PASS: latest run succeeded and all critical checks passed.
    """
    # 1. DB check
    bronze_ok, _ = test_connection(DB_SETTINGS.bronze_db)
    silver_ok, _ = test_connection(DB_SETTINGS.silver_db)
    gold_ok, _ = test_connection(DB_SETTINGS.gold_db)
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
            failed_db = (
                "Gold" if not gold_ok else ("Silver" if not silver_ok else "Bronze")
            )
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
        bronze_rows = row_counts_df[row_counts_df["layer"] == "Bronze"][
            "row_count"
        ].sum()
        gold_rows = row_counts_df[row_counts_df["layer"] == "Gold"]["row_count"].sum()
        records_processed = int(bronze_rows)
        records_loaded = int(gold_rows)

    return {
        "status": overall_status,
        "explanation": explanation,
        "last_run": run_info.get("end_time")
        or run_info.get("start_time", "Not available"),
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
