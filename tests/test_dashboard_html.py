"""HTTP-level coverage for the FastAPI/Jinja dashboard."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

import pandas as pd
import pytest
from starlette.requests import Request

from dashboard import main as dashboard


def request_app(path: str, method: str = "GET") -> dict:
    """Call the registered FastAPI endpoint without an external HTTP client."""
    query = ""
    if "?" in path:
        path, query = path.split("?", maxsplit=1)
    query_params = parse_qs(query)
    route = next(
        route
        for route in dashboard.app.routes
        if getattr(route, "path", None) == path
        and method in getattr(route, "methods", set())
    )

    if path == "/":
        response = route.endpoint()
    elif path == "/refresh":
        redirect_to = query_params.get("redirect_to", ["/home"])[0]
        response = route.endpoint(redirect_to=redirect_to)
    else:
        scope = {
            "type": "http",
            "method": method,
            "scheme": "http",
            "path": path,
            "query_string": query.encode(),
            "headers": [(b"host", b"testserver")],
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        }
        request = Request(scope)
        if path == "/technical-details":
            level = query_params.get("level", ["ALL"])[0]
            response = route.endpoint(request, level=level)
        else:
            response = route.endpoint(request)

    return {
        "status_code": response.status_code,
        "headers": dict(response.headers),
        "text": response.body.decode("utf-8"),
    }


@pytest.fixture
def client(monkeypatch):
    empty_checks = pd.DataFrame(columns=["passed", "status"])
    dq = {
        "score": 100.0,
        "total_checks": 4,
        "passed_checks": 4,
        "warning_checks": 0,
        "failed_checks": 0,
        "null_checks": pd.DataFrame(
            [
                {
                    "check": "customers.customer_id NOT NULL",
                    "total_rows": 10,
                    "failed_rows": 0,
                    "passed": True,
                }
            ]
        ),
        "duplicate_checks": pd.DataFrame(
            columns=["check", "duplicate_keys", "passed", "status"]
        ),
        "fk_checks": empty_checks.copy(),
        "row_count_checks": empty_checks.copy(),
    }
    row_counts = pd.DataFrame(
        [
            {"layer": "Bronze", "table": "raw_customers", "row_count": 10},
            {"layer": "Silver", "table": "customers", "row_count": 10},
            {"layer": "Gold", "table": "dim_customers", "row_count": 10},
        ]
    )
    run_info = {
        "has_run": True,
        "start_time": "2026-10-03 10:00:00",
        "end_time": "2026-10-03 10:01:00",
        "duration": "60.00s",
        "status": "SUCCESS",
        "result_summary": "Pipeline completed successfully.",
        "timings": [],
        "warnings_count": 0,
        "errors_count": 0,
        "raw_records": [
            {
                "timestamp": "2026-10-03 10:00:00",
                "level": "INFO",
                "module": "pipeline",
                "message": "Pipeline start",
            }
        ],
    }
    health_info = {
        "status": "PASS",
        "explanation": "All checks passed.",
        "last_run": run_info["end_time"],
        "duration": run_info["duration"],
        "records_processed": 10,
        "records_loaded": 10,
        "dq_score": 100.0,
        "failed_checks": 0,
        "warnings_count": 0,
        "run_info": run_info,
        "dq_summary": dq,
        "dbs_ok": True,
    }

    monkeypatch.setattr(dashboard, "test_connection", lambda _database: (True, "ok"))
    monkeypatch.setattr(dashboard, "compute_overall_pipeline_status", lambda: health_info)
    monkeypatch.setattr(
        dashboard,
        "get_pipeline_lineage",
        lambda: {"source": 10, "bronze": 10, "silver": 10, "gold": 10},
    )
    monkeypatch.setattr(dashboard, "get_row_counts", lambda: row_counts.copy())
    monkeypatch.setattr(dashboard, "compute_dq_score", lambda: dq)
    monkeypatch.setattr(dashboard, "get_latest_run_details", lambda: run_info)
    monkeypatch.setattr(
        dashboard,
        "parse_pipeline_log",
        lambda max_lines=None: [
            {"timestamp": "10:00", "level": "INFO", "module": "pipeline", "message": "startup"},
            {"timestamp": "10:01", "level": "ERROR", "module": "pipeline", "message": "sample error"},
        ],
    )

    return request_app


def test_root_redirects_to_home(client):
    response = client("/")

    assert response["status_code"] == 307
    assert response["headers"]["location"] == "/home"


@pytest.mark.parametrize(
    ("path", "expected_text"),
    [
        ("/home", "ELT PIPELINE"),
        ("/pipeline-run", "LATEST RUN METRICS"),
        ("/data-quality", "QUALITY SCORE OVERVIEW"),
        ("/database-health", "DATABASE CONNECTION STATUS"),
        ("/technical-details", "SYSTEM ENVIRONMENT"),
    ],
)
def test_html_pages_render(client, path, expected_text):
    response = client(path)

    assert response["status_code"] == 200
    assert "text/html" in response["headers"]["content-type"]
    assert expected_text in response["text"]
    assert 'href="/static/styles.css"' in response["text"]


def test_technical_details_filters_log_level(client):
    response = client("/technical-details?level=ERROR")

    assert response["status_code"] == 200
    assert "sample error" in response["text"]
    assert "startup" not in response["text"]


def test_stylesheet_is_served(client):
    static_mount = next(
        route
        for route in dashboard.app.routes
        if getattr(route, "path", None) == "/static"
    )

    stylesheet = Path(static_mount.app.directory) / "styles.css"
    assert stylesheet.is_file()
    assert "--font-family" in stylesheet.read_text(encoding="utf-8")


def test_refresh_clears_cache_updates_timestamp_and_redirects(client, monkeypatch):
    calls = []
    monkeypatch.setattr(dashboard, "clear_all_caches", lambda: calls.append("clear"))
    monkeypatch.setattr(dashboard, "bump_last_refresh", lambda: calls.append("bump"))

    response = client("/refresh?redirect_to=/technical-details", method="POST")

    assert response["status_code"] == 303
    assert response["headers"]["location"] == "/technical-details"
    assert calls == ["clear", "bump"]
