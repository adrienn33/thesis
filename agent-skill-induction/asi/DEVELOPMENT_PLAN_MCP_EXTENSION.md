# Comprehensive Development Plan: WebArena MCP Extension (Task 21-MCP)

Based on my thorough analysis of the WebArena framework, I've created a detailed development plan for extending tasks 21-25 with MCP (Model Context Protocol) server capabilities.

## Executive Summary

**Objective**: Create "task 21-mcp" - an enhanced version of WebArena tasks 21-25 that integrates MCP servers to provide specialized tools for review analysis, content extraction, and shopping domain operations.

**Key Innovation**: Transform static task-solving into dynamic, tool-augmented agent capabilities by integrating MCP servers that provide specialized functions for e-commerce review analysis, data extraction, and shopping workflows.

## Current State Analysis

### WebArena Framework Architecture (`agent.py:64-93`, `custom_action_set.py:30-82`)

The current architecture uses a `CustomActionSet` that dynamically loads actions from website-specific modules:
- **Action Loading**: Dynamic function discovery from `actions/{website}.py` files
- **Tool Integration**: Currently limited to pre-defined Python functions in the actions directory
- **Extensibility**: Actions are discovered through importlib and integrated into the agent's action space

### Tasks 21-25 Analysis

All tasks follow the pattern: **"List out reviewers who mention about {description}"**
- Task 21: "ear cups being small" (5 expected reviewers)
- Task 22: "under water photo" (N/A - no reviewers)
- Task 23: "good fingerprint resistant" (2 expected reviewers: Rachel, T. Gannon)
- Task 24: "price being unfair" (N/A - no reviewers)
- Task 25: "average print quality" (2 expected reviewers: Goldfish, Roxanne Brandon Coffey)

**Current Success Rate**: Mixed results - agents struggle with precise review content analysis and keyword matching.

## Proposed MCP Extension Architecture

### 1. MCP Server Design

#### Core MCP Server: `review-data-server`

**Purpose**: Provide API-like access to structured review data and semantic search capabilities.

**Tools to Expose**:

```python
# Review Data API
- get_product_reviews(product_url: str) -> List[Review]
- search_reviews_semantic(product_url: str, search_terms: List[str]) -> List[ReviewMatch]
- find_reviewers_by_content(product_url: str, keywords: List[str]) -> List[str]

# Data Processing Tools  
- validate_reviewer_names(reviewer_list: List[str]) -> ValidationResult
- format_reviewer_response(matches: List[ReviewMatch]) -> str
```

**Rationale**: Instead of low-level HTML parsing, provide clean API-like access to review data. The server handles the complexity of extracting and structuring review information from WebArena's shopping site.

### 2. Agent Architecture Modifications

#### A. MCP Client Integration (`agent.py` modifications)

```python
class MCPDemoAgent(DemoAgent):
    def __init__(self, 
                 model_name: str,
                 mcp_servers: List[MCPServerConfig] = None,
                 **kwargs):
        super().__init__(model_name, **kwargs)
        self.mcp_clients = []
        if mcp_servers:
            self.mcp_clients = [MCPClient(server) for server in mcp_servers]
    
    def get_mcp_tools(self) -> Dict[str, Callable]:
        """Discover and load tools from all connected MCP servers"""
        tools = {}
        for client in self.mcp_clients:
            server_tools = client.list_tools()
            for tool in server_tools:
                tools[tool.name] = self.create_mcp_tool_wrapper(client, tool)
        return tools
```

#### B. Enhanced Custom Action Set (`custom_action_set.py` modifications)

```python
class MCPCustomActionSet(CustomActionSet):
    def __init__(self, mcp_clients: List[MCPClient] = None, **kwargs):
        super().__init__(**kwargs)
        self.mcp_clients = mcp_clients or []
        self.mcp_tools = self._load_mcp_tools()
        
    def _load_mcp_tools(self) -> Dict[str, HighLevelAction]:
        """Load tools from MCP servers and convert to HighLevelActions"""
        mcp_tools = {}
        for client in self.mcp_clients:
            tools = client.list_tools()
            for tool in tools:
                mcp_tools[tool.name] = self._convert_mcp_tool_to_action(tool, client)
        return mcp_tools
    
    def describe(self, **kwargs) -> str:
        """Include MCP tools in action space description"""
        base_description = super().describe(**kwargs)
        mcp_description = self._describe_mcp_tools()
        return f"{base_description}\n\n# MCP Tools\n{mcp_description}"
```

### 3. Task Configuration Extensions

#### Enhanced Task Configuration for Task 21-MCP

```json
{
  "sites": ["shopping"],
  "task_id": "21-mcp", 
  "mcp_servers": [
    {
      "name": "review-data-server",
      "transport": "stdio",
      "command": "python",
      "args": ["-m", "mcp_servers.review_data"]
    }
  ],
  "require_login": true,
  "storage_state": "./.auth/shopping_state.json",
  "start_url": "localhost:7770/6s-wireless-headphones-over-ear-noise-canceling-hi-fi-bass-foldable-stereo-wireless-kid-headsets-earbuds-with-built-in-mic-micro-sd-tf-fm-for-iphone-samsung-ipad-pc-black-gold.html",
  "intent": "List out reviewers, if exist, who mention about ear cups being small",
  "eval": {
    "eval_types": ["string_match"],
    "reference_answers": {
      "must_include": ["Joseph Brzezinski", "Catso", "Dibbins", "Anglebert Dinkherhump", "Michelle Davis"]
    }
  }
}
```

### 4. Implementation Roadmap

#### Phase 1: MCP Server Implementation (Week 1)

**Files to Create:**
1. `mcp_servers/review_data.py` - Single MCP server for review data access
2. `mcp_integration/client.py` - Simple MCP client wrapper for stdio transport
3. `config_files/21-mcp.json` - MCP-enhanced task configuration

**Key Development Tasks:**
- Implement basic MCP server with stdio transport only
- Create review data extraction and search tools
- Implement simple semantic matching using sentence transformers

#### Phase 2: Agent Integration (Week 2)

**Files to Modify:**
1. `agent.py` - Add MCP client integration to `DemoAgent`  
2. `custom_action_set.py` - Include MCP tools in action space
3. `run_demo.py` - Add MCP server startup argument

**Key Development Tasks:**
- Connect MCP server on agent startup
- Load MCP tools into agent's action space
- Handle MCP tool execution in agent workflow

#### Phase 3: Testing and Validation (Week 3)

**Validation Approach:**
- Test against tasks 21-25 with MCP enhancement
- Compare results with vanilla WebArena approach
- Measure tool usage and success rates

### 5. Technical Specifications

#### MCP Server Implementation

**Simple Review Data Server:**
```python
class ReviewDataServer(MCPServer):
    def __init__(self):
        super().__init__()
        self.nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    @tool("get_product_reviews")
    def get_product_reviews(self, product_url: str) -> List[Review]:
        """Get structured review data for a product URL"""
        # Fetch page content and extract reviews
        # Return structured review objects
        pass
        
    @tool("find_reviewers_by_content") 
    def find_reviewers_by_content(self, product_url: str, keywords: List[str]) -> List[str]:
        """Find reviewer names who mention specific keywords"""
        reviews = self.get_product_reviews(product_url)
        matching_reviewers = []
        for review in reviews:
            if self._semantic_match(review.text, keywords):
                matching_reviewers.append(review.reviewer_name)
        return matching_reviewers
```

#### Agent Integration

**Simple MCP Client Integration:**
```python
class MCPClient:
    def __init__(self, server_command: List[str]):
        self.process = subprocess.Popen(server_command, 
                                       stdin=subprocess.PIPE, 
                                       stdout=subprocess.PIPE)
        
    def call_tool(self, tool_name: str, params: dict):
        """Call MCP tool via stdio transport"""
        request = {"method": "tools/call", "params": {"name": tool_name, "arguments": params}}
        # Send JSON-RPC request and return response
        pass
```

### 6. Expected Improvements

#### Performance Enhancements
- **Precision**: Semantic search provides better keyword matching than string matching
- **Accuracy**: Structured data access reduces parsing errors
- **Consistency**: Standardized tool interface for review analysis

#### Research Value
- **Tool Usage**: Demonstrate MCP integration in agent frameworks
- **Extensibility**: Show how external tools can augment agent capabilities
- **Simplicity**: Provide clean separation between agent logic and domain tools

### 7. Implementation Notes

#### Keep It Simple
- Single MCP server with stdio transport only
- Focus on the core value: better review analysis through semantic search
- Minimal infrastructure - this is a research prototype, not production system

#### Technical Considerations
- MCP server runs as subprocess, communicating via JSON-RPC over stdio
- Agent integration should be lightweight and optional (graceful fallback)
- Focus on demonstrating the value of external tools vs. framework complexity

## Conclusion

This focused plan provides a practical roadmap for enhancing WebArena tasks 21-25 with MCP server capabilities. By creating a simple review data server that provides API-like access to structured review information and semantic search capabilities, we can significantly improve agent performance on review analysis tasks.

The key insight is that MCP should provide capabilities the agent can't easily do itself - in this case, better review parsing and semantic matching. Navigation, HTML parsing, and other web automation tasks are already well-handled by the existing WebArena framework.

This implementation demonstrates MCP integration in agent frameworks while keeping the scope appropriate for a research project - focused, simple, and demonstrating clear value over the baseline approach.