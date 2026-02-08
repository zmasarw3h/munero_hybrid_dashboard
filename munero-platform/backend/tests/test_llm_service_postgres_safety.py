import importlib.util
import sys
import types
import unittest
from datetime import date
from pathlib import Path


def _load_llm_service_module():
    backend_dir = Path(__file__).resolve().parents[1]
    module_path = backend_dir / "app" / "services" / "llm_service.py"

    # ---- minimal stubs so this test runs without third-party deps installed ----
    previous_modules: dict[str, object] = {}

    def _stub_module(name: str) -> types.ModuleType:
        module = types.ModuleType(name)
        sys.modules[name] = module
        return module

    def _save_and_stub(name: str) -> types.ModuleType:
        if name in sys.modules:
            previous_modules[name] = sys.modules[name]
        return _stub_module(name)

    # pandas stub (module import requires it)
    pandas_stub = _save_and_stub("pandas")
    pandas_stub.DataFrame = type("DataFrame", (), {})

    # app package + submodules used by llm_service
    app_stub = _save_and_stub("app")
    app_stub.__path__ = []  # mark as package

    core_stub = _save_and_stub("app.core")
    core_stub.__path__ = []

    services_stub = _save_and_stub("app.services")
    services_stub.__path__ = []

    # app.core.config stub
    config_stub = _save_and_stub("app.core.config")

    class _StubSettings:
        def __init__(self):
            self.DB_URI = "sqlite:////tmp/munero_test.sqlite"
            self.LLM_PROVIDER = "gemini"
            self.LLM_API_KEY = None
            self.LLM_MODEL = "gemini-2.5-flash"
            self.LLM_BASE_URL = "https://example.invalid"
            self.LLM_TEMPERATURE = 0.0
            self.LLM_TIMEOUT = 60
            self.LLM_MAX_OUTPUT_TOKENS = 512
            self.LLM_RETRIES = 0
            self.SQL_TIMEOUT = 30

        @property
        def db_dialect(self) -> str:
            uri = (self.DB_URI or "").lower()
            if uri.startswith("sqlite"):
                return "sqlite"
            if uri.startswith("postgres"):
                return "postgresql"
            return "unknown"

    config_stub.settings = _StubSettings()

    # app.core.database stub (import requires engine + execute_query_df)
    database_stub = _save_and_stub("app.core.database")
    database_stub.engine = object()

    def _execute_query_df(*_args, **_kwargs):
        raise RuntimeError("execute_query_df is not used in these tests")

    database_stub.execute_query_df = _execute_query_df

    # app.core.logging_utils stub (import requires redact_sql_for_log)
    logging_utils_stub = _save_and_stub("app.core.logging_utils")

    def _redact_sql_for_log(sql, **_kwargs):
        return f"len={len(sql) if sql else 0} sha=<stub>"

    logging_utils_stub.redact_sql_for_log = _redact_sql_for_log

    # app.services.gemini_client stub (import requires these symbols)
    gemini_client_stub = _save_and_stub("app.services.gemini_client")

    class GeminiClientError(RuntimeError):
        pass

    class GeminiClientConfig:
        def __init__(self, **_kwargs):
            pass

    class GeminiClient:
        def __init__(self, _config):
            pass

        def generate_text(self, _prompt: str) -> str:  # pragma: no cover
            raise GeminiClientError("GeminiClient is not used in these tests")

    def can_check_gemini_connection(**_kwargs) -> bool:
        return False

    gemini_client_stub.GeminiClient = GeminiClient
    gemini_client_stub.GeminiClientConfig = GeminiClientConfig
    gemini_client_stub.GeminiClientError = GeminiClientError
    gemini_client_stub.can_check_gemini_connection = can_check_gemini_connection

    # app.models stub (import requires DashboardFilters)
    models_stub = _save_and_stub("app.models")

    class DashboardFilters:
        def __init__(
            self,
            *,
            start_date: date | None = None,
            end_date: date | None = None,
            countries: list[str] | None = None,
            product_types: list[str] | None = None,
            clients: list[str] | None = None,
            brands: list[str] | None = None,
            suppliers: list[str] | None = None,
        ):
            self.start_date = start_date
            self.end_date = end_date
            self.countries = countries or []
            self.product_types = product_types or []
            self.clients = clients or []
            self.brands = brands or []
            self.suppliers = suppliers or []

    models_stub.DashboardFilters = DashboardFilters

    try:
        spec = importlib.util.spec_from_file_location("llm_service_under_test", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Failed to load llm_service module spec.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        # Restore original modules to avoid leaking stubs outside this test module.
        for name in [
            "pandas",
            "app",
            "app.core",
            "app.core.config",
            "app.core.database",
            "app.core.logging_utils",
            "app.services",
            "app.services.gemini_client",
            "app.models",
        ]:
            if name in previous_modules:
                sys.modules[name] = previous_modules[name]  # type: ignore[assignment]
            else:
                sys.modules.pop(name, None)


class TestLLMServicePostgresSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.llm_service = _load_llm_service_module()

    def test_build_filter_predicate_postgres_is_type_safe(self):
        settings = self.llm_service.settings
        settings.DB_URI = "postgresql+psycopg://user:pass@localhost:5432/db"

        service = self.llm_service.LLMService()
        filters = self.llm_service.DashboardFilters(
            start_date=date(2024, 12, 31),
            end_date=date(2025, 12, 30),
        )
        predicate, params = service.build_filter_predicate(filters)

        self.assertIn(
            "COALESCE(NULLIF(lower(is_test::text), ''), '0') IN ('0','false','f')",
            predicate,
        )
        self.assertIn("NULLIF(order_date::text, '')::date", predicate)
        self.assertIn(":munero_start_date", predicate)
        self.assertIn(":munero_end_date", predicate)

        self.assertIsInstance(params["munero_start_date"], date)
        self.assertIsInstance(params["munero_end_date"], date)

    def test_build_sql_prompt_postgres_includes_safe_casts(self):
        settings = self.llm_service.settings
        settings.DB_URI = "postgresql+psycopg://user:pass@localhost:5432/db"

        service = self.llm_service.LLMService()
        prompt = service._build_sql_prompt(
            "What are my top 5 products by revenue?",
            self.llm_service.DashboardFilters(),
        )

        self.assertIn("NULLIF(regexp_replace(order_price_in_aed::text", prompt)
        self.assertIn("to_char(NULLIF(order_date::text, '')::date, 'YYYY-MM')", prompt)
        self.assertIn(f"WHERE {self.llm_service.FILTER_PLACEHOLDER_TOKEN}", prompt)

    def test_build_sql_prompt_sqlite_avoids_postgres_functions(self):
        settings = self.llm_service.settings
        settings.DB_URI = "sqlite:////tmp/munero_test.sqlite"

        service = self.llm_service.LLMService()
        prompt = service._build_sql_prompt(
            "What is total revenue?",
            self.llm_service.DashboardFilters(),
        )

        self.assertNotIn("regexp_replace", prompt)
        self.assertIn("strftime('%Y-%m', order_date)", prompt)

