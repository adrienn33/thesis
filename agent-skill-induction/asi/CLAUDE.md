# Claude Code Session Guide - ASI Project

## Project Overview
This is the Agent Skill Induction (ASI) project working with WebArena environments and MCP (Model Context Protocol) server integration for the Magento shopping application.

## MCP Servers

We have two MCP servers providing direct database access to the Magento shopping application:

### 1. Review Server (`mcp_servers/magento_review_data.py`)
**Tools:**
- ✅ `get_product_reviews(product_id)` - Get all reviews for a product (by entity ID or SKU)
- ✅ `create_review(product_id, title, detail, nickname, rating)` - Submit a new review (no auth required)
- ⏸️ `search_reviews_semantic(product_id, search_terms)` - **Temporarily disabled** (requires ML dependencies - uncomment to enable)

### 2. Product Server (`mcp_servers/magento_products.py`)
**Tools:**
- ✅ `search_products(sku, name, description, category, min_price, max_price, limit)` - Flexible product search
- ✅ `get_product_details(product_id)` - Full product info including stock status and configurable options (color/size)
- ✅ `list_categories()` - Get all product categories

## How MCP Servers Work

**Important:** MCP servers run **inside the Docker container** via `docker exec`, not on the host machine.

**Why inside the container?**
- Direct access to MySQL at `localhost` (no permission issues)
- No need for remote database access configuration
- Simpler dependency management (only `aiomysql` needed in container)

**Server files location:**
- Host: `mcp_servers/magento_review_data.py` and `mcp_servers/magento_products.py`
- Container: `/tmp/magento_review_data.py` and `/tmp/magento_products.py`

**Database connection (from inside container):**
```python
{
    'host': 'localhost',
    'port': 3306,
    'user': 'magentouser',
    'password': 'MyPassword',
    'db': 'magentodb'
}
```

**Updating servers:** After editing server files, copy them to the container:
```bash
docker cp mcp_servers/magento_review_data.py shopping:/tmp/magento_review_data.py
docker cp mcp_servers/magento_products.py shopping:/tmp/magento_products.py
```

### Adding New MCP Servers

When adding a new MCP server, you MUST update `patch_with_custom_exec.py` to make the tools available in the agent's Python execution environment:

1. **Create your MCP server** in `mcp_servers/your_server.py`
2. **Register in agent.py** (add to MCP server configuration)
3. **Update patch_with_custom_exec.py** line ~47:
   ```python
   if callable(obj) and ('magento_review_server' in name or 'magento_product_server' in name or 'your_server_prefix' in name):
   ```
   
**Why this is needed:** MCP tools are connected at the protocol level, but they must be explicitly injected into the agent's `exec()` namespace to be callable as Python functions.

**Symptom if you forget:** Agent will see tools in its action space but get `NameError: name 'your_tool_name' is not defined` when trying to call them.

## Testing

### Quick Test (Smoke Test)
Tests that servers start and respond:
```bash
python3 test_mcp_server.py
```

**Expected output:**
```
Testing MCP Review Data Server...
✅ Connected successfully
✅ Found 2 tools
✅ Tool call succeeded! Found 14 reviews

Testing MCP Product Server...
✅ Connected successfully
✅ Found 3 tools
✅ Search succeeded! Found 5 products
```

### Full Test (Integration Test)
Tests all tools with real database queries:
```bash
python3 test_magento_mcp.py
```

**Expected output:**
```
Testing Magento Review MCP Server...
✅ Found 14 reviews for product B006H52HBC
⚠️ Semantic search failed: Tool not found (expected - disabled)
✅ Review created successfully with ID: 310XXX

Testing Magento Product MCP Server...
✅ Found 5 products matching 'headphones'
✅ Retrieved details for product: Teva Women's Haley Slip-On Shoe
✅ Found 302 categories

============================================================
Review Server: PASS
Product Server: PASS
============================================================
```

**Note:** Virtual environment not required - tests run servers inside Docker container which has all dependencies.

## Container Dependencies

**Currently installed in container:**
- `aiomysql` - MySQL async database driver (✅ working)

**Not installed (semantic search disabled):**
- `sentence-transformers` - Would enable semantic review search
- `scikit-learn` - Required for semantic search

To enable semantic search later, uncomment the code in `magento_review_data.py` and install dependencies in container.

## Docker Container
The shopping application runs in Docker:
```bash
docker ps | grep shopping  # Check if running
docker exec shopping mysql -umagentouser -pMyPassword magentodb -e "SHOW TABLES;"
```

Container exposes:
- Port 7770: Web interface
- Port 3306: MySQL database

## Key Files

### MCP Servers
- `mcp_servers/magento_review_data.py` - Review operations
- `mcp_servers/magento_products.py` - Product browsing

### Tests
- `test_mcp_server.py` - Quick smoke test
- `test_magento_mcp.py` - Full integration test

### Documentation
- `proposed_mcp_actions.md` - Defines all MCP actions (some commented out for Phase 1)
- `MCP_INTEGRATION_STATUS_AND_CONTEXT.md` - Integration status
- `DEVELOPMENT_PLAN_MCP_EXTENSION.md` - Development plan

## Troubleshooting

### "No response from MCP server"
→ Check Docker container is running: `docker ps | grep shopping`
→ Verify server files are in container: `docker exec shopping ls -la /tmp/*.py`
→ Copy servers to container if missing (see "Updating servers" section above)

### "Error connecting to database"
→ Database connection only works from inside container
→ Tests automatically run servers via `docker exec -i shopping python3 /tmp/...`
→ Don't try to run servers directly from host

### "Tool search_reviews_semantic not found"
→ This is expected - semantic search is commented out
→ Warning is normal, not an error

### "Field 'remote_ip' doesn't have a default value"
→ Should be fixed - the `rating_option_vote` table requires `remote_ip`
→ Code provides dummy IP `'127.0.0.1'` automatically
→ If still failing, check `magento_review_data.py` line ~310

### Tests run but return no data
→ Check Docker container has data: `docker exec shopping mysql -umagentouser -pMyPassword magentodb -e "SELECT COUNT(*) FROM review;"`
→ Product "B006H52HBC" should exist and have reviews

## Phase 1 Status: ✅ Complete

**Implemented and Working:**
- ✅ Product browsing (search, details, categories) - 3 tools
- ✅ Review operations (get, create) - 2 tools  
- ⏸️ Semantic review search - disabled (can be enabled with ML dependencies)

**Future Phases (see `proposed_mcp_actions.md`):**
- User account management
- Shopping cart operations
- Checkout/orders
- Wishlist

**Test Results:**
Both test scripts pass successfully with real data from the Magento database.

## MCP Developer Portal 🎨

A visual web interface for exploring and debugging MCP servers.

### Quick Start
```bash
./start_portal.sh
```
Then open: http://localhost:5173

### Features
- **Servers Tab**: View available MCP servers and status
- **Tools Tab**: Browse all tools with descriptions and parameters
- **Tests Tab**: Run test scripts with live output streaming
- **Executor Tab**: Manually execute tools with custom JSON arguments

### Manual Setup
If the startup script doesn't work:

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
python3 dev_portal_backend.py
```

**Terminal 2 - Frontend:**
```bash
cd dev-portal
npm install  # First time only
npm run dev
```

### Architecture
- **Frontend**: React + Vite + Tailwind CSS (port 5173)
- **Backend**: Flask API (port 5000)
- **MCP Servers**: Run in Docker container via `docker exec`

See `dev-portal/README.md` for detailed documentation.

## WebArena Task Architecture

### Task Execution Flow
1. **Agent Model (Claude)**: Generates actions based on browser state (`agent.py:173-451`)
2. **Action Critic (OpenAI GPT)**: Evaluates each action after Claude generates it
3. **Environment**: Executes the action in browser via Playwright
4. **Task Validator**: Checks if goal is achieved (WebArena's built-in evaluators)

### OpenAI API Usage During Tasks

**Important**: OpenAI API calls you see in logs are **NOT** for the agent itself - they are for **online action evaluation**.

**Pattern in logs:**
```
Claude generates action → OpenAI evaluates action → Claude sees evaluation → Claude generates next action
```

**What OpenAI evaluates:**
- Each action Claude proposes (happens during task execution)
- Provides feedback/reward signal on action quality
- Logic was in `evaluation_patch.py` (now only exists as `__pycache__/evaluation_patch.cpython-313.pyc`)

**Evidence:**
- Task 22 logs show 10 OpenAI API calls (one per action step)
- Calls happen between Claude actions: `grep "api.openai.com" results/webarena.*/experiment.log`
- Format: `httpx - INFO - HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"`

**Dev Portal displays this:**
- Backend (`dev_portal_backend.py:386-434`) parses OpenAI API calls from logs
- Frontend shows amber "OpenAI Action Evaluation" panel in trajectory viewer
- Restart backend after code changes: `python3 dev_portal_backend.py`

### Agent Model Configuration
- Primary model: Claude (specified via `--model_name`, default: `claude-3-haiku-20240307`)
- Agent code: `agent.py` (DemoAgent class)
- Action execution: `patch_with_custom_exec.py` (custom Python exec environment)
- Task configs: `config_files/*.json` (use `-mcp-container.json` suffix for MCP-enabled tasks)

### Final Evaluation (Post-Task)
After task completes, a separate evaluation process runs:
- Script: `autoeval/evaluate_trajectory.py`
- Uses Claude OR OpenAI to judge overall success
- Creates `{model}_autoeval.json` in results directory
- This is different from the online action critic

**Key files:**
- `autoeval/evaluator.py` - Evaluation orchestration
- `autoeval/prompts.py` - Evaluation prompts (vision & text modes)
- `autoeval/clients.py` - Model clients (Claude/OpenAI)

**Note:** `gpt-4o` requests in `CLIENT_DICT` actually use `Claude_Vision_Client` - the codebase has been adapted to use Claude for most evaluations.
