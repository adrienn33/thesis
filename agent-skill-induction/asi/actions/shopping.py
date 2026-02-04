from browsergym.core.action.functions import *

import playwright.sync_api
page: playwright.sync_api.Page = None


# Skills will be induced here by ASI


def asi_get_product_reviews_by_keyword(product_sku: str, keyword: str):
    """Retrieve and filter product reviews by keyword mention.
    
    Fetches all reviews for a product and filters them to find reviews 
    that mention the specified keyword in title or detail text.
    
    Args:
        product_sku: The SKU of the product to get reviews for
        keyword: The keyword to search for in reviews (case-insensitive)
        
    Returns:
        List of dictionaries containing filtered reviews with keys:
        'nickname', 'title', 'detail', 'rating'
        
    Examples:
        asi_get_product_reviews_by_keyword('B001D0G57S', 'underwater')
    """
    reviews = magento_review_server_get_product_reviews(product_sku)
    
    filtered_reviews = []
    keyword_lower = keyword.lower()
    
    for review in reviews:
        review_text = (review.get('title', '') + ' ' + review.get('detail', '')).lower()
        if keyword_lower in review_text:
            filtered_reviews.append({
                'nickname': review.get('nickname', 'Unknown'),
                'title': review.get('title', ''),
                'detail': review.get('detail', ''),
                'rating': review.get('rating', 'N/A')
            })
    
    return filtered_reviews


def asi_paginate_and_find_element(page_link_bid: str, target_bid: str, max_pages: int = 10):
    """Navigate through paginated results to find and click a target element.
    
    Clicks through sequential pages to locate a specific element by its bid.
    
    Args:
        page_link_bid: The bid of the pagination link to navigate pages
        target_bid: The bid of the target element to find and click
        max_pages: Maximum number of pages to check (default: 10)
        
    Returns:
        True if target element found and clicked, False otherwise
        
    Examples:
        asi_paginate_and_find_element('1816', '1701', max_pages=5)
    """
    for _ in range(max_pages):
        try:
            element = page.get_by_test_id(target_bid)
            if element:
                click(target_bid)
                return True
        except:
            pass
        
        click(page_link_bid)
    
    return False


def asi_format_and_send_review_list(reviews: list, keyword: str):
    """Format filtered reviews and send to user.
    
    Takes a list of filtered review dictionaries and formats them 
    into a readable message for the user.
    
    Args:
        reviews: List of review dictionaries with 'nickname', 'title', 
                'detail', and 'rating' keys
        keyword: The keyword that was searched for (for context in message)
        
    Returns:
        None (sends message to user)
        
    Examples:
        asi_format_and_send_review_list(filtered_reviews, 'underwater')
    """
    if reviews:
        result = f"Reviewers who mention {keyword}:\n\n"
        for reviewer in reviews:
            result += f"Reviewer: {reviewer['nickname']}\n"
            result += f"Title: {reviewer['title']}\n"
            result += f"Rating: {reviewer['rating']}\n"
            result += f"Review: {reviewer['detail']}\n"
            result += "-" * 50 + "\n"
        send_msg_to_user(result)
    else:
        send_msg_to_user(f"No reviewers found who mention {keyword}.")

def asi_find_and_view_order(start_page_link_bid: str, target_order_id: str, max_pages: int = 10):
    """Find a specific order by ID through paginated order list and navigate to its details.
    
    This function pages through an order history list, searches for a specific order ID,
    and clicks the "View Order" link to display order details.
    
    Args:
        start_page_link_bid: The element ID of the first pagination link to start from
        target_order_id: The order ID to find (e.g., "00178")
        max_pages: Maximum number of pages to search through (default: 10)
        
    Returns:
        None (navigates to the order details page)
        
    Examples:
        asi_find_and_view_order("1816", "00178", max_pages=5)
    """
    current_page_bid = start_page_link_bid
    pages_searched = 0
    
    while pages_searched < max_pages:
        # Check if target order is visible on current page
        order_elements = page.query_selector_all(f'text="{target_order_id}"')
        if order_elements:
            # Found the order, now find its View Order link (typically nearby)
            # Click the View Order button associated with this order
            view_order_link = page.locator(f'text="View Order"').first
            view_order_link.click()
            return
        
        # Navigate to next page
        pages_searched += 1
        next_page_bid = str(int(current_page_bid) + 8)  # Standard increment for pagination
        click(next_page_bid)
        current_page_bid = next_page_bid
    
    send_msg_to_user(f"Order #{target_order_id} not found after searching {max_pages} pages.")

def asi_get_fulfilled_orders_summary(status: str, start_date: str, end_date: str):
    """Retrieve fulfilled orders within a date range and calculate summary statistics.
    
    Args:
        status: Order status filter (e.g., "complete" for fulfilled orders)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        A tuple containing (order_count, total_amount_spent)
        
    Examples:
        count, total = asi_get_fulfilled_orders_summary("complete", "2023-05-12", "2023-06-12")
    """
    orders = magento_checkout_server_list_orders(
        status=status,
        start_date=start_date,
        end_date=end_date
    )
    
    fulfilled_count = len(orders)
    total_spent = sum(float(order['totals'].get('grand_total', 0)) for order in orders)
    
    return fulfilled_count, total_spent

def asi_get_price_range_by_criteria(search_name: str = None, search_sku: str = None, search_category: str = None):
    """Search for products by criteria and return their price range.
    
    Args:
        search_name: Product name to search for (optional)
        search_sku: Product SKU to search for (optional)
        search_category: Product category to search for (optional)
        
    Returns:
        Dictionary with 'min_price', 'max_price', and 'product_count', or None if no products found
        
    Examples:
        result = asi_get_price_range_by_criteria(search_name="EYZUTAK")
        result = asi_get_price_range_by_criteria(search_category="Electronics")
    """
    products = magento_product_server_search_products(
        name=search_name,
        sku=search_sku,
        category=search_category,
        limit=100
    )
    
    if products:
        prices = [float(p['price']) for p in products]
        return {
            'min_price': min(prices),
            'max_price': max(prices),
            'product_count': len(products)
        }
    return None

def asi_get_most_recent_order_by_status(status: str):
    """Retrieve the most recent order with a specific status.
    
    This function queries the order system to find the most recent order
    matching the given status and returns its order number.
    
    Args:
        status: The order status to filter by (e.g., "on hold", "processing", "completed")
        
    Returns:
        The order number (increment_id) of the most recent order with the specified status,
        or None if no orders match the criteria.
        
    Examples:
        order_num = asi_get_most_recent_order_by_status("on hold")
        # Returns order number like "00178"
    """
    orders = magento_checkout_server_list_orders(status=status)
    
    if orders:
        # Assuming API returns in reverse chronological order (most recent first)
        most_recent = orders[0]
        order_number = most_recent.get('increment_id')
        send_msg_to_user(f"The order number of your most recent {status} order is: {order_number}")
        return order_number
    else:
        send_msg_to_user(f"You do not have any {status} orders.")
        return None