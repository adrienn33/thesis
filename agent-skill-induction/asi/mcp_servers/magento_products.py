#!/usr/bin/env python3
"""
MCP Server for Magento Product Browsing
Provides direct database access to Magento 2 product catalog
"""
import asyncio
import json
import sys
import logging
from typing import List, Dict, Any, Optional
import aiomysql

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
        """Extract JSON schema from function signature"""
        import inspect
        sig = inspect.signature(func)
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue
            param_type = "string"
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

class MagentoProductServer(MCPServer):
    """MCP server for Magento product browsing with direct database access"""
    
    def __init__(self):
        super().__init__()
        
        self.db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'magentouser', 
            'password': 'MyPassword',
            'db': 'magentodb'
        }
        
        self.tool("search_products")(self.search_products)
        self.tool("get_product_details")(self.get_product_details)
        self.tool("list_categories")(self.list_categories)
    
    async def _get_db_connection(self):
        """Get database connection"""
        return await aiomysql.connect(**self.db_config)
    
    async def search_products(self, sku: Optional[str] = None, name: Optional[str] = None, 
                             description: Optional[str] = None, category: Optional[str] = None,
                             min_price: Optional[str] = None, max_price: Optional[str] = None,
                             limit: str = "50") -> List[Dict]:
        """Search for products by SKU, product name, description, category, and/or price range.
        
        Args:
            sku: Product SKU (exact or partial match)
            name: Product name (partial match)
            description: Product description text (partial match)
            category: Category name or ID
            min_price: Minimum price
            max_price: Maximum price
            limit: Maximum number of results (default 50)
            
        Returns:
            List of products with basic information
            
        Examples:
            search_products(sku="B006H52HBC")
            search_products(name="headphones", min_price="20", max_price="100")
            search_products(category="Electronics")
        """
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            conditions = []
            params = []
            
            base_query = """
                SELECT DISTINCT
                    cpe.entity_id,
                    cpe.sku,
                    cpev_name.value as name,
                    cpev_desc.value as description,
                    cpd_price.value as price,
                    csi.qty,
                    csi.is_in_stock
                FROM catalog_product_entity cpe
                LEFT JOIN catalog_product_entity_varchar cpev_name 
                    ON cpe.entity_id = cpev_name.entity_id 
                    AND cpev_name.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'name' AND entity_type_id = 4)
                LEFT JOIN catalog_product_entity_text cpev_desc
                    ON cpe.entity_id = cpev_desc.entity_id
                    AND cpev_desc.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'description' AND entity_type_id = 4)
                LEFT JOIN catalog_product_entity_decimal cpd_price
                    ON cpe.entity_id = cpd_price.entity_id
                    AND cpd_price.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'price' AND entity_type_id = 4)
                LEFT JOIN cataloginventory_stock_item csi ON cpe.entity_id = csi.product_id
            """
            
            if sku:
                conditions.append("cpe.sku LIKE %s")
                params.append(f"%{sku}%")
            
            if name:
                conditions.append("cpev_name.value LIKE %s")
                params.append(f"%{name}%")
            
            if description:
                conditions.append("cpev_desc.value LIKE %s")
                params.append(f"%{description}%")
            
            if category:
                base_query += """
                    LEFT JOIN catalog_category_product ccp ON cpe.entity_id = ccp.product_id
                    LEFT JOIN catalog_category_entity cce ON ccp.category_id = cce.entity_id
                    LEFT JOIN catalog_category_entity_varchar ccev 
                        ON cce.entity_id = ccev.entity_id
                        AND ccev.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'name' AND entity_type_id = 3)
                """
                if category.isdigit():
                    conditions.append("cce.entity_id = %s")
                    params.append(int(category))
                else:
                    conditions.append("ccev.value LIKE %s")
                    params.append(f"%{category}%")
            
            if min_price:
                conditions.append("cpd_price.value >= %s")
                params.append(float(min_price))
            
            if max_price:
                conditions.append("cpd_price.value <= %s")
                params.append(float(max_price))
            
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            
            base_query += f" LIMIT {int(limit)}"
            
            await cursor.execute(base_query, tuple(params))
            results = await cursor.fetchall()
            
            products = []
            for row in results:
                products.append({
                    "entity_id": row["entity_id"],
                    "sku": row["sku"],
                    "name": row["name"],
                    "description": row["description"][:200] + "..." if row["description"] and len(row["description"]) > 200 else row["description"],
                    "price": float(row["price"]) if row["price"] else None,
                    "qty": float(row["qty"]) if row["qty"] else 0,
                    "is_in_stock": bool(row["is_in_stock"])
                })
            
            await cursor.close()
            conn.close()
            
            logger.info(f"Found {len(products)} products matching search criteria")
            return products
            
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []
    
    async def get_product_details(self, product_id: str) -> Dict:
        """Get detailed information about a specific product including description, price, 
        stock status, images, and available options (e.g., color, size for configurable products).
        
        Args:
            product_id: Product entity ID or SKU
            
        Returns:
            Detailed product information
            
        Examples:
            get_product_details("123")
            get_product_details("B006H52HBC")
        """
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            if product_id.isdigit():
                where_clause = "cpe.entity_id = %s"
                param = int(product_id)
            else:
                where_clause = "cpe.sku = %s"
                param = product_id
            
            query = f"""
                SELECT 
                    cpe.entity_id,
                    cpe.sku,
                    cpe.type_id,
                    cpev_name.value as name,
                    cpev_desc.value as description,
                    cpd_price.value as price,
                    csi.qty,
                    csi.is_in_stock,
                    cpev_image.value as image
                FROM catalog_product_entity cpe
                LEFT JOIN catalog_product_entity_varchar cpev_name 
                    ON cpe.entity_id = cpev_name.entity_id 
                    AND cpev_name.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'name' AND entity_type_id = 4)
                LEFT JOIN catalog_product_entity_text cpev_desc
                    ON cpe.entity_id = cpev_desc.entity_id
                    AND cpev_desc.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'description' AND entity_type_id = 4)
                LEFT JOIN catalog_product_entity_decimal cpd_price
                    ON cpe.entity_id = cpd_price.entity_id
                    AND cpd_price.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'price' AND entity_type_id = 4)
                LEFT JOIN catalog_product_entity_varchar cpev_image
                    ON cpe.entity_id = cpev_image.entity_id
                    AND cpev_image.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'image' AND entity_type_id = 4)
                LEFT JOIN cataloginventory_stock_item csi ON cpe.entity_id = csi.product_id
                WHERE {where_clause}
            """
            
            await cursor.execute(query, (param,))
            result = await cursor.fetchone()
            
            if not result:
                await cursor.close()
                conn.close()
                return {"error": f"Product not found: {product_id}"}
            
            product = {
                "entity_id": result["entity_id"],
                "sku": result["sku"],
                "type": result["type_id"],
                "name": result["name"],
                "description": result["description"],
                "price": float(result["price"]) if result["price"] else None,
                "stock": {
                    "qty": float(result["qty"]) if result["qty"] else 0,
                    "is_in_stock": bool(result["is_in_stock"])
                },
                "image": result["image"],
                "options": []
            }
            
            if result["type_id"] == "configurable":
                await cursor.execute("""
                    SELECT 
                        ea.attribute_code,
                        ea.frontend_label,
                        cpsa.attribute_id
                    FROM catalog_product_super_attribute cpsa
                    JOIN eav_attribute ea ON cpsa.attribute_id = ea.attribute_id
                    WHERE cpsa.product_id = %s
                """, (result["entity_id"],))
                
                attributes = await cursor.fetchall()
                
                for attr in attributes:
                    await cursor.execute("""
                        SELECT 
                            eaov.value as option_label,
                            eao.option_id
                        FROM eav_attribute_option eao
                        JOIN eav_attribute_option_value eaov ON eao.option_id = eaov.option_id
                        WHERE eao.attribute_id = %s
                        ORDER BY eao.sort_order
                    """, (attr["attribute_id"],))
                    
                    options = await cursor.fetchall()
                    
                    product["options"].append({
                        "attribute_code": attr["attribute_code"],
                        "label": attr["frontend_label"],
                        "values": [{"option_id": opt["option_id"], "label": opt["option_label"]} for opt in options]
                    })
            
            await cursor.close()
            conn.close()
            
            logger.info(f"Retrieved details for product {product_id}")
            return product
            
        except Exception as e:
            logger.error(f"Error getting product details for {product_id}: {e}")
            return {"error": str(e)}
    
    async def list_categories(self) -> List[Dict]:
        """Get all available product categories.
        
        Returns:
            List of categories with id, name, and parent_id
            
        Examples:
            list_categories()
        """
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            query = """
                SELECT 
                    cce.entity_id,
                    cce.parent_id,
                    ccev.value as name,
                    cce.level,
                    cce.position
                FROM catalog_category_entity cce
                JOIN catalog_category_entity_varchar ccev 
                    ON cce.entity_id = ccev.entity_id
                    AND ccev.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'name' AND entity_type_id = 3)
                WHERE cce.level > 0
                ORDER BY cce.level, cce.position
            """
            
            await cursor.execute(query)
            results = await cursor.fetchall()
            
            categories = []
            for row in results:
                categories.append({
                    "category_id": row["entity_id"],
                    "name": row["name"],
                    "parent_id": row["parent_id"],
                    "level": row["level"]
                })
            
            await cursor.close()
            conn.close()
            
            logger.info(f"Retrieved {len(categories)} categories")
            return categories
            
        except Exception as e:
            logger.error(f"Error listing categories: {e}")
            return []

async def main():
    """Main entry point"""
    server = MagentoProductServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
