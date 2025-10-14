#!/usr/bin/env python3
"""
MCP Server for Magento Review Data Integration
Provides direct database access to Magento 2 review data
"""
import asyncio
import json
import sys
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import aiomysql
# from sentence_transformers import SentenceTransformer
# import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            result = await tool_func(**arguments)
            
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

class MagentoReviewServer(MCPServer):
    """MCP server for Magento review data with direct database access"""
    
    def __init__(self):
        super().__init__()
        
        # Database connection config
        self.db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'magentouser', 
            'password': 'MyPassword',
            'db': 'magentodb'
        }
        
        # Load semantic model for advanced search
        # logger.info("Loading semantic search model...")
        # self.nlp_model = SentenceTransformer('all-MiniLM-L6-v2')
        # logger.info("Semantic model loaded successfully")
        
        # Register tools
        self.tool("get_product_reviews")(self.get_product_reviews)
        self.tool("create_review")(self.create_review)
        # self.tool("search_reviews_semantic")(self.search_reviews_semantic)
    
    async def _get_db_connection(self):
        """Get database connection"""
        return await aiomysql.connect(**self.db_config)
    
    async def get_product_reviews(self, product_id: str) -> List[Dict]:
        """Retrieve all reviews for a specific product by product ID or SKU
        
        Args:
            product_id: Product entity ID or SKU
            
        Returns:
            List of reviews with review_id, title, detail, nickname, rating, created_at
            
        Examples:
            get_product_reviews("123")
            get_product_reviews("B006H52HBC")
        """
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            # Check if product_id is numeric (entity_id) or alphanumeric (SKU)
            if product_id.isdigit():
                where_clause = "r.entity_pk_value = %s"
                param = int(product_id)
            else:
                where_clause = "cpe.sku = %s"
                param = product_id
            
            query = f"""
                SELECT 
                    r.review_id,
                    r.entity_pk_value as product_id,
                    cpe.sku as product_sku,
                    rd.nickname,
                    rd.title,
                    rd.detail,
                    r.created_at,
                    AVG(rov.value) as rating
                FROM review r
                JOIN review_detail rd ON r.review_id = rd.review_id
                JOIN catalog_product_entity cpe ON r.entity_pk_value = cpe.entity_id  
                LEFT JOIN rating_option_vote rov ON r.review_id = rov.review_id
                WHERE {where_clause} AND r.status_id = 1
                GROUP BY r.review_id
                ORDER BY r.created_at DESC
            """
            
            await cursor.execute(query, (param,))
            results = await cursor.fetchall()
            
            reviews = []
            for row in results:
                reviews.append({
                    "review_id": row["review_id"],
                    "product_id": row["product_id"], 
                    "product_sku": row["product_sku"],
                    "nickname": row["nickname"] or "Anonymous",
                    "title": row["title"] or "",
                    "detail": row["detail"] or "",
                    "created_at": str(row["created_at"]),
                    "rating": float(row["rating"]) if row["rating"] else None
                })
            
            await cursor.close()
            conn.close()
            
            logger.info(f"Found {len(reviews)} reviews for product {product_id}")
            return reviews
            
        except Exception as e:
            logger.error(f"Error getting reviews for product {product_id}: {e}")
            return []
    
    async def create_review(self, product_id: str, title: str, detail: str, nickname: str, rating: Optional[int] = None) -> Dict:
        """Submit a review for a product. Does not require user authentication.
        
        Args:
            product_id: Product entity ID or SKU
            title: Review title
            detail: Review detail text
            nickname: Reviewer nickname
            rating: Optional rating value (1-5)
            
        Returns:
            Created review information with review_id
            
        Examples:
            create_review("B006H52HBC", "Great product", "I really enjoyed this item", "JohnDoe", 5)
        """
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            # Resolve product_id to entity_id if SKU provided
            if not product_id.isdigit():
                await cursor.execute(
                    "SELECT entity_id FROM catalog_product_entity WHERE sku = %s",
                    (product_id,)
                )
                result = await cursor.fetchone()
                if not result:
                    await cursor.close()
                    conn.close()
                    return {"error": f"Product not found: {product_id}"}
                entity_id = result["entity_id"]
            else:
                entity_id = int(product_id)
            
            # Insert into review table (entity_id=1 is for products, status_id=1 is approved)
            await cursor.execute("""
                INSERT INTO review (created_at, entity_id, entity_pk_value, status_id)
                VALUES (NOW(), 1, %s, 1)
            """, (entity_id,))
            
            review_id = cursor.lastrowid
            
            # Insert into review_detail table
            await cursor.execute("""
                INSERT INTO review_detail (review_id, store_id, title, detail, nickname, customer_id)
                VALUES (%s, 1, %s, %s, %s, NULL)
            """, (review_id, title, detail, nickname))
            
            # Insert rating if provided
            if rating is not None:
                rating_int = int(rating) if isinstance(rating, str) else rating
                if 1 <= rating_int <= 5:
                    # Get the default rating (usually rating_id=1 for "Rating")
                    await cursor.execute("SELECT rating_id FROM rating WHERE rating_code = 'Rating' LIMIT 1")
                    rating_result = await cursor.fetchone()
                    if rating_result:
                        rating_id = rating_result["rating_id"]
                        # Get the option_id for the rating value
                        await cursor.execute(
                            "SELECT option_id FROM rating_option WHERE rating_id = %s AND value = %s",
                            (rating_id, rating_int)
                        )
                        option_result = await cursor.fetchone()
                        if option_result:
                            option_id = option_result["option_id"]
                            await cursor.execute("""
                                INSERT INTO rating_option_vote (option_id, review_id, value, entity_pk_value, remote_ip, remote_ip_long)
                                VALUES (%s, %s, %s, %s, '127.0.0.1', 0)
                            """, (option_id, review_id, rating_int, entity_id))
            
            await conn.commit()
            await cursor.close()
            conn.close()
            
            logger.info(f"Created review {review_id} for product {product_id}")
            return {
                "review_id": review_id,
                "product_id": entity_id,
                "title": title,
                "detail": detail,
                "nickname": nickname,
                "rating": rating,
                "status": "created"
            }
            
        except Exception as e:
            logger.error(f"Error creating review for product {product_id}: {e}")
            return {"error": str(e)}
    
    # Semantic search temporarily disabled - uncomment when running with ML dependencies
    # async def search_reviews_semantic(self, product_id: str, search_terms: str) -> List[Dict]:
    #     """Find reviews using semantic search by product ID or SKU. Returns reviews ranked by semantic similarity.
    #     
    #     Args:
    #         product_id: Product entity ID or SKU
    #         search_terms: Search query (e.g., "too narrow", "poor quality", "battery life")
    #         
    #     Returns:
    #         List of semantically similar reviews with confidence scores
    #         
    #     Examples:
    #         search_reviews_semantic("B006H52HBC", "too narrow tight fit")
    #         search_reviews_semantic("123", "battery life duration")
    #     """
    #     try:
    #         reviews = await self.get_product_reviews(product_id)
    #         
    #         if not reviews:
    #             return []
    #         
    #         # Create embeddings for search terms
    #         search_embedding = self.nlp_model.encode([search_terms])
    #         
    #         # Create embeddings for reviews
    #         review_texts = [f"{r['title']} {r['detail']}" for r in reviews]
    #         review_embeddings = self.nlp_model.encode(review_texts)
    #         
    #         # Calculate cosine similarities
    #         from sklearn.metrics.pairwise import cosine_similarity
    #         similarities = cosine_similarity(search_embedding, review_embeddings)[0]
    #         
    #         # Filter and sort by similarity
    #         matches = []
    #         for i, similarity in enumerate(similarities):
    #             if similarity > 0.3:  # Relevance threshold
    #                 review = reviews[i].copy()
    #                 review["semantic_score"] = float(similarity)
    #                 review["search_query"] = search_terms
    #                 matches.append(review)
    #         
    #         # Sort by semantic score descending
    #         matches.sort(key=lambda x: x["semantic_score"], reverse=True)
    #         
    #         logger.info(f"Found {len(matches)} semantically similar reviews for '{search_terms}'")
    #         return matches
    #         
    #     except Exception as e:
    #         logger.error(f"Error performing semantic search: {e}")
    #         return []

async def main():
    """Main entry point"""
    server = MagentoReviewServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())