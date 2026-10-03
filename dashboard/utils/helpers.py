"""
utils/helpers.py
==============================================================================
General-purpose formatting, human-readable language converters, and
log-parsing helpers for the ELT Pipeline Health Report.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from config import APP_SETTINGS

logger = logging.getLogger("dashboard.helpers")


def format_currency(value: float | None, currency: str = "$") -> str:
    """Format a number as currency with commas, e.g. $116,300."""
    if value is None:
        return f"{currency}0"
    return f"{currency}{value:,.2f}"


def format_number(value: float | None) -> str:
    """Format an integer count with commas, e.g. 116,300."""
    if value is None or value == "":
        return "Not available"
    try:
        val = int(value)
        return f"{val:,}"
    except (ValueError, TypeError):
        return str(value)


def format_percent(value: float | None, decimals: int = 1) -> str:
    """Format a ratio (0-100 scale) as a percent string."""
    if value is None:
        return "Not available"
    return f"{value:.{decimals}f}%"


def format_duration(seconds: float | None) -> str:
    """Format elapsed seconds as a human-readable duration, e.g. 00:04:32 or 4m 32s."""
    if seconds is None:
        return "Not available"
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes, secs = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{int(hours):02d}:{int(minutes):02d}:{int(secs):02d}"
    return f"{int(minutes):02d}:{int(secs):02d}"


def format_timestamp(ts: datetime | str | None) -> str:
    """Format a timestamp for display; returns 'Not available' if missing."""
    if not ts:
        return "Not available"
    if isinstance(ts, str):
        # Clean comma separator if log format "YYYY-MM-DD HH:MM:SS,mmm"
        ts_clean = ts.split(",")[0].strip()
        try:
            ts_obj = datetime.fromisoformat(ts_clean)
            return ts_obj.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return ts_clean
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def humanize_check_name(check_name: str) -> str:
    """
    Convert raw technical check names to clear plain-language sentences.
    As requested in Section 15 of requirements.
    """
    check_lower = check_name.lower()
    if "null" in check_lower:
        return f"NULL check on {check_name.replace(' NOT NULL', '')}"
    if "unique" in check_lower or "duplicate" in check_lower:
        return f"Duplicate key check on {check_name.replace(' UNIQUE', '')}"
    if "sales.sales_cust_id" in check_lower or "fk" in check_lower:
        return f"Foreign key integrity check ({check_name})"
    return check_name


def humanize_check_detail(
    check_type: str, passed: bool | None, count: int | None = 0
) -> str:
    """Return plain-language result explanations for DQ checks."""
    if passed is None:
        return "Check status unverified"
    if check_type == "null":
        return "0 null violations found" if passed else f"{count} null values detected"
    if check_type == "duplicate":
        return (
            "0 duplicate records found"
            if passed
            else f"{count} duplicate records found"
        )
    if check_type == "fk":
        return (
            "0 broken relationships"
            if passed
            else f"{count} orphaned foreign key records found"
        )
    if check_type == "row_count":
        return "Expected row counts met" if passed else "Table contains 0 rows"
    return "Passed" if passed else "Failed"


_LOG_LINE_RE = re.compile(
    r"^(?P<timestamp>[\d\-]+\s[\d:,]+)\s*\|\s*(?P<level>\w+)\s*\|\s*(?P<module>\w+)\s*\|\s*(?P<message>.*)$"
)


def parse_pipeline_log(max_lines: int | None = None) -> list[dict]:
    """
    Parse the pipeline's `pipeline.log` file into structured records.
    """
    max_lines = max_lines or APP_SETTINGS.max_log_lines
    log_path = Path(APP_SETTINGS.log_file_path)

    if not log_path.exists():
        logger.warning("Pipeline log file not found at %s", log_path)
        return []

    records: list[dict] = []
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-max_lines:]
        for line in lines:
            line_str = line.strip()
            match = _LOG_LINE_RE.match(line_str)
            if match:
                records.append(match.groupdict())
            elif line_str:
                records.append(
                    {
                        "timestamp": "",
                        "level": "INFO",
                        "module": "system",
                        "message": line_str,
                    }
                )
    except OSError as exc:
        logger.error("Failed to read pipeline log: %s", exc)
        return []

    return records


def get_latest_run_details() -> dict:
    """
    Extract structured details of the most recent ELT pipeline execution from pipeline.log.
    """
    records = parse_pipeline_log()
    if not records:
        return {
            "has_run": False,
            "start_time": "Not available",
            "end_time": "Not available",
            "duration": "Not available",
            "status": "UNKNOWN",
            "result_summary": "No pipeline log records found at configured log path.",
            "timings": [],
            "warnings_count": 0,
            "errors_count": 0,
        }

    # Find the complete block for the last pipeline run.  Transformation
    # functions and pytest can append diagnostic lines after a run; those
    # lines must not be reported as part of that run's health summary.
    start_indices = [
        i for i, r in enumerate(records) if "Pipeline start" in r.get("message", "")
    ]
    if start_indices:
        start_index = start_indices[-1]
        completion_index = next(
            (
                i
                for i in range(start_index, len(records))
                if "Pipeline complete" in records[i].get("message", "")
            ),
            None,
        )
        run_block = (
            records[start_index : completion_index + 1]
            if completion_index is not None
            else records[start_index:]
        )
    else:
        run_block = records

    start_ts_raw = run_block[0].get("timestamp", "")
    end_ts_raw = run_block[-1].get("timestamp", "")

    start_ts = format_timestamp(start_ts_raw)
    end_ts = format_timestamp(end_ts_raw)

    # Calculate duration if possible
    duration_str = "Not available"
    try:
        if start_ts_raw and end_ts_raw:
            t1 = datetime.fromisoformat(start_ts_raw.split(",")[0].strip())
            t2 = datetime.fromisoformat(end_ts_raw.split(",")[0].strip())
            delta_sec = (t2 - t1).total_seconds()
            duration_str = format_duration(delta_sec)
    except Exception:
        pass

    errors = [r for r in run_block if r.get("level", "").upper() == "ERROR"]
    warnings = [r for r in run_block if r.get("level", "").upper() == "WARNING"]
    completes = [r for r in run_block if "Pipeline complete" in r.get("message", "")]

    if errors:
        status = "FAILED"
        first_err = errors[0].get("message", "Pipeline execution failed.")
        result_summary = f"Pipeline failed: {first_err}"
    elif completes:
        status = "SUCCESS"
        result_summary = "Pipeline completed successfully and the Gold layer is available for analytics."
    else:
        status = "SUCCESS" if not errors else "FAILED"
        result_summary = "Pipeline execution completed."

    timings = extract_batch_timings(run_block)

    return {
        "has_run": True,
        "start_time": start_ts,
        "end_time": end_ts,
        "duration": duration_str,
        "status": status,
        "result_summary": result_summary,
        "timings": timings,
        "warnings_count": len(warnings),
        "errors_count": len(errors),
        "raw_records": run_block,
    }


def extract_batch_timings(records: list[dict]) -> list[dict]:
    """Extract [BATCH END] ... Total time=X.XXs lines for stage timing breakdown."""
    results = []
    pattern = re.compile(
        r"\[BATCH END\]\s*(?P<name>.+?)\s*(completed)?\s*\|\s*Total time=(?P<seconds>[\d.]+)s"
    )
    for r in records:
        m = pattern.search(r.get("message", ""))
        if m:
            results.append(
                {
                    "stage": m.group("name").strip(),
                    "duration_seconds": float(m.group("seconds")),
                    "timestamp": r.get("timestamp", ""),
                }
            )
    return results


def summarize_log_levels(records: list[dict]) -> dict[str, int]:
    """Count log records by level."""
    summary = {"INFO": 0, "WARNING": 0, "ERROR": 0, "OTHER": 0}
    for r in records:
        level = r.get("level", "OTHER").upper()
        summary[level if level in summary else "OTHER"] += 1
    return summary
