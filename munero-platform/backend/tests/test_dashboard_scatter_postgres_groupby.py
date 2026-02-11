import re
import unittest
from pathlib import Path


class TestDashboardScatterPostgresGroupBy(unittest.TestCase):
    def test_scatter_query_aggregates_client_country(self):
        """
        Regression test: SQLite allows selecting non-grouped columns, but Postgres does not.
        The client scatter endpoint must aggregate client_country (or otherwise include it
        safely) to avoid returning empty data on Postgres.
        """
        backend_dir = Path(__file__).resolve().parents[1]
        dashboard_path = backend_dir / "app" / "api" / "dashboard.py"
        contents = dashboard_path.read_text(encoding="utf-8")

        # Allow whitespace/case variations.
        pattern = re.compile(r"\bmin\s*\(\s*client_country\s*\)\s+as\s+client_country\b", re.IGNORECASE)
        self.assertRegex(contents, pattern)

