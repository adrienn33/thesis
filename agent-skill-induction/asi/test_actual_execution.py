#!/usr/bin/env python3
"""
Test the actual execution path that browsergym uses
"""
import sys
sys.path.insert(0, '.')

# Simulate exactly what happens during task execution
test_code_with_explanation = '''To find reviewers who mention underwater photos, I will:

1. Retrieve all reviews for this product using the `magento_review_server_get_product_reviews` function.
2. Loop through the reviews and check if the review detail contains the phrase "underwater photo".
3. If a review mentions underwater photos, I will send the reviewer's nickname to the user.

```
reviews = magento_review_server_get_product_reviews("B001D0G57S")
for review in reviews:
    if "underwater photo" in review["detail"].lower():
        send_msg_to_user(f"Reviewer {review['nickname']} mentioned underwater photos.")
```
'''

# Import the custom action set to see what it does with this
from custom_action_set import CustomActionSet
from mcp_integration.client import MCPManager, MCPServerConfig

# Create a mock MCP manager
manager = MCPManager()
server_config = MCPServerConfig(
    name="magento-review-server",
    command=["docker", "exec", "-i", "shopping", "python3", "/tmp/magento_review_data.py"]
)
manager.add_server(server_config)

# Create action set like the agent does
action_set = CustomActionSet(
    subsets=["custom"],
    custom_actions=[],
    strict=False,
    multiaction=True,
    demo_mode="off",
    mcp_manager=manager
)

print("=== Testing to_python_code ===")
try:
    python_code = action_set.to_python_code(test_code_with_explanation)
    print(f"Generated {len(python_code)} characters of Python code")
    print("\n=== Extracted Code ===")
    # Find the actual action code (after all the imports)
    lines = python_code.split('\n')
    # Find where the actual user code starts (after all the function definitions)
    start_idx = 0
    for i, line in enumerate(lines):
        if 'reviews = magento_review_server_get_product_reviews' in line:
            start_idx = max(0, i - 2)
            break
    
    if start_idx > 0:
        print("Last 10 lines before user code:")
        for line in lines[max(0, start_idx-10):start_idx]:
            print(f"  {line}")
        print("\nUser code:")
        for line in lines[start_idx:start_idx+10]:
            print(f"  {line}")
    else:
        print("Could not find user code in generated Python")
        print("\nLast 30 lines of generated code:")
        for line in lines[-30:]:
            print(f"  {line}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
