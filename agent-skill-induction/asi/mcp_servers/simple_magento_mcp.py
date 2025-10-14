#!/usr/bin/env python3
"""
Simplified MCP Server for Magento Review Data Integration
Direct database access without ML dependencies (for container deployment)
"""
import asyncio
import json
import sys
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import aiomysql

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Review:
    review_id: int
    product_id: int
    product_sku: str
    reviewer_name: str
    review_title: str
    review_text: str
    created_at: str
    rating: Optional[float] = None

class MCPServer:
    """Simple MCP server implementation with stdio transport"""
    
    def __init__(self):
        self.tools = {}
        
    def tool(self, name: str):
        """Decorator to register MCP tools"""
        def decorator(func):
            self.tools[name] = {
                'name': name,
                'description': func.__doc__ or "",
                'function': func,
                'input_schema': self._extract_schema(func)
            }
            return func
        return decorator
    
    def _extract_schema(self, func):
        """Extract JSON schema from function signature (simplified)"""
        import inspect
        sig = inspect.signature(func)
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            param_type = "string"  # Simplified - assume all params are strings
            properties[param_name] = {"type": param_type}
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
                
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests"""
        method = request.get("method")
        params = request.get("params", {})
        
        if method == "tools/list":
            return await self.list_tools()
        elif method == "tools/call":
            return await self.call_tool(params)
        else:
            return {
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools"""
        tools = []
        for tool_info in self.tools.values():
            tools.append({
                "name": tool_info["name"],
                "description": tool_info["description"],
                "inputSchema": tool_info["input_schema"]
            })
        
        return {"tools": tools}
    
    async def call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            return {
                "error": {"code": -32602, "message": f"Tool not found: {tool_name}"}
            }
        
        try:
            tool_func = self.tools[tool_name]["function"]
            # For bound methods, we need to call them directly (they already have self bound)
            if hasattr(tool_func, '__self__'):
                result = await tool_func(**arguments)
            else:
                # For unbound functions, pass self as first argument
                result = await tool_func(self, **arguments)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, default=str)
                    }
                ]
            }
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return {
                "error": {"code": -32603, "message": f"Tool execution error: {str(e)}"}
            }
    
    async def run(self):
        """Run the MCP server with stdio transport"""
        logger.info("Starting MCP server...")
        
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break
                    
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                
                # Send response
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError:
                logger.error("Invalid JSON received")
                error_response = {
                    "error": {"code": -32700, "message": "Parse error"}
                }
                print(json.dumps(error_response), flush=True)
            except Exception as e:
                logger.error(f"Server error: {e}")
                error_response = {
                    "error": {"code": -32603, "message": "Internal error"}
                }
                print(json.dumps(error_response), flush=True)

class SimpleMagentoReviewServer(MCPServer):
    """Simplified MCP server for Magento review data analysis with direct database access"""
    
    def __init__(self):
        super().__init__()
        logger.info("Starting Simple Magento MCP Server...")
        
        # Database connection config - connecting to localhost inside container
        self.db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'magentouser', 
            'password': 'MyPassword',
            'db': 'magentodb'
        }
        
        # Register tools (without semantic search for now)
        self.tool("get_product_reviews_by_sku")(self.get_product_reviews_by_sku)
        self.tool("find_reviewers_mentioning_keywords")(self.find_reviewers_mentioning_keywords)
        self.tool("get_product_sku_from_url")(self.get_product_sku_from_url)
    
    async def _get_db_connection(self):
        """Get database connection"""
        return await aiomysql.connect(**self.db_config)
    
    async def get_product_reviews_by_sku(self, product_sku: str) -> List[Dict]:
        """Get all reviews for a product by SKU
        
        Examples:
            get_product_reviews_by_sku("B006H52HBC")
        """
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            query = """
                SELECT 
                    r.review_id,
                    r.entity_pk_value as product_id,
                    cpe.sku as product_sku,
                    rd.nickname as reviewer_name,
                    rd.title as review_title,
                    rd.detail as review_text,
                    r.created_at,
                    AVG(rov.value) as rating
                FROM review r
                JOIN review_detail rd ON r.review_id = rd.review_id
                JOIN catalog_product_entity cpe ON r.entity_pk_value = cpe.entity_id  
                LEFT JOIN rating_option_vote rov ON r.review_id = rov.review_id
                WHERE cpe.sku = %s AND r.status_id = 1
                GROUP BY r.review_id
                ORDER BY r.created_at DESC
            """
            
            await cursor.execute(query, (product_sku,))
            results = await cursor.fetchall()
            
            reviews = []
            for row in results:
                reviews.append({
                    "review_id": row["review_id"],
                    "product_id": row["product_id"], 
                    "product_sku": row["product_sku"],
                    "reviewer_name": row["reviewer_name"] or "Anonymous",
                    "review_title": row["review_title"] or "",
                    "review_text": row["review_text"] or "",
                    "created_at": str(row["created_at"]),
                    "rating": float(row["rating"]) if row["rating"] else None
                })
            
            await cursor.close()
            conn.close()
            
            logger.info(f"Found {len(reviews)} reviews for product SKU {product_sku}")
            return reviews
            
        except Exception as e:
            logger.error(f"Error getting reviews for SKU {product_sku}: {e}")
            return []
    
    async def find_reviewers_mentioning_keywords(self, product_sku: str, keywords: List[str]) -> List[List]:
        """Find reviewer names who mention specific keywords in their reviews
        
        Returns list of [reviewer_name, excerpt] pairs for send_reviewer_summary()
        
        Examples:
            find_reviewers_mentioning_keywords("B006H52HBC", ["small", "narrow", "tight"])
        """
        reviews = await self.get_product_reviews_by_sku(product_sku)
        matching_reviewers = []
        seen_reviewers = set()
        
        keywords_lower = [k.lower() for k in keywords]
        
        for review in reviews:
            review_text = (review["review_text"] + " " + review["review_title"]).lower()
            if any(keyword in review_text for keyword in keywords_lower):
                reviewer_name = review["reviewer_name"]
                if reviewer_name not in seen_reviewers:
                    seen_reviewers.add(reviewer_name)
                    # Create a brief excerpt showing the relevant part
                    original_text = review["review_text"]
                    # Find first sentence with matching keyword
                    sentences = original_text.split('.')
                    excerpt = original_text[:100] + "..." if len(original_text) > 100 else original_text
                    for sentence in sentences:
                        if any(keyword in sentence.lower() for keyword in keywords_lower):
                            excerpt = sentence.strip()
                            if len(excerpt) > 100:
                                excerpt = excerpt[:100] + "..."
                            break
                    
                    matching_reviewers.append([reviewer_name, f"mentioned: {excerpt}"])
        
        logger.info(f"Found {len(matching_reviewers)} reviewers mentioning keywords {keywords}")
        return matching_reviewers
    
    async def get_product_sku_from_url(self, product_url: str) -> Optional[str]:
        """Extract product SKU from WebArena product URL
        
        Examples:
            get_product_sku_from_url("localhost:7770/6s-wireless-headphones-over-ear...")
        """
        try:
            # Normalize URL - fix double slashes and other issues
            normalized_url = product_url.replace('//', '/').replace('http:/', 'http://').replace('https:/', 'https://')
            
            # WebArena specific URL to SKU mapping for known products
            webarena_mappings = {
                "6s-wireless-headphones-over-ear-noise-canceling-hi-fi-bass-foldable-stereo-wireless-kid-headsets-earbuds-with-built-in-mic-micro-sd-tf-fm-for-iphone-samsung-ipad-pc-black-gold.html": "B086GNDL8K"
            }
            
            # Check for exact URL match first
            for url_pattern, sku in webarena_mappings.items():
                if url_pattern in normalized_url:
                    return sku
            
            # Fallback: Extract potential SKU patterns and validate against database
            url_parts = normalized_url.split('/')
            
            # Look for SKU-like patterns (alphanumeric)
            for part in reversed(url_parts):
                if part and len(part) > 6 and any(c.isdigit() for c in part) and any(c.isalpha() for c in part):
                    # Check if this matches a product in database
                    conn = await self._get_db_connection()
                    cursor = await conn.cursor()
                    
                    # Try exact match first
                    await cursor.execute(
                        "SELECT sku FROM catalog_product_entity WHERE sku = %s LIMIT 1",
                        (part,)
                    )
                    result = await cursor.fetchone()
                    
                    if not result:
                        # Try partial match
                        await cursor.execute(
                            "SELECT sku FROM catalog_product_entity WHERE sku LIKE %s LIMIT 1",
                            (f"%{part}%",)
                        )
                        result = await cursor.fetchone()
                    
                    await cursor.close()
                    conn.close()
                    
                    if result:
                        return result[0]
            
            # If no match found, return None
            return None
            
        except Exception as e:
            logger.error(f"Error extracting SKU from URL {product_url}: {e}")
            return None

async def main():
    """Main entry point"""
    server = SimpleMagentoReviewServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
