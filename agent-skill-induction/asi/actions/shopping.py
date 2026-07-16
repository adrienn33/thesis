from browsergym.core.action.functions import *

import playwright.sync_api
page: playwright.sync_api.Page = None


# Skills will be induced here by ASI


def asi_find_reviewers_by_topic(product_id: str, keywords: list):
    """Find reviewers who mention specific topics in their product reviews.
    
    Retrieves all reviews for a product, searches through review titles and
    details for any of the provided keywords, and returns a list of reviewer
    nicknames who mentioned those topics.
    
    Args:
        product_id: The product ID or SKU to fetch reviews for.
        keywords: A list of keyword strings to search for in review content.
        
    Returns:
        A list of reviewer nicknames who mentioned the specified topics.
        
    Examples:
        asi_find_reviewers_by_topic("B00JXLGF06", ["customer service", "support", "complaint"])
        asi_find_reviewers_by_topic("ABC123", ["battery", "battery life", "charge"])
    """
    reviews = magento_review_server_get_product_reviews(product_id)
    matched_reviewers = []
    for review in reviews:
        combined = review['detail'].lower() + " " + review['title'].lower()
        if any(kw.lower() in combined for kw in keywords):
            matched_reviewers.append(review['nickname'])
    return matched_reviewers

def asi_get_fulfilled_orders_summary(customer_email: str, start_date: str, end_date: str):
    """Retrieve fulfilled (complete) orders for a customer within a date range and summarize count and total spending.
    
    Args:
        customer_email: The email address of the customer whose orders to look up.
        start_date: The start date of the period in 'YYYY-MM-DD' format (inclusive).
        end_date: The end date of the period in 'YYYY-MM-DD' format (inclusive).
        
    Returns:
        A tuple of (count, total) where count is the number of fulfilled orders
        and total is the sum of grand totals across those orders.
        
    Examples:
        asi_get_fulfilled_orders_summary("emma.lopez@gmail.com", "2023-06-10", "2023-06-12")
    """
    orders = magento_checkout_server_list_orders(
        customer_email=customer_email,
        status="complete",
        start_date=start_date,
        end_date=end_date
    )
    count = len(orders)
    total = sum(o['totals']['grand_total'] for o in orders)
    return count, total

def asi_get_latest_order_details(customer_email: str):
    """Retrieve the most recent order and its full details for a given customer.

    Fetches all orders for the customer, identifies the latest one by creation
    date, and returns the detailed order information.

    Args:
        customer_email: The email address of the customer whose latest order
                        should be retrieved.

    Returns:
        A dict containing full order details for the most recent order,
        as returned by magento_checkout_server_get_order_details.

    Examples:
        details = asi_get_latest_order_details("emma.lopez@gmail.com")
        print(details['order_number'], details['status'])
    """
    orders = magento_checkout_server_list_orders(customer_email=customer_email, limit=100)
    latest_order = max(orders, key=lambda o: o['created_at'])
    details = magento_checkout_server_get_order_details(latest_order['order_id'])
    return details

def asi_get_first_purchase_date(customer_email: str):
    """Find the earliest purchase date for a customer by retrieving all orders and finding the minimum date.
    
    Args:
        customer_email: The email address of the customer to look up orders for.
        
    Returns:
        A dictionary with 'date' (YYYY-MM-DD string) and 'order_number' of the earliest order,
        or None if no orders are found.
        
    Examples:
        asi_get_first_purchase_date("emma.lopez@gmail.com")
    """
    orders = magento_checkout_server_list_orders(customer_email=customer_email, limit=100)
    if not orders:
        return None
    earliest_order = min(orders, key=lambda o: o['created_at'])
    return {
        'date': earliest_order['created_at'][:10],
        'order_number': earliest_order['order_number']
    }

def asi_get_category_spending(customer_email: str, start_date: str, end_date: str, category_keywords: list):
    """Calculate total spending on items matching category keywords within a date range,
    considering only completed orders.
    
    Args:
        customer_email: The email address of the customer
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        category_keywords: List of keywords to match against item names for category filtering
        
    Returns:
        A tuple of (total_spent, matched_items) where total_spent is a float and
        matched_items is a list of dicts with item name, qty, and price
        
    Examples:
        asi_get_category_spending("emma.lopez@gmail.com", "2022-03-01", "2022-03-31", ["food", "cook", "kitchen"])
    """
    orders = magento_checkout_server_list_orders(
        customer_email=customer_email,
        start_date=start_date,
        end_date=end_date
    )
    
    total_spent = 0.0
    matched_items = []
    
    for order in orders:
        if order['status'] != 'complete':
            continue
        details = magento_checkout_server_get_order_details(order['order_id'])
        for item in details['items']:
            item_name_lower = item['name'].lower()
            if any(kw.lower() in item_name_lower for kw in category_keywords):
                total_spent += item['price'] * item['qty']
                matched_items.append({
                    'name': item['name'],
                    'qty': item['qty'],
                    'price': item['price']
                })
    
    return total_spent, matched_items

def asi_find_game_card_storage(num_cards: int):
    """Find the best Nintendo Switch game card storage option that can fit a specified number of cards.
    
    Searches for storage products, finds the smallest capacity that fits all cards,
    navigates to the product page, and sends the recommendation to the user.
    
    Args:
        num_cards: The number of Nintendo Switch game cards that need to be stored.
        
    Returns:
        None. Navigates to the best matching product page and sends a message to the user.
        
    Examples:
        asi_find_game_card_storage(23)
    """
    products = magento_product_server_search_products(description="Nintendo Switch game card case storage")
    
    # Filter products that can hold at least num_cards
    suitable = []
    for p in products:
        details = magento_product_server_get_product_details(p['entity_id'])
        desc = (details.get('description', '') + details.get('name', '')).lower()
        # Look for slot count mentions in the description/name
        import re
        slot_matches = re.findall(r'(\d+)\s*game\s*card\s*slot', desc)
        if slot_matches:
            max_slots = max(int(s) for s in slot_matches)
            if max_slots >= num_cards:
                suitable.append((max_slots, p['price'], details))
    
    if suitable:
        # Pick the product with smallest sufficient capacity (best fit)
        suitable.sort(key=lambda x: (x[0], x[1]))
        best = suitable[0][2]
        goto(best['url'])
        send_msg_to_user(f"The best storage option for {num_cards} Nintendo Switch game cards is: {best['name']} (Price: ${best['price']}). It has enough slots to fit all your cards.")
    else:
        send_msg_to_user(f"No suitable storage product found for {num_cards} Nintendo Switch game cards.")

def asi_get_most_expensive_in_category(category_keyword: str):
    """Find and navigate to the most expensive product in a given category.
    
    Searches all categories for one matching the keyword, then finds the 
    most expensive product in that category and navigates to its page.
    
    Args:
        category_keyword: A keyword string to match against category names (case-insensitive)
        
    Returns:
        Navigates to the most expensive product's page and sends a message with the result.
        
    Examples:
        asi_get_most_expensive_in_category('nutrition')
        asi_get_most_expensive_in_category('drink')
    """
    categories = magento_product_server_list_categories()
    matched_cats = [c for c in categories if category_keyword.lower() in c['name'].lower()]
    category_id = matched_cats[0]['category_id']
    products = magento_product_server_search_products(category=category_id)
    most_expensive = max(products, key=lambda p: float(p['price']))
    goto(most_expensive['url'])
    send_msg_to_user(f"The most expensive product in the category is: {most_expensive['name']} at ${most_expensive['price']}")

def asi_navigate_to_category(category_keywords: list):
    """Find and navigate to a product category page by searching category names with keywords.
    
    Args:
        category_keywords: List of keywords to filter category names (all keywords must match)
        
    Returns:
        Navigates the browser to the matched category page URL.
        
    Examples:
        asi_navigate_to_category(['men', 'shoe'])
        asi_navigate_to_category(['women', 'jacket'])
    """
    categories = magento_product_server_list_categories()
    matched = [c for c in categories if all(kw.lower() in c['name'].lower() for kw in category_keywords)]
    if matched:
        category = matched[0]
        goto(category['url'])
    else:
        send_msg_to_user(f"No category found matching keywords: {category_keywords}")

def asi_filter_products_by_max_price(category_url_path: str, max_price: float):
    """Navigate to a product category page filtered by a maximum price.
    
    Constructs and navigates to a URL that filters products in a given category
    by a maximum price using Magento's price range URL pattern.
    
    Args:
        category_url_path: The relative URL path of the category (e.g., "beauty-personal-care/makeup/makeup-remover")
        max_price: The maximum price to filter products by (e.g., 46.99)
        
    Returns:
        None. Navigates the browser to the filtered category page.
        
    Examples:
        asi_filter_products_by_max_price("beauty-personal-care/makeup/makeup-remover", 46.99)
        asi_filter_products_by_max_price("electronics/accessories/headphones", 99.99)
    """
    url = f"http://localhost:7770/{category_url_path}.html?price=0-{max_price}"
    goto(url)

def asi_get_category_url_by_keywords(keywords: list):
    """Find a category URL path by matching keywords against category names.
    
    Args:
        keywords: List of keywords to match against category names (case-insensitive)
        
    Returns:
        The URL path of the first matching category, or None if not found
        
    Examples:
        url = asi_get_category_url_by_keywords(['accent', 'furniture'])
        # Returns something like '/home-kitchen/furniture/accent-furniture.html'
    """
    categories = magento_product_server_list_categories()
    for keyword in keywords:
        matched = [c for c in categories if keyword.lower() in c['name'].lower()]
        if matched:
            return matched[0]['url']
    return None

def asi_search_products(keyword: str):
    """Search for products using the site's search box.
    
    Args:
        keyword: The search term to look for (e.g., "usb wifi", "laptop", "hdmi cable")
        
    Returns:
        None. Navigates to the search results page for the given keyword.
        
    Examples:
        asi_search_products("usb wifi")
        asi_search_products("bluetooth speaker")
    """
    click("576")
    fill("576", keyword)
    keyboard_press("Enter")

def asi_get_latest_order_by_status(customer_email: str, status: str):
    """Find and navigate to the most recent order for a customer filtered by order status.
    
    Args:
        customer_email: The email address of the customer whose orders to search
        status: The order status to filter by (e.g., 'complete', 'pending', 'processing', 'canceled')
        
    Returns:
        Navigates to the order detail page of the most recent order with the given status
        and sends a message to the user with the order details.
        
    Examples:
        asi_get_latest_order_by_status("emma.lopez@gmail.com", "complete")
        asi_get_latest_order_by_status("john.doe@gmail.com", "pending")
    """
    orders = magento_checkout_server_list_orders(customer_email=customer_email, status=status, limit=100)
    latest = max(orders, key=lambda o: o['created_at'])
    order_id = latest['order_id']
    order_number = latest['order_number']
    goto(f"http://localhost:7770/sales/order/view/order_id/{order_id}/")
    send_msg_to_user(f"The most recent {status} order is #{order_number}, placed on {latest['created_at']}.")

def asi_get_cancelled_order_refund(customer_email: str, start_date: str, end_date: str):
    """Calculate the total expected refund for cancelled orders within a date range, including shipping fees.
    
    Args:
        customer_email: The email address of the customer
        start_date: The start date of the period to search (format: YYYY-MM-DD)
        end_date: The end date of the period to search (format: YYYY-MM-DD)
        
    Returns:
        The total refund amount as a float (sum of grand_total for all cancelled orders in the period)
        
    Examples:
        asi_get_cancelled_order_refund("emma.lopez@gmail.com", "2023-02-01", "2023-02-28")
    """
    orders = magento_checkout_server_list_orders(
        customer_email=customer_email,
        status="canceled",
        start_date=start_date,
        end_date=end_date
    )
    total_refund = sum(o['totals']['grand_total'] for o in orders)
    return total_refund

def asi_sort_search_results(sort_option: str):
    """Select a sorting option for the current search/listing results page.
    
    Args:
        sort_option: The sorting option value to select (e.g., 'relevance', 'price', 'name', etc.)
        
    Returns:
        None. The page will be sorted by the specified option.
        
    Examples:
        asi_sort_search_results('relevance')
        asi_sort_search_results('price')
        asi_sort_search_results('name')
    """
    select_option("sorter", sort_option)

def asi_navigate_and_sort_by_price(category_keywords: list, sort_order: str = "asc"):
    """Navigate to a product category and sort results by price.
    
    Uses MCP to find the category URL, navigates to it directly,
    then applies price sorting via the Sort By dropdown.
    
    Args:
        category_keywords: List of keywords to match against category names (case-insensitive)
        sort_order: Sort direction - "asc" for ascending (default) or "desc" for descending
        
    Returns:
        None. Navigates browser to the category page sorted by price.
        
    Examples:
        asi_navigate_and_sort_by_price(['nutrition', 'bar', 'drink'])
        asi_navigate_and_sort_by_price(['protein'], sort_order='desc')
    """
    categories = magento_product_server_list_categories()
    matched = [c for c in categories if any(kw in c['name'].lower() for kw in category_keywords)]
    if matched:
        goto(matched[0]['url'])
    # Sort by price using the Sort By dropdown
    sort_by_select = page.locator("select#sorter, select[id*='sorter']").first
    sort_by_select.select_option("price")
    # Handle sort direction if descending is needed
    if sort_order == "desc":
        # Check if current direction is ascending and click to toggle
        asc_link = page.locator("a.sort-asc, a[data-value='asc']")
        if asc_link.count() > 0:
            asc_link.click()

def asi_get_order_info_by_number(order_number: str):
    """Retrieve order details for a specific order number using MCP tool.
    
    Fetches full order details including dates, billing address, items, totals,
    and status for a given order number (zero-padded to 9 digits).
    
    Args:
        order_number: The order number as a string (e.g., "148", "00178").
                      Will be zero-padded to 9 digits automatically.
    
    Returns:
        A dictionary containing order details such as dates, billing address,
        items, totals, and status.
    
    Examples:
        order = asi_get_order_info_by_number("148")
        order = asi_get_order_info_by_number("00178")
    """
    padded = order_number.zfill(9)
    order = magento_checkout_server_get_order_details(padded)
    return order

def asi_add_to_wishlist():
    """Click the 'Add to Wish List' button on the current product page.
    
    Finds and clicks the 'Add to Wish List' link/button that is visible
    on the current product detail page to add the product to the user's wishlist.
    
    Args:
        None
        
    Returns:
        None. The product is added to the wishlist and the page may redirect
        to the wishlist page.
        
    Examples:
        asi_add_to_wishlist()
    """
    wishlist_link = page.get_by_text("Add to Wish List")
    wishlist_link.click()