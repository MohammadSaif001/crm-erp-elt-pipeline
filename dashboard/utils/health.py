"""Combine live database, pipeline, and data-quality state for the Home page."""

from __future__ import annotations

from config import DB_SETTINGS
from database.connection import test_connection
from database.queries import compute_dq_score, get_row_counts
from utils.helpers import get_latest_run_details


def compute_overall_pipeline_status() -> dict:
    """Build the health summary consumed by the server-rendered Home page."""
    bronze_ok, _ = test_connection(DB_SETTINGS.bronze_db)
    silver_ok, _ = test_connection(DB_SETTINGS.silver_db)
    gold_ok, _ = test_connection(DB_SETTINGS.gold_db)
    all_dbs_ok = bronze_ok and silver_ok and gold_ok

    run_info = get_latest_run_details()
    dq_summary = compute_dq_score()
    nulls = dq_summary.get("null_checks")
    fks = dq_summary.get("fk_checks")
    counts = dq_summary.get("row_count_checks")
    duplicates = dq_summary.get("duplicate_checks")

    critical_failed = any(
        not frame.empty and "passed" in frame.columns and not frame["passed"].all()
        for frame in (nulls, fks, counts)
    )
    duplicate_query_failed = (
        not duplicates.empty
        and "status" in duplicates.columns
        and (duplicates["status"] == "FAILED").any()
    )
    duplicate_failed = (
        not duplicates.empty
        and "passed" in duplicates.columns
        and not duplicates["passed"].all()
    )
    warnings_count = dq_summary.get("warning_checks", 0)
    run_failed = run_info.get("status") == "FAILED"

    if run_failed or not all_dbs_ok or critical_failed or duplicate_query_failed:
        status = "FAILED"
        if not all_dbs_ok:
            failed_db = "Gold" if not gold_ok else "Silver" if not silver_ok else "Bronze"
            explanation = (
                f"Pipeline status is FAILED because the {failed_db} database is unavailable. "
                "The latest Gold layer could not be verified."
            )
        elif run_failed:
            explanation = (
                "Pipeline status is FAILED because the latest execution encountered errors: "
                f"{run_info.get('result_summary')}"
            )
        elif duplicate_query_failed:
            explanation = (
                "Pipeline status is FAILED because a duplicate data-quality query could not "
                "be completed. The duplicate state is unverified."
            )
        else:
            explanation = (
                "Pipeline status is FAILED because critical data-quality checks "
                "(NULL checks, FK integrity, or row count checks) failed."
            )
    elif warnings_count > 0 or duplicate_failed:
        status = "WARNING"
        explanation = (
            f"Latest pipeline run completed with {warnings_count} warning(s). Critical "
            "databases and tables are operational, but non-critical data-quality checks "
            "require review."
        )
    else:
        status = "PASS"
        explanation = (
            "Latest pipeline run completed successfully. All critical data-quality checks "
            "passed. Bronze, Silver, and Gold layers are operational."
        )

    row_counts = get_row_counts()
    bronze_rows = int(row_counts.loc[row_counts["layer"] == "Bronze", "row_count"].sum()) if not row_counts.empty else 0
    gold_rows = int(row_counts.loc[row_counts["layer"] == "Gold", "row_count"].sum()) if not row_counts.empty else 0

    return {
        "status": status,
        "explanation": explanation,
        "last_run": run_info.get("end_time") or run_info.get("start_time", "Not available"),
        "duration": run_info.get("duration", "Not available"),
        "records_processed": bronze_rows,
        "records_loaded": gold_rows,
        "dq_score": dq_summary.get("score", 0.0),
        "failed_checks": dq_summary.get("failed_checks", 0),
        "warnings_count": warnings_count,
        "run_info": run_info,
        "dq_summary": dq_summary,
        "dbs_ok": all_dbs_ok,
    }
