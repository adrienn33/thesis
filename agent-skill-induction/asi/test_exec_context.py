#!/usr/bin/env python3
"""
Test if the exact code the agent generates would work in the exec context
"""
import sys
sys.path.insert(0, '.')

# Simulate the execution environment
test_code = '''
reviews = magento_review_server_get_product_reviews("B086GNDL8K")
print(f"DEBUG: Got {len(reviews)} reviews")
for review in reviews:
    if "small" in review["detail"].lower():
        print(f"DEBUG: Found review by {review['nickname']} mentioning small")
        send_msg_to_user(f"Reviewer {review['nickname']} mentioned the ear cups being small.")
print("DEBUG: Done processing reviews")
'''

# Now set up the environment like the agent does
import os
os.environ['ANTHROPIC_API_KEY'] = os.environ.get('ANTHROPIC_API_KEY', '')

from mcp_integration.client import MCPManager, MCPServerConfig
import asyncio

messages_sent = []

def send_message_to_user(text):
    messages_sent.append(text)
    print(f"MESSAGE SENT: {text}")

async def test():
    # Initialize MCP manager
    manager = MCPManager()
    server_config = MCPServerConfig(
        name="magento-review-server",
        command=["docker", "exec", "-i", "shopping", "python3", "/tmp/magento_review_data.py"]
    )
    manager.add_server(server_config)
    
    # Get all tools
    mcp_tools = manager.get_all_tools()
    print(f"Available tools: {list(mcp_tools.keys())}")
    
    # Set up the execution context like patch_with_custom_exec.py does
    import __main__
    __main__._action_set_mcp_manager = manager
    __main__._mcp_tool_wrappers = {}
    
    def _call_mcp_tool(tool_name, **kwargs):
        """Execute an MCP tool by name"""
        if not hasattr(__main__, '_action_set_mcp_manager'):
            raise RuntimeError("MCP manager not available in execution context")
        tools = __main__._action_set_mcp_manager.get_all_tools()
        if tool_name not in tools:
            raise NameError(f"MCP tool '{tool_name}' not found. Available: {list(tools.keys())}")
        return tools[tool_name](**kwargs)
    
    __main__._call_mcp_tool = _call_mcp_tool
    
    # Now create the wrapper function like agent.py does
    for tool_name, tool_wrapper in mcp_tools.items():
        func_name = tool_name.replace("-", "_")
        func_code = f"""
def {func_name}(product_id):
    return _call_mcp_tool('{tool_name}', product_id=product_id)
"""
        exec(func_code, vars(__main__))
        print(f"Created function: {func_name}")
    
    # Now try to execute the agent's code
    print("\n=== Executing agent code ===")
    globals_dict = {
        'send_msg_to_user': send_message_to_user,
        '_call_mcp_tool': _call_mcp_tool,
    }
    
    # Add all the MCP functions
    main_globals = vars(__main__)
    for name, obj in main_globals.items():
        if callable(obj) and 'magento' in name:
            globals_dict[name] = obj
            print(f"Added to globals: {name}")
    
    try:
        exec(test_code, globals_dict)
        print(f"\n✅ Code executed successfully!")
        print(f"Messages sent: {len(messages_sent)}")
        for msg in messages_sent:
            print(f"  - {msg}")
    except Exception as e:
        print(f"\n❌ Execution failed: {e}")
        import traceback
        traceback.print_exc()
    
    await manager.cleanup()

asyncio.run(test())
