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

    You are a UI Assistant, your goal is to help the user perform tasks using a web browser. You can
    communicate with the user via a chat, to which the user gives you instructions and to which you
    can send back messages. You have access to a web browser that both you and the user can see,
    and with which only you can interact via specific commands.

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

    When high-level functions such as `get_driving_time` or 'book_flights` are available, please prioritize using them.
    
    IMPORTANT: If MCP tool functions are available (functions starting with `magento_review_server_`, `magento_product_server_`, or similar prefixes), you MUST prioritize using them over browser interactions when they can accomplish your goal. MCP tools provide direct database access and are more reliable than browser scraping.
    
    CRITICAL: When writing Python code in triple backticks, write COMPLETE executable code that accomplishes the task. Don't just call a function - capture the result, process it, and report findings using send_msg_to_user(). For example, when searching reviews: capture return value → filter/process data → send results to user.
    
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
                    print("Error message from last action: ", obs["last_action_error"])
                    # cont = input("Continue? (y/n): ")

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
