# MCP Developer Portal

Visual debugging and testing interface for Magento MCP servers.

## Features

- **Servers Tab**: View available MCP servers and their status
- **Tools Tab**: Browse all available tools with descriptions and parameters
- **Tests Tab**: Run test scripts (quick/full) with live output streaming
- **Executor Tab**: Manually execute individual tools with custom parameters

## Setup

### 1. Install Frontend Dependencies
```bash
cd dev-portal
npm install
```

### 2. Install Backend Dependencies
```bash
cd ..
pip install flask flask-cors
```

## Running the Portal

### Option 1: Run both together (separate terminals)

**Terminal 1 - Backend:**
```bash
python3 dev_portal_backend.py
```

**Terminal 2 - Frontend:**
```bash
cd dev-portal
npm run dev
```

Then open: http://localhost:5173

### Option 2: Build and serve from Flask

```bash
cd dev-portal
npm run build
cd ..
# Serve the dist/ folder from Flask (TODO: add route)
```

## Usage

### Servers Tab
View which MCP servers are available and their current status.

### Tools Tab
Browse all tools exposed by each server:
- Click on tool descriptions to see details
- Expand "Parameters" to view input schema

### Tests Tab
Run the test scripts:
- **Quick Test**: Smoke test (fast, basic connectivity)
- **Full Test**: Integration test (comprehensive, all tools)

Watch live output as tests execute.

### Executor Tab
Manually call any tool:
1. Select a server
2. Choose a tool
3. Edit JSON arguments
4. Click "Execute Tool"
5. View formatted results

## Example Tool Execution

```json
{
  "product_id": "B006H52HBC"
}
```

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌────────────────┐
│   React     │ ─HTTP─> │    Flask     │ ─exec─> │ MCP Servers    │
│  (Port 5173)│         │  (Port 5000) │         │ (in container) │
└─────────────┘         └──────────────┘         └────────────────┘
```

## Development

- Frontend hot-reloads automatically with Vite
- Backend restarts needed for code changes (or use `flask --debug`)
- MCP servers run inside Docker container (no changes needed)
