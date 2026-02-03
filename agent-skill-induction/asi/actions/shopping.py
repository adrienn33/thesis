from browsergym.core.action.functions import *

import playwright.sync_api
page: playwright.sync_api.Page = None


# Skills will be induced here by ASI


def asi_navigate_through_paginated_content(page_link_ids: list):
    """Navigate through multiple pages of paginated content by clicking page links sequentially.
    
    Args:
        page_link_ids: List of element IDs representing page navigation links in order
        
    Returns:
        None
        
    Examples:
        asi_navigate_through_paginated_content(['1816', '1824'])
    """
    for page_id in page_link_ids:
        click(page_id)


def asi_search_and_extract_from_reviews(search_term: str, tab_id: str, scroll_distance: int = 300):
    """Click reviews tab, scroll through review content, and prepare to extract mentions of a search term.
    
    Args:
        search_term: The keyword or phrase to search for in reviews
        tab_id: The ID of the Reviews tab element
        scroll_distance: Distance in pixels to scroll (default 300)
        
    Returns:
        None
        
    Examples:
        asi_search_and_extract_from_reviews('fingerprint resistant', '1681')
    """
    click(tab_id)
    scroll(0, scroll_distance)


def asi_collect_and_report_reviewers(reviewers_data: list, search_term: str):
    """Format reviewer information and send to user with mentions of specific term.
    
    Args:
        reviewers_data: List of tuples containing (reviewer_name, review_quote)
        search_term: The search term that reviewers mentioned
        
    Returns:
        None
        
    Examples:
        asi_collect_and_report_reviewers([('Rachel', 'It is super clear and fingerprint resistant.'), ('T. Gannon', 'Seems much better than the one replaced...')], 'fingerprint resistant')
    """
    message = f"Reviewers who mention {search_term}:\n\n"
    for idx, (reviewer_name, quote) in enumerate(reviewers_data, 1):
        message += f"{idx}. {reviewer_name} - '{quote}'\n"
    send_msg_to_user(message)