"""Implements helper functions to assist evaluation cases where other evaluators are not suitable."""
import json
from typing import Any
from urllib.parse import urlparse

import requests
from playwright.sync_api import CDPSession, Page

from browser_env.env_config import (
    ACCOUNTS,
    GITLAB,
    MAP,
    REDDIT,
    SHOPPING,
    SHOPPING_ADMIN,
    WIKIPEDIA,
)
from llms.providers.openai_utils import (
    generate_from_openai_chat_completion,
)

import anthropic as _anthropic

def _generate_from_claude(messages: list[dict], model: str = "claude-sonnet-4-6") -> str:
    """Call Claude via the Anthropic SDK, mirroring the pattern used in autoeval/clients.py."""
    import os
    _client = _anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
    user_messages = [m for m in messages if m["role"] != "system"]
    response = _client.messages.create(
        model=model,
        max_tokens=768,
        temperature=0,
        system=system_msg,
        messages=user_messages,
    )
    return response.content[0].text


def shopping_get_auth_token() -> str:
    response = requests.post(
        url=f"{SHOPPING}/rest/default/V1/integration/admin/token",
        headers={"content-type": "application/json"},
        data=json.dumps(
            {
                "username": ACCOUNTS["shopping_site_admin"]["username"],
                "password": ACCOUNTS["shopping_site_admin"]["password"],
            }
        ),
    )
    token: str = response.json()
    return token


def shopping_get_latest_order_url() -> str:
    """Get the latest order url from the shopping website."""

    header = {
        "Authorization": f"Bearer {shopping_get_auth_token()}",
        "Content-Type": "application/json",
    }

    params = {
        "searchCriteria[sortOrders][0][field]": "created_at",
        "searchCriteria[sortOrders][0][direction]": "DESC",
        "searchCriteria[pageSize]": "1",
    }

    response = requests.get(
        f"{SHOPPING}/rest/V1/orders", params=params, headers=header
    )
    assert response.status_code == 200
    response_obj = response.json()["items"][0]
    order_id = int(response_obj["increment_id"])
    order_url = f"{SHOPPING}/sales/order/view/order_id/{order_id}/"
    return order_url


def shopping_get_sku_latest_review_author(sku: str) -> str:
    """Get the latest review for shopping admin."""
    header = {
        "Authorization": f"Bearer {shopping_get_auth_token()}",
        "Content-Type": "application/json",
    }
    response = requests.get(
        f"{SHOPPING}/rest/V1/products/{sku}/reviews", headers=header
    )
    assert response.status_code == 200
    response_obj = response.json()
    if len(response_obj) == 0:
        return ""
    author: str = response_obj[-1]["nickname"]
    return author


def shopping_get_sku_latest_review_rating(sku: str) -> str:
    """Get the latest review for shopping admin."""
    header = {
        "Authorization": f"Bearer {shopping_get_auth_token()}",
        "Content-Type": "application/json",
    }
    response = requests.get(
        f"{SHOPPING}/rest/V1/products/{sku}/reviews", headers=header
    )
    assert response.status_code == 200
    response_obj = response.json()
    if len(response_obj) == 0:
        return ""
    assert response_obj[0]["ratings"][0]["rating_name"] == "Rating"
    rating: str = str(response_obj[-1]["ratings"][0]["percent"])
    return rating


def reddit_get_post_url(url: str) -> str:
    """Get the post url"""
    # Url is http://domain/f/subreddit/post_id/...
    # get domain, subreddit, post_id
    domain = urlparse(url).netloc
    tok_url = urlparse(url).path.split("/")
    # not a valid post/comment url, return the url as is
    if len(tok_url) < 4:
        return url
    if tok_url[1] != "f":
        return url
    subreddit = urlparse(url).path.split("/")[2]
    post_id = urlparse(url).path.split("/")[3]
    scheme = urlparse(url).scheme
    post_url = f"{scheme}://{domain}/f/{subreddit}/{post_id}/"
    return post_url


def gitlab_get_project_memeber_role(page: Page, account_name: str) -> str:
    # get the account index
    try:
        account_idx = page.evaluate(
            f"""(() => {{
                const elements = document.querySelectorAll("td[data-label='Account'] span.gl-avatar-labeled-sublabel");
                let index = -1;  // Default value if not found

                for(let i = 0; i < elements.length; i++) {{
                    if(elements[i].outerText === '@{account_name}') {{
                        index = i;
                        break;
                    }}
                }}

                return index;
            }})()"""
        )

        # get the role
        role: str = page.evaluate(
            f"""(() => {{
                return document.querySelectorAll("td.col-max-role span")[{account_idx}].outerText;
            }})()"""
        )
    except Exception:
        role = ""

    return role


def llm_fuzzy_match(pred: str, reference: str, question: str) -> float:
    """Check whether the prediction matches the reference using Claude."""
    import logging
    logger = logging.getLogger(__name__)

    message = (
        "You are grading a student's answer to a question. "
        "Your job is to check whether the student's answer contains the information specified in the reference answer.\n\n"
        "IMPORTANT RULES:\n"
        "- The student's answer is CORRECT if it contains the reference information, even if it also includes additional correct details.\n"
        "- Do NOT penalise extra information. A more complete answer is still correct.\n"
        "- The student's answer is INCORRECT only if the reference information is missing or wrong.\n"
        "- The string 'N/A' means the task is not achievable.\n\n"
        f"Question: {question}\n"
        f"Reference answer: {reference}\n"
        f"Student answer: {pred}\n\n"
        "Does the student's answer contain the reference information? "
        "Respond with exactly one word: correct or incorrect."
    )
    messages = [
        {"role": "system", "content": "You are a precise grading assistant. Respond with exactly one word: correct or incorrect."},
        {"role": "user", "content": message},
    ]

    logger.info(f"LLM_FUZZY_MATCH: Evaluating reference='{reference}' against pred='{pred[:100]}{'...' if len(pred) > 100 else ''}'")
    logger.info(f"LLM_FUZZY_MATCH: Full evaluation prompt:\n{message}")

    try:
        response = _generate_from_claude(messages)

        logger.info(f"LLM_FUZZY_MATCH: Raw LLM response: '{response}'")

        response_lower = response.lower()
        logger.info(f"LLM_FUZZY_MATCH: Lowercased response: '{response_lower}'")

        if "incorrect" in response_lower:
            score = 0.0
            logger.info(f"LLM_FUZZY_MATCH: RESULT=FAIL (score=0.0) - Found 'incorrect'")
        elif "correct" in response_lower:
            score = 1.0
            logger.info(f"LLM_FUZZY_MATCH: RESULT=PASS (score=1.0) - Found 'correct'")
        else:
            logger.warning(f"LLM_FUZZY_MATCH: UNEXPECTED RESPONSE FORMAT - no clear judgment found")
            assert "correct" in response_lower

        return score

    except AssertionError as e:
        logger.error(f"LLM_FUZZY_MATCH: AssertionError caught - LLM response did not contain 'correct': {e}")
        logger.error(f"LLM_FUZZY_MATCH: Returning 0.0 due to AssertionError")
        return 0.0
    except Exception as e:
        logger.error(f"LLM_FUZZY_MATCH: Unexpected error during evaluation: {type(e).__name__}: {e}")
        logger.error(f"LLM_FUZZY_MATCH: Returning 0.0 due to error")
        return 0.0


def llm_ua_match(pred: str, reference: str, question: str) -> float:
    """Check whether the prediction matches the reference with Claude."""
    import logging
    logger = logging.getLogger(__name__)

    messages: list[dict[str, Any]] = []
    message = ""
    message += f"task: {question}\n"
    message += f"actual unachievable reason: {reference}\n"
    message += f"reported unachievable reason: {pred}\n"
    message += (
        "The task described above is inherently unachievable due to the reason specified under 'actual unachievable reason'. "
        "An individual previously attempted this task and was unable to complete it. They provided a reason for their failure, "
        "which is listed under 'reported unachievable reason'. Your role is to review both the actual and reported reasons. "
        "Determine if the reported reason aligns with the actual reason, even if implicitly. "
        "If the stated reason is in line with the actual reason, respond with exactly one word: same. "
        "Otherwise, respond with exactly one word: different."
    )
    messages = [
        {"role": "system", "content": "You are a precise grading assistant. Respond with exactly one word: same or different."},
        {"role": "user", "content": message},
    ]

    # Log the evaluation attempt
    logger.info(f"LLM_UA_MATCH: Evaluating unachievable reason match")
    logger.info(f"LLM_UA_MATCH: Reference='{reference}' vs Pred='{pred[:100]}{'...' if len(pred) > 100 else ''}'")
    logger.info(f"LLM_UA_MATCH: Full evaluation prompt:\n{message}")
    
    try:
        response = _generate_from_claude(messages)
        
        # Log the raw response before processing
        logger.info(f"LLM_UA_MATCH: Raw LLM response: '{response}'")
        
        response_lower = response.lower()
        logger.info(f"LLM_UA_MATCH: Lowercased response: '{response_lower}'")
        
        if "different" in response_lower:
            score = 0.0
            logger.info(f"LLM_UA_MATCH: RESULT=FAIL (score=0.0) - Found 'different'")
        elif "same" in response_lower:
            score = 1.0
            logger.info(f"LLM_UA_MATCH: RESULT=PASS (score=1.0) - Found 'same'")
        else:
            logger.warning(f"LLM_UA_MATCH: UNEXPECTED RESPONSE FORMAT - no clear judgment found")
            logger.warning(f"LLM_UA_MATCH: This will trigger AssertionError and return 0.0")
            assert "same" in response_lower
            
        return score
        
    except AssertionError as e:
        logger.error(f"LLM_UA_MATCH: AssertionError caught - LLM response did not contain 'same': {e}")
        logger.error(f"LLM_UA_MATCH: Returning 0.0 due to AssertionError")
        return 0.0
    except Exception as e:
        logger.error(f"LLM_UA_MATCH: Unexpected error during evaluation: {type(e).__name__}: {e}")
        logger.error(f"LLM_UA_MATCH: Returning 0.0 due to error")
        return 0.0


class PseudoPage:
    def __init__(self, original_page: Page, url: str):
        self.url = url
        self.original_page = original_page

    def __getattr__(self, attr: str) -> Any:
        # Delegate attribute access to the original page object
        if attr not in ["url"]:
            return getattr(self.original_page, attr)
        else:
            return getattr(self, attr)
