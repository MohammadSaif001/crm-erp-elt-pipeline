# Tests

All test files live directly in this folder. Their names identify what they exercise:

- `test_transformations.py` — in-memory unit tests; no database needed.
- `test_dashboard_html.py` — FastAPI route and Jinja HTML tests; database calls are mocked.
- `test_pipeline.py` and `test_data_quality.py` — integration tests against live databases.

Run the HTML dashboard tests from the repository root:

```bash
python -m pytest tests/test_dashboard_html.py
```

Run transformation unit tests:

```bash
python -m pytest tests/test_transformations.py
```

Run the database integration checks when the configured MySQL layers are available:

```bash
python -m pytest -m integration tests/test_pipeline.py tests/test_data_quality.py
```
