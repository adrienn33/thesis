# REPL-Style Auto-Display for Agent Actions

## Overview

This feature enables REPL-style automatic display of expression results when the agent executes Python code. When the agent calls a function like `magento_product_server_search_products(name="Amazon Basics")`, the result is automatically captured and made available to the agent in its next observation without requiring explicit print statements or variable assignments.

## How It Works

### 1. Expression Detection & Evaluation

**File**: `patch_with_custom_exec.py` (lines 87-146)

The custom execution logic uses Python's AST (Abstract Syntax Tree) to detect when the last statement in the executed code is an expression:

```python
# Parse code to detect structure
tree = ast.parse(code, mode='exec')

# Check if the LAST statement is an expression
if tree.body and isinstance(tree.body[-1], ast.Expr):
    # Execute all preceding statements, then eval the last expression
    # ...
    result = eval(compile(last_expr, '<string>', 'eval'), globals)
    
    # Display non-None results
    if result is not None:
        result_str = repr(result)
        if len(result_str) > 10000:
            result_str = result_str[:10000] + f"... (truncated, total length: {len(result_str)})"
        send_message_to_user(f"→ {result_str}")
```

**Key Details**:
- Only the **last statement** is checked (handles `python_includes` prepended code)
- Uses `eval()` for the final expression to get the return value
- Truncates output to 10KB to avoid overwhelming the context
- Prefixes output with "→ " marker for easy identification

### 2. Storage in Global Variable

**File**: `patch_with_custom_exec.py` (lines 134-135)

The REPL output is stored in a global variable instead of being sent to chat messages (to avoid triggering WebArena's STOP action):

```python
global repl_output
repl_output = f"→ {result_str}"
```

This is then transferred to the environment's `last_action_output` field in the step function (lines 199-204):

```python
global repl_output
if repl_output is not None:
    self.last_action_output = repl_output
else:
    self.last_action_output = ""
```

### 3. Display to Agent in Next Observation

**File**: `agent.py` (lines 407-418)

Modified the agent's prompt building to display `last_action_output` in task mode:

```python
# Show REPL-style output from previous action
if obs.get("last_action_output"):
    user_msgs.append({
        "type": "text",
        "text": f"""
# Output from last action

{obs["last_action_output"]}

"""
    })
```

The observation preprocessor (line 47) includes this field:

```python
"last_action_output": obs.get("last_action_output", ""),
```

This appears in the agent's prompt as:
```
# Output from last action

→ [{'entity_id': 77264, 'sku': 'B00NH11PEY', 'name': '...', 'price': 5.85}, ...]
```

## Critical Code Paths

### Execution Flow

1. **Agent generates action** → `agent.py:get_action()` (lines 190-483)
2. **BrowserGym executes action** → `patch_with_custom_exec.py:step()` (lines 152-237)
3. **Custom Python execution** → `patch_with_custom_exec.py:execute_python_code()` (lines 13-150)
4. **AST parsing & REPL eval** → Lines 87-150
5. **Result stored in global** → `repl_output = f"→ {result_str}"` (line 135)
6. **Step function sets output** → `self.last_action_output = repl_output` (lines 199-204)
7. **Next observation built** → `agent.py:get_action()` includes REPL output (lines 407-418)

### MCP Tool Integration

**Files**: 
- `agent.py` (lines 87-176): MCP tool wrappers created and added to action space
- `patch_with_custom_exec.py` (lines 45-68): `_call_mcp_tool()` helper injected into exec globals
- `mcp_integration/client.py`: MCP client that communicates with servers

When agent calls `magento_product_server_search_products()`:
1. Wrapper function in `__main__` calls `_call_mcp_tool()`
2. `_call_mcp_tool()` gets tool from MCP manager
3. Tool executes via MCP protocol (stdio with Docker container)
4. Result returned as Python object
5. REPL logic catches it and displays it

## Key Files Reference

| File | Purpose | Key Lines |
|------|---------|-----------|
| `patch_with_custom_exec.py` | Custom execution with REPL logic | 13-150 (execute_python_code), 152-237 (step) |
| `agent.py` | Agent prompt building, shows REPL output | 47 (obs preprocessor), 407-418 (REPL display), 87-176 (MCP setup) |
| `mcp_integration/client.py` | MCP protocol client | 112-148 (call_tool) |
| `mcp_servers/magento_products.py` | MCP server for product search | 159-274 (search_products) |
| `custom_action_set.py` | Defines action space including MCP tools | Full file |

## MCP Server Bug Fix

**File**: `mcp_servers/magento_products.py` (line 249)

Fixed bug where `None` limit parameter caused `int(None)` error:

```python
# Before:
base_query += f" LIMIT {int(limit)}"

# After:
limit_value = int(limit) if limit is not None else 50
base_query += f" LIMIT {limit_value}"
```

## Testing

### Verify REPL Display Works

```bash
# Run agent on task 226
python3 run_demo.py --task_name webarena.226 --model_name claude-3-5-sonnet-20241022 --max_steps 5
```

Check logs for:
1. `INFO - Last statement is an expression - attempting REPL-style eval`
2. `INFO - REPL auto-display sent: [{'entity_id': ...`
3. Agent should see output in step 2 and process it

### Verify MCP Tools Work

```bash
# One-shot test
echo '{"method": "tools/call", "params": {"name": "search_products", "arguments": {"name": "Amazon Basics"}}}' | \
  docker exec -i shopping python3 /tmp/magento_products.py
```

Should return 50 products with prices.

## Known Issues & Limitations

1. **Truncation**: Large results truncated to 10KB (line 131 in patch_with_custom_exec.py)
   - Only ~30 products shown out of 50
   - Consider increasing limit or implementing pagination

2. **Task Evaluation**: Task 226 expects "$5.49 - $375.19" but DB has "$5.49 - $508.37"
   - Config file `config_files/226-mcp-container.json` may need updating
   - Note: Using `last_action_output` instead of chat messages avoids early termination (WebArena only checks chat for STOP actions)

3. **MCP Servers Run in Docker**: Servers execute inside container
   - Server files: `/tmp/magento_review_data.py`, `/tmp/magento_products.py`
   - Update with: `docker cp mcp_servers/magento_products.py shopping:/tmp/magento_products.py`

4. **Stderr Not Visible by Default**: Set logging to DEBUG to see MCP server errors
   - `logger.setLevel(logging.DEBUG)` in relevant files

## Adding New MCP Tools

When adding a new MCP server, you must update:

1. **Task config**: Add server to `mcp_servers` array in `config_files/*.json`
2. **patch_with_custom_exec.py** (line 74): Add server prefix to filter
   ```python
   if callable(obj) and ('magento_review_server' in name or 
                         'magento_product_server' in name or 
                         'your_new_server' in name):
   ```
3. **Copy server to container**: `docker cp mcp_servers/your_server.py shopping:/tmp/`

Without step 2, tools will be in action space but get `NameError` when called.

## Architecture Notes

### Why Use `last_action_output` Instead of Chat Messages?

Initially tried using `chat_messages`, but discovered WebArena's evaluator interprets any assistant message as a STOP action (task completion attempt). This caused premature termination:

```python
# webarena/task.py line 173-174
if chat_messages and chat_messages[-1]["role"] == "assistant":
    last_action = {"action_type": ActionTypes.STOP, "answer": chat_messages[-1]["message"]}
```

Solution: Created `last_action_output` field parallel to `last_action_error`:
- Stored via global variable in execute_python_code()
- Set on environment in step() function  
- Added to observation in obs_preprocessor()
- Displayed in agent prompt
- Not visible to WebArena evaluator (only checks chat_messages)

### Why Not Use `last_action_error`?

- Semantically incorrect (not an error)
- Could confuse agent or evaluation logic
- Separate field makes intent clear

### Execution Context

MCP tool wrappers are created at module level (`__main__`) so they're accessible during `exec()`:
- `agent.py` lines 154-167: Creates wrapper functions in `__main__`
- `patch_with_custom_exec.py` lines 45-76: Adds functions to exec globals
- `_call_mcp_tool` helper must be in both `__main__` and exec globals

## Future Improvements

1. **Smarter Truncation**: Show first/last N items instead of cutting mid-item
2. **Structured Display**: Format dicts/lists more readably for agent
3. **Multiple Outputs**: Track multiple REPL outputs per step, not just last
4. **Output Field**: Add proper `last_action_output` to BrowserGym observations
5. **Disable Evaluation Until Done**: Let agent explicitly signal task completion
