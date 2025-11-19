from browsergym.core.action.functions import *

import playwright.sync_api
page: playwright.sync_api.Page = None


# Skills will be induced here by ASI


def search_product(search_bar_id: str | int, product_name: str):
    """Search for a product in the search bar.
    
    Args:
        search_bar_id: The ID of the search bar element
        product_name: The name or keywords of the product to search for
        
    Returns:
        None
        
    Examples:
        search_product('567', 'Nintendo Switch game card storage case')
        search_product('179', 'Nintendo Switch game card storage')
    """
    click(search_bar_id)
    fill(search_bar_id, product_name)
    keyboard_press("Enter")


def navigate_to_order_history(account_id: str):
    """Navigate from homepage to order history page.
    
    Args:
        account_id: The ID of the "My Account" link
        
    Returns:
        None
        
    Examples:
        navigate_to_order_history('227')
    """
    click(account_id)
    click("1742")


def find_and_review_product_mentions(product_id: str, mention_keyword: str) -> dict:
    """Retrieve all reviews for a product and identify reviewers mentioning specific keywords.
    
    Args:
        product_id: The product ID or SKU to fetch reviews for
        mention_keyword: The keyword or phrase to search for in review content
        
    Returns:
        A dictionary containing the list of reviewers who mention the keyword and summary message
        
    Examples:
        find_and_review_product_mentions("B002C1B1YY", "price being unfair")
        find_and_review_product_mentions("SKU123", "battery life")
    """
    reviews = magento_review_server_get_product_reviews(product_id)
    matching_reviewers = []
    
    for review in reviews:
        if mention_keyword.lower() in review.get("content", "").lower():
            matching_reviewers.append(review.get("reviewer_name", "Unknown"))
    
    return {
        "matching_reviewers": matching_reviewers,
        "total_reviews": len(reviews),
        "product_id": product_id
    }

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