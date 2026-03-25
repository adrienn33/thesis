import base64
import dataclasses
import io
import os
import anthropic
import logging

import numpy as np
from PIL import Image

from browsergym.experiments import AbstractAgentArgs, Agent
from browsergym.utils.obs import flatten_axtree_to_str, flatten_dom_to_str, prune_html

from custom_action_set import CustomActionSet
from actions import ACTION_DICT, get_action_dict
from mcp_integration.client import MCPManager, MCPServerConfig

logger = logging.getLogger(__name__)


def image_to_jpg_base64_url(image: np.ndarray | Image.Image):
    """Convert a numpy array to a base64 encoded image url."""

    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    if image.mode in ("RGBA", "LA"):
        image = image.convert("RGB")

    with io.BytesIO() as buffer:
        image.save(buffer, format="JPEG")
        image_base64 = base64.b64encode(buffer.getvalue()).decode()

    return f"data:image/jpeg;base64,{image_base64}"


class DemoAgent(Agent):
    """A basic agent using OpenAI API, to demonstrate BrowserGym's functionalities."""

    def obs_preprocessor(self, obs: dict) -> dict:

        return {
            "chat_messages": obs["chat_messages"],
            "screenshot": obs["screenshot"],
            "goal_object": obs["goal_object"],
            "last_action": obs["last_action"],
            "last_action_error": obs["last_action_error"],
            "last_action_output": obs.get("last_action_output", ""),
            "open_pages_urls": obs["open_pages_urls"],
            "open_pages_titles": obs["open_pages_titles"],
            "active_page_index": obs["active_page_index"],
            "axtree_txt": flatten_axtree_to_str(obs["axtree_object"]),
            "pruned_html": prune_html(flatten_dom_to_str(obs["dom_object"])),
        }

    def __init__(
        self,
        model_name: str,
        chat_mode: bool,
        demo_mode: str,
        use_html: bool,
        use_axtree: bool,
        use_screenshot: bool,
        websites: tuple[str],
        actions: list[str],
        memory: str,
        mcp_servers: list = None,
    ) -> None:
        super().__init__()
        self.model_name = model_name
        self.chat_mode = chat_mode
        self.use_html = use_html
        self.use_axtree = use_axtree
        self.use_screenshot = use_screenshot

        if not (use_html or use_axtree):
            raise ValueError(f"Either use_html or use_axtree must be set to True.")

        # Refresh ACTION_DICT to pick up any newly added functions
        global ACTION_DICT
        ACTION_DICT = get_action_dict()
        
        # Include general, webarena, and website-specific actions
        custom_actions = ACTION_DICT["general"] + ACTION_DICT["webarena"]
        for website in websites:
            if website in ACTION_DICT:
                custom_actions.extend(ACTION_DICT[website])
        
        # Initialize MCP manager and connect to servers
        self.mcp_manager = MCPManager()
        if mcp_servers:
            for server_config_dict in mcp_servers:
                server_config = MCPServerConfig(**server_config_dict)
                success = self.mcp_manager.add_server(server_config)
                if success:
                    logger.info(f"Connected to MCP server: {server_config.name}")
                else:
                    logger.warning(f"Failed to connect to MCP server: {server_config.name}")
        
        # Get MCP tools and add them to custom actions
        mcp_tools = self.mcp_manager.get_all_tools()
        for tool_name, tool_wrapper in mcp_tools.items():
            # Create a simple function that can be called like regular actions
            # Use exec to create function at module level to avoid indentation issues
            func_name = tool_name.replace("-", "_")
            # Generate proper function signature from MCP tool schema
            schema = tool_wrapper.tool_info.input_schema
            properties = schema.get('properties', {})
            required = schema.get('required', [])
            
            # Build parameter list and argument mapping
            params = []
            arg_mapping = []
            for param_name, param_info in properties.items():
                param_type = param_info.get('type', 'str')
                if param_name in required:
                    params.append(f"{param_name}")
                    arg_mapping.append(f"'{param_name}': {param_name}")
                else:
                    params.append(f"{param_name}=None")
                    arg_mapping.append(f"'{param_name}': {param_name}")
            
            param_str = ', '.join(params)
            args_dict = '{' + ', '.join(arg_mapping) + '}'
            
            # Extract examples from tool description if available
            tool_description = tool_wrapper.get_description()
            examples_section = ""
            if "Examples:" in tool_description:
                # Extract the examples part and convert tool name format
                _, examples_part = tool_description.split("Examples:", 1)
                examples_lines = []
                for line in examples_part.strip().split('\n'):
                    line = line.strip()
                    if line:
                        # Replace the original function name with our wrapped version
                        line = line.replace(tool_name.replace('-', '_'), func_name)
                        examples_lines.append(f"    {line}")
                examples_section = '\n'.join(examples_lines)
            else:
                # Fallback generic example using first required param
                first_param = params[0].split('=')[0] if params else ""
                if first_param:
                    examples_section = f"    {func_name}(\"example_value\")"
                else:
                    examples_section = f"    {func_name}()"
            
            func_code = f"""
def {func_name}({param_str}):
    '''{tool_wrapper.get_description()}'''
    # This is a MCP tool wrapper - actual implementation handled by MCP server
    return _call_mcp_tool('{tool_name}', **{args_dict})
"""
            
            # Store the wrapper in main module globals so the function can access it
            import __main__
            if not hasattr(__main__, '_mcp_tool_wrappers'):
                __main__._mcp_tool_wrappers = {}
            __main__._mcp_tool_wrappers[tool_name] = tool_wrapper
            
            # Execute the function definition in main module globals so it's accessible in execution context
            import __main__
            exec(func_code, vars(__main__))
            
            # Get the created function and add it to custom actions
            mcp_func = getattr(__main__, func_name)
            # Store the original tool name as an attribute for later use
            mcp_func._original_tool_name = tool_name
            custom_actions.append(mcp_func)

        self.action_set = CustomActionSet(
            subsets=["custom"],
            custom_actions=custom_actions,
            strict=False,  # less strict on the parsing of the actions
            multiaction=True,  # enable the agent to take multiple actions at once
            demo_mode=demo_mode,  # add visual effects
            mcp_manager=self.mcp_manager,  # pass MCP manager for tool execution
        )

        self.action_history = []

        self.actions = actions
        self.num_actions = 0
        
        if memory is None: self.memory = None
        else: 
            paths = memory.split(' ')
            self.memory = '\n\n'.join([open(p, 'r').read() for p in paths])
            if self.memory.strip() == "":
                self.memory = None

    def _get_skill_instructions(self) -> str:
        """Return conditional skill instructions based on MCP availability."""
        has_mcp = bool(self.mcp_manager.get_all_tools())
        
        # Get available ASI skills dynamically
        try:
            from actions import shopping
            import importlib
            importlib.reload(shopping)
            asi_functions = [name for name in dir(shopping) if callable(getattr(shopping, name)) and name.startswith('asi_')]
            
            if asi_functions:
                skill_list = "\n".join([f"    - {func}()" for func in asi_functions])
                available_skills = f"\n\nAvailable ASI skills:\n{skill_list}"
            else:
                available_skills = "\n\nNo ASI skills available yet."
        except:
            available_skills = "\n\nCould not load ASI skills."
        
        if has_mcp:
            return f"""IMPORTANT: You have access to MCP tools (prefixed with magento_review_server_, magento_product_server_, magento_checkout_server_, magento_wishlist_server_, magento_account_server_) and ASI skills (prefixed with asi_).{available_skills}

    IMPORTANT: Only use ASI skills that are listed above. Do not make up or guess skill names.

    CRITICAL — HOW send_msg_to_user() WORKS:
    send_msg_to_user() is the SUBMIT BUTTON. Calling it immediately ends the episode and the
    evaluator scores whatever state the browser is in at that moment. No further actions are
    possible after calling it.
    - For INFORMATION tasks: call it exactly once with your final answer. That is how you submit.
    - For NAVIGATION tasks: navigate to the correct page FIRST, then call
      send_msg_to_user("Done") to cleanly terminate. Only call it once you are already on
      the correct page. NEVER call it mid-task to report progress or announce a fallback plan —
      that will terminate the episode before you have navigated anywhere.
    - For STATE-CHANGE tasks: complete the browser action (add to cart, submit form, etc.)
      FIRST, then call send_msg_to_user("Done") to terminate.

    TASK-TYPE AWARENESS — How you complete the task depends on what is being asked:

    1. INFORMATION RETRIEVAL (e.g., "What is the price range of...", "List the reviewers who...",
       "How much did I spend on..."):
       - Use MCP tools to query data, process results, and report via send_msg_to_user().
       - Browser navigation is NOT required.

    ANSWER QUALITY RULES — for ALL information retrieval tasks:

    a) DISTILL, DO NOT DUMP: Never pass raw Python dicts, lists, or objects to send_msg_to_user().
       Always extract the specific value the user asked for and state it as a plain sentence.
       BAD:  send_msg_to_user("Options: " + str(item["selected_options"]))
             produces: "Options: [{{'label': 'Color', 'value': 'Mist 16*24'}}]"
       GOOD: send_msg_to_user("The color configuration is Mist 16*24.")

    b) WHEN LOOKING UP PRODUCT CONFIGURATION (size, color, style bought in an order):
       - Call get_order_details(order_id) to retrieve items.
       - Each item has a `selected_options` field: a list of {{"label": ..., "value": ...}} dicts
         representing the exact configuration the customer chose at time of purchase.
       - Match items using SPECIFIC product-type keywords — do NOT match generic words like
         "frame" or "art" which appear inside unrelated product names (e.g., "bed frame", "sofa frame").
         Instead use the most distinctive noun from the task: "canvas", "poster", "picture frame",
         "wall art print", "mouth guard", "plant", etc.
       - Once you find the matching item, extract the answer from `selected_options`:
           * For COLOR: find the option whose label contains "color" and take its value.
           * For SIZE: FIRST try to find an option whose label contains "size". If none exists,
             scan ALL option values for a dimension pattern like "16x24" and use that match:
               import re
               size_val = next((o["value"] for o in item["selected_options"] if "size" in o["label"].lower()), None)
               if size_val is None:
                   for o in item["selected_options"]:
                       m = re.search(r"\\d+x\\d+", o["value"])
                       if m:
                           size_val = m.group(0)
                           break
               send_msg_to_user("The size configuration is " + str(size_val))
       - Always state the extracted value as a plain sentence. Never dump the raw selected_options list.

    c) PRICE RANGE QUERIES: Always state both endpoints as plain numbers with dollar signs.
       Never dump product lists. E.g.: send_msg_to_user("Price range: $" + str(round(min_p,2)) + " to $" + str(round(max_p,2)))

    2. NAVIGATION / "SHOW ME" (e.g., "Show me products under $25 in women shoes",
       "Show me the most recent completed order", "List products from X category sorted by price"):
       - The task requires you to NAVIGATE THE BROWSER to the correct page with the right
         filters/sorting applied. Using MCP to look up data and sending a chat message will NOT
         satisfy the task.
       - You must use browser actions (click, fill, select_option) to navigate to the appropriate
         page, apply filters, and leave the browser on that page.
       - MCP tools may be used to look up IDs or URLs to help you navigate, but the final state
         must be the browser on the correct page.
       - Only call send_msg_to_user("Done") after you have finished navigating and confirmed
         you are on the correct page. Never call it mid-task to report progress or announce
         a fallback — that ends the episode immediately on the wrong page.

       CRITICAL — USE THE "url" FIELD WHEN NAVIGATING WITH MCP:
       search_products(), get_product_details(), and list_categories() all return a "url" field
       containing the canonical SEO-friendly URL for that product or category.
       - ALWAYS use goto(result["url"]) to navigate — never construct /catalog/product/view/id/...
         or /catalog/category/view/id/... URLs yourself from entity IDs.
       - The evaluator compares the final browser URL against the expected SEO slug. An ID-based
         URL pointing to the same page will fail the check.
       - Example: goto(products[0]["url"]) not goto("http://localhost:7770/catalog/product/view/id/123")

       CRITICAL — "SHOW ME SOMETHING FOR [CONDITION/PROBLEM]" tasks:
       Tasks like "show me something that could alleviate jaw bruxism" or "show me a product
       that helps with back pain" require you to navigate all the way to an INDIVIDUAL PRODUCT
       PAGE — not just a search results or category listing page.
       - Search for the condition or relevant product type to find candidates.
       - Evaluate the search results and CLICK INTO the most relevant product to open its
         product detail page.
       - Your final browser state must be ON the product detail page, not the search results.
       - The evaluator checks the HTML of your last page — a product listing page will NOT
         contain the detailed product description text needed to pass.

    3. STATE-CHANGE (e.g., "Add X to my wish list", "Rate my recent purchase with 5 stars",
       "Fill the contact us form", "Buy the highest rated product", "Add X to cart"):
       - These tasks require VISIBLE CHANGES on the website via browser actions.
       - For BUY / REORDER tasks (e.g., "Buy the highest rated product", "Reorder my cancelled item"):
         Adding the item to the cart is NOT sufficient. You must complete the full checkout:
         1. Add the product to cart (click "Add to Cart" on the product page).
         2. After the success alert, navigate to the cart: goto("http://localhost:7770/checkout/cart/")
         3. On the cart page, click the "Proceed to Checkout" button. Do NOT use goto("/checkout")
            directly — Magento's checkout is a JavaScript SPA and direct URL navigation will redirect
            back to the cart. Always use the "Proceed to Checkout" button.
         4. On the shipping step, the address is pre-filled — click "Next" to continue.
         5. On the shipping method step, select "Flat Rate" if prompted, then click "Next".
         6. Click "Place Order" to submit the order.
         7. The task is complete ONLY when you see the order confirmation page with an order number.
         Stopping after "Added to cart" will FAIL — the evaluator checks the placed order, not the cart.
       - For CART operations (add only, no buy): You MUST use browser actions (search, click "Add to Cart", etc.).
         Do NOT use MCP cart tools — they are disabled.
       - For WISHLIST operations: You MUST use browser actions. Navigate to the product page
         and click "Add to Wish List". Do NOT use MCP wishlist write tools — they are disabled.
         You may use MCP get_wishlist to verify the item was added after completing the browser action.
       - For REVIEW submission: You may use MCP create_review to submit the review. The tool
         returns a "product_url" field. After a successful create_review call, you MUST call
         goto(result["product_url"]) to navigate to that product page before ending the task.
         This confirms the review is visible and satisfies the evaluator.
       - For FORMS (contact us, address change, any form): You MUST use browser actions to fill
         the form fields. Whether you submit depends on the task wording:
           * If the task says "Don't submit", "Don't submit yet", "Draft", or "I will check" —
             fill all fields with the correct content, then STOP. Do NOT click Submit/Send.
             The evaluator checks the filled form HTML, not a confirmation page.
           * If the task says "Fill", "Submit", "Send", or has no qualifier — fill all fields
             and then click the Submit/Send button to complete the action.
         CRITICAL: Submitting a "Don't submit" form will CLEAR all field contents in Magento,
         causing the evaluator to see an empty form and score 0. Leave the form filled but unsubmitted.
       - MCP tools may be used as a read/lookup layer for any state-change task (e.g., use
         list_orders to find the order number before filling a refund form).

    MCP FALLBACK RULE — If an MCP tool returns empty results, switch to browser:
    MCP tools query a structured database and can miss products or data due to naming mismatches,
    missing records, or narrow query parameters. If an MCP tool returns an empty list or no
    matching results, do NOT report failure or stop. Instead:
    - Immediately fall back to browser-based navigation to complete the task.
    - Use the search bar, category menus, or filters to find the data manually.
    - Treat an empty MCP result as a signal to try a different approach, not as a final answer.
    - Do NOT call send_msg_to_user() to announce the fallback — just execute the browser actions.
      send_msg_to_user() is the submit button; calling it before you finish navigating ends the
      episode immediately on the wrong page.
    Example: if magento_product_server_search_products(name="X") returns [], navigate to the
    store search and type "X" in the search bar instead.

    IMPORTANT - Semantic review search: When searching reviews for a topic (e.g. "small size", "battery life", "poor quality"), do NOT search for only the literal phrase. Reviewers express the same idea in many ways. You MUST expand the search to include synonyms, related phrases, and common alternative wordings. For example:
    - "small" → ["small", "tiny", "compact", "narrow", "tight", "little", "miniature", "slim", "thin", "petite"]
    - "battery life" → ["battery", "battery life", "charge", "charging", "run time", "dies quickly", "drains fast"]
    - "poor quality" → ["poor quality", "cheap", "flimsy", "low quality", "poorly made", "bad quality", "disappointing"]
    Always pass a broad list of synonyms/related terms as the keywords argument to ensure no relevant reviews are missed."""
        else:
            return f"""IMPORTANT: You have access to ASI skills (prefixed with asi_) that are reusable, tested browser-based skills.{available_skills}

    IMPORTANT: Only use ASI skills that are listed above. Do not make up or guess skill names. If no suitable ASI skill exists, use browser actions.

    TASK-TYPE AWARENESS — How you complete the task depends on what is being asked:

    1. INFORMATION RETRIEVAL (e.g., "What is the price range of...", "List the reviewers who..."):
       - ASI skills are preferred for looking up and reporting data.
       - Use send_msg_to_user() to report the result.

    2. NAVIGATION / "SHOW ME" (e.g., "Show me products under $25", "Navigate to category X"):
       - Browser actions are required. You must navigate the browser to the correct page.
       - ASI skills may assist with lookups, but cannot replace browser navigation.

       CRITICAL — "SHOW ME SOMETHING FOR [CONDITION/PROBLEM]" tasks:
       Tasks like "show me something that could alleviate jaw bruxism" require navigating to
       an INDIVIDUAL PRODUCT PAGE, not just a search results page. Search for candidates, then
       click into the most relevant product so the browser ends on the product detail page.

    3. STATE-CHANGE (e.g., "Add to cart", "Submit a form", "Update account info"):
       - Browser actions are required for all state-change tasks.
       - ASI skills may assist with finding IDs or URLs, but the final action must be browser-based.

    IMPORTANT - Semantic review search: When searching reviews for a topic (e.g. "small size", "battery life", "poor quality"), do NOT search for only the literal phrase. Reviewers express the same idea in many ways. You MUST expand the search to include synonyms, related phrases, and common alternative wordings. Always pass a broad list of synonyms/related terms as the keywords argument to ensure no relevant reviews are missed."""

    def get_action(self, obs: dict) -> tuple[str, dict]:
        if len(self.actions) == 0 or (self.num_actions > (len(self.actions) - 1)):
            system_msgs = []
            user_msgs = []

            if self.chat_mode:
                system_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
    # Instructions

    You are a dedicated shopping agent, and your goal is to help the user complete their online 
    shopping tasks. You can communicate with the user via chat, to which the user gives you 
    instructions and to which you can send back messages. You have access to a web browser 
    that both you and the user can see, and with which only you can interact via specific 
    commands.

    Review the instructions from the user, the current state of the page and all other information
    to find the best possible next action to accomplish your goal. Your answer will be interpreted
    and executed by a program, make sure to follow the formatting instructions.
    """,
                    }
                )

                # append chat messages
                user_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
    # Chat Messages
    """,
                    }
                )
                for msg in obs["chat_messages"]:
                    if msg["role"] in ("user", "assistant", "infeasible"):
                        user_msgs.append(
                            {
                                "type": "text",
                                "text": f"""\
    - [{msg['role']}] {msg['message']}
    """,
                            }
                        )
                    elif msg["role"] == "user_image":
                        user_msgs.append({"type": "image_url", "image_url": msg["message"]})
                    else:
                        raise ValueError(f"Unexpected chat message role {repr(msg['role'])}")

            else:
                assert obs["goal_object"], "The goal is missing."
                system_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
    # Instructions

    Review the current state of the page and all other information to find the best
    possible next action to accomplish your goal. Your answer will be interpreted
    and executed by a program, make sure to follow the formatting instructions.
    """,
                    }
                )
                # append memory
                if self.memory is not None:
                    system_msgs.append({
                        "type": "text",
                        "text": self.memory,
                    })
                # append goal
                user_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
    # Goal
    """,
                    }
                )
                # goal_object is directly presented as a list of openai-style messages
                user_msgs.extend(obs["goal_object"])

            # append url of all open tabs
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
    # Currently open tabs
    """,
                }
            )
            for page_index, (page_url, page_title) in enumerate(
                zip(obs["open_pages_urls"], obs["open_pages_titles"])
            ):
                user_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
    Tab {page_index}{" (active tab)" if page_index == obs["active_page_index"] else ""}
    Title: {page_title}
    URL: {page_url}
    """,
                    }
                )

            # append page AXTree (if asked)
            if self.use_axtree:
                user_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
    # Current page Accessibility Tree

    {obs["axtree_txt"]}

    """,
                    }
                )
            # append page HTML (if asked)
            if self.use_html:
                user_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
    # Current page DOM

    {obs["pruned_html"]}

    """,
                    }
                )

            # append page screenshot (if asked)
            if self.use_screenshot:
                user_msgs.append(
                    {
                        "type": "text",
                        "text": """\
    # Current page Screenshot
    """,
                    }
                )
                user_msgs.append(
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_to_jpg_base64_url(obs["screenshot"]),
                            "detail": "auto",
                        },  # Literal["low", "high", "auto"] = "auto"
                    }
                )
        
            # append action space description
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
    # Action Space

    {self.action_set.describe(with_long_description=True, with_examples=True)}
    
    {self._get_skill_instructions()}
    
    CRITICAL: When processing the results of skill functions containing lists/arrays of data:
    - NEVER manually transcribe or copy-paste data items one by one
    - ALWAYS use programmatic iteration (for loops, list comprehensions) to process all items
    - ALWAYS verify your count matches the returned data length (e.g., if it returns len=21, your analysis should include all 21 items)
    - Use built-in functions like sum(), len(), max(), min() for calculations instead of manual arithmetic
    
    CRITICAL: When writing Python code in triple backticks, write COMPLETE executable code that accomplishes the task. Don't just call a function - capture the result, process it, and report findings using send_msg_to_user(). For example, when searching reviews: capture return value → filter/process data → send results to user.

    CRITICAL: When reporting results to the user, you MUST send the result via message.
    
    Example:
    ```
    # WRONG - execution stops after the call
    magento_product_server_search_products(name="Amazon Basics")
    
    # CORRECT - capture result and process it
    # products = magento_product_server_search_products(name="Amazon Basics")
    # min_price = min(float(p['price']) for p in products)
    # max_price = max(float(p['price']) for p in products) 
    # send_msg_to_user(f"Price range: ${{min_price:.2f}} - ${{max_price:.2f}}")
    ```
    
    Here are examples of actions with chain-of-thought reasoning:

    I now need to click on the Submit button to send the form. I will use the click action on the button, which has bid 12.
    ```click("12")```

    I found the information requested by the user, I will send it to the chat.
    ```send_msg_to_user("The price for a 15" laptop is 1499 USD.")```

    Only wrap the to-be-executed action in triple backticks. Do not wrap the reasoning or the action description.

    """,
                }
            )

            # append past actions (and last error message) if any
            if self.action_history:
                user_msgs.append(
                    {
                        "type": "text",
                        "text": f"""\
    # History of past actions
    """,
                    }
                )
                user_msgs.extend(
                    [
                        {
                            "type": "text",
                            "text": f"""\

    {action}
    """,
                        }
                        for action in self.action_history
                    ]
                )

                if obs["last_action_error"]:
                    user_msgs.append(
                        {
                            "type": "text",
                            "text": f"""\
    # Error message from last action

    {obs["last_action_error"]}

    """,
                        }
                    )
                
                # Show REPL-style output from previous action
                if obs.get("last_action_output"):
                    user_msgs.append(
                        {
                            "type": "text",
                            "text": f"""\
    # Output from last action

    {obs["last_action_output"]}

    """,
                        }
                    )

            # ask for the next action
            user_msgs.append(
                {
                    "type": "text",
                    "text": f"""\
    # Next action

    You will now think step by step and produce your next best action. Reflect on your past actions, any resulting error message, and the current state of the page before deciding on your next action.
    """,
                }
            )

            prompt_text_strings = []
            for message in system_msgs + user_msgs:
                match message["type"]:
                    case "text":
                        prompt_text_strings.append(message["text"])
                    case "image_url":
                        image_url = message["image_url"]
                        if isinstance(message["image_url"], dict):
                            image_url = image_url["url"]
                        if image_url.startswith("data:image"):
                            prompt_text_strings.append(
                                "image_url: " + image_url[:30] + "... (truncated)"
                            )
                        else:
                            prompt_text_strings.append("image_url: " + image_url)
                    case _:
                        raise ValueError(
                            f"Unknown message type {repr(message['type'])} in the task goal."
                        )

            import time
            import random
            
            max_retries = 3
            base_delay = 30  # 30 second base delay for rate limits
            
            for attempt in range(max_retries):
                try:
                    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
                    response = client.messages.create(
                        model=self.model_name.replace("litellm/neulab/", "").replace("claude-", "claude-"),
                        max_tokens=4096,
                        temperature=0.0,
                        system=system_msgs,
                        messages=[
                            {"role": "user", "content": user_msgs},
                        ],
                    )
                    action = response.content[0].text
                    action = action.replace('```python', '```')
                    break  # Success, exit retry loop
                    
                except anthropic.RateLimitError as e:
                    if attempt < max_retries - 1:
                        delay = base_delay + random.uniform(0, 10)  # Add jitter
                        print(f"Rate limit hit, waiting {delay:.1f} seconds before retry {attempt + 2}/{max_retries}")
                        time.sleep(delay)
                    else:
                        print(f"Rate limit error after {max_retries} attempts: {e}")
                        action = ""
                        
                except Exception as e:
                    print(f"Error calling Anthropic API: {e}")
                    action = ""
                    break  # Don't retry for non-rate-limit errors
        else:
            if self.num_actions > (len(self.actions) - 1):
                action = None
            else:
                action = self.actions[self.num_actions]
            self.num_actions += 1

        self.action_history.append(action)

        return action, {}




@dataclasses.dataclass
class DemoAgentArgs(AbstractAgentArgs):
    """
    This class is meant to store the arguments that define the agent.

    By isolating them in a dataclass, this ensures serialization without storing
    internal states of the agent.
    """

    model_name: str = "gpt-4o-mini"
    chat_mode: bool = False
    demo_mode: str = "off"
    use_html: bool = False
    use_axtree: bool = True
    use_screenshot: bool = False
    websites: tuple[str] = ()
    actions: list[str] = ()
    memory: str = None
    mcp_servers: list = None

    def make_agent(self):
        return DemoAgent(
            model_name=self.model_name,
            chat_mode=self.chat_mode,
            demo_mode=self.demo_mode,
            use_html=self.use_html,
            use_axtree=self.use_axtree,
            use_screenshot=self.use_screenshot,
            websites=self.websites,
            actions=self.actions,
            memory=self.memory,
            mcp_servers=self.mcp_servers,
        )
