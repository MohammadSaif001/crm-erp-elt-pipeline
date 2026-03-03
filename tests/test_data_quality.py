import sys
import os
import pytest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
python_dir = os.path.join(project_root, "python")
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)

from dq_checks.check_duplicates import check_duplicates
from dq_checks.check_nulls import check_nulls
from dq_checks.check_row_counts import get_row_counts, compare_layers
from dq_checks.check_fk_integrity import check_fk_integrity


class TestDuplicates:
    """No duplicates on primary keys in silver layer."""

    def test_silver_no_duplicates(self):
        results = check_duplicates("silver")
        for table, info in results.items():
            assert info["status"] == "PASS", (
                f"Silver table '{table}' has {info.get('duplicate_count', '?')} duplicate rows"
            )

"""
Data Quality Tests
-------------------
Combines all DQ check modules into a pytest suite.

Usage:
    cd d:\\data_engineering_project
    python -m pytest tests/test_data_quality.py -v
"""

class TestNulls:
    """Critical columns must not have NULLs."""

    def test_silver_no_unexpected_nulls(self):
        results = check_nulls("silver")
        for table, checks in results.items():
            for check in checks:
                assert check["status"] == "PASS", (
                    f"Silver {table}.{check['column']} has {check.get('null_count', '?')} NULLs"
                )


class TestRowCounts:
    """All tables should have data and silver <= bronze."""

    @pytest.mark.parametrize("layer", ["bronze", "silver"])
    def test_tables_not_empty(self, layer):
        counts = get_row_counts(layer)
        for table, count in counts.items():
            assert count > 0, f"{layer}.{table} is empty (count={count})"

    def test_silver_lte_bronze(self):
        comparison = compare_layers("bronze", "silver")
        for table, info in comparison.items():
            assert info["silver_count"] <= info["bronze_count"], (
                f"{table}: silver ({info['silver_count']}) > bronze ({info['bronze_count']})"
            )


class TestForeignKeyIntegrity:
    """Referential integrity between related tables."""

    def test_all_fk_rules_pass(self):
        results = check_fk_integrity()
        for r in results:
            assert r["status"] == "PASS", (
                f"FK rule '{r['rule']}' failed: {r.get('orphan_count', '?')} orphan rows. "
                f"Samples: {r.get('sample_orphans', [])}"
            )
