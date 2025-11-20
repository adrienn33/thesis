#!/usr/bin/env python3
"""
Test MCP function execution in agent environment
Mimics exactly how the agent would call MCP functions
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent import DemoAgentArgs
from patch_with_custom_exec import patch_with_custom_exec, execute_python_code
from mcp_integration.client import MCPServerConfig
import __main__

def test_mcp_execution():
    print("=" * 80)
    print("Testing MCP function execution in agent environment")
    print("=" * 80)
    
    # 1. Setup agent with MCP servers (mimics run_demo.py)
    print("\n[1] Initializing agent with MCP servers...")
    agent_args = DemoAgentArgs(
        model_name="claude-haiku-4-5",
        use_html=False,
        use_axtree=True,
        use_screenshot=True,
        websites=("shopping",),
        mcp_servers=[
            {
                'name': 'magento-review-server',
                'command': ['docker', 'exec', '-i', 'shopping', 'python3', '/tmp/magento_review_data.py']
            },
            {
                'name': 'magento-product-server',
                'command': ['docker', 'exec', '-i', 'shopping', 'python3', '/tmp/magento_products.py']
            }
        ]
    )
    
    # 2. Create agent (this initializes MCP clients and creates wrapper functions)
    print("[2] Creating agent (initializes MCP clients)...")
    agent = agent_args.make_agent()
    
    # 3. Check what functions are available in __main__
    print("\n[3] Checking MCP functions in __main__ namespace...")
    mcp_funcs = [name for name in dir(__main__) if 'magento' in name.lower()]
    print(f"Found {len(mcp_funcs)} MCP functions: {mcp_funcs[:5]}...")
    
    # 4. Apply the patch (adds custom exec logic)
    print("\n[4] Applying patch_with_custom_exec...")
    patch_with_custom_exec(agent_args)
    
    # 5. Create mock send_message_to_user
    messages = []
    def mock_send_message(text: str):
        print(f"\n📨 send_message_to_user called:")
        print(f"   {text}")
        messages.append(text)
    
    def mock_report_infeasible(reason: str):
        print(f"\n❌ report_infeasible called:")
        print(f"   {reason}")
    
    # 6. Test simple expression (should auto-display)
    print("\n" + "=" * 80)
    print("TEST 1: Simple expression (2 + 2)")
    print("=" * 80)
    code1 = "2 + 2"
    try:
        execute_python_code(
            code1,
            page=None,
            send_message_to_user=mock_send_message,
            report_infeasible_instructions=mock_report_infeasible,
            agent_args=agent_args,
            env=None
        )
        print("✅ Test 1 passed")
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 7. Test MCP function call (should auto-display result)
    print("\n" + "=" * 80)
    print("TEST 2: MCP function call - search Amazon Basics products")
    print("=" * 80)
    code2 = 'magento_product_server_search_products(name="Amazon Basics", limit="10")'
    try:
        execute_python_code(
            code2,
            page=None,
            send_message_to_user=mock_send_message,
            report_infeasible_instructions=mock_report_infeasible,
            agent_args=agent_args,
            env=None
        )
        print("✅ Test 2 passed")
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 8. Test multi-line code (should NOT auto-display)
    print("\n" + "=" * 80)
    print("TEST 3: Multi-line code with explicit send_msg_to_user")
    print("=" * 80)
    code3 = '''
result = magento_product_server_search_products(name="Amazon Basics", limit="10")
send_msg_to_user(f"Found {len(result)} products")
'''
    try:
        execute_python_code(
            code3,
            page=None,
            send_message_to_user=mock_send_message,
            report_infeasible_instructions=mock_report_infeasible,
            agent_args=agent_args,
            env=None
        )
        print("✅ Test 3 passed")
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 9. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total messages sent to user: {len(messages)}")
    for i, msg in enumerate(messages, 1):
        print(f"\nMessage {i}:")
        print(f"  {msg[:200]}{'...' if len(msg) > 200 else ''}")
    
    print("\n" + "=" * 80)
    print("EXPECTED BEHAVIOR:")
    print("=" * 80)
    print("Test 1: Should see '→ 4' in messages")
    print("Test 2: Should see '→ [...]' with product data in messages")
    print("Test 3: Should see 'Found N products' in messages")
    print("=" * 80)

if __name__ == "__main__":
    test_mcp_execution()
