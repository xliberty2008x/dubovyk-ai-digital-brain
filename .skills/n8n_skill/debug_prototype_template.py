#!/usr/bin/env python3
"""
Debug Prototype Template for n8n Workflow Troubleshooting

Purpose: When stuck debugging a complex transformation or logic issue in n8n,
recreate the exact scenario in Python to verify your logic works correctly.

Usage:
1. Copy the failed input data from n8n execution
2. Implement your transformation logic here
3. Test with the exact data that's failing
4. Verify the logic produces expected output
5. Translate working Python code back to n8n

This is especially useful for:
- Complex data transformations
- Nested object manipulation
- Array operations
- String parsing
- Date/time calculations
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re


# =============================================================================
# TEST DATA - Copy from n8n execution input
# =============================================================================

# Copy the exact input data from your failed n8n node
TEST_INPUT = [
    {
        "json": {
            "id": 1,
            "name": "Sample Item",
            "created_at": "2024-01-15T10:30:00Z",
            "metadata": {
                "tags": ["urgent", "customer"],
                "priority": 1
            },
            "items": [
                {"sku": "ABC123", "quantity": 5},
                {"sku": "DEF456", "quantity": 3}
            ]
        }
    },
    {
        "json": {
            "id": 2,
            "name": "Another Item",
            "created_at": "2024-01-16T14:45:00Z",
            "metadata": {
                "tags": ["internal"],
                "priority": 3
            },
            "items": [
                {"sku": "GHI789", "quantity": 2}
            ]
        }
    }
]

# Expected output format
EXPECTED_OUTPUT = [
    {
        "json": {
            "item_id": 1,
            "display_name": "Sample Item",
            "is_urgent": True,
            "total_quantity": 8
        }
    }
]


# =============================================================================
# TRANSFORMATION LOGIC - Implement your n8n logic here
# =============================================================================

def transform_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a single item.
    
    This function should mirror what your n8n workflow is trying to do.
    Break down complex transformations into smaller, testable functions.
    """
    data = item.get("json", {})
    
    # Example transformation logic
    transformed = {
        "item_id": data.get("id"),
        "display_name": data.get("name", "Unknown"),
        "is_urgent": "urgent" in data.get("metadata", {}).get("tags", []),
        "total_quantity": sum(i.get("quantity", 0) for i in data.get("items", []))
    }
    
    return {"json": transformed}


def filter_items(items: List[Dict[str, Any]], condition: str = "all") -> List[Dict[str, Any]]:
    """
    Filter items based on conditions.
    
    Useful for testing IF/Switch node logic.
    """
    if condition == "all":
        return items
    elif condition == "urgent_only":
        return [item for item in items 
                if "urgent" in item.get("json", {}).get("metadata", {}).get("tags", [])]
    elif condition == "high_priority":
        return [item for item in items 
                if item.get("json", {}).get("metadata", {}).get("priority", 99) <= 2]
    return items


def aggregate_data(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate data across multiple items.
    
    Useful for testing Function node aggregations.
    """
    total_quantity = 0
    unique_skus = set()
    
    for item in items:
        data = item.get("json", {})
        for product in data.get("items", []):
            total_quantity += product.get("quantity", 0)
            unique_skus.add(product.get("sku"))
    
    return {
        "json": {
            "total_items": len(items),
            "total_quantity": total_quantity,
            "unique_products": len(unique_skus),
            "skus": list(unique_skus)
        }
    }


def parse_datetime_field(date_string: str, output_format: str = "%Y-%m-%d") -> str:
    """
    Parse and reformat datetime strings.
    
    Common issue in n8n: date format mismatches.
    """
    try:
        # Try ISO format first
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return dt.strftime(output_format)
    except ValueError:
        # Try other common formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d"
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(date_string, fmt)
                return dt.strftime(output_format)
            except ValueError:
                continue
        return date_string  # Return original if parsing fails


def extract_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Safely extract nested values using dot notation.
    
    Equivalent to n8n's: $json.metadata.tags[0]
    """
    keys = path.split('.')
    value = data
    
    for key in keys:
        # Handle array indices: tags[0]
        if '[' in key:
            key_name, index = key.split('[')
            index = int(index.rstrip(']'))
            value = value.get(key_name, [])
            if isinstance(value, list) and len(value) > index:
                value = value[index]
            else:
                return default
        else:
            if isinstance(value, dict):
                value = value.get(key, default)
            else:
                return default
            
            if value is None or value == default:
                return default
    
    return value


def merge_objects(obj1: Dict, obj2: Dict, strategy: str = "keep_first") -> Dict:
    """
    Merge two objects with conflict resolution.
    
    Strategies:
    - keep_first: Keep values from obj1 when keys conflict
    - keep_last: Keep values from obj2 when keys conflict
    - concatenate: Concatenate string values, sum numeric values
    """
    result = obj1.copy()
    
    for key, value in obj2.items():
        if key not in result:
            result[key] = value
        else:
            if strategy == "keep_first":
                continue  # Keep obj1's value
            elif strategy == "keep_last":
                result[key] = value
            elif strategy == "concatenate":
                if isinstance(result[key], str) and isinstance(value, str):
                    result[key] = f"{result[key]} {value}"
                elif isinstance(result[key], (int, float)) and isinstance(value, (int, float)):
                    result[key] = result[key] + value
                else:
                    result[key] = value
    
    return result


def validate_data(item: Dict[str, Any], required_fields: List[str]) -> tuple[bool, List[str]]:
    """
    Validate that required fields exist and are not null.
    
    Returns: (is_valid, list_of_missing_fields)
    """
    data = item.get("json", {})
    missing = []
    
    for field in required_fields:
        value = extract_nested_value(data, field)
        if value is None or value == "":
            missing.append(field)
    
    return len(missing) == 0, missing


# =============================================================================
# TESTING FUNCTIONS
# =============================================================================

def test_transformation():
    """Test the transformation logic with sample data."""
    print("="*80)
    print("TESTING TRANSFORMATION LOGIC")
    print("="*80)
    
    print("\nInput Data:")
    print(json.dumps(TEST_INPUT, indent=2))
    
    # Transform all items
    transformed = [transform_item(item) for item in TEST_INPUT]
    
    print("\nTransformed Data:")
    print(json.dumps(transformed, indent=2))
    
    print("\nExpected Output:")
    print(json.dumps(EXPECTED_OUTPUT, indent=2))
    
    # Check if transformation matches expected output
    # Adapt this comparison to your specific needs
    print("\n" + "-"*80)
    if len(transformed) == len(EXPECTED_OUTPUT):
        print("✓ Item count matches")
    else:
        print(f"✗ Item count mismatch: got {len(transformed)}, expected {len(EXPECTED_OUTPUT)}")
    
    return transformed


def test_filtering():
    """Test filtering logic."""
    print("\n" + "="*80)
    print("TESTING FILTERING LOGIC")
    print("="*80)
    
    conditions = ["all", "urgent_only", "high_priority"]
    
    for condition in conditions:
        filtered = filter_items(TEST_INPUT, condition)
        print(f"\nCondition: {condition}")
        print(f"Items: {len(filtered)}")
        for item in filtered:
            print(f"  - {item['json']['name']}")


def test_aggregation():
    """Test aggregation logic."""
    print("\n" + "="*80)
    print("TESTING AGGREGATION LOGIC")
    print("="*80)
    
    result = aggregate_data(TEST_INPUT)
    print("\nAggregated Result:")
    print(json.dumps(result, indent=2))


def test_datetime_parsing():
    """Test datetime parsing and formatting."""
    print("\n" + "="*80)
    print("TESTING DATETIME PARSING")
    print("="*80)
    
    test_dates = [
        "2024-01-15T10:30:00Z",
        "2024-01-15 10:30:00",
        "01/15/2024",
        "15/01/2024",
        "2024/01/15"
    ]
    
    for date_str in test_dates:
        formatted = parse_datetime_field(date_str, "%Y-%m-%d")
        print(f"{date_str:30} → {formatted}")


def test_nested_extraction():
    """Test nested value extraction."""
    print("\n" + "="*80)
    print("TESTING NESTED VALUE EXTRACTION")
    print("="*80)
    
    test_paths = [
        "metadata.tags[0]",
        "metadata.priority",
        "items[0].sku",
        "nonexistent.field",
    ]
    
    data = TEST_INPUT[0]["json"]
    
    for path in test_paths:
        value = extract_nested_value(data, path, default="NOT_FOUND")
        print(f"{path:30} → {value}")


def test_validation():
    """Test data validation."""
    print("\n" + "="*80)
    print("TESTING DATA VALIDATION")
    print("="*80)
    
    required_fields = ["id", "name", "metadata.priority"]
    
    for item in TEST_INPUT:
        is_valid, missing = validate_data(item, required_fields)
        item_name = item["json"].get("name", "Unknown")
        
        if is_valid:
            print(f"✓ {item_name}: Valid")
        else:
            print(f"✗ {item_name}: Missing fields: {', '.join(missing)}")


def test_edge_cases():
    """Test edge cases that often cause issues."""
    print("\n" + "="*80)
    print("TESTING EDGE CASES")
    print("="*80)
    
    edge_cases = [
        {"json": {}},  # Empty object
        {"json": {"id": None}},  # Null values
        {"json": {"items": []}},  # Empty arrays
        {"json": {"name": ""}},  # Empty strings
    ]
    
    for i, test_case in enumerate(edge_cases, 1):
        print(f"\nEdge Case {i}: {test_case}")
        try:
            result = transform_item(test_case)
            print(f"✓ Handled successfully: {result}")
        except Exception as e:
            print(f"✗ Error: {e}")


# =============================================================================
# SPECIFIC DEBUGGING SCENARIOS
# =============================================================================

def debug_specific_scenario():
    """
    Use this function to debug a specific failing scenario.
    
    Steps:
    1. Copy exact input from n8n failed execution
    2. Paste it below as test_case
    3. Run the transformation
    4. Compare with expected output
    5. Adjust logic until it works
    """
    print("\n" + "="*80)
    print("DEBUGGING SPECIFIC SCENARIO")
    print("="*80)
    
    # Paste your exact failing data here
    test_case = {
        "json": {
            # Your data here
        }
    }
    
    print("\nInput:")
    print(json.dumps(test_case, indent=2))
    
    try:
        result = transform_item(test_case)
        print("\nOutput:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\n✗ Error occurred: {e}")
        import traceback
        traceback.print_exc()


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run all test functions."""
    print("\n" + "#"*80)
    print(f"# DEBUG TESTING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*80)
    
    test_transformation()
    test_filtering()
    test_aggregation()
    test_datetime_parsing()
    test_nested_extraction()
    test_validation()
    test_edge_cases()
    
    # Uncomment to debug specific scenario
    # debug_specific_scenario()
    
    print("\n" + "#"*80)
    print("# TESTING COMPLETE")
    print("#"*80)
    
    print("\nNEXT STEPS:")
    print("1. Review the outputs above")
    print("2. If logic works in Python, translate to n8n")
    print("3. Use Set node for simple mappings")
    print("4. Use Function node for complex logic")
    print("5. Use built-in expressions when possible")


if __name__ == "__main__":
    run_all_tests()
