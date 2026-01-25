"""
SmartRender Service for intelligent visualization selection.
Ports the smart_render() function from app.py to return configuration objects
instead of rendering directly. The frontend (React/Recharts) renders based on the config.
"""
import re
import pandas as pd
from typing import Tuple, List, Dict, Any, Optional, Literal, cast

from app.models import ChartConfig


# ============================================================================
# CONFIGURATION
# ============================================================================

SMART_RENDER_CONFIG = {
    "max_display_rows": 15,         # Maximum rows to display in charts
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
        
        # --- Detect numeric and non-numeric columns ---
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        non_numeric_cols = [col for col in df.columns if col not in numeric_cols]
        
        # --- Case 3: Too Many Columns (>3) or No Numeric Columns → Table ---
        if len(df.columns) > 3 or len(numeric_cols) == 0:
            return ChartConfig(
                type="table", 
                title="Query Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical"
            )
        
        # --- Determine label and value columns ---
        label_col = str(non_numeric_cols[0]) if non_numeric_cols else str(df.columns[0])
        value_col = str(numeric_cols[0])
        secondary_value_col = str(numeric_cols[1]) if len(numeric_cols) >= 2 else None
        
        # --- Check for user explicit chart type request ---
        user_viz_type = self._detect_user_preference(question)
        
        # --- Case 4: Scatter Plot (2+ numeric columns) ---
        if user_viz_type == "scatter" or (
            user_viz_type is None and 
            secondary_value_col is not None and 
            len(df) > 1
        ):
            title = self._generate_title(question, "scatter", value_col, secondary_value_col)
            return ChartConfig(
                type="scatter",
                x_column=value_col,
                y_column=secondary_value_col,
                secondary_y_column=None,
                orientation="vertical",
                title=title
            )
        
        # --- Case 5: Time Series Detection → Line Chart ---
        is_time_series = self._is_time_series_column(label_col, df)
        
        if user_viz_type == "line" or (user_viz_type is None and is_time_series):
            title = self._generate_title(question, "line", label_col, value_col)
            return ChartConfig(
                type="line",
                x_column=label_col,
                y_column=value_col,
                secondary_y_column=None,
                orientation="vertical",
                title=title
            )
        
        # --- Case 6: Pie Chart (few categories) ---
        unique_values = df[label_col].nunique()
        
        if user_viz_type == "pie" or (
            user_viz_type is None and 
            unique_values <= self.config["pie_chart_max_slices"] and
            unique_values >= 2 and
            self._looks_like_proportion_query(question)
        ):
            title = self._generate_title(question, "pie", label_col, value_col)
            return ChartConfig(
                type="pie",
                x_column=label_col,  # names/labels
                y_column=value_col,   # values
                secondary_y_column=None,
                orientation="vertical",
                title=title
            )
        
        # --- Case 7: Too many categories for chart → Table ---
        if unique_values > self.config["bar_chart_max_categories"]:
            return ChartConfig(
                type="table", 
                title="Query Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical"
            )
        
        # --- Case 8: User explicitly wants table ---
        if user_viz_type == "table":
            return ChartConfig(
                type="table", 
                title="Query Results",
                x_column=None,
                y_column=None,
                secondary_y_column=None,
                orientation="vertical"
            )
        
        # --- Default: Bar Chart ---
        # Detect long labels for horizontal orientation
        max_label_length = df[label_col].astype(str).str.len().max()
        orientation: Literal["horizontal", "vertical"] = (
            "horizontal" if max_label_length > self.config["long_label_threshold"] else "vertical"
        )
        
        title = self._generate_title(question, "bar", label_col, value_col)
        return ChartConfig(
            type="bar",
            x_column=label_col,
            y_column=value_col,
            secondary_y_column=None,
            orientation=orientation,
            title=title
        )
    
    def prepare_data_for_chart(
        self, 
        df: pd.DataFrame, 
        config: ChartConfig
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
        if config.x_column and config.y_column and config.type not in ("metric", "table"):
            df_viz, agg_warnings = self._maybe_aggregate(df_viz, config)
            warnings.extend(agg_warnings)
        
        # --- Sort data appropriately ---
        df_viz = self._sort_data(df_viz, config)
        
        # --- Handle pie chart "Others" grouping ---
        if config.type == "pie" and len(df_viz) > self.config["pie_chart_max_slices"]:
            df_viz, pie_warnings = self._group_pie_others(df_viz, config)
            warnings.extend(pie_warnings)
        
        # --- Limit rows for display (except time series) ---
        is_time_series = config.type == "line"
        
        if not is_time_series and len(df_viz) > self.config["max_display_rows"]:
            original_count = len(df_viz)
            df_viz = df_viz.head(self.config["max_display_rows"])
            warnings.append(f"Showing top {self.config['max_display_rows']} of {original_count} items")
        
        # --- Clean data (remove NaN for charts) ---
        if config.type != "table":
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
        
        # Check if data needs aggregation
        # If every row has a unique label, data is NOT aggregated
        unique_labels = df[label_col].nunique()
        is_aggregated = unique_labels < len(df)
        
        if not is_aggregated and pd.api.types.is_numeric_dtype(df[value_col]):
            # Data needs aggregation - likely raw transactions
            warnings.append(f"Auto-aggregated {len(df)} raw transactions")
            
            # Aggregate all numeric columns
            agg_cols = [value_col]
            if config.secondary_y_column and config.secondary_y_column in df.columns:
                agg_cols.append(config.secondary_y_column)
            
            df = df.groupby(label_col, as_index=False)[agg_cols].sum()
        
        return df, warnings
    
    def _sort_data(self, df: pd.DataFrame, config: ChartConfig) -> pd.DataFrame:
        """Sort data appropriately based on chart type."""
        if config.type == "line" and config.x_column:
            # Time series: sort by date
            try:
                df = df.copy()
                # Try to convert to datetime for proper sorting
                df[config.x_column] = pd.to_datetime(df[config.x_column], errors='coerce')
                df = df.sort_values(by=config.x_column)
            except Exception:
                pass
        elif config.type in ("bar", "pie") and config.y_column:
            # Bar/Pie: sort by value descending
            try:
                df = df.sort_values(by=config.y_column, ascending=False)
            except Exception:
                pass
        
        return df
    
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
                    record[str(col)] = value
            records.append(record)
        
        return records


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def get_smart_render_service() -> SmartRenderService:
    """Factory function to get a configured SmartRenderService instance."""
    return SmartRenderService()
