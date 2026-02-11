import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _load_smart_render_module():
    backend_dir = Path(__file__).resolve().parents[1]
    module_path = backend_dir / "app" / "services" / "smart_render.py"

    previous_modules: dict[str, object] = {}

    def _stub_module(name: str) -> types.ModuleType:
        module = types.ModuleType(name)
        sys.modules[name] = module
        return module

    def _save_and_stub(name: str) -> types.ModuleType:
        if name in sys.modules:
            previous_modules[name] = sys.modules[name]
        return _stub_module(name)

    # ---- minimal stubs so this test runs without third-party deps installed ----
    stubbed_pandas = False
    try:  # pragma: no cover
        import pandas  # noqa: F401
    except ModuleNotFoundError:
        pandas_stub = _save_and_stub("pandas")
        stubbed_pandas = True

        class _FakeColumns(list):
            def tolist(self):
                return list(self)

        class _FakeStrAccessor:
            def __init__(self, values):
                self._values = values

            def len(self):
                return _FakeSeries([len(str(v)) for v in self._values])

        class _FakeSeries:
            def __init__(self, values):
                self._values = values

            def nunique(self):
                return len(set(self._values))

            def astype(self, _type):
                return _FakeSeries([str(v) for v in self._values])

            @property
            def str(self):
                return _FakeStrAccessor(self._values)

            def max(self):
                return max(self._values) if self._values else None

        class _FakeGroupByAgg:
            def __init__(self, df, key_col: str, agg_cols: list[str]):
                self._df = df
                self._key_col = key_col
                self._agg_cols = agg_cols

            def sum(self):
                keys = self._df._data.get(self._key_col, [])
                groups: dict[object, dict[str, float]] = {}
                order: list[object] = []
                for idx, key in enumerate(keys):
                    if key not in groups:
                        groups[key] = {col: 0.0 for col in self._agg_cols}
                        order.append(key)
                    for col in self._agg_cols:
                        value = self._df._data.get(col, [0] * len(keys))[idx]
                        groups[key][col] += float(value or 0)

                out: dict[str, list[object]] = {self._key_col: []}
                for col in self._agg_cols:
                    out[col] = []
                for key in order:
                    out[self._key_col].append(key)
                    for col in self._agg_cols:
                        out[col].append(groups[key][col])
                return _FakeDataFrame(out)

        class _FakeGroupBy:
            def __init__(self, df, key_col: str):
                self._df = df
                self._key_col = key_col

            def __getitem__(self, cols):
                if isinstance(cols, str):
                    cols = [cols]
                return _FakeGroupByAgg(self._df, self._key_col, list(cols))

        class _FakeNullSeries:
            def __init__(self, values):
                self._values = values

            def all(self):
                return all(self._values)

        class _FakeNullDataFrame:
            def __init__(self, data):
                self._data = data

            def all(self):
                return _FakeNullSeries(
                    [all(v is None for v in values) for values in self._data.values()]
                )

        class _FakeDataFrame:
            def __init__(self, data):
                self._data = dict(data or {})
                self.columns = list(self._data.keys())

            @property
            def empty(self):
                return len(self) == 0

            def __len__(self):
                if not self.columns:
                    return 0
                first_col = self._data[self.columns[0]]
                return len(first_col)

            def isnull(self):
                return _FakeNullDataFrame(self._data)

            def select_dtypes(self, *, include=None):
                include = include or []
                wants_number = "number" in include
                numeric_cols = []
                if wants_number:
                    for col, values in self._data.items():
                        if all(isinstance(v, (int, float)) for v in values):
                            numeric_cols.append(col)
                return types.SimpleNamespace(columns=_FakeColumns(numeric_cols))

            def __getitem__(self, key):
                return _FakeSeries(self._data[key])

            def groupby(self, key_col: str, as_index: bool = False):  # noqa: ARG002
                return _FakeGroupBy(self, key_col)

        pandas_stub.DataFrame = _FakeDataFrame
        pandas_stub.isna = lambda value: value is None
        pandas_stub.to_datetime = lambda value, errors=None: value
        pandas_stub.concat = lambda frames, ignore_index=False: frames[0]

        def _is_numeric_dtype(value) -> bool:
            return isinstance(value, _FakeSeries) and all(isinstance(v, (int, float)) for v in value._values)

        api_types = types.SimpleNamespace(
            is_datetime64_any_dtype=lambda _value: False,
            is_numeric_dtype=_is_numeric_dtype,
        )
        pandas_stub.api = types.SimpleNamespace(types=api_types)

    app_stub = _save_and_stub("app")
    app_stub.__path__ = []  # mark as package

    models_stub = _save_and_stub("app.models")

    class ChartConfig:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    models_stub.ChartConfig = ChartConfig

    try:
        spec = importlib.util.spec_from_file_location("smart_render_under_test", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("Failed to load smart_render module spec.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        for name in ["app", "app.models"]:
            if name in previous_modules:
                sys.modules[name] = previous_modules[name]  # type: ignore[assignment]
            else:
                sys.modules.pop(name, None)

        if stubbed_pandas:
            if "pandas" in previous_modules:
                sys.modules["pandas"] = previous_modules["pandas"]  # type: ignore[assignment]
            else:
                sys.modules.pop("pandas", None)


class TestSmartRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.smart_render = _load_smart_render_module()

    def test_breakdown_defaults_to_single_metric(self):
        df = self.smart_render.pd.DataFrame(
            {
                "order_type": ["gift_card", "merchandise"],
                "orders": [10, 5],
                "total_revenue": [1000.0, 500.0],
            }
        )

        service = self.smart_render.SmartRenderService()
        config = service.determine_chart_type(
            df,
            "how many gift cards vs merchandise do I sell?",
        )

        self.assertEqual(config.type, "bar")
        self.assertEqual(config.x_column, "order_type")
        self.assertEqual(config.y_column, "orders")
        self.assertIsNone(config.secondary_y_column)

    def test_revenue_breakdown_prefers_pie_when_multiple_categories(self):
        df = self.smart_render.pd.DataFrame(
            {
                "order_type": ["gift_card", "merchandise"],
                "orders": [10, 5],
                "total_revenue": [1000.0, 500.0],
            }
        )

        service = self.smart_render.SmartRenderService()
        config = service.determine_chart_type(
            df,
            "show me revenue breakdown by product type",
        )

        self.assertEqual(config.type, "pie")
        self.assertEqual(config.x_column, "order_type")
        self.assertEqual(config.y_column, "total_revenue")
        self.assertIsNone(config.secondary_y_column)

    def test_explicit_orders_and_revenue_sets_secondary_metric(self):
        df = self.smart_render.pd.DataFrame(
            {
                "order_type": ["gift_card", "merchandise"],
                "orders": [10, 5],
                "total_revenue": [1000.0, 500.0],
            }
        )

        service = self.smart_render.SmartRenderService()
        config = service.determine_chart_type(
            df,
            "orders + revenue by order_type",
        )

        self.assertEqual(config.type, "bar")
        self.assertEqual(config.x_column, "order_type")
        self.assertEqual(config.y_column, "orders")
        self.assertEqual(config.secondary_y_column, "total_revenue")

    def test_maybe_aggregate_does_not_warn_when_already_grouped(self):
        df = self.smart_render.pd.DataFrame(
            {
                "order_type": ["gift_card", "merchandise"],
                "total_revenue": [1.0, 2.0],
            }
        )

        service = self.smart_render.SmartRenderService()
        config = self.smart_render.ChartConfig(
            type="bar",
            x_column="order_type",
            y_column="total_revenue",
            secondary_y_column=None,
            orientation="vertical",
            title="test",
        )
        _out_df, warnings = service._maybe_aggregate(df, config)
        self.assertEqual(warnings, [])

    def test_maybe_aggregate_warns_and_groups_when_duplicates_exist(self):
        df = self.smart_render.pd.DataFrame(
            {
                "order_type": ["gift_card", "gift_card", "merchandise"],
                "total_revenue": [1.0, 2.0, 3.0],
            }
        )

        service = self.smart_render.SmartRenderService()
        config = self.smart_render.ChartConfig(
            type="bar",
            x_column="order_type",
            y_column="total_revenue",
            secondary_y_column=None,
            orientation="vertical",
            title="test",
        )
        out_df, warnings = service._maybe_aggregate(df, config)
        self.assertEqual(warnings, ["Auto-aggregated 3 rows into 2 groups by order_type."])
        self.assertEqual(len(out_df), 2)


if __name__ == "__main__":
    unittest.main()
