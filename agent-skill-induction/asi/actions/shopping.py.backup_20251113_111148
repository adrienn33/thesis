from browsergym.core.action.functions import *

import playwright.sync_api
page: playwright.sync_api.Page = None


# Skills will be induced here by ASI



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

def navigate_to_order_history(account_link_id: str, view_all_link_id: str):
    """Navigate to the full order history page from the main account page.
    
    Args:
        account_link_id: The ID of the "My Account" link
        view_all_link_id: The ID of the "View All" link for orders
    
    Returns:
        None
    
    Examples:
        navigate_to_order_history('227', '1416')
    """
    click(account_link_id)  # Click on "My Account" link
    click(view_all_link_id)  # Click on "View All" link to see all orders

def set_items_per_page(dropdown_id: str, items_count: str):
    """Set the number of items to display per page in a listing.
    
    Args:
        dropdown_id: The ID of the dropdown selector
        items_count: The number of items to show per page (e.g., '20', '50', '100')
    
    Returns:
        None
    
    Examples:
        set_items_per_page('1509', '50')
    """
    select_option(dropdown_id, items_count)  # Select number of items to show per page