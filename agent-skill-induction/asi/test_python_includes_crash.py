#!/usr/bin/env python3
"""Test if python_includes + MCP call causes a crash"""
import ast

# Simulate what actually gets executed
python_includes = """
import playwright.sync_api
import requests
from typing import Literal
from browsergym.utils.obs import flatten_axtree_to_str, flatten_dom_to_str, prune_html
from bs4 import BeautifulSoup

demo_mode='off'
retry_with_force=False

if demo_mode is None:
    demo_mode = "default" if DEMO_MODE else "off"

def some_util_func():
    pass
"""

user_code = 'magento_product_server_search_products(name="Amazon Basics")'

full_code = python_includes + "\n" + user_code

print("Parsing code...")
try:
    tree = ast.parse(full_code, mode='exec')
    print(f"✓ Parsed successfully: {len(tree.body)} statements")
    print(f"Last statement type: {type(tree.body[-1])}")
    print(f"Is last an Expr? {isinstance(tree.body[-1], ast.Expr)}")
    
    if isinstance(tree.body[-1], ast.Expr):
        print("\nAttempting to split code for REPL-style execution...")
        
        # This is what the patch does
        last_expr_node = tree.body[-1]
        preceding_code = ast.Module(body=tree.body[:-1], type_ignores=[])
        
        print(f"✓ Created preceding_code AST module")
        
        # Try to compile
        compiled_preceding = compile(preceding_code, '<string>', 'exec')
        print(f"✓ Compiled preceding code")
        
        # Try to compile last expression
        last_expr = ast.Expression(body=last_expr_node.value)
        compiled_last = compile(last_expr, '<string>', 'eval')
        print(f"✓ Compiled last expression")
        
        print("\n✅ No crash - AST manipulation works!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
