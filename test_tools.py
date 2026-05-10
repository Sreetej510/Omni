#!/usr/bin/env python3
"""
Individual tool testing script.
Tests each tool separately to verify they work correctly.
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tools.web_search_tool import WebSearchTool
from src.tools.fetch_url_tool import FetchURLTool
from src.utils.tool_validator import ToolValidator


def test_web_search_tool():
    """Test the web_search_tool."""
    print("\n" + "="*70)
    print("TESTING: WebSearchTool")
    print("="*70)
    
    try:
        tool = WebSearchTool()
        
        # Test 1: Basic search
        print("\n[Test 1] Basic web search...")
        result = tool.web_search(query="Radcliffe Line 1947")
        
        if "Web Search Results" in result and "URLs" in result:
            print("PASS: Search returned expected format")
            lines = result.split('\n')
            for line in lines[:5]:
                print(f"  {line}")
        else:
            print("FAIL: Unexpected result format")
            print(f"  Result: {result[:200]}")
        
        # Test 2: Search with freshness
        print("\n[Test 2] Search with freshness filter...")
        result = tool.web_search(query="India Pakistan partition", freshness="pm")
        
        if "Web Search Results" in result:
            print("PASS: Search with freshness worked")
        else:
            print("FAIL: Freshness parameter failed")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


def test_fetch_url_tool():
    """Test the fetch_url_tool."""
    print("\n" + "="*70)
    print("TESTING: FetchURLTool")
    print("="*70)
    
    try:
        tool = FetchURLTool()
        
        # Test 1: Fetch Wikipedia page
        print("\n[Test 1] Fetch Wikipedia URL...")
        test_url = "https://en.wikipedia.org/wiki/Radcliffe_Line"
        result = tool.fetch_url(test_url)
        
        if "Error" in result:
            print(f"FAIL: {result}")
        elif "Content from" in result and len(result) > 50:
            print("PASS: URL fetched and cleaned successfully")
            preview = result[:300] + "..." if len(result) > 300 else result
            print(f"  {preview}")
        else:
            print(f"FAIL: Unexpected result: {result[:200]}")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


def test_tool_validator():
    """Test the tool_validator."""
    print("\n" + "="*70)
    print("TESTING: ToolValidator")
    print("="*70)
    
    try:
        # Test 1: Main agent validator (limit=5)
        print("\n[Test 1] Main agent validator (limit=5)...")
        validator = ToolValidator(web_search_limit=5)
        
        for i in range(5):
            is_allowed, error = validator.validate_tool_call("web_search")
            if is_allowed:
                validator.increment_web_search()
                print(f"  Call {i+1}: Allowed")
            else:
                print(f"  Call {i+1}: Blocked (unexpected)")
        
        is_allowed, error = validator.validate_tool_call("web_search")
        if not is_allowed:
            print(f"  Call 6: Blocked (as expected)")
            print(f"    Error message: {error}")
        else:
            print(f"  Call 6: Allowed (should be blocked)")
        
        # Test 2: Subagent validator (limit=3)
        print("\n[Test 2] Subagent validator (limit=3)...")
        validator = ToolValidator(web_search_limit=3)
        
        for i in range(3):
            is_allowed, error = validator.validate_tool_call("web_search")
            if is_allowed:
                validator.increment_web_search()
                print(f"  Call {i+1}: Allowed")
            else:
                print(f"  Call {i+1}: Blocked (unexpected)")
        
        is_allowed, error = validator.validate_tool_call("web_search")
        if not is_allowed:
            print(f"  Call 4: Blocked (as expected)")
        else:
            print(f"  Call 4: Allowed (should be blocked)")
        
        # Test 3: Other tools should always be allowed
        print("\n[Test 3] Other tools should always be allowed...")
        validator = ToolValidator(web_search_limit=1)
        validator.increment_web_search()
        
        other_tools = ["fetch_url", "findings_write", "findings_list", "findings_read", "generate_report"]
        for tool_name in other_tools:
            is_allowed, error = validator.validate_tool_call(tool_name)
            if is_allowed:
                print(f"  {tool_name}: Allowed")
            else:
                print(f"  {tool_name}: Blocked (should be allowed)")
        
        # Test 4: Status reporting
        print("\n[Test 4] Validator status...")
        validator = ToolValidator(web_search_limit=5)
        validator.increment_web_search()
        validator.increment_web_search()
        status = validator.get_status()
        print(f"  Status: {status}")
        if status["web_search_count"] == 2 and status["remaining_web_searches"] == 3:
            print("  Status correct")
        else:
            print("  Status incorrect")
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("TOOL TESTING SUITE")
    print("="*70)
    print("\nThis script tests each tool individually.")
    
    test_web_search_tool()
    test_fetch_url_tool()
    test_tool_validator()
    
    print("\n" + "="*70)
    print("TESTING COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
