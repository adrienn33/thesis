"""
Simple MCP Client for WebArena Agent Integration
Handles communication with MCP servers via stdio transport
"""
import json
import subprocess
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    command: List[str]
    env: Optional[Dict[str, str]] = None

@dataclass 
class ToolInfo:
    """Information about an MCP tool"""
    name: str
    description: str
    input_schema: Dict[str, Any]

class MCPClient:
    """Simple MCP client using stdio transport"""
    
    def __init__(self, server_config: MCPServerConfig):
        self.server_config = server_config
        self.process = None
        self.tools = {}
        self._connected = False
        
    def connect(self) -> bool:
        """Connect to the MCP server"""
        try:
            logger.info(f"Starting MCP server: {self.server_config.name}")
            self.process = subprocess.Popen(
                self.server_config.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.server_config.env
            )
            
            # Load available tools
            self._load_tools()
            self._connected = True
            logger.info(f"Connected to MCP server {self.server_config.name} with {len(self.tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.server_config.name}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the MCP server"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
        self._connected = False
    
    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MCP server and get response"""
        if not self.process:
            raise RuntimeError("MCP server not connected")
        
        try:
            # Send request
            request_json = json.dumps(request) + '\n'
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # Read response
            response_line = self.process.stdout.readline()
            if not response_line:
                raise RuntimeError("No response from MCP server")
            
            response = json.loads(response_line.strip())
            return response
            
        except Exception as e:
            logger.error(f"Error communicating with MCP server: {e}")
            raise
    
    def _load_tools(self):
        """Load available tools from the MCP server"""
        request = {"method": "tools/list", "params": {}}
        response = self._send_request(request)
        
        if "error" in response:
            raise RuntimeError(f"Error loading tools: {response['error']}")
        
        tools_data = response.get("tools", [])
        for tool_data in tools_data:
            tool_info = ToolInfo(
                name=tool_data["name"],
                description=tool_data["description"],
                input_schema=tool_data["inputSchema"]
            )
            self.tools[tool_info.name] = tool_info
    
    def list_tools(self) -> List[ToolInfo]:
        """Get list of available tools"""
        return list(self.tools.values())
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call an MCP tool with given arguments"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        
        request = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        response = self._send_request(request)
        
        if "error" in response:
            raise RuntimeError(f"Tool execution error: {response['error']}")
        
        # Extract result from response content
        content = response.get("content", [])
        if content and content[0].get("type") == "text":
            try:
                # Try to parse JSON result
                return json.loads(content[0]["text"])
            except json.JSONDecodeError:
                # Return raw text if not JSON
                return content[0]["text"]
        
        return None

class MCPToolWrapper:
    """Wrapper to make MCP tools callable like regular functions"""
    
    def __init__(self, client: MCPClient, tool_info: ToolInfo):
        self.client = client
        self.tool_info = tool_info
        
    def __call__(self, **kwargs):
        """Execute the MCP tool"""
        return self.client.call_tool(self.tool_info.name, kwargs)
    
    def get_signature(self) -> str:
        """Generate function signature for action space"""
        params = []
        properties = self.tool_info.input_schema.get('properties', {})
        required = self.tool_info.input_schema.get('required', [])
        
        for param_name, param_info in properties.items():
            param_type = param_info.get('type', 'str')
            if param_name in required:
                params.append(f"{param_name}: {param_type}")
            else:
                params.append(f"{param_name}: {param_type} = None")
        
        return f"{self.tool_info.name}({', '.join(params)})"
    
    def get_description(self) -> str:
        """Get tool description formatted for WebArena action set"""
        base_description = self.tool_info.description or "MCP tool"
        # Format as expected by CustomActionSet (needs "Examples:" section)
        return f"{base_description}\n\nExamples:\n    {self.tool_info.name}()"

class MCPManager:
    """Manages multiple MCP clients"""
    
    def __init__(self):
        self.clients = {}
        
    def add_server(self, server_config: MCPServerConfig) -> bool:
        """Add and connect to an MCP server"""
        client = MCPClient(server_config)
        if client.connect():
            self.clients[server_config.name] = client
            return True
        return False
    
    def disconnect_all(self):
        """Disconnect from all MCP servers"""
        for client in self.clients.values():
            client.disconnect()
        self.clients.clear()
    
    def get_all_tools(self) -> Dict[str, MCPToolWrapper]:
        """Get all tools from all connected servers"""
        all_tools = {}
        for server_name, client in self.clients.items():
            for tool_info in client.list_tools():
                tool_wrapper = MCPToolWrapper(client, tool_info)
                # Prefix tool name with server name to avoid conflicts
                tool_key = f"{server_name}_{tool_info.name}"
                all_tools[tool_key] = tool_wrapper
        return all_tools
    
    def get_tools_for_server(self, server_name: str) -> Dict[str, MCPToolWrapper]:
        """Get tools for a specific server"""
        if server_name not in self.clients:
            return {}
        
        client = self.clients[server_name]
        tools = {}
        for tool_info in client.list_tools():
            tool_wrapper = MCPToolWrapper(client, tool_info)
            tools[tool_info.name] = tool_wrapper
        return tools