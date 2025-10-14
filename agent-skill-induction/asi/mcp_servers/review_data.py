#!/usr/bin/env python3
"""
MCP Server for Review Data Analysis
Provides API-like access to structured review data and semantic search capabilities.
"""
import asyncio
import json
import sys
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Review:
    reviewer_name: str
    review_text: str
    rating: Optional[str] = None
    date: Optional[str] = None

@dataclass
class ReviewMatch:
    reviewer_name: str
    review_text: str
    confidence: float
    matched_keywords: List[str]

class MCPServer:
    """Simple MCP server implementation with stdio transport"""
    
    def __init__(self):
        self.tools = {}
        self.nlp_model = None
        
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
            result = await tool_func(**arguments)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
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

class ReviewDataServer(MCPServer):
    """MCP server for review data analysis"""
    
    def __init__(self):
        super().__init__()
        logger.info("Loading semantic model...")
        self.nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully")
        
        # Register tools
        self.tool("get_product_reviews")(self.get_product_reviews)
        self.tool("find_reviewers_by_content")(self.find_reviewers_by_content)
        self.tool("search_reviews_semantic")(self.search_reviews_semantic)
    
    async def get_product_reviews(self, product_html: str) -> List[Dict]:
        """Get structured review data from product page HTML"""
        try:
            # Parse the provided HTML
            soup = BeautifulSoup(product_html, 'html.parser')
            reviews = self._extract_reviews_from_html(soup)
            
            return [
                {
                    "reviewer_name": review.reviewer_name,
                    "review_text": review.review_text,
                    "rating": review.rating,
                    "date": review.date
                }
                for review in reviews
            ]
            
        except Exception as e:
            logger.error(f"Error parsing reviews from HTML: {e}")
            return []
    
    async def find_reviewers_by_content(self, product_html: str, keywords: List[str]) -> List[str]:
        """Find reviewer names who mention specific keywords"""
        reviews_data = await self.get_product_reviews(product_html)
        matching_reviewers = []
        
        for review_data in reviews_data:
            if self._contains_keywords(review_data["review_text"], keywords):
                matching_reviewers.append(review_data["reviewer_name"])
        
        return matching_reviewers
    
    async def search_reviews_semantic(self, product_html: str, search_terms: List[str]) -> List[Dict]:
        """Find reviews using semantic search"""
        reviews_data = await self.get_product_reviews(product_html)
        
        if not reviews_data:
            return []
        
        # Create embeddings for search terms
        search_query = " ".join(search_terms)
        search_embedding = self.nlp_model.encode([search_query])
        
        # Create embeddings for reviews
        review_texts = [r["review_text"] for r in reviews_data]
        review_embeddings = self.nlp_model.encode(review_texts)
        
        # Calculate similarities
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(search_embedding, review_embeddings)[0]
        
        # Filter and sort by similarity
        matches = []
        for i, similarity in enumerate(similarities):
            if similarity > 0.3:  # Threshold for relevance
                matches.append({
                    "reviewer_name": reviews_data[i]["reviewer_name"],
                    "review_text": reviews_data[i]["review_text"],
                    "confidence": float(similarity),
                    "matched_terms": search_terms
                })
        
        # Sort by confidence
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        return matches
    
    def _extract_reviews_from_html(self, soup: BeautifulSoup) -> List[Review]:
        """Extract review data from HTML soup"""
        reviews = []
        
        # This is a simplified extraction - would need to be customized for actual WebArena HTML structure
        # Look for common review patterns
        review_containers = soup.find_all(['div', 'section'], class_=['review', 'comment', 'feedback'])
        
        if not review_containers:
            # Fallback: look for text patterns that might be reviews
            text_blocks = soup.find_all('p')
            review_containers = [p for p in text_blocks if len(p.get_text().strip()) > 50]
        
        for container in review_containers:
            reviewer_name = self._extract_reviewer_name(container)
            review_text = container.get_text().strip()
            
            if reviewer_name and review_text:
                reviews.append(Review(
                    reviewer_name=reviewer_name,
                    review_text=review_text
                ))
        
        return reviews
    
    def _extract_reviewer_name(self, container) -> Optional[str]:
        """Extract reviewer name from review container"""
        # Look for name patterns in the container
        name_indicators = ['by', 'from', 'reviewer:', 'customer:', 'user:']
        text = container.get_text().lower()
        
        for indicator in name_indicators:
            if indicator in text:
                # Simple name extraction logic
                parts = text.split(indicator)
                if len(parts) > 1:
                    potential_name = parts[1].split()[0:2]  # Take first two words after indicator
                    return ' '.join(potential_name).strip()
        
        return "Anonymous"
    
    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords (case insensitive)"""
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

async def main():
    """Main entry point"""
    server = ReviewDataServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())