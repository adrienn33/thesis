"""
MCP Client for communicating with MCP server running inside Docker container
"""
import json
import subprocess
import logging
import threading
import queue
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from mcp_integration.client import ToolInfo, MCPToolWrapper

logger = logging.getLogger(__name__)

@dataclass
class ContainerMCPServerConfig:
    """Configuration for an MCP server running inside a Docker container"""
    name: str
    container_name: str
    server_path: str
    python_cmd: str = "python3"

class ContainerMCPClient:
    """MCP client that communicates with server running inside Docker container"""
    
    def __init__(self, server_config: ContainerMCPServerConfig):
        self.server_config = server_config
        self.process = None
        self.tools = {}
        self._connected = False
        self._response_queue = queue.Queue()
        self._reader_thread = None
        
    def connect(self) -> bool:
        """Connect to the MCP server running inside container"""
        try:
            logger.info(f"Starting MCP server inside container: {self.server_config.name}")
            
            # Start MCP server inside Docker container
            cmd = [
                "docker", "exec", "-i", self.server_config.container_name,
                self.server_config.python_cmd, self.server_config.server_path
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Unbuffered for real-time communication
            )
            
            # Start reader thread to handle responses
            self._reader_thread = threading.Thread(target=self._read_responses)
            self._reader_thread.daemon = True
            self._reader_thread.start()
            
            # Load available tools
            self._load_tools()
            self._connected = True
            logger.info(f"Connected to container MCP server {self.server_config.name} with {len(self.tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to container MCP server {self.server_config.name}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the MCP server"""
        if self.process:
            self.process.terminate()
            self.process.wait()
            self.process = None
        self._connected = False
    
    def _read_responses(self):
        """Thread to read responses from server"""
        while self.process and self.process.stdout:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                self._response_queue.put(line.strip())
            except Exception as e:
                logger.error(f"Error reading response: {e}")
                break
    
    def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MCP server and get response"""
        if not self.process or not self._connected:
            raise RuntimeError("MCP server not connected")
        
        try:
            # Send request
            request_json = json.dumps(request) + '\n'
            self.process.stdin.write(request_json)
            self.process.stdin.flush()
            
            # Wait for response with timeout
            try:
                response_line = self._response_queue.get(timeout=30)  # 30 second timeout
                return json.loads(response_line)
            except queue.Empty:
                raise RuntimeError("Timeout waiting for response from MCP server")
                
        except Exception as e:
            logger.error(f"Error communicating with container MCP server: {e}")
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

class ContainerMCPManager:
    """Manages MCP clients running inside Docker containers"""
    
    def __init__(self):
        self.clients = {}
        
    def add_server(self, server_config: ContainerMCPServerConfig) -> bool:
        """Add and connect to a container MCP server"""
        client = ContainerMCPClient(server_config)
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
        for server_name, client in self.clients.values():
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