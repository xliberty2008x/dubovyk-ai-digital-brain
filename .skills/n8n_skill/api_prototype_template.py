#!/usr/bin/env python3
"""
API Prototype Template for n8n Pre-Implementation Testing

Purpose: Quickly test and validate API endpoints before building n8n workflows.
This saves significant time by discovering API quirks in a faster development environment.

Usage:
1. Fill in API_BASE_URL and AUTH credentials
2. Implement test_authentication()
3. Add specific endpoint tests
4. Run script to validate API behavior
5. Document findings in comments
6. Build n8n workflow with confidence
"""

import requests
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import time


# =============================================================================
# CONFIGURATION - Update these for your API
# =============================================================================

API_BASE_URL = "https://api.example.com/v1"

# Authentication - Choose your method
AUTH_CONFIG = {
    "type": "bearer",  # Options: bearer, api_key, basic, oauth2
    "token": "your_token_here",  # For bearer
    "api_key": "your_key_here",  # For api_key
    "api_key_header": "X-API-Key",  # Header name for api_key
    "username": "user",  # For basic auth
    "password": "pass",  # For basic auth
}

# Rate limiting configuration
RATE_LIMIT = {
    "requests_per_second": 10,
    "delay_between_requests": 0.1,  # seconds
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_headers() -> Dict[str, str]:
    """Generate headers based on auth type."""
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "n8n-prototype/1.0"
    }
    
    if AUTH_CONFIG["type"] == "bearer":
        headers["Authorization"] = f"Bearer {AUTH_CONFIG['token']}"
    elif AUTH_CONFIG["type"] == "api_key":
        headers[AUTH_CONFIG["api_key_header"]] = AUTH_CONFIG["api_key"]
    
    return headers


def make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    handle_rate_limit: bool = True
) -> Dict[str, Any]:
    """
    Make API request with error handling and rate limiting.
    
    Returns dict with:
        - success: bool
        - status_code: int
        - data: response data
        - error: error message if failed
        - headers: response headers
    """
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if handle_rate_limit:
            time.sleep(RATE_LIMIT["delay_between_requests"])
        
        response = requests.request(
            method=method,
            url=url,
            headers=get_headers(),
            json=data if method in ["POST", "PUT", "PATCH"] else None,
            params=params,
            timeout=30
        )
        
        return {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "data": response.json() if response.content else None,
            "error": None if response.status_code < 400 else response.text,
            "headers": dict(response.headers)
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "status_code": 0,
            "data": None,
            "error": "Request timed out",
            "headers": {}
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "status_code": 0,
            "data": None,
            "error": str(e),
            "headers": {}
        }
    except json.JSONDecodeError:
        return {
            "success": False,
            "status_code": response.status_code,
            "data": None,
            "error": "Invalid JSON response",
            "headers": dict(response.headers)
        }


def print_result(test_name: str, result: Dict[str, Any]):
    """Pretty print test results."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'='*80}")
    print(f"Status: {'✓ SUCCESS' if result['success'] else '✗ FAILED'}")
    print(f"Status Code: {result['status_code']}")
    
    if result['success']:
        print(f"\nResponse Data:")
        print(json.dumps(result['data'], indent=2))
    else:
        print(f"\nError: {result['error']}")
    
    # Check for rate limit headers
    rate_headers = {k: v for k, v in result['headers'].items() 
                   if 'rate' in k.lower() or 'limit' in k.lower()}
    if rate_headers:
        print(f"\nRate Limit Headers:")
        for k, v in rate_headers.items():
            print(f"  {k}: {v}")


# =============================================================================
# TEST FUNCTIONS - Implement these for your specific API
# =============================================================================

def test_authentication():
    """Test if authentication credentials work."""
    # Update endpoint to your auth test endpoint
    result = make_request("GET", "/user/me")
    print_result("Authentication Test", result)
    return result['success']


def test_list_endpoint():
    """Test listing resources with pagination."""
    params = {
        "page": 1,
        "limit": 10
    }
    result = make_request("GET", "/resources", params=params)
    print_result("List Resources", result)
    
    if result['success'] and result['data']:
        print(f"\nData Structure Analysis:")
        print(f"  - Response type: {type(result['data'])}")
        if isinstance(result['data'], dict):
            print(f"  - Keys: {list(result['data'].keys())}")
        if isinstance(result['data'], list) and len(result['data']) > 0:
            print(f"  - First item keys: {list(result['data'][0].keys())}")
    
    return result


def test_create_endpoint():
    """Test creating a new resource."""
    data = {
        "name": "Test Resource",
        "description": "Created via API prototype",
        "created_at": datetime.utcnow().isoformat()
    }
    result = make_request("POST", "/resources", data=data)
    print_result("Create Resource", result)
    return result


def test_update_endpoint(resource_id: str):
    """Test updating an existing resource."""
    data = {
        "name": "Updated Test Resource",
        "updated_at": datetime.utcnow().isoformat()
    }
    result = make_request("PUT", f"/resources/{resource_id}", data=data)
    print_result("Update Resource", result)
    return result


def test_delete_endpoint(resource_id: str):
    """Test deleting a resource."""
    result = make_request("DELETE", f"/resources/{resource_id}")
    print_result("Delete Resource", result)
    return result


def test_error_scenarios():
    """Test how API handles various error conditions."""
    print(f"\n{'='*80}")
    print("TESTING ERROR SCENARIOS")
    print(f"{'='*80}")
    
    # Test 1: Invalid endpoint (404)
    result = make_request("GET", "/nonexistent")
    print_result("404 Not Found", result)
    
    # Test 2: Invalid data (400)
    result = make_request("POST", "/resources", data={"invalid": "data"})
    print_result("400 Bad Request", result)
    
    # Test 3: Unauthorized (401) - test with bad token
    original_token = AUTH_CONFIG["token"]
    AUTH_CONFIG["token"] = "invalid_token"
    result = make_request("GET", "/user/me")
    AUTH_CONFIG["token"] = original_token
    print_result("401 Unauthorized", result)


def test_rate_limiting():
    """Test rate limit behavior."""
    print(f"\n{'='*80}")
    print("TESTING RATE LIMITS")
    print(f"{'='*80}")
    
    print(f"Sending {RATE_LIMIT['requests_per_second']} rapid requests...")
    
    for i in range(RATE_LIMIT['requests_per_second']):
        result = make_request("GET", "/user/me", handle_rate_limit=False)
        print(f"Request {i+1}: {result['status_code']}")
        
        if result['status_code'] == 429:
            print(f"⚠ Rate limit hit at request {i+1}")
            retry_after = result['headers'].get('Retry-After', 'Not specified')
            print(f"Retry-After: {retry_after}")
            break


def test_pagination():
    """Test pagination implementation."""
    print(f"\n{'='*80}")
    print("TESTING PAGINATION")
    print(f"{'='*80}")
    
    page = 1
    all_items = []
    
    while page <= 3:  # Test first 3 pages
        result = make_request("GET", "/resources", params={"page": page, "limit": 10})
        
        if not result['success']:
            print(f"Failed at page {page}")
            break
        
        data = result['data']
        
        # Adapt this based on your API's response structure
        items = data.get('items', []) if isinstance(data, dict) else data
        all_items.extend(items)
        
        print(f"Page {page}: {len(items)} items")
        
        # Check if there are more pages
        has_next = data.get('has_next', False) if isinstance(data, dict) else len(items) > 0
        if not has_next or len(items) == 0:
            break
        
        page += 1
    
    print(f"\nTotal items fetched: {len(all_items)}")


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_all_tests():
    """Run comprehensive API test suite."""
    print(f"\n{'#'*80}")
    print(f"# API PROTOTYPE TESTING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# API: {API_BASE_URL}")
    print(f"{'#'*80}")
    
    # Test authentication first
    if not test_authentication():
        print("\n❌ Authentication failed. Fix credentials before continuing.")
        return
    
    print("\n✓ Authentication successful! Proceeding with tests...\n")
    
    # Run other tests
    test_list_endpoint()
    test_pagination()
    test_error_scenarios()
    test_rate_limiting()
    
    # Uncomment when ready to test write operations
    # create_result = test_create_endpoint()
    # if create_result['success'] and create_result['data']:
    #     resource_id = create_result['data'].get('id')
    #     if resource_id:
    #         test_update_endpoint(resource_id)
    #         test_delete_endpoint(resource_id)
    
    print(f"\n{'#'*80}")
    print("# TESTING COMPLETE")
    print(f"{'#'*80}\n")
    
    print("NEXT STEPS:")
    print("1. Review the output above")
    print("2. Document field names, types, and nested structures")
    print("3. Note any pagination patterns")
    print("4. Document rate limit headers")
    print("5. Save error response formats")
    print("6. Build n8n workflow with this knowledge")


# =============================================================================
# DOCUMENTATION TEMPLATE
# =============================================================================

def print_documentation_template():
    """Print template for documenting findings."""
    print("""
API DOCUMENTATION TEMPLATE
==========================

## Authentication
- Type: [bearer/api_key/oauth2]
- Token/Key location: [header/query param]
- Token format: [format]

## Endpoints Tested

### GET /resources
- Purpose: List resources
- Pagination: [yes/no] - [page-based/cursor-based/offset-based]
- Response structure:
  ```json
  {
    "items": [],
    "total": 0,
    "page": 1,
    "has_next": true
  }
  ```

### POST /resources
- Purpose: Create resource
- Required fields: [field1, field2]
- Optional fields: [field3]
- Returns: [resource object/id only]

## Rate Limiting
- Limit: X requests per Y seconds
- Headers: X-RateLimit-Limit, X-RateLimit-Remaining
- Status code when exceeded: 429
- Retry-After header: [yes/no]

## Error Responses
- Format: [json/plain text]
- Structure:
  ```json
  {
    "error": "message",
    "code": "ERROR_CODE"
  }
  ```

## Notes for n8n Implementation
- [ ] Use Loop Over Items for batching
- [ ] Implement retry logic with backoff
- [ ] Cache frequently accessed data
- [ ] Use sub-workflows for complex transformations
- [ ] Set up Error Trigger workflow
    """)


if __name__ == "__main__":
    run_all_tests()
    # Uncomment to see documentation template
    # print_documentation_template()
