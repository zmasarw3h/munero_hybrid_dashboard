import re
import unittest
from pathlib import Path


class TestDashboardFiltersSparklineAndCatalog(unittest.TestCase):
    def test_build_where_clause_includes_is_test_predicate(self):
        backend_dir = Path(__file__).resolve().parents[1]
        dashboard_path = backend_dir / "app" / "api" / "dashboard.py"
        contents = dashboard_path.read_text(encoding="utf-8")

        pattern = re.compile(
            r"def\s+build_where_clause\s*\(.*?\):.*?_sql_is_test_predicate\s*\(",
            re.IGNORECASE | re.DOTALL,
        )
        self.assertRegex(contents, pattern)

    def test_sparkline_has_post_route(self):
        backend_dir = Path(__file__).resolve().parents[1]
        dashboard_path = backend_dir / "app" / "api" / "dashboard.py"
        contents = dashboard_path.read_text(encoding="utf-8")

        pattern = re.compile(r"@router\.post\s*\(\s*[\"']\/sparkline\/\{metric\}[\"']")
        self.assertRegex(contents, pattern)

    def test_catalog_kpis_builds_prior_where_clause_from_filters(self):
        backend_dir = Path(__file__).resolve().parents[1]
        dashboard_path = backend_dir / "app" / "api" / "dashboard.py"
        contents = dashboard_path.read_text(encoding="utf-8")

        pattern = re.compile(r"build_where_clause\s*\(\s*prior_filters\s*\)")
        self.assertRegex(contents, pattern)

    def test_config_defaults_db_return_empty_on_error_false(self):
        backend_dir = Path(__file__).resolve().parents[1]
        config_path = backend_dir / "app" / "core" / "config.py"
        contents = config_path.read_text(encoding="utf-8")
        self.assertRegex(contents, re.compile(r"DB_RETURN_EMPTY_ON_ERROR:\s*bool\s*=\s*False"))

    def test_leaderboard_row_supports_product_type(self):
        backend_dir = Path(__file__).resolve().parents[1]
        models_path = backend_dir / "app" / "models.py"
        contents = models_path.read_text(encoding="utf-8")
        self.assertRegex(contents, re.compile(r"class\s+LeaderboardRow\b[\s\S]*\bproduct_type\b"))

    def test_leaderboard_sets_product_type_for_product_dimension(self):
        backend_dir = Path(__file__).resolve().parents[1]
        dashboard_path = backend_dir / "app" / "api" / "dashboard.py"
        contents = dashboard_path.read_text(encoding="utf-8")
        self.assertIn("product_type_by_label", contents)
        self.assertRegex(contents, re.compile(r"LeaderboardRow\s*\([\s\S]*\bproduct_type\s*="))

    def test_trend_growth_sanitizes_infinity(self):
        backend_dir = Path(__file__).resolve().parents[1]
        dashboard_path = backend_dir / "app" / "api" / "dashboard.py"
        contents = dashboard_path.read_text(encoding="utf-8")
        self.assertIn(".replace([np.inf, -np.inf], np.nan)", contents)

    def test_scatter_aov_avoids_divide_by_zero(self):
        backend_dir = Path(__file__).resolve().parents[1]
        dashboard_path = backend_dir / "app" / "api" / "dashboard.py"
        contents = dashboard_path.read_text(encoding="utf-8")
        self.assertIn("denom = final_df['total_orders'].replace({0: np.nan})", contents)
