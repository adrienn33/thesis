#!/usr/bin/env python3
import asyncio
import logging
import sys
import json
from typing import Optional, Dict, List, Any
import aiomysql

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'magentouser',
    'password': 'MyPassword',
    'db': 'magentodb'
}

class MCPServer:
    def __init__(self):
        self.tools = {}
        self.db_pool = None
        
    def tool(self, name: str):
        def decorator(func):
            self.tools[name] = {
                'name': name,
                'description': func.__doc__ or '',
                'handler': func
            }
            return func
        return decorator
    
    async def initialize_db(self):
        self.db_pool = await aiomysql.create_pool(
            **DB_CONFIG,
            minsize=1,
            maxsize=5,
            autocommit=True
        )
        
    async def cleanup(self):
        if self.db_pool:
            self.db_pool.close()
            await self.db_pool.wait_closed()

class MagentoAccountServer(MCPServer):
    def __init__(self):
        super().__init__()
        self.tool("get_account_info")(self.get_account_info)
        self.tool("update_account_info")(self.update_account_info)
        
    async def get_account_info(self, customer_email: str) -> Dict:
        """Get comprehensive account information for a customer.
        
        Args:
            customer_email: Customer email address
            
        Returns:
            Customer account information with this structure:
            {
                "customer_id": 123,                  // int: Customer entity ID
                "email": "emma.lopez@gmail.com",     // str: Customer email address
                "firstname": "Emma",                 // str: Customer first name
                "lastname": "Lopez",                 // str: Customer last name
                "created_at": "2023-01-15T10:30:00", // str: Account creation timestamp
                "is_active": true,                   // bool: Account status
                "default_billing_id": 456,          // int|null: Default billing address ID
                "default_shipping_id": 456,         // int|null: Default shipping address ID
                "addresses": [                       // list: Customer addresses
                    {
                        "address_id": 456,           // int: Address entity ID
                        "firstname": "Emma",         // str: Address first name
                        "lastname": "Lopez",         // str: Address last name
                        "street": "123 Main St",     // str: Street address
                        "city": "San Francisco",     // str: City
                        "region": "California",      // str: State/region
                        "postcode": "94105",         // str: ZIP/postal code
                        "country_id": "US",          // str: Country code
                        "telephone": "555-0123",     // str: Phone number
                        "is_default_billing": true,  // bool: Is default billing address
                        "is_default_shipping": true, // bool: Is default shipping address
                        "company": "ABC Corp",       // str|optional: Company name
                        "prefix": "Ms.",             // str|optional: Name prefix
                        "middlename": "Marie",       // str|optional: Middle name
                        "suffix": "Jr.",             // str|optional: Name suffix
                        "fax": "555-0124"            // str|optional: Fax number
                    }
                ],
                "prefix": "Ms.",                     // str|optional: Customer name prefix
                "middlename": "Marie",               // str|optional: Customer middle name
                "suffix": "Jr.",                     // str|optional: Customer name suffix
                "date_of_birth": "1990-05-15",      // str|optional: Date of birth
                "gender": "Female"                   // str|optional: "Male", "Female", "Other", "Not Specified"
            }
            
            Or error response:
            {
                "error": "Customer not found: invalid@email.com"
            }
            
            Use this to get complete customer profile including all saved addresses.
            
        Examples:
            get_account_info("convexegg@gmail.com")
        """
        customer_email = str(customer_email)
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT 
                        entity_id,
                        email,
                        firstname,
                        lastname,
                        prefix,
                        middlename,
                        suffix,
                        dob,
                        gender,
                        created_at,
                        updated_at,
                        default_billing,
                        default_shipping,
                        is_active,
                        store_id,
                        website_id,
                        group_id
                    FROM customer_entity
                    WHERE email = %s
                """, (customer_email,))
                
                customer = await cursor.fetchone()
                
                if not customer:
                    return {
                        "error": f"Customer not found: {customer_email}"
                    }
                
                logger.info(f"Found customer: {customer['email']} (ID: {customer['entity_id']})")
                
                await cursor.execute("""
                    SELECT 
                        entity_id,
                        firstname,
                        lastname,
                        prefix,
                        middlename,
                        suffix,
                        company,
                        street,
                        city,
                        region,
                        region_id,
                        postcode,
                        country_id,
                        telephone,
                        fax,
                        is_active
                    FROM customer_address_entity
                    WHERE parent_id = %s
                    ORDER BY entity_id
                """, (customer['entity_id'],))
                
                addresses = await cursor.fetchall()
                
                address_list = []
                for addr in addresses:
                    address_data = {
                        "address_id": addr['entity_id'],
                        "firstname": addr['firstname'],
                        "lastname": addr['lastname'],
                        "street": addr['street'],
                        "city": addr['city'],
                        "region": addr['region'],
                        "postcode": addr['postcode'],
                        "country_id": addr['country_id'],
                        "telephone": addr['telephone'],
                        "is_default_billing": (addr['entity_id'] == customer['default_billing']),
                        "is_default_shipping": (addr['entity_id'] == customer['default_shipping'])
                    }
                    
                    if addr['prefix']:
                        address_data['prefix'] = addr['prefix']
                    if addr['middlename']:
                        address_data['middlename'] = addr['middlename']
                    if addr['suffix']:
                        address_data['suffix'] = addr['suffix']
                    if addr['company']:
                        address_data['company'] = addr['company']
                    if addr['fax']:
                        address_data['fax'] = addr['fax']
                    
                    address_list.append(address_data)
                
                gender_map = {0: "Not Specified", 1: "Male", 2: "Female", 3: "Other"}
                
                result = {
                    "customer_id": customer['entity_id'],
                    "email": customer['email'],
                    "firstname": customer['firstname'],
                    "lastname": customer['lastname'],
                    "created_at": customer['created_at'].isoformat() if customer['created_at'] else None,
                    "is_active": bool(customer['is_active']),
                    "addresses": address_list,
                    "default_billing_id": customer['default_billing'],
                    "default_shipping_id": customer['default_shipping']
                }
                
                if customer['prefix']:
                    result['prefix'] = customer['prefix']
                if customer['middlename']:
                    result['middlename'] = customer['middlename']
                if customer['suffix']:
                    result['suffix'] = customer['suffix']
                if customer['dob']:
                    result['date_of_birth'] = customer['dob'].isoformat()
                if customer['gender']:
                    result['gender'] = gender_map.get(customer['gender'], "Not Specified")
                
                logger.info(f"Retrieved account info for {customer_email} with {len(address_list)} addresses")
                
                return result
    
    async def update_account_info(self, customer_email: str, 
                                  firstname: Optional[str] = None,
                                  lastname: Optional[str] = None,
                                  prefix: Optional[str] = None,
                                  middlename: Optional[str] = None,
                                  suffix: Optional[str] = None,
                                  dob: Optional[str] = None,
                                  gender: Optional[str] = None) -> Dict:
        """Update customer account information.
        
        Args:
            customer_email: Customer email address (used to identify customer)
            firstname: First name (optional)
            lastname: Last name (optional)
            prefix: Name prefix like Mr., Mrs., Dr. (optional)
            middlename: Middle name (optional)
            suffix: Name suffix like Jr., Sr., III (optional)
            dob: Date of birth in YYYY-MM-DD format (optional)
            gender: Gender - "male", "female", "other", or "not_specified" (optional)
            
        Returns:
            Account update result with this structure:
            {
                "success": true,                     // bool: Update operation success
                "customer_id": 123,                  // int: Customer entity ID
                "updated_fields": [                  // list: Fields that were changed
                    "firstname",
                    "lastname"
                ],
                "customer_info": {                   // dict: Complete updated customer info
                    "customer_id": 123,              // Same structure as get_account_info()
                    "email": "emma.lopez@gmail.com",
                    "firstname": "Emma",
                    "lastname": "Lopez-Smith",
                    "addresses": [...],
                    ...
                }
            }
            
            Or error responses:
            {
                "error": "Customer not found: invalid@email.com"
            }
            {
                "error": "No fields to update",
                "customer_id": 123,
                "email": "emma.lopez@gmail.com"
            }
            
            Only specify fields you want to update. Unspecified fields remain unchanged.
            Gender values: "male", "female", "other", "not_specified" (case insensitive).
            
        Examples:
            update_account_info("emma.lopez@gmail.com", firstname="Emma", lastname="Lopez-Smith")
            update_account_info("convexegg@gmail.com", dob="1990-05-15", gender="male")
        """
        customer_email = str(customer_email)
        async with self.db_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("""
                    SELECT entity_id, firstname, lastname
                    FROM customer_entity
                    WHERE email = %s
                """, (customer_email,))
                
                customer = await cursor.fetchone()
                
                if not customer:
                    return {
                        "error": f"Customer not found: {customer_email}"
                    }
                
                customer_id = customer['entity_id']
                
                update_fields = []
                update_values = []
                
                if firstname is not None:
                    update_fields.append("firstname = %s")
                    update_values.append(firstname)
                
                if lastname is not None:
                    update_fields.append("lastname = %s")
                    update_values.append(lastname)
                
                if prefix is not None:
                    update_fields.append("prefix = %s")
                    update_values.append(prefix if prefix else None)
                
                if middlename is not None:
                    update_fields.append("middlename = %s")
                    update_values.append(middlename if middlename else None)
                
                if suffix is not None:
                    update_fields.append("suffix = %s")
                    update_values.append(suffix if suffix else None)
                
                if dob is not None:
                    update_fields.append("dob = %s")
                    update_values.append(dob if dob else None)
                
                if gender is not None:
                    gender_map = {
                        "not_specified": 0,
                        "male": 1,
                        "female": 2,
                        "other": 3
                    }
                    gender_value = gender_map.get(str(gender).lower(), 0)
                    update_fields.append("gender = %s")
                    update_values.append(gender_value)
                
                if not update_fields:
                    return {
                        "error": "No fields to update",
                        "customer_id": customer_id,
                        "email": customer_email
                    }
                
                update_fields.append("updated_at = NOW()")
                
                update_values.append(customer_id)
                
                query = f"""
                    UPDATE customer_entity
                    SET {', '.join(update_fields)}
                    WHERE entity_id = %s
                """
                
                await cursor.execute(query, update_values)
                
                logger.info(f"Updated customer {customer_email} (ID: {customer_id}) - fields: {', '.join(f.split(' = ')[0] for f in update_fields if 'updated_at' not in f)}")
                
                updated_info = await self.get_account_info(customer_email)
                
                return {
                    "success": True,
                    "customer_id": customer_id,
                    "updated_fields": [f.split(' = ')[0] for f in update_fields if 'updated_at' not in f],
                    "customer_info": updated_info
                }

async def handle_request(request_line: str, server: MagentoAccountServer):
    try:
        request = json.loads(request_line)
        method = request.get('method')
        params = request.get('params', {})
        request_id = request.get('id')
        
        if method == 'tools/list':
            tools_list = [
                {
                    'name': tool['name'],
                    'description': tool['description'],
                    'inputSchema': {
                        'type': 'object',
                        'properties': {}
                    }
                }
                for tool in server.tools.values()
            ]
            return {'tools': tools_list}
        
        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})
            
            if tool_name not in server.tools:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {
                        'code': -32601,
                        'message': f'Tool not found: {tool_name}'
                    }
                }
            
            tool = server.tools[tool_name]
            result = await tool['handler'](**arguments)
            
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': {
                    'content': [
                        {
                            'type': 'text',
                            'text': json.dumps(result, indent=2, default=str)
                        }
                    ]
                }
            }
        
        else:
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32601,
                    'message': f'Method not found: {method}'
                }
            }
    
    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        return {
            'jsonrpc': '2.0',
            'id': request.get('id') if 'request' in locals() else None,
            'error': {
                'code': -32603,
                'message': f'Internal error: {str(e)}'
            }
        }

async def main():
    logger.info("Starting MCP server...")
    
    server = MagentoAccountServer()
    await server.initialize_db()
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            response = await handle_request(line, server)
            print(json.dumps(response), flush=True)
    
    finally:
        await server.cleanup()

if __name__ == '__main__':
    asyncio.run(main())
