#!/usr/bin/env python3
"""
MCP Server for Magento Checkout & Orders
Provides direct database access to Magento 2 order data
"""
import asyncio
import json
import sys
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import zoneinfo
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

def _parse_product_options(raw: Any) -> list:
    """Parse the product_options JSON column from sales_order_item into a clean list.

    Returns a list of {"label": ..., "value": ...} dicts, or [] if no options.

    Dimension values like "Mist 16*24" are normalized so that '*' is replaced
    with 'x', producing "Mist 16x24".  This ensures substring checks for sizes
    such as "16x24" work correctly against the returned value strings.
    """
    if not raw:
        return []
    try:
        import re as _re
        data = json.loads(raw) if isinstance(raw, str) else raw
        opts = data.get("options", [])
        result = []
        for o in opts:
            value = o.get("value", "")
            # Normalize dimension separator: "16*24" → "16x24"
            value = _re.sub(r'(\d+)\s*\*\s*(\d+)', r'\1x\2', value)
            result.append({"label": o.get("label", ""), "value": value})
        return result
    except Exception:
        return []

# Store timezone cached after first DB read.
_store_tz: Optional[zoneinfo.ZoneInfo] = None

async def _get_store_tz(conn) -> zoneinfo.ZoneInfo:
    """Read the Magento store timezone from core_config_data, cache it."""
    global _store_tz
    if _store_tz is not None:
        return _store_tz
    try:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT value FROM core_config_data WHERE path = 'general/locale/timezone' LIMIT 1"
            )
            row = await cur.fetchone()
            if row and row.get("value"):
                _store_tz = zoneinfo.ZoneInfo(row["value"])
                return _store_tz
    except Exception:
        pass
    # Fallback: UTC (no conversion)
    _store_tz = zoneinfo.ZoneInfo("UTC")
    return _store_tz

def _fmt_dt(dt_value: Any, tz: zoneinfo.ZoneInfo) -> str:
    """Convert a UTC datetime (from MySQL) to the store's local timezone and format as string.

    MySQL returns naive datetime objects; we treat them as UTC, convert to store
    timezone, and return an ISO-like string so the agent sees localized dates
    matching what the Magento frontend displays.
    """
    if dt_value is None:
        return ""
    if isinstance(dt_value, str):
        try:
            dt_value = datetime.fromisoformat(dt_value)
        except ValueError:
            return dt_value
    if isinstance(dt_value, datetime):
        if dt_value.tzinfo is None:
            dt_value = dt_value.replace(tzinfo=timezone.utc)
        local = dt_value.astimezone(tz)
        return local.strftime("%Y-%m-%d %H:%M:%S")
    return str(dt_value)


class MagentoCheckoutServer(MCPServer):
    """MCP server for Magento checkout and orders with direct database access"""
    
    def __init__(self):
        super().__init__()
        
        self.db_config = {
            'host': 'localhost',
            'port': 3306,
            'user': 'magentouser', 
            'password': 'MyPassword',
            'db': 'magentodb'
        }
        
        self.tool("list_orders")(self.list_orders)
        self.tool("get_order_details")(self.get_order_details)
        # Cart write operations disabled — browser session incompatible with direct DB writes.
        # Agent must use browser actions for cart modifications.
        # self.tool("add_to_cart")(self.add_to_cart)
        self.tool("get_cart")(self.get_cart)
        # self.tool("update_cart_item")(self.update_cart_item)
        # self.tool("remove_from_cart")(self.remove_from_cart)
    
    async def _get_db_connection(self):
        """Get database connection"""
        return await aiomysql.connect(**self.db_config)
    
    async def list_orders(self, customer_email: Optional[str] = None, 
                         status: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         limit: str = "100") -> List[Dict]:
        """Get order history with optional filtering by customer, status, and date range.
        
        Args:
            customer_email: Filter by customer email (optional)
            status: Filter by order status (e.g., 'pending', 'processing', 'complete', 'canceled', 'closed') (optional)
            start_date: Start date for order range in format YYYY-MM-DD (optional)
            end_date: End date for order range in format YYYY-MM-DD (optional)
            limit: Maximum number of results (default 100)
            
        Returns:
            List of order dictionaries. Each order has this exact structure:
            [
                {
                    "order_id": 180,                           // int: Internal order ID
                    "order_number": "000000180",              // str: Public order number
                    "state": "complete",                      // str: Order state
                    "status": "complete",                     // str: Order status
                    "customer": {
                        "email": "emma.lopez@gmail.com",      // str: Customer email
                        "firstname": "Emma",                  // str: Customer first name
                        "lastname": "Lopez"                   // str: Customer last name
                    },
                    "created_at": "2023-03-11 09:44:12",     // str: Order creation in store local time (America/New_York)
                    "updated_at": "2023-04-23 12:52:47",     // str: Last update in store local time (America/New_York)
                    "totals": {
                        "grand_total": 65.32,                // float: TOTAL ORDER AMOUNT
                        "subtotal": 40.32,                   // float: Subtotal before shipping/tax
                        "shipping_amount": 25.0,             // float: Shipping cost
                        "tax_amount": 0,                     // float: Tax amount
                        "discount_amount": 0                 // float: Discount amount
                    },
                    "total_qty_ordered": 5,                   // int: Total items quantity
                    "shipping_address": {                     // dict or null
                        "street": "101 S San Mateo Dr",
                        "city": "San Mateo", 
                        "region": "California",
                        "postcode": "94010",
                        "country": "US"
                    }
                }
            ]
            
            CRITICAL: To access the total amount spent, use order['totals']['grand_total']
            NOT order['grand_total'] (which doesn't exist at the root level).
            
        Examples:
            list_orders()
            list_orders(customer_email="emma.lopez@gmail.com")
            list_orders(status="complete")
            list_orders(start_date="2023-03-01", end_date="2023-03-31")
            list_orders(customer_email="emma.lopez@gmail.com", status="pending")
        """
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)
            
            conditions = []
            params = []
            
            query = """
                SELECT 
                    so.entity_id as order_id,
                    so.increment_id as order_number,
                    so.state,
                    so.status,
                    so.customer_email,
                    so.customer_firstname,
                    so.customer_lastname,
                    so.created_at,
                    so.updated_at,
                    so.grand_total,
                    so.subtotal,
                    so.shipping_amount,
                    so.tax_amount,
                    so.discount_amount,
                    so.total_qty_ordered,
                    ssa.street as shipping_street,
                    ssa.city as shipping_city,
                    ssa.region as shipping_region,
                    ssa.postcode as shipping_postcode,
                    ssa.country_id as shipping_country
                FROM sales_order so
                LEFT JOIN sales_order_address ssa 
                    ON so.entity_id = ssa.parent_id 
                    AND ssa.address_type = 'shipping'
            """
            
            # Default to Emma Lopez (WebArena test user) if no customer email specified
            if customer_email is None:
                customer_email = "emma.lopez@gmail.com"
            
            conditions.append("so.customer_email = %s")
            params.append(customer_email)
            
            if status:
                conditions.append("so.status = %s")
                params.append(status)
            
            if start_date:
                conditions.append("DATE(so.created_at) >= %s")
                params.append(start_date)
            
            if end_date:
                conditions.append("DATE(so.created_at) <= %s")
                params.append(end_date)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY so.created_at DESC"
            
            limit_value = int(limit) if limit is not None else 100
            query += f" LIMIT {limit_value}"
            
            logger.info(f"Executing list_orders query with {len(conditions)} conditions")
            await cursor.execute(query, tuple(params))
            results = await cursor.fetchall()
            logger.info(f"Query returned {len(results)} orders")

            tz = await _get_store_tz(conn)
            orders = []
            for row in results:
                orders.append({
                    "order_id": row["order_id"],
                    "order_number": row["order_number"],
                    "state": row["state"],
                    "status": row["status"],
                    "customer": {
                        "email": row["customer_email"],
                        "firstname": row["customer_firstname"],
                        "lastname": row["customer_lastname"]
                    },
                    "created_at": _fmt_dt(row["created_at"], tz),
                    "updated_at": _fmt_dt(row["updated_at"], tz),
                    "totals": {
                        "grand_total": float(row["grand_total"]) if row["grand_total"] else 0,
                        "subtotal": float(row["subtotal"]) if row["subtotal"] else 0,
                        "shipping_amount": float(row["shipping_amount"]) if row["shipping_amount"] else 0,
                        "tax_amount": float(row["tax_amount"]) if row["tax_amount"] else 0,
                        "discount_amount": float(row["discount_amount"]) if row["discount_amount"] else 0
                    },
                    "total_qty_ordered": int(row["total_qty_ordered"]) if row["total_qty_ordered"] else 0,
                    "shipping_address": {
                        "street": row["shipping_street"],
                        "city": row["shipping_city"],
                        "region": row["shipping_region"],
                        "postcode": row["shipping_postcode"],
                        "country": row["shipping_country"]
                    } if row["shipping_street"] else None
                })
            
            await cursor.close()
            conn.close()
            
            logger.info(f"Retrieved {len(orders)} orders")
            return orders
            
        except Exception as e:
            logger.error(f"Error listing orders: {e}")
            return []
    
    async def get_order_details(self, order_id: str) -> Dict:
        """Retrieve detailed information about a specific order by order ID or order number.
        
        Args:
            order_id: Order entity ID or order increment_id (order number like "000000170")
            
        Returns:
            Detailed order dictionary with this structure:
            {
                "order_id": 170,                           // int: Internal order ID
                "order_number": "000000170",              // str: Public order number
                "state": "complete",                      // str: Order state
                "status": "complete",                     // str: Order status
                "customer": {
                    "id": 23,                            // int: Customer ID
                    "email": "emma.lopez@gmail.com",     // str: Customer email
                    "firstname": "Emma",                 // str: Customer first name
                    "lastname": "Lopez"                  // str: Customer last name
                },
                "dates": {
                    "created_at": "2023-02-27 08:15:14", // str: Order creation in store local time (America/New_York)
                    "updated_at": "2023-04-23 12:52:38"  // str: Last update in store local time (America/New_York)
                },
                "totals": {
                    "grand_total": 762.18,              // float: TOTAL ORDER AMOUNT
                    "subtotal": 742.18,                 // float: Subtotal before shipping/tax
                    "shipping_amount": 20.0,            // float: Shipping cost  
                    "tax_amount": 0,                    // float: Tax amount
                    "discount_amount": 0                // float: Discount amount
                },
                "items": [                              // List of order items
                    {
                        "item_id": 456,                 // int: Order item ID
                        "product_id": 789,              // int: Product ID
                        "name": "Product Name",         // str: Product name
                        "sku": "PROD123",               // str: Product SKU
                        "qty": 2,                       // int: Quantity ordered
                        "price": 25.99,                 // float: Unit price
                        "selected_options": [           // list: Chosen configuration at time of purchase
                            {"label": "Color", "value": "Mist 16*24"},
                            {"label": "Size",  "value": "X-Large"}
                        ]                               // Empty list for unconfigured (simple) products
                    }
                ],
                "shipping_address": {                   // dict: Shipping address
                    "street": "101 S San Mateo Dr",
                    "city": "San Mateo",
                    "region": "California", 
                    "postcode": "94010",
                    "country": "US"
                },
                "billing_address": {                    // dict: Billing address
                    "street": "101 S San Mateo Dr",
                    "city": "San Mateo",
                    "region": "California",
                    "postcode": "94010", 
                    "country": "US"
                }
            }
            
            CRITICAL: To access the total amount, use order['totals']['grand_total']
            
        Examples:
            get_order_details("123")
            get_order_details("000000170")
        """
        order_id = str(order_id)
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)

            # Determine if order_id is numeric (entity_id) or order number (increment_id)
            if order_id.isdigit() and len(order_id) <= 6:
                where_clause = "so.entity_id = %s"
                param = int(order_id)
            else:
                where_clause = "so.increment_id = %s"
                param = order_id
            
            # Get main order information
            query = f"""
                SELECT 
                    so.entity_id as order_id,
                    so.increment_id as order_number,
                    so.state,
                    so.status,
                    so.customer_email,
                    so.customer_firstname,
                    so.customer_lastname,
                    so.customer_id,
                    so.created_at,
                    so.updated_at,
                    so.grand_total,
                    so.subtotal,
                    so.shipping_amount,
                    so.shipping_description,
                    so.tax_amount,
                    so.discount_amount,
                    so.discount_description,
                    so.total_qty_ordered,
                    so.weight,
                    so.base_currency_code,
                    so.order_currency_code
                FROM sales_order so
                WHERE {where_clause}
            """
            
            await cursor.execute(query, (param,))
            order_row = await cursor.fetchone()
            
            if not order_row:
                await cursor.close()
                conn.close()
                return {"error": f"Order not found: {order_id}"}
            
            order_entity_id = order_row["order_id"]
            
            # Get order items
            await cursor.execute("""
                SELECT 
                    soi.item_id,
                    soi.product_id,
                    soi.sku,
                    soi.name as product_name,
                    soi.qty_ordered,
                    soi.qty_shipped,
                    soi.qty_canceled,
                    soi.price,
                    soi.row_total,
                    soi.tax_amount,
                    soi.discount_amount,
                    soi.product_options
                FROM sales_order_item soi
                WHERE soi.order_id = %s AND soi.parent_item_id IS NULL
                ORDER BY soi.item_id
            """, (order_entity_id,))
            items = await cursor.fetchall()
            
            # Get shipping address
            await cursor.execute("""
                SELECT 
                    firstname,
                    lastname,
                    company,
                    street,
                    city,
                    region,
                    postcode,
                    country_id,
                    telephone
                FROM sales_order_address
                WHERE parent_id = %s AND address_type = 'shipping'
            """, (order_entity_id,))
            shipping_address = await cursor.fetchone()
            
            # Get billing address
            await cursor.execute("""
                SELECT 
                    firstname,
                    lastname,
                    company,
                    street,
                    city,
                    region,
                    postcode,
                    country_id,
                    telephone
                FROM sales_order_address
                WHERE parent_id = %s AND address_type = 'billing'
            """, (order_entity_id,))
            billing_address = await cursor.fetchone()
            
            # Get payment information
            await cursor.execute("""
                SELECT 
                    method,
                    additional_information
                FROM sales_order_payment
                WHERE parent_id = %s
            """, (order_entity_id,))
            payment = await cursor.fetchone()
            
            await cursor.close()
            conn.close()

            tz = await _get_store_tz(conn)
            # Build response
            order_details = {
                "order_id": order_row["order_id"],
                "order_number": order_row["order_number"],
                "state": order_row["state"],
                "status": order_row["status"],
                "customer": {
                    "id": order_row["customer_id"],
                    "email": order_row["customer_email"],
                    "firstname": order_row["customer_firstname"],
                    "lastname": order_row["customer_lastname"]
                },
                "dates": {
                    "created_at": _fmt_dt(order_row["created_at"], tz),
                    "updated_at": _fmt_dt(order_row["updated_at"], tz)
                },
                "totals": {
                    "grand_total": float(order_row["grand_total"]) if order_row["grand_total"] else 0,
                    "subtotal": float(order_row["subtotal"]) if order_row["subtotal"] else 0,
                    "shipping_amount": float(order_row["shipping_amount"]) if order_row["shipping_amount"] else 0,
                    "tax_amount": float(order_row["tax_amount"]) if order_row["tax_amount"] else 0,
                    "discount_amount": float(order_row["discount_amount"]) if order_row["discount_amount"] else 0
                },
                "currency": {
                    "base": order_row["base_currency_code"],
                    "order": order_row["order_currency_code"]
                },
                "shipping": {
                    "description": order_row["shipping_description"],
                    "amount": float(order_row["shipping_amount"]) if order_row["shipping_amount"] else 0,
                    "address": {
                        "firstname": shipping_address["firstname"] if shipping_address else None,
                        "lastname": shipping_address["lastname"] if shipping_address else None,
                        "company": shipping_address["company"] if shipping_address else None,
                        "street": shipping_address["street"] if shipping_address else None,
                        "city": shipping_address["city"] if shipping_address else None,
                        "region": shipping_address["region"] if shipping_address else None,
                        "postcode": shipping_address["postcode"] if shipping_address else None,
                        "country": shipping_address["country_id"] if shipping_address else None,
                        "telephone": shipping_address["telephone"] if shipping_address else None
                    } if shipping_address else None
                },
                "billing_address": {
                    "firstname": billing_address["firstname"] if billing_address else None,
                    "lastname": billing_address["lastname"] if billing_address else None,
                    "company": billing_address["company"] if billing_address else None,
                    "street": billing_address["street"] if billing_address else None,
                    "city": billing_address["city"] if billing_address else None,
                    "region": billing_address["region"] if billing_address else None,
                    "postcode": billing_address["postcode"] if billing_address else None,
                    "country": billing_address["country_id"] if billing_address else None,
                    "telephone": billing_address["telephone"] if billing_address else None
                } if billing_address else None,
                "payment": {
                    "method": payment["method"] if payment else None
                } if payment else None,
                "items": [
                    {
                        "item_id": item["item_id"],
                        "product_id": item["product_id"],
                        "sku": item["sku"],
                        "name": item["product_name"],
                        "qty_ordered": float(item["qty_ordered"]) if item["qty_ordered"] else 0,
                        "qty": float(item["qty_ordered"]) if item["qty_ordered"] else 0,  # alias for agent compatibility
                        "qty_shipped": float(item["qty_shipped"]) if item["qty_shipped"] else 0,
                        "qty_canceled": float(item["qty_canceled"]) if item["qty_canceled"] else 0,
                        "price": float(item["price"]) if item["price"] else 0,
                        "row_total": float(item["row_total"]) if item["row_total"] else 0,
                        "tax_amount": float(item["tax_amount"]) if item["tax_amount"] else 0,
                        "discount_amount": float(item["discount_amount"]) if item["discount_amount"] else 0,
                        "selected_options": _parse_product_options(item["product_options"])
                    } for item in items
                ],
                "discount_description": order_row["discount_description"],
                "total_qty_ordered": int(order_row["total_qty_ordered"]) if order_row["total_qty_ordered"] else 0,
                "weight": float(order_row["weight"]) if order_row["weight"] else 0
            }
            
            logger.info(f"Retrieved details for order {order_id}")
            return order_details
            
        except Exception as e:
            logger.error(f"Error getting order details for {order_id}: {e}")
            return {"error": str(e)}
    
    async def add_to_cart(self, customer_email: str, product_id: str, qty: str = "1") -> Dict:
        """Add a product to the customer's shopping cart.
        
        Args:
            customer_email: Customer email address
            product_id: Product entity ID or SKU
            qty: Quantity to add (default 1)
            
        Returns:
            Cart update result with this structure:
            {
                "item_id": 234,                      // int: Cart item ID (for future updates/removal)
                "product": {
                    "entity_id": 456,                // int: Product ID
                    "name": "Headphones",            // str: Product name
                    "sku": "B006H52HBC",             // str: Product SKU
                    "price": 29.95                   // float: Unit price
                },
                "qty": 2,                            // int: Quantity added
                "cart_totals": {
                    "items_count": 2,                // int: Number of different items in cart
                    "items_qty": 3,                  // float: Total quantity of all items
                    "grand_total": 89.85             // float: TOTAL CART VALUE
                }
            }
            
            If product already exists in cart, quantities are combined.
            Use the returned item_id for update_cart_item() or remove_from_cart().
            
        Examples:
            add_to_cart("emma.lopez@gmail.com", "B006H52HBC", "2")
            add_to_cart("emma.lopez@gmail.com", "123")
        """
        product_id = str(product_id)
        qty = str(qty)
        try:
            conn = await self._get_db_connection()
            cursor = await conn.cursor(aiomysql.DictCursor)

            # Get customer info
            await cursor.execute(
                "SELECT entity_id, firstname, lastname FROM customer_entity WHERE email = %s",
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
                    cpd.value as price,
                    cpe.type_id
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
            
            if not product_details or not product_details["price"]:
                await cursor.close()
                conn.close()
                return {"error": f"Product details not found or product has no price: {product_id}"}
            
            product_name = product_details["name"]
            product_price = float(product_details["price"])
            product_type = product_details["type_id"]
            
            # Get or create active quote for customer
            await cursor.execute("""
                SELECT entity_id, store_id 
                FROM quote 
                WHERE customer_id = %s AND is_active = 1
                ORDER BY updated_at DESC
                LIMIT 1
            """, (customer_id,))
            quote = await cursor.fetchone()
            
            if quote:
                quote_id = quote["entity_id"]
                store_id = quote["store_id"]
            else:
                # Create new quote
                await cursor.execute("""
                    INSERT INTO quote (
                        store_id, created_at, updated_at, is_active, 
                        customer_id, customer_email, customer_firstname, customer_lastname,
                        customer_is_guest, items_count, items_qty,
                        base_currency_code, store_currency_code, quote_currency_code
                    ) VALUES (
                        1, NOW(), NOW(), 1,
                        %s, %s, %s, %s,
                        0, 0, 0,
                        'USD', 'USD', 'USD'
                    )
                """, (customer_id, customer_email, customer["firstname"], customer["lastname"]))
                quote_id = cursor.lastrowid
                store_id = 1
            
            # Check if product already in cart
            await cursor.execute("""
                SELECT item_id, qty 
                FROM quote_item 
                WHERE quote_id = %s AND product_id = %s AND parent_item_id IS NULL
            """, (quote_id, product_entity_id))
            existing_item = await cursor.fetchone()
            
            qty_value = float(qty)
            
            if existing_item:
                # Update existing item quantity
                new_qty = float(existing_item["qty"]) + qty_value
                await cursor.execute("""
                    UPDATE quote_item 
                    SET qty = %s,
                        row_total = %s,
                        base_row_total = %s,
                        updated_at = NOW()
                    WHERE item_id = %s
                """, (new_qty, new_qty * product_price, new_qty * product_price, existing_item["item_id"]))
                item_id = existing_item["item_id"]
                logger.info(f"Updated cart item {item_id} quantity to {new_qty}")
            else:
                # Add new item to cart
                await cursor.execute("""
                    INSERT INTO quote_item (
                        quote_id, created_at, updated_at, product_id, store_id,
                        sku, name, product_type, qty, price, base_price,
                        row_total, base_row_total, is_virtual
                    ) VALUES (
                        %s, NOW(), NOW(), %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, 0
                    )
                """, (
                    quote_id, product_entity_id, store_id,
                    product_sku, product_name, product_type, qty_value, product_price, product_price,
                    qty_value * product_price, qty_value * product_price
                ))
                item_id = cursor.lastrowid
                logger.info(f"Added new cart item {item_id}")
            
            # Update quote totals
            await cursor.execute("""
                SELECT 
                    COUNT(*) as items_count,
                    SUM(qty) as items_qty,
                    SUM(row_total) as grand_total
                FROM quote_item
                WHERE quote_id = %s AND parent_item_id IS NULL
            """, (quote_id,))
            totals = await cursor.fetchone()
            
            await cursor.execute("""
                UPDATE quote 
                SET items_count = %s,
                    items_qty = %s,
                    grand_total = %s,
                    base_grand_total = %s,
                    updated_at = NOW()
                WHERE entity_id = %s
            """, (
                totals["items_count"],
                totals["items_qty"],
                totals["grand_total"],
                totals["grand_total"],
                quote_id
            ))
            
            await conn.commit()
            await cursor.close()
            conn.close()
            
            logger.info(f"Added product {product_id} to cart for {customer_email}")
            return {
                "success": True,
                "quote_id": quote_id,
                "item_id": item_id,
                "product": {
                    "id": product_entity_id,
                    "sku": product_sku,
                    "name": product_name,
                    "price": product_price
                },
                "qty": qty_value,
                "cart_totals": {
                    "items_count": totals["items_count"],
                    "items_qty": float(totals["items_qty"]),
                    "grand_total": float(totals["grand_total"])
                }
            }
            
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return {"error": str(e)}
    
    async def get_cart(self, customer_email: str) -> Dict:
        """View current shopping cart contents and totals for a customer.
        
        Args:
            customer_email: Customer email address
            
        Returns:
            Cart dictionary with this structure:
            {
                "quote_id": 42,                      // int: Internal cart ID
                "items": [                           // list: Items in cart
                    {
                        "item_id": 123,              // int: Cart item ID (for updates/removal)
                        "product_id": 456,           // int: Product ID
                        "name": "Headphones",        // str: Product name
                        "sku": "B006H52HBC",         // str: Product SKU
                        "qty": 2,                    // int: Quantity in cart
                        "price": 29.95,             // float: Unit price
                        "row_total": 59.90,          // float: Total for this line (qty * price)
                        "product_type": "simple"     // str: Product type
                    }
                ],
                "totals": {
                    "items_count": 1,                // int: Number of item types
                    "items_qty": 2,                  // float: Total quantity of all items
                    "grand_total": 59.90             // float: TOTAL CART VALUE
                }
            }
            
            If cart is empty, items will be empty array and totals will be zero.
            Use item_id for update_cart_item() and remove_from_cart() operations.
            
        Examples:
            get_cart("emma.lopez@gmail.com")
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
            
            # Get active quote
            await cursor.execute("""
                SELECT entity_id, items_count, items_qty, grand_total, created_at, updated_at
                FROM quote 
                WHERE customer_id = %s AND is_active = 1
                ORDER BY updated_at DESC
                LIMIT 1
            """, (customer_id,))
            quote = await cursor.fetchone()
            
            if not quote:
                await cursor.close()
                conn.close()
                return {
                    "quote_id": None,
                    "items": [],
                    "totals": {
                        "items_count": 0,
                        "items_qty": 0,
                        "grand_total": 0
                    }
                }
            
            quote_id = quote["entity_id"]
            
            # Get cart items
            await cursor.execute("""
                SELECT 
                    item_id,
                    product_id,
                    sku,
                    name,
                    qty,
                    price,
                    row_total
                FROM quote_item
                WHERE quote_id = %s AND parent_item_id IS NULL
                ORDER BY item_id
            """, (quote_id,))
            items = await cursor.fetchall()
            
            await cursor.close()
            conn.close()
            
            logger.info(f"Retrieved cart for {customer_email} with {len(items)} items")
            return {
                "quote_id": quote_id,
                "created_at": str(quote["created_at"]),
                "updated_at": str(quote["updated_at"]),
                "items": [
                    {
                        "item_id": item["item_id"],
                        "product_id": item["product_id"],
                        "sku": item["sku"],
                        "name": item["name"],
                        "qty": float(item["qty"]),
                        "price": float(item["price"]),
                        "row_total": float(item["row_total"])
                    } for item in items
                ],
                "totals": {
                    "items_count": quote["items_count"],
                    "items_qty": float(quote["items_qty"]),
                    "grand_total": float(quote["grand_total"])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting cart: {e}")
            return {"error": str(e)}
    
    async def update_cart_item(self, customer_email: str, item_id: str, qty: str) -> Dict:
        """Update the quantity of a specific item in the customer's cart.
        
        Args:
            customer_email: Customer email address
            item_id: Cart item ID (from get_cart response)
            qty: New quantity (must be greater than 0)
            
        Returns:
            Cart update result with this structure:
            {
                "updated_item_id": 123,              // int: Cart item ID that was updated
                "product": {
                    "name": "Headphones",            // str: Product name
                    "sku": "B006H52HBC",             // str: Product SKU
                    "price": 29.95                   // float: Unit price
                },
                "old_qty": 2,                        // int: Previous quantity
                "new_qty": 5,                        // int: New quantity
                "cart_totals": {
                    "items_count": 2,                // int: Number of different items in cart
                    "items_qty": 8,                  // float: Total quantity of all items
                    "grand_total": 179.75            // float: TOTAL CART VALUE
                }
            }
            
            Use item_id from get_cart() or add_to_cart() responses.
            To remove an item completely, use remove_from_cart() instead.
            
        Examples:
            update_cart_item("emma.lopez@gmail.com", "123", "5")
        """
        item_id = str(item_id)
        qty = str(qty)
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

            # Verify item belongs to customer's active cart
            await cursor.execute("""
                SELECT qi.item_id, qi.quote_id, qi.price, qi.product_id, qi.sku, qi.name
                FROM quote_item qi
                JOIN quote q ON qi.quote_id = q.entity_id
                WHERE qi.item_id = %s AND q.customer_id = %s AND q.is_active = 1
            """, (int(item_id), customer_id))
            item = await cursor.fetchone()
            
            if not item:
                await cursor.close()
                conn.close()
                return {"error": f"Item {item_id} not found in customer's active cart"}
            
            qty_value = float(qty)
            if qty_value <= 0:
                await cursor.close()
                conn.close()
                return {"error": "Quantity must be greater than 0. Use remove_from_cart to delete items."}
            
            # Update item quantity
            price_value = float(item["price"])
            await cursor.execute("""
                UPDATE quote_item 
                SET qty = %s,
                    row_total = %s,
                    base_row_total = %s,
                    updated_at = NOW()
                WHERE item_id = %s
            """, (qty_value, qty_value * price_value, qty_value * price_value, int(item_id)))
            
            quote_id = item["quote_id"]
            
            # Update quote totals
            await cursor.execute("""
                SELECT 
                    COUNT(*) as items_count,
                    SUM(qty) as items_qty,
                    SUM(row_total) as grand_total
                FROM quote_item
                WHERE quote_id = %s AND parent_item_id IS NULL
            """, (quote_id,))
            totals = await cursor.fetchone()
            
            await cursor.execute("""
                UPDATE quote 
                SET items_count = %s,
                    items_qty = %s,
                    grand_total = %s,
                    base_grand_total = %s,
                    updated_at = NOW()
                WHERE entity_id = %s
            """, (
                totals["items_count"],
                totals["items_qty"],
                totals["grand_total"],
                totals["grand_total"],
                quote_id
            ))
            
            await conn.commit()
            await cursor.close()
            conn.close()
            
            logger.info(f"Updated cart item {item_id} to quantity {qty_value} for {customer_email}")
            return {
                "success": True,
                "item_id": int(item_id),
                "product": {
                    "id": item["product_id"],
                    "sku": item["sku"],
                    "name": item["name"]
                },
                "qty": qty_value,
                "cart_totals": {
                    "items_count": totals["items_count"],
                    "items_qty": float(totals["items_qty"]),
                    "grand_total": float(totals["grand_total"])
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating cart item: {e}")
            return {"error": str(e)}
    
    async def remove_from_cart(self, customer_email: str, item_id: str) -> Dict:
        """Remove a specific item from the customer's cart.
        
        Args:
            customer_email: Customer email address
            item_id: Cart item ID (from get_cart response)
            
        Returns:
            Cart removal result with this structure:
            {
                "success": true,                     // bool: Operation success
                "removed_item": {
                    "item_id": 123,                  // int: Cart item ID that was removed
                    "sku": "B006H52HBC",             // str: Product SKU that was removed
                    "name": "Headphones"             // str: Product name that was removed
                },
                "cart_totals": {
                    "items_count": 1,                // int: Number of different items remaining
                    "items_qty": 3,                  // float: Total quantity remaining
                    "grand_total": 89.85             // float: TOTAL CART VALUE after removal
                }
            }
            
            If cart becomes empty after removal:
            {
                "success": true,
                "removed_item": {...},
                "cart_totals": {
                    "items_count": 0,
                    "items_qty": 0,
                    "grand_total": 0
                }
            }
            
            Use item_id from get_cart() response to specify which item to remove.
            
        Examples:
            remove_from_cart("emma.lopez@gmail.com", "123")
        """
        item_id = str(item_id)
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

            # Verify item belongs to customer's active cart
            await cursor.execute("""
                SELECT qi.item_id, qi.quote_id, qi.sku, qi.name
                FROM quote_item qi
                JOIN quote q ON qi.quote_id = q.entity_id
                WHERE qi.item_id = %s AND q.customer_id = %s AND q.is_active = 1
            """, (int(item_id), customer_id))
            item = await cursor.fetchone()
            
            if not item:
                await cursor.close()
                conn.close()
                return {"error": f"Item {item_id} not found in customer's active cart"}
            
            quote_id = item["quote_id"]
            removed_name = item["name"]
            
            # Delete the item
            await cursor.execute(
                "DELETE FROM quote_item WHERE item_id = %s",
                (int(item_id),)
            )
            
            # Update quote totals
            await cursor.execute("""
                SELECT 
                    COUNT(*) as items_count,
                    SUM(qty) as items_qty,
                    SUM(row_total) as grand_total
                FROM quote_item
                WHERE quote_id = %s AND parent_item_id IS NULL
            """, (quote_id,))
            totals = await cursor.fetchone()
            
            # Handle empty cart case
            if totals["items_count"] == 0:
                await cursor.execute("""
                    UPDATE quote 
                    SET items_count = 0,
                        items_qty = 0,
                        grand_total = 0,
                        base_grand_total = 0,
                        updated_at = NOW()
                    WHERE entity_id = %s
                """, (quote_id,))
            else:
                await cursor.execute("""
                    UPDATE quote 
                    SET items_count = %s,
                        items_qty = %s,
                        grand_total = %s,
                        base_grand_total = %s,
                        updated_at = NOW()
                    WHERE entity_id = %s
                """, (
                    totals["items_count"],
                    totals["items_qty"],
                    totals["grand_total"],
                    totals["grand_total"],
                    quote_id
                ))
            
            await conn.commit()
            await cursor.close()
            conn.close()
            
            logger.info(f"Removed item {item_id} from cart for {customer_email}")
            return {
                "success": True,
                "removed_item_id": int(item_id),
                "removed_product_name": removed_name,
                "cart_totals": {
                    "items_count": totals["items_count"] or 0,
                    "items_qty": float(totals["items_qty"]) if totals["items_qty"] else 0,
                    "grand_total": float(totals["grand_total"]) if totals["grand_total"] else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error removing from cart: {e}")
            return {"error": str(e)}

async def main():
    """Main entry point"""
    server = MagentoCheckoutServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
