from browsergym.core.action.functions import *

import playwright.sync_api
page: playwright.sync_api.Page = None


# Skills will be induced here by ASI


def asi_search_reviews_by_keyword(product_id: str, keywords: list):
    """Search product reviews for mentions of specific keywords.
    
    Fetches all reviews for a product and filters them based on whether
    the review title or detail contains all specified keywords (case-insensitive).
    
    Args:
        product_id: The product ID to fetch reviews for
        keywords: List of keywords to search for in reviews (all must be present)
        
    Returns:
        List of review dictionaries containing nickname, title, detail, and rating
        of reviews that mention all keywords
        
    Examples:
        asi_search_reviews_by_keyword("B001D0G57S", ["under", "water", "photo"])
    """
    reviews = magento_review_server_get_product_reviews(product_id)
    
    matching_reviews = []
    for review in reviews:
        review_text = (review.get('title', '') + ' ' + review.get('detail', '')).lower()
        if all(keyword.lower() in review_text for keyword in keywords):
            matching_reviews.append({
                'nickname': review.get('nickname'),
                'title': review.get('title'),
                'detail': review.get('detail'),
                'rating': review.get('rating')
            })
    
    return matching_reviews


def asi_format_and_send_reviewer_results(reviewers: list, search_term: str):
    """Format reviewer search results and send to user.
    
    Takes a list of matching reviewers and formats them into a readable message,
    then sends to the user. Handles the case when no reviewers are found.
    
    Args:
        reviewers: List of reviewer dictionaries with nickname, title, detail, rating
        search_term: The original search term/description to reference in the message
        
    Returns:
        None (sends message to user)
        
    Examples:
        asi_format_and_send_reviewer_results(
            [{'nickname': 'John', 'title': 'Great for underwater', ...}],
            "underwater photo"
        )
    """
    if reviewers:
        result = f"Reviewers who mention {search_term}:\n\n"
        for reviewer in reviewers:
            result += f"Reviewer: {reviewer['nickname']}\n"
            result += f"Title: {reviewer['title']}\n"
            result += f"Rating: {reviewer['rating']}\n"
            result += f"Review: {reviewer['detail']}\n\n"
        send_msg_to_user(result)
    else:
        send_msg_to_user(f"No reviewers found who mention {search_term}.")


def asi_navigate_to_pagination_page(page_link_id: str):
    """Navigate to a specific page in paginated results.
    
    Clicks on a pagination link to navigate to the next set of items.
    
    Args:
        page_link_id: The element ID of the pagination link to click
        
    Returns:
        None (navigates to new page)
        
    Examples:
        asi_navigate_to_pagination_page("1816")
    """
    click(page_link_id)


def asi_view_specific_order(order_view_link_id: str):
    """Click on a specific order's view link to see order details.
    
    Navigates to the detailed view of an order.
    
    Args:
        order_view_link_id: The element ID of the "View Order" link
        
    Returns:
        None (navigates to order details page)
        
    Examples:
        asi_view_specific_order("1701")
    """
    click(order_view_link_id)

def asi_get_fulfilled_orders_by_period(start_date: str, end_date: str):
    """Retrieve fulfilled orders within a specified date range and calculate statistics.
    
    Args:
        start_date: Start date in format 'YYYY-MM-DD'
        end_date: End date in format 'YYYY-MM-DD'
        
    Returns:
        Dictionary containing:
            - 'count': Number of fulfilled orders
            - 'total_spent': Total amount spent (float)
            - 'orders': List of order objects
        
    Examples:
        asi_get_fulfilled_orders_by_period('2023-05-12', '2023-06-12')
    """
    orders = magento_checkout_server_list_orders(
        status="complete",
        start_date=start_date,
        end_date=end_date
    )
    
    fulfilled_count = len(orders)
    total_spent = sum(float(order.get('grand_total', 0)) for order in orders)
    
    return {
        'count': fulfilled_count,
        'total_spent': total_spent,
        'orders': orders
    }


def asi_send_order_summary(fulfilled_count: int, total_spent: float, period_description: str):
    """Format and send order summary information to the user.
    
    Args:
        fulfilled_count: Number of fulfilled orders
        total_spent: Total amount spent (float)
        period_description: Description of the period (e.g., "over the past month")
        
    Examples:
        asi_send_order_summary(5, 250.75, "over the past month")
    """
    result_message = f"Fulfilled Orders {period_description}: {fulfilled_count}\n"
    result_message += f"Total Amount Spent: ${total_spent:.2f}"
    
    send_msg_to_user(result_message)

def asi_get_brand_price_range(brand_name: str):
    """Search for products from a specific brand and retrieve their price range.
    
    Args:
        brand_name: The brand name to search for products
        
    Returns:
        A tuple of (min_price, max_price) as floats, or None if no products found
        
    Examples:
        asi_get_brand_price_range("EYZUTAK")
    """
    products = magento_product_server_search_products(name=brand_name)
    
    if products:
        prices = [float(p['price']) for p in products]
        min_price = min(prices)
        max_price = max(prices)
        return (min_price, max_price)
    else:
        return None

def asi_navigate_to_order_by_number(order_number: str, max_pages: int = 5):
    """Navigate through order history pages to find and view a specific order.
    
    Searches through pagination to locate an order by its number and opens
    the order details page.
    
    Args:
        order_number: The order number to find (e.g., "00178")
        max_pages: Maximum number of pages to search through (default: 5)
        
    Returns:
        None (navigates to order details page and sends results to user)
        
    Examples:
        asi_navigate_to_order_by_number("00178", max_pages=5)
    """
    page_num = 1
    found = False
    
    while page_num <= max_pages and not found:
        # Try to find order on current page
        order_element = page.get_by_text(order_number)
        if order_element:
            view_link = order_element.locator("xpath=following::a[contains(text(), 'View Order')]").first
            if view_link:
                view_link.click()
                found = True
                break
        
        # If not found, go to next page
        if not found and page_num < max_pages:
            next_page_link = page.locator(f"a:has-text('Page {page_num + 1}')")
            if next_page_link.count() > 0:
                next_page_link.click()
                page_num += 1
            else:
                break
    
    if not found:
        send_msg_to_user(f"Order #{order_number} not found in the first {max_pages} pages.")

def asi_get_recent_order_by_status(status: str):
    """Retrieve the most recent order number for a given order status using MCP tools.
    
    Args:
        status: The order status to filter by (e.g., "on-hold", "pending", "processing")
        
    Returns:
        The order number (increment_id) of the most recent order with the given status,
        or None if no orders found
        
    Examples:
        order_num = asi_get_recent_order_by_status("on-hold")
        # Returns: "00178"
    """
    orders = magento_checkout_server_list_orders(status=status)
    if orders:
        most_recent = orders[0]  # Assumes API returns ordered by date (most recent first)
        return most_recent.get('increment_id')
    return None


def asi_send_recent_order_info(status: str):
    """Retrieve and send the most recent order number for a given status to the user.
    
    Args:
        status: The order status to filter by (e.g., "on-hold", "pending", "processing")
        
    Examples:
        asi_send_recent_order_info("on-hold")
        # Sends message about most recent on-hold order
    """
    order_number = asi_get_recent_order_by_status(status)
    if order_number:
        send_msg_to_user(f"Your most recent {status} order number is: {order_number}")
    else:
        send_msg_to_user(f"No {status} orders found.")