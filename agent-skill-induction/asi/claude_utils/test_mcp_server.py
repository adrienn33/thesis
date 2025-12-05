#!/usr/bin/env python3
"""
Test script for the MCP Review Data Server
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from mcp_integration.client import MCPClient, MCPServerConfig

def test_mcp_server():
    """Test the MCP server functionality"""
    print("Testing MCP Review Data Server...")
    
    # Create server config - run inside container
    server_config = MCPServerConfig(
        name="magento-review-server",
        command=["docker", "exec", "-i", "shopping", "python3", "/tmp/magento_review_data.py"]
    )
    
    # Create client
    client = MCPClient(server_config)
    
    try:
        # Connect to server
        print("1. Connecting to server...")
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
        
        # Test a simple tool call with a known product
        print("3. Testing tool call with real product...")
        try:
            result = client.call_tool("get_product_reviews", {"product_id": "B006H52HBC"})
            if isinstance(result, list):
                print(f"✅ Tool call succeeded! Found {len(result)} reviews")
                if result:
                    print(f"   Sample: {result[0].get('nickname', 'Anonymous')} - '{result[0].get('title', '')[:50]}...'")
            else:
                print(f"✅ Tool call succeeded, result type: {type(result)}")
        except Exception as e:
            print(f"⚠️ Tool call failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        client.disconnect()
        print("4. Disconnected from server")

def test_product_server():
    """Test the MCP Product Server functionality"""
    print("\nTesting MCP Product Server...")
    
    # Create server config - run inside container
    server_config = MCPServerConfig(
        name="magento-product-server",
        command=["docker", "exec", "-i", "shopping", "python3", "/tmp/magento_products.py"]
    )
    
    # Create client
    client = MCPClient(server_config)
    
    try:
        # Connect to server
        print("1. Connecting to server...")
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
        
        # Test search_products
        print("3. Testing product search...")
        try:
            result = client.call_tool("search_products", {"name": "headphones", "limit": "5"})
            if isinstance(result, list):
                print(f"✅ Search succeeded! Found {len(result)} products")
                if result:
                    print(f"   Sample: {result[0].get('name', 'Unknown')} - ${result[0].get('price', 0)}")
            else:
                print(f"✅ Search succeeded, result type: {type(result)}")
        except Exception as e:
            print(f"⚠️ Search failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        client.disconnect()
        print("4. Disconnected from server")

def test_checkout_server():
    """Test the MCP Checkout Server functionality"""
    print("\nTesting MCP Checkout Server...")
    
    # Create server config - run inside container
    server_config = MCPServerConfig(
        name="magento-checkout-server",
        command=["docker", "exec", "-i", "shopping", "python3", "/tmp/magento_checkout.py"]
    )
    
    # Create client
    client = MCPClient(server_config)
    
    try:
        # Connect to server
        print("1. Connecting to server...")
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
        
        # Test list_orders
        print("3. Testing list_orders with customer email...")
        first_order_number = None
        try:
            result = client.call_tool("list_orders", {"customer_email": "emma.lopez@gmail.com", "limit": "5"})
            if isinstance(result, list):
                print(f"✅ list_orders succeeded! Found {len(result)} orders")
                if result:
                    first_order_number = result[0].get('order_number', 'N/A')
                    print(f"   Sample: Order #{first_order_number} - Status: {result[0].get('status', 'N/A')} - Total: ${result[0].get('totals', {}).get('grand_total', 0):.2f}")
            else:
                print(f"✅ list_orders succeeded, result type: {type(result)}")
        except Exception as e:
            print(f"⚠️ list_orders failed: {e}")
        
        # Test get_order_details
        if first_order_number:
            print("4. Testing get_order_details...")
            try:
                result = client.call_tool("get_order_details", {"order_id": first_order_number})
                if isinstance(result, dict) and "error" not in result:
                    print(f"✅ get_order_details succeeded!")
                    print(f"   Order: #{result.get('order_number')} - {len(result.get('items', []))} items - Total: ${result.get('totals', {}).get('grand_total', 0):.2f}")
                    if result.get('items'):
                        print(f"   First item: {result['items'][0].get('name', 'Unknown')} - Qty: {result['items'][0].get('qty_ordered', 0)}")
                else:
                    print(f"⚠️ get_order_details returned error: {result.get('error', 'Unknown')}")
            except Exception as e:
                print(f"⚠️ get_order_details failed: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    finally:
        client.disconnect()
        print("4. Disconnected from server")

if __name__ == "__main__":
    success1 = test_mcp_server()
    success2 = test_product_server()
    success3 = test_checkout_server()
    sys.exit(0 if (success1 and success2 and success3) else 1)