#!/usr/bin/env python3
"""
Test script for the Magento MCP Servers (Reviews and Products)
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_integration.client import MCPClient, MCPServerConfig

def test_magento_review_server():
    """Test the Magento Review MCP server functionality"""
    print("Testing Magento Review MCP Server with Real Database Access...")
    
    # Create server config - run inside container
    server_config = MCPServerConfig(
        name="magento-review-server",
        command=["docker", "exec", "-i", "shopping", "python3", "/tmp/magento_review_data.py"]
    )
    
    # Create client
    client = MCPClient(server_config)
    
    try:
        # Connect to server
        print("1. Connecting to Magento MCP server...")
        if not client.connect():
            print("❌ Failed to connect to server")
            return False
        print("✅ Connected successfully")
        
        # List available tools
        print("2. Listing available tools...")
        tools = client.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        # Test getting reviews for a known product
        print("3. Testing real product review lookup...")
        try:
            result = client.call_tool("get_product_reviews", {"product_id": "B006H52HBC"})
            if isinstance(result, list):
                print(f"✅ Found {len(result)} reviews for product B006H52HBC")
                if result:
                    print(f"   Sample review: {result[0]['nickname']} - '{result[0]['title'][:50]}...'")
            else:
                print(f"⚠️ Unexpected result type: {type(result)}")
        except Exception as e:
            print(f"⚠️ Review lookup failed: {e}")
        
        # Test semantic search  
        print("4. Testing semantic review search...")
        try:
            result = client.call_tool("search_reviews_semantic", {
                "product_id": "B006H52HBC", 
                "search_terms": "ear cups too small narrow tight"
            })
            if isinstance(result, list):
                print(f"✅ Found {len(result)} semantically matching reviews")
                if result:
                    print(f"   Top match (score {result[0].get('semantic_score', 0):.2f}): {result[0]['nickname']} - '{result[0]['title'][:50]}...'")
            else:
                print(f"⚠️ Unexpected result type: {type(result)}")
        except Exception as e:
            print(f"⚠️ Semantic search failed: {e}")
        
        # Test creating a review
        print("5. Testing review creation...")
        try:
            result = client.call_tool("create_review", {
                "product_id": "B006H52HBC",
                "title": "Test Review",
                "detail": "This is a test review created by the MCP test script.",
                "nickname": "TestUser",
                "rating": "5"
            })
            if isinstance(result, dict) and "review_id" in result:
                print(f"✅ Review created successfully with ID: {result['review_id']}")
            elif isinstance(result, dict) and "error" not in result:
                print(f"✅ Review creation response: {result}")
            else:
                print(f"⚠️ Unexpected result: {result}")
        except Exception as e:
            print(f"⚠️ Review creation failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        client.disconnect()
        print("5. Disconnected from server")

def test_magento_product_server():
    """Test the Magento Product MCP server functionality"""
    print("\nTesting Magento Product MCP Server with Real Database Access...")
    
    # Create server config - run inside container
    server_config = MCPServerConfig(
        name="magento-product-server",
        command=["docker", "exec", "-i", "shopping", "python3", "/tmp/magento_products.py"]
    )
    
    # Create client
    client = MCPClient(server_config)
    
    try:
        # Connect to server
        print("1. Connecting to Magento Product MCP server...")
        if not client.connect():
            print("❌ Failed to connect to server")
            return False
        print("✅ Connected successfully")
        
        # List available tools
        print("2. Listing available tools...")
        tools = client.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        # Test product search
        print("3. Testing product search...")
        try:
            result = client.call_tool("search_products", {"name": "headphones", "limit": "5"})
            if isinstance(result, list):
                print(f"✅ Found {len(result)} products matching 'headphones'")
                if result:
                    print(f"   Sample: {result[0].get('name', 'Unknown')} (SKU: {result[0].get('sku', 'N/A')})")
            else:
                print(f"⚠️ Unexpected result type: {type(result)}")
        except Exception as e:
            print(f"⚠️ Product search failed: {e}")
        
        # Test getting product details
        print("4. Testing product details lookup...")
        try:
            result = client.call_tool("get_product_details", {"product_id": "B006H52HBC"})
            if isinstance(result, dict) and "entity_id" in result:
                print(f"✅ Retrieved details for product: {result.get('name', 'Unknown')}")
                print(f"   Price: ${result.get('price', 0)}, Stock: {result.get('stock', {}).get('qty', 0)} units")
                if result.get('options'):
                    print(f"   Configurable options: {[opt['attribute_code'] for opt in result['options']]}")
            else:
                print(f"⚠️ Unexpected result: {result}")
        except Exception as e:
            print(f"⚠️ Product details lookup failed: {e}")
        
        # Test listing categories
        print("5. Testing category listing...")
        try:
            result = client.call_tool("list_categories", {})
            if isinstance(result, list):
                print(f"✅ Found {len(result)} categories")
                if result:
                    print(f"   Sample categories: {', '.join([c['name'] for c in result[:3]])}...")
            else:
                print(f"⚠️ Unexpected result type: {type(result)}")
        except Exception as e:
            print(f"⚠️ Category listing failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        client.disconnect()
        print("6. Disconnected from server")

if __name__ == "__main__":
    success1 = test_magento_review_server()
    success2 = test_magento_product_server()
    print("\n" + "="*60)
    print(f"Review Server: {'PASS' if success1 else 'FAIL'}")
    print(f"Product Server: {'PASS' if success2 else 'FAIL'}")
    print("="*60)
    sys.exit(0 if (success1 and success2) else 1)