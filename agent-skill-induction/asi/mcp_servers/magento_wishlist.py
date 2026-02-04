#!/usr/bin/env python3
"""
MCP Server for Magento Wishlist
Provides direct database access to Magento 2 wishlist data
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

class MagentoWishlistServer(MCPServer):
    """MCP server for Magento wishlist with direct database access"""
    
    def __init__(self):
        super().__init__()
        
        self.db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'magentouser', 
            'password': 'MyPassword',
            'db': 'magentodb'
        }
        
        self.tool("get_wishlist")(self.get_wishlist)
        self.tool("add_to_wishlist")(self.add_to_wishlist)
        self.tool("remove_from_wishlist")(self.remove_from_wishlist)
    
    async def _get_db_connection(self):
        """Get database connection"""
        return await aiomysql.connect(**self.db_config)
    
    async def get_wishlist(self, customer_email: str = "emma.lopez@gmail.com") -> Dict:
        """View all items in the customer's wishlist.
        
        Args:
            customer_email: Customer email address (defaults to Emma Lopez)
            
        Returns:
            Wishlist information with this structure:
            {
                "wishlist_id": 123,                  // int: Wishlist entity ID
                "updated_at": "2023-06-15 14:30:00", // str: Last modification timestamp
                "item_count": 3,                     // int: Total number of items in wishlist
                "items": [                           // list: Wishlist items
                    {
                        "wishlist_item_id": 456,     // int: Unique wishlist item ID
                        "product_id": 789,           // int: Product entity ID
                        "sku": "B006H52HBC",         // str: Product SKU
                        "name": "Headphones",        // str: Product name
                        "price": 29.95,              // float|null: Product price
                        "qty": 2,                    // float: Desired quantity
                        "is_in_stock": true,         // bool: Stock availability
                        "added_at": "2023-06-10 10:15:00", // str: When added to wishlist
                        "description": "Birthday gift" // str: Optional user note/description
                    }
                ]
            }
            
            Empty wishlist response:
            {
                "wishlist_id": 124,
                "items": [],
                "item_count": 0
            }
            
            Error response:
            {
                "error": "Customer not found: invalid@email.com"
            }
            
            Use wishlist_item_id for remove_from_wishlist() operations.
            If customer has no wishlist, one is created automatically.
            
        Examples:
            get_wishlist("emma.lopez@gmail.com")
        """
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            # Get customer ID
            await cursor.execute(
                "SELECT entity_id FROM customer_entity WHERE email = %s",
                (customer_email,)
            )
            customer = await cursor.fetchone()
            
            if not customer:
                await cursor.close()
                conn.close()
                return {"error": f"Customer not found: {customer_email}"}
            
            customer_id = customer["entity_id"]
            
            # Get wishlist
            await cursor.execute("""
                SELECT wishlist_id, shared, updated_at
                FROM wishlist 
                WHERE customer_id = %s
            """, (customer_id,))
            wishlist = await cursor.fetchone()
            
            if not wishlist:
                # Create wishlist if it doesn't exist
                await cursor.execute("""
                    INSERT INTO wishlist (customer_id, shared, updated_at)
                    VALUES (%s, 0, NOW())
                """, (customer_id,))
                wishlist_id = cursor.lastrowid
                await conn.commit()
                
                await cursor.close()
                conn.close()
                return {
                    "wishlist_id": wishlist_id,
                    "items": [],
                    "item_count": 0
                }
            
            wishlist_id = wishlist["wishlist_id"]
            
            # Get wishlist items with product details
            await cursor.execute("""
                SELECT 
                    wi.wishlist_item_id,
                    wi.product_id,
                    wi.added_at,
                    wi.description,
                    wi.qty,
                    cpe.sku,
                    cpev.value as product_name,
                    cpd.value as price,
                    csi.is_in_stock
                FROM wishlist_item wi
                JOIN catalog_product_entity cpe ON wi.product_id = cpe.entity_id
                LEFT JOIN catalog_product_entity_varchar cpev 
                    ON cpe.entity_id = cpev.entity_id 
                    AND cpev.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'name' AND entity_type_id = 4)
                LEFT JOIN catalog_product_entity_decimal cpd
                    ON cpe.entity_id = cpd.entity_id
                    AND cpd.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'price' AND entity_type_id = 4)
                LEFT JOIN cataloginventory_stock_item csi ON cpe.entity_id = csi.product_id
                WHERE wi.wishlist_id = %s
                ORDER BY wi.added_at DESC
            """, (wishlist_id,))
            items = await cursor.fetchall()
            
            await cursor.close()
            conn.close()
            
            logger.info(f"Retrieved wishlist for {customer_email} with {len(items)} items")
            return {
                "wishlist_id": wishlist_id,
                "updated_at": str(wishlist["updated_at"]),
                "items": [
                    {
                        "wishlist_item_id": item["wishlist_item_id"],
                        "product_id": item["product_id"],
                        "sku": item["sku"],
                        "name": item["product_name"],
                        "price": float(item["price"]) if item["price"] else None,
                        "qty": float(item["qty"]) if item["qty"] else 1,
                        "is_in_stock": bool(item["is_in_stock"]),
                        "added_at": str(item["added_at"]),
                        "description": item["description"]
                    } for item in items
                ],
                "item_count": len(items)
            }
            
        except Exception as e:
            logger.error(f"Error getting wishlist: {e}")
            return {"error": str(e)}
    
    async def add_to_wishlist(self, product_id: str, customer_email: str = "emma.lopez@gmail.com", qty: str = "1", description: str = "") -> Dict:
        """Add a product to the customer's wishlist.
        
        Args:
            customer_email: Customer email address (defaults to Emma Lopez)
            product_id: Product entity ID or SKU
            qty: Quantity (default 1)
            description: Optional description/note for the wishlist item
            
        Returns:
            Wishlist addition result with this structure:
            {
                "success": true,                     // bool: Addition operation success
                "wishlist_id": 123,                  // int: Wishlist entity ID
                "wishlist_item_id": 456,             // int: New wishlist item ID
                "product": {
                    "id": 789,                       // int: Product entity ID
                    "sku": "B006H52HBC",             // str: Product SKU
                    "name": "Headphones",            // str: Product name
                    "price": 29.95                   // float|null: Product price
                },
                "qty": 2,                            // float: Quantity added
                "description": "Birthday gift idea" // str: User description/note
            }
            
            Error responses:
            {
                "error": "Customer not found: invalid@email.com"
            }
            {
                "error": "Product not found: InvalidSKU"
            }
            {
                "error": "Product already in wishlist (item_id: 456)"
            }
            
            Product can be specified by entity ID (numeric) or SKU (string).
            Creates wishlist automatically if customer doesn't have one.
            Prevents duplicate items - use update if item already exists.
            
        Examples:
            add_to_wishlist("emma.lopez@gmail.com", "B006H52HBC")
            add_to_wishlist("emma.lopez@gmail.com", "123", "2", "Birthday gift idea")
        """
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            # Get customer ID
            await cursor.execute(
                "SELECT entity_id FROM customer_entity WHERE email = %s",
                (customer_email,)
            )
            customer = await cursor.fetchone()
            
            if not customer:
                await cursor.close()
                conn.close()
                return {"error": f"Customer not found: {customer_email}"}
            
            customer_id = customer["entity_id"]
            
            # Resolve product_id to entity_id if SKU provided
            if not product_id.isdigit():
                await cursor.execute(
                    "SELECT entity_id, sku FROM catalog_product_entity WHERE sku = %s",
                    (product_id,)
                )
                product = await cursor.fetchone()
                if not product:
                    await cursor.close()
                    conn.close()
                    return {"error": f"Product not found: {product_id}"}
                product_entity_id = product["entity_id"]
                product_sku = product["sku"]
            else:
                product_entity_id = int(product_id)
                await cursor.execute(
                    "SELECT sku FROM catalog_product_entity WHERE entity_id = %s",
                    (product_entity_id,)
                )
                product = await cursor.fetchone()
                if not product:
                    await cursor.close()
                    conn.close()
                    return {"error": f"Product not found: {product_id}"}
                product_sku = product["sku"]
            
            # Get product details
            await cursor.execute("""
                SELECT 
                    cpev.value as name,
                    cpd.value as price
                FROM catalog_product_entity cpe
                LEFT JOIN catalog_product_entity_varchar cpev 
                    ON cpe.entity_id = cpev.entity_id 
                    AND cpev.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'name' AND entity_type_id = 4)
                LEFT JOIN catalog_product_entity_decimal cpd
                    ON cpe.entity_id = cpd.entity_id
                    AND cpd.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'price' AND entity_type_id = 4)
                WHERE cpe.entity_id = %s
            """, (product_entity_id,))
            product_details = await cursor.fetchone()
            
            if not product_details:
                await cursor.close()
                conn.close()
                return {"error": f"Product details not found: {product_id}"}
            
            product_name = product_details["name"]
            product_price = float(product_details["price"]) if product_details["price"] else None
            
            # Get or create wishlist
            await cursor.execute("""
                SELECT wishlist_id 
                FROM wishlist 
                WHERE customer_id = %s
            """, (customer_id,))
            wishlist = await cursor.fetchone()
            
            if wishlist:
                wishlist_id = wishlist["wishlist_id"]
            else:
                # Create new wishlist
                await cursor.execute("""
                    INSERT INTO wishlist (customer_id, shared, updated_at)
                    VALUES (%s, 0, NOW())
                """, (customer_id,))
                wishlist_id = cursor.lastrowid
            
            # Check if product already in wishlist
            await cursor.execute("""
                SELECT wishlist_item_id 
                FROM wishlist_item 
                WHERE wishlist_id = %s AND product_id = %s
            """, (wishlist_id, product_entity_id))
            existing_item = await cursor.fetchone()
            
            if existing_item:
                await cursor.close()
                conn.close()
                return {"error": f"Product already in wishlist (item_id: {existing_item['wishlist_item_id']})"}
            
            # Add item to wishlist
            qty_value = float(qty)
            await cursor.execute("""
                INSERT INTO wishlist_item (
                    wishlist_id, product_id, store_id, added_at, description, qty
                ) VALUES (
                    %s, %s, 1, NOW(), %s, %s
                )
            """, (wishlist_id, product_entity_id, description, qty_value))
            
            wishlist_item_id = cursor.lastrowid
            
            # Update wishlist timestamp
            await cursor.execute("""
                UPDATE wishlist 
                SET updated_at = NOW()
                WHERE wishlist_id = %s
            """, (wishlist_id,))
            
            await conn.commit()
            await cursor.close()
            conn.close()
            
            logger.info(f"Added product {product_id} to wishlist for {customer_email}")
            return {
                "success": True,
                "wishlist_id": wishlist_id,
                "wishlist_item_id": wishlist_item_id,
                "product": {
                    "id": product_entity_id,
                    "sku": product_sku,
                    "name": product_name,
                    "price": product_price
                },
                "qty": qty_value,
                "description": description
            }
            
        except Exception as e:
            logger.error(f"Error adding to wishlist: {e}")
            return {"error": str(e)}
    
    async def remove_from_wishlist(self, wishlist_item_id: str, customer_email: str = "emma.lopez@gmail.com") -> Dict:
        """Remove a specific item from the customer's wishlist.
        
        Args:
            customer_email: Customer email address (defaults to Emma Lopez)
            wishlist_item_id: Wishlist item ID (from get_wishlist response)
            
        Returns:
            Wishlist removal result with this structure:
            {
                "success": true,                     // bool: Removal operation success
                "removed_item_id": 456,              // int: Wishlist item ID that was removed
                "removed_product": {
                    "sku": "B006H52HBC",             // str: Product SKU that was removed
                    "name": "Headphones"             // str: Product name that was removed
                },
                "remaining_items": 2                 // int: Number of items left in wishlist
            }
            
            Error responses:
            {
                "error": "Customer not found: invalid@email.com"
            }
            {
                "error": "Wishlist item 999 not found for customer"
            }
            
            Use wishlist_item_id from get_wishlist() response to specify which item to remove.
            Updates wishlist timestamp automatically after removal.
            
        Examples:
            remove_from_wishlist("emma.lopez@gmail.com", "123")
        """
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            # Get customer ID
            await cursor.execute(
                "SELECT entity_id FROM customer_entity WHERE email = %s",
                (customer_email,)
            )
            customer = await cursor.fetchone()
            
            if not customer:
                await cursor.close()
                conn.close()
                return {"error": f"Customer not found: {customer_email}"}
            
            customer_id = customer["entity_id"]
            
            # Verify item belongs to customer's wishlist and get product details
            await cursor.execute("""
                SELECT 
                    wi.wishlist_item_id,
                    wi.wishlist_id,
                    wi.product_id,
                    cpe.sku,
                    cpev.value as product_name
                FROM wishlist_item wi
                JOIN wishlist w ON wi.wishlist_id = w.wishlist_id
                JOIN catalog_product_entity cpe ON wi.product_id = cpe.entity_id
                LEFT JOIN catalog_product_entity_varchar cpev 
                    ON cpe.entity_id = cpev.entity_id 
                    AND cpev.attribute_id = (SELECT attribute_id FROM eav_attribute WHERE attribute_code = 'name' AND entity_type_id = 4)
                WHERE wi.wishlist_item_id = %s AND w.customer_id = %s
            """, (int(wishlist_item_id), customer_id))
            item = await cursor.fetchone()
            
            if not item:
                await cursor.close()
                conn.close()
                return {"error": f"Wishlist item {wishlist_item_id} not found for customer"}
            
            wishlist_id = item["wishlist_id"]
            product_name = item["product_name"]
            product_sku = item["sku"]
            
            # Delete the item
            await cursor.execute(
                "DELETE FROM wishlist_item WHERE wishlist_item_id = %s",
                (int(wishlist_item_id),)
            )
            
            # Update wishlist timestamp
            await cursor.execute("""
                UPDATE wishlist 
                SET updated_at = NOW()
                WHERE wishlist_id = %s
            """, (wishlist_id,))
            
            # Get remaining item count
            await cursor.execute("""
                SELECT COUNT(*) as item_count
                FROM wishlist_item
                WHERE wishlist_id = %s
            """, (wishlist_id,))
            count_result = await cursor.fetchone()
            remaining_items = count_result["item_count"]
            
            await conn.commit()
            await cursor.close()
            conn.close()
            
            logger.info(f"Removed wishlist item {wishlist_item_id} for {customer_email}")
            return {
                "success": True,
                "removed_item_id": int(wishlist_item_id),
                "removed_product": {
                    "sku": product_sku,
                    "name": product_name
                },
                "remaining_items": remaining_items
            }
            
        except Exception as e:
            logger.error(f"Error removing from wishlist: {e}")
            return {"error": str(e)}

async def main():
    """Main entry point"""
    server = MagentoWishlistServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
