#!/usr/bin/env python3
# filepath: /Users/zmasarweh/Documents/Munero_Hybrid_Dashboard/munero-platform/scripts/test_smart_render.py
"""
Test script for the SmartRender Service.
Tests chart type detection and data preparation.
"""
import sys
import os

# Add the backend app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pandas as pd
from app.services.smart_render import SmartRenderService


def test_service():
    print("=" * 60)
    print("SMART RENDER SERVICE TEST")
    print("=" * 60)
    
    # Initialize the service
    print("\n1. Initializing SmartRenderService...")
    service = SmartRenderService()
    print(f"   ✓ Config: {service.config}")
    
    # Test 1: Bar Chart
    print("\n2. Testing Bar Chart Detection...")
    df_bar = pd.DataFrame({
        "product_name": ["Product A", "Product B", "Product C", "Product D", "Product E"],
        "revenue": [10000, 8000, 6000, 4000, 2000]
    })
    config = service.determine_chart_type(df_bar, "top products by revenue")
    print(f"   ✓ Type: {config.type}")
    print(f"   ✓ X Column: {config.x_column}")
    print(f"   ✓ Y Column: {config.y_column}")
    print(f"   ✓ Orientation: {config.orientation}")
    print(f"   ✓ Title: {config.title}")
    assert config.type == "bar", f"Expected 'bar', got '{config.type}'"
    
    # Test 2: Line Chart (Time Series)
    print("\n3. Testing Line Chart Detection (Time Series)...")
    df_line = pd.DataFrame({
        "month": ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05"],
        "revenue": [10000, 12000, 11000, 15000, 13000]
    })
    config = service.determine_chart_type(df_line, "monthly revenue trend")
    print(f"   ✓ Type: {config.type}")
    print(f"   ✓ X Column: {config.x_column}")
    print(f"   ✓ Y Column: {config.y_column}")
    print(f"   ✓ Title: {config.title}")
    assert config.type == "line", f"Expected 'line', got '{config.type}'"
    
    # Test 3: Single Metric (KPI)
    print("\n4. Testing Metric Detection (Single Value)...")
    df_metric = pd.DataFrame({
        "total_revenue": [4567890.00]
    })
    config = service.determine_chart_type(df_metric, "total revenue")
    print(f"   ✓ Type: {config.type}")
    print(f"   ✓ Title: {config.title}")
    assert config.type == "metric", f"Expected 'metric', got '{config.type}'"
    
    # Test 4: Pie Chart (Distribution)
    print("\n5. Testing Pie Chart Detection...")
    df_pie = pd.DataFrame({
        "order_type": ["gift_cards", "merchandise", "vouchers"],
        "revenue": [50000, 30000, 20000]
    })
    config = service.determine_chart_type(df_pie, "revenue distribution by type")
    print(f"   ✓ Type: {config.type}")
    print(f"   ✓ X Column: {config.x_column}")
    print(f"   ✓ Y Column: {config.y_column}")
    print(f"   ✓ Title: {config.title}")
    assert config.type == "pie", f"Expected 'pie', got '{config.type}'"
    
    # Test 5: Scatter Plot (Two Numeric Columns)
    print("\n6. Testing Scatter Plot Detection...")
    df_scatter = pd.DataFrame({
        "client_name": ["Client A", "Client B", "Client C", "Client D"],
        "orders": [100, 80, 150, 60],
        "revenue": [50000, 40000, 75000, 30000]
    })
    config = service.determine_chart_type(df_scatter, "orders vs revenue")
    print(f"   ✓ Type: {config.type}")
    print(f"   ✓ X Column: {config.x_column}")
    print(f"   ✓ Y Column: {config.y_column}")
    print(f"   ✓ Title: {config.title}")
    assert config.type == "scatter", f"Expected 'scatter', got '{config.type}'"
    
    # Test 6: Table (Too Many Columns)
    print("\n7. Testing Table Detection (Many Columns)...")
    df_table = pd.DataFrame({
        "col1": [1, 2, 3],
        "col2": [4, 5, 6],
        "col3": [7, 8, 9],
        "col4": [10, 11, 12],
        "col5": ["a", "b", "c"]
    })
    config = service.determine_chart_type(df_table, "show all data")
    print(f"   ✓ Type: {config.type}")
    print(f"   ✓ Title: {config.title}")
    assert config.type == "table", f"Expected 'table', got '{config.type}'"
    
    # Test 7: Horizontal Bar Chart (Long Labels)
    print("\n8. Testing Horizontal Bar Chart (Long Labels)...")
    df_horizontal = pd.DataFrame({
        "product_name": [
            "iTunes Gift Card $100 - USA Region",
            "Google Play Store $50 - Middle East",
            "Amazon Gift Card Premium Edition $25"
        ],
        "revenue": [10000, 8000, 6000]
    })
    config = service.determine_chart_type(df_horizontal, "top products")
    print(f"   ✓ Type: {config.type}")
    print(f"   ✓ Orientation: {config.orientation}")
    assert config.type == "bar", f"Expected 'bar', got '{config.type}'"
    assert config.orientation == "horizontal", f"Expected 'horizontal', got '{config.orientation}'"
    
    # Test 8: Prepare Data for Chart
    print("\n9. Testing Data Preparation...")
    df_prep = pd.DataFrame({
        "client": ["A", "B", "C", "D", "E"] * 5,  # 25 rows
        "revenue": [1000, 2000, 3000, 4000, 5000] * 5
    })
    config = service.determine_chart_type(df_prep, "top clients")
    data_list, warnings = service.prepare_data_for_chart(df_prep, config)
    print(f"   ✓ Data rows: {len(data_list)}")
    print(f"   ✓ Warnings: {warnings}")
    print(f"   ✓ First item: {data_list[0] if data_list else 'None'}")
    
    # Test 9: Format Answer Text
    print("\n10. Testing Answer Text Formatting...")
    
    # Metric answer
    answer = service.format_answer_text(df_metric, "total revenue", 
                                        ChartConfig(type="metric", title="Total Revenue"))
    print(f"   ✓ Metric Answer: {answer}")
    
    # Top N answer
    answer = service.format_answer_text(df_bar, "top 5 products", 
                                        ChartConfig(type="bar", title="Top 5", 
                                                    x_column="product_name", y_column="revenue"))
    print(f"   ✓ Top N Answer: {answer}")
    
    # Test 10: Empty DataFrame
    print("\n11. Testing Empty DataFrame Handling...")
    df_empty = pd.DataFrame()
    config = service.determine_chart_type(df_empty, "anything")
    print(f"   ✓ Type: {config.type}")
    assert config.type == "table", f"Expected 'table', got '{config.type}'"
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    
    return True


# Need to import ChartConfig for test 9
from app.models import ChartConfig

if __name__ == "__main__":
    try:
        test_service()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
