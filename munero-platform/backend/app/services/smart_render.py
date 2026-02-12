"""
SmartRender Service for intelligent visualization selection.
Ports the smart_render() function from app.py to return configuration objects
instead of rendering directly. The frontend (React/Recharts) renders based on the config.
"""
import re
import pandas as pd
from datetime import date, datetime
from decimal import Decimal
from typing import Tuple, List, Dict, Any, Optional, Literal, cast

from app.models import ChartConfig


# ============================================================================
# CONFIGURATION
# ============================================================================

SMART_RENDER_CONFIG = {
    "max_display_rows": 15,         # Maximum rows to display in charts
    "max_table_rows": 10,           # Maximum rows to display in tables
    "max_time_series_points_daily": 180,    # Max points for daily line charts
    "max_time_series_points_monthly": 120,  # Max points for monthly line charts
    "max_time_series_points_yearly": 50,    # Max points for yearly line charts
    "long_label_threshold": 20,     # Character length to trigger horizontal bars
    "pie_chart_max_slices": 8,      # Maximum slices for readable pie chart
    "bar_chart_max_categories": 20, # Maximum categories before switching to table
}


# ============================================================================
# SMART RENDER SERVICE CLASS
# ============================================================================

class SmartRenderService:
    """
    Service class for intelligent visualization selection.
    Analyzes DataFrame structure and determines the best chart type.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the SmartRender service.
        
        Args:
            config: Optional override for default configuration
        """
        self.config = {**SMART_RENDER_CONFIG, **(config or {})}
    
    def determine_chart_type(self, df: pd.DataFrame, question: str = "") -> ChartConfig:
        """
        Analyze DataFrame and question to determine the best visualization type.
        
        Args:
            df: Query result DataFrame
            question: Original user question (for context and user preferences)
            
        Returns:
            ChartConfig: Configuration object for the frontend to render
        """
        # Handle empty DataFrame
        if df.empty:
            return ChartConfig(
                type="table", 
                title="No Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical"
            )
        
        # Handle DataFrame with all NULL values (aggregate with no matches)
        if len(df) == 1 and df.isnull().all().all():
            return ChartConfig(
                type="table", 
                title="No Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical"
            )
        
        # --- Case 1: Single Value (KPI/Metric) ---
        # 1 row × 1 column → metric card
        if len(df) == 1 and len(df.columns) == 1:
            col_name = df.columns[0]
            title = self._format_column_title(str(col_name))
            return ChartConfig(
                type="metric", 
                title=title,
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical"
            )
        
        # --- Case 2: Single Column → Table ---
        if len(df.columns) == 1:
            return ChartConfig(
                type="table", 
                title="Query Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical"
            )

        # --- Check for user explicit chart type request ---
        user_viz_type = self._detect_user_preference(question)
        if user_viz_type == "table":
            return ChartConfig(
                type="table",
                title="Query Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical",
            )

        wants_time_series = self._wants_time_series(question, user_viz_type)

        # --- Detect numeric and non-numeric columns ---
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        non_numeric_cols = [col for col in df.columns if col not in numeric_cols]

        # No numeric metrics → Table
        if len(numeric_cols) == 0:
            return ChartConfig(
                type="table",
                title="Query Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical",
            )

        # --- Determine label column ---
        label_col = self._pick_time_like_column(df) if wants_time_series else (str(non_numeric_cols[0]) if non_numeric_cols else None)

        if label_col is None:
            # No suitable label axis: allow scatter when requested, or as a fallback for 2+ numeric metrics.
            if len(numeric_cols) >= 2 and len(df) > 1 and (user_viz_type == "scatter" or user_viz_type is None):
                scatter_primary, scatter_secondary = self._choose_primary_and_secondary_metric(
                    question, [str(c) for c in numeric_cols]
                )
                if scatter_secondary is not None:
                    title = self._generate_title(question, "scatter", scatter_primary, scatter_secondary)
                    return ChartConfig(
                        type="scatter",
                        x_column=scatter_primary,
                        y_column=scatter_secondary,
                        secondary_y_column=None,
                        orientation="vertical",
                        title=title,
                    )

            return ChartConfig(
                type="table",
                title="Query Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical",
            )

        # Prefer using non-label numeric columns as metrics (e.g., day should not be treated as y)
        numeric_metric_cols = [str(c) for c in numeric_cols if str(c) != str(label_col)]
        if len(numeric_metric_cols) == 0:
            return ChartConfig(
                type="table",
                title="Query Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical",
            )

        # --- Case 3: Too Many Columns (>3) → Table (unless it is a pure time-series with extra numeric metrics) ---
        if len(df.columns) > 3:
            extra_non_numeric = [
                str(c)
                for c in df.columns
                if str(c) != str(label_col) and str(c) not in [str(n) for n in numeric_cols]
            ]
            if not (wants_time_series and len(extra_non_numeric) == 0):
                return ChartConfig(
                    type="table",
                    title="Query Results",
                    x_column=None,
                    y_column=None,
                    secondary_y_column=None,
                    orientation="vertical",
                )

        # --- Determine primary + secondary metrics ---
        primary_metric, secondary_metric = self._choose_primary_and_secondary_metric(question, numeric_metric_cols)
        wants_two_metrics = bool(secondary_metric) and self._wants_two_metrics(question)
        secondary_metric_to_plot = secondary_metric if wants_two_metrics else None

        # --- Scatter Plot ---
        # Only choose scatter when explicitly requested, or when there is no suitable label axis.
        if len(numeric_metric_cols) >= 2 and len(df) > 1:
            if user_viz_type == "scatter":
                title = self._generate_title(question, "scatter", primary_metric, secondary_metric)
                return ChartConfig(
                    type="scatter",
                    x_column=primary_metric,
                    y_column=secondary_metric,
                    secondary_y_column=None,
                    orientation="vertical",
                    title=title,
                )

        # --- Time Series Detection ---
        is_time_series = self._is_time_series_column(label_col, df)

        # --- Categories for label-based charts ---
        unique_values = df[label_col].nunique()
        if unique_values > self.config["bar_chart_max_categories"] and not (
            is_time_series or user_viz_type == "line"
        ):
            return ChartConfig(
                type="table",
                title="Query Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical",
            )

        # --- 2-metric results (plot both only if explicitly requested) ---
        if secondary_metric_to_plot is not None:
            if user_viz_type == "line" or (user_viz_type is None and is_time_series):
                title = self._generate_title(question, "line", label_col, primary_metric)
                return ChartConfig(
                    type="line",
                    x_column=label_col,
                    y_column=primary_metric,
                    secondary_y_column=secondary_metric_to_plot,
                    orientation="vertical",
                    title=title,
                )

            max_label_length = df[label_col].astype(str).str.len().max()
            orientation: Literal["horizontal", "vertical"] = (
                "horizontal" if max_label_length > self.config["long_label_threshold"] else "vertical"
            )
            title = self._generate_title(question, "bar", label_col, primary_metric)
            return ChartConfig(
                type="bar",
                x_column=label_col,
                y_column=primary_metric,
                secondary_y_column=secondary_metric_to_plot,
                orientation=orientation,
                title=title,
            )

        # --- Single-metric label-based charts ---
        if user_viz_type == "line" or (user_viz_type is None and is_time_series):
            title = self._generate_title(question, "line", label_col, primary_metric)
            return ChartConfig(
                type="line",
                x_column=label_col,
                y_column=primary_metric,
                secondary_y_column=None,
                orientation="vertical",
                title=title,
            )

        # Pie should only be used when we are plotting a single metric.
        if secondary_metric_to_plot is None and (
            (user_viz_type == "pie" and not wants_two_metrics)
            or (
                user_viz_type is None
                and unique_values <= self.config["pie_chart_max_slices"]
                and unique_values >= 2
                and self._looks_like_proportion_query(question)
            )
        ):
            title = self._generate_title(question, "pie", label_col, primary_metric)
            return ChartConfig(
                type="pie",
                x_column=label_col,  # names/labels
                y_column=primary_metric,  # values
                secondary_y_column=None,
                orientation="vertical",
                title=title,
            )

        # --- Default: Bar Chart ---
        max_label_length = df[label_col].astype(str).str.len().max()
        orientation: Literal["horizontal", "vertical"] = (
            "horizontal" if max_label_length > self.config["long_label_threshold"] else "vertical"
        )

        title = self._generate_title(question, "bar", label_col, primary_metric)
        return ChartConfig(
            type="bar",
            x_column=label_col,
            y_column=primary_metric,
            secondary_y_column=None,
            orientation=orientation,
            title=title,
        )
    
    def prepare_data_for_chart(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig,
        question: str = "",
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Prepare DataFrame for JSON serialization and chart rendering.
        
        Args:
            df: Query result DataFrame
            config: Chart configuration from determine_chart_type
            
        Returns:
            Tuple of (data_list, warnings)
            - data_list: List of dicts for JSON serialization
            - warnings: List of warning messages
        """
        warnings: List[str] = []
        
        if df.empty:
            return [], []
        
        df_viz = df.copy()
        
        # --- Handle aggregation if needed ---
        # Scatter plots represent relationships between numeric metrics and should not be auto-aggregated,
        # otherwise label columns (e.g., client_name) can be collapsed/dropped.
        if config.x_column and config.y_column and config.type not in ("metric", "table", "scatter"):
            df_viz, agg_warnings = self._maybe_aggregate(df_viz, config)
            warnings.extend(agg_warnings)

        # --- Optional: fill missing enum categories for clarity ---
        df_viz, fill_warnings = self._maybe_zero_fill_order_type(df_viz, config, question)
        warnings.extend(fill_warnings)
        
        # --- Sort data appropriately ---
        df_viz = self._sort_data(df_viz, config)

        # --- Truncate time series for readability ---
        if config.type == "line" and config.x_column and config.x_column in df_viz.columns:
            granularity = self._infer_time_series_granularity(config.x_column, df_viz[config.x_column])
            df_viz, ts_warnings = self._truncate_time_series(df_viz, config.x_column, granularity)
            warnings.extend(ts_warnings)
        
        # --- Handle pie chart "Others" grouping ---
        if config.type == "pie" and len(df_viz) > self.config["pie_chart_max_slices"]:
            df_viz, pie_warnings = self._group_pie_others(df_viz, config)
            warnings.extend(pie_warnings)
        
        # --- Limit rows for display (except time series) ---
        is_time_series = config.type == "line"

        max_rows = self._determine_display_row_limit(config, question)
        if not is_time_series and len(df_viz) > max_rows:
            original_count = len(df_viz)
            df_viz = df_viz.head(max_rows)
            if config.type == "table":
                warnings.append(f"Showing top {max_rows} of {original_count} rows")
            else:
                warnings.append(f"Showing top {max_rows} of {original_count} items")
        
        # --- Clean data (remove NaN for charts) ---
        if config.type != "table":
            # Be tolerant of sparse results: keep rows by filling missing labels/metrics when possible.
            if config.type in ("bar", "pie") and config.x_column and config.x_column in df_viz.columns:
                try:
                    if df_viz[config.x_column].isnull().any():
                        df_viz = df_viz.copy()
                        df_viz[config.x_column] = df_viz[config.x_column].fillna("(Unknown)")
                except Exception:
                    pass

            for metric_col in [config.y_column, config.secondary_y_column]:
                if metric_col and metric_col in df_viz.columns:
                    try:
                        if pd.api.types.is_numeric_dtype(df_viz[metric_col]) and df_viz[metric_col].isnull().any():
                            df_viz = df_viz.copy()
                            df_viz[metric_col] = df_viz[metric_col].fillna(0)
                    except Exception:
                        pass

            cols_to_check = [c for c in [config.x_column, config.y_column, config.secondary_y_column] if c]
            if cols_to_check:
                df_viz = df_viz.dropna(subset=[c for c in cols_to_check if c in df_viz.columns])
        
        # --- Convert to list of dicts for JSON ---
        # Handle datetime objects and other non-serializable types
        data_list = self._dataframe_to_json_safe(df_viz)
        
        return data_list, warnings
    
    def format_answer_text(
        self, 
        df: pd.DataFrame, 
        question: str, 
        config: ChartConfig
    ) -> str:
        """
        Generate a natural language summary for the query results.
        
        Args:
            df: Query result DataFrame
            question: Original user question
            config: Chart configuration
            
        Returns:
            str: Natural language answer text
        """
        if df.empty:
            return "No results found for your query."
        
        # --- Single Metric ---
        if config.type == "metric" and len(df) == 1 and len(df.columns) == 1:
            col_name = str(df.columns[0])
            value = df.iloc[0, 0]
            formatted_value = self._format_value(value, col_name)
            label = self._format_column_title(col_name)
            return f"{label}: {formatted_value}"
        
        # --- Extract key info from question ---
        row_count = len(df)
        
        # Try to detect "top N" pattern
        top_match = re.search(r'top\s+(\d+)', question.lower())
        if top_match:
            n = int(top_match.group(1))
            return f"Here are your top {n} results:"
        
        # Try to detect what's being queried
        if config.type == "line":
            if config.y_column:
                metric_name = self._format_column_title(config.y_column)
                return f"Here's the {metric_name} trend:"
        
        if config.type == "pie":
            if config.y_column:
                metric_name = self._format_column_title(config.y_column)
                return f"Here's the distribution of {metric_name}:"
        
        if config.type == "bar":
            if config.y_column and config.x_column:
                metric_name = self._format_column_title(config.y_column)
                dimension_name = self._format_column_title(config.x_column)
                if config.secondary_y_column:
                    secondary_name = self._format_column_title(config.secondary_y_column)
                    return f"Here's {metric_name} and {secondary_name} by {dimension_name}:"
                return f"Here's {metric_name} by {dimension_name}:"
        
        if config.type == "scatter":
            if config.x_column and config.y_column:
                x_name = self._format_column_title(config.x_column)
                y_name = self._format_column_title(config.y_column)
                return f"Here's the relationship between {x_name} and {y_name}:"
        
        if config.type == "table":
            return f"Here are {row_count} results:"
        
        return f"Found {row_count} results:"
    
    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================
    
    def _detect_user_preference(self, question: str) -> Optional[str]:
        """Detect if user explicitly requested a specific chart type."""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['pie chart', 'pie graph', 'use pie', 'as pie', 'show pie']):
            return "pie"
        if any(word in question_lower for word in ['bar chart', 'bar graph', 'use bar', 'as bar', 'show bar']):
            return "bar"
        if any(word in question_lower for word in ['line chart', 'line graph', 'use line', 'as line', 'show line', 'trend']):
            return "line"
        if any(word in question_lower for word in ['table', 'show table', 'as table', 'list all']):
            return "table"
        if any(word in question_lower for word in ['scatter', 'scatter plot', 'correlation', 'relationship']):
            return "scatter"
        
        return None
    
    def _is_time_series_column(self, col_name: str, df: pd.DataFrame) -> bool:
        """Check if a column represents time series data."""
        col_lower = col_name.lower()
        
        # Check column name for time-related keywords
        time_keywords = ['date', 'time', 'month', 'year', 'day', 'week', 'quarter', 'period']
        if any(keyword in col_lower for keyword in time_keywords):
            return True
        
        # Check if column is datetime type
        if col_name in df.columns and pd.api.types.is_datetime64_any_dtype(df[col_name]):
            return True
        
        return False
    
    def _looks_like_proportion_query(self, question: str) -> bool:
        """Check if the question is asking about proportions/distribution."""
        proportion_keywords = [
            'distribution', 'breakdown', 'split', 'proportion', 
            'percentage', 'share', 'by type', 'by category'
        ]
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in proportion_keywords)

    def _wants_time_series(self, question: str, user_viz_type: Optional[str]) -> bool:
        """
        Detect whether the user likely wants a time-series chart.

        We treat explicit line/trend intent as time-series, as well as common granularity hints.
        """
        if user_viz_type == "line":
            return True

        q = (question or "").lower()
        time_series_keywords = [
            "trend",
            "over time",
            "time series",
            "timeseries",
            "daily",
            "weekly",
            "monthly",
            "yearly",
            "by day",
            "by week",
            "by month",
            "by year",
        ]
        return any(kw in q for kw in time_series_keywords)

    def _sample_series_strings(self, series: Any, max_samples: int = 20) -> List[str]:
        """Best-effort sampling of a Series-like object as strings (works with pandas and the test stub)."""
        try:
            values = series.astype(str).head(max_samples).tolist()
            return [str(v) for v in values]
        except Exception:
            values = getattr(series, "_values", None)
            if values is None:
                return []
            return [str(v) for v in list(values)[:max_samples]]

    def _pick_time_like_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        Prefer a time-like column for time-series intent.

        Priority:
        1) Column name tokens include date/time keywords (works even if column is numeric, e.g., day).
        2) Datetime dtype.
        3) Sample values look like YYYY / YYYY-MM / YYYY-MM-DD.
        4) Fallback to first non-numeric column.
        """
        if df is None or df.empty:
            return None

        time_tokens = {"date", "time", "day", "week", "month", "year", "quarter", "period"}

        for col in df.columns:
            col_str = str(col)
            tokens = [t for t in re.split(r"[_\s-]+", col_str.lower()) if t]
            if any(t in time_tokens for t in tokens):
                return col_str

        for col in df.columns:
            col_str = str(col)
            try:
                if pd.api.types.is_datetime64_any_dtype(df[col_str]):
                    return col_str
            except Exception:
                pass

        daily_re = re.compile(r"^\d{4}-\d{2}-\d{2}")
        monthly_re = re.compile(r"^\d{4}-\d{2}$")
        yearly_re = re.compile(r"^\d{4}$")

        for col in df.columns:
            col_str = str(col)
            try:
                samples = self._sample_series_strings(df[col_str], max_samples=20)
            except Exception:
                continue
            if any(daily_re.match(v) for v in samples):
                return col_str
            if any(monthly_re.match(v) for v in samples):
                return col_str
            if any(yearly_re.match(v) for v in samples):
                return col_str

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        non_numeric_cols = [col for col in df.columns if col not in numeric_cols]
        return str(non_numeric_cols[0]) if non_numeric_cols else None

    def _infer_time_series_granularity(
        self, x_column_name: str, series: Any
    ) -> Literal["daily", "monthly", "yearly"]:
        name = (x_column_name or "").lower()
        tokens = [t for t in re.split(r"[_\s-]+", name) if t]
        if "year" in tokens:
            return "yearly"
        if "month" in tokens:
            return "monthly"
        if "day" in tokens or "date" in tokens or "time" in tokens:
            return "daily"

        samples = self._sample_series_strings(series, max_samples=20)
        if any(re.match(r"^\d{4}-\d{2}-\d{2}", v) for v in samples):
            return "daily"
        if any(re.match(r"^\d{4}-\d{2}$", v) for v in samples):
            return "monthly"
        if any(re.match(r"^\d{4}$", v) for v in samples):
            return "yearly"

        return "daily"

    def _truncate_time_series(
        self, df: pd.DataFrame, x_col: str, granularity: Literal["daily", "monthly", "yearly"]
    ) -> Tuple[pd.DataFrame, List[str]]:
        warnings: List[str] = []

        max_points_by_granularity = {
            "daily": int(self.config["max_time_series_points_daily"]),
            "monthly": int(self.config["max_time_series_points_monthly"]),
            "yearly": int(self.config["max_time_series_points_yearly"]),
        }
        max_points = max_points_by_granularity.get(granularity, int(self.config["max_time_series_points_daily"]))

        if len(df) > max_points:
            original_count = len(df)
            df = df.tail(max_points)
            warnings.append(
                f"Showing last {max_points} {granularity} points (out of {original_count}) for readability."
            )

        return df, warnings

    def _wants_two_metrics(self, question: str) -> bool:
        """
        True when the user explicitly asks for both a count-like metric and a revenue-like metric.
        """
        q = (question or "").lower()
        wants_orders = any(kw in q for kw in ["how many", "order count", "orders", "count", "number of"])
        wants_revenue = any(kw in q for kw in ["revenue", "sales", "amount", "aed"])
        return wants_orders and wants_revenue

    def _extract_order_type_mentions(self, question: str) -> set[str]:
        q = (question or "").lower()
        mentions: set[str] = set()

        if re.search(r"\bgift\s*cards?\b", q) or re.search(r"\bgift[_-]?cards?\b", q) or re.search(
            r"\bgiftcards?\b", q
        ):
            mentions.add("gift_card")

        if re.search(r"\bmerch(?:andise)?\b", q):
            mentions.add("merchandise")

        return mentions

    def _maybe_zero_fill_order_type(
        self, df: pd.DataFrame, config: ChartConfig, question: str
    ) -> Tuple[pd.DataFrame, List[str]]:
        warnings: List[str] = []

        if not question or config.type in ("metric", "table"):
            return df, warnings

        if not config.x_column or config.x_column != "order_type":
            return df, warnings

        mentions = self._extract_order_type_mentions(question)
        expected = {"gift_card", "merchandise"}
        if not (mentions.issuperset(expected)):
            return df, warnings

        if "order_type" not in df.columns:
            return df, warnings

        try:
            existing = set(df["order_type"].astype(str).str.strip().str.lower().tolist())
        except Exception:
            existing = set(str(v).strip().lower() for v in list(df["order_type"]))

        missing = expected - existing
        if not missing:
            return df, warnings

        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        for missing_value in sorted(missing):
            row: Dict[str, Any] = {"order_type": missing_value}
            for col in numeric_cols:
                row[col] = 0
            if config.y_column and config.y_column in df.columns:
                row[config.y_column] = 0
            if config.secondary_y_column and config.secondary_y_column in df.columns:
                row[config.secondary_y_column] = 0

            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            warnings.append(
                f"Added missing order_type category '{missing_value}' with 0 to match the question."
            )

        return df, warnings

    def _choose_primary_and_secondary_metric(
        self, question: str, numeric_cols: List[str]
    ) -> Tuple[str, Optional[str]]:
        """
        Choose primary/secondary metrics for multi-metric results.

        Rules:
        - If the question implies count/orders/"how many", prefer an orders-like column as primary.
        - If the question implies revenue/sales/amount/AED, prefer a revenue-like column as primary.
        - Otherwise prefer revenue-like if present; else first numeric.
        """
        if not numeric_cols:
            return "value", None

        q = (question or "").lower()
        prefers_orders = any(kw in q for kw in ["how many", "count", "number of", "orders", "order count"])
        prefers_revenue = any(kw in q for kw in ["revenue", "sales", "amount", "aed"])

        def _tokens(col: str) -> List[str]:
            return [t for t in re.split(r"[_\s-]+", (col or "").lower()) if t]

        def _find_first(pred) -> Optional[str]:
            for col in numeric_cols:
                if pred(col):
                    return col
            return None

        orders_col = _find_first(
            lambda c: ("orders" in _tokens(c)) or ("order" in _tokens(c) and "count" in _tokens(c))
        )
        revenue_col = _find_first(
            lambda c: any(t in _tokens(c) for t in ["revenue", "sales", "amount", "aed", "price"])
        )

        primary = numeric_cols[0]
        if prefers_orders and orders_col:
            primary = orders_col
        elif prefers_revenue and revenue_col:
            primary = revenue_col
        else:
            primary = revenue_col or numeric_cols[0]

        secondary: Optional[str] = None
        if len(numeric_cols) >= 2:
            if primary == orders_col and revenue_col and revenue_col != primary:
                secondary = revenue_col
            elif primary == revenue_col and orders_col and orders_col != primary:
                secondary = orders_col
            else:
                secondary = next((c for c in numeric_cols if c != primary), None)

        return primary, secondary

    def _format_column_title(self, col_name: str) -> str:
        """Format a column name as a readable title."""
        return col_name.replace("_", " ").replace("-", " ").title()
    
    def _format_value(self, value: Any, col_name: str) -> str:
        """Format a value for display based on its type and column name."""
        if pd.isna(value):
            return "No Data"
        
        if isinstance(value, (int, float)):
            # Check if it's a currency/revenue column
            col_lower = col_name.lower()
            if any(word in col_lower for word in ['revenue', 'price', 'cost', 'amount', 'value', 'total', 'sum']):
                return f"AED {value:,.2f}"
            elif any(word in col_lower for word in ['count', 'quantity', 'orders', 'num']):
                return f"{int(value):,}"
            elif any(word in col_lower for word in ['percent', 'pct', 'rate', 'margin']):
                return f"{value:.1f}%"
            else:
                return f"{value:,.2f}"
        
        return str(value)
    
    def _generate_title(
        self, 
        question: str, 
        chart_type: str, 
        primary_col: str, 
        secondary_col: Optional[str] = None
    ) -> str:
        """Generate a chart title based on question and columns."""
        # Try to extract a meaningful title from the question
        question_clean = question.strip()
        if question_clean and len(question_clean) < 60:
            # Use the question as title (capitalized)
            return question_clean.capitalize().rstrip("?")
        
        # Generate title from columns
        primary_title = self._format_column_title(primary_col)
        
        if chart_type == "line":
            return f"{secondary_col and self._format_column_title(secondary_col) or 'Value'} Over Time"
        elif chart_type == "pie":
            return f"Distribution by {primary_title}"
        elif chart_type == "scatter":
            if secondary_col:
                secondary_title = self._format_column_title(secondary_col)
                return f"{primary_title} vs {secondary_title}"
            return f"{primary_title} Analysis"
        elif chart_type == "bar":
            if secondary_col:
                secondary_title = self._format_column_title(secondary_col)
                return f"{secondary_title} by {primary_title}"
            return f"{primary_title} Analysis"
        
        return "Query Results"
    
    def _maybe_aggregate(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Aggregate data if needed (raw transactions → grouped)."""
        warnings: List[str] = []
        
        if not config.x_column or not config.y_column:
            return df, warnings
            
        if config.x_column not in df.columns or config.y_column not in df.columns:
            return df, warnings
        
        label_col = config.x_column
        value_col = config.y_column

        # Avoid treating NULL label values as "duplicates" (pandas nunique() drops NaNs by default),
        # which can trigger bogus aggregation and drop rows via groupby.
        try:
            if df[label_col].isnull().any():
                df = df.copy()
                df[label_col] = df[label_col].fillna("(Unknown)")
        except Exception:
            pass
        
        # Check if data needs aggregation
        unique_labels = df[label_col].nunique()
        needs_aggregation = unique_labels < len(df)
        
        if needs_aggregation and pd.api.types.is_numeric_dtype(df[value_col]):
            # Data needs aggregation - likely raw transactions
            warnings.append(
                f"Auto-aggregated {len(df)} rows into {unique_labels} groups by {label_col}."
            )
            
            # Aggregate all numeric columns
            agg_cols = [value_col]
            if config.secondary_y_column and config.secondary_y_column in df.columns:
                agg_cols.append(config.secondary_y_column)
            
            df = df.groupby(label_col, as_index=False)[agg_cols].sum()
        
        return df, warnings
    
    def _sort_data(self, df: pd.DataFrame, config: ChartConfig) -> pd.DataFrame:
        """Sort data appropriately based on chart type."""
        if config.type == "line" and config.x_column:
            # Time series: sort by x column
            try:
                if pd.api.types.is_numeric_dtype(df[config.x_column]):
                    return df.sort_values(by=config.x_column)
            except Exception:
                pass

            try:
                df = df.copy()
                # Try to convert to datetime for proper sorting
                df[config.x_column] = pd.to_datetime(df[config.x_column], errors="coerce")
                df = df.sort_values(by=config.x_column)
            except Exception:
                pass
        elif config.type in ("bar", "pie") and config.y_column:
            # Bar/Pie: sort by value descending (prefer revenue for 2-metric breakdowns)
            try:
                sort_col = config.y_column
                preferred = self._pick_preferred_sort_metric(config)
                if preferred and preferred in df.columns:
                    sort_col = preferred
                df = df.sort_values(by=sort_col, ascending=False)
            except Exception:
                pass
        elif config.type == "scatter" and config.x_column and config.y_column:
            # Scatter: when truncating to max_display_rows, keep the "most important" points.
            # Prefer revenue-like metrics; otherwise sort by y_column descending.
            def _is_revenue_like(col: str) -> bool:
                tokens = set(re.split(r"[_\s-]+", (col or "").lower()))
                return bool(tokens & {"revenue", "sales", "amount", "aed"})

            try:
                sort_col = (
                    config.x_column
                    if _is_revenue_like(config.x_column)
                    else (config.y_column if _is_revenue_like(config.y_column) else config.y_column)
                )
                df = df.sort_values(by=sort_col, ascending=False)
            except Exception:
                pass
        
        return df

    def _extract_requested_top_n(self, question: str) -> int | None:
        match = re.search(r"\btop\s+(\d{1,4})\b", (question or "").lower())
        if not match:
            return None
        try:
            n = int(match.group(1))
        except Exception:
            return None
        return n if n > 0 else None

    def _determine_display_row_limit(self, config: ChartConfig, question: str) -> int:
        """
        Decide how many rows to include in `data` for frontend rendering.

        Defaults:
        - Tables: max_table_rows
        - Charts: max_display_rows

        Special-case:
        - Dual-metric horizontal bar charts also render a table on the frontend, so cap to max_table_rows
          and respect explicit "top N" questions up to that cap.
        - Scatter plots respect explicit "top N" up to max_display_rows.
        """
        max_table_rows = int(self.config["max_table_rows"])
        max_display_rows = int(self.config["max_display_rows"])

        if config.type == "scatter":
            requested_top_n = self._extract_requested_top_n(question)
            if requested_top_n is None:
                return max_display_rows
            return min(requested_top_n, max_display_rows)

        if (
            config.type == "bar"
            and bool(config.secondary_y_column)
            and (config.orientation or "").lower() == "horizontal"
        ):
            requested_top_n = self._extract_requested_top_n(question)
            if requested_top_n is None:
                return max_table_rows
            return min(requested_top_n, max_table_rows)

        if config.type == "table":
            requested_top_n = self._extract_requested_top_n(question)
            if requested_top_n is None:
                return max_table_rows
            return min(requested_top_n, max_table_rows)

        return max_display_rows

    def _pick_preferred_sort_metric(self, config: ChartConfig) -> str | None:
        """
        For multi-metric results, prefer sorting by revenue over orders when both are present.
        """
        candidates: list[str] = []
        if config.y_column:
            candidates.append(str(config.y_column))
        if config.secondary_y_column:
            candidates.append(str(config.secondary_y_column))

        def _tokens(col: str) -> list[str]:
            return [t for t in re.split(r"[_\s-]+", (col or "").lower()) if t]

        for col in candidates:
            tokens = set(_tokens(col))
            if tokens & {"revenue", "sales", "amount", "aed"}:
                return col

        return candidates[0] if candidates else None
    
    def _group_pie_others(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
    ) -> Tuple[pd.DataFrame, List[str]]:
        """Group small pie slices into 'Others'."""
        warnings: List[str] = []
        
        if not config.x_column or not config.y_column:
            return df, warnings
            
        if config.x_column not in df.columns or config.y_column not in df.columns:
            return df, warnings
        
        label_col = config.x_column
        value_col = config.y_column
        max_slices = self.config["pie_chart_max_slices"]
        
        if len(df) > max_slices:
            # Sort by value descending
            df = df.sort_values(by=value_col, ascending=False)
            
            # Take top (max_slices - 1) and group rest as "Others"
            top_items = df.head(max_slices - 1)
            remaining = df.iloc[max_slices - 1:]
            
            if len(remaining) > 0:
                others_value = remaining[value_col].sum()
                others_row = pd.DataFrame({
                    label_col: ["Others"],
                    value_col: [others_value]
                })
                df = pd.concat([top_items, others_row], ignore_index=True)
                warnings.append(
                    f"Grouped {len(remaining)} smaller items into 'Others' for readability"
                )
        
        return df, warnings
    
    def _dataframe_to_json_safe(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Convert DataFrame to JSON-serializable list of dicts."""
        # Convert datetime columns to ISO strings
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
        
        # Convert to records and cast properly
        records: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            record: Dict[str, Any] = {}
            for col in df.columns:
                value = row[col]
                if pd.isna(value):
                    record[str(col)] = None
                else:
                    if isinstance(value, (datetime, date)):
                        record[str(col)] = value.isoformat()
                        continue
                    if isinstance(value, Decimal):
                        record[str(col)] = float(value)
                        continue

                    item = getattr(value, "item", None)
                    if callable(item):
                        try:
                            record[str(col)] = item()
                            continue
                        except Exception:
                            pass

                    record[str(col)] = value
            records.append(record)
        
        return records


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_smart_render_service() -> SmartRenderService:
    """Factory function to get a configured SmartRenderService instance."""
    return SmartRenderService()
