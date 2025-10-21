#!/usr/bin/env python3
"""
Debug script to test MCP tool execution in the WebArena context
"""
import json
from agent import DemoAgentArgs
from patch_with_custom_exec import execute_python_code

def debug_mcp_execution():
    print("=== Debugging MCP Tool Execution in WebArena Context ===")
    
    # Load MCP configuration
    with open('config_files/21-mcp-container.json', 'r') as f:
        config = json.load(f)
    
    # Create agent with MCP tools
    args = DemoAgentArgs(
        model_name='claude-3-haiku-20240307',
        websites=['shopping'],
        mcp_servers=config.get('mcp_servers')
    )
    agent = args.make_agent()
    
    print(f"1. Agent created, MCP tools available: {list(agent.mcp_manager.get_all_tools().keys())}")
    
    # Check if MCP tools are available globally
    import __main__
    main_globals = vars(__main__)
    mcp_funcs = [name for name in main_globals.keys() if 'magento_review_server' in name]
    print(f"2. Global MCP functions: {mcp_funcs}")
    
    # Test direct execution of MCP tool code
    test_code = """
try:
    print("Testing MCP tool execution...")
    print("Available globals:", list(globals().keys()))
    
    # Try to call MCP tool directly
    result = magento_review_server_find_reviewers_mentioning_keywords(
        product_sku="B006H52HBC", 
        keywords=["small", "narrow", "tight"]
    )
    print(f"MCP tool result: {result}")
    
except Exception as e:
    print(f"MCP tool execution failed: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
"""
    
    print("3. Testing code execution in WebArena context...")
    
    try:
        # Mock the required parameters for execute_python_code
        def mock_send_message(msg):
            print(f"SEND MESSAGE: {msg}")
        
        def mock_report_infeasible(msg):
            print(f"INFEASIBLE: {msg}")
        
        class MockPage:
            pass
        
        execute_python_code(
            test_code,
            MockPage(),
            send_message_to_user=mock_send_message,
            report_infeasible_instructions=mock_report_infeasible,
            agent_args=args
        )
        
    except Exception as e:
        print(f"Execution failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_mcp_execution()