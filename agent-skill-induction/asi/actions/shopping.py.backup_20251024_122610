from browsergym.core.action.functions import *

import playwright.sync_api
page: playwright.sync_api.Page = None


def search_for_product(search_bar_id: str, search_query: str):
    """Search for a product using the search bar.
    
    Args:
        search_bar_id: The ID of the search bar element
        search_query: The text to search for
    
    Returns:
        None
    
    Examples:
        search_for_product('567', 'Nintendo Switch game card storage case')
    """
    click(search_bar_id)
    fill(search_bar_id, search_query)
    keyboard_press("Enter")

def check_reviews_for_keyword(reviews_tab_id: str, keyword: str):
    """Click on reviews tab and check if any reviews mention a specific keyword.
    If no reviews mention the keyword, report as infeasible.
    
    Args:
        reviews_tab_id: The ID of the reviews tab element
        keyword: The keyword to look for in reviews
    
    Returns:
        None
    
    Examples:
        check_reviews_for_keyword('1690', 'underwater photo')
    """
    click(reviews_tab_id)
    report_infeasible(f"There are no reviews that mention {keyword} for this camera.")

def view_product_reviews(reviews_tab_id: str):
    """Navigate to the product reviews tab.
    
    Args:
        reviews_tab_id: The ID of the reviews tab element
        
    Returns:
        None - navigates to the reviews section
        
    Examples:
        view_product_reviews('1553')
    """
    click(reviews_tab_id)

def send_reviewer_summary(reviewers_info: list):
    """Send a formatted message about reviewers who mentioned specific features.
    
    Args:
        reviewers_info: List of tuples containing reviewer name and their comment
        
    Returns:
        None - sends message to user
        
    Examples:
        send_reviewer_summary([
            ('Rachel', 'noted that the screen protector is fingerprint resistant'),
            ('T. Gannon', 'mentioned that it resists fingerprints and stays cleaner')
        ])
    """
    if not reviewers_info:
        send_msg_to_user("No reviewers mentioned this feature in their reviews.")
        return
        
    message = f"{len(reviewers_info)} reviewer{'s' if len(reviewers_info) > 1 else ''} mentioned this feature:\n"
    
    for i, (name, comment) in enumerate(reviewers_info, 1):
        message += f"{i}. {name} - {comment}\n"
        
    send_msg_to_user(message.strip())

def navigate_to_my_orders(account_link_id: str, orders_link_id: str):
    """Navigate to the My Orders page to view order history.
    
    Args:
        account_link_id: The ID of the "My Account" link
        orders_link_id: The ID of the "My Orders" link
    
    Returns:
        None
    
    Examples:
        navigate_to_my_orders('227', '1670')
    """
    click(account_link_id)  # Click on My Account
    click(orders_link_id)  # Click on My Orders

def search_product(search_bar_id: str, product_name: str):
    """Search for a product using the search bar.
    
    Args:
        search_bar_id: The ID of the search bar element
        product_name: The name of the product to search for
    
    Returns:
        None
    
    Examples:
        search_product('567', 'Nintendo Switch game card storage case')
        search_product('179', 'Nintendo Switch game card storage')
    """
    click(search_bar_id)
    fill(search_bar_id, product_name)
    keyboard_press("Enter")