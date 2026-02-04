# MCP Response Schemas Reference

This document provides detailed response schemas for all MCP tools to help agents properly handle returned data structures.

## 🛒 Checkout Server (`magento-checkout-server`)

### `list_orders()`

**Returns:** List of order dictionaries
```python
[
    {
        "order_id": 180,                           # int: Internal order ID
        "order_number": "000000180",              # str: Public order number
        "state": "complete",                      # str: Order state
        "status": "complete",                     # str: Order status
        "customer": {
            "email": "emma.lopez@gmail.com",      # str: Customer email
            "firstname": "Emma",                  # str: Customer first name
            "lastname": "Lopez"                   # str: Customer last name
        },
        "created_at": "2023-03-11 14:44:12",     # str: Order creation timestamp
        "updated_at": "2023-04-23 16:52:47",     # str: Last update timestamp
        "totals": {
            "grand_total": 65.32,                # float: TOTAL ORDER AMOUNT
            "subtotal": 40.32,                   # float: Subtotal before shipping/tax
            "shipping_amount": 25.0,             # float: Shipping cost
            "tax_amount": 0,                     # float: Tax amount
            "discount_amount": 0                 # float: Discount amount
        },
        "total_qty_ordered": 5,                   # int: Total items quantity
        "shipping_address": {                     # dict or null
            "street": "101 S San Mateo Dr",
            "city": "San Mateo", 
            "region": "California",
            "postcode": "94010",
            "country": "US"
        }
    }
]
```

**⚠️ CRITICAL:** To access total amount, use `order['totals']['grand_total']`  
**❌ NOT:** `order['grand_total']` (doesn't exist at root level)

### `get_order_details()`

**Returns:** Single order dictionary with additional details
```python
{
    "order_id": 170,                           # int: Internal order ID
    "order_number": "000000170",              # str: Public order number
    "state": "complete",                      # str: Order state
    "status": "complete",                     # str: Order status
    "customer": {
        "id": 23,                            # int: Customer ID
        "email": "emma.lopez@gmail.com",     # str: Customer email
        "firstname": "Emma",                 # str: Customer first name
        "lastname": "Lopez"                  # str: Customer last name
    },
    "dates": {
        "created_at": "2023-02-27 13:15:14", # str: Order creation
        "updated_at": "2023-04-23 16:52:38"  # str: Last update
    },
    "totals": {
        "grand_total": 762.18,              # float: TOTAL ORDER AMOUNT
        "subtotal": 742.18,                 # float: Subtotal before shipping/tax
        "shipping_amount": 20.0,            # float: Shipping cost  
        "tax_amount": 0,                    # float: Tax amount
        "discount_amount": 0                # float: Discount amount
    },
    "items": [                              # List of order items
        {
            "item_id": 456,                 # int: Order item ID
            "product_id": 789,              # int: Product ID
            "name": "Product Name",         # str: Product name
            "sku": "PROD123",               # str: Product SKU
            "qty": 2,                       # int: Quantity ordered
            "price": 25.99                  # float: Unit price
        }
    ],
    "shipping_address": {                   # dict: Shipping address
        "street": "101 S San Mateo Dr",
        "city": "San Mateo",
        "region": "California", 
        "postcode": "94010",
        "country": "US"
    },
    "billing_address": {                    # dict: Billing address
        "street": "101 S San Mateo Dr",
        "city": "San Mateo",
        "region": "California",
        "postcode": "94010", 
        "country": "US"
    }
}
```

## 📦 Product Server (`magento-product-server`)

### `search_products()`

**Returns:** List of product dictionaries
```python
[
    {
        "entity_id": 123,                     # int: Product ID
        "sku": "B006H52HBC",                  # str: Product SKU
        "name": "Sennheiser HD 202 II Professional Headphones", # str: Product name
        "price": 29.95,                      # float: Product price
        "description": "Professional closed back headphones...", # str: Description
        "short_description": "Professional headphones",          # str: Short description
        "weight": "1.2000",                  # str: Product weight
        "status": 1,                         # int: Product status (1=enabled)
        "visibility": 4,                     # int: Visibility setting
        "type_id": "simple",                 # str: Product type
        "attribute_set_id": 4,               # int: Attribute set
        "category_ids": [15, 16],            # list: Associated category IDs
        "website_ids": [1],                  # list: Website IDs
        "stock_status": 1,                   # int: Stock status (1=in stock)
        "qty": 100                           # int: Available quantity
    }
]
```

### `get_product_details()`

**Returns:** Single product dictionary with detailed information
```python
{
    "entity_id": 789,                        # int: Product entity ID
    "sku": "B075FLPZ5Q",                     # str: Product SKU
    "name": "Teva Women's Haley Slip-On Shoe", # str: Product name
    "price": 70.00,                         # float: Product price
    "description": "The Haley slip-on shoe...", # str: Full description
    "short_description": "Comfortable slip-on", # str: Short description
    "weight": "1.5000",                     # str: Product weight
    "status": 1,                            # int: Product status (1=enabled)
    "visibility": 4,                        # int: Visibility setting
    "type_id": "configurable",              # str: Product type (simple/configurable)
    "stock_info": {
        "is_in_stock": true,                # bool: Stock availability
        "qty": 50,                          # int: Available quantity
        "manage_stock": true,               # bool: Stock management enabled
        "backorders": 0,                    # int: Backorder setting
        "min_sale_qty": 1,                  # int: Minimum sale quantity
        "max_sale_qty": null                # int|null: Maximum sale quantity
    },
    "categories": [                         # list: Category information
        {
            "category_id": 25,              # int: Category ID
            "name": "Women",                # str: Category name
            "path": "Default Category/Women" # str: Full category path
        }
    ],
    "configurable_options": [               # list: Configuration options (if configurable)
        {
            "attribute_id": 93,             # int: Attribute ID
            "label": "Color",               # str: Option label
            "values": [                     # list: Available values
                {"value_index": 49, "label": "Black"},
                {"value_index": 50, "label": "Brown"}
            ]
        },
        {
            "attribute_id": 142,
            "label": "Size",
            "values": [
                {"value_index": 167, "label": "6"},
                {"value_index": 168, "label": "7"}
            ]
        }
    ],
    "images": [                             # list: Product images
        {
            "file": "/t/e/teva_haley_black.jpg", # str: Image file path
            "position": 1,                  # int: Image position
            "label": "Teva Haley Black",    # str: Image label
            "disabled": false               # bool: Image disabled status
        }
    ],
    "related_products": [],                 # list: Related product IDs
    "upsell_products": [],                  # list: Upsell product IDs
    "cross_sell_products": []               # list: Cross-sell product IDs
}
```

### `list_categories()`

**Returns:** List of category dictionaries
```python
[
    {
        "entity_id": 15,                    # int: Category ID
        "name": "Electronics",              # str: Category name
        "path": "Default Category/Electronics", # str: Full category path
        "level": 2,                         # int: Category level in hierarchy
        "parent_id": 2,                     # int: Parent category ID
        "is_active": true,                  # bool: Category active status
        "position": 1,                      # int: Sort position
        "children_count": 5                 # int: Number of subcategories
    }
]
```

## 🛒 Checkout Server (`magento-checkout-server`) - Continued

### `get_cart()`

**Returns:** Cart information with this structure:
```python
{
    "quote_id": 123,                        # int: Shopping cart ID
    "created_at": "2023-06-15 10:30:00",   # str: Cart creation timestamp
    "updated_at": "2023-06-15 14:45:00",   # str: Last modification timestamp
    "items": [                              # list: Cart items
        {
            "item_id": 456,                 # int: Cart item ID (use for updates/removals)
            "product_id": 789,              # int: Product entity ID
            "sku": "B006H52HBC",            # str: Product SKU
            "name": "Headphones",           # str: Product name
            "qty": 2,                       # float: Quantity in cart
            "price": 29.95,                 # float: Unit price
            "row_total": 59.90              # float: Total for this item (qty × price)
        }
    ],
    "totals": {
        "items_count": 2,                   # int: Number of different items in cart
        "items_qty": 5,                     # float: Total quantity of all items
        "grand_total": 149.75               # float: TOTAL CART VALUE
    }
}
```

**Empty cart response:**
```python
{
    "quote_id": null,
    "items": [],
    "totals": {
        "items_count": 0,
        "items_qty": 0,
        "grand_total": 0
    }
}
```

### `add_to_cart()`

**Returns:** Cart addition result
```python
{
    "success": true,                        # bool: Addition operation success
    "item_id": 456,                         # int: New cart item ID
    "product": {
        "id": 789,                          # int: Product entity ID
        "sku": "B006H52HBC",                # str: Product SKU
        "name": "Headphones",               # str: Product name
        "price": 29.95                      # float: Unit price
    },
    "qty": 2,                               # float: Quantity added
    "cart_totals": {
        "items_count": 3,                   # int: Number of different items in cart
        "items_qty": 8,                     # float: Total quantity of all items
        "grand_total": 239.70               # float: TOTAL CART VALUE after addition
    }
}
```

### `update_cart_item()`

**Returns:** Cart update result
```python
{
    "success": true,                        # bool: Update operation success
    "item_id": 456,                         # int: Cart item ID that was updated
    "product": {
        "id": 789,                          # int: Product entity ID
        "sku": "B006H52HBC",                # str: Product SKU
        "name": "Headphones"                # str: Product name
    },
    "qty": 5,                               # float: New quantity
    "cart_totals": {
        "items_count": 2,                   # int: Number of different items in cart
        "items_qty": 8,                     # float: Total quantity of all items
        "grand_total": 179.75               # float: TOTAL CART VALUE after update
    }
}
```

### `remove_from_cart()`

**Returns:** Cart removal result
```python
{
    "success": true,                        # bool: Removal operation success
    "removed_item": {
        "item_id": 456,                     # int: Cart item ID that was removed
        "sku": "B006H52HBC",                # str: Product SKU that was removed
        "name": "Headphones"                # str: Product name that was removed
    },
    "cart_totals": {
        "items_count": 1,                   # int: Number of different items remaining
        "items_qty": 3,                     # float: Total quantity remaining
        "grand_total": 89.85                # float: TOTAL CART VALUE after removal
    }
}
```

## ⭐ Review Server (`magento-review-server`)

### `get_product_reviews()`

**Returns:** List of review dictionaries
```python
[
    {
        "review_id": 456,                    # int: Review ID
        "product_id": 789,                   # int: Product entity ID
        "product_sku": "B006H52HBC",         # str: Product SKU
        "title": "Great product!",          # str: Review title
        "detail": "I really love this product. It works great...", # str: Review text
        "nickname": "John D.",              # str: Reviewer nickname
        "rating": 4.0,                      # float|null: Rating value (1-5) or null
        "created_at": "2023-01-15 10:30:00" # str: Review creation date
    }
]
```

### `create_review()`

**Returns:** Created review information
```python
{
    "review_id": 310123,                    # int: Unique review ID
    "product_id": 789,                      # int: Product entity ID
    "title": "Great product",               # str: Review title
    "detail": "I really enjoyed this item", # str: Review detail text
    "nickname": "JohnDoe",                  # str: Reviewer nickname
    "rating": 5,                            # int|null: Rating value (1-5) or null
    "status": "created"                     # str: Creation status
}
```

## 👤 Account Server (`magento-account-server`)

### `get_account_info()`

**Returns:** Customer account information
```python
{
    "customer_id": 123,                     # int: Customer entity ID
    "email": "emma.lopez@gmail.com",        # str: Customer email address
    "firstname": "Emma",                    # str: Customer first name
    "lastname": "Lopez",                    # str: Customer last name
    "created_at": "2023-01-15T10:30:00",    # str: Account creation timestamp
    "is_active": true,                      # bool: Account status
    "default_billing_id": 456,              # int|null: Default billing address ID
    "default_shipping_id": 456,             # int|null: Default shipping address ID
    "addresses": [                          # list: Customer addresses
        {
            "address_id": 456,              # int: Address entity ID
            "firstname": "Emma",            # str: Address first name
            "lastname": "Lopez",            # str: Address last name
            "street": "123 Main St",        # str: Street address
            "city": "San Francisco",        # str: City
            "region": "California",         # str: State/region
            "postcode": "94105",            # str: ZIP/postal code
            "country_id": "US",             # str: Country code
            "telephone": "555-0123",        # str: Phone number
            "is_default_billing": true,     # bool: Is default billing address
            "is_default_shipping": true,    # bool: Is default shipping address
            "company": "ABC Corp",          # str|optional: Company name
            "prefix": "Ms.",                # str|optional: Name prefix
            "middlename": "Marie",          # str|optional: Middle name
            "suffix": "Jr.",                # str|optional: Name suffix
            "fax": "555-0124"               # str|optional: Fax number
        }
    ],
    "prefix": "Ms.",                        # str|optional: Customer name prefix
    "middlename": "Marie",                  # str|optional: Customer middle name
    "suffix": "Jr.",                        # str|optional: Customer name suffix
    "date_of_birth": "1990-05-15",         # str|optional: Date of birth
    "gender": "Female"                      # str|optional: "Male", "Female", "Other", "Not Specified"
}
```

### `update_account_info()`

**Returns:** Account update result
```python
{
    "success": true,                        # bool: Update operation success
    "customer_id": 123,                     # int: Customer entity ID
    "updated_fields": [                     # list: Fields that were changed
        "firstname",
        "lastname"
    ],
    "customer_info": {                      # dict: Complete updated customer info
        "customer_id": 123,                 # Same structure as get_account_info()
        "email": "emma.lopez@gmail.com",
        "firstname": "Emma",
        "lastname": "Lopez-Smith",
        "addresses": [...],
        ...
    }
}
```

## 💝 Wishlist Server (`magento-wishlist-server`)

### `get_wishlist()`

**Returns:** Wishlist information
```python
{
    "wishlist_id": 123,                     # int: Wishlist entity ID
    "updated_at": "2023-06-15 14:30:00",    # str: Last modification timestamp
    "item_count": 3,                        # int: Total number of items in wishlist
    "items": [                              # list: Wishlist items
        {
            "wishlist_item_id": 456,        # int: Unique wishlist item ID
            "product_id": 789,              # int: Product entity ID
            "sku": "B006H52HBC",            # str: Product SKU
            "name": "Headphones",           # str: Product name
            "price": 29.95,                 # float|null: Product price
            "qty": 2,                       # float: Desired quantity
            "is_in_stock": true,            # bool: Stock availability
            "added_at": "2023-06-10 10:15:00", # str: When added to wishlist
            "description": "Birthday gift"  # str: Optional user note/description
        }
    ]
}
```

**Empty wishlist response:**
```python
{
    "wishlist_id": 124,
    "items": [],
    "item_count": 0
}
```

### `add_to_wishlist()`

**Returns:** Wishlist addition result
```python
{
    "success": true,                        # bool: Addition operation success
    "wishlist_id": 123,                     # int: Wishlist entity ID
    "wishlist_item_id": 456,                # int: New wishlist item ID
    "product": {
        "id": 789,                          # int: Product entity ID
        "sku": "B006H52HBC",                # str: Product SKU
        "name": "Headphones",               # str: Product name
        "price": 29.95                      # float|null: Product price
    },
    "qty": 2,                               # float: Quantity added
    "description": "Birthday gift idea"     # str: User description/note
}
```

### `remove_from_wishlist()`

**Returns:** Wishlist removal result
```python
{
    "success": true,                        # bool: Removal operation success
    "removed_item_id": 456,                 # int: Wishlist item ID that was removed
    "removed_product": {
        "sku": "B006H52HBC",                # str: Product SKU that was removed
        "name": "Headphones"                # str: Product name that was removed
    },
    "remaining_items": 2                    # int: Number of items left in wishlist
}
```

## 🔧 Common Issues & Best Practices

### Order Total Calculation
```python
# ✅ CORRECT
total_spent = sum(order['totals']['grand_total'] for order in orders)

# ❌ WRONG - Will return 0
total_spent = sum(order.get('grand_total', 0) for order in orders)
```

### Product Search
```python
# Use search_products() for finding products
products = search_products(name="headphones", min_price="20")

# Use get_product_details() for detailed info about specific products
details = get_product_details(products[0]['entity_id'])
```

### Review Analysis
```python
# Get all reviews first, then filter in code
reviews = get_product_reviews("B006H52HBC")
positive_reviews = [r for r in reviews if r['rating'] > 60]
```

---

## 📊 Summary

**All 16 MCP tools are now fully documented with comprehensive response schemas:**

### 🛒 Checkout Server (6 tools)
- ✅ `list_orders()` - Order history with nested totals structure
- ✅ `get_order_details()` - Detailed order information with items
- ✅ `get_cart()` - Cart contents with item details
- ✅ `add_to_cart()` - Cart addition results
- ✅ `update_cart_item()` - Cart item quantity updates
- ✅ `remove_from_cart()` - Cart item removal

### 📦 Product Server (3 tools)
- ✅ `search_products()` - Product search results
- ✅ `get_product_details()` - Detailed product information with options
- ✅ `list_categories()` - Product category hierarchy

### ⭐ Review Server (2 tools)
- ✅ `get_product_reviews()` - Product review listings
- ✅ `create_review()` - Review submission results

### 👤 Account Server (2 tools)
- ✅ `get_account_info()` - Customer profile with addresses
- ✅ `update_account_info()` - Account update results

### 💝 Wishlist Server (3 tools)
- ✅ `get_wishlist()` - Wishlist items and metadata
- ✅ `add_to_wishlist()` - Wishlist addition results
- ✅ `remove_from_wishlist()` - Wishlist removal results

**Key Improvements:**
- **Critical data structure paths documented** (e.g., `order['totals']['grand_total']`)
- **Inline type annotations** with comments showing data types
- **Error response formats** for all failure scenarios
- **Field usage notes** for complex operations
- **Cross-references** between related tools

This prevents data structure bugs like the one that caused task failures where agents accessed `order['grand_total']` instead of the correct nested path `order['totals']['grand_total']`.

---

**Last Updated:** 2026-02-04  
**Note:** This documentation is embedded in the MCP tool descriptions that agents receive automatically.