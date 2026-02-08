import importlib.util
import unittest
from pathlib import Path


def _load_sql_safety_module():
    backend_dir = Path(__file__).resolve().parents[1]
    module_path = backend_dir / "app" / "services" / "sql_safety.py"
    spec = importlib.util.spec_from_file_location("sql_safety", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load sql_safety module spec.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSQLSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql_safety = _load_sql_safety_module()

    def test_allows_simple_select(self):
        self.sql_safety.validate_sql_safety("SELECT 1;")

    def test_allows_with_cte(self):
        self.sql_safety.validate_sql_safety("WITH x AS (SELECT 1) SELECT * FROM x;")

    def test_allows_leading_comment(self):
        self.sql_safety.validate_sql_safety("-- comment\nSELECT 1;")

    def test_does_not_match_keywords_inside_strings(self):
        self.sql_safety.validate_sql_safety("SELECT 'DROP' AS keyword;")

    def test_blocks_multi_statement(self):
        with self.assertRaises(self.sql_safety.SQLSafetyError):
            self.sql_safety.validate_sql_safety("SELECT 1; SELECT 2;")

    def test_blocks_ddl(self):
        with self.assertRaises(self.sql_safety.SQLSafetyError):
            self.sql_safety.validate_sql_safety("DROP TABLE fact_orders;")

    def test_blocks_select_into(self):
        with self.assertRaises(self.sql_safety.SQLSafetyError):
            self.sql_safety.validate_sql_safety("SELECT * INTO new_table FROM fact_orders;")

    def test_blocks_dml(self):
        with self.assertRaises(self.sql_safety.SQLSafetyError):
            self.sql_safety.validate_sql_safety("DELETE FROM fact_orders;")

