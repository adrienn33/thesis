## README

# Proposed MCP Actions

## User Account Management

<!-- 1. **create_account** - Register a new user account with email, password, and basic profile information
2. **login** - Authenticate a user and establish a session
3. **logout** - End the current user session
4. **get_account_info** - Retrieve current user's profile details
5. **update_account_info** - Update user profile information (name, email, password) -->

## Product Browsing & Search

6. **search_products** - Search for products by SKU, product name, description, category, and/or price range. Flexible enough to handle category-based queries (returns all products in a category when only category is specified)
7. **get_product_details** - Get detailed information about a specific product including description, price, stock status (qty, is_in_stock), images, and available options (e.g., color, size for configurable products)
8. **list_categories** - Get all available product categories

## Shopping Cart

<!-- 9. **add_to_cart** - Add a product to the shopping cart with specified quantity and product options (e.g., color, size for configurable products)
10. **remove_from_cart** - Remove a specific item from the cart
11. **update_cart_item** - Update quantity of an item in the cart
12. **get_cart** - View current cart contents and totals -->

## Checkout & Orders
<!-- 
13. **add_shipping_address** - Add or update shipping address for checkout
14. **add_billing_address** - Add or update billing address for checkout
15. **set_shipping_method** - Select shipping method (standard, express, etc.)
16. **set_payment_method** - Select payment method
17. **place_order** - Complete the checkout process and place the order
18. **get_order_details** - Retrieve details of a specific order by order ID
19. **list_orders** - Get order history for the current user -->

## Wishlist

<!-- 20. **add_to_wishlist** - Add a product to the user's wishlist
21. **remove_from_wishlist** - Remove an item from the wishlist
22. **get_wishlist** - View all items in the user's wishlist -->

## Product Reviews

23. **get_product_reviews** - Retrieve all reviews for a specific product (308,940+ reviews exist in the system)
24. **create_review** - Submit a review for a product including title, detail text, and nickname. Does not require user authentication (customer_id can be NULL)



Idea: Build in no-op tools so the agent actually has to choose
