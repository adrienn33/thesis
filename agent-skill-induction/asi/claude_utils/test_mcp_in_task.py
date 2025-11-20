#!/usr/bin/env python3
"""
Test if MCP tools are accessible during task execution
"""
import os
import sys

# Set up environment
os.environ['ANTHROPIC_API_KEY'] = os.environ.get('ANTHROPIC_API_KEY', '')
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', '')

# Import browsergym and agent
from browsergym.experiments import EnvArgs, ExpArgs
from agent import DemoAgent, DemoAgentArgs

# Create minimal agent
agent_args = DemoAgentArgs(
    model_name="claude-3-haiku-20240307",
    use_html=False,
    use_axtree=True,
    use_screenshot=False,
    websites=['shopping'],
    mcp_servers=[
        {
            "name": "magento-review-server",
            "command": ["docker", "exec", "-i", "shopping", "python3", "/tmp/magento_review_data.py"]
        },
        {
            "name": "magento-product-server",
            "command": ["docker", "exec", "-i", "shopping", "python3", "/tmp/magento_products.py"]
        }
    ]
)

# Create agent
agent = DemoAgent(agent_args)

# Check if MCP tools are available
print("\n=== Checking MCP Tool Availability ===")
print(f"MCP Manager exists: {agent.mcp_manager is not None}")
if agent.mcp_manager:
    tools = agent.mcp_manager.get_all_tools()
    print(f"Available tools: {list(tools.keys())}")
    
    # Check if tools are in action set
    print(f"\nAction set functions:")
    for name in agent.action_set.action_set.keys():
        if 'magento' in name:
            print(f"  - {name}")
    
    # Check __main__ globals
    import __main__
    print(f"\n__main__._action_set_mcp_manager exists: {hasattr(__main__, '_action_set_mcp_manager')}")
    print(f"__main__._mcp_tool_wrappers exists: {hasattr(__main__, '_mcp_tool_wrappers')}")
    
    # Try to call a tool directly
    print(f"\n=== Testing Direct Tool Call ===")
    try:
        reviews = tools['get_product_reviews'](product_id="B086GNDL8K")
        print(f"✅ Tool call succeeded! Got {len(reviews)} reviews")
        
        # Check for "small" mentions
        small_reviews = [r for r in reviews if "small" in r["detail"].lower()]
        print(f"✅ Found {len(small_reviews)} reviews mentioning 'small':")
        for r in small_reviews[:3]:
            print(f"   - {r['nickname']}")
    except Exception as e:
        print(f"❌ Tool call failed: {e}")
        import traceback
        traceback.print_exc()
