#!/usr/bin/env python3
"""Test to understand the python_includes issue"""
import ast

# Simulate what CustomActionSet.to_python_code() does
python_includes = """
import playwright.sync_api
import requests
from typing import Literal

def _call_mcp_tool(tool_name, **kwargs):
    pass
"""

user_code = 'magento_product_server_search_products(name="Amazon Basics")'

# What gets sent to execute_python_code
full_code = python_includes + user_code

print("User code:")
print(user_code)
print("\nFull code sent to execute_python_code:")
print(full_code)
print("\n" + "=" * 80)

# Parse and check structure
tree = ast.parse(full_code, mode='exec')
print(f"Number of statements: {len(tree.body)}")
print(f"Last statement type: {type(tree.body[-1])}")
print(f"Is single expression? {len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr)}")

print("\n" + "=" * 80)
print("PROBLEM: python_includes are prepended, so it's never a single expression!")
