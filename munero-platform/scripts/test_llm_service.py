#!/usr/bin/env python3
"""
Test script for the LLM Service.
Tests SQL generation and execution capabilities.
"""
import sys
import os

# Add the backend app to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.services.llm_service import LLMService
from app.models import DashboardFilters
from datetime import date


def test_service():
    print("=" * 60)
    print("LLM SERVICE TEST")
    print("=" * 60)
    
    # Initialize the service
    print("\n1. Initializing LLMService...")
    service = LLMService()
    print(f"   ✓ Model: {service.model}")
    print(f"   ✓ Base URL: {service.base_url}")
    print(f"   ✓ Database: {service.db_path}")
    
    # Test Ollama connection
    print("\n2. Testing Ollama connection...")
    is_connected = service.check_connection()
    if is_connected:
        print("   ✓ Ollama is running and model is available")
    else:
        print("   ✗ Ollama is NOT available. Start with: ollama serve")
        print("   ✗ Make sure the model is pulled: ollama pull qwen2.5-coder:7b")
        return False
    
    # Test schema generation
    print("\n3. Testing schema generation...")
    schema = service.get_database_schema()
    print(f"   ✓ Schema generated ({len(schema)} chars)")
    
    # Test filter clause generation
    print("\n4. Testing filter clause generation...")
    filters = DashboardFilters(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        countries=["AE", "SA"],
        product_types=["gift_cards"]
    )
    context, where_clause = service.build_filter_clause(filters)
    print(f"   ✓ Context: {context}")
    print(f"   ✓ WHERE: {where_clause}")
    
    # Test SQL generation
    print("\n5. Testing SQL generation...")
    question = "What are my top 5 products by revenue?"
    try:
        sql = service.generate_sql(question, filters)
        print(f"   ✓ Question: {question}")
        print(f"   ✓ Generated SQL:\n      {sql}")
    except TimeoutError as e:
        print(f"   ✗ Timeout: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test SQL execution
    print("\n6. Testing SQL execution...")
    try:
        df = service.execute_sql(sql)
        print(f"   ✓ Query executed successfully")
        print(f"   ✓ Rows returned: {len(df)}")
        print(f"   ✓ Columns: {list(df.columns)}")
        if not df.empty:
            print(f"   ✓ Sample data:\n{df.head().to_string()}")
    except Exception as e:
        print(f"   ✗ Execution error: {e}")
        return False
    
    # Test complete query pipeline
    print("\n7. Testing complete query pipeline (no filters)...")
    try:
        question2 = "What is the total revenue?"
        df2, sql2 = service.query(question2, filters=None)
        print(f"   ✓ Question: {question2}")
        print(f"   ✓ SQL: {sql2}")
        print(f"   ✓ Result: {df2.to_dict('records')}")
    except Exception as e:
        print(f"   ✗ Pipeline error: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_service()
    sys.exit(0 if success else 1)
