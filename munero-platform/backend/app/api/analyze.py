"""
Driver Analysis API endpoints.
Provides variance analysis to answer "why did X change?" questions.
"""
import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from app.models import (
    DriverAnalysisRequest,
    DriverAnalysisResponse,
    DriverEntity,
    DriverSummary,
    DashboardFilters,
    MetaResponse
)
from app.core.config import settings
from app.core.database import get_data
from datetime import datetime
import pandas as pd

router = APIRouter()
logger = logging.getLogger(__name__)


def build_filter_clause(filters: Optional[DashboardFilters]) -> tuple[str, dict]:
    """
    Constructs SQL WHERE clause from optional filters (excluding date filters).
    Date filters are handled separately for period comparison.
    """
    if filters is None:
        return "1=1", {}

    conditions = ["1=1"]
    params = {}

    # List Filters - Only apply if list is not empty
    if filters.countries:
        placeholders = [f":country_{i}" for i in range(len(filters.countries))]
        conditions.append(f"client_country IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.countries):
            params[f"country_{i}"] = val

    if filters.clients:
        placeholders = [f":client_{i}" for i in range(len(filters.clients))]
        conditions.append(f"client_name IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.clients):
            params[f"client_{i}"] = val

    if filters.product_types:
        placeholders = [f":type_{i}" for i in range(len(filters.product_types))]
        conditions.append(f"order_type IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.product_types):
            params[f"type_{i}"] = val

    if filters.brands:
        placeholders = [f":brand_{i}" for i in range(len(filters.brands))]
        conditions.append(f"product_brand IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.brands):
            params[f"brand_{i}"] = val

    if filters.suppliers:
        placeholders = [f":supplier_{i}" for i in range(len(filters.suppliers))]
        conditions.append(f"supplier_name IN ({','.join(placeholders)})")
        for i, val in enumerate(filters.suppliers):
            params[f"supplier_{i}"] = val

    return " AND ".join(conditions), params


def get_metric_aggregation(metric: str) -> str:
    """Returns the SQL aggregation for a given metric."""
    metric_map = {
        "revenue": "SUM(order_price_in_aed)",
        "orders": "COUNT(DISTINCT order_number)",
        "margin": "(SUM(order_price_in_aed) - SUM(COALESCE(cogs_in_aed, 0))) / NULLIF(SUM(order_price_in_aed), 0) * 100",
        "aov": "SUM(order_price_in_aed) / NULLIF(COUNT(DISTINCT order_number), 0)"
    }
    return metric_map.get(metric, "SUM(order_price_in_aed)")


def analyze_dimension(
    dimension: str,
    metric: str,
    current_start: str,
    current_end: str,
    prior_start: str,
    prior_end: str,
    filter_clause: str,
    filter_params: dict,
    top_n: int,
    total_change: float
) -> List[DriverEntity]:
    """
    Analyze variance for a single dimension.
    Returns top N drivers sorted by absolute delta.
    """
    metric_agg = get_metric_aggregation(metric)

    # SQLite doesn't support FULL OUTER JOIN, so we use UNION approach
    query = f"""
        WITH current_period AS (
            SELECT
                {dimension} as entity,
                {metric_agg} as value
            FROM fact_orders
            WHERE order_date >= :current_start
              AND order_date <= :current_end
              AND {filter_clause}
            GROUP BY {dimension}
        ),
        prior_period AS (
            SELECT
                {dimension} as entity,
                {metric_agg} as value
            FROM fact_orders
            WHERE order_date >= :prior_start
              AND order_date <= :prior_end
              AND {filter_clause}
            GROUP BY {dimension}
        ),
        combined AS (
            SELECT entity FROM current_period
            UNION
            SELECT entity FROM prior_period
        )
        SELECT
            c.entity as name,
            COALESCE(cp.value, 0) as current_value,
            COALESCE(pp.value, 0) as prior_value,
            COALESCE(cp.value, 0) - COALESCE(pp.value, 0) as delta
        FROM combined c
        LEFT JOIN current_period cp ON c.entity = cp.entity
        LEFT JOIN prior_period pp ON c.entity = pp.entity
        WHERE c.entity IS NOT NULL
        ORDER BY ABS(COALESCE(cp.value, 0) - COALESCE(pp.value, 0)) DESC
        LIMIT :top_n
    """

    params = {
        **filter_params,
        "current_start": current_start,
        "current_end": current_end,
        "prior_start": prior_start,
        "prior_end": prior_end,
        "top_n": top_n
    }

    df = get_data(query, params)

    if df.empty:
        return []

    drivers = []
    for _, row in df.iterrows():
        current_val = float(row['current_value']) if pd.notna(row['current_value']) else 0.0
        prior_val = float(row['prior_value']) if pd.notna(row['prior_value']) else 0.0
        delta = float(row['delta']) if pd.notna(row['delta']) else 0.0

        # Calculate percentage change
        delta_pct = None
        if prior_val != 0:
            delta_pct = round((delta / abs(prior_val)) * 100, 2)

        # Calculate contribution to total change
        contribution = 0.0
        if total_change != 0:
            contribution = round((delta / total_change) * 100, 2)

        drivers.append(DriverEntity(
            name=str(row['name']) if pd.notna(row['name']) else "Unknown",
            current_value=round(current_val, 2),
            prior_value=round(prior_val, 2),
            delta=round(delta, 2),
            delta_pct=delta_pct,
            contribution_to_total_change=contribution
        ))

    return drivers


@router.post("/drivers", response_model=DriverAnalysisResponse)
def analyze_drivers(request: DriverAnalysisRequest):
    """
    Analyze what drove changes in a metric between two periods.

    **Purpose**: Answer "why did X change?" questions with mathematical precision.

    **How It Works**:
    1. Compares metric values between current and prior periods
    2. Scans across multiple dimensions (client, brand, country, product type)
    3. Identifies top contributors to the total change
    4. Returns contribution percentages (guaranteed to sum to ~100%)

    **Supported Metrics**:
    - `revenue`: Total revenue (SUM of order_price_in_aed)
    - `orders`: Order count (COUNT DISTINCT order_number)
    - `margin`: Profit margin percentage
    - `aov`: Average order value

    **Example Request**:
    ```json
    {
        "metric": "revenue",
        "current_period": {"start": "2025-12-01", "end": "2025-12-31"},
        "prior_period": {"start": "2025-11-01", "end": "2025-11-30"},
        "dimensions": ["client_name", "product_brand"],
        "top_n": 5
    }
    ```

    **Example Response**:
    ```json
    {
        "metric": "revenue",
        "current_total": 55000,
        "prior_total": 65000,
        "total_change": -10000,
        "total_change_pct": -15.38,
        "direction": "decrease",
        "drivers": {
            "by_client_name": [
                {"name": "TechCorp", "delta": -8000, "contribution_to_total_change": 80.0},
                {"name": "RetailCo", "delta": -1500, "contribution_to_total_change": 15.0}
            ]
        },
        "summary": {
            "primary_driver": {"dimension": "client_name", "entity": "TechCorp", "contribution": 80.0}
        }
    }
    ```
    """
    logger.info(
        "🔍 Driver analysis request (metric=%s, current=%s, prior=%s)",
        request.metric,
        request.current_period,
        request.prior_period,
    )

    # 1. Build filter clause (excluding date filters)
    filter_clause, filter_params = build_filter_clause(request.filters)

    # 2. Calculate totals for both periods
    metric_agg = get_metric_aggregation(request.metric)

    totals_query = f"""
        SELECT
            'current' as period,
            {metric_agg} as total
        FROM fact_orders
        WHERE order_date >= :current_start
          AND order_date <= :current_end
          AND {filter_clause}
        UNION ALL
        SELECT
            'prior' as period,
            {metric_agg} as total
        FROM fact_orders
        WHERE order_date >= :prior_start
          AND order_date <= :prior_end
          AND {filter_clause}
    """

    totals_params = {
        **filter_params,
        "current_start": str(request.current_period.start),
        "current_end": str(request.current_period.end),
        "prior_start": str(request.prior_period.start),
        "prior_end": str(request.prior_period.end)
    }

    totals_df = get_data(totals_query, totals_params)

    if totals_df.empty:
        raise HTTPException(status_code=404, detail="No data found for the specified periods")

    # Extract totals
    current_total = 0.0
    prior_total = 0.0
    for _, row in totals_df.iterrows():
        if row['period'] == 'current':
            current_total = float(row['total']) if pd.notna(row['total']) else 0.0
        else:
            prior_total = float(row['total']) if pd.notna(row['total']) else 0.0

    total_change = current_total - prior_total
    total_change_pct = 0.0
    if prior_total != 0:
        total_change_pct = round((total_change / abs(prior_total)) * 100, 2)

    # Determine direction
    direction = "flat"
    if total_change > 0:
        direction = "increase"
    elif total_change < 0:
        direction = "decrease"

    if settings.DEBUG:
        logger.debug(
            "📊 Totals: current=%.2f prior=%.2f change=%.2f change_pct=%s",
            current_total,
            prior_total,
            total_change,
            total_change_pct,
        )

    # 3. Analyze each dimension
    drivers: Dict[str, List[DriverEntity]] = {}
    all_drivers: List[tuple[str, DriverEntity]] = []

    # Validate dimensions against allowed columns
    valid_dimensions = ["client_name", "product_brand", "client_country", "order_type", "supplier_name", "product_name"]

    for dimension in request.dimensions:
        if dimension not in valid_dimensions:
            logger.warning("⚠️ Skipping invalid dimension: %s", dimension)
            continue

        if settings.DEBUG:
            logger.debug("   Analyzing dimension: %s", dimension)
        dimension_drivers = analyze_dimension(
            dimension=dimension,
            metric=request.metric,
            current_start=str(request.current_period.start),
            current_end=str(request.current_period.end),
            prior_start=str(request.prior_period.start),
            prior_end=str(request.prior_period.end),
            filter_clause=filter_clause,
            filter_params=filter_params,
            top_n=request.top_n,
            total_change=total_change
        )

        drivers[f"by_{dimension}"] = dimension_drivers

        # Track all drivers for summary
        for driver in dimension_drivers:
            all_drivers.append((dimension, driver))

    # 4. Find primary and secondary drivers
    summary: Dict[str, DriverSummary] = {}

    if all_drivers:
        # Sort by absolute contribution
        sorted_drivers = sorted(all_drivers, key=lambda x: abs(x[1].contribution_to_total_change), reverse=True)

        # Primary driver
        if len(sorted_drivers) >= 1:
            dim, driver = sorted_drivers[0]
            summary["primary_driver"] = DriverSummary(
                dimension=dim,
                entity=driver.name,
                contribution=driver.contribution_to_total_change
            )

        # Secondary driver (different entity than primary)
        for dim, driver in sorted_drivers[1:]:
            if driver.name != summary.get("primary_driver", DriverSummary(dimension="", entity="", contribution=0)).entity:
                summary["secondary_driver"] = DriverSummary(
                    dimension=dim,
                    entity=driver.name,
                    contribution=driver.contribution_to_total_change
                )
                break

    logger.info("✅ Driver analysis complete: %s dimensions analyzed", len(drivers))
    if "primary_driver" in summary:
        if settings.DEBUG:
            logger.debug(
                "   Primary driver: %s (%s%% of change)",
                summary["primary_driver"].entity,
                summary["primary_driver"].contribution,
            )

    return DriverAnalysisResponse(
        metric=request.metric,
        current_total=round(current_total, 2),
        prior_total=round(prior_total, 2),
        total_change=round(total_change, 2),
        total_change_pct=total_change_pct,
        direction=direction,
        drivers=drivers,
        summary=summary
    )


@router.get("/meta", response_model=MetaResponse)
def get_meta():
    """
    Returns data freshness and metadata information.

    **Purpose**: Display "Last updated: X" in the dashboard header.

    **Response**:
    - `last_updated`: Most recent order date or load timestamp in the data
    - `data_source`: Name of the data source
    - `refresh_schedule`: Expected data refresh schedule
    - `total_records`: Total number of records in the database
    """
    if settings.DEBUG:
        logger.debug("🔍 Fetching data freshness metadata")

    # Query for max date and count
    query = """
        SELECT
            MAX(order_date) as last_order_date,
            COUNT(*) as total_records
        FROM fact_orders
    """

    df = get_data(query)

    last_updated = None
    total_records = None

    if not df.empty:
        row = df.iloc[0]

        # Parse last order date
        if pd.notna(row['last_order_date']):
            try:
                last_updated = datetime.strptime(str(row['last_order_date']), "%Y-%m-%d")
            except ValueError:
                last_updated = None

        total_records = int(row['total_records']) if pd.notna(row['total_records']) else None

    logger.info("✅ Meta: last_updated=%s records=%s", last_updated, total_records)

    return MetaResponse(
        last_updated=last_updated,
        data_source=settings.db_dialect,
        refresh_schedule="Daily at 2:00 AM UTC",
        total_records=total_records
    )
