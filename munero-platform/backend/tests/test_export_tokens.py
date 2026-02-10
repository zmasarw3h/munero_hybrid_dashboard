import importlib.util
import unittest
from pathlib import Path


def _load_export_tokens_module():
    backend_dir = Path(__file__).resolve().parents[1]
    module_path = backend_dir / "app" / "core" / "export_tokens.py"
    spec = importlib.util.spec_from_file_location("export_tokens_under_test", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load export_tokens module spec.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestExportTokens(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tokens = _load_export_tokens_module()

    def test_round_trip_token_verifies(self):
        secret = "super-secret"
        sql_query = "SELECT 1;"
        filters = {"start_date": "2025-01-01", "end_date": "2025-12-31", "countries": []}
        token = self.tokens.make_export_token(
            secret=secret,
            sql_query=sql_query,
            filters=filters,
            ttl_s=900,
            now_epoch=1_700_000_000,
        )
        self.tokens.verify_export_token(
            secret=secret,
            token=token,
            sql_query=sql_query,
            filters=filters,
            now_epoch=1_700_000_001,
        )

    def test_expired_token_rejects(self):
        secret = "super-secret"
        sql_query = "SELECT 1"
        filters = {"countries": ["AE"]}
        token = self.tokens.make_export_token(
            secret=secret,
            sql_query=sql_query,
            filters=filters,
            ttl_s=10,
            now_epoch=100,
        )
        with self.assertRaises(self.tokens.ExportTokenError):
            self.tokens.verify_export_token(
                secret=secret,
                token=token,
                sql_query=sql_query,
                filters=filters,
                now_epoch=111,
            )

    def test_token_rejects_different_sql(self):
        secret = "super-secret"
        filters = {"countries": ["AE"]}
        token = self.tokens.make_export_token(
            secret=secret,
            sql_query="SELECT 1;",
            filters=filters,
            ttl_s=900,
            now_epoch=1_700_000_000,
        )
        with self.assertRaises(self.tokens.ExportTokenError):
            self.tokens.verify_export_token(
                secret=secret,
                token=token,
                sql_query="SELECT 2;",
                filters=filters,
                now_epoch=1_700_000_001,
            )

    def test_token_rejects_different_filters(self):
        secret = "super-secret"
        sql_query = "SELECT 1;"
        token = self.tokens.make_export_token(
            secret=secret,
            sql_query=sql_query,
            filters={"countries": ["AE"]},
            ttl_s=900,
            now_epoch=1_700_000_000,
        )
        with self.assertRaises(self.tokens.ExportTokenError):
            self.tokens.verify_export_token(
                secret=secret,
                token=token,
                sql_query=sql_query,
                filters={"countries": ["SA"]},
                now_epoch=1_700_000_001,
            )

